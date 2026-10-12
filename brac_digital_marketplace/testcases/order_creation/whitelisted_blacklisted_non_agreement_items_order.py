from dotenv import load_dotenv
import os
from decimal import Decimal
from pathlib import Path

import pytest
import allure

load_dotenv()

# Digital Marketplace (staging)
proj_user = os.getenv("test_user_name")
proj_env = os.getenv("test_env")
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
# ERP staging address: requisition and FA links open ERP pages
erp_url = os.getenv("test_url")
# Requisition item remarks (shown in the shopping cart and checkout)
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
# New cart attachment: must be different from the requisition attachment
cart_attachment_file = os.getenv("test_requisition_attachment_file_2")
# Shopping cart quantity and the 2 delivery schedules (same values as marketplace_staging_sanity.py)
fractional_cart_qty = os.getenv("test_fractional_cart_qty")
delivery_schedule_quantity = os.getenv("test_delivery_schedule_quantity")
manual_delivery_location_1 = os.getenv("test_delivery_location_1")
manual_delivery_location_2 = os.getenv("test_delivery_location_2")
receiving_pin_1 = os.getenv("test_receiving_pin")
order_initiator = os.getenv("test_order_initiator")
order_remarks = os.getenv("test_order_remarks")
# Project root is 3 levels up: testcases/order_creation/<this file>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
UTILS_DIR = PROJECT_ROOT / "utils"
DOWNLOAD_DIR = PROJECT_ROOT / "artifacts" / "downloads"
# Shopping cart attachment rules: max 20 MB; RAR, DOCX, JPG, PNG, XLSX, PDF, PPTX, ZIP
CART_ATTACHMENT_TYPES = {".rar", ".docx", ".jpg", ".png", ".xlsx", ".pdf", ".pptx", ".zip"}
MAX_CART_ATTACHMENT_SIZE_MB = 20
MAX_CART_ITEM_REMARKS_LENGTH = 500

from utils.test_data_store import load_result, save_result
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.shopping_cart import ShoppingCart
from pages.digital_marketplace.public_side.checkout_page import CheckoutPage
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails
from brac_digital_marketplace.testcases.order_creation.order_page_links import check_cart_item_links, \
    check_checkout_page_links, check_checkout_attachment, check_order_details_page_links, read_requisition_from_link
from brac_digital_marketplace.testcases.order_creation.order_details_checks import check_order_information, \
    check_product, check_delivery_schedules, check_action_history, check_order_preview, to_amount, new_check

# Requisition of whitelisted_blacklisted_non_agreement_items_requisition.py
# (whitelisted_blacklisted_nonagreement_requisition_result.json)
requisition = {}
# Only the whitelisted agreement item syncs to the Digital Marketplace (blacklisted and non-agreement do not)
whitelisted_item = {}
req_num = ''
order_vendor = ''
# Shopping cart (Test case 1-3)
cart_item_before_vendor = {}
cart_item_after_vendor = {}
attachment_remove_message = ''
cart_attachment_name = ''
cart_quantity = ''
cart_checked_out = False
# Delivery schedule (Test case 4-5)
requisition_schedule = []
delivery_schedule = ''
# Marketplace order (Test case 6-7)
order_reference_number = ''
order_status = ''
# Links of each page (requisition, Framework Agreement, product details, attachment)
page_links = {}
# Order details (Test case 8-9) and order preview (Test case 10)
order_details = {}
order_preview = {}
# Order result for the pending approval test file
order_result = {}


def attach_and_assert_checks(checks, title):
    # Why: every check is listed in the report (expected / actual / result); When: after the checks of a step;
    # the test fails if any check failed
    allure.attach(
        "\n".join(f"{check}: expected {expected} | actual {actual} | {result}" for check, expected, actual, result in checks),
        name=title,
        attachment_type=allure.attachment_type.TEXT
    )
    failed_checks = [f"{check}: expected {expected}, found {actual}"
                     for check, expected, actual, result in checks if result == "FAIL"]
    assert not failed_checks, f"{title}:\n" + "\n".join(failed_checks)


def remaining_quantity():
    # Why: the second delivery schedule gets the rest of the cart quantity; When: schedule and order checks
    return to_amount(cart_quantity) - to_amount(delivery_schedule_quantity)


def expected_schedules():
    # Why: the 2 delivery schedules of Test case 5; When: order details and preview checks
    return [{"Quantity": delivery_schedule_quantity, "Location": manual_delivery_location_1, "Receiver": receiving_pin_1},
            {"Quantity": str(remaining_quantity()), "Location": manual_delivery_location_2, "Receiver": order_initiator}]


def expected_order():
    # Why: the values the order details and the order document must show; When: order details and preview checks
    return {
        "order_reference_number": order_reference_number, "requisition_number": req_num,
        "agreement_number": whitelisted_item["agreement_number"], "order_status": order_status,
        "order_remarks": order_remarks, "vendor": order_vendor,
        "master_item_code": whitelisted_item["master_item_code"], "item_code": whitelisted_item["item_code"],
        "specification": whitelisted_item["specification"], "remarks": requisition_item_remarks,
        "uom": cart_item_after_vendor["UoM"], "quantity": cart_quantity, "unit_price": whitelisted_item["unit_price"],
        "schedules": expected_schedules(),
    }


def item_products():
    # Why: the product link text is the agreement item name of the cart item; When: checkout product link checks
    return {cart_item_after_vendor["Agreement item name"]: [whitelisted_item["item_code"]]}


def note_earlier_cart_changes(label, changes):
    # Why: "Update shopping cart" saves the cart changes, so a checkout that was not confirmed (an earlier run that
    # stopped) leaves them in the cart; When: the cart item already has the changes of the cart preparation test
    message = f"The cart item keeps the cart changes of an earlier unconfirmed checkout: {changes}"
    print(f"EARLIER CART CHANGES ({label}):", changes)
    allure.attach(message, name=f"Earlier cart changes ({label})", attachment_type=allure.attachment_type.TEXT)


def verify_cart_item(page, label):
    # Why: the cart item must be the whitelisted requisition item (values) and link to the requisition (ERP),
    # agreement attachment, product details page and item attachment; When: before and after the vendor selection
    cart_page = ShoppingCart(page)
    item_row = cart_page.get_requisition_cart_rows(requisition_number=req_num)[0]
    cart_item = cart_page.read_cart_item_cell(item_row)
    # Cart changes of Test case 3 already in the cart (earlier unconfirmed checkout): expected instead of the
    # requisition quantity and attachment
    expected_quantity, expected_attachment = whitelisted_item["quantity"], whitelisted_item["attachment_name"]
    if to_amount(cart_item["Qty."]) == to_amount(fractional_cart_qty) and \
            (cart_item["Attachment path"] or "").endswith(cart_attachment_file):
        expected_quantity, expected_attachment = fractional_cart_qty, cart_attachment_file
        note_earlier_cart_changes(label, f"quantity {fractional_cart_qty}, attachment {cart_attachment_file}")
    checks = [
        new_check("Master item", whitelisted_item["master_item_code"], cart_item["Master item"],
                  cart_item["Master item"].startswith(whitelisted_item["master_item_code"])),
        new_check("Requisition number", req_num, cart_item["Requisition"], cart_item["Requisition"] == req_num),
        new_check("Framework agreement number", whitelisted_item["agreement_number"], cart_item["FA No."],
                  cart_item["FA No."] == whitelisted_item["agreement_number"]),
        new_check("Agreement item code", whitelisted_item["item_code"], cart_item["Agreement item code"],
                  cart_item["Agreement item code"] == whitelisted_item["item_code"]),
        new_check("Agreement item specification", whitelisted_item["specification"], cart_item["Specification"],
                  cart_item["Specification"] == " ".join(whitelisted_item["specification"].split())),
        new_check("Requisition remarks", requisition_item_remarks, cart_item["Remarks"],
                  cart_item["Remarks"] == " ".join(requisition_item_remarks.split())),
        new_check("Qty.", expected_quantity, cart_item["Qty."],
                  to_amount(cart_item["Qty."]) == to_amount(expected_quantity)),
        new_check("Unit Price", whitelisted_item["unit_price"], cart_item["Unit Price"],
                  to_amount(cart_item["Unit Price"]) == to_amount(whitelisted_item["unit_price"])),
    ]
    link_checks, page_links[label] = check_cart_item_links(
        page, item_row, req_num, whitelisted_item["item_code"], expected_attachment, label, DOWNLOAD_DIR)
    print(f"CART ITEM ({label}):", cart_item)
    cart_page.get_full_page_screenshot(f'order_{label}_links_checked')
    attach_and_assert_checks(checks + link_checks, f"Shopping cart item and links ({label})")
    return cart_item


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Item Before Vendor Selection")
@allure.title("Test_case_1: Verify cart item and links before vendor selection")
@allure.description("Test case 1: Before the vendor selection, verify the whitelisted item of the requisition in the "
                    "shopping cart, open the requisition details (ERP), download the agreement attachment, open the "
                    "product details page and download the item attachment.")
@pytest.mark.order(1)
def test_1_verify_cart_item_before_vendor_selection(page):
    """
    Test case 1: Shopping cart item and links before the vendor selection.

    Steps:
        1. Load the requisition of whitelisted_blacklisted_non_agreement_items_requisition.py
           (whitelisted_blacklisted_nonagreement_requisition_result.json); store its whitelisted agreement item
           (the only item synced to the marketplace) in 'whitelisted_item'.
        2. Log in to the Digital Marketplace as the order initiator ('proj_user').
        3. Shopping cart, before vendor selection: only the whitelisted item is in the cart; verify the item
           (master item - requisition, FA No., agreement item, specification, remarks, Qty., Unit Price), the
           requisition details (ERP; all opened tabs closed), the agreement attachment download, the product details
           page and the item attachment download (same file type as the requisition attachment).
        No logout: Test case 2 continues in the shopping cart.

    All scenario values are read from .env.
    """
    global requisition, whitelisted_item, req_num, order_vendor, cart_item_before_vendor

    required_env_values = {
        "test_user_name": proj_user,
        "test_env": proj_env,
        "test_url": erp_url,
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_requisition_item_remarks": requisition_item_remarks,
        "test_requisition_attachment_file_2": cart_attachment_file,
        "test_fractional_cart_qty": fractional_cart_qty,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    login_page = LoginPage(page)
    home_page = HomePage(page)
    cart_page = ShoppingCart(page)

    # Step 1: Requisition from whitelisted_blacklisted_non_agreement_items_requisition.py
    with allure.step("Step 1: Load the requisition result of whitelisted_blacklisted_non_agreement_items_requisition.py"):
        requisition = load_result("whitelisted_blacklisted_nonagreement_requisition_result",
                                  created_by="whitelisted_blacklisted_non_agreement_items_requisition.py")
        req_num = requisition["requisition_number"]
        order_vendor = requisition["vendor"]
        # The whitelisted agreement item is the only product synced to the marketplace
        synced_fwa_numbers = [product["fwa_no"] for product in requisition["active_requisition_products"]]
        whitelisted_item = next((item for item in requisition["items"]
                                 if item["agreement_number"] and item["agreement_number"] in synced_fwa_numbers), {})
        assert whitelisted_item, f"Whitelisted agreement item not found in the requisition result: {synced_fwa_numbers}"
        print("REQ NUM:", req_num)
        print("WHITELISTED ITEM:", whitelisted_item)
        # New cart attachment: shopping cart rules and different from the requisition attachment
        cart_attachment_path = UTILS_DIR / cart_attachment_file
        assert cart_attachment_path.is_file(), f"Cart attachment not found in utils: {cart_attachment_path}"
        assert cart_attachment_path.suffix.lower() in CART_ATTACHMENT_TYPES, \
            f"Cart attachment type {cart_attachment_path.suffix} is not allowed: {sorted(CART_ATTACHMENT_TYPES)}"
        assert cart_attachment_path.stat().st_size / (1024 * 1024) <= MAX_CART_ATTACHMENT_SIZE_MB, \
            f"Cart attachment must be max {MAX_CART_ATTACHMENT_SIZE_MB} MB"
        assert cart_attachment_path.name != whitelisted_item["attachment_name"], \
            "The new cart attachment must be different from the requisition attachment"
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in whitelisted_item.items()),
            name="Whitelisted requisition item",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 2: Log in to the Digital Marketplace
    with allure.step(f"Step 2: Log in to the Digital Marketplace as {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=proj_user, pass_word=marketplace_password)
        print(f"Logging in to the Digital Marketplace as: {proj_user}")
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('order_cart_login')

    # Step 3: Shopping cart, before vendor selection
    with allure.step(f"Step 3: Verify requisition {req_num} item and links in the shopping cart (before vendor selection)"):
        home_page.goto_shopping_cart()
        assert cart_page.wait_for_requisition_in_cart(requisition_number=req_num), \
            f"Requisition {req_num} is not synced to the shopping cart"
        item_rows = cart_page.get_requisition_cart_rows(requisition_number=req_num)
        assert len(item_rows) == 1, f"Only the whitelisted item must be in the cart, found {len(item_rows)} item(s)"
        cart_page.get_full_page_screenshot('order_cart_before_vendor')
        cart_item_before_vendor = verify_cart_item(page, "cart_before_vendor")


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Item After Vendor Selection")
@allure.title("Test_case_2: Verify cart item and links after vendor selection")
@allure.description("Test case 2: Select the requisition vendor, then verify the whitelisted item and open its "
                    "requisition details, agreement attachment, product details and item attachment again.")
@pytest.mark.order(2)
def test_2_verify_cart_item_after_vendor_selection(page):
    """
    Test case 2: Shopping cart item and links after the vendor selection. Continues in the shopping cart of Test case 1.

    Steps:
        1. Select the vendor of the requisition (only this requisition stays ticked).
        2. Verify the item and its links again (same checks as Test case 1).
        No logout: Test case 3 continues in the shopping cart.
    """
    global cart_item_after_vendor
    assert cart_item_before_vendor, "Test case 1 must pass first: shopping cart item is not verified"
    cart_page = ShoppingCart(page)

    # Step 1: Vendor selection
    with allure.step(f"Step 1: Select vendor {order_vendor} for requisition {req_num}"):
        cart_page.select_vendor_for_requisition_found(requisition_number=req_num)
        # The shopping cart can have many requisitions (business data): keep only this requisition ticked
        assert cart_page.select_vendor_keep_only_requisition(vendor_name=order_vendor, requisition_number=req_num), \
            f"Vendor {order_vendor} not found in the shopping cart"
        cart_page.get_full_page_screenshot('order_cart_after_vendor')

    # Step 2: The same checks again
    with allure.step("Step 2: Verify the item and its links again"):
        cart_item_after_vendor = verify_cart_item(page, "cart_after_vendor")


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Preparation")
@allure.title("Test_case_3: Replace cart attachment, update quantity and checkout")
@allure.description("Test case 3: Keep the item remarks, remove the requisition attachment (confirm) and upload a new "
                    "attachment, update the quantity and checkout.")
@pytest.mark.order(3)
def test_3_replace_attachment_update_quantity_and_checkout(page):
    """
    Test case 3: Prepare the shopping cart for checkout. Continues in the shopping cart of Test case 2.

    Steps:
        1. Item remarks are not changed. Remove the requisition attachment (confirm) and upload a new attachment
           ('test_requisition_attachment_file_2', different from the requisition attachment).
        2. Update the quantity ('test_fractional_cart_qty'), accept terms of service and checkout.

    All scenario values are read from .env.
    """
    global attachment_remove_message, cart_attachment_name, cart_quantity, cart_checked_out
    assert cart_item_after_vendor, "Test case 2 must pass first: vendor is not selected"

    cart_page = ShoppingCart(page)
    cart_attachment_path = UTILS_DIR / cart_attachment_file

    # Step 1: Remarks not changed; replace the requisition attachment with a new attachment
    with allure.step(f"Step 1: Remove the requisition attachment and upload {cart_attachment_path.name}"):
        item_row = cart_page.get_requisition_cart_rows(requisition_number=req_num)[0]
        attachment_remove_message = cart_page.remove_cart_attachment(item_row)
        print("ATTACHMENT REMOVE CONFIRMATION:", attachment_remove_message)
        cart_page.get_full_page_screenshot('order_cart_attachment_removed')
        cart_page.upload_cart_item_attachment(item_row, cart_attachment_path)
        cart_attachment_name = cart_attachment_path.name
        uploaded_path = cart_page.read_cart_item_cell(item_row)["Attachment path"]
        print("CART ATTACHMENT:", cart_attachment_name, uploaded_path)
        allure.attach(
            f"Removed: {whitelisted_item['attachment_name']}\nRemove confirmation: {attachment_remove_message}\n"
            f"Uploaded: {cart_attachment_name}\nAttachment path: {uploaded_path}",
            name="Cart attachment replaced",
            attachment_type=allure.attachment_type.TEXT
        )
        cart_page.get_full_page_screenshot('order_cart_attachment_uploaded')
        assert uploaded_path.endswith(cart_attachment_name), \
            f"Cart attachment is '{uploaded_path}', expected the new file {cart_attachment_name}"

    # Step 2: Update the quantity, accept terms of service and checkout
    with allure.step(f"Step 2: Update the quantity to {fractional_cart_qty} and checkout"):
        cart_page.update_cart_item_quantity(item_row, fractional_cart_qty)
        item_row = cart_page.get_requisition_cart_rows(requisition_number=req_num)[0]
        cart_quantity = cart_page.read_cart_item_cell(item_row)["Qty."]
        print("CART QUANTITY:", cart_quantity)
        assert to_amount(cart_quantity) == to_amount(fractional_cart_qty), \
            f"Cart quantity is {cart_quantity}, expected {fractional_cart_qty}"
        cart_page.get_full_page_screenshot('order_cart_updated')
        cart_page.cart_page_checkout()
        cart_checked_out = True
        cart_page.get_full_page_screenshot('order_cart_checkout')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Links")
@allure.title("Test_case_4: Verify delivery schedule links")
@allure.description("Test case 4: On the delivery schedule, open the requisition details, agreement attachment and "
                    "product details links (a link that is not on this step is noted) and download the item attachment.")
@pytest.mark.order(4)
def test_4_verify_delivery_schedule_links(page):
    """
    Test case 4: Delivery schedule links.

    Steps:
        1. Requisition details (ERP), agreement attachment download and product details links: a link that is not
           on the delivery schedule is noted in the report.
        2. Item attachment download (same file type as the cart attachment).
    """
    assert cart_checked_out, "Test case 3 must pass first: the cart is not checked out"

    # Step 1-2: Links and item attachment of the delivery schedule
    with allure.step("Step 1-2: Open the requisition details, agreement attachment, product details and item attachment"):
        link_checks, page_links["delivery_schedule"] = check_checkout_page_links(
            page, req_num, [whitelisted_item["agreement_number"]], item_products(), 'order_schedule',
            links_required=False, save_folder=DOWNLOAD_DIR)
        attachment_checks, page_links["delivery_schedule"]["Attachment"] = check_checkout_attachment(
            page, cart_attachment_name, 'order_schedule', DOWNLOAD_DIR)
        CheckoutPage(page).get_full_page_screenshot('order_schedule_links_checked')
        attach_and_assert_checks(link_checks + attachment_checks, "Delivery schedule links and item attachment")


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Preparation Window")
@allure.title("Test_case_5: Prepare delivery schedule")
@allure.description("Test case 5: Verify the Requisition Schedule and the item (quantity, UoM, remarks) with the "
                    "requisition and the shopping cart, then prepare 2 delivery schedules (no Auto Generate).")
@pytest.mark.order(5)
def test_5_prepare_delivery_schedule(page):
    """
    Test case 5: Prepare the order delivery schedule (same 2 schedules as marketplace_staging_sanity.py).

    Steps:
        1. Requisition Schedule: verify the item row (Quantity = requisition quantity, Unit of Measure,
           Delivery Details = requisition delivery address, Requisition = 'req_num').
        2. Item before the schedule: verify item name, cart quantity and remarks.
        3. Schedule 1: 'test_delivery_schedule_quantity', expected date, location 1 and receiving person 1.
        4. Schedule 2: remaining quantity, location 2 and the order initiator.
        5. Wait until Continue is enabled and click Continue.

    All scenario values are read from .env.
    """
    global requisition_schedule, delivery_schedule
    assert "delivery_schedule" in page_links, "Test case 4 must pass first: delivery schedule links are not verified"
    required_env_values = {
        "test_delivery_schedule_quantity": delivery_schedule_quantity,
        "test_delivery_location_1": manual_delivery_location_1,
        "test_delivery_location_2": manual_delivery_location_2,
        "test_receiving_pin": receiving_pin_1,
        "test_order_initiator": order_initiator,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    assert to_amount(delivery_schedule_quantity) < to_amount(cart_quantity), \
        f"test_delivery_schedule_quantity {delivery_schedule_quantity} must be less than the cart quantity {cart_quantity}"

    checkout_page = CheckoutPage(page)

    # Step 1: Requisition Schedule (same as the requisition and the shopping cart)
    with allure.step(f"Step 1: Verify the Requisition Schedule of {req_num}"):
        requisition_schedule = checkout_page.get_requisition_schedule_rows()
        schedule_row = next((row for row in requisition_schedule if row.get("Requisition") == req_num), {})
        checkout_page.get_full_page_screenshot('order_schedule_requisition_schedule')
        checks = [
            new_check("Requisition Schedule row", req_num, schedule_row.get("Requisition", "-"), bool(schedule_row)),
            new_check("Requisition Schedule Item", cart_item_after_vendor["Agreement item name"],
                      schedule_row.get("Item", "-"), cart_item_after_vendor["Agreement item name"] in schedule_row.get("Item", "")),
            new_check("Requisition Schedule Quantity (requisition quantity)", whitelisted_item["quantity"],
                      schedule_row.get("Quantity", "-"),
                      bool(schedule_row) and to_amount(schedule_row["Quantity"]) == to_amount(whitelisted_item["quantity"])),
            new_check("Requisition Schedule Unit of Measure", cart_item_after_vendor["UoM"],
                      schedule_row.get("Unit of Measure", "-"), schedule_row.get("Unit of Measure") == cart_item_after_vendor["UoM"]),
            new_check("Requisition Schedule Delivery Details (requisition delivery address)",
                      requisition["delivery_address"], schedule_row.get("Delivery Details", "-"),
                      requisition["delivery_address"] in schedule_row.get("Delivery Details", "")),
        ]

    # Step 2: Item before the schedule: item, cart quantity and remarks
    with allure.step("Step 2: Verify the item, quantity and remarks before the schedule"):
        page_text = checkout_page.get_page_text()
        checks += [
            new_check("Item name", cart_item_after_vendor["Agreement item name"], "on the page",
                      cart_item_after_vendor["Agreement item name"] in page_text),
            new_check("Remarks", requisition_item_remarks, "on the page",
                      " ".join(requisition_item_remarks.split()) in page_text),
            new_check("Shopping cart quantity", cart_quantity, "on the page", f"{cart_quantity}" in page_text),
        ]
        attach_and_assert_checks(checks, "Delivery schedule window vs requisition and shopping cart")

    # Step 3: Schedule 1
    with allure.step(f"Step 3: Schedule 1 - {delivery_schedule_quantity} to {manual_delivery_location_1}"):
        checkout_page.fractional_schedule_update_quantity(delivery_schedule_quantity=delivery_schedule_quantity)
        checkout_page.update_expected_date()
        checkout_page.delivery_schedule_preparation(location=manual_delivery_location_1, pin=receiving_pin_1)
        checkout_page.click_add_schedule_btn()
        checkout_page.wait_for_timeout(2000)
        checkout_page.get_full_page_screenshot('order_schedule_1')

    # Step 4: Schedule 2 (remaining quantity)
    with allure.step(f"Step 4: Schedule 2 - remaining quantity to {manual_delivery_location_2}"):
        checkout_page.delivery_schedule_preparation(location=manual_delivery_location_2, pin=order_initiator)
        checkout_page.click_add_schedule_btn()
        checkout_page.get_full_page_screenshot('order_schedule_2')

    # Step 5: Continue
    with allure.step("Step 5: Wait until Continue is enabled and click Continue"):
        delivery_schedule = (f"{delivery_schedule_quantity} to {manual_delivery_location_1} ({receiving_pin_1}); "
                             f"{remaining_quantity()} to {manual_delivery_location_2} ({order_initiator})")
        print("DELIVERY SCHEDULE:", delivery_schedule)
        allure.attach(delivery_schedule, name="Delivery schedule", attachment_type=allure.attachment_type.TEXT)
        checkout_page.click_continue_when_enabled()
        checkout_page.get_full_page_screenshot('order_schedule_continue')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order Links")
@allure.title("Test_case_6: Verify confirm order links")
@allure.description("Test case 6: On the confirm order page, open the requisition details (ERP), download the "
                    "agreement attachment, open the product details page and download the item attachment.")
@pytest.mark.order(6)
def test_6_verify_confirm_order_links(page):
    """
    Test case 6: Confirm order links.

    Steps:
        1. Requisition details (ERP; all opened tabs closed), agreement attachment download and product details
           links: each link must be on the confirm order page.
        2. Item attachment download (same file type as the cart attachment).
    """
    assert delivery_schedule, "Test case 5 must pass first: delivery schedule is not prepared"
    checkout_page = CheckoutPage(page)

    # Step 1-2: Links and item attachment of the confirm order page
    with allure.step("Step 1-2: Open the requisition details, agreement attachment, product details and item attachment"):
        checkout_page.wait_for_confirm_order_step()
        link_checks, page_links["confirm_order"] = check_checkout_page_links(
            page, req_num, [whitelisted_item["agreement_number"]], item_products(), 'order_confirm',
            save_folder=DOWNLOAD_DIR)
        attachment_checks, page_links["confirm_order"]["Attachment"] = check_checkout_attachment(
            page, cart_attachment_name, 'order_confirm', DOWNLOAD_DIR)
        checkout_page.get_full_page_screenshot('order_confirm_links_checked')
        attach_and_assert_checks(link_checks + attachment_checks, "Confirm order links and item attachment")


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order")
@allure.title("Test_case_7: Confirm marketplace order")
@allure.description("Test case 7: Verify the confirm order information (agreement, vendor, requisition, item details, "
                    "prices, delivery schedules), confirm the order and get the order reference number.")
@pytest.mark.order(7)
def test_7_confirm_marketplace_order(page):
    """
    Test case 7: Confirm the marketplace order.

    Steps (each verification step has its own expected/actual checks):
        1. Order header: Framework Agreement, Vendor Name, Requisition number.
        2. Item details: master item, agreement item, specification, remarks.
        3. Item details: UoM, Qty. (shopping cart quantity), Unit Price, Total Price (Qty. x Unit Price).
        4. Expected delivery date and place: the 2 schedules of Test case 5 (quantity, location).
        5. Fill the order remarks ('test_order_remarks'), accept terms of service and confirm the order;
           store the order reference number.
        No logout: Test case 8 continues on the order details page.

    All scenario values are read from .env.
    """
    global order_reference_number
    assert "confirm_order" in page_links, "Test case 6 must pass first: confirm order links are not verified"
    assert order_remarks, "Missing in .env: test_order_remarks"
    assert len(order_remarks) <= MAX_CART_ITEM_REMARKS_LENGTH, "test_order_remarks must be max 500 characters"

    checkout_page = CheckoutPage(page)
    total_price = (to_amount(cart_quantity) * to_amount(whitelisted_item["unit_price"])).quantize(Decimal("0.01"))
    page_text = checkout_page.get_page_text()

    def verify_on_confirm_page(title, expected_values, screenshot_name):
        # Why: the confirm order page must show the order values; When: each confirm order check step
        checks = [new_check(check, expected, "on the page" if expected in page_text else "not found",
                            expected in page_text) for check, expected in expected_values]
        checkout_page.get_full_page_screenshot(screenshot_name)
        attach_and_assert_checks(checks, title)

    # Step 1: Order header: Framework Agreement, vendor and requisition
    with allure.step("Step 1: Verify the Framework Agreement, Vendor Name and Requisition number"):
        verify_on_confirm_page("Confirm order header", [
            ("Framework Agreement", whitelisted_item["agreement_number"]),
            ("Vendor Name", order_vendor),
            ("Requisition number", req_num),
        ], 'order_confirm_header')

    # Step 2: Item details: item information
    with allure.step("Step 2: Verify the item details (master item, agreement item, specification, remarks)"):
        verify_on_confirm_page("Confirm order item information", [
            ("Master item", whitelisted_item["master_item_code"]),
            ("Agreement item", whitelisted_item["item_code"]),
            ("Specification", " ".join(whitelisted_item["specification"].split())),
            ("Remarks", " ".join(requisition_item_remarks.split())),
        ], 'order_confirm_item_information')

    # Step 3: Item details: UoM, quantity and prices
    with allure.step(f"Step 3: Verify UoM, Qty. {cart_quantity}, Unit Price and Total Price {total_price}"):
        verify_on_confirm_page("Confirm order quantity and prices", [
            ("UoM", cart_item_after_vendor["UoM"]),
            ("Qty. (shopping cart quantity)", f"{to_amount(cart_quantity)}"),
            ("Unit Price", f"{to_amount(whitelisted_item['unit_price'])}"),
            ("Total Price (Qty. x Unit Price)", f"{total_price}"),
        ], 'order_confirm_quantity_prices')

    # Step 4: Expected delivery date and place (the 2 delivery schedules of Test case 5)
    with allure.step("Step 4: Verify the expected delivery date and place (2 schedules)"):
        verify_on_confirm_page("Confirm order delivery schedules", [
            ("Schedule 1 quantity", f"{to_amount(delivery_schedule_quantity)}"),
            ("Schedule 1 location", manual_delivery_location_1),
            ("Schedule 2 quantity", f"{remaining_quantity()}"),
            ("Schedule 2 location", manual_delivery_location_2),
        ], 'order_confirm_delivery_schedules')

    # Step 5: Order remarks, terms of service and confirm
    with allure.step(f"Step 5: Fill order remarks '{order_remarks}', accept terms of service and confirm"):
        checkout_page.fillup_order_remarks(input_remarks=order_remarks)
        checkout_page.select_terms_of_service()
        checkout_page.get_full_page_screenshot('order_remarks_terms')
        order_reference_number = checkout_page.confirm_order()
        assert order_reference_number, "Order reference number not displayed after Confirm"
        print("ORDER REFERENCE NUMBER:", order_reference_number)
        checkout_page.wait_for_timeout(2000)
        checkout_page.get_full_page_screenshot('order_confirmed')


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Details Links")
@allure.title("Test_case_8: Verify order details links")
@allure.description("Test case 8: Open the order details, download the agreement attachment (agreement number first), "
                    "open the requisition details (ERP), product details page, Preferred Delivery Schedule product and "
                    "requisition links, and download the item attachment.")
@pytest.mark.order(8)
def test_8_verify_order_details_links(page):
    """
    Test case 8: Order details links. Continues after the order confirmation of Test case 7.

    Steps:
        1. Open the order details and store the order status in 'order_status'.
        2. Agreement attachment download (first the agreement number of the order information, then the product
           FA link), requisition details (ERP; all opened tabs closed), product details page and item attachment
           download (same file type as the cart attachment).
        3. Preferred Delivery Schedule product link (product details page) and requisition link (ERP requisition
           details; all opened tabs closed).
        No logout: Test case 9 continues on the order details page.
    """
    global order_status
    assert order_reference_number, "Test case 7 must pass first: order is not confirmed"
    checkout_page = CheckoutPage(page)
    order_details_page = OrderDetails(page)

    # Step 1: Order details and status
    with allure.step(f"Step 1: Open the order details of {order_reference_number}"):
        order_status = checkout_page.goto_public_side_order_details_view()
        print("ORDER STATUS:", order_status)
        checkout_page.get_full_page_screenshot('order_details')

    # Step 2: Order details links and item attachment
    with allure.step("Step 2: Download the agreement attachment, open the requisition details and product details, "
                     "download the item attachment"):
        link_checks, page_links["order_details"] = check_order_details_page_links(
            page, req_num, whitelisted_item["agreement_number"], whitelisted_item["item_code"], cart_attachment_name,
            'order_details', DOWNLOAD_DIR)
        attach_and_assert_checks(link_checks, "Order details links and item attachment")

    # Step 3: Preferred Delivery Schedule product and requisition links
    with allure.step("Step 3: Open the Preferred Delivery Schedule product and requisition links"):
        schedule_item_tab = order_details_page.open_delivery_schedule_product_link_by_index(0)
        schedule_item_url = schedule_item_tab.url
        HomePage(schedule_item_tab).get_full_page_screenshot('order_details_schedule_product_page')
        order_details_page.close_opened_tabs([schedule_item_tab])
        schedule_requisition, opened_tabs = read_requisition_from_link(
            page, lambda: order_details_page.open_link_all_tabs(
                order_details_page.delivery_schedule_requisition_link(req_num)),
            'order_details_schedule_erp_requisition')
        page_links["order_details"]["Delivery schedule product page"] = schedule_item_url
        page_links["order_details"]["Delivery schedule requisition"] = schedule_requisition["req_no"]
        checks = [
            new_check("Preferred Delivery Schedule product link", whitelisted_item["item_code"], schedule_item_url,
                      whitelisted_item["item_code"].lower() in schedule_item_url.lower()),
            new_check("Preferred Delivery Schedule requisition link (ERP REQ. No)", req_num,
                      schedule_requisition["req_no"], schedule_requisition["req_no"] == req_num),
            new_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1),
        ]
        checkout_page.get_full_page_screenshot('order_details_links_checked')
        attach_and_assert_checks(checks, "Order details Preferred Delivery Schedule links")


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Details Information")
@allure.title("Test_case_9: Verify order details information")
@allure.description("Test case 9: Verify the order status, Order Date, order information, product, Preferred Delivery "
                    "Schedule and Action History of the order details with the requisition, the shopping cart and the "
                    "delivery schedule.")
@pytest.mark.order(9)
def test_9_verify_order_details_information(page):
    """
    Test case 9: Order details information. Continues on the order details page of Test case 8.

    Steps:
        1. Order information: Order Reference No., Framework Agreement, Order Status, Order Total (Qty. x Unit
           Price), Order Remarks, Vendor Name, Letter Pad Type.
        2. Product: master item - requisition, FA No., agreement item, specification, remarks, attachment, UoM,
           Quantity (shopping cart quantity), Unit Price, Total Price and Sub-Total.
        3. Preferred Delivery Schedule: the 2 schedules of Test case 5 (quantity, location, receiver).
        4. Action History (stored): submitted for approval by the requisition initiator; Order Date = the date the
           order was submitted.
    """
    assert "order_details" in page_links, "Test case 8 must pass first: order details links are not verified"
    order_details_page = OrderDetails(page)

    # Step 1: Order information
    with allure.step("Step 1: Verify the order information"):
        checks, order_details["information"] = check_order_information(page, expected_order())
        order_details_page.get_full_page_screenshot('order_details_information')
        attach_and_assert_checks(checks, "Order details information")

    # Step 2: Product and Sub-Total
    with allure.step("Step 2: Verify the product and the Sub-Total"):
        checks, order_details["product"] = check_product(page, expected_order())
        order_details_page.get_full_page_screenshot('order_details_product')
        attach_and_assert_checks(checks, "Order details product")

    # Step 3: Preferred Delivery Schedule (the 2 schedules of Test case 5)
    with allure.step("Step 3: Verify the Preferred Delivery Schedule (2 schedules)"):
        checks, order_details["delivery_schedule"] = check_delivery_schedules(page, expected_schedules())
        order_details_page.get_full_page_screenshot('order_details_delivery_schedule')
        attach_and_assert_checks(checks, "Order details Preferred Delivery Schedule")

    # Step 4: Action History (stored) and Order Date
    with allure.step("Step 4: Store the Action History and verify the order submission and Order Date"):
        checks, order_details["action_history"] = check_action_history(page, order_details["information"]["Order Date"])
        allure.attach(
            "\n".join(" | ".join(f"{title}: {value}" for title, value in row.items())
                      for row in order_details["action_history"]),
            name="Order Action History",
            attachment_type=allure.attachment_type.TEXT
        )
        order_details_page.get_full_page_screenshot('order_details_action_history')
        attach_and_assert_checks(checks, "Order details Action History and Order Date")


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Preview")
@allure.title("Test_case_10: Verify order preview, download the order document and save the order result")
@allure.description("Test case 10: Click Preview, download the order document and verify it (BRAC letter pad, order "
                    "status, Purchase Order number, item, totals, amount in words, delivery date and place), then log "
                    "out and save the order result.")
@pytest.mark.order(10)
def test_10_verify_order_preview(page):
    """
    Test case 10: Order preview. Continues on the order details page of Test case 9.

    Steps:
        1. Click Preview (ERP; log in with the ResetHub link when the ERP login page is shown): download the order
           document and verify the preview address (order reference, order status, BRAC letter pad), the Purchase
           Order number, the item details, totals, amount in words and the 2 delivery schedules.
        2. Log out from the Digital Marketplace.
        3. Save the order result (whitelisted_blacklisted_non_agreement_order_result.json).
    """
    global order_preview, order_result
    assert order_details.get("action_history") is not None, \
        "Test case 9 must pass first: order details information is not verified"

    # Step 1: Preview and order document
    with allure.step("Step 1: Click Preview, download the order document and verify it"):
        checks, order_preview = check_order_preview(page, expected_order(), DOWNLOAD_DIR)
        attach_and_assert_checks(checks, "Order preview")

    # Step 2: Log out from the Digital Marketplace
    with allure.step("Step 2: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        HomePage(page).get_full_page_screenshot('order_initiator_logout')

    # Step 3: Save the order result
    with allure.step("Step 3: Save the order result"):
        order_result = {
            "order_reference_number": order_reference_number,
            "order_status": order_status,
            "requisition_number": req_num,
            "agreement_number": whitelisted_item["agreement_number"],
            "agreement_version": whitelisted_item["agreement_version"],
            "vendor": order_vendor,
            "order_approver": requisition["final_approver"],
            "item_code": whitelisted_item["item_code"],
            "master_item_code": whitelisted_item["master_item_code"],
            "specification": whitelisted_item["specification"],
            "cart_remarks": requisition_item_remarks,
            "uom": cart_item_after_vendor["UoM"],
            "cart_quantity": cart_quantity,
            "unit_price": whitelisted_item["unit_price"],
            "cart_attachment": cart_attachment_name,
            "order_remarks": order_remarks,
            "delivery_schedule": delivery_schedule,
            "expected_schedules": expected_schedules(),
            "order_details": order_details,
            "order_preview": order_preview,
            "page_links": page_links,
        }
        save_result("whitelisted_blacklisted_non_agreement_order_result", order_result)
        print("ORDER RESULT:", order_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in order_result.items()),
            name="Saved order result",
            attachment_type=allure.attachment_type.TEXT
        )
