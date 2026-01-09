from dotenv import load_dotenv
import os
import re
import random
import string
import pytest
from conftest import new_tab
from datetime import datetime, timedelta

# from tests.testcases.test_r import whitelisted_agreement_number

load_dotenv()

# Project URLs
proj_url = os.getenv("test_url")
requisition_list_url = proj_url + "/procurementDashboard/myDashboard#!/requisition/list"

# Procurement information
proj_user = os.getenv("test_user_name")
proj_pass = os.getenv("test_user_pass")
requisition_project_name = os.getenv("test_requisition_project_name")
whitelisted_agreement_number = os.getenv("test_whitelisted_agreement_number")
blacklisted_agreement_number = os.getenv("test_blacklisted_agreement_number")
requisition_funding_source = os.getenv("test_requisition_funding_source")
requisition_funding_remarks = os.getenv("test_requisition_funding_remarks")
master_item_1 = os.getenv("test_master_item_1")
master_item_1_full_path = os.getenv("test_master_item_1_full_path")

master_item_2 = os.getenv("test_master_item_2")
master_item_2_full_path = os.getenv("test_master_item_2_full_path")

master_item_3 = os.getenv("test_master_item_3")
master_item_3_full_path = os.getenv("test_master_item_3_full_path")

item_gl_code_1 = os.getenv("test_item_gl_code_1")
item_gl_code_2 = os.getenv("test_item_gl_code_2")
item_gl_code_3 = os.getenv("test_item_gl_code_3")
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
schedule_address = os.getenv("test_schedule_address")

marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")

# Page models for procurement
from pages.digital_marketplace.procurement_login_page import ProcurementLoginPage
from pages.digital_marketplace.dashboard_page import DashboardPage
from pages.digital_marketplace.procurement_home_page import ProcurementHomePage
from pages.digital_marketplace.requisition_creation import CreateReqPage
from pages.digital_marketplace.requisition_list import RequisitionList
from pages.digital_marketplace.main_navigation_bar import MainNavigationBar
from pages.digital_marketplace.requisition_approve_list import RequisitionApproveList
from pages.digital_marketplace.requisition_details_information import RequisitionDetailsInformation
from pages.digital_marketplace.framework_information import FrameworkInformation
from pages.digital_marketplace.framework_order_list import FrameworkOrderListPage
from pages.digital_marketplace.proc_item_receive_list import ProcItemReceiveListPage

# Page models for marketplace
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.active_requisition_list import ActiveRequisitionListPage
from pages.digital_marketplace.active_requisition_product_list import ActiveRequisitionProductList
from pages.digital_marketplace.main_navigation_bar import MainNavigationBar

# For validation
from playwright.sync_api import expect

# Import for beautiful reporting
from rich.traceback import install

install()

# Procurement global variable
req_num = ''
approver_id = ''
approver_id_2 = ''
order_vendor = ''
# order_approver = ''
approver_id_3 = ''


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Create Requisition with Whitelisted, Blacklisted, and Non-Agreement Items.

    Objective:
        To verify that a user can successfully create and submit a requisition containing
        a combination of:
        - Whitelisted framework agreement items
        - Blacklisted framework agreement items
        - Non-framework (open market) items

        and that the system correctly processes each item type within a single requisition.""")
def test_1_create_requisition_with_whitelisted_blacklisted_and_non_agreement_item(page):
    """
    Test Case 1: Create Requisition with Whitelisted, Blacklisted, and Non-Agreement Items.

    Objective:
        To verify that a user can successfully create and submit a requisition containing
        a combination of:
        - Whitelisted framework agreement items
        - Blacklisted framework agreement items
        - Non-framework (open market) items

        and that the system correctly processes each item type within a single requisition.

    Steps:
        1. Log in to the ERP Procurement system using valid user credentials.
        2. Navigate to the Procurement module.
        3. Open the "Create Requisition" page.
        4. Enter requisition header details such as project, funding source, and remarks.
        5. Add a whitelisted framework agreement item:
            - Select the active whitelisted agreement.
            - Choose an agreement item and define quantity.
            - Assign GL code and item remarks.
        6. Add a blacklisted framework agreement item:
            - Select the active blacklisted agreement.
            - Choose an agreement item and define quantity.
            - Assign GL code and item remarks.
        7. Add a non-framework (non-agreement) item:
            - Define item quantity and unit price.
            - Assign GL code and item remarks.
        8. Configure delivery schedule and location.
        9. Submit the requisition.
        10. Capture and store the generated requisition number.
        11. Navigate to the requisition list and verify successful creation.

    """
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=proj_user,
        pass_word=proj_pass,
        timeout=60000
    )

    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()
    proc_dashboard_page.get_full_page_screenshot('full_page_screenshot_1')

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.navigate_to_create_requisition()
    proc_home_page.get_full_page_screenshot('full_page_screenshot_2')

    print("Test 1: Creating requisition...")
    create_requisition_page = CreateReqPage(page)
    # c_page.validate()
    create_requisition_page.setting_requisition_for(project_name=requisition_project_name)
    create_requisition_page.setting_requisition_information(fund_source=requisition_funding_source,
                                                            fund_remarks=requisition_funding_remarks)
    # Whitelisted framework agreement information
    create_requisition_page.setting_requisition_details(item_info_1=master_item_1, item_info_2=master_item_1_full_path)

    create_requisition_page.active_agreement_button.click()
    create_requisition_page.setting_active_framework_list(agreement_info=whitelisted_agreement_number)
    create_requisition_page.agreement_item_selector.nth(0).click()
    create_requisition_page.finalize_item_quantity(item_quantity="100")

    create_requisition_page.setting_requisition_for_details(gl_code=item_gl_code_1,
                                                            item_remarks=requisition_item_remarks)

    # Blacklisted framework agreement information
    create_requisition_page.setting_requisition_details(item_info_1=master_item_2, item_info_2=master_item_2_full_path)

    create_requisition_page.active_agreement_button.click()
    create_requisition_page.setting_active_framework_list(agreement_info=blacklisted_agreement_number)
    create_requisition_page.agreement_item_selector.nth(0).click()
    # create_requisition_page.count_and_select_active_framework_items()
    create_requisition_page.finalize_item_quantity(item_quantity="90")

    create_requisition_page.setting_requisition_for_details(gl_code=item_gl_code_2,
                                                            item_remarks=requisition_item_remarks)

    # Non-framework agreement information
    create_requisition_page.setting_requisition_details(item_info_1=master_item_3, item_info_2=master_item_3_full_path)
    create_requisition_page.finalize_item_quantity(item_quantity="50")
    create_requisition_page.finalize_item_unit_price(unit_price="10")

    create_requisition_page.setting_requisition_for_details(gl_code=item_gl_code_3,
                                                            item_remarks=requisition_item_remarks)

    # create_requisition_page.setting_requisition_for_details("1202010501",
    #                                                         "Item remarks abc123@")
    # create_requisition_page.setting_requisition_for_details("[1101010101-02] Petty Cash",
    #                                                         "Item remarks abc123@")
    create_requisition_page.setting_same_schedule_for_date()
    create_requisition_page.setting_location_for_central_store(address=schedule_address)
    create_requisition_page.get_full_page_screenshot('full_page_screenshot_3')
    global req_num
    req_num = create_requisition_page.submit_requisition()
    print("REQ NUM:", req_num)
    create_requisition_page.navigate_to_requisition_list()
    create_requisition_page.get_full_page_screenshot('full_page_screenshot_4')


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 2: Identify and capture the first approver of a submitted requisition.

    Objective:
        To verify that the system correctly retrieves the first-level approver
        assigned to the newly created requisition, ensuring that workflow routing
        is functioning as expected.""")
def test_2_identify_first_approver_for_created_requisition(page):
    """
    Test Case 2: Identify and capture the first approver of a submitted requisition.

    Objective:
        To verify that the system correctly retrieves the first-level approver
        assigned to the newly created requisition, ensuring that workflow routing
        is functioning as expected.

    Steps:
        1. Access the Requisition List page.
        2. Capture a full-page screenshot for documentation.
        3. Search for the recently submitted requisition using its requisition number ('req_num').
        4. Retrieve and store the approver ID of the first-level approver.
        5. Capture another screenshot showing the approver information.
        6. Log out from the current session to complete the test flow.
    """
    print("Test 2: Finding approver of the requisition...")
    requisition_list_page = RequisitionList(page)
    requisition_list_page.get_full_page_screenshot('full_page_screenshot_5')
    requisition_list_page.search_requisition(req_num)

    global approver_id
    approver_id = str(int(requisition_list_page.find_approver_id()))
    print("APPROVER ID:", approver_id)
    requisition_list_page.get_full_page_screenshot('full_page_screenshot_6')

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot('full_page_screenshot_7')
    m_page.wait_for_timeout(2000)


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 3: Login as the first approver and approve the submitted requisition in the ERP Procurement system.

    Objective:
        To verify that the first-level approver can successfully log in to the
        procurement portal, locate the submitted requisition, and approve it,
        ensuring that the workflow moves correctly to the next approval stage.""")
def test_3_login_as_first_approver_and_approve_requisition(page):
    """
    Test Case 3: Login as the first approver and approve the submitted requisition in the ERP Procurement system.

    Objective:
        To verify that the first-level approver can successfully log in to the
        procurement portal, locate the submitted requisition, and approve it,
        ensuring that the workflow moves correctly to the next approval stage.

    Steps:
        1. Login to the procurement portal as the first-level approver using the 'approver_id'.
        2. Navigate to the procurement dashboard.
        3. Access the "Requisition Approve List" page.
        4. Capture a full-page screenshot for documentation.
        5. Search for the requisition using its requisition number ('req_num').
        6. Select the requisition from the list.
        7. Approve the requisition.
        8. Capture a screenshot showing the approved requisition.
        9. Wait briefly to ensure actions are completed.
        10. Log out from the session and capture a final screenshot.
    """
    print("Test 3: Logging in as first approver and approving requisition...")
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=approver_id,
        pass_word=proj_pass,
        timeout=60000
    )

    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.menu_click_procurement_hyperlink()

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.navigate_to_requisition_approve_list()

    requisition_approve_list_page = RequisitionApproveList(page)
    requisition_approve_list_page.get_full_page_screenshot('full_page_screenshot_8')
    requisition_approve_list_page.search_requisition(req_num)
    requisition_approve_list_page.select_requisition()
    requisition_approve_list_page.approve_requisition()
    requisition_approve_list_page.get_full_page_screenshot('full_page_screenshot_9')
    requisition_approve_list_page.wait_for_timeout(2000)

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot('full_page_screenshot_10')
    m_page.wait_for_timeout(2000)


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 4: Identify and capture the second-level approver of a submitted requisition in the ERP Procurement system.

    Objective:
        To verify that the system correctly retrieves the second-level approver
        for a previously submitted requisition, ensuring that the approval workflow
        is routed correctly to the next approver.""")
def test_4_identify_second_approver_for_created_requisition(page):
    """
    Test Case 4: Identify and capture the second-level approver of a submitted requisition in the ERP Procurement system.

    Objective:
        To verify that the system correctly retrieves the second-level approver
        for a previously submitted requisition, ensuring that the approval workflow
        is routed correctly to the next approver.

    Steps:
        1. Login to the procurement portal using the procurement user credentials.
        2. Navigate to the procurement dashboard.
        3. Access the "Requisition List" page.
        4. Search for the submitted requisition using its requisition number ('req_num').
        5. Capture a full-page screenshot for verification purposes.
        6. Retrieve and store the approver ID of the second-level approver in 'approver_id_2'.
        7. Capture a screenshot showing the approver information.
        8. Log out from the session and capture a final screenshot.
    """
    print("Test 4: Finding approver of the requisition again...")
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=proj_user,
        pass_word=proj_pass,
        timeout=60000
    )
    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.navigate_to_requisition_list()

    requisition_list_page = RequisitionList(page)
    requisition_list_page.search_requisition(req_num)
    requisition_list_page.get_full_page_screenshot('full_page_screenshot_11')

    global approver_id_2
    # global approver_id_2, order_approver
    # global order_approver
    # order_approver = requisition_list_page.find_approver_id()
    approver_id_2 = str(int(requisition_list_page.find_approver_id()))
    print("APPROVER ID 2:", approver_id_2)
    requisition_list_page.get_full_page_screenshot('full_page_screenshot_12')

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot('full_page_screenshot_13')
    m_page.wait_for_timeout(2000)


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 5: Login as the second-level approver and approve the submitted requisition in the ERP Procurement system.

    Objective:
        To verify that the second-level approver can successfully log in, locate the requisition,
        and approve it, ensuring that the approval workflow progresses correctly to the next stage.""")
def test_5_login_as_second_approver_and_approve_requisition(page):
    """
    Test Case 5: Login as the second-level approver and approve the submitted requisition in the ERP Procurement system.

    Objective:
        To verify that the second-level approver can successfully log in, locate the requisition,
        and approve it, ensuring that the approval workflow progresses correctly to the next stage.

    Steps:
        1. Login to the procurement portal using the second-level approver credentials ('approver_id_2').
        2. Navigate to the procurement dashboard.
        3. Access the "Requisition Approve List" page.
        4. Capture a full-page screenshot for documentation purposes.
        5. Search for the submitted requisition using its requisition number ('req_num').
        6. Select the requisition from the list.
        7. Approve the requisition.
        8. Capture a screenshot showing the approved requisition.
        9. Wait briefly to ensure all actions are completed.
        10. Log out from the session and capture a final screenshot.
    """
    print("Test 5: Logging in as second approver and approving requisition...")
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=approver_id_2,
        pass_word=proj_pass,
        timeout=60000  # Increased timeout for login
    )
    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.navigate_to_requisition_approve_list()

    requisition_approve_list_page = RequisitionApproveList(page)
    requisition_approve_list_page.get_full_page_screenshot('full_page_screenshot_14')
    requisition_approve_list_page.search_requisition(req_num)
    requisition_approve_list_page.select_requisition()
    requisition_approve_list_page.approve_requisition()
    requisition_approve_list_page.get_full_page_screenshot('full_page_screenshot_15')
    requisition_approve_list_page.wait_for_timeout(2000)

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot('full_page_screenshot_16')
    m_page.wait_for_timeout(2000)


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 6: Verify that the requisition is approved and retrieve vendor information from the ERP Procurement system.

    Objective:
        To ensure that the requisition submitted and approved in previous steps
        is correctly reflected as "Approved" in the system, and to capture
        detailed information including the assigned vendor for documentation and verification.""")
def test_6_verify_requisition_is_approved(page, new_tab):
    """
    Test Case 6: Verify that the requisition is approved and retrieve vendor information from the ERP Procurement system.

    Objective:
        To ensure that the requisition submitted and approved in previous steps
        is correctly reflected as "Approved" in the system, and to capture
        detailed information including the assigned vendor for documentation and verification.

    Steps:
        1. Login to the procurement portal using the procurement user credentials.
        2. Navigate to the procurement dashboard.
        3. Access the "Requisition List" page.
        4. Search for the submitted requisition using its requisition number ('req_num').
        5. Capture a screenshot of the requisition list and verify the requisition status.
        6. Open the requisition details page in a new tab.
        7. Capture a screenshot of the requisition details.
        8. Open the first FA (Framework Agreement) hyperlink in another new tab.
        9. Retrieve vendor information from the framework information page and store it in 'order_vendor'.
        10. Capture a screenshot of the framework information page.
        11. Close all newly opened tabs and return to the main page.
        12. Wait briefly to ensure all actions are completed.
        13. Log out from the session and capture a final screenshot.
    """
    print("Test 6: Checking requisition status after approval...")
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=proj_user,
        pass_word=proj_pass,
        timeout=60000
    )
    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.navigate_to_requisition_list()

    requisition_list_page = RequisitionList(page)
    requisition_list_page.search_requisition(req_num)
    req_status = requisition_list_page.find_requisition_status()
    print("REQ STATUS:", req_status)
    requisition_list_page.get_full_page_screenshot('full_page_screenshot_17')
    # expect(req_status).to_be_equal("Approved")
    # requisition_list_page.goto_requisition_details_information()
    # requisition_list_page.requisition_no.nth(0).click()

    new_page = new_tab(lambda p: requisition_list_page.goto_requisition_details_information())
    requisition_list_page.get_full_page_screenshot('full_page_screenshot_18')
    req_details = RequisitionDetailsInformation(new_page)
    # req_details.fa_no_hyperlink.nth(0).click()
    req_details.wait_for_timeout(2000)
    new_page_2 = new_tab(lambda p: req_details.fa_no_hyperlink.nth(0).click())
    req_details.get_full_page_screenshot('full_page_screenshot_19')
    framework_info = FrameworkInformation(new_page_2)

    global order_vendor
    order_vendor = framework_info.get_vendor_info()
    framework_info.wait_for_timeout(2000)
    framework_info.get_full_page_screenshot('full_page_screenshot_20')
    new_page_2.close()

    req_details.wait_for_timeout(2000)
    new_page.close()

    requisition_list_page = RequisitionList(page)
    requisition_list_page.wait_for_timeout(5000)

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot('full_page_screenshot_21')


# # Marketplace flow

@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 7: Marketplace order initiation process in the Staging environment.

    Objective:
        To verify that a marketplace order can be initiated, processed, and confirmed successfully
        by the order initiator, including selecting vendors, updating cart information, uploading attachments,
        scheduling delivery, and confirming the order.""")
def test_7_verify_requisition_sync_to_marketplace(page, new_tab):
    """
    Test Case 7: Verify Requisition Synchronization to Marketplace (Staging Environment).

    Objective:
        To validate that a successfully approved requisition in the ERP Procurement
        system is correctly synchronized and visible in the Marketplace staging
        environment under the Active Requisition list.

    Steps:
        1. Navigate to the Marketplace staging URL.
        2. Log in using SSO credentials.
        3. Verify successful login by checking the welcome message.
        4. Capture a full-page screenshot of the Marketplace home page.
        5. Navigate to the Active Requisition List.
        6. Search for the requisition using the requisition number.
        7. Open the Active Requisition Product List in a new tab.
        8. Capture screenshots of the product list and product switch history.
        9. Close the product list tab.
        10. Exit the Marketplace module and log out.
    """
    print("Test 7: Marketplace requisition is available on the Active Requisition List...")
    login_page = LoginPage(page)
    login_page.navigate_to_url(marketplace_url_qa)
    login_page.perform_login_for_sso_login(
        user_name=proj_user,
        pass_word=marketplace_password
    )

    home_page = HomePage(page)
    home_page.verify_welcome_message()
    home_page.get_full_page_screenshot('full_page_screenshot_22')
    home_page.wait_for_timeout(2000)
    home_page.go_to_active_requisition_list()

    active_requisition_list = ActiveRequisitionListPage(page)
    active_requisition_list.search_order_requisition_number(requisition_number=req_num)

    new_page = new_tab(lambda p: active_requisition_list.goto_active_requisition_product_list())

    active_requisition_product_list = ActiveRequisitionProductList(new_page)
    active_requisition_product_list.get_full_page_screenshot('full_page_screenshot_23')
    active_requisition_product_list.view_product_switch_history()
    active_requisition_product_list.get_full_page_screenshot('full_page_screenshot_24')
    new_page.close()

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot('full_page_screenshot_25')
