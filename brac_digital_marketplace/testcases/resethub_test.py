from dotenv import load_dotenv
import os
import re
from urllib.parse import urlparse

import pytest
import allure
from playwright.sync_api import expect

load_dotenv()

# ERP Procurement staging server (ResetHub username/password: test_resethub_username/test_resethub_password)
proj_url = os.getenv("test_url")
proj_env = os.getenv("test_env")
proj_user = os.getenv("test_user_name")

from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.main_navigation_bar import MainNavigationBar


@allure.suite("ResetHub")
@allure.feature("ERP Procurement Staging")
@allure.story("ResetHub Login")
@allure.title("Test_case_1: ERP Procurement staging login via ResetHub")
@allure.description("Test case 1: Generate the ResetHub link for the ERP Procurement staging server, "
                    "log in with it, open Procurement and log out.")
@pytest.mark.order(1)
def test_1_erp_procurement_staging_login_via_reset_hub(page):
    """
    Test case 1: ERP Procurement staging login via ResetHub.

    Steps:
        1. Generate the ResetHub link for the staging server ('test_env') and user ('test_user_name').
        2. Verify the link points to the staging server ('test_url').
        3. Open the link and verify the ERP dashboard is shown.
        4. Go to Procurement and verify the Procurement dashboard is shown.
        5. Exit and log out from ERP.
    """
    required_env_values = {
        "test_url": proj_url,
        "test_env": proj_env,
        "test_user_name": proj_user,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    reset_page = ResetHubPage(page)
    proc_dashboard_page = DashboardPage(page)
    server_host = urlparse(proj_url).netloc

    # Step 1: Generate the ResetHub link
    with allure.step(f"Step 1: Generate ResetHub link for env '{proj_env}' and user {proj_user}"):
        link = reset_page.generate_reset_link(env=proj_env, username=proj_user)
        print("Generated Link:", link)
        allure.attach(f"Environment: {proj_env}\nUser: {proj_user}\nLink: {link}",
                      name="ResetHub link", attachment_type=allure.attachment_type.TEXT)

    # Step 2: The link points to the staging server
    with allure.step(f"Step 2: Verify the link points to {server_host}"):
        assert link.startswith("http"), f"ResetHub link is not a URL: {link}"
        assert urlparse(link).netloc == server_host, \
            f"ResetHub link is not for {server_host}: {link}"

    # Step 3: Open the link and verify the ERP dashboard
    with allure.step("Step 3: Open the ResetHub link and verify the ERP dashboard"):
        reset_page.open_generated_link(link)
        expect(page).to_have_url(re.compile(re.escape(server_host)), timeout=30000)
        expect(proc_dashboard_page.myDashboardItem_procurement.first).to_be_visible(timeout=30000)
        proc_dashboard_page.get_full_page_screenshot('resethub_staging_erp_dashboard')

    # Step 4: Procurement dashboard
    with allure.step("Step 4: Go to Procurement and verify the Procurement dashboard"):
        proc_dashboard_page.goto_procurement()
        expect(page).to_have_url(re.compile("procurementDashboard"), timeout=30000)
        proc_dashboard_page.get_full_page_screenshot('resethub_staging_procurement_dashboard')
        print(f"Logged in to ERP Procurement staging as {proj_user}: {page.url}")

    # Step 5: Exit and log out
    with allure.step("Step 5: Exit and log out from ERP"):
        m_page = MainNavigationBar(page)
        m_page.exit()
        m_page.logout()
        m_page.get_full_page_screenshot('resethub_staging_logout')
