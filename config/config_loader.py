"""
Configuration loader for Naukri tests.
Reads settings from config/config.yaml and environment variables.
Environment variables override YAML config for security.
"""
import os
import sys

import yaml


class ConfigLoader:
    """Load and manage test configuration from YAML and environment variables."""

    _config = None
    _config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "config.yaml",
    )

    @classmethod
    def load(cls) -> dict:
        """Load configuration from YAML file."""
        if cls._config is None:
            # Load environment variables first
            cls._load_env()
            
            # Load YAML config as fallback/default
            if os.path.exists(cls._config_path):
                with open(cls._config_path, "r") as f:
                    cls._config = yaml.safe_load(f)
            else:
                cls._config = {}
        return cls._config

    @classmethod
    def _load_env(cls) -> None:
        """Load environment variables from .env file."""
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env",
        )
        
        # Load .env file if it exists
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())

    @classmethod
    def get(cls, *keys, default=None):
        """Get a nested configuration value from YAML."""
        config = cls.load()
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                return default
        return config

    @classmethod
    def get_url(cls) -> str:
        """Get the Naukri URL from env or config."""
        return os.environ.get("NAUKRI_URL") or cls.get("naukri", "url", default="https://www.naukri.com/")

    @classmethod
    def get_username(cls) -> str:
        """Get the username from env or config."""
        return os.environ.get("NAUKRI_USERNAME") or cls.get("naukri", "username", default="")

    @classmethod
    def get_password(cls) -> str:
        """Get the password from env or config."""
        return os.environ.get("NAUKRI_PASSWORD") or cls.get("naukri", "password", default="")

    @classmethod
    def get_headless(cls) -> bool:
        """Get the headless browser setting from env or config."""
        env_headless = os.environ.get("HEADLESS", "").lower()
        if env_headless in ("true", "1", "yes"):
            return True
        if env_headless in ("false", "0", "no"):
            return False
        return cls.get("test", "headless", default=False)

    @classmethod
    def get_timeout(cls) -> int:
        """Get the timeout value from config."""
        env_timeout = os.environ.get("TIMEOUT")
        if env_timeout:
            return int(env_timeout)
        return cls.get("test", "timeout", default=30000)

    @classmethod
    def get_screenshot_dir(cls) -> str:
        """Get the screenshots directory."""
        return cls.get("screenshots", "directory", default="reports/screenshots")

    @classmethod
    def should_screenshot_on_pass(cls) -> bool:
        """Whether to take screenshots on pass."""
        return cls.get("screenshots", "on_pass", default=True)

    @classmethod
    def should_screenshot_on_fail(cls) -> bool:
        """Whether to take screenshots on fail."""
        return cls.get("screenshots", "on_fail", default=True)
