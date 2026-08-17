from dotenv import load_dotenv
import os
import random
import string
import pytest

load_dotenv()

# Project URLs
proj_url = os.getenv("test_url")
# requisition_list_url = proj_url + "/procurementDashboard/myDashboard#!/requisition/list"

# Procurement information
proj_env = os.getenv("test_env")
proj_user = os.getenv("test_user")
# proj_user = os.getenv("test_user_name")
proj_pass = os.getenv("test_user_pass")
# proj_gen_pass = os.getenv("test_user_generic_pass")
# admin_user = os.getenv("test_admin")
# assigned_person = os.getenv("test_requisition_assignee")
# vendor_name = os.getenv("test_vendor_name")
# dp_approver = os.getenv("test_dp_approver")
bill_creator = os.getenv("test_bill_creator")

# Marketplace information
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
order_initiator = os.getenv("test_order_initiator")
marketplace_password = os.getenv("test_marketplace_password")
stg_vendor_pass = os.getenv("test_stg_vendor_pass")
# req_num = os.getenv("test_req_num")
receiving_pin_1 = os.getenv("test_receiving_pin")
sso_login_receiver_pin = os.getenv("test_sso_login_receiver_pin")
order_approver = os.getenv("test_order_approver")
marketplace_admin = os.getenv("test_order_admin")
manual_delivery_location_1 = os.getenv("test_delivery_location_1")
manual_delivery_location_2 = os.getenv("test_delivery_location_2")
dm_user_gen_password = os.getenv("test_dm_user_gen_password")
agreement = os.getenv("test_white_listed_agreement")
login_credential_for_receiver = os.getenv("test_login_credential_for_receiver")
proc_admin = os.getenv("test_proc_admin")
# order_reference_number = os.getenv("test_order_reference_number")

# Page models for procurement
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.my_dashboard.procurement.requisition.create_requisition import CreateReqPage

# Page models for marketplace
from pages.erp_procurement.reset_hub_page import ResetHubPage

# For validation

# Import for beautiful reporting
from rich.traceback import install

install()
# Marketplace global variable
order_reference_number = ''
framework_order_no = ''
vendor_login_id = ''
challan_num_for_receiver = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
challan_num_for_order_initiator = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
challan_num_for_order_initiator_2 = ''.join(random.choices(string.ascii_letters, k=8))

# Procurement global variable
req_num = ''
approver_id = ''
approver_id_2 = ''
order_vendor = ''
# order_approver = ''
approver_id_3 = ''
purchase_num = ''
challan_num = str(random.randint(10000, 99999))
bill_num = str(random.randint(10000, 99999))
bill_recommender_1 = ''
bill_recommender_2 = ''
bill_approver_id = ''
bill_recommender_3 = ''


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""Test Case 1: Login to the ERP Procurement system and create & submit a requisition for white listed agreement item.

    Objective:
        To validate that a user can successfully log in to the ERP Procurement system,
        create a requisition using a whitelisted framework agreement item,
        provide all necessary requisition details, and submit it successfully —
        generating a unique requisition number for further processing.""")
def test_1_create_requisition_with_whitelisted_agreement_item(page, logger):
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
    # proc_login_page = ProcurementLoginPage(page)
    # proc_login_page.perform_login(
    #     given_url=proj_url,
    #     user_name=proj_user,
    #     pass_word=proj_pass,
    #     # pass_word="%hj8hU!T",
    #     timeout=60000
    # )

    reset_page = ResetHubPage(page)

    link = reset_page.generate_reset_link(
        env=proj_env,
        username=proj_user,
    )

    print("Generated Link:" + link)
    reset_page.open_generated_link(link)
    assert isinstance(link, str) and link.startswith("http")

    logger.step(f" 📥 Logging in as user: {proj_user}")

    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()
    # proc_dashboard_page.wait_for_timeout(30000)
    proc_dashboard_page.get_full_page_screenshot('full_page_screenshot_1')

    proc_home_page = ProcurementHomePage(page)
    # proc_home_page.wait_for_timeout(30000)
    proc_home_page.navigate_to_create_requisition()
    proc_home_page.get_full_page_screenshot('full_page_screenshot_2')

    print("Test 1: Creating requisition...")
    create_requisition_page = CreateReqPage(page)
    # c_page.validate()
    create_requisition_page.setting_requisition_for("[H10] - Construction")
    create_requisition_page.setting_requisition_information("BRAC Fund", "Remarks for funding")
    create_requisition_page.setting_requisition_details("pen",
                                                        "[22245]-Pen Box-(Supplies and Stationeries->Supplies and Stationeries->Stationery)")
