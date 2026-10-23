from dotenv import load_dotenv
import os
import re
import string
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
whitelisted_agreement_number = os.getenv("test_whitelisted_agreement_number")
requisition_project_name = os.getenv("test_requisition_project_name")
requisition_funding_source = os.getenv("test_requisition_funding_source")
requisition_funding_remarks = os.getenv("test_requisition_funding_remarks")
# Head Office delivery location
schedule_address = os.getenv("test_schedule_address")

# Requisition items: item N = row N of the whitelisted agreement, master item N, GL code N, quantity N,
# a different attachment type (item 8: no attachment) and item remarks (item 8: 500 characters with all
# special characters). All values are .env keys.
REQUISITION_ITEMS = [
    {"number": 1, "attachment_type": "PDF", "attachment_key": "test_requisition_attachment_file",
     "remarks_key": "test_requisition_item_remarks"},
    {"number": 2, "attachment_type": "JPG", "attachment_key": "test_requisition_attachment_file_jpg",
     "remarks_key": "test_requisition_item_remarks"},
    {"number": 3, "attachment_type": "PNG", "attachment_key": "test_requisition_attachment_file_png",
     "remarks_key": "test_requisition_item_remarks"},
    {"number": 4, "attachment_type": "XLS", "attachment_key": "test_requisition_attachment_file_xls",
     "remarks_key": "test_requisition_item_remarks"},
    {"number": 5, "attachment_type": "PPTX", "attachment_key": "test_requisition_attachment_file_pptx",
     "remarks_key": "test_requisition_item_remarks"},
    {"number": 6, "attachment_type": "DOCX", "attachment_key": "test_requisition_attachment_file_2",
     "remarks_key": "test_requisition_item_remarks"},
    {"number": 7, "attachment_type": "ZIP", "attachment_key": "test_requisition_attachment_file_zip",
     "remarks_key": "test_requisition_item_remarks"},
    {"number": 8, "attachment_type": "No attachment", "attachment_key": None,
     "remarks_key": "test_requisition_item_remarks_500"},
]
for requisition_item in REQUISITION_ITEMS:
    item_number = requisition_item["number"]
    requisition_item["master_item_key"] = f"test_master_item_{item_number}"
    requisition_item["master_item_full_path_key"] = f"test_master_item_{item_number}_full_path"
    requisition_item["gl_code_key"] = f"test_item_gl_code_{item_number}"
    requisition_item["quantity_key"] = f"test_requisition_item_{item_number}_quantity"

# Attachment and remarks rules
UTILS_DIR = Path(__file__).resolve().parents[3] / "utils"
ALLOWED_ATTACHMENT_TYPES = {".docx", ".pdf", ".xls", ".jpg", ".png", ".ppt", ".zip", ".pptx"}
MAX_ATTACHMENT_SIZE_MB = 20
MAX_REQUISITION_REMARKS_LENGTH = 300
MAX_ITEM_REMARKS_LENGTH = 500

# Procurement global variable
# Added requisition items (item name with code, master item, attachment, remarks, quantity, ...)
added_items = []
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
order_vendor = ''
# Requisition result for the order creation journey
requisition_result = {}

# Marketplace global variable
active_requisition_found = False
# Active Requisition Product List rows/links and Product Switch History
# ERP requisition details opened from the ERP View button
erp_requisition_information = {}
product_list_tab = None
active_product_links = []
product_switch_history = []


def env_value(env_name):
    value = os.getenv(env_name)
    assert value, f"Missing in .env: {env_name}"
    return value


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


def check_item_remarks(env_name, remarks):
    # Item remarks: max 500 characters; the 500 character remarks must also have all special characters
    assert len(remarks) <= MAX_ITEM_REMARKS_LENGTH, \
        f"{env_name} must be max {MAX_ITEM_REMARKS_LENGTH} characters, found {len(remarks)}"
    if env_name == "test_requisition_item_remarks_500":
        assert len(remarks) == MAX_ITEM_REMARKS_LENGTH, \
            f"{env_name} must be exactly {MAX_ITEM_REMARKS_LENGTH} characters, found {len(remarks)}"
        missing_special_characters = [character for character in string.punctuation if character not in remarks]
        assert not missing_special_characters, \
            f"{env_name} must contain all special characters, missing: {missing_special_characters}"


def read_item_values(requisition_item):
    # All values of one requisition item from .env, checked before the item is added
    item_values = {
        "number": requisition_item["number"],
        "attachment_type": requisition_item["attachment_type"],
        "master_item": env_value(requisition_item["master_item_key"]),
        "master_item_full_path": env_value(requisition_item["master_item_full_path_key"]),
        "gl_code": env_value(requisition_item["gl_code_key"]),
        "quantity": check_item_quantity(requisition_item["quantity_key"], env_value(requisition_item["quantity_key"])),
        "remarks": env_value(requisition_item["remarks_key"]),
        "attachment_path": None,
        "attachment_size_mb": 0,
    }
    check_item_remarks(requisition_item["remarks_key"], item_values["remarks"])
    if requisition_item["attachment_key"]:
        item_values["attachment_path"], item_values["attachment_size_mb"] = check_attachment(
            requisition_item["attachment_key"], env_value(requisition_item["attachment_key"]))
    return item_values


def add_requisition_item(create_requisition_page, requisition_item):
    # Add one item: master item, agreement item of the same row number, quantity, GL code, attachment, remarks
    item_values = read_item_values(requisition_item)
    item_number = item_values["number"]

    with allure.step(f"Item {item_number}: Search and select Item Information {item_values['master_item_full_path']}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=item_values["master_item"],
            item_info_2=item_values["master_item_full_path"]
        )
        create_requisition_page.get_full_page_screenshot(f'requisition_item_{item_number}_information')

    with allure.step(f"Item {item_number}: Search Active Framework Agreement {whitelisted_agreement_number} "
                     f"and select item row {item_number}"):
        applicable_for = create_requisition_page.search_active_framework(agreement_number=whitelisted_agreement_number)
        agreement_item = create_requisition_page.select_active_framework_item_by_row(
            agreement_number=whitelisted_agreement_number,
            row_number=item_number
        )
        print(f"ITEM {item_number} AGREEMENT ITEM:", agreement_item)
        create_requisition_page.get_full_page_screenshot(f'requisition_item_{item_number}_selected')

    with allure.step(f"Item {item_number}: Enter quantity {item_values['quantity']}, then Amount and Quantity radio"):
        create_requisition_page.finalize_item_quantity(item_quantity=f"{item_values['quantity']:.2f}")
        create_requisition_page.verify_item_quantity(expected_quantity=item_values["quantity"])
        create_requisition_page.reset_cost_allocation_by_quantity()
        create_requisition_page.verify_item_quantity(expected_quantity=item_values["quantity"])
        create_requisition_page.get_full_page_screenshot(f'requisition_item_{item_number}_quantity')

    with allure.step(f"Item {item_number}: Select GL Code {item_values['gl_code']}"):
        create_requisition_page.setting_item_gl_code(gl_code=item_values["gl_code"])
        create_requisition_page.get_full_page_screenshot(f'requisition_item_{item_number}_gl_code')

    attachment_path = item_values["attachment_path"]
    with allure.step(f"Item {item_number}: {item_values['attachment_type']} attachment "
                     f"{attachment_path.name if attachment_path else '(none)'}"):
        if attachment_path:
            assert create_requisition_page.upload_requisition_item_document(str(attachment_path)), \
                f"Attachment upload failed: {attachment_path.name}"
            create_requisition_page.get_full_page_screenshot(f'requisition_item_{item_number}_attachment')
        print(f"ITEM {item_number} ATTACHMENT:", attachment_path.name if attachment_path else "-")

    with allure.step(f"Item {item_number}: Add item remarks ({len(item_values['remarks'])} characters), "
                     f"click Add to grid and verify the item row"):
        create_requisition_page.setting_item_remarks(item_remarks=item_values["remarks"])
        create_requisition_page.add_item_requisition_details_information_list()
        grid_row = create_requisition_page.verify_grid_item(
            quantity=item_values["quantity"],
            unit_price=agreement_item["unit_price"]
        )
        create_requisition_page.verify_grid_row_count(expected_count=item_number)
        create_requisition_page.get_full_page_screenshot(f'requisition_item_{item_number}_add_to_grid')

    added_item = {
        "number": item_number,
        "agreement_version": agreement_item["fa_no"],
        "applicable_for": applicable_for,
        "vendor_name": agreement_item["vendor_name"],
        "item_name": agreement_item["item_name"],
        "item_code": agreement_item["item_code"],
        "specification": agreement_item["specification"],
        "unit_price": agreement_item["unit_price"],
        "master_item": item_values["master_item_full_path"],
        "master_item_code": re.search(r"\[[^\]]+\]", item_values["master_item_full_path"]).group(0),
        "gl_code": item_values["gl_code"],
        "quantity": str(item_values["quantity"]),
        "attachment_type": item_values["attachment_type"],
        "attachment_name": attachment_path.name if attachment_path else "",
        "remarks": item_values["remarks"],
        "grid_row": grid_row,
    }
    added_items.append(added_item)
    allure.attach(
        "\n".join(f"{key}: {value}" for key, value in added_item.items()),
        name=f"Requisition item {item_number}",
        attachment_type=allure.attachment_type.TEXT
    )
    return added_item


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
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_1: Create requisition with first item and PDF attachment")
@allure.description("Test case 1: Login to the ERP Procurement system and create a requisition with the first item "
                    "(master item 1, row 1 of the whitelisted Framework Agreement, PDF attachment and item remarks "
                    "from .env).")
@pytest.mark.order(1)
def test_1_create_requisition_with_first_item_and_pdf_attachment(page):
    """
    Test Case 1: Create Requisition in ERP with the first item and a PDF attachment.

    Steps:
        1. Log in to ERP (ResetHub link) and open
           Procurement > Requisition > Create Requisition.
        2. Select Head Office, Project, Source of Fund and enter Remarks (max 300 characters).
        3. Add item 1: master item 1, search the whitelisted Framework Agreement (Applicable For: Both, then
           HO/HCMP) and select its row 1, quantity 1, Amount then Quantity radio button, GL Code 1,
           PDF attachment, item remarks; Add to grid and verify the item row and 1 item.

    All scenario values are read from .env.
    """
    added_items.clear()

    # All scenario values must come from .env
    required_env_values = {
        "test_env": proj_env,
        "test_user_name": proj_user,
        "test_whitelisted_agreement_number": whitelisted_agreement_number,
        "test_requisition_project_name": requisition_project_name,
        "test_requisition_funding_source": requisition_funding_source,
        "test_requisition_funding_remarks": requisition_funding_remarks,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    assert len(requisition_funding_remarks) <= MAX_REQUISITION_REMARKS_LENGTH, \
        f"test_requisition_funding_remarks must be max {MAX_REQUISITION_REMARKS_LENGTH} characters, " \
        f"found {len(requisition_funding_remarks)}"
    # All 8 items' .env values are checked before logging in
    for requisition_item in REQUISITION_ITEMS:
        read_item_values(requisition_item)

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

    # Step 3: Item 1 with PDF attachment
    with allure.step("Step 3: Add item 1 (row 1 of the agreement, PDF attachment) and verify 1 item"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[0])


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_2: Add item 2 with JPG attachment")
@allure.description("Test case 2: Add item 2 to the requisition (master item 2, row 2 of the "
                    "whitelisted Framework Agreement, quantity, GL code, JPG attachment and "
                    "item remarks from .env).")
@pytest.mark.order(2)
def test_2_add_item_2_jpg_attachment(page):
    """
    Test Case 2: Add item 2 with JPG attachment.

    Steps:
        1. Add item 2: master item 2, search the whitelisted Framework Agreement (Applicable For: Both,
           then HO/HCMP) and select its row 2, quantity 2, Amount then Quantity radio button,
           GL Code 2, JPG attachment, item remarks; Add to grid and verify the item row
           and 2 items.

    All scenario values are read from .env.
    """
    assert len(added_items) == 1, "Test Case 1 must pass first: item 1 is not added to the requisition"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Item 2 (JPG)
    with allure.step("Step 1: Add item 2 (row 2 of the agreement, JPG attachment) and verify 2 items"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[1])


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_3: Add item 3 with PNG attachment")
@allure.description("Test case 3: Add item 3 to the requisition (master item 3, row 3 of the "
                    "whitelisted Framework Agreement, quantity, GL code, PNG attachment and "
                    "item remarks from .env).")
@pytest.mark.order(3)
def test_3_add_item_3_png_attachment(page):
    """
    Test Case 3: Add item 3 with PNG attachment.

    Steps:
        1. Add item 3: master item 3, search the whitelisted Framework Agreement (Applicable For: Both,
           then HO/HCMP) and select its row 3, quantity 3, Amount then Quantity radio button,
           GL Code 3, PNG attachment, item remarks; Add to grid and verify the item row
           and 3 items.

    All scenario values are read from .env.
    """
    assert len(added_items) == 2, "Test Case 2 must pass first: item 2 is not added to the requisition"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Item 3 (PNG)
    with allure.step("Step 1: Add item 3 (row 3 of the agreement, PNG attachment) and verify 3 items"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[2])


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_4: Add item 4 with XLS (Excel) attachment")
@allure.description("Test case 4: Add item 4 to the requisition (master item 4, row 4 of the "
                    "whitelisted Framework Agreement, quantity, GL code, XLS attachment and "
                    "item remarks from .env).")
@pytest.mark.order(4)
def test_4_add_item_4_xls_attachment(page):
    """
    Test Case 4: Add item 4 with XLS (Excel) attachment.

    Steps:
        1. Add item 4: master item 4, search the whitelisted Framework Agreement (Applicable For: Both,
           then HO/HCMP) and select its row 4, quantity 4, Amount then Quantity radio button,
           GL Code 4, XLS attachment, item remarks; Add to grid and verify the item row
           and 4 items.

    All scenario values are read from .env.
    """
    assert len(added_items) == 3, "Test Case 3 must pass first: item 3 is not added to the requisition"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Item 4 (XLS)
    with allure.step("Step 1: Add item 4 (row 4 of the agreement, XLS attachment) and verify 4 items"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[3])


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_5: Add item 5 with PPTX attachment")
@allure.description("Test case 5: Add item 5 to the requisition (master item 5, row 5 of the "
                    "whitelisted Framework Agreement, quantity, GL code, PPTX attachment and "
                    "item remarks from .env).")
@pytest.mark.order(5)
def test_5_add_item_5_pptx_attachment(page):
    """
    Test Case 5: Add item 5 with PPTX attachment.

    Steps:
        1. Add item 5: master item 5, search the whitelisted Framework Agreement (Applicable For: Both,
           then HO/HCMP) and select its row 5, quantity 5, Amount then Quantity radio button,
           GL Code 5, PPTX attachment, item remarks; Add to grid and verify the item row
           and 5 items.

    All scenario values are read from .env.
    """
    assert len(added_items) == 4, "Test Case 4 must pass first: item 4 is not added to the requisition"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Item 5 (PPTX)
    with allure.step("Step 1: Add item 5 (row 5 of the agreement, PPTX attachment) and verify 5 items"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[4])


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_6: Add item 6 with DOCX attachment")
@allure.description("Test case 6: Add item 6 to the requisition (master item 6, row 6 of the "
                    "whitelisted Framework Agreement, quantity, GL code, DOCX attachment and "
                    "item remarks from .env).")
@pytest.mark.order(6)
def test_6_add_item_6_docx_attachment(page):
    """
    Test Case 6: Add item 6 with DOCX attachment.

    Steps:
        1. Add item 6: master item 6, search the whitelisted Framework Agreement (Applicable For: Both,
           then HO/HCMP) and select its row 6, quantity 6, Amount then Quantity radio button,
           GL Code 6, DOCX attachment, item remarks; Add to grid and verify the item row
           and 6 items.

    All scenario values are read from .env.
    """
    assert len(added_items) == 5, "Test Case 5 must pass first: item 5 is not added to the requisition"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Item 6 (DOCX)
    with allure.step("Step 1: Add item 6 (row 6 of the agreement, DOCX attachment) and verify 6 items"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[5])


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_7: Add item 7 with ZIP attachment")
@allure.description("Test case 7: Add item 7 to the requisition (master item 7, row 7 of the "
                    "whitelisted Framework Agreement, quantity, GL code, ZIP attachment and "
                    "item remarks from .env).")
@pytest.mark.order(7)
def test_7_add_item_7_zip_attachment(page):
    """
    Test Case 7: Add item 7 with ZIP attachment.

    Steps:
        1. Add item 7: master item 7, search the whitelisted Framework Agreement (Applicable For: Both,
           then HO/HCMP) and select its row 7, quantity 7, Amount then Quantity radio button,
           GL Code 7, ZIP attachment, item remarks; Add to grid and verify the item row
           and 7 items.

    All scenario values are read from .env.
    """
    assert len(added_items) == 6, "Test Case 6 must pass first: item 6 is not added to the requisition"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Item 7 (ZIP)
    with allure.step("Step 1: Add item 7 (row 7 of the agreement, ZIP attachment) and verify 7 items"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[6])


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Item Remarks And Attachment Upload")
@allure.title("Test_case_8: Add item 8 without attachment and 500 character remarks")
@allure.description("Test case 8: Add item 8 to the requisition (master item 8, row 8 of the "
                    "whitelisted Framework Agreement, quantity, GL code, no attachment and "
                    "500 character remarks with all special characters from .env).")
@pytest.mark.order(8)
def test_8_add_item_8_no_attachment_and_500_character_remarks(page):
    """
    Test Case 8: Add item 8 without attachment and 500 character remarks.

    Steps:
        1. Add item 8: master item 8, search the whitelisted Framework Agreement (Applicable For: Both,
           then HO/HCMP) and select its row 8, quantity 8, Amount then Quantity radio button,
           GL Code 8, no attachment, 500 character remarks with all special characters; Add to grid and verify the item row
           and 8 items.
        2. Verify the Requisition Detail Information List has 8 items.

    All scenario values are read from .env.
    """
    assert len(added_items) == 7, "Test Case 7 must pass first: item 7 is not added to the requisition"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Item 8 (No attachment)
    with allure.step("Step 1: Add item 8 (row 8 of the agreement, no attachment) and verify 8 items"):
        add_requisition_item(create_requisition_page, REQUISITION_ITEMS[7])

    # Step 2: 8 items in the Requisition Detail Information List
    with allure.step(f"Step 2: Verify {len(REQUISITION_ITEMS)} items in the Requisition Detail Information List"):
        create_requisition_page.verify_grid_row_count(expected_count=len(REQUISITION_ITEMS))
        print("ADDED ITEMS:", [(item["number"], item["item_code"], item["attachment_type"]) for item in added_items])
        allure.attach(
            "\n".join(f"Item {item['number']}: {item['item_name']} | {item['master_item']} | "
                      f"quantity {item['quantity']} | unit price {item['unit_price']} | "
                      f"{item['attachment_type']} {item['attachment_name'] or '-'} | "
                      f"remarks {len(item['remarks'])} characters" for item in added_items),
            name="Requisition items",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_all_items_added')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Submit Requisition")
@allure.title("Test_case_9: Submit requisition with 8 items")
@allure.description("Test case 9: Set the delivery schedule and Head Office location, submit the requisition with "
                    "8 items and get the submission confirmation message and requisition number.")
@pytest.mark.order(9)
def test_9_submit_requisition(page):
    """
    Test Case 9: Submit the requisition with the 8 items.

    Steps:
        1. Set the same schedule (today).
        2. Set delivery location: Head Office and 'test_schedule_address'.
        3. Submit the requisition, get the submission confirmation message and store the
           requisition number in 'req_num'.

    All scenario values are read from .env.
    """
    global req_num, req_submission_message

    # All items come from Test Case 1 and 2
    assert len(added_items) == len(REQUISITION_ITEMS), \
        "Test Cases 1-8 must pass first: requisition items are not added"
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
@allure.title("Test_case_10: Identify first approver")
@allure.description("Test case 10: Identify and capture the first approver of a submitted requisition.")
@pytest.mark.order(10)
def test_10_identify_first_approver(page):
    """
    Test Case 10: Identify and capture the first approver of the submitted requisition.

    Steps:
        1. Go to Requisition > Requisition List.
        2. Search the submitted requisition ('req_num').
        3. Get the first layer approver ID ('approver_id') and status ('req_status').
        4. Exit and log out from ERP.
    """
    global approver_id, req_status

    assert req_num, "Test Case 9 must pass first: no requisition number available"

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
@allure.title("Test_case_11: Approve requisition as first approver")
@allure.description(
    "Test case 11: Login as the first approver, approve the submitted requisition in the ERP Procurement system and "
    "get the approval confirmation message.")
@pytest.mark.order(11)
def test_11_approve_requisition_as_first_approver(page):
    """
    Test case 11: Login as the first approver and approve the submitted requisition.

    Steps:
        1. Log in to ERP as the first approver ('approver_id') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition, approve it and store the approval confirmation message
           in 'first_approval_message'.
        4. Exit and log out.
    """
    global first_approval_message
    assert req_num and approver_id, "Test case 10 must pass first: no requisition number/approver ID available"

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

    # Step 3: Select and approve the requisition, get the approval confirmation message
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
@allure.title("Test_case_12: Identify second approver")
@allure.description(
    "Test case 12: Identify and capture the second-level approver of a submitted requisition in the ERP "
    "Procurement system.")
@pytest.mark.order(12)
def test_12_identify_second_approver(page):
    """
    Test case 12: Identify and capture the second-level approver of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List and search the requisition ('req_num').
        3. Get the second (final) layer approver ID ('approver_id_2') and status ('second_layer_req_status').
        4. Exit and log out.
    """
    global approver_id_2, second_layer_req_status
    assert req_num, "Test case 9 must pass first: no requisition number available"

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
@allure.title("Test_case_13: Approve requisition as final approver")
@allure.description(
    "Test case 13: Login as the second-level (final) approver, approve the submitted requisition in the ERP "
    "Procurement system and get the approval confirmation message.")
@pytest.mark.order(13)
def test_13_approve_requisition_as_final_approver(page):
    """
    Test case 13: Login as the second-level (final) approver and approve the requisition.

    Steps:
        1. Log in to ERP as the final approver ('approver_id_2') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition, approve it and store the approval confirmation message
           in 'final_approval_message'.
        4. Exit and log out.
    """
    global final_approval_message
    assert req_num and approver_id_2, "Test case 12 must pass first: no requisition number/second approver available"

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
@allure.title("Test_case_14: Requisition initiator gets approval status")
@allure.description(
    "Test case 14: Login as the requisition initiator, get the approval status of the requisition, verify the 8 "
    "requisition items (master item, quantity, unit price) and the vendor, and save the requisition result for the "
    "order creation journey.")
@pytest.mark.order(14)
def test_14_requisition_initiator_gets_approval_status(page, new_tab):
    """
    Test case 14: Requisition initiator gets the approval status of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List, search the requisition ('req_num') and get its approval status.
        3. Open the requisition details in a new tab and verify the 8 items of the whitelisted Framework
           Agreement with their master item, quantity and unit price.
        4. Open the FA No link in a new tab and verify the vendor is the same as the agreement items vendor;
           store it in 'order_vendor'.
        5. Close the tabs, exit and log out.
        6. Save the requisition result (item_remarks_attachment_requisition_result.json): item name with code,
           master item name, attachment file, remarks and quantity of each item, for the order creation journey.
    """
    global approved_req_status, verified_requisition_details, order_vendor, requisition_result
    assert req_num, "Test case 9 must pass first: no requisition number available"
    assert len(added_items) == len(REQUISITION_ITEMS), "Test Cases 1-8 must pass first: requisition items not available"

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

    # Step 3: Open requisition details in a new tab and verify the 8 items
    with allure.step(f"Step 3: Verify requisition details of {req_num} ({len(added_items)} items)"):
        details_tab = new_tab(lambda p: requisition_list_page.goto_requisition_details_information())
        requisition_details_page = RequisitionDetailsInformation(details_tab)

        requisition_details_page.verify_requisition_item_count(fa_no=whitelisted_agreement_number,
                                                               expected_count=len(added_items))
        for item in added_items:
            verified_requisition_details[item["number"]] = requisition_details_page.verify_requisition_item(
                requisition_number=req_num,
                fa_no=whitelisted_agreement_number,
                item_code=item["master_item_code"],
                quantity=item["quantity"],
                unit_price=item["unit_price"]
            )
        print("VERIFIED REQUISITION DETAILS:", verified_requisition_details)
        allure.attach(
            f"Requisition number: {req_num}\nStatus: {approved_req_status}\nFA. No: {whitelisted_agreement_number}\n"
            + "\n".join(f"Item {number}: {details}" for number, details in verified_requisition_details.items()),
            name="Verified requisition details",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_details_page.get_full_page_screenshot('requisition_details_verified')

    # Step 4: Get the vendor of each agreement in the requisition (one agreement: first FA No link only)
    with allure.step("Step 4: Get the agreement vendor from the FA No link and verify it"):
        agreement_vendors = requisition_details_page.get_agreement_vendors()
        print("AGREEMENT VENDORS:", agreement_vendors)
        assert list(agreement_vendors) == [whitelisted_agreement_number], \
            f"Expected only agreement {whitelisted_agreement_number} in the requisition, found {list(agreement_vendors)}"
        order_vendor = agreement_vendors[whitelisted_agreement_number]
        print("ORDER VENDOR:", order_vendor)
        allure.attach(
            f"Agreement items vendor: {added_items[0]['vendor_name']}\n"
            f"Requisition vendor (FA No link): {order_vendor}",
            name="Verified vendor",
            attachment_type=allure.attachment_type.TEXT
        )
        # Grid vendor has the vendor code, e.g. "[SU000723]- Walton Hi-Tech Industries PLC"
        for item in added_items:
            assert order_vendor.lower() in item["vendor_name"].lower(), \
                f"Item {item['number']} vendor '{item['vendor_name']}' is not the requisition vendor '{order_vendor}'"

    # Step 5: Close the tabs, exit and log out
    with allure.step("Step 5: Close requisition details tabs, exit and log out from ERP"):
        details_tab.close()
        page.bring_to_front()
        erp_logout(page, 'requisition_initiator_final_logout')

    # Step 6: Save the requisition result for the order creation journey
    with allure.step("Step 6: Save the requisition result for the order creation journey"):
        requisition_result = {
            "requisition_number": req_num,
            "requisition_status": approved_req_status,
            "first_approval_message": first_approval_message,
            "final_approval_message": final_approval_message,
            "agreement_number": whitelisted_agreement_number,
            "vendor": order_vendor,
            "final_approver": approver_id_2,
            "delivery_address": schedule_address,
            "items": [{key: value for key, value in item.items() if key != "grid_row"} for item in added_items],
        }
        save_result("item_remarks_attachment_requisition_result", requisition_result)
        print("REQUISITION RESULT:", requisition_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in requisition_result.items() if key != "items")
            + "\n" + "\n".join(
                f"Item {item['number']}: {item['item_name']} | master item {item['master_item']} | "
                f"quantity {item['quantity']} | {item['attachment_type']} {item['attachment_name'] or '-'} | "
                f"remarks: {item['remarks']}" for item in requisition_result["items"]),
            name="Saved requisition result",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.suite("Public Side")
@allure.feature("Active Requisition List")
@allure.story("Requisition Sync")
@allure.title("Test_case_15: Verify requisition sync to marketplace and ERP view")
@allure.description("Test case 15: Verify the approved requisition is synchronized to the Digital Marketplace, the "
                    "ERP View button opens the same requisition details in ERP staging, and store the Active "
                    "Requisition Product List rows.")
@pytest.mark.order(15)
def test_15_verify_requisition_sync_to_marketplace(page, new_tab):
    """
    Test Case 15: Verify Requisition Synchronization to Marketplace and the ERP View.

    Steps:
        1. Log in to the Digital Marketplace as 'proj_user' using SSO and verify the welcome message.
        2. Go to the Active Requisition List and search the requisition ('req_num').
        3. Click the ERP View button: a new tab opens the ERP staging server. If it shows the ERP login page,
           log in as the same user (ResetHub link), close it and click ERP View again. Verify and match all
           requisition information (REQ. No, Status, Project Name, Source of Fund, Remarks, FA No and both
           item rows) with the created requisition and store it; close the ERP tab and go back to the
           Active Requisition List.
        4. Open the Active Requisition Product List in a new tab, verify 8 product(s) and store the product rows
           (Sub-Category, Product, FwA No.).
        No logout: Test case 16 and 11 continue on the Active Requisition Product List.

    All scenario values are read from .env.
    """
    global active_requisition_found, erp_requisition_information, product_list_tab, active_product_links
    assert req_num, "Test case 9 must pass first: no requisition number available"

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

        # The ERP requisition must match the created requisition (Test case 1-14)
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
            ("FA No", whitelisted_agreement_number, erp_requisition_information["agreement_numbers"],
             erp_requisition_information["agreement_numbers"] == [whitelisted_agreement_number]),
        ]
        erp_details_page.verify_requisition_item_count(fa_no=whitelisted_agreement_number,
                                                       expected_count=len(added_items))
        erp_requisition_information["items"] = [
            erp_details_page.verify_requisition_item(
                requisition_number=req_num, fa_no=whitelisted_agreement_number, item_code=item["master_item_code"],
                quantity=item["quantity"], unit_price=item["unit_price"])
            for item in added_items
        ]
        erp_checks.append(("Requisition Details rows", len(added_items), len(erp_requisition_information["items"]), True))
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
        assert len(product_rows) == 8, f"Expected 8 product(s) in the Active Requisition Product List, found {len(product_rows)}"
        for row in product_rows:
            active_product_links.append({
                "sub_category": active_requisition_product_list.cell_text(row["Sub-Category"]),
                "product": active_requisition_product_list.cell_text(row["Product"]),
                "fwa_no": active_requisition_product_list.cell_text(row["FwA No."]),
            })
        print("ACTIVE REQUISITION PRODUCT ROWS:", active_product_links)
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
@allure.title("Test_case_16: Verify Active Requisition Product List links")
@allure.description("Test case 16: For every product of the requisition, open the Sub-Category link and come back, "
                    "store the product name ('item name - delivery location', not clicked), and open the FwA No. "
                    "attachment (or verify the ERP staging message when the attachment is not available).")
@pytest.mark.order(16)
def test_16_verify_active_requisition_product_list_links(page):
    """
    Test Case 16: Verify the Sub-Category, Product and FwA No. links of the Active Requisition Product List.
    Continues on the Active Requisition Product List of Test case 15 (no new login).

    Steps:
        1. Sub-Category link of every product: open it, store the sub-category, go back to the list.
        2. Product name of every product: stored ("item name - delivery location"), not clicked; it is verified on
           the next pages (shopping cart, checkout, order details, approval, vendor and receive pages).
        3. FwA No. link of every product: if the agreement attachment is available, open/download it;
           if not, verify the new tab is the ERP staging server with a message, close it and come back.
        No logout: Test case 17 continues on the Active Requisition Product List.

    All scenario values are read from .env.
    """
    assert active_product_links and product_list_tab, \
        "Test case 15 must pass first: Active Requisition Product List not available"
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
            with allure.step(f"Product {index + 1}: FwA No. {product['fwa_no']}"):
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
@allure.title("Test_case_17: Verify Product Switch History links")
@allure.description("Test case 17: For every product, open its Product Switch History, verify the product name and "
                    "FwA No. are the same as the Active Requisition Product List (product name not clicked), open "
                    "the FwA No. attachment (or verify the ERP staging message), go back to the product list, then log "
                    "out and save the requisition result with the marketplace data.")
@pytest.mark.order(17)
def test_17_verify_product_switch_history_links(page):
    """
    Test Case 17: Verify the Product Switch History of every product.
    Continues on the Active Requisition Product List of Test case 15 and 10 (no new login).

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
        "Test case 15 must pass first: Active Requisition Product List not available"
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
            assert any(row["FwA No."] == product["fwa_no"] for row in history), \
                f"FwA No. '{product['fwa_no']}' not found in its Product Switch History: {history}"


            # FwA No. link of the history (attachment or ERP staging message)
            attachment = history_page.open_fwa_attachment(
                history_page.get_history_rows()[0]["FwA No."],
                screenshot_name=f'product_switch_history_fwa_{index + 1}'
            )
            check_fwa_attachment(attachment)

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
        assert requisition_result, "Test case 14 must pass first: requisition result not available"
        requisition_result["erp_view"] = erp_requisition_information
        requisition_result["active_requisition_products"] = active_product_links
        requisition_result["product_switch_history"] = product_switch_history
        save_result("item_remarks_attachment_requisition_result", requisition_result)
        print("REQUISITION RESULT (with marketplace data):", requisition_result)
