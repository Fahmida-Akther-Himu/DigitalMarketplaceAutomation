from dotenv import load_dotenv
import re
import random
import string
from conftest import new_tab
from datetime import datetime, timedelta
import os

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

# challan_num_for_receiver = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
# challan_num_for_order_initiator = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
# challan_num_for_order_initiator_2 = ''.join(random.choices(string.ascii_letters, k=8))

# Procurement global variable
agreement_approver = ''
agreement_reviewer = ''

approver_id_2 = ''
order_vendor = ''
# order_approver = ''
approver_id_3 = ''


def test_1_search_whitelisted_agreement_on_procurement_module(page, new_tab):
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=agreement_officer,
        pass_word=proj_pass
        # timeout=60000
    )

    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()
    proc_dashboard_page.get_full_page_screenshot('1. Framework officer enters procurement module')

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.goto_framework_agreement_list()
    print("Test 1: Framework agreement search")

    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    # framework_list.get_status_info()

    global agreement_reviewer
    agreement_reviewer = str(int(framework_list.get_status_info()))
    print("Agreement Reviewer ID:", agreement_reviewer)

    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_info = FrameworkInformation(new_page)
    framework_info.agreement_date.click()
    framework_info.wait_for_timeout(5000)

    # framework_agreement_information = FrameworkAgreementInformation(new_page)
    # framework_agreement_information.select_start_date()
    # framework_agreement_information.select_end_date()
    # framework_agreement_information.select_price_review_date()
    # framework_agreement_information.upload_framework_document(
    #     '')

    # global agreement_approver
    # agreement_approver=framework_list.find_agreement_approver_id()
    # agreement_approver = framework_list.find_agreement_approver_id()
    # print("DEBUG returned approver value:", agreement_approver)
    # framework_list.find_agreement_approver_id_1()

    # agreement_approver = str(int(framework_list.find_agreement_approver_id()))
    # print("Agreement approver ID:", agreement_approver)

    # new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    # framework_info = FrameworkInformation(new_page)
    # framework_info.enter_edit_comments(edit_comments=edit_remarks)
    # framework_info.edit_button.click()
    # framework_info.wait_for_timeout(2000)
    #
    # framework_agreement_information = FrameworkAgreementInformation(new_page)
    # framework_agreement_information.select_start_date()
    # framework_agreement_information.select_end_date()
    # framework_agreement_information.select_price_review_date()
    # # framework_agreement_information.upload_framework_document(
    # #     '')
    # current_dir = os.getcwd()
    # # print(f"Current directory: {current_dir}")
    # upload_document_location = os.path.join(current_dir, 'utils', 'upload_file.pdf')
    # framework_agreement_information.upload_framework_document(upload_document_location)
    # framework_agreement_information.wait_for_timeout(2000)
    #
    # current_dir = os.getcwd()
    # # print(f"Current directory: {current_dir}")
    # excel_document_location = os.path.join(current_dir, 'utils', 'Excel_file.excel')
    # framework_agreement_information.upload_excel_document(excel_document_location)
    # framework_agreement_information.applicable_for_both.click()
    # framework_agreement_information.enter_remarks(remarks=agreement_remarks)
    # framework_agreement_information.wait_for_timeout(5000)
    # proc_login_page = ProcurementLoginPage(page)
    # proc_login_page.perform_logout()

    # m_page = MainNavigationBar(page)
    # m_page.exit()
    # m_page.logout()
    # # m_page.get_full_page_screenshot('full_page_screenshot_7')
    # m_page.wait_for_timeout(2000)
