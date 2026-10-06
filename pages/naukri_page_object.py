"""
Naukri Page Object Model (POM) for Naukri.com
Encapsulates all page interactions and locators.
"""
import os
import sys

from playwright.sync_api import Playwright, expect

# Ensure config can be imported
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from config.config_loader import ConfigLoader


class NaukriPage:
    """Page Object for Naukri.com login and profile update flows."""

    # Locators loaded from YAML
    LOCATORS = {
        "login_link": "login_link",
        "naukri_home_link": "naukri_home_link",
        "login_button": "login_button",
        "open_profile_menu_button": "open_profile_menu_button",
        "view_update_profile_link": "view_update_profile_link",
        "profile_summary_heading": "profile_summary_heading",
        "edit_profile_summary_button": "edit_profile_summary_button",
        "save_button": "save_button",
        "profile_updated_success_message": "profile_updated_success_message",
        "email_input": "email_input",
        "password_input": "password_input",
    }

    def __init__(self, playwright: Playwright):
        self.playwright = playwright
        self.locators = self.LOCATORS
        self.config = ConfigLoader.load()
        headless = ConfigLoader.get_headless()

        # Launch browser with stealth settings to avoid bot detection
        self.browser = playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Create context with realistic settings
        self.context = self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            permissions=["geolocation"],
        )

        # Add stealth script to hide automation indicators
        self.context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-IN', 'en'],
            });
            window.chrome = {
                runtime: {},
                app: {},
                loadTimes: function() {},
                csi: function() {},
            };
            """
        )

        self.page = self.context.new_page()

    def click_element(self, locator_key: str) -> None:
        """Click an element based on locator key."""
        locator = self._get_locator(locator_key)
        self.page.wait_for_selector(locator["selector"])
        self.page.locator(locator["selector"]).click()

    def fill_element(self, locator_key: str, value: str) -> None:
        """Fill an element based on locator key."""
        locator = self._get_locator(locator_key)
        self.page.wait_for_selector(locator["selector"])
        self.page.locator(locator["selector"]).fill(value)

    def _get_locator(self, key: str) -> dict:
        """Get locator definition from YAML config."""
        from playwright.sync_api import Playwright
        import yaml

        yaml_path = os.path.join(os.path.dirname(__file__), "naukri_locations.yaml")
        with open(yaml_path, "r") as f:
            self._yaml_locators = yaml.safe_load(f)

        return self._yaml_locators.get(key, {})

    # --- Navigation ---

    def navigate_to_home(self) -> None:
        """Navigate to Naukri homepage."""
        url = ConfigLoader.get_url()
        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")

    def click_login_link(self) -> None:
        """Click the Login link on the Naukri homepage."""
        self.page.get_by_role("link", name="Login").click()

    def click_login_button(self) -> None:
        """Click the Login button on the login form."""
        self.page.get_by_role("button", name="Login", exact=True).click()

    def click_open_profile_menu(self) -> None:
        """Click the Open profile menu button."""
        self.page.get_by_role("button", name="Open profile menu").click()

    def click_view_update_profile(self) -> None:
        """Click the View & Update Profile link."""
        self.page.get_by_role("link", name="View & Update Profile").click()

    def click_profile_summary_heading(self) -> None:
        """Click the Profile Summary heading button."""
        self.page.get_by_role("button", name="Profile summary").click()

    def click_edit_profile_summary_button(self) -> None:
        """Click the Edit Profile Summary button."""
        self.page.get_by_role("button", name="Edit profile summary").click()

    # --- Form Interactions ---

    def fill_email(self, email: str) -> None:
        """Fill the Email ID / Username textbox."""
        self.page.get_by_role("textbox", name="Email ID / Username").fill(email)

    def fill_password(self, password: str) -> None:
        """Fill the Password textbox."""
        self.page.get_by_role("textbox", name="Password").fill(password)

    # --- Button Actions ---

    def click_save(self) -> None:
        """Click the Save button."""
        self.page.get_by_role("button", name="Save").click()

    # --- Assertions ---

    def assert_login_link_visible(self) -> None:
        """Assert that the Login link is visible."""
        expect(self.page.get_by_role("link", name="Login")).to_be_visible()

    def assert_naukri_home_visible(self) -> None:
        """Assert that the Naukri.com home link is visible."""
        expect(self.page.get_by_role("link", name="Naukri.com").first).to_be_visible()

    def assert_profile_summary_visible(self) -> None:
        """Assert that the Profile summary heading is visible."""
        expect(self.page.get_by_role("heading", name="Profile summary")).to_be_visible()

    def assert_save_button_visible(self) -> None:
        """Assert that the Save button is visible."""
        expect(self.page.get_by_role("button", name="Save")).to_be_visible()

    def assert_profile_updated_success(self) -> None:
        """Assert that the profile update success message is visible."""
        expect(self.page.get_by_text("Profile updated successfully")).to_be_visible()

    # --- Screenshot Helpers ---

    def take_screenshot(self, filename: str = "screenshot.png", full_page: bool = True) -> None:
        """Take a screenshot of the current page."""
        self.page.screenshot(path=filename, full_page=full_page)

    def take_screenshot_on_pass(self, test_name: str = "test") -> None:
        """Take a screenshot on test pass."""
        screenshot_dir = os.path.join(os.getcwd(), "reports", "screenshots", "pass")
        os.makedirs(screenshot_dir, exist_ok=True)
        self.take_screenshot(
            filename=os.path.join(screenshot_dir, f"{test_name}_pass.png"),
            full_page=True,
        )

    def take_screenshot_on_fail(self, test_name: str = "test") -> None:
        """Take a screenshot on test failure."""
        screenshot_dir = os.path.join(os.getcwd(), "reports", "screenshots", "fail")
        os.makedirs(screenshot_dir, exist_ok=True)
        self.take_screenshot(
            filename=os.path.join(screenshot_dir, f"{test_name}_fail.png"),
            full_page=True,
        )

    # --- Error Handling ---

    def assert_no_error(self, message: str = "Test failed") -> None:
        """Assert that no unexpected errors occurred."""
        error_elements = self.page.query_selector_all(".error, .alert, .invalid")
        if error_elements:
            raise AssertionError(f"Unexpected error elements found: {[el.name for el in error_elements]}")
        else:
            print(f"[PASS] No error elements detected ({len(error_elements)} found)")

    def assert_test_complete(self) -> bool:
        """Run all assertions and return True if all pass."""
        try:
            self.assert_login_link_visible()
            self.assert_naukri_home_visible()
            self.assert_profile_summary_visible()
            self.assert_save_button_visible()
            self.assert_profile_updated_success()
            return True
        except AssertionError as e:
            print(f"[FAIL] Test assertion failed: {e}")
            return False

    # --- Cleanup ---

    def close(self) -> None:
        """Clean up browser and context resources."""
        if hasattr(self, "context") and self.context:
            self.context.close()
        if hasattr(self, "browser") and self.browser:
            self.browser.close()
