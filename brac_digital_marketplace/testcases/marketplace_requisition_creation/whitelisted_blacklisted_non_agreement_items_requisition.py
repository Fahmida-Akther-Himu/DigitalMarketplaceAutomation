from dotenv import load_dotenv
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
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
from pages.digital_marketplace.public_side.my_account.product_switch_history import ProductSwitchHistory

# Procurement information
proj_env = os.getenv("test_env")
proj_user = os.getenv("test_user_name")
# ERP staging address: a FwA attachment that is not available opens an ERP page with a message
erp_url = os.getenv("test_url")

# Marketplace information
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")

# Requisition information
requisition_project_name = os.getenv("test_requisition_project_name")
requisition_funding_source = os.getenv("test_requisition_funding_source")
requisition_funding_remarks = os.getenv("test_requisition_funding_remarks")
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
# Whitelisted and blacklisted framework agreements
whitelisted_agreement_number = os.getenv("test_whitelisted_agreement_number")
blacklisted_agreement_number = os.getenv("test_blacklisted_agreement_number")
# First item (agreement 1)
master_item_1 = os.getenv("test_master_item_1")
master_item_1_full_path = os.getenv("test_master_item_1_full_path")
item_gl_code_1 = os.getenv("test_item_gl_code_1")
requisition_item_1_quantity = os.getenv("test_requisition_item_1_quantity")
# Attachment file name in the utils folder (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX)
requisition_attachment_file = os.getenv("test_requisition_attachment_file")
# Second item (agreement 2)
master_item_2 = os.getenv("test_master_item_2")
master_item_2_full_path = os.getenv("test_master_item_2_full_path")
item_gl_code_2 = os.getenv("test_item_gl_code_2")
requisition_item_2_quantity = os.getenv("test_requisition_item_2_quantity")
requisition_attachment_file_2 = os.getenv("test_requisition_attachment_file_2")
# Third item (non-agreement item with a unit price)
master_item_3 = os.getenv("test_master_item_3")
master_item_3_full_path = os.getenv("test_master_item_3_full_path")
item_gl_code_3 = os.getenv("test_item_gl_code_3")
requisition_item_3_quantity = os.getenv("test_requisition_item_3_quantity")
requisition_non_agreement_unit_price = os.getenv("test_requisition_non_agreement_unit_price")
# Central Store delivery address
schedule_address = os.getenv("test_schedule_address")

# Attachment and remarks rules
UTILS_DIR = Path(__file__).resolve().parents[3] / "utils"
ALLOWED_ATTACHMENT_TYPES = {".docx", ".pdf", ".xls", ".jpg", ".png", ".ppt", ".zip", ".pptx"}
MAX_ATTACHMENT_SIZE_MB = 20
MAX_REQUISITION_REMARKS_LENGTH = 300
MAX_ITEM_REMARKS_LENGTH = 500

# Procurement global variable
first_item = {}
first_item_applicable_for = ''
first_item_quantity = ''
first_item_attachment_name = ''
first_item_grid_row = ''
second_item = {}
second_item_applicable_for = ''
second_item_quantity = ''
second_item_attachment_name = ''
second_item_grid_row = ''
non_agreement_item = {}
third_item_quantity = ''
third_item_grid_row = ''
req_num = ''
req_submission_message = ''
approver_id = ''
req_status = ''
first_approval_message = ''
approver_id_2 = ''
second_layer_req_status = ''
final_approval_message = ''
approved_req_status = ''
verified_requisition_details = {}
agreement_vendors = {}
order_vendor = ''
# Requisition result for an order creation test file
requisition_result = {}

# Marketplace global variable
active_requisition_found = False
# Active Requisition Product List links (Test case 10) and Product Switch History (Test case 11)
# ERP requisition details opened from the ERP View button
erp_requisition_information = {}
product_list_tab = None
active_product_links = []
product_switch_history = []


def env_decimal(env_name, value):
    # .env value as an exact 2-digit fractional number, with a clear error if it is not a number
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        raise AssertionError(f"{env_name} in .env is not a valid number: {value!r}")


def check_item_quantity(env_name, value):
    # Item quantity: 2-digit fractional number, more than 0
    quantity = env_decimal(env_name, value)
    assert quantity > 0, f"{env_name} must be > 0, found {value}"
    assert Decimal(str(value)) == quantity, f"{env_name} must have max 2 decimals, found {value}"
    return quantity


def check_attachment(env_name, file_name):
    # Attachment in utils: allowed type and max 20 MB
    attachment_path = UTILS_DIR / file_name
    assert attachment_path.is_file(), f"{env_name} not found in utils: {attachment_path}"
    assert attachment_path.suffix.lower() in ALLOWED_ATTACHMENT_TYPES, \
        f"Attachment type {attachment_path.suffix} is not allowed: {sorted(ALLOWED_ATTACHMENT_TYPES)}"
    attachment_size_mb = attachment_path.stat().st_size / (1024 * 1024)
    assert attachment_size_mb <= MAX_ATTACHMENT_SIZE_MB, \
        f"Attachment must be max {MAX_ATTACHMENT_SIZE_MB} MB, found {attachment_size_mb:.2f} MB"
    return attachment_path, attachment_size_mb


def without_spaces(text):
    # ERP shows "[H10]- Construction" for "[H10] - Construction": compare without spaces, case-insensitive
    return "".join(str(text).split()).lower()


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
@allure.story("Whitelisted Blacklisted And Non-Agreement Items")
@allure.title("Test_case_1: Create requisition with whitelisted agreement item")
@allure.description("Test case 1: Login to the ERP Procurement system and create a requisition with the first master "
                    "item and the first item of the whitelisted Framework Agreement (quantity, GL code, "
                    "attachment and remarks from .env).")
@pytest.mark.order(1)
def test_1_create_requisition_with_whitelisted_agreement_item(page):
    """
    Test Case 1: Create Requisition in ERP with the first agreement item.

    Steps:
        1. Log in to ERP (ResetHub link) and open
           Procurement > Requisition > Create Requisition.
        2. Select Head Office, Project, Source of Fund and enter Remarks (max 300 characters).
        3. Search and select Item Information (master item 1).
        4. Click Check all active framework agreement and search the first Framework Agreement
           ('test_whitelisted_agreement_number') with Applicable For: Both. If not found, search again
           with HO, then HCMP.
        5. Select the first item of the exact Framework Agreement and store it in 'first_item'.
        6. Enter the first item quantity from .env and store it in 'first_item_quantity'.
        7. Click Amount radio button, then Quantity radio button; verify Quantity is unchanged.
        8. Select GL Code 1.
        9. Add attachment from utils (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX).
        10. Add item remarks (max 500 characters), click Add to grid and verify the item row
            (Quantity and Unit Price) and 1 item in the Requisition Detail Information List.

    All scenario values are read from .env.
    """
    global first_item, first_item_applicable_for, first_item_quantity, first_item_attachment_name, \
        first_item_grid_row

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

    # Quantity, remarks and attachment rules
    first_item_quantity = check_item_quantity("test_requisition_item_1_quantity", requisition_item_1_quantity)
    assert len(requisition_funding_remarks) <= MAX_REQUISITION_REMARKS_LENGTH, \
        f"test_requisition_funding_remarks must be max {MAX_REQUISITION_REMARKS_LENGTH} characters, " \
        f"found {len(requisition_funding_remarks)}"
    assert len(requisition_item_remarks) <= MAX_ITEM_REMARKS_LENGTH, \
        f"test_requisition_item_remarks must be max {MAX_ITEM_REMARKS_LENGTH} characters, " \
        f"found {len(requisition_item_remarks)}"
    attachment_path, attachment_size_mb = check_attachment("test_requisition_attachment_file",
                                                           requisition_attachment_file)

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

    # Step 3: Search and select Item Information (master item 1)
    with allure.step(f"Step 3: Search and select Item Information {master_item_1_full_path}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=master_item_1,
            item_info_2=master_item_1_full_path
        )
        create_requisition_page.get_full_page_screenshot('requisition_first_item_information')

    # Step 4: Search the first Framework Agreement (Applicable For: Both, then HO/HCMP)
    with allure.step(f"Step 4: Search Active Framework Agreement {whitelisted_agreement_number}"):
        first_item_applicable_for = create_requisition_page.search_active_framework(
            agreement_number=whitelisted_agreement_number
        )
        allure.attach(
            f"{whitelisted_agreement_number} found with Applicable For: {first_item_applicable_for}",
            name="First Framework Agreement search",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_first_item_framework_search')

    # Step 5: Select the first item of the first Framework Agreement
    with allure.step(f"Step 5: Select the first item of {whitelisted_agreement_number}"):
        first_item = create_requisition_page.select_first_active_framework_item(
            agreement_number=whitelisted_agreement_number
        )
        print("FIRST ITEM:", first_item)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in first_item.items())
            + f"\napplicable_for: {first_item_applicable_for}",
            name="Selected first agreement item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_first_item_selected')

    # Step 6: Enter the first item quantity from .env
    with allure.step(f"Step 6: Enter first item quantity {first_item_quantity}"):
        create_requisition_page.finalize_item_quantity(item_quantity=f"{first_item_quantity:.2f}")
        create_requisition_page.verify_item_quantity(expected_quantity=first_item_quantity)
        print("FIRST ITEM QUANTITY:", first_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_first_item_quantity')

    # Step 7: Click Amount, then Quantity radio button
    with allure.step("Step 7: Click Amount radio button, then Quantity radio button"):
        create_requisition_page.reset_cost_allocation_by_quantity()
        create_requisition_page.verify_item_quantity(expected_quantity=first_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_first_item_cost_allocation')

    # Step 8: Select GL Code 1
    with allure.step(f"Step 8: Select GL Code {item_gl_code_1}"):
        create_requisition_page.setting_item_gl_code(gl_code=item_gl_code_1)
        create_requisition_page.get_full_page_screenshot('requisition_first_item_gl_code')

    # Step 9: Add attachment from utils
    with allure.step(f"Step 9: Add attachment {attachment_path.name}"):
        assert create_requisition_page.upload_requisition_item_document(str(attachment_path)), \
            f"Attachment upload failed: {attachment_path.name}"
        first_item_attachment_name = attachment_path.name
        print("FIRST ITEM ATTACHMENT:", first_item_attachment_name)
        allure.attach(
            f"{attachment_path.name} ({attachment_size_mb:.2f} MB)",
            name="First item attachment",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_first_item_attachment')

    # Step 10: Add item remarks, click Add to grid and verify the item row
    with allure.step("Step 10: Add item remarks, click Add to grid and verify 1 item"):
        create_requisition_page.setting_item_remarks(item_remarks=requisition_item_remarks)
        create_requisition_page.add_item_requisition_details_information_list()
        first_item_grid_row = create_requisition_page.verify_grid_item(
            quantity=first_item_quantity,
            unit_price=first_item["unit_price"]
        )
        create_requisition_page.verify_grid_row_count(expected_count=1)
        allure.attach(
            first_item_grid_row,
            name="Requisition Detail Information List first item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_first_item_add_to_grid')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Whitelisted Blacklisted And Non-Agreement Items")
@allure.title("Test_case_2: Add blacklisted agreement item")
@allure.description("Test case 2: Add a second item to the requisition with a different master item and the first "
                    "item of the blacklisted Framework Agreement (quantity, GL code and attachment from .env).")
@pytest.mark.order(2)
def test_2_add_blacklisted_agreement_item(page):
    """
    Test Case 2: Add the second item from the blacklisted Framework Agreement.

    Steps:
        1. Search and select a different Item Information (master item 2).
        2. Click Check all active framework agreement and search the second Framework Agreement
           ('test_blacklisted_agreement_number') with Applicable For: Both. If not found, search again
           with HO, then HCMP.
        3. Select the first item of the blacklisted Framework Agreement and store it in 'second_item'.
        4. Enter the second item quantity from .env and store it in 'second_item_quantity'.
        5. Click Amount radio button, then Quantity radio button; verify Quantity is unchanged.
        6. Select a different GL Code (GL Code 2).
        7. Add attachment from utils (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX).
        8. Add item remarks (max 500 characters), click Add to grid and verify the requisition now has
           2 items.

    All scenario values are read from .env.
    """
    global second_item, second_item_applicable_for, second_item_quantity, second_item_attachment_name, \
        second_item_grid_row

    # First item comes from Test Case 1
    assert first_item, "Test Case 1 must pass first: first item is not added to the requisition"

    # All scenario values must come from .env
    required_env_values = {
        "test_blacklisted_agreement_number": blacklisted_agreement_number,
        "test_master_item_2": master_item_2,
        "test_master_item_2_full_path": master_item_2_full_path,
        "test_item_gl_code_2": item_gl_code_2,
        "test_requisition_item_2_quantity": requisition_item_2_quantity,
        "test_requisition_attachment_file_2": requisition_attachment_file_2,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    # Second agreement, master item and GL code must be different from the first item
    assert blacklisted_agreement_number != whitelisted_agreement_number, \
        "test_blacklisted_agreement_number must be different from test_whitelisted_agreement_number"
    assert master_item_2_full_path != master_item_1_full_path, \
        "test_master_item_2_full_path must be different from test_master_item_1_full_path"
    assert item_gl_code_2 != item_gl_code_1, "test_item_gl_code_2 must be different from test_item_gl_code_1"
    second_item_quantity = check_item_quantity("test_requisition_item_2_quantity", requisition_item_2_quantity)
    attachment_path_2, attachment_size_mb_2 = check_attachment("test_requisition_attachment_file_2",
                                                               requisition_attachment_file_2)

    create_requisition_page = CreateRequisition(page)

    # Step 1: Search and select a different Item Information (master item 2)
    with allure.step(f"Step 1: Search and select Item Information {master_item_2_full_path}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=master_item_2,
            item_info_2=master_item_2_full_path
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_information')

    # Step 2: Search the second Framework Agreement (Applicable For: Both, then HO/HCMP)
    with allure.step(f"Step 2: Search Active Framework Agreement {blacklisted_agreement_number}"):
        second_item_applicable_for = create_requisition_page.search_active_framework(
            agreement_number=blacklisted_agreement_number
        )
        allure.attach(
            f"{blacklisted_agreement_number} found with Applicable For: {second_item_applicable_for}",
            name="Second Framework Agreement search",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_framework_search')

    # Step 3: Select the first item of the blacklisted Framework Agreement
    with allure.step(f"Step 3: Select the first item of {blacklisted_agreement_number}"):
        second_item = create_requisition_page.select_first_active_framework_item(
            agreement_number=blacklisted_agreement_number
        )
        print("SECOND ITEM:", second_item)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in second_item.items())
            + f"\napplicable_for: {second_item_applicable_for}",
            name="Selected second agreement item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_selected')

    # Step 4: Enter the second item quantity from .env
    with allure.step(f"Step 4: Enter second item quantity {second_item_quantity}"):
        create_requisition_page.finalize_item_quantity(item_quantity=f"{second_item_quantity:.2f}")
        create_requisition_page.verify_item_quantity(expected_quantity=second_item_quantity)
        print("SECOND ITEM QUANTITY:", second_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_second_item_quantity')

    # Step 5: Click Amount, then Quantity radio button
    with allure.step("Step 5: Click Amount radio button, then Quantity radio button"):
        create_requisition_page.reset_cost_allocation_by_quantity()
        create_requisition_page.verify_item_quantity(expected_quantity=second_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_second_item_cost_allocation')

    # Step 6: Select a different GL Code
    with allure.step(f"Step 6: Select GL Code {item_gl_code_2}"):
        create_requisition_page.setting_item_gl_code(gl_code=item_gl_code_2)
        create_requisition_page.get_full_page_screenshot('requisition_second_item_gl_code')

    # Step 7: Add attachment from utils
    with allure.step(f"Step 7: Add attachment {attachment_path_2.name}"):
        assert create_requisition_page.upload_requisition_item_document(str(attachment_path_2)), \
            f"Attachment upload failed: {attachment_path_2.name}"
        second_item_attachment_name = attachment_path_2.name
        print("SECOND ITEM ATTACHMENT:", second_item_attachment_name)
        allure.attach(
            f"{attachment_path_2.name} ({attachment_size_mb_2:.2f} MB)",
            name="Second item attachment",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_attachment')

    # Step 8: Add item remarks, click Add to grid and verify 2 items
    with allure.step("Step 8: Add item remarks, click Add to grid and verify 2 items"):
        create_requisition_page.setting_item_remarks(item_remarks=requisition_item_remarks)
        create_requisition_page.add_item_requisition_details_information_list()
        second_item_grid_row = create_requisition_page.verify_grid_item(
            quantity=second_item_quantity,
            unit_price=second_item["unit_price"]
        )
        create_requisition_page.verify_grid_row_count(expected_count=2)
        allure.attach(
            second_item_grid_row,
            name="Requisition Detail Information List second item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_add_to_grid')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Whitelisted Blacklisted And Non-Agreement Items")
@allure.title("Test_case_3: Add non-agreement item")
@allure.description("Test case 3: Add a third item to the requisition without a Framework Agreement: master item 3 "
                    "with quantity, unit price, GL code and remarks from .env.")
@pytest.mark.order(3)
def test_3_add_non_agreement_item(page):
    """
    Test Case 3: Add the non-agreement item (no Framework Agreement).

    Steps:
        1. Search and select a different Item Information (master item 3).
        2. Enter the third item quantity from .env and store it in 'third_item_quantity'.
        3. Enter the unit price from .env ('test_requisition_non_agreement_unit_price').
        4. Select GL Code 3.
        5. Add item remarks (max 500 characters), click Add to grid and verify the item row
           (Quantity and Unit Price) and 3 items in the Requisition Detail Information List.

    All scenario values are read from .env.
    """
    global non_agreement_item, third_item_quantity, third_item_grid_row

    # Agreement items come from Test Case 1 and 2
    assert first_item and second_item, "Test Case 1 and 2 must pass first: agreement items are not added"

    # All scenario values must come from .env
    required_env_values = {
        "test_master_item_3": master_item_3,
        "test_master_item_3_full_path": master_item_3_full_path,
        "test_item_gl_code_3": item_gl_code_3,
        "test_requisition_item_3_quantity": requisition_item_3_quantity,
        "test_requisition_non_agreement_unit_price": requisition_non_agreement_unit_price,
        "test_requisition_item_remarks": requisition_item_remarks,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    # Third master item and GL code must be different from the agreement items
    assert master_item_3_full_path not in (master_item_1_full_path, master_item_2_full_path), \
        "test_master_item_3_full_path must be different from test_master_item_1/2_full_path"
    assert item_gl_code_3 not in (item_gl_code_1, item_gl_code_2), \
        "test_item_gl_code_3 must be different from test_item_gl_code_1/2"
    third_item_quantity = check_item_quantity("test_requisition_item_3_quantity", requisition_item_3_quantity)
    unit_price = check_item_quantity("test_requisition_non_agreement_unit_price", requisition_non_agreement_unit_price)

    create_requisition_page = CreateRequisition(page)

    # Step 1: Search and select Item Information (master item 3)
    with allure.step(f"Step 1: Search and select Item Information {master_item_3_full_path}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=master_item_3,
            item_info_2=master_item_3_full_path
        )
        create_requisition_page.get_full_page_screenshot('requisition_third_item_information')

    # Step 2: Enter the third item quantity from .env
    with allure.step(f"Step 2: Enter third item quantity {third_item_quantity}"):
        create_requisition_page.finalize_item_quantity(item_quantity=f"{third_item_quantity:.2f}")
        create_requisition_page.verify_item_quantity(expected_quantity=third_item_quantity)
        print("THIRD ITEM QUANTITY:", third_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_third_item_quantity')

    # Step 3: Enter the unit price from .env
    with allure.step(f"Step 3: Enter unit price {unit_price}"):
        create_requisition_page.finalize_item_unit_price(unit_price=f"{unit_price:.2f}")
        print("THIRD ITEM UNIT PRICE:", unit_price)
        create_requisition_page.get_full_page_screenshot('requisition_third_item_unit_price')

    # Step 4: Select GL Code 3
    with allure.step(f"Step 4: Select GL Code {item_gl_code_3}"):
        create_requisition_page.setting_item_gl_code(gl_code=item_gl_code_3)
        create_requisition_page.get_full_page_screenshot('requisition_third_item_gl_code')

    # Step 5: Add item remarks, click Add to grid and verify 3 items
    with allure.step("Step 5: Add item remarks, click Add to grid and verify 3 items"):
        create_requisition_page.setting_item_remarks(item_remarks=requisition_item_remarks)
        create_requisition_page.add_item_requisition_details_information_list()
        third_item_grid_row = create_requisition_page.verify_grid_item(
            quantity=third_item_quantity,
            unit_price=unit_price
        )
        create_requisition_page.verify_grid_row_count(expected_count=3)
        non_agreement_item = {
            "item_name": master_item_3_full_path,
            "unit_price": f"{unit_price:.2f}",
        }
        print("NON-AGREEMENT ITEM:", non_agreement_item)
        allure.attach(
            third_item_grid_row,
            name="Requisition Detail Information List third item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_third_item_add_to_grid')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Submit Requisition")
@allure.title("Test_case_4: Submit requisition with whitelisted, blacklisted and non-agreement items")
@allure.description("Test case 4: Set the delivery schedule and Central Store address, submit the requisition with "
                    "3 items and get the submission confirmation message and requisition number.")
@pytest.mark.order(4)
def test_4_submit_requisition(page):
    """
    Test Case 4: Submit the requisition with the 3 items.

    Steps:
        1. Set the same schedule (today).
        2. Set delivery location: Central Store and 'test_schedule_address'.
        3. Submit the requisition, get the submission confirmation message and store the
           requisition number in 'req_num'.

    All scenario values are read from .env.
    """
    global req_num, req_submission_message

    # Both items come from Test Case 1 and 2
    assert first_item and second_item and non_agreement_item, \
        "Test Case 1-3 must pass first: requisition items are not added"
    assert schedule_address, "Missing in .env: test_schedule_address"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Same schedule for today
    with allure.step("Step 1: Set same schedule (today)"):
        create_requisition_page.setting_same_schedule_for_date()
        create_requisition_page.get_full_page_screenshot('requisition_schedule')

    # Step 2: Delivery location (Central Store)
    with allure.step(f"Step 2: Set delivery location Central Store - {schedule_address}"):
        create_requisition_page.setting_location_for_central_store(address=schedule_address)
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
@allure.title("Test_case_5: Identify first approver")
@allure.description("Test case 5: Identify and capture the first approver of a submitted requisition.")
@pytest.mark.order(5)
def test_5_identify_first_approver(page):
    """
    Test Case 5: Identify and capture the first approver of the submitted requisition.

    Steps:
        1. Go to Requisition > Requisition List.
        2. Search the submitted requisition ('req_num').
        3. Get the first layer approver ID ('approver_id') and status ('req_status').
        4. Exit and log out from ERP.
    """
    global approver_id, req_status

    assert req_num, "Test Case 4 must pass first: no requisition number available"

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
@allure.title("Test_case_6: Approve requisition as first approver")
@allure.description(
    "Test case 6: Login as the first approver, approve the submitted requisition in the ERP Procurement system and "
    "get the approval confirmation message.")
@pytest.mark.order(6)
def test_6_approve_requisition_as_first_approver(page):
    """
    Test case 6: Login as the first approver and approve the submitted requisition.

    Steps:
        1. Log in to ERP as the first approver ('approver_id') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition, approve it and store the approval confirmation message
           in 'first_approval_message'.
        4. Exit and log out.
    """
    global first_approval_message
    assert req_num and approver_id, "Test case 5 must pass first: no requisition number/approver ID available"

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
    with allure.step(f"Step 3: Approve requisition {req_num} as first approver and get the confirmation message"):
        requisition_approve_list_page.select_requisition()
        first_approval_message = requisition_approve_list_page.approve_requisition_with_message()
        print(f"Requisition {req_num} approved by first approver: {approver_id}")
        print("FIRST APPROVAL MESSAGE:", first_approval_message)
        allure.attach(
            f"Requisition number: {req_num}\nApproved by first approver: {approver_id}\n"
            f"Approval confirmation message: {first_approval_message}",
            name="First layer approval",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_approve_list_page.get_full_page_screenshot('requisition_first_approver_approved')
        assert first_approval_message, f"No approval confirmation message shown for requisition {req_num}"
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_first_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Second Layer Approval")
@allure.title("Test_case_7: Identify second approver")
@allure.description(
    "Test case 7: Identify and capture the second-level approver of a submitted requisition in the ERP "
    "Procurement system.")
@pytest.mark.order(7)
def test_7_identify_second_approver(page):
    """
    Test case 7: Identify and capture the second-level approver of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List and search the requisition ('req_num').
        3. Get the second (final) layer approver ID ('approver_id_2') and status ('second_layer_req_status').
        4. Exit and log out.
    """
    global approver_id_2, second_layer_req_status
    assert req_num, "Test case 4 must pass first: no requisition number available"

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
@allure.title("Test_case_8: Approve requisition as final approver")
@allure.description(
    "Test case 8: Login as the second-level (final) approver, approve the submitted requisition in the ERP "
    "Procurement system and get the approval confirmation message.")
@pytest.mark.order(8)
def test_8_approve_requisition_as_final_approver(page):
    """
    Test case 8: Login as the second-level (final) approver and approve the requisition.

    Steps:
        1. Log in to ERP as the final approver ('approver_id_2') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition, approve it and store the approval confirmation message
           in 'final_approval_message'.
        4. Exit and log out.
    """
    global final_approval_message
    assert req_num and approver_id_2, "Test case 7 must pass first: no requisition number/second approver available"

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

    # Step 3: Select and approve the requisition, get the approval confirmation message
    with allure.step(f"Step 3: Approve requisition {req_num} as final approver and get the confirmation message"):
        requisition_approve_list_page.select_requisition()
        final_approval_message = requisition_approve_list_page.approve_requisition_with_message()
        print(f"Requisition {req_num} approved by final approver: {approver_id_2}")
        print("FINAL APPROVAL MESSAGE:", final_approval_message)
        allure.attach(
            f"Requisition number: {req_num}\nApproved by final approver: {approver_id_2}\n"
            f"Approval confirmation message: {final_approval_message}",
            name="Final layer approval",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_approve_list_page.get_full_page_screenshot('requisition_final_approver_approved')
        assert final_approval_message, f"No approval confirmation message shown for requisition {req_num}"
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_final_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Requisition Status")
@allure.title("Test_case_9: Requisition initiator gets approval status")
@allure.description(
    "Test case 9: Login as the requisition initiator, get the approval status of the requisition and verify the "
    "requisition details (whitelisted and blacklisted agreement items and the non-agreement item) and the "
    "agreement vendors.")
@pytest.mark.order(9)
def test_9_requisition_initiator_gets_approval_status(page, new_tab):
    """
    Test case 9: Requisition initiator gets the approval status of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List, search the requisition ('req_num') and get its approval status.
        3. Open the requisition details in a new tab and verify 1 item of each Framework Agreement
           with its master item, quantity and unit price.
        4. Open the FA No link of each Framework Agreement and verify each shows the vendor of its agreement item;
           store the whitelisted agreement vendor in 'order_vendor'.
        5. Close the tabs, exit and log out.
        6. Save the requisition result (whitelisted_blacklisted_nonagreement_requisition_result.json).
    """
    global approved_req_status, verified_requisition_details, agreement_vendors, order_vendor, requisition_result
    assert req_num, "Test case 4 must pass first: no requisition number available"
    assert first_item and second_item and non_agreement_item, \
        "Test case 1-3 must pass first: requisition items not available"

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

    # Master item codes, e.g. "[22245]" from "[22245]-Pen Box-(...)"
    master_item_1_code = re.search(r"\[[^\]]+\]", master_item_1_full_path).group(0)
    master_item_2_code = re.search(r"\[[^\]]+\]", master_item_2_full_path).group(0)
    master_item_3_code = re.search(r"\[[^\]]+\]", master_item_3_full_path).group(0)

    # Step 3: Open requisition details in a new tab and verify 1 item of each Framework Agreement
    with allure.step(f"Step 3: Verify requisition details of {req_num} (1 item of each Framework Agreement)"):
        details_tab = new_tab(lambda p: requisition_list_page.goto_requisition_details_information())
        requisition_details_page = RequisitionDetailsInformation(details_tab)

        requisition_details_page.verify_requisition_item_count(fa_no=whitelisted_agreement_number, expected_count=1)
        requisition_details_page.verify_requisition_item_count(fa_no=blacklisted_agreement_number, expected_count=1)
        first_item_details = requisition_details_page.verify_requisition_item(
            requisition_number=req_num,
            fa_no=whitelisted_agreement_number,
            item_code=master_item_1_code,
            quantity=first_item_quantity,
            unit_price=first_item["unit_price"]
        )
        second_item_details = requisition_details_page.verify_requisition_item(
            requisition_number=req_num,
            fa_no=blacklisted_agreement_number,
            item_code=master_item_2_code,
            quantity=second_item_quantity,
            unit_price=second_item["unit_price"]
        )
        third_item_details = requisition_details_page.verify_requisition_item_without_agreement(
            requisition_number=req_num,
            item_code=master_item_3_code,
            quantity=third_item_quantity,
            unit_price=non_agreement_item["unit_price"]
        )
        verified_requisition_details = {
            "first_item": first_item_details,
            "second_item": second_item_details,
            "third_item": third_item_details,
        }
        print("VERIFIED REQUISITION DETAILS:", verified_requisition_details)
        allure.attach(
            f"Requisition number: {req_num}\nStatus: {approved_req_status}\n"
            f"Item 1: {whitelisted_agreement_number}, {master_item_1_code}, quantity {first_item_quantity}, "
            f"unit price {first_item['unit_price']}\n  Details row: {first_item_details}\n"
            f"Item 2: {blacklisted_agreement_number}, {master_item_2_code}, quantity {second_item_quantity}, "
            f"unit price {second_item['unit_price']}\n  Details row: {second_item_details}\n"
            f"Item 3 (non-agreement): {master_item_3_code}, quantity {third_item_quantity}, "
            f"unit price {non_agreement_item['unit_price']}\n  Details row: {third_item_details}",
            name="Verified requisition details",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_details_page.get_full_page_screenshot('requisition_details_verified')

    # Step 4: Get the vendor of each different agreement in the requisition (first FA No link of each)
    with allure.step(f"Step 4: Get the vendors of {whitelisted_agreement_number} and "
                     f"{blacklisted_agreement_number} and verify them"):
        agreement_vendors = requisition_details_page.get_agreement_vendors()
        print("AGREEMENT VENDORS:", agreement_vendors)
        assert set(agreement_vendors) == {whitelisted_agreement_number, blacklisted_agreement_number}, \
            f"Expected agreements {whitelisted_agreement_number} and {blacklisted_agreement_number} " \
            f"in the requisition, found {list(agreement_vendors)}"
        order_vendor = agreement_vendors[whitelisted_agreement_number]
        print("ORDER VENDOR:", order_vendor)
        allure.attach(
            f"Whitelisted item vendor (Test case 1): {first_item['vendor_name']}\n"
            f"Blacklisted item vendor (Test case 2): {second_item['vendor_name']}\n"
            + "\n".join(f"{fa_no} vendor (FA No link): {vendor}" for fa_no, vendor in agreement_vendors.items()),
            name="Verified vendors",
            attachment_type=allure.attachment_type.TEXT
        )
        # Grid vendor has the vendor code, e.g. "[SU000723]- Walton Hi-Tech Industries PLC"
        for fa_no, item in ((whitelisted_agreement_number, first_item), (blacklisted_agreement_number, second_item)):
            assert agreement_vendors[fa_no].lower() in item["vendor_name"].lower(), \
                f"{fa_no} vendor '{agreement_vendors[fa_no]}' is not the same as its item vendor '{item['vendor_name']}'"

    # Step 5: Close the tabs, exit and log out
    with allure.step("Step 5: Close requisition details tab, exit and log out from ERP"):
        details_tab.close()
        page.bring_to_front()
        erp_logout(page, 'requisition_initiator_final_logout')

    # Step 6: Save the requisition result for an order creation test file
    with allure.step("Step 6: Save the requisition result"):
        requisition_result = {
            "requisition_number": req_num,
            "requisition_status": approved_req_status,
            "first_approval_message": first_approval_message,
            "final_approval_message": final_approval_message,
            "vendor": order_vendor,
            "final_approver": approver_id_2,
            "delivery_address": schedule_address,
            "items": [
                {
                    "agreement_number": whitelisted_agreement_number,
                    "agreement_version": first_item["fa_no"],
                    "item_code": first_item["item_code"],
                    "item_name": first_item["item_name"],
                    "master_item_code": master_item_1_code,
                    "specification": first_item["specification"],
                    "quantity": str(first_item_quantity),
                    "unit_price": first_item["unit_price"],
                    "attachment_name": first_item_attachment_name,
                },
                {
                    "agreement_number": blacklisted_agreement_number,
                    "agreement_version": second_item["fa_no"],
                    "item_code": second_item["item_code"],
                    "item_name": second_item["item_name"],
                    "master_item_code": master_item_2_code,
                    "specification": second_item["specification"],
                    "quantity": str(second_item_quantity),
                    "unit_price": second_item["unit_price"],
                    "attachment_name": second_item_attachment_name,
                },
                {
                    "agreement_number": "",
                    "item_name": non_agreement_item["item_name"],
                    "master_item_code": master_item_3_code,
                    "quantity": str(third_item_quantity),
                    "unit_price": non_agreement_item["unit_price"],
                },
            ],
        }
        save_result("whitelisted_blacklisted_nonagreement_requisition_result", requisition_result)
        print("REQUISITION RESULT:", requisition_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in requisition_result.items()),
            name="Saved requisition result",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.suite("Public Side")
@allure.feature("Active Requisition List")
@allure.story("Requisition Sync")
@allure.title("Test_case_10: Verify requisition sync to marketplace and ERP view")
@allure.description("Test case 10: Verify the approved requisition is synchronized to the Digital Marketplace, the "
                    "ERP View button opens the same requisition details in ERP staging, and store the Active "
                    "Requisition Product List rows.")
@pytest.mark.order(10)
def test_10_verify_requisition_sync_to_marketplace(page, new_tab):
    """
    Test Case 10: Verify Requisition Synchronization to Marketplace and the ERP View.

    Steps:
        1. Log in to the Digital Marketplace as 'proj_user' using SSO and verify the welcome message.
        2. Go to the Active Requisition List, search the requisition ('req_num') and verify its Total Budget
           and Remaining Budget are only the whitelisted item total (blacklisted and non-agreement items
           do not sync to the Digital Marketplace).
        3. Click the ERP View button: a new tab opens the ERP staging server. If it shows the ERP login page,
           log in as the same user (ResetHub link), close it and click ERP View again. Verify and match all
           requisition information (REQ. No, Status, Project Name, Source of Fund, Remarks, FA No and both
           item rows) with the created requisition and store it; close the ERP tab and go back to the
           Active Requisition List.
        4. Open the Active Requisition Product List in a new tab, verify 1 product(s) and store the product rows
           (Sub-Category, Product, FwA No.).
        No logout: Test case 11 and 11 continue on the Active Requisition Product List.

    All scenario values are read from .env.
    """
    global active_requisition_found, erp_requisition_information, product_list_tab, active_product_links
    assert req_num, "Test case 4 must pass first: no requisition number available"

    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_url": erp_url,
        "test_env": proj_env,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    active_requisition_list = ActiveRequisitionListPage(page)
    active_product_links = []

    # Step 1: Log in to the Digital Marketplace
    with allure.step(f"Step 1: Log in to the Digital Marketplace as {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=proj_user, pass_word=marketplace_password)
        print(f"Logging in to the Digital Marketplace as: {proj_user}")
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('marketplace_login')

    # Step 2: Active Requisition List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Active Requisition List and verify its budget"):
        home_page.go_to_active_requisition_list()
        active_requisition_list.search_order_requisition_number(requisition_number=req_num)
        active_requisition_found = True
        print(f"Requisition {req_num} found in Active Requisition List")
        allure.attach(
            f"Requisition number: {req_num}",
            name="Active requisition",
            attachment_type=allure.attachment_type.TEXT
        )
        # Marketplace budget is only for the whitelisted agreement item (quantity x unit price)
        requisition_budget = active_requisition_list.get_requisition_budget(requisition_number=req_num)
        whitelisted_total = (first_item_quantity * Decimal(first_item["unit_price"].replace(",", ""))).quantize(Decimal("0.01"))
        total_budget = Decimal(requisition_budget["total_budget"].replace(",", ""))
        remaining_budget = Decimal(requisition_budget["remaining_budget"].replace(",", ""))
        print("REQUISITION BUDGET:", requisition_budget, "| whitelisted item total:", whitelisted_total)
        allure.attach(
            f"Requisition number: {req_num}\nTotal Budget: {requisition_budget['total_budget']}\n"
            f"Remaining Budget: {requisition_budget['remaining_budget']}\n"
            f"Whitelisted item total (quantity {first_item_quantity} x unit price {first_item['unit_price']}): "
            f"{whitelisted_total}",
            name="Marketplace requisition budget (whitelisted item only)",
            attachment_type=allure.attachment_type.TEXT
        )
        active_requisition_list.get_full_page_screenshot('marketplace_active_requisition_search')
        assert total_budget == whitelisted_total, \
            f"Total Budget {total_budget} must be only the whitelisted item total {whitelisted_total}"
        assert remaining_budget == total_budget, \
            f"Remaining Budget {remaining_budget} must be the same as Total Budget {total_budget} (no order yet)"

    # Step 3: ERP View: ERP staging requisition details (log in as the same user when the ERP login page is shown)
    with allure.step(f"Step 3: Click ERP View of {req_num}, match the ERP requisition details and go back"):
        erp_tab = active_requisition_list.open_erp_view(requisition_number=req_num)
        erp_tab.wait_for_url(lambda url: urlparse(url).netloc == urlparse(erp_url).netloc, timeout=60000)
        erp_details_page = RequisitionDetailsInformation(erp_tab)
        if erp_details_page.is_erp_login_page():
            print(f"ERP login page shown: logging in as {proj_user} with the ResetHub link")
            erp_details_page.get_full_page_screenshot('marketplace_erp_view_login_page')
            reset_page = ResetHubPage(erp_tab)
            link = reset_page.generate_reset_link(env=proj_env, username=proj_user)
            reset_page.open_generated_link(link)
            assert isinstance(link, str) and link.startswith("http")
            erp_tab.close()
            page.bring_to_front()
            erp_tab = active_requisition_list.open_erp_view(requisition_number=req_num)
            erp_tab.wait_for_url(lambda url: urlparse(url).netloc == urlparse(erp_url).netloc, timeout=60000)
            erp_details_page = RequisitionDetailsInformation(erp_tab)
            assert not erp_details_page.is_erp_login_page(), \
                f"ERP View still shows the ERP login page after logging in as {proj_user}"
        erp_requisition_information = erp_details_page.get_requisition_information()
        erp_requisition_information["erp_url"] = erp_tab.url
        print("ERP REQUISITION INFORMATION:", erp_requisition_information)
        erp_details_page.get_full_page_screenshot('marketplace_erp_view_requisition_details')

        # The ERP requisition must match the created requisition (Test case 1-9)
        master_item_1_code = re.search(r"\[[^\]]+\]", master_item_1_full_path).group(0)
        master_item_2_code = re.search(r"\[[^\]]+\]", master_item_2_full_path).group(0)
        master_item_3_code = re.search(r"\[[^\]]+\]", master_item_3_full_path).group(0)
        erp_checks = [
            ("REQ. No", req_num, erp_requisition_information["req_no"],
             erp_requisition_information["req_no"] == req_num),
            ("Status", "Approved", erp_requisition_information["status"],
             "approved" in erp_requisition_information["status"].lower()),
            ("Project Name", requisition_project_name, erp_requisition_information["project_name"],
             without_spaces(requisition_project_name) in without_spaces(erp_requisition_information["project_name"])),
            ("Source of Fund", requisition_funding_source, erp_requisition_information["source_of_fund"],
             without_spaces(requisition_funding_source) in without_spaces(erp_requisition_information["source_of_fund"])),
            ("Remarks", requisition_funding_remarks, erp_requisition_information["remarks"],
             erp_requisition_information["remarks"] == " ".join(requisition_funding_remarks.split())),
            ("FA No", [whitelisted_agreement_number, blacklisted_agreement_number], erp_requisition_information["agreement_numbers"],
             set(erp_requisition_information["agreement_numbers"]) == {whitelisted_agreement_number, blacklisted_agreement_number}),
        ]
        erp_details_page.verify_requisition_item_count(fa_no=whitelisted_agreement_number, expected_count=1)
        erp_details_page.verify_requisition_item_count(fa_no=blacklisted_agreement_number, expected_count=1)
        erp_requisition_information["items"] = [
            erp_details_page.verify_requisition_item(
                requisition_number=req_num, fa_no=whitelisted_agreement_number, item_code=master_item_1_code,
                quantity=first_item_quantity, unit_price=first_item["unit_price"]),
            erp_details_page.verify_requisition_item(
                requisition_number=req_num, fa_no=blacklisted_agreement_number, item_code=master_item_2_code,
                quantity=second_item_quantity, unit_price=second_item["unit_price"]),
            erp_details_page.verify_requisition_item_without_agreement(
                requisition_number=req_num, item_code=master_item_3_code,
                quantity=third_item_quantity, unit_price=non_agreement_item["unit_price"]),
        ]
        erp_checks.append(("Requisition Details rows", 3, len(erp_requisition_information["items"]), True))
        allure.attach(
            "\n".join(f"{check}: expected {expected} | actual {actual} | {'PASS' if passed else 'FAIL'}"
                      for check, expected, actual, passed in erp_checks)
            + "\n" + "\n".join(f"Item {index + 1}: {row}" for index, row in enumerate(erp_requisition_information["items"])),
            name="ERP requisition details (ERP View) vs created requisition",
            attachment_type=allure.attachment_type.TEXT
        )
        failed_checks = [f"{check}: expected {expected}, found {actual}"
                         for check, expected, actual, passed in erp_checks if not passed]
        assert not failed_checks, "ERP requisition details do not match the created requisition:\n" + "\n".join(failed_checks)

        # Close the ERP tab and go back to the Active Requisition List
        erp_tab.close()
        page.bring_to_front()
        active_requisition_list.verify_requisition_in_list(requisition_number=req_num)
        active_requisition_list.get_full_page_screenshot('marketplace_back_to_active_requisition_list')

    # Step 4: Active Requisition Product List and its product rows (no product switch history here)
    with allure.step(f"Step 4: Open product list of {req_num} and store the Active Requisition Product List rows"):
        product_list_tab = new_tab(lambda p: active_requisition_list.goto_active_requisition_product_list())
        active_requisition_product_list = ActiveRequisitionProductList(product_list_tab)
        active_requisition_product_list.get_full_page_screenshot('marketplace_active_requisition_product_list')
        product_rows = active_requisition_product_list.get_product_rows()
        print("ACTIVE REQUISITION PRODUCTS:", len(product_rows))
        assert len(product_rows) == 1, f"Expected 1 product(s) in the Active Requisition Product List, found {len(product_rows)}"
        for row in product_rows:
            active_product_links.append({
                "sub_category": active_requisition_product_list.cell_text(row["Sub-Category"]),
                "product": active_requisition_product_list.cell_text(row["Product"]),
                "fwa_no": active_requisition_product_list.cell_text(row["FwA No."]),
            })
        print("ACTIVE REQUISITION PRODUCT ROWS:", active_product_links)
        # Only the whitelisted agreement item syncs (blacklisted and non-agreement items do not)
        assert active_product_links[0]["fwa_no"].startswith(whitelisted_agreement_number), \
            f"The synced product must be the whitelisted agreement item {whitelisted_agreement_number}, " \
            f"found FwA No. '{active_product_links[0]['fwa_no']}'"
        allure.attach(
            "\n".join(f"Product {index + 1}: Sub-Category {product['sub_category']} | Product {product['product']} | "
                      f"FwA No. {product['fwa_no']}" for index, product in enumerate(active_product_links)),
            name="Active Requisition Product List rows",
            attachment_type=allure.attachment_type.TEXT
        )


def check_fwa_attachment(attachment):
    # Available: the attachment is shown/downloaded; not available: ERP staging page with a message
    if not attachment["available"]:
        assert urlparse(attachment["attachment_url"]).netloc == urlparse(erp_url).netloc, \
            f"FwA {attachment['fwa_no']} did not open the ERP staging server: {attachment['attachment_url']}"
        assert attachment["message"], f"FwA {attachment['fwa_no']}: no message shown on the ERP page"


@allure.suite("Public Side")
@allure.feature("Active Requisition Product List")
@allure.story("Product List Links")
@allure.title("Test_case_11: Verify Active Requisition Product List links")
@allure.description("Test case 11: For every product of the requisition, open the Sub-Category link and come back, "
                    "store the product name ('item name - delivery location', not clicked), and open the FwA No. "
                    "attachment (or verify the ERP staging message when the attachment is not available).")
@pytest.mark.order(11)
def test_11_verify_active_requisition_product_list_links(page):
    """
    Test Case 11: Verify the Sub-Category, Product and FwA No. links of the Active Requisition Product List.
    Continues on the Active Requisition Product List of Test case 10 (no new login).

    Steps:
        1. Sub-Category link of every product: open it, store the sub-category, go back to the list.
        2. Product name of every product: stored ("item name - delivery location"), not clicked; it is verified on
           the next pages (shopping cart, checkout, order details, approval, vendor and receive pages).
        3. FwA No. link of every product: if the agreement attachment is available, open/download it;
           if not, verify the new tab is the ERP staging server with a message, close it and come back.
        No logout: Test case 12 continues on the Active Requisition Product List.

    All scenario values are read from .env.
    """
    assert active_product_links and product_list_tab, \
        "Test case 10 must pass first: Active Requisition Product List not available"
    assert erp_url, "Missing in .env: test_url"

    product_list_page = ActiveRequisitionProductList(product_list_tab)

    # Step 1: Sub-Category link of every product
    with allure.step("Step 1: Open the Sub-Category link of every product and come back"):
        for index, product in enumerate(active_product_links):
            with allure.step(f"Product {index + 1}: Sub-Category {product['sub_category']}"):
                opened = product_list_page.open_link_and_back(
                    product_list_page.get_product_rows()[index]["Sub-Category"],
                    back_page_table=product_list_page.product_list_table,
                    screenshot_name=f'product_links_sub_category_{index + 1}'
                )
                product["sub_category_url"] = opened["opened_url"]
                print(f"SUB-CATEGORY {index + 1}:", product["sub_category"], opened["opened_url"])

    # Step 2: Product name of every product: stored, not clicked (user rule)
    with allure.step("Step 2: Store the product name of every product (not clicked)"):
        for index, product in enumerate(active_product_links):
            print(f"PRODUCT NAME {index + 1}:", product["product"])
        allure.attach("\n".join(f"Product {index + 1}: {product['product']}" for index, product in enumerate(active_product_links)),
                      name="Product names (item name - delivery location)", attachment_type=allure.attachment_type.TEXT)
        assert all(product["product"] for product in active_product_links), "A product name is not shown"

    # Step 3: FwA No. link of every product (attachment or ERP staging message)
    with allure.step("Step 3: Open the FwA No. attachment of every product"):
        for index, product in enumerate(active_product_links):
            with allure.step(f"Product {index + 1}: FwA No. {product['fwa_no'] or '(non-agreement item)'}"):
                if not product["fwa_no"]:
                    # Non-agreement item: no Framework Agreement, so no FwA No. link
                    product["fwa_attachment"] = {"available": False, "file_name": "",
                                                 "message": "Non-agreement item: no FwA No."}
                    print(f"FWA {index + 1}: non-agreement item, no FwA No.")
                    continue
                attachment = product_list_page.open_fwa_attachment(
                    product_list_page.get_product_rows()[index]["FwA No."],
                    screenshot_name=f'product_links_fwa_{index + 1}'
                )
                check_fwa_attachment(attachment)
                product["fwa_attachment"] = attachment
                print(f"FWA {index + 1}:", attachment)
        allure.attach(
            "\n".join(f"Product {index + 1}: Sub-Category {product['sub_category']} | Product {product['product']} | "
                      f"FwA No. {product['fwa_no']} | attachment "
                      f"{'available: ' + product['fwa_attachment']['file_name'] if product['fwa_attachment']['available'] else 'not available: ' + product['fwa_attachment']['message']}"
                      for index, product in enumerate(active_product_links)),
            name="Active Requisition Product List links",
            attachment_type=allure.attachment_type.TEXT
        )
        product_list_page.get_full_page_screenshot('product_links_done')


@allure.suite("Public Side")
@allure.feature("Product Switch History")
@allure.story("Product Switch History Links")
@allure.title("Test_case_12: Verify Product Switch History links")
@allure.description("Test case 12: For every product, open its Product Switch History, verify the product name and "
                    "FwA No. are the same as the Active Requisition Product List (product name not clicked), open "
                    "the FwA No. attachment (or verify the ERP staging message), go back to the product list, then log "
                    "out and save the requisition result with the marketplace data.")
@pytest.mark.order(12)
def test_12_verify_product_switch_history_links(page):
    """
    Test Case 12: Verify the Product Switch History of every product.
    Continues on the Active Requisition Product List of Test case 10 and 10 (no new login).

    Steps (for every product):
        1. Click History; store the Product Switch History rows (Product Name, Specification, Unit Price,
           FwA No., Vendor Name, Date) and verify the product name and FwA No. are the same as the
           Active Requisition Product List.
        2. Product Name: verified as stored (not clicked).
        3. FwA No. link: if the agreement attachment is available, open/download it; if not, verify the
           new tab is the ERP staging server with a message, close it and come back.
        4. Click Back to Requisition Product List.
    Then close the product list tab, log out and save the requisition result with the marketplace data.

    All scenario values are read from .env.
    """
    global product_switch_history, requisition_result
    assert active_product_links and product_list_tab, \
        "Test case 10 must pass first: Active Requisition Product List not available"
    assert erp_url, "Missing in .env: test_url"

    product_list_page = ActiveRequisitionProductList(product_list_tab)
    history_page = ProductSwitchHistory(product_list_tab)
    product_switch_history = []

    for index, product in enumerate(active_product_links):
        with allure.step(f"Step {index + 1}: Product Switch History of product {index + 1} ({product['product']})"):
            # History of the product: rows, same product name and FwA No. as the product list
            product_list_page.view_product_switch_history_by_index(index)
            history_rows = history_page.get_history_rows()
            history = [{title: history_page.cell_text(cell) for title, cell in row.items()} for row in history_rows]
            print(f"PRODUCT SWITCH HISTORY {index + 1}:", history)
            history_page.get_full_page_screenshot(f'product_switch_history_{index + 1}')
            assert any(row["Product Name"] == product["product"] for row in history), \
                f"Product '{product['product']}' not found in its Product Switch History: {history}"
            if product["fwa_no"]:
                assert any(row["FwA No."] == product["fwa_no"] for row in history), \
                    f"FwA No. '{product['fwa_no']}' not found in its Product Switch History: {history}"


            # FwA No. link of the history (attachment or ERP staging message); none for the non-agreement item
            if product["fwa_no"]:
                attachment = history_page.open_fwa_attachment(
                    history_page.get_history_rows()[0]["FwA No."],
                    screenshot_name=f'product_switch_history_fwa_{index + 1}'
                )
                check_fwa_attachment(attachment)
            else:
                attachment = {"available": False, "file_name": "", "message": "Non-agreement item: no FwA No."}

            product_switch_history.append({
                "product": product["product"],
                "history": history,
                "fwa_attachment": attachment,
            })
            allure.attach(
                "\n".join(" | ".join(f"{title}: {value}" for title, value in row.items()) for row in history)
                + f"\nFwA attachment: {'available: ' + attachment['file_name'] if attachment['available'] else 'not available: ' + attachment['message']}",
                name=f"Product Switch History {index + 1}",
                attachment_type=allure.attachment_type.TEXT
            )

            # Back to Requisition Product List
            product_list_page.go_to_product_history()
            product_list_tab.wait_for_load_state("domcontentloaded")
            assert len(product_list_page.get_product_rows()) == len(active_product_links), \
                "Back to Requisition Product List did not show the product list"

    # Close the product list tab, log out and save the marketplace data with the requisition result
    with allure.step(f"Step {len(active_product_links) + 1}: Close the product list tab, log out and save the requisition result"):
        product_list_tab.close()
        page.bring_to_front()
        MainNavigationMenu(page).perform_logout()
        HomePage(page).get_full_page_screenshot('marketplace_logout')
        assert requisition_result, "Test case 9 must pass first: requisition result not available"
        requisition_result["erp_view"] = erp_requisition_information
        requisition_result["active_requisition_products"] = active_product_links
        requisition_result["product_switch_history"] = product_switch_history
        save_result("whitelisted_blacklisted_nonagreement_requisition_result", requisition_result)
        print("REQUISITION RESULT (with marketplace data):", requisition_result)
