from dotenv import load_dotenv
import os
import re
from urllib.parse import urlparse

import pytest
import allure
from playwright.sync_api import expect

load_dotenv()

# ERP Procurement QA server (ResetHub username/password: test_resethub_username/test_resethub_password)
qa_url = os.getenv("test_qa_url")
qa_env = os.getenv("test_qa_env")
qa_user = os.getenv("test_qa_user_name")

from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.main_navigation_bar import MainNavigationBar


@allure.suite("ResetHub")
@allure.feature("ERP Procurement QA")
@allure.story("ResetHub Login")
@allure.title("Test_case_1: ERP Procurement QA login via ResetHub")
@allure.description("Test case 1: Generate the ResetHub link for the ERP Procurement QA server, "
                    "log in with it, open Procurement and log out.")
@pytest.mark.order(1)
def test_1_erp_procurement_qa_login_via_resethub(page):
    """
    Test case 1: ERP Procurement QA login via ResetHub.

    Steps:
        1. Generate the ResetHub link for the QA server ('test_qa_env') and user ('test_qa_user_name').
        2. Verify the link points to the QA server ('test_qa_url').
        3. Open the link and verify the ERP dashboard is shown.
        4. Go to Procurement and verify the Procurement dashboard is shown.
        5. Exit and log out from ERP.
    """
    required_env_values = {
        "test_qa_url": qa_url,
        "test_qa_env": qa_env,
        "test_qa_user_name": qa_user,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    reset_page = ResetHubPage(page)
    proc_dashboard_page = DashboardPage(page)
    server_host = urlparse(qa_url).netloc

    # Step 1: Generate the ResetHub link
    with allure.step(f"Step 1: Generate ResetHub link for env '{qa_env}' and user {qa_user}"):
        link = reset_page.generate_reset_link(env=qa_env, username=qa_user)
        print("Generated Link:", link)
        allure.attach(f"Environment: {qa_env}\nUser: {qa_user}\nLink: {link}",
                      name="ResetHub link", attachment_type=allure.attachment_type.TEXT)

    # Step 2: The link points to the QA server
    with allure.step(f"Step 2: Verify the link points to {server_host}"):
        assert link.startswith("http"), f"ResetHub link is not a URL: {link}"
        assert urlparse(link).netloc == server_host, \
            f"ResetHub link is not for {server_host}: {link}"

    # Step 3: Open the link and verify the ERP dashboard
    with allure.step("Step 3: Open the ResetHub link and verify the ERP dashboard"):
        reset_page.open_generated_link(link)
        expect(page).to_have_url(re.compile(re.escape(server_host)), timeout=30000)
        expect(proc_dashboard_page.myDashboardItem_procurement.first).to_be_visible(timeout=30000)
        proc_dashboard_page.get_full_page_screenshot('resethub_qa_erp_dashboard')

    # Step 4: Procurement dashboard
    with allure.step("Step 4: Go to Procurement and verify the Procurement dashboard"):
        proc_dashboard_page.goto_procurement()
        expect(page).to_have_url(re.compile("procurementDashboard"), timeout=30000)
        proc_dashboard_page.get_full_page_screenshot('resethub_qa_procurement_dashboard')
        print(f"Logged in to ERP Procurement QA as {qa_user}: {page.url}")

    # Step 5: Exit and log out
    with allure.step("Step 5: Exit and log out from ERP"):
        m_page = MainNavigationBar(page)
        m_page.exit()
        m_page.logout()
        m_page.get_full_page_screenshot('resethub_qa_logout')
