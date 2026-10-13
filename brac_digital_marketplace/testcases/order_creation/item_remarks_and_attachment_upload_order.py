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
# Receiving person of the auto generated delivery schedules
order_initiator = os.getenv("test_order_initiator")
order_remarks = os.getenv("test_order_remarks")
# Project root is 3 levels up: testcases/order_creation/<this file>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
UTILS_DIR = PROJECT_ROOT / "utils"
DOWNLOAD_DIR = PROJECT_ROOT / "artifacts" / "downloads"

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

# Requisition of item_remarks_and_attachment_upload_requisition.py (item_remarks_attachment_requisition_result.json):
# 8 items of one framework agreement and one vendor; items 1-7 with a PDF, JPG, PNG, XLS, PPTX, DOCX, ZIP attachment,
# item 8 without attachment and with 500 character remarks. In the shopping cart the remarks, attachments and
# quantities are not changed, so the delivery schedule is auto generated for all items.
requisition = {}
req_num = ''
order_vendor = ''
agreement_number = ''
requisition_items = []
# Shopping cart (Test case 1-3), by agreement item code
cart_items_before_vendor = {}
cart_items_after_vendor = {}
cart_link_results = {}
cart_checked_out = False
# Links of the delivery schedule (Test case 4) and the confirm order page (Test case 6)
schedule_links = {}
confirm_links = {}
# Delivery schedule (Test case 5)
requisition_schedule = []
delivery_schedule = ''
# Marketplace order (Test case 7)
order_reference_number = ''
order_status = ''
# Order details page (Test case 8 and 9)
order_details_information = {}
order_details_products = {}
order_details_delivery_schedule = []
order_action_history = []
order_details_links = {}
# Order preview (Test case 10)
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


def without_spaces(text):
    return "".join((text or "").split())


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


def item_total(item):
    return (to_amount(item["quantity"]) * to_amount(item["unit_price"])).quantize(Decimal("0.01"))


def order_total():
    return sum((item_total(item) for item in requisition_items), Decimal("0.00"))


def items_with_attachment():
    return [item for item in requisition_items if item["attachment_name"]]


def check_attachments(checks, download_attachment, label):
    # Attachment icons in page order (items without attachment have no icon): each downloaded file is one of the
    # requisition attachments (same file type, downloaded) and every requisition attachment is found once
    expected_attachments = {item["attachment_name"] for item in items_with_attachment()}
    downloaded = []
    for index in range(len(items_with_attachment())):
        downloaded_file = download_attachment(index)
        downloaded.append(downloaded_file.name)
        matching = [name for name in expected_attachments if same_file_type(downloaded_file, name)]
        add_check(checks, f"{label} attachment {index + 1}", "a requisition attachment type, downloaded",
                  matching[0] if matching else downloaded_file.name, bool(matching))
        expected_attachments -= set(matching[:1])
    add_check(checks, f"{label} all requisition attachments", "none missing",
              ", ".join(sorted(expected_attachments)) or "none missing", not expected_attachments)
    return downloaded


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


def get_cart_rows_by_item_code(cart_page):
    # Cart rows of the requisition by agreement item code
    rows = {}
    for row in cart_page.get_requisition_cart_rows(requisition_number=req_num):
        rows[cart_page.read_cart_item_cell(row)["Agreement item code"]] = row
    return rows


def product_item_code(product):
    # Agreement item code of an order details product, e.g. "([FWI049375] - BYA FR Skin Coated ...)" -> FWI049375
    return next((item["item_code"] for item in requisition_items if item["item_code"] in product["Agreement item"]),
                product["Agreement item"])


def confirm_order_items():
    # Why: the confirm order links are checked row by row with the expected values of each item; When: Test case 6
    return [{"name": f"item {item['number']}", "agreement_number": agreement_number, "item_code": item["item_code"],
             "product_name": cart_items_after_vendor[item["item_code"]]["Agreement item name"],
             "attachment_name": item["attachment_name"]} for item in requisition_items]


def same_date(first_date, second_date):
    # Why: ERP shows "10-10-2026" and the marketplace "10/10/2026"; When: requisition date checks
    return bool(first_date) and re.findall(r"\d+", first_date) == re.findall(r"\d+", second_date)


def item_products():
    # Why: the product link text is the agreement item name (items can have the same name: the item codes of each
    # product name); When: checkout product link checks
    products = {}
    for item in requisition_items:
        products.setdefault(cart_items_after_vendor[item["item_code"]]["Agreement item name"], []).append(item["item_code"])
    return products


def verify_cart_item(cart_page, item_row, item, label, check_erp_links):
    # Item/Service name & Specification cell: requisition values (remarks, attachment and quantity not changed),
    # the agreement item link and the attachment; the requisition and FA links (same for all items of the
    # requisition) are opened for the first item only
    cart_item = cart_page.read_cart_item_cell(item_row)
    checks = []
    add_check(checks, "Master item", item["master_item_code"], cart_item["Master item"],
              cart_item["Master item"].startswith(item["master_item_code"]))
    add_check(checks, "Requisition number", req_num, cart_item["Requisition"], cart_item["Requisition"] == req_num)
    add_check(checks, "Framework agreement number", agreement_number, cart_item["FA No."],
              cart_item["FA No."] == agreement_number)
    add_check(checks, "Agreement item code", item["item_code"], cart_item["Agreement item code"],
              cart_item["Agreement item code"] == item["item_code"])
    add_check(checks, "Agreement item specification", item["specification"], cart_item["Specification"],
              cart_item["Specification"] == " ".join(item["specification"].split()))
    add_check(checks, "Remarks (requisition remarks)", expected_remarks_display(item["remarks"]), cart_item["Remarks"],
              same_remarks(item["remarks"], cart_item["Remarks"]))
    if item["attachment_name"]:
        add_check(checks, "Attachment (requisition attachment)", item["attachment_name"],
                  cart_item["Attachment path"] or "(no icon)", cart_item["Attachment path"].endswith(item["attachment_name"]))
    else:
        add_check(checks, "Attachment", "no attachment", cart_item["Attachment path"] or "no attachment",
                  not cart_item["Attachment path"])
    add_check(checks, "Qty. (requisition quantity)", item["quantity"], cart_item["Qty."],
              to_amount(cart_item["Qty."]) == to_amount(item["quantity"]))
    add_check(checks, "Unit Price", item["unit_price"], cart_item["Unit Price"],
              to_amount(cart_item["Unit Price"]) == to_amount(item["unit_price"]))
    add_check(checks, "Total Price (Qty. x Unit Price)", item_total(item), cart_item["Total Price"],
              to_amount(cart_item["Total Price"]) == item_total(item))
    # Links: requisition details (ERP; opened for the first item only: same requisition for all items; all opened
    # tabs closed), agreement attachment download, product details page and item attachment download (same file type)
    link_checks, cart_link_results[label] = check_cart_item_links(
        cart_page.page, item_row, req_num, item["item_code"], item["attachment_name"], label, DOWNLOAD_DIR,
        check_requisition=check_erp_links)
    checks += link_checks
    print(f"CART ITEM ({label}):", cart_item)
    attach_and_assert_checks(checks, f"Shopping cart item vs requisition ({label})")
    return cart_item


def verify_requisition_cart_items(cart_page, stage):
    # All 8 items of the requisition in the shopping cart (each item in its own Allure step)
    cart_rows = get_cart_rows_by_item_code(cart_page)
    assert len(cart_rows) == len(requisition_items), \
        f"All {len(requisition_items)} requisition items must be in the cart, found {list(cart_rows)}"
    cart_items = {}
    failed_items = []
    # FIFO: the items are checked from the top cart row down (requisition and FA links: opened for the top item)
    page_items = in_page_order(requisition_items, lambda item: cart_rows.get(item["item_code"]))
    for item in page_items:
        try:
            with allure.step(f"Item {item['number']}: {item['item_code']} ({item['attachment_type']})"):
                assert item["item_code"] in cart_rows, f"{item['item_code']} not found in the cart"
                cart_items[item["item_code"]] = verify_cart_item(
                    cart_page, cart_rows[item["item_code"]], item, f"{stage}_item_{item['number']}",
                    check_erp_links=item is page_items[0])
        except AssertionError as error:
            failed_items.append(f"Item {item['number']}: {error}")
    assert not failed_items, "\n".join(failed_items)
    return cart_items


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Items Before Vendor Selection")
@allure.title("Test_case_1: Verify shopping cart items before vendor selection")
@allure.description("Test case 1: Before the vendor selection, verify the 8 items of the requisition in the shopping "
                    "cart (master item - requisition, FA, agreement item, specification, remarks, attachment, quantity, "
                    "prices) and their links.")
@pytest.mark.order(1)
def test_1_verify_cart_items_before_vendor_selection(page):
    """
    Test case 1: Verify the shopping cart items of the requisition before the vendor selection.

    Steps:
        1. Load the requisition of item_remarks_and_attachment_upload_requisition.py
           (item_remarks_attachment_requisition_result.json): 8 items of one framework agreement and one vendor.
        2. Log in to the Digital Marketplace as the order initiator ('proj_user').
        3. Shopping cart, before vendor selection: all 8 items are in the cart; for each item verify the
           Item/Service name & Specification (requisition remarks, attachment and quantity), the agreement item
           link and the attachment (= requisition attachment; item 8 has no attachment). The requisition link
           (ERP requisition details) and the FA link are the same for all items: opened for the first item.
        No logout: Test case 2 continues in the shopping cart.

    All scenario values are read from .env.
    """
    global requisition, req_num, order_vendor, agreement_number, requisition_items, cart_items_before_vendor

    required_env_values = {
        "test_user_name": proj_user,
        "test_env": proj_env,
        "test_url": erp_url,
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_order_initiator": order_initiator,
        "test_order_remarks": order_remarks,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    login_page = LoginPage(page)
    home_page = HomePage(page)
    cart_page = ShoppingCart(page)

    # Step 1: Requisition from item_remarks_and_attachment_upload_requisition.py
    with allure.step("Step 1: Load the requisition result of item_remarks_and_attachment_upload_requisition.py"):
        requisition = load_result("item_remarks_attachment_requisition_result",
                                  created_by="item_remarks_and_attachment_upload_requisition.py")
        req_num = requisition["requisition_number"]
        order_vendor = requisition["vendor"]
        agreement_number = requisition["agreement_number"]
        requisition_items = requisition["items"]
        assert len(requisition_items) == 8, f"The requisition must have 8 items, found {len(requisition_items)}"
        for item in requisition_items:
            check_remarks_length(f"Item {item['number']} remarks", item["remarks"])
            if item["attachment_name"]:
                assert (UTILS_DIR / item["attachment_name"]).is_file(), \
                    f"Item {item['number']} attachment not found in utils: {item['attachment_name']}"
        print("REQ NUM:", req_num)
        print("AGREEMENT:", agreement_number, "| VENDOR:", order_vendor)
        allure.attach(
            "\n".join(f"Item {item['number']}: {item['item_code']} | quantity {item['quantity']} | "
                      f"unit price {item['unit_price']} | {item['attachment_type']} {item['attachment_name'] or '-'} | "
                      f"remarks ({len(item['remarks'])} characters)" for item in requisition_items),
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
@allure.description("Test case 2: Select the requisition vendor and verify the 8 items of the requisition in the "
                    "shopping cart and their links again.")
@pytest.mark.order(2)
def test_2_verify_cart_items_after_vendor_selection(page):
    """
    Test case 2: Select the vendor and verify the shopping cart items of the requisition again.
    Continues in the shopping cart of Test case 1 (no new login).

    Steps:
        1. Select the vendor of the requisition (only this requisition stays ticked).
        2. Verify the 8 items and their links again (same checks as Test case 1).
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
    with allure.step("Step 2: Verify the 8 items and their links again"):
        cart_items_after_vendor = verify_requisition_cart_items(cart_page, "after_vendor")


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Preparation")
@allure.title("Test_case_3: Checkout without changes (remarks, attachments and quantities as in the requisition)")
@allure.description("Test case 3: Remarks, attachments and quantities are not changed in the shopping cart: verify "
                    "the cart total of the requisition and checkout.")
@pytest.mark.order(3)
def test_3_checkout_without_changes(page):
    """
    Test case 3: Checkout the shopping cart without changes.
    Continues in the shopping cart of Test case 2 (no new login).

    Steps:
        1. Remarks, attachments and quantities are not changed: the cart items are the requisition items
           (verified in Test case 2); the requisition total = sum of Qty. x Unit Price of the 8 items.
        2. Accept terms of service and checkout.
    """
    global cart_checked_out
    assert cart_items_after_vendor, "Test case 2 must pass first: vendor is not selected"

    cart_page = ShoppingCart(page)

    # Step 1: No changes; requisition total
    with allure.step(f"Step 1: No changes in the shopping cart; requisition total {order_total()}"):
        checks = []
        cart_total = sum((to_amount(cart_item["Total Price"]) for cart_item in cart_items_after_vendor.values()),
                         Decimal("0.00"))
        add_check(checks, "Requisition total in the cart (sum of the 8 items)", order_total(), cart_total,
                  cart_total == order_total())
        cart_page.get_full_page_screenshot('order_cart_no_changes')
        attach_and_assert_checks(checks, "Shopping cart total")

    # Step 2: Accept terms of service and checkout
    with allure.step("Step 2: Accept terms of service and checkout"):
        cart_page.cart_page_checkout()
        cart_checked_out = True
        cart_page.get_full_page_screenshot('order_cart_checkout')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Links")
@allure.title("Test_case_4: Verify delivery schedule links")
@allure.description("Test case 4: On the delivery schedule, open the requisition details, agreement attachment and "
                    "product details links (a link that is not on this step is noted) and download the item attachments.")
@pytest.mark.order(4)
def test_4_verify_delivery_schedule_links(page):
    """
    Test case 4: Delivery schedule links.

    Steps:
        1. Requisition details (ERP; all opened tabs closed), agreement attachment download and product details
           links of every product: a link that is not on the delivery schedule is noted in the report.
        2. Item attachments (each one a requisition attachment, same file type).
    """
    global schedule_links
    assert cart_checked_out, "Test case 3 must pass first: the cart is not checked out"
    checkout_page = CheckoutPage(page)

    # Step 1-2: Links and item attachments
    with allure.step("Step 1-2: Open the requisition details, agreement attachment, product details and item attachments"):
        link_checks, schedule_links = check_checkout_page_links(
            page, req_num, [agreement_number], item_products(), 'order_schedule', links_required=False, save_folder=DOWNLOAD_DIR)
        check_attachments(link_checks, lambda index: checkout_page.download_checkout_attachment(DOWNLOAD_DIR, index),
                          "Delivery schedule")
        checkout_page.get_full_page_screenshot('order_schedule_links_checked')
        attach_and_assert_checks(link_checks, "Delivery schedule links and item attachments")


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Preparation Window")
@allure.title("Test_case_5: Prepare delivery schedule with Auto Generate")
@allure.description("Test case 5: Verify the Requisition Schedule and the 8 items (quantity, remarks, attachment) "
                    "with the requisition, click Auto Generate (cart quantity = requisition quantity for all items) "
                    "and fill the receiving person of every generated schedule.")
@pytest.mark.order(5)
def test_5_prepare_delivery_schedule_auto_generate(page):
    """
    Test case 5: Prepare the order delivery schedule with Auto Generate.

    Steps:
        1. Requisition Schedule: one row per item (Quantity = requisition quantity, Delivery Details = requisition
           delivery address, Requisition = 'req_num').
        2. Items before the schedule: quantities, remarks (item 8: 500 characters) and the 7 attachments
           (each a requisition attachment).
        3. Click Auto Generate: every item gets one schedule with its requisition quantity.
        4. Fill the Receiving Person ('test_order_initiator') of every auto generated schedule row.
        5. Wait until Continue is enabled and click Continue.
    """
    global requisition_schedule, delivery_schedule
    assert schedule_links, "Test case 4 must pass first: delivery schedule links are not verified"

    checkout_page = CheckoutPage(page)

    # Step 1: Requisition Schedule (one row per item, found by its requisition quantity)
    with allure.step(f"Step 1: Verify the Requisition Schedule of {req_num} (8 items)"):
        requisition_schedule = checkout_page.get_requisition_schedule_rows()
        checkout_page.get_full_page_screenshot('order_schedule_requisition_schedule')
        checks = []
        add_check(checks, "Requisition Schedule rows", len(requisition_items), len(requisition_schedule),
                  len(requisition_schedule) == len(requisition_items))
        for item in requisition_items:
            schedule_row = next((row for row in requisition_schedule if row.get("Requisition") == req_num
                                 and to_amount(row.get("Quantity", "0")) == to_amount(item["quantity"])), {})
            uom = cart_items_after_vendor[item["item_code"]]["UoM"]
            add_check(checks, f"Item {item['number']} row (requisition quantity)", item["quantity"],
                      schedule_row.get("Quantity", "not found"), bool(schedule_row))
            add_check(checks, f"Item {item['number']} Unit of Measure", uom, schedule_row.get("Unit of Measure", "-"),
                      schedule_row.get("Unit of Measure") == uom)
            add_check(checks, f"Item {item['number']} Delivery Details (requisition delivery address)",
                      requisition["delivery_address"], schedule_row.get("Delivery Details", "-"),
                      requisition["delivery_address"] in schedule_row.get("Delivery Details", ""))
        attach_and_assert_checks(checks, "Requisition Schedule vs requisition")

    # Step 2: Items before the schedule: quantities, remarks and attachments
    with allure.step("Step 2: Verify the quantities, remarks and attachments of the 8 items before the schedule"):
        page_text = checkout_page.get_page_text()
        page_numbers = numbers_in_text(page_text)
        checks = []
        for item in requisition_items:
            remarks = expected_remarks_display(item["remarks"])
            add_check(checks, f"Item {item['number']} quantity", item["quantity"],
                      "on the page" if to_amount(item["quantity"]) in page_numbers else "not found",
                      to_amount(item["quantity"]) in page_numbers)
            add_check(checks, f"Item {item['number']} remarks ({len(item['remarks'])} characters)", remarks[:60],
                      "on the page" if remarks in page_text else "not found", remarks in page_text)
        checkout_page.get_full_page_screenshot('order_schedule_items')
        attach_and_assert_checks(checks, "Delivery schedule window vs requisition")

    # Step 3: Auto Generate (all items: cart quantity = requisition quantity)
    with allure.step("Step 3: Click Auto Generate (all 8 items)"):
        checkout_page.auto_generate_schedule()
        checkout_page.get_full_page_screenshot('order_schedule_auto_generate')

    # Step 4: Receiving person of every auto generated schedule row
    with allure.step(f"Step 4: Receiving Person {order_initiator} for every auto generated schedule"):
        filled_rows = checkout_page.fill_all_generated_schedule_receiving_persons(pin=order_initiator)
        checkout_page.get_full_page_screenshot('order_schedule_receiving_persons')
        allure.attach(f"Auto generated schedule rows filled: {filled_rows}", name="Receiving persons",
                      attachment_type=allure.attachment_type.TEXT)

    # Step 5: Continue
    with allure.step("Step 5: Wait until Continue is enabled and click Continue"):
        delivery_schedule = (f"Auto generated: one schedule per item with the requisition quantity, "
                             f"receiving person {order_initiator}")
        print("DELIVERY SCHEDULE:", delivery_schedule)
        allure.attach(delivery_schedule, name="Delivery schedule", attachment_type=allure.attachment_type.TEXT)
        checkout_page.click_continue_when_enabled()
        checkout_page.get_full_page_screenshot('order_schedule_continue')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order Links")
@allure.title("Test_case_6: Verify confirm order page links")
@allure.description("Test case 6: On the confirm order page, open the links in page order (first in, first out): "
                    "the order header agreement, then every item row from the top: requisition details (ERP), "
                    "agreement attachment, product details page and item attachment.")
@pytest.mark.order(6)
def test_6_verify_confirm_order_links(page):
    """
    Test case 6: Confirm order links.

    Steps (links opened in page order, first in, first out):
        1. Order header Framework Agreement link: agreement attachment download.
        2. Every item row from the top (8 rows): requisition details (ERP; all opened tabs closed), "FA:" agreement
           attachment, product details page and item attachment (the requisition attachment, same file type;
           item 8: no attachment icon).
    """
    global confirm_links
    assert delivery_schedule, "Test case 5 must pass first: delivery schedule is not prepared"
    checkout_page = CheckoutPage(page)

    # Step 1-2: Links of the confirm order page in page order
    with allure.step("Step 1-2: Open the header agreement link, then each item row: requisition, FA, product page, attachment"):
        checkout_page.wait_for_confirm_order_step()
        link_checks, confirm_links = check_confirm_order_rows_links(
            page, req_num, [agreement_number], confirm_order_items(), 'order_confirm', DOWNLOAD_DIR)
        checkout_page.get_full_page_screenshot('order_confirm_links_checked')
        attach_and_assert_checks(link_checks, "Confirm order links and item attachments (page order)")


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order")
@allure.title("Test_case_7: Confirm marketplace order")
@allure.description("Test case 7: Verify the confirm order information of the 8 items (agreement, vendor, "
                    "requisition, item details, prices, auto generated schedules), the Framework Agreement link and the "
                    "attachments, confirm the order and get the order reference number.")
@pytest.mark.order(7)
def test_7_confirm_marketplace_order(page):
    """
    Test case 7: Confirm the marketplace order (8 items, one vendor).

    Steps (each verification step has its own expected/actual checks):
        1. Order header: Framework Agreement, Vendor Name, Requisition No, Requisition Date (= ERP requisition date
           of Test case 6).
        2. Item rows (each item in its own row): master item, requisition, FA No., agreement item, specification,
           remarks, UoM, Qty., Unit Price, Total Price (Qty. x Unit Price).
        3. Order total (sum of the 8 items).
        4. Expected delivery date and place: the 8 auto generated schedules (requisition quantity, date shown,
           requisition delivery address, receiver 'test_order_initiator').
        5. Fill the order remarks ('test_order_remarks'), accept terms of service and confirm the order;
           store the order reference number.
        No logout: Test case 8 continues on the order details page.
    """
    global order_reference_number
    assert confirm_links, "Test case 6 must pass first: confirm order links are not verified"
    check_remarks_length("test_order_remarks", order_remarks)

    checkout_page = CheckoutPage(page)
    checkout_page.wait_for_confirm_order_step()
    page_text = checkout_page.get_page_text()
    page_numbers = numbers_in_text(page_text)

    def verify_on_confirm_page(title, expected_texts, expected_numbers, screenshot_name):
        # Each expected text / number must be shown on the confirm order page; the step fails if any is missing
        checks = []
        for check, expected in expected_texts:
            add_check(checks, check, expected[:80], "on the page" if expected in page_text else "not found",
                      expected in page_text)
        for check, expected in expected_numbers:
            add_check(checks, check, expected, "on the page" if expected in page_numbers else "not found",
                      expected in page_numbers)
        checkout_page.get_full_page_screenshot(screenshot_name)
        attach_and_assert_checks(checks, title)

    # Step 1: Order header: Framework Agreement, vendor and requisition
    with allure.step("Step 1: Verify the Framework Agreement, Vendor Name, Requisition No and Requisition Date"):
        header = checkout_page.read_confirm_order_header()
        erp_requisition_date = next((value["requisition_date"] for value in confirm_links.values()
                                     if isinstance(value, dict) and "requisition_date" in value), "")
        checks = []
        add_check(checks, "Framework Agreement", agreement_number, header["Framework Agreement"],
                  header["Framework Agreement"] == agreement_number)
        add_check(checks, "Vendor Name", order_vendor, header["Vendor Name"],
                  header["Vendor Name"].lower() == order_vendor.lower())
        add_check(checks, "Requisition No", req_num, header["Requisition No"], header["Requisition No"] == req_num)
        add_check(checks, "Requisition Date (= ERP requisition date)", erp_requisition_date or "-",
                  header["Requisition Date"], same_date(erp_requisition_date, header["Requisition Date"]))
        checkout_page.get_full_page_screenshot('order_confirm_header')
        attach_and_assert_checks(checks, "Confirm order header")

    # Step 2: Item rows: every value in the row of its item
    with allure.step("Step 2: Verify each item row of the 8 items (master item, requisition, FA, agreement item, "
                     "specification, remarks, UoM, Qty., Unit Price, Total Price)"):
        item_rows = [checkout_page.read_confirm_item_row(item_row)
                     for item_row in checkout_page.confirm_item_rows(req_num)]
        checks = []
        add_check(checks, "Item rows", len(requisition_items), len(item_rows), len(item_rows) == len(requisition_items))
        for item in requisition_items:
            number = item["number"]
            row = next((row for row in item_rows if item["item_code"] in row.get("Item/Service", "")), {})
            item_text = row.get("Item/Service", "")
            add_check(checks, f"Item {number} row (agreement item code)", item["item_code"],
                      "found" if row else "not found", bool(row))
            if not row:
                continue
            for check, expected in (("Master item", item["master_item_code"]), ("Requisition", req_num),
                                    ("FA No.", agreement_number),
                                    ("Specification", " ".join(item["specification"].split())),
                                    ("Remarks", expected_remarks_display(item["remarks"]))):
                add_check(checks, f"Item {number} {check}", expected[:80],
                          "in the row" if expected in item_text else "not found", expected in item_text)
            uom = cart_items_after_vendor[item["item_code"]]["UoM"]
            add_check(checks, f"Item {number} UoM", uom, row.get("UoM", "-"), row.get("UoM") == uom)
            for check, expected, column in (("Qty.", to_amount(item["quantity"]), "Qty"),
                                            ("Unit Price", to_amount(item["unit_price"]), "Unit Price"),
                                            ("Total Price (Qty. x Unit Price)", item_total(item), "Total Price")):
                add_check(checks, f"Item {number} {check}", expected, row.get(column, "-"),
                          column in row and to_amount(row[column]) == expected)
        checkout_page.get_full_page_screenshot('order_confirm_item_rows')
        attach_and_assert_checks(checks, "Confirm order item rows")

    # Step 3: Order total
    with allure.step(f"Step 3: Verify the order total {order_total()} (sum of the 8 items)"):
        verify_on_confirm_page("Confirm order total", [], [("Order total (sum of the 8 items)", order_total())],
                               'order_confirm_total')

    # Step 4: Expected delivery date and place (the 8 auto generated schedules)
    with allure.step("Step 4: Verify the expected delivery date and place (8 auto generated schedules)"):
        schedule_rows = checkout_page.get_confirm_schedule_rows()
        checks = []
        add_check(checks, "Delivery schedule rows", len(requisition_items), len(schedule_rows),
                  len(schedule_rows) == len(requisition_items))
        used_rows = []
        for item in requisition_items:
            number = item["number"]
            schedule_row = next((row for row in schedule_rows if row not in used_rows
                                 and to_amount(row.get("Quantity", "0")) == to_amount(item["quantity"])), {})
            if schedule_row:
                used_rows.append(schedule_row)
            add_check(checks, f"Item {number} schedule quantity", item["quantity"],
                      schedule_row.get("Quantity", "not found"), bool(schedule_row))
            add_check(checks, f"Item {number} schedule date", "shown", schedule_row.get("Date") or "-",
                      bool(schedule_row.get("Date")))
            add_check(checks, f"Item {number} schedule location (requisition delivery address)",
                      requisition["delivery_address"][:60], schedule_row.get("Location", "-")[:60],
                      without_spaces(requisition["delivery_address"]) in without_spaces(schedule_row.get("Location", "")))
            add_check(checks, f"Item {number} schedule receiver", order_initiator, schedule_row.get("Receiver Info", "-"),
                      order_initiator in schedule_row.get("Receiver Info", ""))
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


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Details Links")
@allure.title("Test_case_8: Verify order details links")
@allure.description("Test case 8: Open the order details of the confirmed order, download the agreement attachment "
                    "(agreement number first), open the requisition (ERP; all opened tabs are closed), FA and product "
                    "links of the 8 products in page order, download the 7 attachments and open the Preferred Delivery "
                    "Schedule product and requisition links.")
@pytest.mark.order(8)
def test_8_verify_order_details_links(page):
    """
    Test case 8: Verify the links of the order details.
    Continues after the order confirmation of Test case 7 (no new login).

    Steps:
        1. Open the order details and store the order status in 'order_status'.
        2-5. Agreement attachment download (first the agreement number of the order information, then each
             product FA link), requisition details (ERP; ResetHub login when the ERP login page is shown; all
             opened tabs closed), product details page and item attachment of every product (each a requisition
             attachment, same file type; an item without attachment has no attachment icon).
        6. Preferred Delivery Schedule product links (8): the product details pages of the 8 items.
        7. Preferred Delivery Schedule requisition link: ERP requisition details (all opened tabs closed).
        No logout: Test case 9 continues on the order details page.
    """
    global order_status, order_details_links
    assert order_reference_number, "Test case 7 must pass first: order is not confirmed"

    checkout_page = CheckoutPage(page)
    order_details_page = OrderDetails(page)

    # Step 1: Order details and status
    with allure.step(f"Step 1: Open the order details of {order_reference_number}"):
        order_status = checkout_page.goto_public_side_order_details_view()
        print("ORDER STATUS:", order_status)
        order_details_page.get_full_page_screenshot('order_details')

    # Step 2-5: Agreement attachment (agreement number first), requisition, product pages and item attachments
    with allure.step("Step 2-5: Download the agreement attachment, open the requisition details and product details, "
                     "download the item attachments"):
        link_checks, order_details_links["products"] = check_order_details_all_products_links(
            page, req_num, [agreement_number],
            [{"item_code": item["item_code"], "master_item_code": item["master_item_code"],
              "attachment_name": item["attachment_name"]} for item in requisition_items],
            'order_details', DOWNLOAD_DIR)
        attach_and_assert_checks(link_checks, "Order details links and item attachments")

    # Step 6: Preferred Delivery Schedule product links (products can have the same name: opened by position)
    with allure.step("Step 6: Open the 8 Preferred Delivery Schedule product links (product details pages)"):
        checks = []
        schedule_item_urls = []
        expected_item_codes = {item["item_code"] for item in requisition_items}
        for index in range(len(requisition_items)):
            schedule_item_tab = order_details_page.open_delivery_schedule_product_link_by_index(index)
            schedule_item_urls.append(schedule_item_tab.url)
            HomePage(schedule_item_tab).get_full_page_screenshot(f'order_details_schedule_item_{index + 1}_page')
            schedule_item_tab.close()
            page.bring_to_front()
            item_code = next((code for code in expected_item_codes if code.lower() in schedule_item_tab.url.lower()), "")
            add_check(checks, f"Preferred Delivery Schedule product link {index + 1}", "a requisition item page",
                      schedule_item_tab.url, bool(item_code))
            expected_item_codes.discard(item_code)
        add_check(checks, "Preferred Delivery Schedule product links of all items", "none missing",
                  ", ".join(sorted(expected_item_codes)) or "none missing", not expected_item_codes)
        order_details_links["delivery_schedule_item_urls"] = schedule_item_urls
        attach_and_assert_checks(checks, "Order details Preferred Delivery Schedule product links")

    # Step 7: Preferred Delivery Schedule requisition link
    with allure.step(f"Step 7: Open the Preferred Delivery Schedule requisition link {req_num} (ERP)"):
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


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Details Information")
@allure.title("Test_case_9: Verify order details information")
@allure.description("Test case 9: Verify the order information, the 8 products, totals, Preferred Delivery "
                    "Schedule and Action History of the order details with the requisition; store the Action History "
                    "and save the order result.")
@pytest.mark.order(9)
def test_9_verify_order_details_information(page):
    """
    Test case 9: Verify the order details information.
    Continues on the order details page of Test case 8 (no new login).

    Steps (each step has its own expected/actual checks):
        1. Order information: Order Reference No., Framework Agreement,
           Order Status, Order Total (sum of the 8 items), Order Remarks, Vendor Name; store Programme Name,
           Letter Pad Type and Order Date.
        2. Product(s): the 8 products, found by agreement item code (master item - requisition, FA, agreement item,
           specification, remarks, attachment icon (item 8: none), UoM, Quantity, Unit Price, Total Price) and the
           Sub-Total.
        3. Preferred Delivery Schedule: the 8 auto generated schedules (requisition quantity, location,
           receiver 'test_order_initiator').
        4. Action History: store all rows; the order is submitted for approval by the requisition initiator.
        5. Save the order result (item_remarks_and_attachment_upload_order_result.json).
        6. Order Date = the date the order was submitted (checked last, after all other order details).
        No logout: Test case 10 continues on the order details page.
    """
    global order_details_information, order_details_products, order_details_delivery_schedule, \
        order_action_history, order_result
    assert order_details_links, "Test case 8 must pass first: order details links are not verified"

    order_details_page = OrderDetails(page)
    # Order Date check (asserted in Step 5)
    last_step_checks = []

    # Step 1: Order information
    with allure.step("Step 1: Verify the order information"):
        order_details_information = {
            label: order_details_page.get_order_field(label)
            for label in ("Order Reference No", "Framework Agreement", "Order Date", "Order Status", "Order Total",
                          "Letter Pad Type", "Order Remarks", "Vendor Name", "Programme Name")}
        print("ORDER DETAILS INFORMATION:", order_details_information)
        order_details_page.get_full_page_screenshot('order_details_information')
        checks = []
        add_check(checks, "Order Reference No", order_reference_number, order_details_information["Order Reference No"],
                  order_details_information["Order Reference No"] == order_reference_number)
        add_check(checks, "Framework Agreement", agreement_number, order_details_information["Framework Agreement"],
                  order_details_information["Framework Agreement"] == agreement_number)
        add_check(checks, "Order Status", "not empty", order_details_information["Order Status"],
                  bool(order_details_information["Order Status"]))
        add_check(checks, "Order Total (sum of the 8 items)", order_total(), order_details_information["Order Total"],
                  to_amount(order_details_information["Order Total"]) == order_total())
        add_check(checks, "Order Remarks", order_remarks, order_details_information["Order Remarks"],
                  same_remarks(order_remarks, order_details_information["Order Remarks"]))
        add_check(checks, "Vendor Name", order_vendor, order_details_information["Vendor Name"],
                  order_details_information["Vendor Name"].lower() == order_vendor.lower())
        attach_and_assert_checks(checks, "Order details information")

    # Step 2: Product(s) and Sub-Total
    with allure.step("Step 2: Verify the 8 products and the Sub-Total"):
        product_rows = order_details_page.get_product_rows()
        products = [order_details_page.read_product_row(product_row) for product_row in product_rows]
        order_details_products = {product_item_code(product): product for product in products}
        sub_total = order_details_page.get_sub_total()
        checks = []
        add_check(checks, "Products", len(requisition_items), len(product_rows), len(product_rows) == len(requisition_items))
        for item in requisition_items:
            number = item["number"]
            product = order_details_products.get(item["item_code"], {})
            uom = cart_items_after_vendor[item["item_code"]]["UoM"]
            add_check(checks, f"Item {number} product row (agreement item code)", item["item_code"],
                      product.get("Agreement item", "not found"), bool(product))
            if not product:
                continue
            add_check(checks, f"Item {number} Master item", item["master_item_code"], product["Master item"],
                      product["Master item"].startswith(item["master_item_code"]))
            add_check(checks, f"Item {number} Requisition number", req_num, product["Requisition"],
                      product["Requisition"] == req_num)
            add_check(checks, f"Item {number} FA No.", agreement_number, product["FA No."],
                      product["FA No."] == agreement_number)
            add_check(checks, f"Item {number} Specification", item["specification"], product["Specification"],
                      product["Specification"] == " ".join(item["specification"].split()))
            add_check(checks, f"Item {number} Remarks", expected_remarks_display(item["remarks"])[:60],
                      product["Remarks"][:60], same_remarks(item["remarks"], product["Remarks"]))
            add_check(checks, f"Item {number} Attachment icon", "shown" if item["attachment_name"] else "not shown",
                      "shown" if product["Attachment icon"] else "not shown",
                      product["Attachment icon"] == bool(item["attachment_name"]))
            add_check(checks, f"Item {number} UoM", uom, product["UoM"], product["UoM"] == uom)
            add_check(checks, f"Item {number} Quantity (requisition quantity)", item["quantity"], product["Quantity"],
                      to_amount(product["Quantity"]) == to_amount(item["quantity"]))
            add_check(checks, f"Item {number} Unit Price", item["unit_price"], product["Unit Price"],
                      to_amount(product["Unit Price"]) == to_amount(item["unit_price"]))
            add_check(checks, f"Item {number} Total Price (Qty. x Unit Price)", item_total(item), product["Total Price"],
                      to_amount(product["Total Price"]) == item_total(item))
        add_check(checks, "Sub-Total (sum of the 8 items)", order_total(), sub_total, to_amount(sub_total) == order_total())
        order_details_page.get_full_page_screenshot('order_details_products')
        attach_and_assert_checks(checks, "Order details products and totals")

    # Step 3: Preferred Delivery Schedule (the 8 auto generated schedules)
    with allure.step("Step 3: Verify the Preferred Delivery Schedule (8 auto generated schedules)"):
        order_details_delivery_schedule = order_details_page.get_all_preferred_delivery_schedules()
        checks = []
        add_check(checks, "Delivery schedules", len(requisition_items), len(order_details_delivery_schedule),
                  len(order_details_delivery_schedule) == len(requisition_items))
        for item in requisition_items:
            schedule = next((row for row in order_details_delivery_schedule
                             if to_amount(row.get("Quantity", "0")) == to_amount(item["quantity"])), {})
            add_check(checks, f"Item {item['number']} schedule Quantity", item["quantity"],
                      schedule.get("Quantity", "not found"), bool(schedule))
            add_check(checks, f"Item {item['number']} schedule Location (requisition delivery address)",
                      requisition["delivery_address"], schedule.get("Location", "-"),
                      requisition["delivery_address"] in schedule.get("Location", ""))
            add_check(checks, f"Item {item['number']} schedule Receiver Info", order_initiator,
                      schedule.get("Receiver Info", "-"), order_initiator in schedule.get("Receiver Info", ""))
        order_details_page.get_full_page_screenshot('order_details_delivery_schedule')
        attach_and_assert_checks(checks, "Order details Preferred Delivery Schedule")

    # Step 4: Action History (stored)
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

    # Step 5: Save the order result (before the Order Date check, so Test case 10 can still run)
    with allure.step("Step 5: Save the order result"):
        order_result = {
            "order_reference_number": order_reference_number,
            "order_status": order_status,
            "requisition_number": req_num,
            "agreement_number": agreement_number,
            "vendor": order_vendor,
            "order_approver": requisition["final_approver"],
            "order_remarks": order_remarks,
            "delivery_address": requisition["delivery_address"],
            "items": [{"number": item["number"], "agreement_version": item["agreement_version"],
                       "item_code": item["item_code"], "master_item_code": item["master_item_code"],
                       "specification": " ".join(item["specification"].split()),
                       "uom": cart_items_after_vendor[item["item_code"]]["UoM"],
                       "quantity": item["quantity"], "unit_price": item["unit_price"],
                       "total_price": str(item_total(item)), "remarks": expected_remarks_display(item["remarks"]),
                       "attachment": item["attachment_name"]} for item in requisition_items],
            "total_price": str(order_total()),
            "delivery_schedule": delivery_schedule,
            "order_details_information": order_details_information,
            "order_details_products": order_details_products,
            "order_details_delivery_schedule": order_details_delivery_schedule,
            "order_action_history": order_action_history,
            "order_details_links": order_details_links,
        }
        save_result("item_remarks_and_attachment_upload_order_result", order_result)
        print("ORDER RESULT:", order_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in order_result.items()),
            name="Saved order result",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 6: Order Date
    with allure.step("Step 6: Verify the Order Date (date the order was submitted)"):
        attach_and_assert_checks(last_step_checks, "Order details Order Date")


@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order Preview")
@allure.title("Test_case_10: Verify order preview and download the order document")
@allure.description("Test case 10: Click Preview (ERP; log in as the same user when the ERP login page is shown and "
                    "click Preview again), verify the order document (BRAC letter pad, order status, the 8 items, "
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
        3. Item Details of the 8 items: master item, agreement item, specification, remarks (item 8: 500
           characters), UoM, Quantity, Unit Price, Total Price, FA No., requisition, Grand Total (sum) and the
           amount in words.
        4. Delivery Date and Place: the 8 auto generated schedules (quantity, place, receiver).
        5. Close the preview, log out and save the order result with the preview data.
    """
    global order_preview, order_result
    assert order_result, "Test case 9 must pass first: order details information is not verified"

    order_details_page = OrderDetails(page)

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

    # Step 3: Item Details of the 8 items and totals
    with allure.step("Step 3: Verify the Item Details of the 8 items, Grand Total and amount in words"):
        checks = []
        # Long texts (remarks, specification) wrap over the PDF lines: compared without spaces
        preview_text_no_spaces = without_spaces(preview_text)
        expected_texts = [("Requisition number", req_num), ("FA No.", agreement_number),
                          ("Attachment", "Downloadable from the system")]
        expected_numbers = [("Grand Total (sum of the 8 items)", order_total())]
        for item in requisition_items:
            number = item["number"]
            expected_texts += [(f"Item {number} Master item", item["master_item_code"]),
                               (f"Item {number} Agreement item", item["item_code"]),
                               (f"Item {number} Specification", item["specification"]),
                               (f"Item {number} Remarks", expected_remarks_display(item["remarks"])),
                               (f"Item {number} UoM", cart_items_after_vendor[item["item_code"]]["UoM"])]
            expected_numbers += [(f"Item {number} Quantity", to_amount(item["quantity"])),
                                 (f"Item {number} Unit Price", to_amount(item["unit_price"])),
                                 (f"Item {number} Total Price (Qty. x Unit Price)", item_total(item))]
        for check, expected in expected_texts:
            found = without_spaces(expected) in preview_text_no_spaces
            add_check(checks, check, expected[:80], "on the preview" if found else "not found", found)
        for check, expected in expected_numbers:
            add_check(checks, check, expected, "on the preview" if expected in preview_numbers else "not found",
                      expected in preview_numbers)
        # Amount in words after the Grand Total, e.g. "FIFTEEN LAKH ... TAKA AND FIFTY SIX PAISA ONLY"
        # (paisa only when the total has paisa)
        amount_in_words = order_details_page.get_amount_in_words(preview_text)
        order_preview["amount_in_words"] = amount_in_words
        has_paisa = order_total() % 1 != 0
        add_check(checks, "Amount in words (TAKA, PAISA when the total has paisa, ONLY)",
                  "... TAKA AND ... PAISA ONLY" if has_paisa else "... TAKA ONLY", amount_in_words or "not found",
                  "TAKA" in amount_in_words and ("PAISA" in amount_in_words) == has_paisa
                  and amount_in_words.endswith("ONLY"))
        attach_and_assert_checks(checks, "Order preview item details and totals")

    # Step 4: Delivery Date and Place (the 8 auto generated schedules)
    with allure.step("Step 4: Verify the Delivery Date and Place (8 auto generated schedules)"):
        checks = []
        add_check(checks, "Delivery place (requisition delivery address)", requisition["delivery_address"],
                  "on the preview" if without_spaces(requisition["delivery_address"]) in without_spaces(preview_text)
                  else "not found",
                  without_spaces(requisition["delivery_address"]) in without_spaces(preview_text))
        add_check(checks, "Receiver", order_initiator,
                  "on the preview" if order_initiator in preview_text else "not found", order_initiator in preview_text)
        for item in requisition_items:
            quantity = to_amount(item["quantity"])
            add_check(checks, f"Item {item['number']} schedule quantity", quantity,
                      "on the preview" if quantity in preview_numbers else "not found", quantity in preview_numbers)
        attach_and_assert_checks(checks, "Order preview delivery date and place")

    # Step 5: Close the preview, log out and save the order result with the preview data
    with allure.step("Step 5: Close the preview, log out and save the order result"):
        preview_tab.close()
        page.bring_to_front()
        MainNavigationMenu(page).perform_logout()
        HomePage(page).get_full_page_screenshot('order_initiator_logout')
        order_result["order_preview"] = order_preview
        save_result("item_remarks_and_attachment_upload_order_result", order_result)
        print("ORDER RESULT:", order_result)
