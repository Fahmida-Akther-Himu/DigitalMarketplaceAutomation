from dotenv import load_dotenv
import re
import random
import string
from conftest import new_tab
# from conftest_1 import new_tab
# from datetime import datetime, timedelta
import os
from datetime import datetime
import pytest

load_dotenv()

# Project URLs
proj_url = os.getenv("test_url")
requisition_list_url = proj_url + "/procurementDashboard/myDashboard#!/requisition/list"

# Procurement information
proj_user = os.getenv("test_user_name")
proj_pass = os.getenv("test_user_pass")

agreement_officer = os.getenv("test_agreement_officer")
agreement_number = os.getenv("test_agreement_number")

agreement = os.getenv("test_white_listed_agreement")
proc_admin = os.getenv("test_proc_admin")
amended_agreement_recommender = os.getenv("test_amended_agreement_recommender")
amended_agreement_approver = os.getenv("test_amended_agreement_approver")
# order_reference_number = os.getenv("test_order_reference_number")

# Page models for procurement
from pages.digital_marketplace.procurement_login_page import ProcurementLoginPage
from pages.digital_marketplace.dashboard_page import DashboardPage
from pages.digital_marketplace.procurement_home_page import ProcurementHomePage
from pages.digital_marketplace.main_navigation_bar import MainNavigationBar
from pages.digital_marketplace.framework_information import FrameworkInformation
from pages.digital_marketplace.framework_order_list import FrameworkOrderListPage
from pages.digital_marketplace.framework_list import FrameworkList
from pages.digital_marketplace.framework_agreement_information import FrameworkAgreementInformation
from datetime import datetime
# For validation
from playwright.sync_api import expect

# Import for beautiful reporting
from rich.traceback import install

install()
# Procurement global variable
allowed_chars = string.ascii_letters + string.digits + ' '
amendment_remarks = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
edit_remarks = ''.join(random.choices(string.ascii_letters + string.digits + string.ascii_letters, k=15))
agreement_remarks = ''.join(random.choices(allowed_chars, k=20))
approval_remarks = ''.join(random.choices(allowed_chars, k=20))

# Procurement global variable
agreement_reviewer = ''
agreement_recommender = ''
agreement_approver = ''


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="Verify that agreement amendment_1")
def test_2_reviewer_approves_amended_agreement_1(page, new_tab):
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name="175050",
        pass_word=proj_pass,
        timeout=60000
    )

    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()
    proc_dashboard_page.get_full_page_screenshot('1. Framework officer enters procurement module')

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.goto_framework_agreement_list()
    print("Test 1: Framework agreement search")

    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)

    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_info = FrameworkInformation(new_page)
    framework_info.enter_agreement_comments(comments=approval_remarks)
    framework_info.confirm_agreement_approval()
    new_page.close()

    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.get_status_info()

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.wait_for_timeout(2000)
