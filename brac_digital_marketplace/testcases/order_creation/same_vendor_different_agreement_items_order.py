from dotenv import load_dotenv
import os
import re
import base64
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse, parse_qs
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
# Requisition item remarks (both items of the requisition)
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
# First item in the shopping cart: new remarks (max 500 characters, all special characters; the remarks field
# takes no more than 500 characters), new attachment and new quantity
cart_item_remarks = os.getenv("test_requisition_item_remarks_500", "")
CART_REMARKS_EXTRA_CHARACTERS = " extra characters after 500"
cart_attachment_file = os.getenv("test_requisition_attachment_file_png")
fractional_cart_qty = os.getenv("test_fractional_cart_qty")
# First item: 2 delivery schedules (same values as marketplace_staging_sanity.py);
# second item: Auto Generate schedule and receiving person
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

from utils.test_data_store import load_result, save_result
from brac_digital_marketplace.testcases.order_creation.order_page_links import check_checkout_page_links, \
    check_cart_item_links, check_order_details_all_products_links, in_page_order, check_confirm_order_rows_links
from utils.attachment_rules import same_file_type
from utils.remarks_rules import check_remarks_length, expected_remarks_display, same_remarks
from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.shopping_cart import ShoppingCart
from pages.digital_marketplace.public_side.checkout_page import CheckoutPage
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails

# Requisition of same_vendor_different_agreement_items_requisition.py (same_vendor_agreement_requisition_result.json):
# 2 items of 2 framework agreements of the same vendor -> one marketplace order
requisition = {}
req_num = ''
order_vendor = ''
# First item: attachment, quantity and remarks updated in the shopping cart
first_item = {}
# Second item: stays as it was created in the requisition (attachment, quantity, remarks)
second_item = {}
# Shopping cart (Test case 1-3), by FA No.
cart_items_before_vendor = {}
cart_items_after_vendor = {}
cart_link_results = {}
attachment_remove_message = ''
cart_attachment_name = ''
cart_quantity = ''
cart_checked_out = False
# Links of the delivery schedule (Test case 4) and the confirm order page (Test case 6)
schedule_links = {}
confirm_links = {}
# Delivery schedule (Test case 5)
requisition_schedule = []
delivery_schedule = ''
# Marketplace order (Test case 5)
order_reference_number = ''
order_status = ''
# Order details page (Test case 6 and 7)
order_details_information = {}
order_details_products = {}
order_details_delivery_schedule = []
order_action_history = []
order_details_links = {}
# Order preview (Test case 8)
order_preview = {}
# Order result for the pending approval test file
order_result = {}


def to_amount(value):
    # "BDT 5,080.00" -> Decimal("5080.00")
    return Decimal(str(value).replace("BDT", "").replace(",", "").strip()).quantize(Decimal("0.01"))


def numbers_in_text(text):
    # All numbers of a text as Decimal, e.g. "10.5 5080 53340.00" -> {10.5, 5080, 53340.00} (10.5 == 10.50)
    numbers = set()
    for number in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            numbers.add(Decimal(number.replace(",", "")))
        except InvalidOperation:
            pass
    return numbers


def add_check(checks, check, expected, actual, passed):
    checks.append((check, expected, actual, "PASS" if passed else "FAIL"))


def attach_and_assert_checks(checks, title):
    # All checks in Allure (expected / actual / result); the test fails if any check failed
    allure.attach(
        "\n".join(f"{check}: expected {expected} | actual {actual} | {result}" for check, expected, actual, result in checks),
        name=title,
        attachment_type=allure.attachment_type.TEXT
    )
    failed_checks = [f"{check}: expected {expected}, found {actual}"
                     for check, expected, actual, result in checks if result == "FAIL"]
    assert not failed_checks, f"{title}:\n" + "\n".join(failed_checks)


def is_first_item(item):
    return item["agreement_number"] == first_item["agreement_number"]


def cart_start_quantity(item):
    # Why: when part of the requisition was ordered before, the cart shows the remaining quantity; When: the quantity
    # of an item that is not changed in the cart (set by Test case 1-2, the requisition quantity before that)
    return item.get("remaining_quantity", item["quantity"])


def expected_quantity(item):
    # First item: shopping cart quantity; second item: requisition quantity
    return cart_quantity if is_first_item(item) else cart_start_quantity(item)


def expected_remarks(item):
    # First item: shopping cart remarks; second item: requisition remarks
    return cart_item_remarks if is_first_item(item) else requisition_item_remarks


def expected_attachment(item):
    # First item: shopping cart attachment; second item: requisition attachment
    return cart_attachment_name if is_first_item(item) else item["attachment_name"]


def item_total(item):
    return (to_amount(expected_quantity(item)) * to_amount(item["unit_price"])).quantize(Decimal("0.01"))


def order_total():
    return item_total(first_item) + item_total(second_item)


def first_item_remaining_quantity():
    return to_amount(cart_quantity) - to_amount(delivery_schedule_quantity)


def expected_schedules():
    # (item, quantity, location, receiver): first item 2 schedules, second item the auto generated schedule
    # (its location is the requisition delivery address)
    return [(first_item, to_amount(delivery_schedule_quantity), manual_delivery_location_1, receiving_pin_1),
            (first_item, first_item_remaining_quantity(), manual_delivery_location_2, order_initiator),
            (second_item, to_amount(cart_start_quantity(second_item)), None, order_initiator)]


def wait_for_erp_address(erp_tab):
    erp_tab.wait_for_url(lambda url: urlparse(url).netloc == urlparse(erp_url).netloc, timeout=60000,
                         wait_until="commit")


def open_erp_requisition(open_tab_action):
    # Requisition link opens ERP staging: log in as the same user (ResetHub) when the ERP login page is shown
    erp_tab = open_tab_action()
    wait_for_erp_address(erp_tab)
    if RequisitionDetailsInformation(erp_tab).is_erp_login_page():
        reset_page = ResetHubPage(erp_tab)
        reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=proj_user))
        erp_tab.close()
        erp_tab = open_tab_action()
        wait_for_erp_address(erp_tab)
    return erp_tab


def close_tabs(tabs, page):
    # Why: a link can open 1 or 2 tabs; When: after reading the opened page, to close them all and go back
    HomePage(page).close_opened_tabs(tabs)


def check_order_details_requisition_link(order_details_page, get_link, screenshot_name):
    # Order details requisition link: opens the ERP requisition details, sometimes in 2 tabs. Log in as the
    # same user (ResetHub) when the ERP login page is shown; read the requisition and close ALL opened tabs
    # before going back to the order details page
    page = order_details_page.page
    erp_tabs = order_details_page.open_link_all_tabs(get_link())
    for erp_tab in erp_tabs:
        wait_for_erp_address(erp_tab)
    if any(RequisitionDetailsInformation(erp_tab).is_erp_login_page() for erp_tab in erp_tabs):
        reset_page = ResetHubPage(erp_tabs[0])
        reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=proj_user))
        close_tabs(erp_tabs, page)
        erp_tabs = order_details_page.open_link_all_tabs(get_link())
        for erp_tab in erp_tabs:
            wait_for_erp_address(erp_tab)
    # With 2 opened tabs the first one can be behind the second one: bring it to the front before reading it
    erp_tabs[0].bring_to_front()
    erp_information = RequisitionDetailsInformation(erp_tabs[0]).get_requisition_information()
    RequisitionDetailsInformation(erp_tabs[0]).get_full_page_screenshot(screenshot_name)
    opened_tabs = len(erp_tabs)
    close_tabs(erp_tabs, page)
    print(f"Requisition link: {opened_tabs} tab(s) opened and closed")
    return erp_information, opened_tabs


def product_item_code(product):
    # Agreement item code of an order details product, e.g. "([FWI036581] - Water Tank ...)" -> FWI036581
    return next((item["item_code"] for item in (first_item, second_item) if item["item_code"] in product["Agreement item"]),
                product["Agreement item"])


def check_item_attachments(download_attachment, label):
    # Why: each checkout attachment icon must give an item attachment (first item: cart attachment, second item:
    # requisition attachment; same file type); When: delivery schedule and confirm order links checks
    checks = []
    expected_attachments = {expected_attachment(first_item), expected_attachment(second_item)}
    for index in range(2):
        downloaded_file = download_attachment(index)
        matching = [name for name in expected_attachments if same_file_type(downloaded_file, name)]
        add_check(checks, f"{label} attachment {index + 1}", " or ".join(sorted(expected_attachments)),
                  matching[0] if matching else downloaded_file.name, bool(matching))
        expected_attachments -= set(matching[:1])
    add_check(checks, f"{label} attachments of both items", "none missing",
              ", ".join(expected_attachments) or "none missing", not expected_attachments)
    return checks


def confirm_order_items():
    # Why: the confirm order links are checked row by row with the expected values of each item; When: Test case 6
    return [{"name": f"item {number}", "agreement_number": item["agreement_number"], "item_code": item["item_code"],
             "product_name": cart_items_after_vendor[item["agreement_number"]]["Agreement item name"],
             "attachment_name": expected_attachment(item)}
            for number, item in ((1, first_item), (2, second_item))]


def same_date(first_date, second_date):
    # Why: ERP shows "10-10-2026" and the marketplace "10/10/2026"; When: requisition date checks
    return bool(first_date) and re.findall(r"\d+", first_date) == re.findall(r"\d+", second_date)


def item_products():
    # Why: the product link text is the agreement item name of each cart item; When: checkout product link checks
    return {cart_items_after_vendor[item["agreement_number"]]["Agreement item name"]: [item["item_code"]]
            for item in (first_item, second_item)}


def get_cart_rows_by_fa(cart_page):
    # Cart rows of the requisition by FA No.
    return {row.locator("a.item-framework-link").get_attribute("data-framework-number"): row
            for row in cart_page.get_requisition_cart_rows(requisition_number=req_num)}


def verify_cart_item(cart_page, item_row, item, label, attachment_name, remarks, quantity):
    # Why: the cart item must have its requisition values and link to the requisition (ERP), agreement attachment,
    # product details page and item attachment; When: before and after the vendor selection
    cart_item = cart_page.read_cart_item_cell(item_row)
    checks = []
    add_check(checks, "Master item", item["master_item_code"], cart_item["Master item"],
              cart_item["Master item"].startswith(item["master_item_code"]))
    add_check(checks, "Requisition number", req_num, cart_item["Requisition"], cart_item["Requisition"] == req_num)
    add_check(checks, "Framework agreement number", item["agreement_number"], cart_item["FA No."],
              cart_item["FA No."] == item["agreement_number"])
    add_check(checks, "Agreement item code", item["item_code"], cart_item["Agreement item code"],
              cart_item["Agreement item code"] == item["item_code"])
    add_check(checks, "Agreement item specification", item["specification"], cart_item["Specification"],
              cart_item["Specification"] == " ".join(item["specification"].split()))
    add_check(checks, "Remarks", expected_remarks_display(remarks), cart_item["Remarks"] or "(blank)",
              same_remarks(remarks, cart_item["Remarks"]) or (not remarks and not cart_item["Remarks"]))
    add_check(checks, "Attachment", attachment_name, cart_item["Attachment path"] or "(no icon)",
              cart_item["Attachment path"].endswith(attachment_name))
    add_check(checks, "Qty.", quantity, cart_item["Qty."], to_amount(cart_item["Qty."]) == to_amount(quantity))
    add_check(checks, "Unit Price", item["unit_price"], cart_item["Unit Price"],
              to_amount(cart_item["Unit Price"]) == to_amount(item["unit_price"]))

    # Links: requisition details (ERP; all opened tabs closed), agreement attachment download, product details page
    # and item attachment download (same file type)
    link_checks, cart_link_results[label] = check_cart_item_links(
        cart_page.page, item_row, req_num, item["item_code"], attachment_name, label, DOWNLOAD_DIR)
    print(f"CART ITEM ({label}):", cart_item)
    attach_and_assert_checks(checks + link_checks, f"Shopping cart item and links ({label})")
    return cart_item


def note_earlier_cart_changes(label, changes):
    # Why: "Update shopping cart" saves the cart changes, so a checkout that was not confirmed (an earlier run that
    # stopped) leaves them in the cart; When: the cart item already has the changes of the cart preparation test
    message = f"The cart item keeps the cart changes of an earlier unconfirmed checkout: {changes}"
    print(f"EARLIER CART CHANGES ({label}):", changes)
    allure.attach(message, name=f"Earlier cart changes ({label})", attachment_type=allure.attachment_type.TEXT)


def verify_requisition_cart_items(cart_page, stage):
    # Both items of the requisition in the shopping cart: requisition attachment, quantity and remarks
    cart_rows = get_cart_rows_by_fa(cart_page)
    assert len(cart_rows) == 2, f"Both requisition items must be in the cart, found {list(cart_rows)}"
    cart_items = {}
    # FIFO: the items are checked from the top cart row down
    for number, item in in_page_order(((1, first_item), (2, second_item)),
                                      lambda numbered: cart_rows.get(numbered[1]["agreement_number"])):
        with allure.step(f"Item {number}: {item['item_name']} ({item['agreement_number']})"):
            assert item["agreement_number"] in cart_rows, f"{item['agreement_number']} not found in the cart"
            attachment_name, remarks, quantity = item["attachment_name"], requisition_item_remarks, item["quantity"]
            # Part of the requisition quantity ordered before: the cart shows the remaining quantity
            shown_quantity = cart_page.read_cart_item_cell(cart_rows[item["agreement_number"]])["Qty."]
            if Decimal(0) < to_amount(shown_quantity) < to_amount(item["quantity"]):
                item["remaining_quantity"] = quantity = shown_quantity
                note_earlier_cart_changes(f"{stage}_item_{number}", f"remaining quantity {shown_quantity} of "
                                                                    f"{item['quantity']} (part ordered before)")
            if item is first_item:
                # Cart changes of Test case 3 already in the cart (earlier unconfirmed checkout): expected instead
                # of the requisition values
                shown = cart_page.read_cart_item_cell(cart_rows[item["agreement_number"]])
                if to_amount(shown["Qty."]) == to_amount(fractional_cart_qty) and \
                        (shown["Attachment path"] or "").endswith(cart_attachment_file):
                    attachment_name, remarks, quantity = cart_attachment_file, cart_item_remarks[:500], fractional_cart_qty
                    note_earlier_cart_changes(f"{stage}_item_1", f"quantity {fractional_cart_qty}, attachment "
                                                                 f"{cart_attachment_file}, remarks (500 characters)")
            cart_items[item["agreement_number"]] = verify_cart_item(
                cart_page, cart_rows[item["agreement_number"]], item, f"{stage}_item_{number}",
                attachment_name=attachment_name, remarks=remarks, quantity=quantity)
    return cart_items


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Items Before Vendor Selection")
@allure.title("Test_case_1: Verify shopping cart items before vendor selection")
@allure.description("Test case 1: Before the vendor selection, verify both items of the requisition (2 framework "
                    "agreements of the same vendor) in the shopping cart (master item - requisition, FA, agreement "
                    "item, remarks, attachment, quantity, unit price) and their links.")
@pytest.mark.order(1)
def test_1_verify_cart_items_before_vendor_selection(page):
    """
    Test case 1: Verify the shopping cart items of the requisition before the vendor selection.

    Steps:
        1. Load the requisition of same_vendor_different_agreement_items_requisition.py
           (same_vendor_agreement_requisition_result.json): 'first_item' (updated in the cart) and
           'second_item' (stays as created in the requisition).
        2. Log in to the Digital Marketplace as the order initiator ('proj_user').
        3. Shopping cart, before vendor selection: both items are in the cart; verify each Item/Service name &
           Specification and its links: requisition number (ERP requisition details), FA No. (agreement
           attachment or ERP message), agreement item (item details page), attachment (= requisition attachment).
        No logout: Test case 2 continues in the shopping cart.

    All scenario values are read from .env.
    """
    global requisition, req_num, order_vendor, first_item, second_item, cart_items_before_vendor

    required_env_values = {
        "test_user_name": proj_user,
        "test_env": proj_env,
        "test_url": erp_url,
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_requisition_item_remarks": requisition_item_remarks,
        "test_requisition_attachment_file_png": cart_attachment_file,
        "test_fractional_cart_qty": fractional_cart_qty,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    check_remarks_length("test_requisition_item_remarks_500", cart_item_remarks)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    login_page = LoginPage(page)
    home_page = HomePage(page)
    cart_page = ShoppingCart(page)

    # Step 1: Requisition from same_vendor_different_agreement_items_requisition.py
    with allure.step("Step 1: Load the requisition result of same_vendor_different_agreement_items_requisition.py"):
        requisition = load_result("same_vendor_agreement_requisition_result",
                                  created_by="same_vendor_different_agreement_items_requisition.py")
        req_num = requisition["requisition_number"]
        order_vendor = requisition["vendor"]
        assert len(requisition["items"]) == 2, f"The requisition must have 2 items, found {len(requisition['items'])}"
        first_item, second_item = requisition["items"]
        print("REQ NUM:", req_num)
        print("FIRST ITEM:", first_item)
        print("SECOND ITEM:", second_item)
        # New cart attachment of the first item: shopping cart rules and different from the requisition attachment
        cart_attachment_path = UTILS_DIR / cart_attachment_file
        assert cart_attachment_path.is_file(), f"Cart attachment not found in utils: {cart_attachment_path}"
        assert cart_attachment_path.suffix.lower() in CART_ATTACHMENT_TYPES, \
            f"Cart attachment type {cart_attachment_path.suffix} is not allowed: {sorted(CART_ATTACHMENT_TYPES)}"
        assert cart_attachment_path.stat().st_size / (1024 * 1024) <= MAX_CART_ATTACHMENT_SIZE_MB, \
            f"Cart attachment must be max {MAX_CART_ATTACHMENT_SIZE_MB} MB"
        assert cart_attachment_path.name not in (first_item["attachment_name"], second_item["attachment_name"]), \
            "The new cart attachment must be different from the requisition attachments"
        assert to_amount(fractional_cart_qty) != to_amount(first_item["quantity"]), \
            "test_fractional_cart_qty must be different from the first item requisition quantity"
        allure.attach(
            "\n".join(f"Item {number}: " + " | ".join(f"{key}: {value}" for key, value in item.items())
                      for number, item in ((1, first_item), (2, second_item))),
            name="Requisition items",
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
    with allure.step(f"Step 3: Verify requisition {req_num} items in the shopping cart (before vendor selection)"):
        home_page.goto_shopping_cart()
        assert cart_page.wait_for_requisition_in_cart(requisition_number=req_num), \
            f"Requisition {req_num} is not synced to the shopping cart"
        cart_page.get_full_page_screenshot('order_cart_before_vendor')
        cart_items_before_vendor = verify_requisition_cart_items(cart_page, "before_vendor")


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Items After Vendor Selection")
@allure.title("Test_case_2: Verify shopping cart items after vendor selection")
@allure.description("Test case 2: Select the requisition vendor (same vendor for both framework agreements) and "
                    "verify both items of the requisition in the shopping cart and their links again.")
@pytest.mark.order(2)
def test_2_verify_cart_items_after_vendor_selection(page):
    """
    Test case 2: Select the vendor and verify the shopping cart items of the requisition again.
    Continues in the shopping cart of Test case 1 (no new login).

    Steps:
        1. Select the vendor of the requisition (only this requisition stays ticked).
        2. Verify both items and their links again (same checks as Test case 1).
        No logout: Test case 3 continues in the shopping cart.
    """
    global cart_items_after_vendor
    assert cart_items_before_vendor, "Test case 1 must pass first: shopping cart items are not verified"

    cart_page = ShoppingCart(page)

    # Step 1: Vendor selection
    with allure.step(f"Step 1: Select vendor {order_vendor} for requisition {req_num}"):
        cart_page.select_vendor_for_requisition_found(requisition_number=req_num)
        # The shopping cart can have many requisitions (business data): keep only this requisition ticked
        assert cart_page.select_vendor_keep_only_requisition(vendor_name=order_vendor, requisition_number=req_num), \
            f"Vendor {order_vendor} not found in the shopping cart"
        cart_page.get_full_page_screenshot('order_cart_after_vendor')

    # Step 2: The same checks again
    with allure.step("Step 2: Verify both items and their links again"):
        cart_items_after_vendor = verify_requisition_cart_items(cart_page, "after_vendor")


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Preparation")
@allure.title("Test_case_3: Update the first item (attachment, quantity, remarks) and checkout")
@allure.description("Test case 3: First item: remove the requisition attachment (Yes) and upload a new attachment, "
                    "update the remarks and the quantity. Second item stays as created in the requisition "
                    "(attachment, quantity, remarks). Checkout.")
@pytest.mark.order(3)
def test_3_update_first_item_and_checkout(page):
    """
    Test case 3: Prepare the shopping cart for checkout.
    Continues in the shopping cart of Test case 2 (no new login).

    Steps:
        1. First item: remove the requisition attachment (pop-up Yes) and upload a new attachment
           ('test_requisition_attachment_file_png', different from the requisition attachments).
        2. First item: new remarks ('test_cart_item_remarks', 0 to 500 characters) and quantity
           ('test_fractional_cart_qty'), then Update shopping cart.
        3. Verify the first item (new attachment, remarks, quantity) and the second item (requisition attachment,
           remarks and quantity, not changed).
        4. Accept terms of service and checkout.

    All scenario values are read from .env.
    """
    global attachment_remove_message, cart_attachment_name, cart_quantity, cart_checked_out
    assert cart_items_after_vendor, "Test case 2 must pass first: vendor is not selected"

    cart_page = ShoppingCart(page)
    cart_attachment_path = UTILS_DIR / cart_attachment_file

    # Step 1: First item: replace the requisition attachment with a new attachment
    with allure.step(f"Step 1: First item - remove {first_item['attachment_name']} and upload {cart_attachment_path.name}"):
        first_row = get_cart_rows_by_fa(cart_page)[first_item["agreement_number"]]
        attachment_remove_message = cart_page.remove_cart_attachment(first_row)
        print("ATTACHMENT REMOVE CONFIRMATION:", attachment_remove_message)
        cart_page.get_full_page_screenshot('order_cart_first_item_attachment_removed')
        cart_page.upload_cart_item_attachment(first_row, cart_attachment_path)
        cart_attachment_name = cart_attachment_path.name
        allure.attach(
            f"Removed: {first_item['attachment_name']}\nRemove confirmation: {attachment_remove_message}\n"
            f"Uploaded: {cart_attachment_name}",
            name="First item cart attachment replaced",
            attachment_type=allure.attachment_type.TEXT
        )
        cart_page.get_full_page_screenshot('order_cart_first_item_attachment_uploaded')

    # Step 2: First item: remarks and quantity, then Update shopping cart
    with allure.step(f"Step 2: First item - remarks ({len(cart_item_remarks)} characters) and quantity {fractional_cart_qty}"):
        # The remarks field takes max 500 characters: the extra characters after 500 are not entered
        cart_page.fill_cart_item_remarks(first_row, cart_item_remarks + CART_REMARKS_EXTRA_CHARACTERS)
        entered_remarks = cart_page.get_cart_item_remarks_input(first_row)
        allure.attach(
            f"Typed: {len(cart_item_remarks + CART_REMARKS_EXTRA_CHARACTERS)} characters\n"
            f"Entered: {len(entered_remarks)} characters\n{entered_remarks}",
            name="First item cart remarks (max 500 characters)",
            attachment_type=allure.attachment_type.TEXT
        )
        assert entered_remarks == cart_item_remarks[:500], \
            f"Cart remarks field must keep the first 500 characters only, found {len(entered_remarks)} characters"
        cart_page.update_cart_item_quantity(first_row, fractional_cart_qty)
        cart_quantity = fractional_cart_qty
        cart_page.get_full_page_screenshot('order_cart_first_item_updated')

    # Step 3: First item updated, second item not changed
    with allure.step("Step 3: Verify the first item (updated) and the second item (not changed)"):
        cart_rows = get_cart_rows_by_fa(cart_page)
        checks = []
        for number, item in ((1, first_item), (2, second_item)):
            cart_item = cart_page.read_cart_item_cell(cart_rows[item["agreement_number"]])
            add_check(checks, f"Item {number} Attachment", expected_attachment(item), cart_item["Attachment path"] or "-",
                      cart_item["Attachment path"].endswith(expected_attachment(item)))
            add_check(checks, f"Item {number} Remarks", expected_remarks_display(expected_remarks(item)),
                      cart_item["Remarks"] or "(blank)",
                      same_remarks(expected_remarks(item), cart_item["Remarks"])
                      or (not expected_remarks(item) and not cart_item["Remarks"]))
            add_check(checks, f"Item {number} Qty.", expected_quantity(item), cart_item["Qty."],
                      to_amount(cart_item["Qty."]) == to_amount(expected_quantity(item)))
            add_check(checks, f"Item {number} Total Price (Qty. x Unit Price)", item_total(item), cart_item["Total Price"],
                      to_amount(cart_item["Total Price"]) == item_total(item))
        attach_and_assert_checks(checks, "Shopping cart items before checkout")

    # Step 4: Accept terms of service and checkout
    with allure.step("Step 4: Accept terms of service and checkout"):
        cart_page.cart_page_checkout()
        cart_checked_out = True
        cart_page.get_full_page_screenshot('order_cart_checkout')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Links")
@allure.title("Test_case_4: Verify delivery schedule links")
@allure.description("Test case 4: On the delivery schedule, open the requisition details, agreement attachments and "
                    "product details links (a link that is not on this step is noted) and download the item attachments.")
@pytest.mark.order(4)
def test_4_verify_delivery_schedule_links(page):
    """
    Test case 4: Delivery schedule links.

    Steps:
        1. Requisition details (ERP), agreement attachment download (both FAs) and product details links (both
           items): a link that is not on the delivery schedule is noted in the report.
        2. Item attachments: first item the shopping cart attachment, second item the requisition attachment
           (same file type).
    """
    global schedule_links
    assert cart_checked_out, "Test case 3 must pass first: the cart is not checked out"
    checkout_page = CheckoutPage(page)

    # Step 1-2: Links and item attachments of the delivery schedule
    with allure.step("Step 1-2: Open the requisition details, agreement attachments, product details and item attachments"):
        link_checks, schedule_links = check_checkout_page_links(
            page, req_num, [item["agreement_number"] for item in (first_item, second_item)], item_products(),
            'order_schedule', links_required=False, save_folder=DOWNLOAD_DIR)
        attachment_checks = check_item_attachments(
            lambda index: checkout_page.download_checkout_attachment(DOWNLOAD_DIR, index), "Delivery schedule")
        checkout_page.get_full_page_screenshot('order_schedule_links_checked')
        attach_and_assert_checks(link_checks + attachment_checks, "Delivery schedule links and item attachments")


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Preparation Window")
@allure.title("Test_case_5: Prepare delivery schedule")
@allure.description("Test case 5: Verify the Requisition Schedule and both items (quantity, remarks) with "
                    "the requisition and the shopping cart; first item: 2 delivery schedules; second item (cart "
                    "quantity = requisition quantity): Auto Generate and receiving person.")
@pytest.mark.order(5)
def test_5_prepare_delivery_schedule(page):
    """
    Test case 5: Prepare the order delivery schedule (2 items).

    Steps:
        1. Requisition Schedule: both item rows (Item, Quantity = requisition quantity, Unit of Measure,
           Delivery Details = requisition delivery address, Requisition = 'req_num').
        2. Items before the schedule: item names, cart quantities and remarks (the attachments are checked in
           Test case 4).
        3. Click Auto Generate: only the second item gets its schedule (cart quantity = requisition quantity).
        4. First item schedule 1: 'test_delivery_schedule_quantity', expected date, location 1, receiving person 1.
        5. First item schedule 2: remaining quantity, location 2 and the order initiator.
        6. Second item: Receiving Person 'order_initiator' in the auto generated schedule row.
        7. Wait until Continue is enabled and click Continue.

    All scenario values are read from .env.
    """
    global requisition_schedule, delivery_schedule
    assert schedule_links, "Test case 4 must pass first: delivery schedule links are not verified"
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

    # Step 1: Requisition Schedule (requisition quantity and delivery address of both items)
    with allure.step(f"Step 1: Verify the Requisition Schedule of {req_num} (2 items)"):
        requisition_schedule = checkout_page.get_requisition_schedule_rows()
        checkout_page.get_full_page_screenshot('order_schedule_requisition_schedule')
        checks = []
        for number, item in ((1, first_item), (2, second_item)):
            item_name = cart_items_after_vendor[item["agreement_number"]]["Agreement item name"]
            uom = cart_items_after_vendor[item["agreement_number"]]["UoM"]
            schedule_row = next((row for row in requisition_schedule
                                 if row.get("Requisition") == req_num and item_name in row.get("Item", "")), {})
            add_check(checks, f"Item {number} Requisition Schedule row", item_name, schedule_row.get("Item", "not found"),
                      bool(schedule_row))
            add_check(checks, f"Item {number} Quantity (requisition / remaining quantity)",
                      f"{item['quantity']} or {cart_start_quantity(item)}",
                      schedule_row.get("Quantity", "-"),
                      bool(schedule_row) and to_amount(schedule_row["Quantity"]) in
                      (to_amount(item["quantity"]), to_amount(cart_start_quantity(item))))
            add_check(checks, f"Item {number} Unit of Measure", uom, schedule_row.get("Unit of Measure", "-"),
                      schedule_row.get("Unit of Measure") == uom)
            add_check(checks, f"Item {number} Delivery Details (requisition delivery address)",
                      requisition["delivery_address"], schedule_row.get("Delivery Details", "-"),
                      requisition["delivery_address"] in schedule_row.get("Delivery Details", ""))
        attach_and_assert_checks(checks, "Requisition Schedule vs requisition")

    # Step 2: Items before the schedule: names, cart quantities, remarks and attachments
    with allure.step("Step 2: Verify both items (name, quantity, remarks) before the schedule"):
        page_text = checkout_page.get_page_text()
        page_numbers = numbers_in_text(page_text)
        checks = []
        for number, item in ((1, first_item), (2, second_item)):
            item_name = cart_items_after_vendor[item["agreement_number"]]["Agreement item name"]
            remarks = expected_remarks_display(expected_remarks(item))
            add_check(checks, f"Item {number} name", item_name, "on the page", item_name in page_text)
            add_check(checks, f"Item {number} remarks", remarks, "on the page" if remarks in page_text else "not found",
                      remarks in page_text)
            add_check(checks, f"Item {number} shopping cart quantity", expected_quantity(item),
                      "on the page" if to_amount(expected_quantity(item)) in page_numbers else "not found",
                      to_amount(expected_quantity(item)) in page_numbers)
        checkout_page.get_full_page_screenshot('order_schedule_items')
        attach_and_assert_checks(checks, "Delivery schedule window vs requisition and shopping cart")

    # Step 3: Auto Generate (second item: cart quantity = requisition quantity)
    with allure.step("Step 3: Click Auto Generate (second item)"):
        checkout_page.auto_generate_schedule()
        checkout_page.get_full_page_screenshot('order_schedule_auto_generate')

    # Step 4: First item schedule 1
    with allure.step(f"Step 4: First item schedule 1 - {delivery_schedule_quantity} to {manual_delivery_location_1}"):
        checkout_page.fractional_schedule_update_quantity(delivery_schedule_quantity=delivery_schedule_quantity)
        checkout_page.update_expected_date()
        checkout_page.delivery_schedule_preparation(location=manual_delivery_location_1, pin=receiving_pin_1)
        checkout_page.click_add_schedule_btn()
        checkout_page.wait_for_timeout(2000)
        checkout_page.get_full_page_screenshot('order_schedule_first_item_1')

    # Step 5: First item schedule 2 (remaining quantity)
    with allure.step(f"Step 5: First item schedule 2 - remaining quantity to {manual_delivery_location_2}"):
        checkout_page.delivery_schedule_preparation(location=manual_delivery_location_2, pin=order_initiator)
        checkout_page.click_add_schedule_btn()
        checkout_page.get_full_page_screenshot('order_schedule_first_item_2')

    # Step 6: Second item receiving person in the auto generated schedule row
    with allure.step(f"Step 6: Second item Receiving Person {order_initiator}"):
        checkout_page.fill_generated_schedule_receiving_person(pin=order_initiator)
        checkout_page.get_full_page_screenshot('order_schedule_second_item')

    # Step 7: Continue
    with allure.step("Step 7: Wait until Continue is enabled and click Continue"):
        delivery_schedule = (f"First item: {delivery_schedule_quantity} to {manual_delivery_location_1} "
                             f"({receiving_pin_1}); {first_item_remaining_quantity()} to {manual_delivery_location_2} "
                             f"({order_initiator}). Second item: auto generated {second_item['quantity']} "
                             f"({order_initiator})")
        print("DELIVERY SCHEDULE:", delivery_schedule)
        allure.attach(delivery_schedule, name="Delivery schedule", attachment_type=allure.attachment_type.TEXT)
        checkout_page.click_continue_when_enabled()
        checkout_page.get_full_page_screenshot('order_schedule_continue')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order Links")
@allure.title("Test_case_6: Verify confirm order links")
@allure.description("Test case 6: On the confirm order page, open the links in page order (first in, first out): "
                    "the order header agreement, then every item row from the top: requisition details (ERP), "
                    "agreement attachment, product details page and item attachment.")
@pytest.mark.order(6)
def test_6_verify_confirm_order_links(page):
    """
    Test case 6: Confirm order links.

    Steps (links opened in page order, first in, first out):
        1. Order header Framework Agreement link(s): agreement attachment download (a FA No. that is not shown in the
           header is noted; the header is checked in Test case 7).
        2. Every item row from the top: requisition details (ERP; all opened tabs closed), "FA:" agreement attachment,
           product details page and item attachment (first item the shopping cart attachment, second item the
           requisition attachment; same file type).
    """
    global confirm_links
    assert delivery_schedule, "Test case 5 must pass first: delivery schedule is not prepared"
    checkout_page = CheckoutPage(page)

    # Step 1-2: Links of the confirm order page in page order
    with allure.step("Step 1-2: Open the header agreement link, then each item row: requisition, FA, product page, attachment"):
        checkout_page.wait_for_confirm_order_step()
        link_checks, confirm_links = check_confirm_order_rows_links(
            page, req_num, [item["agreement_number"] for item in (first_item, second_item)], confirm_order_items(),
            'order_confirm', DOWNLOAD_DIR)
        checkout_page.get_full_page_screenshot('order_confirm_links_checked')
        attach_and_assert_checks(link_checks, "Confirm order links and item attachments (page order)")


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order")
@allure.title("Test_case_7: Confirm marketplace order")
@allure.description("Test case 7: Verify the confirm order information of both items (agreements, vendor, "
                    "requisition, item details, prices, delivery schedules), confirm the order (one "
                    "order for the same vendor) and get the order reference number.")
@pytest.mark.order(7)
def test_7_confirm_marketplace_order(page):
    """
    Test case 7: Confirm the marketplace order (both items, one order for the same vendor).

    Steps (each verification step has its own expected/actual checks):
        1. Order header: Vendor Name, Requisition No, Requisition Date (= ERP requisition date of Test case 6).
        2. Item rows (each item in its own row): master item, requisition, FA No., agreement item, specification,
           remarks, UoM, Qty., Unit Price, Total Price (Qty. x Unit Price).
        3. Order total (sum of both items).
        4. Expected delivery date and place: the 3 schedules of Test case 5 (quantity, date shown, location,
           receiver).
        5. Fill the order remarks ('test_order_remarks'), accept terms of service and confirm the order;
           store the order reference number.
        6. Order header Framework Agreement: both FA No. (known application issue: one FA No. is shown for an
           order with more agreements; checked last so the order is still confirmed).
        No logout: Test case 8 continues on the order details page.

    All scenario values are read from .env.
    """
    global order_reference_number
    assert confirm_links, "Test case 6 must pass first: confirm order links are not verified"
    assert order_remarks, "Missing in .env: test_order_remarks"
    check_remarks_length("test_order_remarks", order_remarks)

    checkout_page = CheckoutPage(page)
    checkout_page.wait_for_confirm_order_step()
    page_text = checkout_page.get_page_text()
    page_numbers = numbers_in_text(page_text)

    def verify_on_confirm_page(title, expected_texts, expected_numbers, screenshot_name):
        # Each expected text / number must be shown on the confirm order page; the step fails if any is missing
        checks = []
        for check, expected in expected_texts:
            add_check(checks, check, expected, "on the page" if expected in page_text else "not found",
                      expected in page_text)
        for check, expected in expected_numbers:
            add_check(checks, check, expected, "on the page" if expected in page_numbers else "not found",
                      expected in page_numbers)
        checkout_page.get_full_page_screenshot(screenshot_name)
        attach_and_assert_checks(checks, title)

    # Step 1: Order header: vendor and requisition (the Framework Agreement is checked last, Step 6)
    with allure.step("Step 1: Verify the Vendor Name, Requisition No and Requisition Date of the order header"):
        header = checkout_page.read_confirm_order_header()
        erp_requisition_date = next((value["requisition_date"] for value in confirm_links.values()
                                     if isinstance(value, dict) and "requisition_date" in value), "")
        checks = []
        add_check(checks, "Vendor Name", order_vendor, header["Vendor Name"],
                  header["Vendor Name"].lower() == order_vendor.lower())
        add_check(checks, "Requisition No", req_num, header["Requisition No"], header["Requisition No"] == req_num)
        add_check(checks, "Requisition Date (= ERP requisition date)", erp_requisition_date or "-",
                  header["Requisition Date"], same_date(erp_requisition_date, header["Requisition Date"]))
        checkout_page.get_full_page_screenshot('order_confirm_header')
        attach_and_assert_checks(checks, "Confirm order header")

    # Step 2: Item rows: every value in the row of its item
    with allure.step("Step 2: Verify each item row (master item, requisition, FA, agreement item, specification, "
                     "remarks, UoM, Qty., Unit Price, Total Price)"):
        item_rows = [checkout_page.read_confirm_item_row(item_row)
                     for item_row in checkout_page.confirm_item_rows(req_num)]
        checks = []
        add_check(checks, "Item rows", 2, len(item_rows), len(item_rows) == 2)
        for number, item in ((1, first_item), (2, second_item)):
            row = next((row for row in item_rows if item["item_code"] in row.get("Item/Service", "")), {})
            item_text = row.get("Item/Service", "")
            add_check(checks, f"Item {number} row (agreement item code)", item["item_code"],
                      "found" if row else "not found", bool(row))
            if not row:
                continue
            for check, expected in (("Master item", item["master_item_code"]), ("Requisition", req_num),
                                    ("FA No.", item["agreement_number"]),
                                    ("Specification", " ".join(item["specification"].split())),
                                    ("Remarks", expected_remarks_display(expected_remarks(item)))):
                add_check(checks, f"Item {number} {check}", expected, "in the row" if expected in item_text else "not found",
                          expected in item_text)
            uom = cart_items_after_vendor[item["agreement_number"]]["UoM"]
            add_check(checks, f"Item {number} UoM", uom, row.get("UoM", "-"), row.get("UoM") == uom)
            for check, expected, column in (("Qty.", to_amount(expected_quantity(item)), "Qty"),
                                            ("Unit Price", to_amount(item["unit_price"]), "Unit Price"),
                                            ("Total Price (Qty. x Unit Price)", item_total(item), "Total Price")):
                add_check(checks, f"Item {number} {check}", expected, row.get(column, "-"),
                          column in row and to_amount(row[column]) == expected)
        checkout_page.get_full_page_screenshot('order_confirm_item_rows')
        attach_and_assert_checks(checks, "Confirm order item rows")

    # Step 3: Order total
    with allure.step(f"Step 3: Verify the order total {order_total()} (sum of both items)"):
        verify_on_confirm_page("Confirm order total", [], [("Order total (sum of both items)", order_total())],
                               'order_confirm_total')

    # Step 4: Expected delivery date and place (the 3 delivery schedules of Test case 5)
    with allure.step("Step 4: Verify the expected delivery date and place (first item 2 schedules, second item 1)"):
        schedule_rows = checkout_page.get_confirm_schedule_rows()
        checks = []
        add_check(checks, "Delivery schedule rows", 3, len(schedule_rows), len(schedule_rows) == 3)
        for number, (item, quantity, location, receiver) in enumerate(expected_schedules(), start=1):
            schedule_row = next((row for row in schedule_rows if to_amount(row.get("Quantity", "0")) == quantity
                                 and (not location or location in row.get("Location", ""))), {})
            add_check(checks, f"Schedule {number} quantity / location", f"{quantity} / {location or 'requisition address'}",
                      f"{schedule_row.get('Quantity', '-')} / {schedule_row.get('Location', '-')}", bool(schedule_row))
            add_check(checks, f"Schedule {number} date", "shown", schedule_row.get("Date") or "-",
                      bool(schedule_row.get("Date")))
            add_check(checks, f"Schedule {number} receiver", receiver, schedule_row.get("Receiver Info", "-"),
                      receiver in schedule_row.get("Receiver Info", ""))
        checkout_page.get_full_page_screenshot('order_confirm_delivery_schedules')
        attach_and_assert_checks(checks, "Confirm order delivery schedules")

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

    # Step 6: Order header Framework Agreement (known application issue: checked after the order is confirmed)
    with allure.step("Step 6: Verify the order header Framework Agreement shows both FA No."):
        checks = []
        for number, item in ((1, first_item), (2, second_item)):
            add_check(checks, f"Order header Framework Agreement (item {number})", item["agreement_number"],
                      header["Framework Agreement"], item["agreement_number"] in header["Framework Agreement"])
        attach_and_assert_checks(checks, "Confirm order header Framework Agreement")


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Details Information")
@allure.title("Test_case_8: Verify order details information")
@allure.description("Test case 8: Open the order details of the confirmed order and verify the order information, "
                    "both products, totals, Preferred Delivery Schedule and Action History with the requisition, the "
                    "shopping cart and the delivery schedule; store the Action History.")
@pytest.mark.order(8)
def test_8_verify_order_details_information(page):
    """
    Test case 8: Verify the order details information.
    Continues after the order confirmation of Test case 7 (no new login).

    Steps (each step has its own expected/actual checks):
        1. Open the order details and verify the order information: Order Reference No., Framework Agreement
           (both FAs), Order Status, Order Total (sum of both items), Order Remarks, Vendor Name; store Programme
           Name, Letter Pad Type and Order Date.
        2. Product(s): both products, found by agreement item code (master item - requisition, agreement item,
           specification, remarks, attachment, UoM, Quantity, Unit Price, Total Price) and the Sub-Total.
        3. Preferred Delivery Schedule: the 3 schedules of Test case 4 (quantity, location, receiver).
        4. Action History: store all rows; the order is submitted for approval by the requisition initiator;
           Order Date = the date it was submitted.
        5. Order Date (= the date the order was submitted) and Framework Agreements: the order information shows
           both FAs and each product shows its own FA (checked last, so all other order details are verified first).

    All scenario values are read from .env.
    """
    global order_status, order_details_information, order_details_products, order_details_delivery_schedule, \
        order_action_history
    assert order_reference_number, "Test case 7 must pass first: order is not confirmed"

    checkout_page = CheckoutPage(page)
    order_details_page = OrderDetails(page)
    # Order Date and Framework Agreement checks (asserted in Step 5)
    last_step_checks = []

    # Step 1: Order information
    with allure.step(f"Step 1: Open the order details of {order_reference_number} and verify the order information"):
        order_status = checkout_page.goto_public_side_order_details_view()
        print("ORDER STATUS:", order_status)
        order_details_information = {
            label: order_details_page.get_order_field(label)
            for label in ("Order Reference No", "Framework Agreement", "Order Date", "Order Status", "Order Total",
                          "Letter Pad Type", "Order Remarks", "Vendor Name", "Programme Name")}
        print("ORDER DETAILS INFORMATION:", order_details_information)
        order_details_page.get_full_page_screenshot('order_details_information')
        checks = []
        add_check(checks, "Order Reference No", order_reference_number, order_details_information["Order Reference No"],
                  order_details_information["Order Reference No"] == order_reference_number)
        for number, item in ((1, first_item), (2, second_item)):
            add_check(last_step_checks, f"Order information Framework Agreement (item {number})", item["agreement_number"],
                      order_details_information["Framework Agreement"],
                      item["agreement_number"] in order_details_information["Framework Agreement"])
        add_check(checks, "Order Status", "not empty", order_details_information["Order Status"],
                  bool(order_details_information["Order Status"]))
        add_check(checks, "Order Total (sum of both items)", order_total(), order_details_information["Order Total"],
                  to_amount(order_details_information["Order Total"]) == order_total())
        add_check(checks, "Order Remarks", order_remarks, order_details_information["Order Remarks"],
                  same_remarks(order_remarks, order_details_information["Order Remarks"]))
        add_check(checks, "Vendor Name", order_vendor, order_details_information["Vendor Name"],
                  order_details_information["Vendor Name"].lower() == order_vendor.lower())
        attach_and_assert_checks(checks, "Order details information")

    # Step 2: Product(s) and Sub-Total
    with allure.step("Step 2: Verify both products and the Sub-Total"):
        product_rows = order_details_page.get_product_rows()
        products = [order_details_page.read_product_row(product_row) for product_row in product_rows]
        # Products by agreement item code (the FA No. of each product is checked in Step 5)
        order_details_products = {product_item_code(product): product for product in products}
        sub_total = order_details_page.get_sub_total()
        checks = []
        add_check(checks, "Products", 2, len(product_rows), len(product_rows) == 2)
        for number, item in ((1, first_item), (2, second_item)):
            product = order_details_products.get(item["item_code"], {})
            uom = cart_items_after_vendor[item["agreement_number"]]["UoM"]
            add_check(checks, f"Item {number} product row (agreement item code)", item["item_code"],
                      product.get("Agreement item", "not found"), bool(product))
            if not product:
                continue
            add_check(last_step_checks, f"Item {number} ({item['item_code']}) product FA No.", item["agreement_number"],
                      product["FA No."], product["FA No."] == item["agreement_number"])
            add_check(checks, f"Item {number} Master item", item["master_item_code"], product["Master item"],
                      product["Master item"].startswith(item["master_item_code"]))
            add_check(checks, f"Item {number} Requisition number", req_num, product["Requisition"],
                      product["Requisition"] == req_num)
            add_check(checks, f"Item {number} Agreement item", item["item_code"], product["Agreement item"],
                      item["item_code"] in product["Agreement item"])
            add_check(checks, f"Item {number} Specification", item["specification"], product["Specification"],
                      product["Specification"] == " ".join(item["specification"].split()))
            add_check(checks, f"Item {number} Remarks", expected_remarks_display(expected_remarks(item)),
                      product["Remarks"], same_remarks(expected_remarks(item), product["Remarks"]))
            add_check(checks, f"Item {number} Attachment icon", "shown",
                      "shown" if product["Attachment icon"] else "not shown", product["Attachment icon"])
            add_check(checks, f"Item {number} UoM", uom, product["UoM"], product["UoM"] == uom)
            add_check(checks, f"Item {number} Quantity", expected_quantity(item), product["Quantity"],
                      to_amount(product["Quantity"]) == to_amount(expected_quantity(item)))
            add_check(checks, f"Item {number} Unit Price", item["unit_price"], product["Unit Price"],
                      to_amount(product["Unit Price"]) == to_amount(item["unit_price"]))
            add_check(checks, f"Item {number} Total Price (Qty. x Unit Price)", item_total(item), product["Total Price"],
                      to_amount(product["Total Price"]) == item_total(item))
        add_check(checks, "Sub-Total (sum of both items)", order_total(), sub_total, to_amount(sub_total) == order_total())
        order_details_page.get_full_page_screenshot('order_details_products')
        attach_and_assert_checks(checks, "Order details products and totals")

    # Step 3: Preferred Delivery Schedule (the 3 schedules of Test case 4)
    with allure.step("Step 3: Verify the Preferred Delivery Schedule (first item 2 schedules, second item 1)"):
        order_details_delivery_schedule = order_details_page.get_all_preferred_delivery_schedules()
        checks = []
        add_check(checks, "Delivery schedules", 3, len(order_details_delivery_schedule),
                  len(order_details_delivery_schedule) == 3)
        for number, (item, quantity, location, receiver) in enumerate(expected_schedules(), start=1):
            schedule = next((row for row in order_details_delivery_schedule
                             if to_amount(row.get("Quantity", "0")) == quantity
                             and (location is None or location.lower() in row.get("Location", "").lower())), {})
            add_check(checks, f"Schedule {number} ({item['item_code']}) Quantity", quantity,
                      schedule.get("Quantity", "not found"), bool(schedule))
            add_check(checks, f"Schedule {number} Location", location or "requisition delivery location",
                      schedule.get("Location", "-"), bool(schedule) and bool(schedule.get("Location")))
            add_check(checks, f"Schedule {number} Receiver Info", receiver, schedule.get("Receiver Info", "-"),
                      receiver in schedule.get("Receiver Info", ""))
        order_details_page.get_full_page_screenshot('order_details_delivery_schedule')
        attach_and_assert_checks(checks, "Order details Preferred Delivery Schedule")

    # Step 4: Action History (stored) and Order Date
    with allure.step("Step 4: Store the Action History and verify the order submission"):
        order_action_history = order_details_page.get_action_history()
        print("ACTION HISTORY:", order_action_history)
        allure.attach(
            "\n".join(" | ".join(f"{title}: {value}" for title, value in row.items()) for row in order_action_history),
            name="Order Action History",
            attachment_type=allure.attachment_type.TEXT
        )
        submitted_rows = [row for row in order_action_history if row.get("Order Status") == "Submitted for Approval"
                          and proj_user in row.get("Action Taken By", "")]
        submitted_date = submitted_rows[0].get("Time", "").split(" ")[0] if submitted_rows else ""
        checks = []
        add_check(checks, "Action History - Submitted for Approval by the requisition initiator", proj_user,
                  submitted_rows[0]["Action Taken By"] if submitted_rows else "-", bool(submitted_rows))
        add_check(last_step_checks, "Order Date (date the order was submitted)", submitted_date,
                  order_details_information["Order Date"], order_details_information["Order Date"] == submitted_date)
        order_details_page.get_full_page_screenshot('order_details_action_history')
        attach_and_assert_checks(checks, "Order details Action History")

    # Step 5: Order Date, Framework Agreements of the order and of each product
    with allure.step("Step 5: Verify the Order Date and the Framework Agreements of the order and of each product"):
        attach_and_assert_checks(last_step_checks, "Order details Order Date and Framework Agreements")


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Details Links")
@allure.title("Test_case_9: Verify order details links")
@allure.description("Test case 9: Download the agreement attachments (order information agreement numbers first), open "
                    "the requisition details (ERP), both product FA links, product details pages and item attachments, "
                    "the Preferred Delivery Schedule product and requisition links, then save the order result.")
@pytest.mark.order(9)
def test_9_verify_order_details_links(page):
    """
    Test case 9: Verify the links of the order details.
    Continues on the order details page of Test case 8 (no new login).

    Steps:
        1-4. Agreement attachment download: first the agreement numbers of the order information (both FAs must be
             shown: checked in Step 8, after the result is saved), then each product FA link; requisition details
             (ERP; ResetHub login when the ERP login page is shown; all opened tabs closed); product details page
             and item attachment of both products (first item: cart attachment, second item: requisition
             attachment; same file type).
        5. Preferred Delivery Schedule product links (both): the product details pages.
        6. Preferred Delivery Schedule requisition link: ERP requisition details (all opened tabs closed).
        7. Save the order result (same_vendor_different_agreement_items_order_result.json).
        8. Order information Framework Agreements: both FAs are shown.
        No logout: Test case 8 continues on the order details page.
    """
    global order_details_links, order_result
    assert order_details_products, "Test case 8 must pass first: order details are not verified"

    order_details_page = OrderDetails(page)
    # Order information Framework Agreement checks (asserted in Step 8)
    framework_checks = []

    # Step 1-4: Agreement attachments (agreement numbers first), requisition, product pages and item attachments
    with allure.step("Step 1-4: Download the agreement attachments, open the requisition details and product details, "
                     "download the item attachments"):
        link_checks, order_details_links["products"] = check_order_details_all_products_links(
            page, req_num, [item["agreement_number"] for item in (first_item, second_item)],
            [{"item_code": item["item_code"], "master_item_code": item["master_item_code"],
              "attachment_name": expected_attachment(item)} for item in (first_item, second_item)],
            'order_details', DOWNLOAD_DIR)
        # Known issue: the order information can show only one Framework Agreement (checked in Step 8)
        framework_checks.extend(check for check in link_checks if check[0].startswith("Order information Framework")
                                and check[0].endswith("shown"))
        attach_and_assert_checks([check for check in link_checks if check not in framework_checks],
                                 "Order details links and item attachments")

    # Step 5: Preferred Delivery Schedule product links
    with allure.step("Step 5: Open both Preferred Delivery Schedule product links (product details pages)"):
        checks = []
        schedule_item_urls = {}
        # FIFO: the product links are opened by position (top link first); together they open the page of both items
        items_not_opened = [first_item, second_item]
        for index in range(2):
            schedule_item_tab = order_details_page.open_delivery_schedule_product_link_by_index(index)
            HomePage(schedule_item_tab).get_full_page_screenshot(f'order_details_schedule_link_{index + 1}_page')
            schedule_item_tab.close()
            page.bring_to_front()
            opened_item = next((item for item in items_not_opened
                                if item["item_code"].lower() in schedule_item_tab.url.lower()), None)
            add_check(checks, f"Preferred Delivery Schedule product link {index + 1}",
                      " or ".join(item["item_code"] for item in items_not_opened) or "-",
                      schedule_item_tab.url, bool(opened_item))
            if opened_item:
                schedule_item_urls[opened_item["agreement_number"]] = schedule_item_tab.url
                items_not_opened.remove(opened_item)
        add_check(checks, "Preferred Delivery Schedule product links: page of both items", "none missing",
                  ", ".join(item["item_code"] for item in items_not_opened) or "none missing", not items_not_opened)
        order_details_links["delivery_schedule_item_urls"] = schedule_item_urls
        attach_and_assert_checks(checks, "Order details Preferred Delivery Schedule product links")

    # Step 6: Preferred Delivery Schedule requisition link
    with allure.step(f"Step 6: Open the Preferred Delivery Schedule requisition link {req_num} (ERP)"):
        schedule_erp_information, opened_tabs = check_order_details_requisition_link(
            order_details_page, lambda: order_details_page.delivery_schedule_requisition_link(req_num),
            'order_details_schedule_erp_requisition')
        order_details_links["delivery_schedule_erp_requisition"] = schedule_erp_information
        checks = []
        add_check(checks, "Preferred Delivery Schedule requisition link (ERP REQ. No)", req_num,
                  schedule_erp_information["req_no"], schedule_erp_information["req_no"] == req_num)
        add_check(checks, "Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed",
                  len(page.context.pages) == 1)
        attach_and_assert_checks(checks, "Order details Preferred Delivery Schedule requisition link")

    # Step 7: Save the order result
    with allure.step("Step 7: Save the order result"):
        order_result = {
            "order_reference_number": order_reference_number,
            "order_status": order_status,
            "requisition_number": req_num,
            "vendor": order_vendor,
            "order_approver": requisition["final_approver"],
            "items": [{"agreement_version": item["agreement_version"], "item_code": item["item_code"],
                       "quantity": expected_quantity(item), "unit_price": item["unit_price"],
                       "total_price": str(item_total(item)), "remarks": expected_remarks_display(expected_remarks(item)),
                       "attachment": expected_attachment(item)} for item in (first_item, second_item)],
            "total_price": str(order_total()),
            "delivery_schedule": delivery_schedule,
            "order_details_information": order_details_information,
            "order_details_products": order_details_products,
            "order_details_delivery_schedule": order_details_delivery_schedule,
            "order_action_history": order_action_history,
            "order_details_links": order_details_links,
        }
        save_result("same_vendor_different_agreement_items_order_result", order_result)
        print("ORDER RESULT:", order_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in order_result.items()),
            name="Saved order result",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 8: Order information Framework Agreements
    with allure.step("Step 8: Verify both Framework Agreements are shown in the order information"):
        attach_and_assert_checks(framework_checks, "Order information Framework Agreement links")


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Preview")
@allure.title("Test_case_10: Verify order preview and download the order document")
@allure.description("Test case 10: Click Preview (ERP; log in as the same user when the ERP login page is shown and "
                    "click Preview again), verify the order document (BRAC letter pad, order status, both items, "
                    "totals, delivery date and place), download the order document and log out.")
@pytest.mark.order(10)
def test_10_verify_order_preview(page):
    """
    Test case 10: Verify the order preview (order document).
    Continues on the order details page of Test case 9 (no new login).

    Steps:
        1. Click Preview: the order document (PDF) opens in a new tab (ERP). If the ERP login page is shown, log in
           as the same user (ResetHub link) and click Preview again. Download the order document and verify the
           preview address: order reference number, order status and the BRAC letter pad (letterPad=1).
        2. Order document: the letter pad is BRAC, the order status and the Purchase Order number (stored).
        3. Item Details of both items: master item, requisition, FA, agreement item, specification, remarks,
           UoM, Quantity, Unit Price, Total Price, Grand Total (sum) and the amount in words.
        4. Delivery Date and Place: the 3 delivery schedules (quantity, location, receiver).
        5. Close the preview, log out and save the order result with the preview data.
        6. Order document Framework Agreements: the FA No. of both items (checked last).
    """
    global order_preview, order_result
    assert order_details_links, "Test case 9 must pass first: order details links are not verified"

    order_details_page = OrderDetails(page)
    # Framework Agreement checks of the order document (asserted in Step 6)
    framework_checks = []

    # Step 1: Preview, download the order document (PDF) and check the preview address
    with allure.step("Step 1: Click Preview, download the order document and verify the preview address"):
        preview_tab = open_erp_requisition(order_details_page.open_order_preview)
        order_preview = {"url": preview_tab.url}
        print("ORDER PREVIEW:", preview_tab.url)
        order_document = order_details_page.download_order_document(
            preview_tab, DOWNLOAD_DIR, f"order_document_{order_reference_number.replace('/', '_')}.pdf")
        order_preview["order_document"] = order_document.name
        allure.attach.file(str(order_document), name=f"Order document - {order_document.name}")
        preview_parameters = {key: values[0] for key, values in parse_qs(urlparse(preview_tab.url).query).items()}
        tracking_number = base64.b64decode(preview_parameters.get("trackingNumber", "")).decode("utf-8", "ignore")
        preview_status = base64.b64decode(preview_parameters.get("Status", "")).decode("utf-8", "ignore")
        checks = []
        add_check(checks, "Order document is a PDF", "%PDF", order_document.read_bytes()[:4].decode("latin-1"),
                  order_document.read_bytes()[:4] == b"%PDF")
        add_check(checks, "Preview tracking number (order reference)", order_reference_number, tracking_number,
                  tracking_number == order_reference_number)
        add_check(checks, "Preview status (same as order details)", order_status, preview_status,
                  preview_status == order_status)
        add_check(checks, "Preview letter pad (BRAC)", "1", preview_parameters.get("letterPad", "-"),
                  preview_parameters.get("letterPad") == "1")
        attach_and_assert_checks(checks, "Order preview address and document")
        preview_text = order_details_page.read_order_document_text(order_document)
        preview_numbers = numbers_in_text(preview_text)
        allure.attach(preview_text, name="Order document text", attachment_type=allure.attachment_type.TEXT)

    # Step 2: Letter pad, order status and Purchase Order number
    with allure.step("Step 2: Verify the BRAC letter pad, order status and Purchase Order number"):
        checks = []
        add_check(checks, "Letter Pad Type (order details)", "BRAC", order_details_information["Letter Pad Type"],
                  order_details_information["Letter Pad Type"] == "BRAC")
        add_check(checks, "Letter pad BRAC (preview)", "BRAC", "on the preview" if "BRAC" in preview_text else "not found",
                  "BRAC" in preview_text)
        add_check(checks, "Order status (same as order details)", order_status,
                  "on the preview" if order_status in preview_text else "not found", order_status in preview_text)
        # The order document is the ERP Purchase Order: it shows the Purchase Order number (the marketplace
        # order reference is checked in the preview address in Step 1)
        purchase_order_match = re.search(r"Purchase Order:\s*(\S+)", preview_text)
        order_preview["purchase_order_number"] = purchase_order_match.group(1) if purchase_order_match else ""
        print("PURCHASE ORDER NUMBER:", order_preview["purchase_order_number"])
        add_check(checks, "Purchase Order number", "shown", order_preview["purchase_order_number"] or "not found",
                  bool(order_preview["purchase_order_number"]))
        attach_and_assert_checks(checks, "Order preview letter pad, status and Purchase Order")

    # Step 3: Item Details of both items and totals
    with allure.step("Step 3: Verify the Item Details of both items, Grand Total and amount in words"):
        checks = []
        expected_texts = [("Requisition number", req_num), ("Attachment", "Downloadable from the system")]
        # Amount in words after the Grand Total, e.g. "FIFTEEN LAKH ... TAKA AND FIFTY SIX PAISA ONLY"
        # (paisa only when the total has paisa)
        amount_in_words = order_details_page.get_amount_in_words(preview_text)
        order_preview["amount_in_words"] = amount_in_words
        has_paisa = order_total() % 1 != 0
        add_check(checks, "Amount in words (TAKA, PAISA when the total has paisa, ONLY)",
                  "... TAKA AND ... PAISA ONLY" if has_paisa else "... TAKA ONLY", amount_in_words or "not found",
                  "TAKA" in amount_in_words and ("PAISA" in amount_in_words) == has_paisa
                  and amount_in_words.endswith("ONLY"))
        expected_numbers = [("Grand Total (sum of both items)", order_total())]
        for number, item in ((1, first_item), (2, second_item)):
            add_check(framework_checks, f"Item {number} ({item['item_code']}) FA No.", item["agreement_number"],
                      "on the preview" if item["agreement_number"] in preview_text else "not found",
                      item["agreement_number"] in preview_text)
            expected_texts += [(f"Item {number} Master item", item["master_item_code"]),
                               (f"Item {number} Agreement item", item["item_code"]),
                               (f"Item {number} Specification", " ".join(item["specification"].split())),
                               (f"Item {number} Remarks", expected_remarks_display(expected_remarks(item))),
                               (f"Item {number} UoM", cart_items_after_vendor[item["agreement_number"]]["UoM"])]
            expected_numbers += [(f"Item {number} Quantity", to_amount(expected_quantity(item))),
                                 (f"Item {number} Unit Price", to_amount(item["unit_price"])),
                                 (f"Item {number} Total Price (Qty. x Unit Price)", item_total(item))]
        # Long texts (remarks, specification) wrap over the PDF lines: compared without spaces
        preview_text_no_spaces = "".join(preview_text.split())
        for check, expected in expected_texts:
            found = "".join(expected.split()) in preview_text_no_spaces
            add_check(checks, check, expected, "on the preview" if found else "not found", found)
        for check, expected in expected_numbers:
            add_check(checks, check, expected, "on the preview" if expected in preview_numbers else "not found",
                      expected in preview_numbers)
        attach_and_assert_checks(checks, "Order preview item details and totals")

    # Step 4: Delivery Date and Place (the 3 delivery schedules)
    with allure.step("Step 4: Verify the Delivery Date and Place (first item 2 schedules, second item 1)"):
        checks = []
        for number, (item, quantity, location, receiver) in enumerate(expected_schedules(), start=1):
            add_check(checks, f"Schedule {number} ({item['item_code']}) quantity", quantity,
                      "on the preview" if quantity in preview_numbers else "not found", quantity in preview_numbers)
            if location:
                add_check(checks, f"Schedule {number} location", location,
                          "on the preview" if location in preview_text else "not found", location in preview_text)
            add_check(checks, f"Schedule {number} receiver", receiver,
                      "on the preview" if receiver in preview_text else "not found", receiver in preview_text)
        attach_and_assert_checks(checks, "Order preview delivery date and place")

    # Step 5: Close the preview, log out and save the order result with the preview data
    with allure.step("Step 5: Close the preview, log out and save the order result"):
        preview_tab.close()
        page.bring_to_front()
        MainNavigationMenu(page).perform_logout()
        HomePage(page).get_full_page_screenshot('order_initiator_logout')
        order_result["order_preview"] = order_preview
        save_result("same_vendor_different_agreement_items_order_result", order_result)
        print("ORDER RESULT:", order_result)

    # Step 6: Framework Agreements of the order document
    with allure.step("Step 6: Verify the Framework Agreements of both items in the order document"):
        attach_and_assert_checks(framework_checks, "Order preview Framework Agreements")
