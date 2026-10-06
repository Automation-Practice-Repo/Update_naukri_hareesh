"""
Email notification utility for Naukri automation.
Sends email alerts with test results and screenshots.
"""
import os
import sys
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config_loader import ConfigLoader


class EmailNotifier:
    """Send email notifications with test results and attachments."""

    def __init__(self):
        self.config = ConfigLoader.load()
        self.enabled = self.config.get("email", {}).get("enabled", False) or \
                      os.environ.get("EMAIL_ENABLED", "false").lower() == "true"

    @property
    def smtp_host(self) -> str:
        return self.config.get("email", {}).get("smtp_host", "").replace(
            "${SMTP_HOST}", os.environ.get("SMTP_HOST", "")
        )

    @property
    def smtp_port(self) -> int:
        port = self.config.get("email", {}).get("smtp_port", 587)
        if isinstance(port, str) and port.startswith("${"):
            env_var = port.replace("${", "").replace("}", "")
            return int(os.environ.get(env_var, 587))
        return int(port)

    @property
    def smtp_user(self) -> str:
        return os.environ.get("SMTP_USER", self.config.get("email", {}).get("smtp_user", ""))

    @property
    def smtp_password(self) -> str:
        return os.environ.get("SMTP_PASSWORD", self.config.get("email", {}).get("smtp_password", ""))

    @property
    def sender(self) -> str:
        return os.environ.get("SMTP_USER", self.config.get("email", {}).get("sender", ""))

    @property
    def recipients(self) -> list:
        return self.config.get("email", {}).get("recipients", [])

    @property
    def notify_on_pass(self) -> bool:
        return self.config.get("email", {}).get("notify_on_pass", False)

    @property
    def notify_on_fail(self) -> bool:
        return self.config.get("email", {}).get("notify_on_fail", True)

    def send_notification(
        self,
        subject: str,
        body: str,
        attachments: list = None,
        is_html: bool = False,
    ) -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject line
            body: Email body content
            attachments: List of file paths to attach
            is_html: Whether the body is HTML
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.enabled:
            print("[INFO] Email notifications are disabled.")
            return True

        if not self.smtp_host or not self.smtp_user or not self.smtp_password:
            print("[WARN] Email configuration is incomplete. Skipping notification.")
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = ", ".join(self.recipients)
            msg["Subject"] = subject
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

            # Attach body
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Attach files
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        self._attach_file(msg, file_path)

            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"[SUCCESS] Email notification sent to {', '.join(self.recipients)}")
            return True

        except smtplib.SMTPAuthenticationError:
            print(f"[ERROR] SMTP authentication failed. Check credentials for {self.smtp_user}")
            return False
        except smtplib.SMTPRecipientsRefused:
            print(f"[ERROR] All recipients were refused: {self.recipients}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to send email notification: {e}")
            return False

    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> None:
        """Attach a file to the email message."""
        filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            file_data = f.read()

        # Try to determine file type
        if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                with open(file_path, "rb") as img_file:
                    img = MIMEImage(img_file.read())
                    img.add_header("Content-ID", f"<{filename}>")
                    msg.attach(img)
            except Exception:
                # Fallback to generic attachment
                part = MIMEApplication(file_data, _subtype=file_path.split(".")[-1])
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)
        else:
            part = MIMEApplication(file_data, _subtype=file_path.split(".")[-1])
            part.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(part)

    def send_test_result(
        self,
        test_name: str,
        success: bool,
        report_content: str = "",
        screenshot_path: str = None,
    ) -> bool:
        """
        Send a test result notification.
        
        Args:
            test_name: Name of the test that was run
            success: Whether the test passed
            report_content: Additional report content
            screenshot_path: Path to screenshot to attach
            
        Returns:
            True if email was sent successfully
        """
        if not self.enabled:
            return True

        # Check notification settings
        if success and not self.notify_on_pass:
            return True
        if not success and not self.notify_on_fail:
            return True

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "PASSED" if success else "FAILED"

        subject = f"[Naukri Automation] Test {status}: {test_name}"

        body = f"""
Naukri Automation Test Report
==============================

Test Name: {test_name}
Status: {status}
Timestamp: {timestamp}

Report Details:
{report_content if report_content else 'No additional details available.'}

This is an automated message from the Naukri Automation Scheduler.
        """

        attachments = []
        if screenshot_path and os.path.exists(screenshot_path):
            attachments.append(screenshot_path)

        return self.send_notification(subject, body, attachments)

    def send_summary_report(
        self,
        run_count: int,
        successes: int,
        failures: int,
        report_content: str = "",
    ) -> bool:
        """
        Send a daily/weekly summary report.
        
        Args:
            run_count: Number of test runs
            successes: Number of successful runs
            failures: Number of failed runs
            report_content: Additional report content
            
        Returns:
            True if email was sent successfully
        """
        if not self.enabled:
            return True

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subject = f"[Naukri Automation] Summary Report - {datetime.now().strftime('%Y-%m-%d')}"

        success_rate = (successes / run_count * 100) if run_count > 0 else 0

        body = f"""
Naukri Automation Summary Report
================================

Report Period: {timestamp}
Total Runs: {run_count}
Successful Runs: {successes}
Failed Runs: {failures}
Success Rate: {success_rate:.1f}%

Detailed Report:
{report_content if report_content else 'No additional details available.'}

This is an automated message from the Naukri Automation Scheduler.
        """

        return self.send_notification(subject, body)
