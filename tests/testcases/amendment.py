import pytest
from dotenv import load_dotenv
import os
import re
import random
import string
from conftest import new_tab
from datetime import datetime, timedelta

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

# Procurement global variable
agreement_approver = ''
agreement_reviewer = ''


# approver_id_2 = ''
# order_vendor = ''
# # order_approver = ''
# approver_id_3 = ''
# @pytest.mark.reporting(
#     functional_specification="amendment",
#     test_description="Framework agreement amendment"
# )
def test_1_search_whitelisted_agreement_on_procurement_module(page, new_tab):
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=agreement_officer,
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
    framework_list.get_full_page_screenshot('2. Framework officer go to the framework agreement list')
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.get_full_page_screenshot('3. Framework officer searches the framework agreement number')


def test_2_get_whitelisted_agreement_information(page, new_tab):
    framework_list = FrameworkList(page)
    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_list.get_full_page_screenshot('4. Framework officer views the framework agreement details')

    framework_info = FrameworkInformation(new_page)
    framework_info.get_vendor_info()
    framework_info.print_agreement_date()
    framework_info.print_price_review_date()
    framework_info.print_from_date()
    framework_info.print_to_date()
    framework_info.print_framework_item_details()
    # framework_info.print_item_details_2()
    framework_info.go_to_framework_list()
    new_page.close()


def test_3_whitelisted_agreement_amendment_identify_reviewer_information(page, new_tab):
    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    new_page = new_tab(lambda p: framework_list.fa_no_link.click())

    framework_info = FrameworkInformation(new_page)
    framework_info.enter_amendment_comments(amendment_comments=amendment_remarks)
    framework_info.confirm_agreement_amendment()
    new_page.close()

    framework_list.search_agreement(search_framework_agreement=agreement_number)
    global agreement_reviewer
    agreement_reviewer = str(int(framework_list.get_status_info()))
    print("Agreement Reviewer ID:", agreement_reviewer)

    # global agreement_approver
    # agreement_approver = str(int(framework_list.get_status_info()))
    # print("Agreement approver ID:", agreement_approver)

    # m_page = MainNavigationBar(page)
    # m_page.exit()
    # m_page.logout()
    # # m_page.get_full_page_screenshot('full_page_screenshot_7')
    # m_page.wait_for_timeout(2000)


def test_4_agreement_reviewer_review_amended_agreement(page, new_tab):
    framework_list = FrameworkList(page)
    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_info = FrameworkInformation(new_page)
    framework_info.enter_edit_comments(edit_comments=edit_remarks)
    framework_info.edit_button.click()
    framework_info.wait_for_timeout(2000)

    framework_agreement_information = FrameworkAgreementInformation(new_page)
    framework_agreement_information.select_start_date()
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.select_end_date()
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.select_price_review_date()
    framework_agreement_information.wait_for_timeout(2000)

    current_dir = os.getcwd()
    document_location = os.path.join(current_dir, 'utils', 'upload_file.pdf')
    framework_agreement_information.upload_framework_document(document_location)
    framework_agreement_information.applicable_for_both.click()
    framework_agreement_information.enter_remarks(remarks=agreement_remarks)
    framework_agreement_information.print_item_details()
    # framework_agreement_information.print_table_data()
    # framework_agreement_information.print_table_data(only_status=True)
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.modify_item_unit_price(unit_price="50")
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.update_and_next_button.click()
