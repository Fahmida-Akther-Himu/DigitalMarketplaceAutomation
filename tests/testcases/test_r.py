from dotenv import load_dotenv
import os
import re
import random
import string
import pytest
from conftest import new_tab
from datetime import datetime, timedelta

load_dotenv()

# Project URLs
proj_url = os.getenv("test_url")
requisition_list_url = proj_url + "/procurementDashboard/myDashboard#!/requisition/list"

# Procurement information
proj_user = os.getenv("test_user_name")
proj_pass = os.getenv("test_user_pass")
requisition_project_name = os.getenv("test_requisition_project_name")
whitelisted_agreement_number = os.getenv("test_whitelisted_agreement_number")

# Marketplace information
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
order_initiator = os.getenv("test_order_initiator")
marketplace_password = os.getenv("test_marketplace_password")
stg_vendor_pass = os.getenv("test_stg_vendor_pass")
# req_num = os.getenv("test_req_num")
# receiving_pin_1 = os.getenv("test_receiving_pin")
# sso_login_receiver_pin = os.getenv("test_sso_login_receiver_pin")
order_approver = os.getenv("test_order_approver")
marketplace_admin = os.getenv("test_order_admin")
# manual_delivery_location_1 = os.getenv("test_delivery_location_1")
# manual_delivery_location_2 = os.getenv("test_delivery_location_2")
dm_user_gen_password = os.getenv("test_dm_user_gen_password")
agreement = os.getenv("test_white_listed_agreement")
login_credential_for_receiver = os.getenv("test_login_credential_for_receiver")
proc_admin = os.getenv("test_proc_admin")
# order_reference_number = os.getenv("test_order_reference_number")

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
# from pages.digital_marketplace.bill_list import BillList
# from pages.digital_marketplace.create_vendor_bill_payable import CreateVendorBillPayable
# from pages.digital_marketplace.bill_details import BillDetails

# Page models for marketplace
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
# from pages.digital_marketplace.shopping_cart import ShoppingCart
# from pages.digital_marketplace.checkout_page import CheckoutPage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.active_requisition_list import ActiveRequisitionListPage
from pages.digital_marketplace.active_requisition_product_list import ActiveRequisitionProductList
from pages.digital_marketplace.pending_approval_orders import PendingApprovalOrders
# from pages.digital_marketplace.customers import Customers
# from pages.digital_marketplace.product_switch_history import ProductSwitchHistory
# from pages.digital_marketplace.vendor_dashboard import VendorDashboard
# from pages.digital_marketplace.all_order_for_admin import AllOrderForAdminPage
# from pages.digital_marketplace.order_management import OrderManagement
# from pages.digital_marketplace.receivable_order_list import ReceivableOrderListPage
# from pages.digital_marketplace.item_received_list import ItemReceivedList
# from pages.digital_marketplace.order_details_administration import OrderDetailsAdministration
from pages.digital_marketplace.preview import Preview

# For validation
from playwright.sync_api import expect

# Import for beautiful reporting
from rich.traceback import install

install()
# Marketplace global variable
# order_reference_number = ''
# framework_order_no = ''
# vendor_login_id = ''
# challan_num_for_receiver = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
# challan_num_for_order_initiator = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
# challan_num_for_order_initiator_2 = ''.join(random.choices(string.ascii_letters, k=8))

# Procurement global variable
req_num = ''
approver_id = ''
approver_id_2 = ''
order_vendor = ''
# order_approver = ''
approver_id_3 = ''
purchase_num = ''
challan_num = str(random.randint(10000, 99999))


# bill_num = str(random.randint(10000, 99999))
# bill_recommender_1 = ''
# bill_recommender_2 = ''
# bill_approver_id = ''
# bill_recommender_3 = ''


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 1: Login to the ERP Procurement system and create & submit a requisition for white listed agreement item.

    Objective:
        To validate that a user can successfully log in to the ERP Procurement system,
        create a requisition using a whitelisted framework agreement item,
        provide all necessary requisition details, and submit it successfully —
        generating a unique requisition number for further processing.""")
def test_1_create_requisition_with_whitelisted_agreement_item(page):
    """
    Test Case 1: Login to the ERP Procurement system and create & submit a requisition for white listed agreement item.

    Objective:
        To validate that a user can successfully log in to the ERP Procurement system,
        create a requisition using a whitelisted framework agreement item,
        provide all necessary requisition details, and submit it successfully —
        generating a unique requisition number for further processing.

    Steps:
        1. Login to the procurement portal using valid credentials.
        2. Navigate to the procurement dashboard.
        3. Capture a full-page screenshot for verification.
        4. Go to the "Create Requisition" page.
        5. Set up requisition details such as department, funding source, and remarks.
        6. Add items, select active framework agreements, and finalize quantities.
        7. Add scheduling and location details.
        8. Submit the requisition and record the generated requisition number.
        9. Navigate to the requisition list to confirm successful creation.
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
    create_requisition_page.setting_requisition_information("BRAC Fund", "Remarks for funding")
    create_requisition_page.setting_requisition_details("pen",
                                                        "[22245]-Pen Box-(Supplies and Stationeries->Supplies and Stationeries->Stationery)")

    create_requisition_page.active_agreement_button.click()
    create_requisition_page.setting_active_framework_list(agreement_info=whitelisted_agreement_number)
    create_requisition_page.count_and_select_active_framework_items()
    create_requisition_page.wait_for_timeout(2000)
    # create_requisition_page.agreement_item_selector.nth(0).click()
    # create_requisition_page.finalize_item_quantity(item_quantity="100")
    #
    # create_requisition_page.setting_requisition_for_details("1202010501",
    #                                                         "Item remarks abc123@")
    # # create_requisition_page.setting_requisition_for_details("[1101010101-02] Petty Cash",
    # #                                                         "Item remarks abc123@")
    # create_requisition_page.setting_same_schedule_for_date()
    # create_requisition_page.setting_location_for_head_office(address="Gulshan 1, Head Office, Dhaka - 1200")
    # create_requisition_page.get_full_page_screenshot('full_page_screenshot_3')
    # global req_num
    # req_num = create_requisition_page.submit_requisition()
    # print("REQ NUM:", req_num)
    # create_requisition_page.navigate_to_requisition_list()
    # create_requisition_page.get_full_page_screenshot('full_page_screenshot_4')
