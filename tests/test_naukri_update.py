"""
Naukri Update Test Suite
Professional Page Object Model (POM) implementation.

Locators are defined in pages/naukri_locations.yaml
Configuration is defined in config/config.yaml
"""
import os
import sys

import pytest

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from pages.naukri_page_object import NaukriPage
from config.config_loader import ConfigLoader


# =============================================================================
# Test Cases
# =============================================================================

def test_login_and_profile_update(pytest_config=None) -> None:
    """
    Test the complete Naukri login and profile update flow.
    
    Steps:
    1. Navigate to Naukri homepage
    2. Click Login
    3. Fill Email ID / Username
    4. Fill Password
    5. Click Login
    6. Open profile menu
    7. Click View & Update Profile
    8. Click Profile Summary
    9. Click Edit Profile Summary
    10. Click Save
    11. Verify profile updated successfully
    """
    from playwright.sync_api import sync_playwright

    # Load configuration
    config = ConfigLoader.load()
    base_url = ConfigLoader.get_url()
    username = ConfigLoader.get_username()
    password = ConfigLoader.get_password()

    # Initialize page object with playwright instance
    with sync_playwright() as playwright:
        page = NaukriPage(playwright)
        
        try:
            # Step 1: Navigate to homepage
            page.navigate_to_home()
            
            # Step 2: Verify Login link is visible
            page.assert_login_link_visible()
            
            # Step 3: Click Login link on homepage
            page.click_login_link()
            
            # Step 4: Fill email and password from config
            page.fill_email(username)
            page.fill_password(password)
            
            # Step 5: Click Login button on form
            page.click_login_button()
            
            # Step 6: Open profile menu
            page.click_open_profile_menu()
            
            # Step 7: Click View & Update Profile
            page.click_view_update_profile()
            
            # Step 8: Click Profile Summary
            page.click_profile_summary_heading()
            
            # Step 9: Click Edit Profile Summary
            page.click_edit_profile_summary_button()
            
            # Step 10: Click Save
            page.click_save()
            
            # Step 11: Verify success message
            page.assert_profile_updated_success()
            
            # Take screenshot on pass
            page.take_screenshot_on_pass("test_login_and_profile_update")
            
            # All assertions passed
            print("[PASS] Naukri login and profile update test completed successfully")
            
        except AssertionError as e:
            print(f"[FAIL] Test assertion failed: {e}")
            # Take screenshot on fail
            page.take_screenshot_on_fail("test_login_and_profile_update")
            raise
        except Exception as e:
            print(f"[ERROR] Unexpected error during test: {e}")
            # Take screenshot on error
            page.take_screenshot_on_fail("test_login_and_profile_update")
            raise
        finally:
            # Cleanup - close browser
            page.close()

