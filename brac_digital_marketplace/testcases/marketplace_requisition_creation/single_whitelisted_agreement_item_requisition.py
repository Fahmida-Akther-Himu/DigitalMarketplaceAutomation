from dotenv import load_dotenv
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
import pytest
import allure

load_dotenv()

# Page models for procurement
from utils.test_data_store import save_result
from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.my_dashboard.procurement.requisition.create_requisition import CreateRequisition
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_list import RequisitionList
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_approve_list import RequisitionApproveList
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_information import FrameworkInformation

# Page models for marketplace
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.public_side.my_account.active_requisition_list import ActiveRequisitionListPage
from pages.digital_marketplace.public_side.my_account.active_requisition_product_list import \
    ActiveRequisitionProductList
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu

# Procurement information
proj_env = os.getenv("test_env")
proj_user = os.getenv("test_user_name")

# Marketplace information
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")

# Requisition information
whitelisted_agreement_number = os.getenv("test_whitelisted_agreement_number")
requisition_project_name = os.getenv("test_requisition_project_name")
requisition_funding_source = os.getenv("test_requisition_funding_source")
requisition_funding_remarks = os.getenv("test_requisition_funding_remarks")
master_item_1 = os.getenv("test_master_item_1")
master_item_1_full_path = os.getenv("test_master_item_1_full_path")
item_gl_code_1 = os.getenv("test_item_gl_code_1")
requisition_item_1_quantity = os.getenv("test_requisition_item_1_quantity")
# Attachment file name in the utils folder (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX)
requisition_attachment_file = os.getenv("test_requisition_attachment_file")
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
# Head Office delivery location
schedule_address = os.getenv("test_schedule_address")

# Attachment and remarks rules
UTILS_DIR = Path(__file__).resolve().parents[3] / "utils"
ALLOWED_ATTACHMENT_TYPES = {".docx", ".pdf", ".xls", ".jpg", ".png", ".ppt", ".zip", ".pptx"}
MAX_ATTACHMENT_SIZE_MB = 20
MAX_REQUISITION_REMARKS_LENGTH = 300
MAX_ITEM_REMARKS_LENGTH = 500

# Procurement global variable
whitelisted_item = {}
whitelisted_item_applicable_for = ''
requisition_item_quantity = ''
requisition_attachment_name = ''
requisition_grid_item = ''
req_num = ''
req_submission_message = ''
approver_id = ''
req_status = ''
approver_id_2 = ''
second_layer_req_status = ''
approved_req_status = ''
verified_requisition_details = ''
order_vendor = ''
# Requisition result for order_creation/single_whitelisted_agreement_item_order.py
requisition_result = {}

# Marketplace global variable
active_requisition_found = False


def env_decimal(env_name, value):
    # .env value as an exact 2-digit fractional number, with a clear error if it is not a number
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        raise AssertionError(f"{env_name} in .env is not a valid number: {value!r}")


def erp_login(page, user_name):
    # ERP login with the ResetHub link
    reset_page = ResetHubPage(page)
    link = reset_page.generate_reset_link(
        env=proj_env,
        username=user_name,
    )
    reset_page.open_generated_link(link)
    assert isinstance(link, str) and link.startswith("http")
    print(f"Logging in as user: {user_name}")


def erp_logout(page, screenshot_name):
    # Exit and log out from ERP
    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot(screenshot_name)
    m_page.wait_for_timeout(2000)


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Whitelisted Framework Agreement Item")
@allure.title("Test_case_1: Create requisition with whitelisted item")
@allure.description("Test case 1: Login to the ERP Procurement system and create a requisition with one item of the "
                    "whitelisted Framework Agreement (quantity, GL code, attachment and remarks from .env).")
@pytest.mark.order(1)
def test_1_create_requisition_with_whitelisted_item(page):
    """
    Test Case 1: Create Requisition in ERP with a Whitelisted Framework Agreement Item.

    Steps:
        1. Log in to ERP (ResetHub link) and open
           Procurement > Requisition > Create Requisition.
        2. Select Head Office, Project, Source of Fund and enter Remarks (max 300 characters).
        3. Search and select Item Information.
        4. Click Check all active framework agreement and search the whitelisted Framework Agreement
           with Applicable For: Both. If not found, search again with HO, then HCMP.
        5. Select the first item of the exact whitelisted Framework Agreement and store it in 'whitelisted_item'.
        6. Enter the item quantity from .env and store it in 'requisition_item_quantity'.
        7. Click Amount radio button, then Quantity radio button; verify Quantity is unchanged.
        8. Select GL Code.
        9. Add attachment from utils (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX).
        10. Add item remarks (max 500 characters), click Add to grid and verify the item row
            (Quantity and Unit Price) and 1 item in the Requisition Detail Information List.

    All scenario values are read from .env.
    """
    global whitelisted_item, whitelisted_item_applicable_for, requisition_item_quantity, \
        requisition_attachment_name, requisition_grid_item

    # All scenario values must come from .env
    required_env_values = {
        "test_env": proj_env,
        "test_user_name": proj_user,
        "test_whitelisted_agreement_number": whitelisted_agreement_number,
        "test_requisition_project_name": requisition_project_name,
        "test_requisition_funding_source": requisition_funding_source,
        "test_requisition_funding_remarks": requisition_funding_remarks,
        "test_master_item_1": master_item_1,
        "test_master_item_1_full_path": master_item_1_full_path,
        "test_item_gl_code_1": item_gl_code_1,
        "test_requisition_item_1_quantity": requisition_item_1_quantity,
        "test_requisition_attachment_file": requisition_attachment_file,
        "test_requisition_item_remarks": requisition_item_remarks,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    # Item quantity: 2-digit fractional number, more than 0
    requisition_item_quantity = env_decimal("test_requisition_item_1_quantity", requisition_item_1_quantity)
    assert requisition_item_quantity > 0, \
        f"test_requisition_item_1_quantity must be > 0, found {requisition_item_1_quantity}"
    assert Decimal(str(requisition_item_1_quantity)) == requisition_item_quantity, \
        f"test_requisition_item_1_quantity must have max 2 decimals, found {requisition_item_1_quantity}"

    # Remarks and attachment rules
    assert len(requisition_funding_remarks) <= MAX_REQUISITION_REMARKS_LENGTH, \
        f"test_requisition_funding_remarks must be max {MAX_REQUISITION_REMARKS_LENGTH} characters, " \
        f"found {len(requisition_funding_remarks)}"
    assert len(requisition_item_remarks) <= MAX_ITEM_REMARKS_LENGTH, \
        f"test_requisition_item_remarks must be max {MAX_ITEM_REMARKS_LENGTH} characters, " \
        f"found {len(requisition_item_remarks)}"
    attachment_path = UTILS_DIR / requisition_attachment_file
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"
    assert attachment_path.suffix.lower() in ALLOWED_ATTACHMENT_TYPES, \
        f"Attachment type {attachment_path.suffix} is not allowed: {sorted(ALLOWED_ATTACHMENT_TYPES)}"
    attachment_size_mb = attachment_path.stat().st_size / (1024 * 1024)
    assert attachment_size_mb <= MAX_ATTACHMENT_SIZE_MB, \
        f"Attachment must be max {MAX_ATTACHMENT_SIZE_MB} MB, found {attachment_size_mb:.2f} MB"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    create_requisition_page = CreateRequisition(page)

    # Step 1: Log in to ERP and open Create Requisition
    with allure.step(f"Step 1: Log in to ERP as {proj_user} and open Create Requisition"):
        erp_login(page, proj_user)
        proc_dashboard_page.goto_procurement()
        proc_home_page.navigate_to_create_requisition()
        create_requisition_page.validate()
        create_requisition_page.get_full_page_screenshot('requisition_create_requisition')

    # Step 2: Head Office, Project, Source of Fund and Remarks
    with allure.step("Step 2: Select Head Office, Project, Source of Fund and enter Remarks"):
        create_requisition_page.setting_requisition_for(project_name=requisition_project_name)
        create_requisition_page.setting_requisition_information(
            fund_source=requisition_funding_source,
            fund_remarks=requisition_funding_remarks
        )
        create_requisition_page.get_full_page_screenshot('requisition_requisition_information')

    # Step 3: Search and select Item Information
    with allure.step(f"Step 3: Search and select Item Information {master_item_1_full_path}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=master_item_1,
            item_info_2=master_item_1_full_path
        )
        create_requisition_page.get_full_page_screenshot('requisition_item_information')

    # Step 4: Search the whitelisted Framework Agreement (Applicable For: Both, then HO/HCMP)
    with allure.step(f"Step 4: Search Active Framework Agreement {whitelisted_agreement_number}"):
        whitelisted_item_applicable_for = create_requisition_page.search_active_framework(
            agreement_number=whitelisted_agreement_number
        )
        allure.attach(
            f"{whitelisted_agreement_number} found with Applicable For: {whitelisted_item_applicable_for}",
            name="Active Framework Agreement search",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_active_framework_search')

    # Step 5: Select the first item of the whitelisted Framework Agreement
    with allure.step(f"Step 5: Select the first item of {whitelisted_agreement_number}"):
        whitelisted_item = create_requisition_page.select_first_active_framework_item(
            agreement_number=whitelisted_agreement_number
        )
        print("WHITELISTED ITEM:", whitelisted_item)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in whitelisted_item.items())
            + f"\napplicable_for: {whitelisted_item_applicable_for}",
            name="Selected whitelisted item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_whitelisted_item_selected')

    # Step 6: Enter the item quantity from .env
    with allure.step(f"Step 6: Enter item quantity {requisition_item_quantity}"):
        create_requisition_page.finalize_item_quantity(item_quantity=f"{requisition_item_quantity:.2f}")
        create_requisition_page.verify_item_quantity(expected_quantity=requisition_item_quantity)
        print("ITEM QUANTITY:", requisition_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_item_quantity')

    # Step 7: Click Amount, then Quantity radio button
    with allure.step("Step 7: Click Amount radio button, then Quantity radio button"):
        create_requisition_page.reset_cost_allocation_by_quantity()
        create_requisition_page.verify_item_quantity(expected_quantity=requisition_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_cost_allocation_quantity')

    # Step 8: Select GL Code
    with allure.step(f"Step 8: Select GL Code {item_gl_code_1}"):
        create_requisition_page.setting_item_gl_code(gl_code=item_gl_code_1)
        create_requisition_page.get_full_page_screenshot('requisition_gl_code')

    # Step 9: Add attachment from utils
    with allure.step(f"Step 9: Add attachment {attachment_path.name}"):
        assert create_requisition_page.upload_requisition_item_document(str(attachment_path)), \
            f"Attachment upload failed: {attachment_path.name}"
        requisition_attachment_name = attachment_path.name
        print("ATTACHMENT:", requisition_attachment_name)
        allure.attach(
            f"{attachment_path.name} ({attachment_size_mb:.2f} MB)",
            name="Attachment",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_attachment')

    # Step 10: Add item remarks, click Add to grid and verify the item row
    with allure.step("Step 10: Add item remarks, click Add to grid and verify 1 item"):
        create_requisition_page.setting_item_remarks(item_remarks=requisition_item_remarks)
        create_requisition_page.add_item_requisition_details_information_list()
        requisition_grid_item = create_requisition_page.verify_grid_item(
            quantity=requisition_item_quantity,
            unit_price=whitelisted_item["unit_price"]
        )
        create_requisition_page.verify_grid_row_count(expected_count=1)
        allure.attach(
            requisition_grid_item,
            name="Requisition Detail Information List item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_add_to_grid')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Submit Requisition")
@allure.title("Test_case_2: Submit requisition with whitelisted item")
@allure.description("Test case 2: Set the delivery schedule and Head Office location, submit the requisition with "
                    "the whitelisted item and get the submission confirmation message and requisition number.")
@pytest.mark.order(2)
def test_2_submit_requisition(page):
    """
    Test Case 2: Submit the requisition with the whitelisted Framework Agreement item.

    Steps:
        1. Set the same schedule (today).
        2. Set delivery location: Head Office and 'test_schedule_address'.
        3. Submit the requisition, get the submission confirmation message and store the
           requisition number in 'req_num'.

    All scenario values are read from .env.
    """
    global req_num, req_submission_message

    # Item comes from Test Case 1
    assert whitelisted_item, "Test Case 1 must pass first: requisition item is not added"
    assert schedule_address, "Missing in .env: test_schedule_address"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Same schedule for today
    with allure.step("Step 1: Set same schedule (today)"):
        create_requisition_page.setting_same_schedule_for_date()
        create_requisition_page.get_full_page_screenshot('requisition_schedule')

    # Step 2: Delivery location (Head Office)
    with allure.step(f"Step 2: Set delivery location Head Office - {schedule_address}"):
        create_requisition_page.setting_location_for_head_office(address=schedule_address)
        create_requisition_page.get_full_page_screenshot('requisition_delivery_location')

    # Step 3: Submit requisition, get the confirmation message and requisition number
    with allure.step("Step 3: Submit requisition"):
        req_submission_message, req_num = create_requisition_page.submit_requisition_with_message()
        assert req_num, "Requisition number not displayed after Submit"
        print("SUBMISSION MESSAGE:", req_submission_message)
        print("REQ NUM:", req_num)
        allure.attach(
            req_submission_message,
            name="Submission confirmation message",
            attachment_type=allure.attachment_type.TEXT
        )
        allure.attach(
            req_num,
            name="Requisition number",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_submitted')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Requisition Approver")
@allure.title("Test_case_3: Identify first approver")
@allure.description("Test case 3: Identify and capture the first approver of a submitted requisition.")
@pytest.mark.order(3)
def test_3_identify_first_approver(page):
    """
    Test Case 3: Identify and capture the first approver of the submitted requisition.

    Steps:
        1. Go to Requisition > Requisition List.
        2. Search the submitted requisition ('req_num').
        3. Get the first layer approver ID ('approver_id') and status ('req_status').
        4. Exit and log out from ERP.
    """
    global approver_id, req_status

    assert req_num, "Test Case 2 must pass first: no requisition number available"

    create_requisition_page = CreateRequisition(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Requisition > Requisition List
    with allure.step("Step 1: Go to Requisition > Requisition List"):
        create_requisition_page.navigate_to_requisition_list()
        requisition_list_page.get_full_page_screenshot('requisition_list')

    # Step 2: Search the submitted requisition
    with allure.step(f"Step 2: Search requisition {req_num}"):
        requisition_list_page.search_requisition(req_num)
        requisition_list_page.get_full_page_screenshot('requisition_list_search')

    # Step 3: Get first layer approver ID and status
    with allure.step(f"Step 3: Get first layer approver ID and status of {req_num}"):
        approver_id = str(int(requisition_list_page.find_approver_id()))
        req_status = requisition_list_page.find_requisition_status()
        print("APPROVER ID:", approver_id)
        print("REQ STATUS:", req_status)
        allure.attach(
            f"Requisition number: {req_num}\nFirst approver ID: {approver_id}\nStatus: {req_status}",
            name="First approver ID and status",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_list_page.get_full_page_screenshot('requisition_first_approver_id')

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_initiator_logout')


@allure.suite("Requisition")
@allure.feature("Requisition Approve List")
@allure.story("First Layer Approval")
@allure.title("Test_case_4: Approve requisition as first approver")
@allure.description(
    "Test case 4: Login as the first approver and approve the submitted requisition in the ERP Procurement system.")
@pytest.mark.order(4)
def test_4_approve_requisition_as_first_approver(page):
    """
    Test case 4: Login as the first approver and approve the submitted requisition.

    Steps:
        1. Log in to ERP as the first approver ('approver_id') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition and approve it.
        4. Exit and log out.
    """
    assert req_num and approver_id, "Test case 3 must pass first: no requisition number/approver ID available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_approve_list_page = RequisitionApproveList(page)

    # Step 1: Log in as the first approver
    with allure.step(f"Step 1: Log in to ERP as first approver {approver_id}"):
        erp_login(page, approver_id)
        proc_dashboard_page.menu_click_procurement_hyperlink()
        proc_dashboard_page.get_full_page_screenshot('requisition_first_approver_login')

    # Step 2: Requisition Approve List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition Approve List"):
        proc_home_page.navigate_to_requisition_approve_list()
        requisition_approve_list_page.search_requisition(req_num)
        requisition_approve_list_page.get_full_page_screenshot('requisition_first_approver_search')

    # Step 3: Select and approve the requisition
    with allure.step(f"Step 3: Approve requisition {req_num} as first approver"):
        requisition_approve_list_page.select_requisition()
        requisition_approve_list_page.approve_requisition()
        print(f"Requisition {req_num} approved by first approver: {approver_id}")
        allure.attach(
            f"Requisition number: {req_num}\nApproved by first approver: {approver_id}",
            name="First layer approval",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_approve_list_page.get_full_page_screenshot('requisition_first_approver_approved')
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_first_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Second Layer Approval")
@allure.title("Test_case_5: Identify second approver")
@allure.description(
    "Test case 5: Identify and capture the second-level approver of a submitted requisition in the ERP "
    "Procurement system.")
@pytest.mark.order(5)
def test_5_identify_second_approver(page):
    """
    Test case 5: Identify and capture the second-level approver of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List and search the requisition ('req_num').
        3. Get the second (final) layer approver ID ('approver_id_2') and status ('second_layer_req_status').
        4. Exit and log out.
    """
    global approver_id_2, second_layer_req_status
    assert req_num, "Test case 2 must pass first: no requisition number available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Log in as the requisition initiator
    with allure.step(f"Step 1: Log in to ERP as requisition initiator {proj_user}"):
        erp_login(page, proj_user)
        proc_dashboard_page.goto_procurement()

    # Step 2: Requisition List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition List"):
        proc_home_page.navigate_to_requisition_list()
        requisition_list_page.search_requisition(req_num)
        requisition_list_page.get_full_page_screenshot('requisition_second_approver_search')

    # Step 3: Get the second (final) layer approver ID
    with allure.step("Step 3: Get the second (final) layer approver ID"):
        approver_id_2 = str(int(requisition_list_page.find_approver_id()))
        second_layer_req_status = requisition_list_page.find_requisition_status()
        print("APPROVER ID 2:", approver_id_2)
        print("REQ STATUS:", second_layer_req_status)
        allure.attach(
            f"Requisition number: {req_num}\nSecond approver ID: {approver_id_2}\nStatus: {second_layer_req_status}",
            name="Second approver ID and status",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_list_page.get_full_page_screenshot('requisition_second_approver_id')

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_second_approver_identify_logout')


@allure.suite("Requisition")
@allure.feature("Requisition Approve List")
@allure.story("Second Layer Approval")
@allure.title("Test_case_6: Approve requisition as final approver")
@allure.description(
    "Test case 6: Login as the second-level (final) approver and approve the submitted requisition in the ERP "
    "Procurement system.")
@pytest.mark.order(6)
def test_6_approve_requisition_as_final_approver(page):
    """
    Test case 6: Login as the second-level (final) approver and approve the requisition.

    Steps:
        1. Log in to ERP as the final approver ('approver_id_2') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition and approve it.
        4. Exit and log out.
    """
    assert req_num and approver_id_2, "Test case 5 must pass first: no requisition number/second approver available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_approve_list_page = RequisitionApproveList(page)

    # Step 1: Log in as the final approver
    with allure.step(f"Step 1: Log in to ERP as final approver {approver_id_2}"):
        erp_login(page, approver_id_2)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('requisition_final_approver_login')

    # Step 2: Requisition Approve List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition Approve List"):
        proc_home_page.navigate_to_requisition_approve_list()
        requisition_approve_list_page.search_requisition(req_num)
        requisition_approve_list_page.get_full_page_screenshot('requisition_final_approver_search')

    # Step 3: Select and approve the requisition
    with allure.step(f"Step 3: Approve requisition {req_num} as final approver"):
        requisition_approve_list_page.select_requisition()
        requisition_approve_list_page.approve_requisition()
        print(f"Requisition {req_num} approved by final approver: {approver_id_2}")
        allure.attach(
            f"Requisition number: {req_num}\nApproved by final approver: {approver_id_2}",
            name="Final layer approval",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_approve_list_page.get_full_page_screenshot('requisition_final_approver_approved')
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_final_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Requisition Status")
@allure.title("Test_case_7: Requisition initiator gets approval status")
@allure.description(
    "Test case 7: Login as the requisition initiator, get the approval status of the requisition and verify the "
    "requisition details (FA No, item, quantity, unit price) and vendor match the whitelisted item.")
@pytest.mark.order(7)
def test_7_requisition_initiator_gets_approval_status(page, new_tab):
    """
    Test case 7: Requisition initiator gets the approval status of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List, search the requisition ('req_num') and get its approval status.
        3. Open the requisition details in a new tab and verify the whitelisted item (Test case 1)
           with its FA No, item, quantity and unit price.
        4. Open the FA No link in a new tab and verify the vendor is the same as the
           whitelisted item vendor (Test case 1); store it in 'order_vendor'.
        5. Close the tabs, exit and log out.
        6. Save the requisition result for single_whitelisted_agreement_item_order.py.
    """
    global approved_req_status, verified_requisition_details, order_vendor, requisition_result
    assert req_num, "Test case 2 must pass first: no requisition number available"
    assert whitelisted_item, "Test case 1 must pass first: requisition item not available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Log in as the requisition initiator
    with allure.step(f"Step 1: Log in to ERP as requisition initiator {proj_user}"):
        erp_login(page, proj_user)
        proc_dashboard_page.goto_procurement()

    # Step 2: Requisition List, search the requisition and get its approval status
    with allure.step(f"Step 2: Get approval status of requisition {req_num}"):
        proc_home_page.navigate_to_requisition_list()
        requisition_list_page.search_requisition(req_num)
        approved_req_status = requisition_list_page.find_requisition_status()
        print("REQ STATUS:", approved_req_status)
        allure.attach(
            f"Requisition number: {req_num}\nStatus: {approved_req_status}",
            name="Requisition approval status",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_list_page.get_full_page_screenshot('requisition_approval_status')

    # Step 3: Open requisition details in a new tab and verify the whitelisted item
    with allure.step(f"Step 3: Verify requisition details of {req_num}"):
        details_tab = new_tab(lambda p: requisition_list_page.goto_requisition_details_information())
        requisition_details_page = RequisitionDetailsInformation(details_tab)
        # Master item code, e.g. "[22245]" from "[22245]-Pen Box-(...)"
        master_item_1_code = re.search(r"\[[^\]]+\]", master_item_1_full_path).group(0)

        verified_requisition_details = requisition_details_page.verify_requisition_details(
            requisition_number=req_num,
            fa_no=whitelisted_agreement_number,
            item_code=master_item_1_code,
            quantity=requisition_item_quantity,
            unit_price=whitelisted_item["unit_price"]
        )
        print("VERIFIED REQUISITION DETAILS:", verified_requisition_details)
        allure.attach(
            f"Requisition number: {req_num}\nStatus: {approved_req_status}\n"
            f"FA. No: {whitelisted_agreement_number}\n"
            f"Item: {master_item_1_code}, quantity {requisition_item_quantity}, "
            f"unit price {whitelisted_item['unit_price']}\n  Details row: {verified_requisition_details}",
            name="Verified requisition details",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_details_page.get_full_page_screenshot('requisition_details_verified')

    # Step 4: Open the FA No link and verify the vendor is the same as the whitelisted item vendor
    with allure.step(f"Step 4: Verify vendor of {whitelisted_agreement_number} is {whitelisted_item['vendor_name']}"):
        framework_tab = new_tab(
            lambda p: requisition_details_page.open_framework_details_by_fa_no(whitelisted_agreement_number))
        framework_info_page = FrameworkInformation(framework_tab)
        order_vendor = framework_info_page.get_vendor_info()
        print("ORDER VENDOR:", order_vendor)
        # Grid vendor has the vendor code, e.g. "[SU000723]- Walton Hi-Tech Industries PLC"
        assert order_vendor.lower() in whitelisted_item["vendor_name"].lower(), \
            f"Requisition vendor '{order_vendor}' is not the same as the whitelisted item vendor " \
            f"'{whitelisted_item['vendor_name']}'"
        allure.attach(
            f"Whitelisted item vendor (Test case 1): {whitelisted_item['vendor_name']}\n"
            f"Requisition vendor (FA No link): {order_vendor}",
            name="Verified vendor",
            attachment_type=allure.attachment_type.TEXT
        )
        framework_info_page.get_full_page_screenshot('requisition_vendor_verified')

    # Step 5: Close the tabs, exit and log out
    with allure.step("Step 5: Close requisition details tabs, exit and log out from ERP"):
        framework_tab.close()
        details_tab.close()
        page.bring_to_front()
        erp_logout(page, 'requisition_initiator_final_logout')

    # Step 6: Save the requisition result for the order test file
    with allure.step("Step 6: Save the requisition result for single_whitelisted_agreement_item_order.py"):
        requisition_result = {
            "requisition_number": req_num,
            "requisition_status": approved_req_status,
            "agreement_number": whitelisted_agreement_number,
            "agreement_version": whitelisted_item["fa_no"],
            "applicable_for": whitelisted_item_applicable_for,
            "vendor": order_vendor,
            "final_approver": approver_id_2,
            "attachment_name": requisition_attachment_name,
            "item": {
                "item_code": whitelisted_item["item_code"],
                "item_name": whitelisted_item["item_name"],
                "master_item_code": master_item_1_code,
                "specification": whitelisted_item["specification"],
                "quantity": str(requisition_item_quantity),
                "unit_price": whitelisted_item["unit_price"],
            },
        }
        save_result("single_whitelisted_requisition_result", requisition_result)
        print("REQUISITION RESULT:", requisition_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in requisition_result.items()),
            name="Saved requisition result",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.suite("Public Side")
@allure.feature("Active Requisition List")
@allure.story("Active Requisition Product List")
@allure.title("Test_case_8: Verify requisition sync to marketplace")
@allure.description("Test case 8: Verify the approved requisition is synchronized to the Digital Marketplace and "
                    "visible in the Active Requisition List with its product list and product switch history.")
@pytest.mark.order(8)
def test_8_verify_requisition_sync_to_marketplace(page, new_tab):
    """
    Test Case 8: Verify Requisition Synchronization to Marketplace.

    Steps:
        1. Log in to the Digital Marketplace as 'proj_user' using SSO and verify the welcome message.
        2. Go to the Active Requisition List and search the requisition ('req_num').
        3. Open the Active Requisition Product List in a new tab and view the product switch history.
        4. Close the product list tab and log out from the Digital Marketplace.

    All scenario values are read from .env.
    """
    global active_requisition_found
    assert req_num, "Test case 2 must pass first: no requisition number available"

    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    active_requisition_list = ActiveRequisitionListPage(page)

    # Step 1: Log in to the Digital Marketplace
    with allure.step(f"Step 1: Log in to the Digital Marketplace as {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=proj_user, pass_word=marketplace_password)
        print(f"Logging in to the Digital Marketplace as: {proj_user}")
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('marketplace_login')

    # Step 2: Active Requisition List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Active Requisition List"):
        home_page.go_to_active_requisition_list()
        active_requisition_list.search_order_requisition_number(requisition_number=req_num)
        active_requisition_found = True
        print(f"Requisition {req_num} found in Active Requisition List")
        allure.attach(
            f"Requisition number: {req_num}",
            name="Active requisition",
            attachment_type=allure.attachment_type.TEXT
        )
        active_requisition_list.get_full_page_screenshot('marketplace_active_requisition_search')

    # Step 3: Active Requisition Product List and product switch history
    with allure.step(f"Step 3: Open product list of {req_num} and view product switch history"):
        product_list_tab = new_tab(lambda p: active_requisition_list.goto_active_requisition_product_list())
        active_requisition_product_list = ActiveRequisitionProductList(product_list_tab)
        active_requisition_product_list.get_full_page_screenshot('marketplace_active_requisition_product_list')
        active_requisition_product_list.view_product_switch_history()
        active_requisition_product_list.get_full_page_screenshot('marketplace_product_switch_history')

    # Step 4: Close the product list tab and log out
    with allure.step("Step 4: Close the product list tab and log out from the Digital Marketplace"):
        product_list_tab.close()
        page.bring_to_front()
        MainNavigationMenu(page).perform_logout()
        home_page.get_full_page_screenshot('marketplace_logout')
