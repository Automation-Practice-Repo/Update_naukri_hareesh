#!/usr/bin/env python3
"""
Naukri Automation Scheduler

Reads schedule configuration from config/schedule.yaml and runs
the Naukri update tests at the specified interval.
Sends Telegram notifications with test results and screenshots.
"""
import os
import sys
import time
import subprocess
import logging
import yaml
from datetime import datetime


# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.config_loader import ConfigLoader
from config.telegram_notifier import TelegramNotifier
from config.email_notifier import EmailNotifier


class NaukriScheduler:
    """Scheduler for running Naukri automation tests at regular intervals."""

    def __init__(self, schedule_file="config/schedule.yaml"):
        self.schedule_file = os.path.join(project_root, schedule_file)
        self.config = self._load_schedule_config()
        self.logger = self._setup_logger()
        self.telegram_notifier = TelegramNotifier()
        self.email_notifier = EmailNotifier()
        self.run_count = 0
        self.success_count = 0
        self.failure_count = 0

    def _load_schedule_config(self) -> dict:
        """Load schedule configuration from YAML file."""
        with open(self.schedule_file, "r") as f:
            return yaml.safe_load(f)

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        log_file = os.path.join(
            project_root,
            self.config.get("notifications", {}).get("log_file", "reports/scheduler.log"),
        )
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        logger = logging.getLogger("NaukriScheduler")
        logger.setLevel(logging.INFO)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _get_latest_screenshot(self, status: str) -> str:
        """Find the most recent screenshot for pass or fail."""
        screenshot_dir = os.path.join(project_root, "reports", "screenshots", status)
        if not os.path.exists(screenshot_dir):
            return None

        screenshots = [
            f for f in os.listdir(screenshot_dir)
            if f.endswith(".png")
        ]

        if not screenshots:
            return None

        # Sort by modification time, get most recent
        screenshots.sort(
            key=lambda x: os.path.getmtime(os.path.join(screenshot_dir, x)),
            reverse=True,
        )
        return os.path.join(screenshot_dir, screenshots[0])

    def _run_test(self) -> bool:
        """Run the pytest test and return True if successful."""
        exec_config = self.config.get("execution", {})
        pytest_path = exec_config.get("pytest_path", "./naukri/bin/python -m pytest")
        test_file = exec_config.get("test_file", "tests/test_naukri_update.py")
        pytest_flags = exec_config.get("pytest_flags", "-v --tb=short")
        working_dir = exec_config.get("working_directory", project_root)

        # Parse the pytest path into command parts
        pytest_parts = pytest_path.split()
        command_parts = pytest_parts + test_file.split() + pytest_flags.split()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"[{timestamp}] Executing: {' '.join(command_parts)}")

        try:
            result = subprocess.run(
                command_parts,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            success = result.returncode == 0

            if success:
                self.logger.info("Test execution completed successfully.")
            else:
                self.logger.error(
                    f"Test execution failed with return code {result.returncode}."
                )

            # Log stdout (truncated to avoid excessive logging)
            if result.stdout:
                for line in result.stdout.split("\n"):
                    if line.strip():
                        self.logger.info(f"  {line.strip()}")

            return success

        except subprocess.TimeoutExpired:
            self.logger.error("Test execution timed out (300s limit).")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during test execution: {e}")
            return False

    def _send_notification(self, success: bool) -> None:
        """Send notification with test results via Telegram (primary) and email (fallback)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Determine screenshot path based on result
        screenshot_dir = "pass" if success else "fail"
        screenshot_path = self._get_latest_screenshot(screenshot_dir)

        # Prepare report content
        report_lines = [
            f"Run #{self.run_count}",
            f"Status: {'PASSED' if success else 'FAILED'}",
            f"Timestamp: {timestamp}",
            f"Successes: {self.success_count}",
            f"Failures: {self.failure_count}",
        ]
        report_content = "\n".join(report_lines)

        # Send via Telegram (primary)
        telegram_sent = False
        try:
            telegram_sent = self.telegram_notifier.send_test_result(
                test_name=f"Naukri Update Run #{self.run_count}",
                success=success,
                report_content=report_content,
                screenshot_path=screenshot_path,
            )
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")

        # Fallback to email if Telegram failed or is disabled
        if not telegram_sent:
            try:
                self.email_notifier.send_test_result(
                    test_name=f"Naukri Update Run #{self.run_count}",
                    success=success,
                    report_content=report_content,
                    screenshot_path=screenshot_path,
                )
            except Exception as e:
                self.logger.error(f"Failed to send email notification: {e}")

    def _calculate_delay_until_daily(self, daily_time: str, timezone_str: str) -> int:
        """Calculate seconds until the next daily_time in the given timezone."""
        from datetime import datetime, time, timedelta
        from zoneinfo import ZoneInfo

        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            tz = ZoneInfo("Asia/Kolkata")

        now = datetime.now(tz)
        target_time = time.fromisoformat(daily_time)
        target_dt = datetime.combine(now.date(), target_time, tzinfo=tz)

        # If target time already passed today, schedule for tomorrow
        if target_dt <= now:
            target_dt += timedelta(days=1)

        delay = int((target_dt - now).total_seconds())
        return delay

    def _run_daily_schedule(self) -> None:
        """Run scheduler with daily schedule at specified time."""
        schedule_config = self.config.get("schedule", {})
        daily_time = schedule_config.get("daily_time", "09:00")
        timezone_str = schedule_config.get("timezone", "Asia/Kolkata")
        max_runs = schedule_config.get("max_runs", 0)

        self.logger.info("=" * 60)
        self.logger.info("Naukri Automation Scheduler Started (Daily Mode)")
        self.logger.info(f"Running daily at {daily_time} {timezone_str}.")
        self.logger.info(f"Max runs: {'unlimited' if max_runs == 0 else max_runs}")
        self.logger.info(f"Headless mode: {ConfigLoader.get_headless()}")
        self.logger.info("=" * 60)

        try:
            while True:
                # Calculate delay until next daily run
                delay = self._calculate_delay_until_daily(daily_time, timezone_str)

                self.logger.info(f"Next run scheduled in {delay // 3600}h {(delay % 3600) // 60}m {delay % 60}s")

                if delay > 0:
                    time.sleep(delay)

                # Run the test
                self.run_count += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.logger.info(f"--- Run #{self.run_count} at {timestamp} ---")

                success = self._run_test()

                if success:
                    self.success_count += 1
                    self.logger.info(f"Run #{self.run_count} completed successfully.")
                else:
                    self.failure_count += 1
                    self.logger.warning(f"Run #{self.run_count} failed.")

                # Send notifications
                self._send_notification(success)

                # Check for max runs
                if max_runs > 0 and self.run_count >= max_runs:
                    self.logger.info(f"Reached max_runs ({max_runs}). Stopping scheduler.")
                    self._send_summary_report()
                    break

        except KeyboardInterrupt:
            self.logger.info("\nScheduler stopped by user.")
            self._send_summary_report()
        except Exception as e:
            self.logger.error(f"Scheduler encountered an error: {e}")
            raise

    def run(self) -> None:
        """Main scheduling loop - supports both interval and daily modes."""
        schedule_config = self.config.get("schedule", {})
        schedule_type = schedule_config.get("type", "interval")

        if schedule_type == "daily":
            self._run_daily_schedule()
        else:
            # Original interval-based scheduling
            interval = schedule_config.get("interval_seconds", 120)
            max_runs = schedule_config.get("max_runs", 0)
            initial_delay = schedule_config.get("initial_delay", 0)

            # Wait before first run
            if initial_delay > 0:
                self.logger.info(f"Waiting {initial_delay} seconds before first run...")
                time.sleep(initial_delay)

            self.logger.info("=" * 60)
            self.logger.info("Naukri Automation Scheduler Started (Interval Mode)")
            self.logger.info(f"Running every {interval} seconds.")
            self.logger.info(f"Max runs: {'unlimited' if max_runs == 0 else max_runs}")
            self.logger.info(f"Headless mode: {ConfigLoader.get_headless()}")
            self.logger.info("=" * 60)

            try:
                while True:
                    self.run_count += 1
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.logger.info(f"--- Run #{self.run_count} at {timestamp} ---")

                    success = self._run_test()

                    if success:
                        self.success_count += 1
                        self.logger.info(f"Run #{self.run_count} completed successfully.")
                    else:
                        self.failure_count += 1
                        self.logger.warning(f"Run #{self.run_count} failed.")

                    # Send notifications
                    self._send_notification(success)

                    # Check for max runs
                    if max_runs > 0 and self.run_count >= max_runs:
                        self.logger.info(f"Reached max_runs ({max_runs}). Stopping scheduler.")
                        self._send_summary_report()
                        break

                    self.logger.info(f"Waiting {interval} seconds until next run...")
                    time.sleep(interval)

            except KeyboardInterrupt:
                self.logger.info("\nScheduler stopped by user.")
                self._send_summary_report()
            except Exception as e:
                self.logger.error(f"Scheduler encountered an error: {e}")
                raise

    def _send_summary_report(self) -> None:
        """Send a summary report at shutdown via Telegram (primary) and email (fallback)."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_lines = [
                f"Scheduler Stopped at {timestamp}",
                f"Total runs: {self.run_count}",
                f"Successful runs: {self.success_count}",
                f"Failed runs: {self.failure_count}",
            ]
            report_content = "\n".join(report_lines)

            # Send via Telegram (primary)
            telegram_sent = False
            try:
                telegram_sent = self.telegram_notifier.send_summary_report(
                    run_count=self.run_count,
                    successes=self.success_count,
                    failures=self.failure_count,
                    report_content=report_content,
                )
            except Exception as e:
                self.logger.error(f"Failed to send Telegram summary: {e}")

            # Fallback to email if Telegram failed or is disabled
            if not telegram_sent:
                self.email_notifier.send_summary_report(
                    run_count=self.run_count,
                    successes=self.success_count,
                    failures=self.failure_count,
                    report_content=report_content,
                )
        except Exception as e:
            self.logger.error(f"Failed to send summary report: {e}")


if __name__ == "__main__":
    import sys
    schedule_file = sys.argv[1] if len(sys.argv) > 1 else "config/schedule.yaml"
    scheduler = NaukriScheduler(schedule_file)
    scheduler.run()