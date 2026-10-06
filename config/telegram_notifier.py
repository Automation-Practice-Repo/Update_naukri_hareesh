"""
Telegram notification utility for Naukri automation.
Sends test results and screenshots via Telegram Bot API.

Setup:
1. Open Telegram, search for @BotFather
2. Send /newbot and follow instructions to create a bot
3. Copy the bot token
4. Send a message to your bot
5. Visit https://api.telegram.org/bot<token>/getUpdates to get your chat_id
"""
import os
import sys
import requests
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config_loader import ConfigLoader


class TelegramNotifier:
    """Send Telegram notifications with test results and screenshots."""

    API_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self):
        self.config = ConfigLoader.load()
        self.enabled = self._is_enabled()
        self.bot_token = self._get_bot_token()
        self.chat_id = self._get_chat_id()

    def _is_enabled(self) -> bool:
        """Check if Telegram notifications are enabled."""
        env_enabled = os.environ.get("TELEGRAM_ENABLED", "").lower()
        if env_enabled in ("true", "1", "yes"):
            return True
        if env_enabled in ("false", "0", "no"):
            return False
        return self.config.get("telegram", {}).get("enabled", False)

    def _get_bot_token(self) -> str:
        """Get the Telegram bot token."""
        return os.environ.get("TELEGRAM_BOT_TOKEN", "")

    def _get_chat_id(self) -> str:
        """Get the Telegram chat ID."""
        return os.environ.get("TELEGRAM_CHAT_ID", "")

    @property
    def notify_on_pass(self) -> bool:
        """Whether to notify on pass."""
        return self.config.get("telegram", {}).get("notify_on_pass", False)

    @property
    def notify_on_fail(self) -> bool:
        """Whether to notify on fail."""
        return self.config.get("telegram", {}).get("notify_on_fail", True)

    def _is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str) -> bool:
        """
        Send a text message to Telegram.

        Args:
            text: Message text to send

        Returns:
            True if message was sent successfully
        """
        if not self.enabled:
            print("[INFO] Telegram notifications are disabled.")
            return True

        if not self._is_configured():
            print("[WARN] Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
            return False

        url = self.API_URL.format(token=self.bot_token, method="sendMessage")
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                print(f"[SUCCESS] Telegram message sent to chat {self.chat_id}")
                return True
            else:
                print(f"[ERROR] Telegram API error: {result.get('description', 'Unknown error')}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to send Telegram message: {e}")
            return False

    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        """
        Send a photo to Telegram.

        Args:
            photo_path: Path to the photo file
            caption: Caption for the photo

        Returns:
            True if photo was sent successfully
        """
        if not self.enabled:
            return True

        if not self._is_configured():
            return False

        if not os.path.exists(photo_path):
            print(f"[WARN] Photo not found: {photo_path}")
            return False

        url = self.API_URL.format(token=self.bot_token, method="sendPhoto")
        payload = {
            "chat_id": self.chat_id,
            "caption": caption,
        }

        try:
            with open(photo_path, "rb") as photo_file:
                files = {"photo": photo_file}
                response = requests.post(url, data=payload, files=files, timeout=30)
                response.raise_for_status()
                result = response.json()

            if result.get("ok"):
                print(f"[SUCCESS] Telegram photo sent to chat {self.chat_id}")
                return True
            else:
                print(f"[ERROR] Telegram API error: {result.get('description', 'Unknown error')}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to send Telegram photo: {e}")
            return False

    def send_test_result(
        self,
        test_name: str,
        success: bool,
        report_content: str = "",
        screenshot_path: str = None,
    ) -> bool:
        """
        Send a test result notification to Telegram.

        Args:
            test_name: Name of the test
            success: Whether the test passed
            report_content: Additional report content
            screenshot_path: Path to screenshot to send

        Returns:
            True if notification was sent successfully
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
        emoji = "✅" if success else "❌"

        # Build message
        message = (
            f"{emoji} <b>Naukri Automation Test {status}</b>\n"
            f"\n"
            f"<b>Test:</b> {test_name}\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Time:</b> {timestamp}\n"
        )

        if report_content:
            message += f"\n<b>Details:</b>\n<pre>{report_content}</pre>\n"

        message += f"\n<i>Automated message from Naukri Scheduler</i>"

        # Send message
        sent = self.send_message(message)

        # Send screenshot if available
        if screenshot_path and os.path.exists(screenshot_path):
            caption = f"{emoji} {test_name} - {status} at {timestamp}"
            self.send_photo(screenshot_path, caption)

        return sent

    def send_summary_report(
        self,
        run_count: int,
        successes: int,
        failures: int,
        report_content: str = "",
    ) -> bool:
        """
        Send a summary report to Telegram.

        Args:
            run_count: Total number of runs
            successes: Number of successful runs
            failures: Number of failed runs
            report_content: Additional report content

        Returns:
            True if notification was sent successfully
        """
        if not self.enabled:
            return True

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success_rate = (successes / run_count * 100) if run_count > 0 else 0

        message = (
            f"📊 <b>Naukri Automation Summary Report</b>\n"
            f"\n"
            f"<b>Date:</b> {timestamp}\n"
            f"<b>Total Runs:</b> {run_count}\n"
            f"<b>Successful:</b> ✅ {successes}\n"
            f"<b>Failed:</b> ❌ {failures}\n"
            f"<b>Success Rate:</b> {success_rate:.1f}%\n"
        )

        if report_content:
            message += f"\n<b>Details:</b>\n<pre>{report_content}</pre>\n"

        message += f"\n<i>Automated message from Naukri Scheduler</i>"

        return self.send_message(message)
