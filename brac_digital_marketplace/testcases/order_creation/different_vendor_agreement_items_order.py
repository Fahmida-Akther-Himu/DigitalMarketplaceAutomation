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
# Requisition item remarks (same values as the requisition file): item 1 500 characters, item 2 short remarks
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
requisition_item_remarks_500 = os.getenv("test_requisition_item_remarks_500")
# Vendor 2 item in the shopping cart: new remarks, new attachment (uploaded over the requisition attachment) and new
# quantity (max the requisition / remaining quantity; 0 removes the item from the shopping cart)
cart_item_remarks = os.getenv("test_cart_item_remarks", "")
cart_attachment_file = os.getenv("test_requisition_attachment_file_jpg")
cart_item_quantity = os.getenv("test_cart_item_quantity")
# Vendor 1 order: receiving person of the auto generated schedule
order_admin_receiver = os.getenv("test_order_admin_receiver")
# Vendor 2 order: 2 delivery schedules (same values as marketplace_staging_sanity.py)
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
    check_checkout_attachment, check_order_details_page_links, read_requisition_from_link, check_cart_item_links, \
    in_page_order, requisition_product_name_checks
from utils.remarks_rules import check_remarks_length, expected_remarks_display, same_remarks
from utils.attachment_rules import same_file_type
from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.shopping_cart import ShoppingCart
from pages.digital_marketplace.public_side.checkout_page import CheckoutPage
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails

# Requisition of different_vendor_agreement_items_requisition.py (different_vendor_agreement_requisition_result.json):
# 2 items of 2 framework agreements with 2 different vendors. The marketplace makes one order per vendor:
# - order 1 (vendor of item 1): cart remarks changed to empty (shown as N/A), attachment removed, quantity not
#   changed -> Auto Generate schedule, receiving person 'test_order_admin_receiver'
# - order 2 (vendor of item 2): cart remarks updated, a new attachment uploaded over the requisition attachment,
#   quantity updated ('test_cart_item_quantity', 0 removes the item) -> 2 manual delivery schedules
# Each item keeps its cart values in "cart_remarks", "cart_attachment" and "cart_quantity".
requisition = {}
req_num = ''
requisition_items = []
# Shopping cart before the vendor selection (Test case 1), by FA No.
cart_items_before_vendor = {}
# One order per vendor: {1: {...}, 2: {...}} (cart changes, delivery schedule, order, order details, links, preview)
orders = {1: {}, 2: {}}
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
    # Long texts (address, remarks) wrap differently on each page: used to compare them without spaces
    return "".join((text or "").split())


def add_check(checks, check, expected, actual, passed):
    # One expected/actual check row for the Allure report: used by every verification step
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
    # Order total of an item: cart quantity x unit price
    return (to_amount(item["cart_quantity"]) * to_amount(item["unit_price"])).quantize(Decimal("0.01"))


def remarks_shown(expected_remarks, shown_remarks):
    # Remarks shown in the shopping cart: the remarks, or blank / N/A when the remarks are empty
    return same_remarks(expected_remarks, shown_remarks) or (not expected_remarks and not (shown_remarks or "").strip())


def expected_schedules(number):
    # (quantity, location, receiver) of the delivery schedules of order <number>; location None = the requisition
    # delivery address (auto generated schedule)
    item = requisition_items[number - 1]
    if number == 1:
        return [(to_amount(item["cart_quantity"]), None, order_admin_receiver)]
    if to_amount(item["cart_quantity"]) > to_amount(delivery_schedule_quantity):
        return [(to_amount(delivery_schedule_quantity), manual_delivery_location_1, receiving_pin_1),
                (to_amount(item["cart_quantity"]) - to_amount(delivery_schedule_quantity), manual_delivery_location_2,
                 order_initiator)]
    return [(to_amount(item["cart_quantity"]), manual_delivery_location_1, receiving_pin_1)]


def wait_for_erp_address(erp_tab):
    # ERP pages (requisition, preview) may never finish loading: used to wait only until the ERP address opens
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


def requisition_product_name(item):
    # Why: the product name ("item name - delivery location") of an item, stored by the requisition test file from the
    # Active Requisition Product List (the row with the FwA No. of the item); When: product name checks of every page
    return next(product["product"] for product in requisition["active_requisition_products"]
                if product["fwa_no"].startswith(item["agreement_number"]))


def check_checkout_links(page, item, order, label, links_required=True):
    # Requisition, Framework Agreement and product links of a checkout step (shared check, as on the shopping cart
    # page); the product name of the requisition is verified, not clicked
    checks, links = check_checkout_page_links(page, req_num, [item["agreement_number"]],
                                              {order["cart_item"]["Agreement item name"]: [item["item_code"]]}, label,
                                              links_required=links_required, save_folder=DOWNLOAD_DIR,
                                              requisition_product_name=requisition_product_name(item))
    attach_and_assert_checks(checks, f"{label} requisition, agreement and product details links")
    return links


def get_cart_rows_by_fa(cart_page):
    # Cart rows of the requisition by FA No. (one item per framework agreement); empty when the requisition has
    # no item in the shopping cart
    try:
        rows = cart_page.get_requisition_cart_rows(requisition_number=req_num)
    except AssertionError:
        return {}
    return {row.locator("a.item-framework-link").get_attribute("data-framework-number"): row for row in rows}


def verify_cart_item(cart_page, item_row, item, label, check_erp_links):
    # Item/Service name & Specification cell: the cart values of the item (remarks, attachment, quantity), the FA,
    # agreement item and attachment links; the requisition link is opened when check_erp_links
    cart_item = cart_page.read_cart_item_cell(item_row)
    # No attachment: the (hidden) attachment icon has no attachment path
    cart_item["Attachment path"] = cart_item["Attachment path"] or ""
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
    add_check(checks, f"Remarks ({len(item['cart_remarks'])} characters)",
              expected_remarks_display(item["cart_remarks"])[:60], cart_item["Remarks"][:60] or "(blank)",
              remarks_shown(item["cart_remarks"], cart_item["Remarks"]))
    add_check(checks, "Attachment", item["cart_attachment"] or "no attachment", cart_item["Attachment path"] or "no attachment",
              cart_item["Attachment path"].endswith(item["cart_attachment"]) if item["cart_attachment"]
              else not cart_item["Attachment path"])
    add_check(checks, "Qty. (cart quantity)", item["cart_quantity"], cart_item["Qty."],
              to_amount(cart_item["Qty."]) == to_amount(item["cart_quantity"]))
    add_check(checks, "Unit Price", item["unit_price"], cart_item["Unit Price"],
              to_amount(cart_item["Unit Price"]) == to_amount(item["unit_price"]))
    add_check(checks, "Total Price (Qty. x Unit Price)", item_total(item), cart_item["Total Price"],
              to_amount(cart_item["Total Price"]) == item_total(item))
    # Links: requisition details (ERP, when check_erp_links; all opened tabs closed), agreement attachment download,
    # product details page and item attachment download (same file type; no attachment: not downloaded)
    link_checks, link_results = check_cart_item_links(
        cart_page.page, item_row, req_num, item["item_code"], item["cart_attachment"], label, DOWNLOAD_DIR,
        check_requisition=check_erp_links, requisition_product_name=requisition_product_name(item))
    checks += link_checks

    print(f"CART ITEM ({label}):", cart_item)
    attach_and_assert_checks(checks, f"Shopping cart item ({label})")
    cart_item["links"] = link_results
    return cart_item


def keep_earlier_cart_changes(cart_page, item_row, item, number):
    # The shopping cart keeps the cart changes of an earlier checkout that was not confirmed (Update shopping cart
    # saves them): vendor 1 item with empty remarks and no attachment, vendor 2 item with the cart remarks or the cart
    # attachment. These cart values are expected (and noted in the report) instead of the requisition values.
    cart_item = cart_page.read_cart_item_cell(item_row)
    shown_remarks = " ".join((cart_item["Remarks"] or "").split())
    attachment_path = cart_item["Attachment path"] or ""
    earlier_changes = []
    if number == 1:
        if not shown_remarks:
            item["cart_remarks"] = ""
            earlier_changes.append("remarks empty")
        if not attachment_path:
            item["cart_attachment"] = ""
            earlier_changes.append("attachment removed")
    else:
        if cart_item_remarks and shown_remarks == " ".join(cart_item_remarks.split()):
            item["cart_remarks"] = cart_item_remarks
            earlier_changes.append("cart remarks")
        if attachment_path.endswith(cart_attachment_file):
            item["cart_attachment"] = cart_attachment_file
            earlier_changes.append(f"attachment {cart_attachment_file}")
    if earlier_changes:
        allure.attach(f"Item {number} ({item['agreement_number']}) keeps the cart changes of an earlier unconfirmed "
                      f"checkout: {', '.join(earlier_changes)}",
                      name=f"Item {number} earlier cart changes", attachment_type=allure.attachment_type.TEXT)
        print(f"ITEM {number} EARLIER CART CHANGES:", earlier_changes)


# ---------------- One order per vendor: the same steps for vendor 1 and vendor 2 ----------------

def update_vendor_1_item(cart_page, item_row, item, order):
    # Vendor 1 item: remarks changed to empty, attachment removed (pop-up Yes), quantity not changed
    with allure.step("Step 3: Item 1 - change the remarks to empty and remove the attachment"):
        cart_page.fill_cart_item_remarks(item_row, "")
        if item["cart_attachment"]:
            order["attachment_remove_message"] = cart_page.remove_cart_attachment(item_row)
        else:
            order["attachment_remove_message"] = "no attachment in the cart (removed in an earlier unconfirmed checkout)"
        cart_page.update_shopping_cart_info()
        cart_page.page.wait_for_load_state("load")
        cart_page.wait_for_timeout(3000)
        item["cart_remarks"] = ""
        item["cart_attachment"] = ""
        order["cart_changes"] = {"remarks": "(empty)", "attachment": f"removed {item['attachment_name']}",
                                 "attachment_remove_message": order["attachment_remove_message"],
                                 "quantity": f"not changed ({item['cart_quantity']})"}
        cart_page.get_full_page_screenshot('order_1_cart_item_updated')


def update_vendor_2_item(cart_page, item_row, item, order):
    # Vendor 2 item: remarks updated, new attachment uploaded over the requisition attachment, quantity updated
    # (0 removes the item from the shopping cart); returns False when the item is removed
    cart_attachment_path = UTILS_DIR / cart_attachment_file
    with allure.step(f"Step 3: Item 2 - remarks '{cart_item_remarks}', upload {cart_attachment_path.name} (without "
                     f"removing {item['attachment_name']}) and quantity {cart_item_quantity}"):
        assert cart_attachment_path.is_file(), f"Cart attachment not found in utils: {cart_attachment_path}"
        assert cart_attachment_path.suffix.lower() in CART_ATTACHMENT_TYPES, \
            f"Cart attachment type {cart_attachment_path.suffix} is not allowed: {sorted(CART_ATTACHMENT_TYPES)}"
        assert cart_attachment_path.stat().st_size / (1024 * 1024) <= MAX_CART_ATTACHMENT_SIZE_MB, \
            f"Cart attachment must be max {MAX_CART_ATTACHMENT_SIZE_MB} MB"
        # New quantity: max the quantity in the cart (requisition quantity, or the remaining quantity when items of
        # the requisition were ordered before)
        assert Decimal(0) <= to_amount(cart_item_quantity) <= to_amount(item["cart_quantity"]), \
            f"test_cart_item_quantity {cart_item_quantity} must be 0 to {item['cart_quantity']} (cart / remaining quantity)"
        cart_page.fill_cart_item_remarks(item_row, cart_item_remarks)
        cart_page.upload_cart_item_attachment(item_row, cart_attachment_path)
        order["cart_changes"] = {"remarks": cart_item_remarks,
                                 "attachment": f"{cart_attachment_path.name} uploaded over {item['attachment_name']}",
                                 "quantity": f"{item['cart_quantity']} -> {cart_item_quantity}"}
        cart_page.get_full_page_screenshot('order_2_cart_item_attachment_uploaded')
        cart_page.update_cart_item_quantity(item_row, cart_item_quantity)
        item["cart_remarks"] = cart_item_remarks
        item["cart_attachment"] = cart_attachment_path.name
        item["cart_quantity"] = cart_item_quantity
        cart_page.get_full_page_screenshot('order_2_cart_item_updated')

    if to_amount(cart_item_quantity) == 0:
        # Quantity 0: the item is removed from the shopping cart (no order 2)
        with allure.step("Step 4: Quantity 0 - the item is removed from the shopping cart"):
            checks = []
            in_cart = item["agreement_number"] in get_cart_rows_by_fa(cart_page)
            add_check(checks, "Item 2 removed from the shopping cart (quantity 0)", "removed",
                      "in the cart" if in_cart else "removed", not in_cart)
            order["removed"] = True
            attach_and_assert_checks(checks, "Item 2 quantity 0")
        return False
    return True


def select_vendor_and_checkout(page, number):
    # Shopping cart: select the vendor of item <number> (only this requisition ticked), verify the item, change the
    # cart values of the item and checkout
    item = requisition_items[number - 1]
    other_item = requisition_items[2 - number]
    cart_page = ShoppingCart(page)
    order = orders[number]

    # Step 1: Vendor selection
    with allure.step(f"Step 1: Select vendor {item['vendor']} for requisition {req_num}"):
        cart_page.select_vendor_for_requisition_found(requisition_number=req_num)
        # The shopping cart can have many requisitions (business data): keep only this requisition ticked
        assert cart_page.select_vendor_keep_only_requisition(vendor_name=item["vendor"], requisition_number=req_num), \
            f"Vendor {item['vendor']} not found in the shopping cart"
        cart_page.get_full_page_screenshot(f'order_{number}_cart_vendor_selected')

    # Step 2: The item of this vendor and its links
    with allure.step(f"Step 2: Verify item {number} ({item['agreement_number']}) of vendor {item['vendor']}"):
        cart_rows = get_cart_rows_by_fa(cart_page)
        assert item["agreement_number"] in cart_rows, \
            f"Item {number} ({item['agreement_number']}) not found in the cart: {list(cart_rows)}"
        order["cart_item_before_changes"] = verify_cart_item(
            cart_page, cart_rows[item["agreement_number"]], item, f"order_{number}_item_{number}", check_erp_links=True)

    # Step 3: Cart changes of this vendor's item
    item_row = get_cart_rows_by_fa(cart_page)[item["agreement_number"]]
    if number == 1:
        update_vendor_1_item(cart_page, item_row, item, order)
    elif not update_vendor_2_item(cart_page, item_row, item, order):
        return

    # Step 4: The item after the changes (remarks, attachment, quantity) and its links
    with allure.step(f"Step 4: Verify item {number} after the changes: {order['cart_changes']}"):
        item_row = get_cart_rows_by_fa(cart_page)[item["agreement_number"]]
        order["cart_item"] = verify_cart_item(cart_page, item_row, item, f"order_{number}_item_{number}_updated",
                                              check_erp_links=False)
        allure.attach("\n".join(f"{key}: {value}" for key, value in order["cart_changes"].items()),
                      name=f"Order {number} cart changes", attachment_type=allure.attachment_type.TEXT)

    # Step 5: Accept terms of service and checkout
    with allure.step("Step 5: Accept terms of service and checkout"):
        cart_page.cart_page_checkout()
        order["checked_out"] = True
        cart_page.get_full_page_screenshot(f'order_{number}_cart_checkout')

    # Step 6: Checkout of this vendor: only the item of this vendor (one order per vendor)
    with allure.step(f"Step 6: Verify only item {number} of vendor {item['vendor']} is in the checkout"):
        checkout_page = CheckoutPage(page)
        requisition_schedule = checkout_page.get_requisition_schedule_rows()
        order["requisition_schedule"] = requisition_schedule
        other_item_shown = any(other_item["agreement_number"] in " ".join(row.values()) or
                               to_amount(row.get("Quantity", "0")) == to_amount(other_item["quantity"])
                               for row in requisition_schedule)
        checks = []
        add_check(checks, "Requisition Schedule rows (one item of this vendor)", 1, len(requisition_schedule),
                  len(requisition_schedule) == 1)
        add_check(checks, f"Item of the other vendor ({other_item['vendor']}) not in the checkout", "not shown",
                  "shown" if other_item_shown else "not shown", not other_item_shown)
        attach_and_assert_checks(checks, f"Order {number} checkout: one vendor")


def checkout_attachment_checks(page, item, label):
    # Why: the checkout must show the cart attachment of the item, or no attachment icon when it was removed in the
    # cart; When: delivery schedule and confirm order links tests
    if item["cart_attachment"]:
        checks, _ = check_checkout_attachment(page, item["cart_attachment"], label, DOWNLOAD_DIR)
        return checks
    attachment_icons = CheckoutPage(page).item_attachment_icon.count()
    return [("Attachment (removed in the cart)", "no attachment icon", f"{attachment_icons} icon(s)",
             "PASS" if attachment_icons == 0 else "FAIL")]


def verify_checkout_page_links(page, number, confirm_page):
    # Why: the delivery schedule and confirm order pages must link to the requisition (ERP), agreement attachment and
    # product details and show the item attachment; When: the links tests of order <number> (confirm_page: the
    # confirm order page, every link must be shown; otherwise the delivery schedule, a missing link is noted)
    item = requisition_items[number - 1]
    order = orders[number]
    if order.get("removed"):
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    if confirm_page:
        assert order.get("delivery_schedule"), f"Order {number}: delivery schedule is not prepared"
    else:
        assert order.get("checked_out"), f"Order {number}: the cart is not checked out"
    checkout_page = CheckoutPage(page)
    page_name, label = ("Confirm order", f'order_{number}_confirm') if confirm_page \
        else ("Delivery schedule", f'order_{number}_schedule')

    # Step 1-2: Links (requisition, agreement attachment, product details) and item attachment
    with allure.step(f"Step 1-2: {page_name} - open the requisition details, agreement attachment, product details "
                     f"and item attachment"):
        if confirm_page:
            checkout_page.wait_for_confirm_order_step()
        order["confirm_order_links" if confirm_page else "delivery_schedule_links"] = check_checkout_links(
            page, item, order, label, links_required=confirm_page)
        checkout_page.get_full_page_screenshot(f'{label}_links_checked')
        attach_and_assert_checks(checkout_attachment_checks(page, item, label), f"Order {number} {page_name} item attachment")


def verify_order_details_links(page, number):
    # Why: the order details of order <number> must link to the agreement attachment (agreement number first),
    # requisition (ERP), product page, item attachment and the Preferred Delivery Schedule product and requisition;
    # When: the order details links test of order <number> (opens the order details after the confirmation)
    item = requisition_items[number - 1]
    order = orders[number]
    if order.get("removed"):
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    assert order.get("order_reference_number"), f"Order {number} is not confirmed"
    checkout_page = CheckoutPage(page)
    order_details_page = OrderDetails(page)

    # Step 1: Open the order details
    with allure.step(f"Step 1: Open the order details of {order['order_reference_number']}"):
        order["order_status"] = checkout_page.goto_public_side_order_details_view()
        print(f"ORDER {number} STATUS:", order["order_status"])
        order_details_page.get_full_page_screenshot(f'order_{number}_details')

    # Step 2: Agreement attachment (agreement number first), requisition, product page and item attachment
    with allure.step("Step 2: Download the agreement attachment, open the requisition details and product details, "
                     "download the item attachment"):
        link_checks, links = check_order_details_page_links(
            page, req_num, item["agreement_number"], item["item_code"], item["cart_attachment"],
            f'order_{number}_details', DOWNLOAD_DIR, requisition_product_name=requisition_product_name(item))
        attach_and_assert_checks(link_checks, f"Order {number} details links and item attachment")

    # Step 3: Preferred Delivery Schedule product name (not clicked) and requisition link
    with allure.step("Step 3: Verify the Preferred Delivery Schedule product name and open the requisition link"):
        schedule_requisition, opened_tabs = read_requisition_from_link(
            page, lambda: order_details_page.open_link_all_tabs(
                order_details_page.delivery_schedule_requisition_link(req_num)),
            f'order_{number}_details_schedule_erp_requisition')
        links["Delivery schedule requisition"] = schedule_requisition["req_no"]
        order["order_details_links"] = links
        checks = requisition_product_name_checks(page.locator("body"), requisition_product_name(item),
                                                 "Preferred Delivery Schedule")
        add_check(checks, "Preferred Delivery Schedule requisition link (ERP REQ. No)", req_num,
                  schedule_requisition["req_no"], schedule_requisition["req_no"] == req_num)
        add_check(checks, "Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed",
                  len(page.context.pages) == 1)
        order_details_page.get_full_page_screenshot(f'order_{number}_details_links_checked')
        attach_and_assert_checks(checks, f"Order {number} Preferred Delivery Schedule links")


def prepare_delivery_schedule(page, number):
    # Delivery schedule of order <number>: Requisition Schedule, the item; order 1 Auto Generate (quantity not
    # changed), order 2 manual schedules (quantity changed)
    item = requisition_items[number - 1]
    order = orders[number]
    if order.get("removed"):
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    assert order.get("delivery_schedule_links"), f"Order {number}: delivery schedule links are not verified"
    checkout_page = CheckoutPage(page)
    uom = order["cart_item"]["UoM"]

    # Step 1: Requisition Schedule (requisition / remaining quantity and delivery address)
    with allure.step(f"Step 1: Verify the Requisition Schedule of item {number}"):
        schedule_row = next((row for row in order["requisition_schedule"] if row.get("Requisition") == req_num), {})
        checkout_page.get_full_page_screenshot(f'order_{number}_schedule_requisition_schedule')
        checks = []
        add_check(checks, "Requisition Schedule Quantity (requisition / remaining quantity)",
                  f"{item['quantity']} or {item['remaining_quantity']}", schedule_row.get("Quantity", "not found"),
                  bool(schedule_row) and to_amount(schedule_row["Quantity"]) in
                  (to_amount(item["quantity"]), to_amount(item["remaining_quantity"])))
        add_check(checks, "Requisition Schedule Unit of Measure", uom, schedule_row.get("Unit of Measure", "-"),
                  schedule_row.get("Unit of Measure") == uom)
        add_check(checks, "Requisition Schedule Delivery Details (requisition delivery address)",
                  requisition["delivery_address"][:60], schedule_row.get("Delivery Details", "-")[:60],
                  without_spaces(requisition["delivery_address"]) in without_spaces(schedule_row.get("Delivery Details", "")))
        attach_and_assert_checks(checks, f"Order {number} Requisition Schedule vs requisition")

    # Step 2: The item before the schedule: cart quantity and remarks
    with allure.step("Step 2: Verify the cart quantity and remarks before the schedule"):
        page_text = checkout_page.get_page_text()
        remarks = expected_remarks_display(item["cart_remarks"])
        checks = []
        add_check(checks, "Cart quantity", item["cart_quantity"],
                  "on the page" if to_amount(item["cart_quantity"]) in numbers_in_text(page_text) else "not found",
                  to_amount(item["cart_quantity"]) in numbers_in_text(page_text))
        if item["cart_remarks"]:
            add_check(checks, "Remarks (cart remarks)", remarks[:60], "on the page" if remarks in page_text else "not found",
                      remarks in page_text)
        checkout_page.get_full_page_screenshot(f'order_{number}_schedule_item')
        attach_and_assert_checks(checks, f"Order {number} delivery schedule window vs shopping cart")

    if number == 1:
        # Step 3: Auto Generate (cart quantity = requisition quantity) and the receiving person
        with allure.step(f"Step 3: Click Auto Generate and fill the Receiving Person {order_admin_receiver}"):
            checkout_page.auto_generate_schedule()
            checkout_page.get_full_page_screenshot('order_1_schedule_auto_generate')
            checkout_page.fill_all_generated_schedule_receiving_persons(pin=order_admin_receiver)
            checkout_page.get_full_page_screenshot('order_1_schedule_receiving_person')
    else:
        # Step 3: Quantity changed (no Auto Generate): manual delivery schedules
        schedules = expected_schedules(2)
        with allure.step(f"Step 3: Schedule 1 - {schedules[0][0]} to {schedules[0][1]}"):
            checkout_page.fractional_schedule_update_quantity(delivery_schedule_quantity=str(schedules[0][0]))
            checkout_page.update_expected_date()
            checkout_page.delivery_schedule_preparation(location=schedules[0][1], pin=schedules[0][2])
            checkout_page.click_add_schedule_btn()
            checkout_page.wait_for_timeout(2000)
            checkout_page.get_full_page_screenshot('order_2_schedule_1')
        if len(schedules) == 2:
            with allure.step(f"Step 3: Schedule 2 - remaining quantity {schedules[1][0]} to {schedules[1][1]}"):
                checkout_page.delivery_schedule_preparation(location=schedules[1][1], pin=schedules[1][2])
                checkout_page.click_add_schedule_btn()
                checkout_page.get_full_page_screenshot('order_2_schedule_2')

    # Step 4: Continue
    with allure.step("Step 4: Wait until Continue is enabled and click Continue"):
        order["delivery_schedule"] = "; ".join(
            f"{quantity} to {location or 'the requisition delivery address (auto generated)'} ({receiver})"
            for quantity, location, receiver in expected_schedules(number))
        allure.attach(order["delivery_schedule"], name="Delivery schedule", attachment_type=allure.attachment_type.TEXT)
        checkout_page.click_continue_when_enabled()
        checkout_page.get_full_page_screenshot(f'order_{number}_schedule_continue')


def confirm_order(page, number):
    # Confirm order <number>: header, item, prices, schedules, FA link, attachment; order reference number
    item = requisition_items[number - 1]
    other_item = requisition_items[2 - number]
    order = orders[number]
    if order.get("removed"):
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    assert order.get("confirm_order_links"), f"Order {number}: confirm order links are not verified"
    check_remarks_length("test_order_remarks", order_remarks)
    checkout_page = CheckoutPage(page)
    checkout_page.wait_for_confirm_order_step()
    page_text = checkout_page.get_page_text()
    page_numbers = numbers_in_text(page_text)

    # Step 1: Order header, item, prices and schedules of this vendor only
    with allure.step(f"Step 1: Verify the confirm order information of item {number} ({item['vendor']})"):
        checks = []
        expected_texts = [("Framework Agreement", item["agreement_number"]), ("Vendor Name", item["vendor"]),
                          ("Requisition number", req_num), ("Master item", item["master_item_code"]),
                          ("Agreement item", item["item_code"]),
                          ("Specification", " ".join(item["specification"].split())),
                          ("UoM", order["cart_item"]["UoM"])]
        if item["cart_remarks"]:
            expected_texts.append(("Remarks (cart remarks)", item["cart_remarks"]))
        else:
            # Empty cart remarks are shown blank before the integration (N/A only after it): the requisition
            # remarks are not shown any more
            removed = without_spaces(item["remarks"]) not in without_spaces(page_text)
            add_check(checks, "Remarks (changed to empty in the cart): requisition remarks not shown", "not shown",
                      "not shown" if removed else "shown", removed)
        expected_numbers = [("Qty. (cart quantity)", to_amount(item["cart_quantity"])),
                            ("Unit Price", to_amount(item["unit_price"])),
                            ("Total Price / order total (Qty. x Unit Price)", item_total(item))]
        for schedule_number, (quantity, location, receiver) in enumerate(expected_schedules(number), start=1):
            expected_numbers.append((f"Schedule {schedule_number} quantity", quantity))
            expected_texts.append((f"Schedule {schedule_number} place", location or requisition["delivery_address"]))
        for check, expected in expected_texts:
            found = without_spaces(expected) in without_spaces(page_text)
            add_check(checks, check, expected[:60], "on the page" if found else "not found", found)
        for check, expected in expected_numbers:
            add_check(checks, check, expected, "on the page" if expected in page_numbers else "not found",
                      expected in page_numbers)
        # One order per vendor: the item of the other vendor is not in this order
        add_check(checks, f"Other vendor item ({other_item['agreement_number']}) not in this order", "not shown",
                  "shown" if other_item["agreement_number"] in page_text else "not shown",
                  other_item["agreement_number"] not in page_text)
        checkout_page.get_full_page_screenshot(f'order_{number}_confirm_information')
        attach_and_assert_checks(checks, f"Order {number} confirm order information")

    # Step 2: Order remarks, terms of service and confirm
    with allure.step(f"Step 2: Fill order remarks '{order_remarks}', accept terms of service and confirm"):
        checkout_page.fillup_order_remarks(input_remarks=order_remarks)
        checkout_page.select_terms_of_service()
        checkout_page.get_full_page_screenshot(f'order_{number}_remarks_terms')
        order["order_reference_number"] = checkout_page.confirm_order()
        assert order["order_reference_number"], "Order reference number not displayed after Confirm"
        print(f"ORDER {number} REFERENCE NUMBER:", order["order_reference_number"])
        checkout_page.wait_for_timeout(2000)
        checkout_page.get_full_page_screenshot(f'order_{number}_confirmed')


def verify_order_details(page, number):
    # Why: the order details of order <number> must be the order that was created; When: the order details
    # information test (information, product, schedules, Action History; Order Date last)
    item = requisition_items[number - 1]
    order = orders[number]
    if order.get("removed"):
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    assert order.get("order_details_links"), f"Order {number}: order details links are not verified"
    order_details_page = OrderDetails(page)
    uom = order["cart_item"]["UoM"]
    # Order Date check (asserted in the last step)
    last_step_checks = []

    # Step 1: Order information
    with allure.step(f"Step 1: Verify the order information of {order['order_reference_number']}"):
        information = {label: order_details_page.get_order_field(label)
                       for label in ("Order Reference No", "Framework Agreement", "Order Date", "Order Status",
                                     "Order Total", "Letter Pad Type", "Order Remarks", "Vendor Name", "Programme Name")}
        order["order_details_information"] = information
        print(f"ORDER {number} DETAILS INFORMATION:", information)
        order_details_page.get_full_page_screenshot(f'order_{number}_details_information')
        checks = []
        add_check(checks, "Order Reference No", order["order_reference_number"], information["Order Reference No"],
                  information["Order Reference No"] == order["order_reference_number"])
        add_check(checks, "Framework Agreement", item["agreement_number"], information["Framework Agreement"],
                  information["Framework Agreement"] == item["agreement_number"])
        add_check(checks, "Order Status", "not empty", information["Order Status"], bool(information["Order Status"]))
        add_check(checks, "Order Total (cart quantity x Unit Price)", item_total(item), information["Order Total"],
                  to_amount(information["Order Total"]) == item_total(item))
        add_check(checks, "Order Remarks", order_remarks, information["Order Remarks"],
                  same_remarks(order_remarks, information["Order Remarks"]))
        add_check(checks, "Vendor Name", item["vendor"], information["Vendor Name"],
                  information["Vendor Name"].lower() == item["vendor"].lower())
        attach_and_assert_checks(checks, f"Order {number} details information")

    # Step 2: Product and Sub-Total
    with allure.step(f"Step 2: Verify the product (item {number}) and the Sub-Total"):
        product_rows = order_details_page.get_product_rows()
        product = order_details_page.read_product_row(product_rows[0])
        product["Sub-Total"] = order_details_page.get_sub_total()
        order["order_details_product"] = product
        checks = []
        add_check(checks, "Products (one item of this vendor)", 1, len(product_rows), len(product_rows) == 1)
        add_check(checks, "Master item", item["master_item_code"], product["Master item"],
                  product["Master item"].startswith(item["master_item_code"]))
        add_check(checks, "Requisition number", req_num, product["Requisition"], product["Requisition"] == req_num)
        add_check(checks, "FA No.", item["agreement_number"], product["FA No."], product["FA No."] == item["agreement_number"])
        add_check(checks, "Agreement item", item["item_code"], product["Agreement item"],
                  item["item_code"] in product["Agreement item"])
        add_check(checks, "Specification", item["specification"], product["Specification"],
                  product["Specification"] == " ".join(item["specification"].split()))
        add_check(checks, "Remarks (cart remarks; empty -> blank or N/A)",
                  expected_remarks_display(item["cart_remarks"])[:60] if item["cart_remarks"] else "blank or N/A",
                  product["Remarks"][:60] or "(blank)", remarks_shown(item["cart_remarks"], product["Remarks"]))
        add_check(checks, "Attachment icon", "shown" if item["cart_attachment"] else "not shown (removed in the cart)",
                  "shown" if product["Attachment icon"] else "not shown",
                  product["Attachment icon"] == bool(item["cart_attachment"]))
        add_check(checks, "UoM", uom, product["UoM"], product["UoM"] == uom)
        add_check(checks, "Quantity (cart quantity)", item["cart_quantity"], product["Quantity"],
                  to_amount(product["Quantity"]) == to_amount(item["cart_quantity"]))
        add_check(checks, "Unit Price", item["unit_price"], product["Unit Price"],
                  to_amount(product["Unit Price"]) == to_amount(item["unit_price"]))
        add_check(checks, "Total Price (Qty. x Unit Price)", item_total(item), product["Total Price"],
                  to_amount(product["Total Price"]) == item_total(item))
        add_check(checks, "Sub-Total", item_total(item), product["Sub-Total"], to_amount(product["Sub-Total"]) == item_total(item))
        order_details_page.get_full_page_screenshot(f'order_{number}_details_product')
        attach_and_assert_checks(checks, f"Order {number} details product and totals")

    # Step 3: Preferred Delivery Schedule and Action History
    with allure.step("Step 3: Verify the Preferred Delivery Schedule and store the Action History"):
        schedules = order_details_page.get_all_preferred_delivery_schedules()
        order["order_details_delivery_schedule"] = schedules
        order["order_action_history"] = order_details_page.get_action_history()
        allure.attach(
            "\n".join(" | ".join(f"{title}: {value}" for title, value in row.items()) for row in order["order_action_history"]),
            name=f"Order {number} Action History",
            attachment_type=allure.attachment_type.TEXT
        )
        submitted_rows = [row for row in order["order_action_history"] if row.get("Order Status") == "Submitted for Approval"
                          and proj_user in row.get("Action Taken By", "")]
        submitted_date = submitted_rows[0].get("Time", "").split(" ")[0] if submitted_rows else ""
        checks = []
        add_check(checks, "Delivery schedules", len(expected_schedules(number)), len(schedules),
                  len(schedules) == len(expected_schedules(number)))
        for schedule_number, (quantity, location, receiver) in enumerate(expected_schedules(number), start=1):
            place = location or requisition["delivery_address"]
            schedule = next((row for row in schedules if to_amount(row.get("Quantity", "0")) == quantity), {})
            add_check(checks, f"Schedule {schedule_number} Quantity", quantity, schedule.get("Quantity", "not found"),
                      bool(schedule))
            add_check(checks, f"Schedule {schedule_number} Location", place[:60], schedule.get("Location", "-")[:60],
                      without_spaces(place).lower() in without_spaces(schedule.get("Location", "")).lower())
            add_check(checks, f"Schedule {schedule_number} Receiver Info", receiver, schedule.get("Receiver Info", "-"),
                      receiver in schedule.get("Receiver Info", ""))
        add_check(checks, "Action History - Submitted for Approval by the requisition initiator", proj_user,
                  submitted_rows[0]["Action Taken By"] if submitted_rows else "-", bool(submitted_rows))
        add_check(last_step_checks, "Order Date (date the order was submitted)", submitted_date,
                  information["Order Date"], information["Order Date"] == submitted_date)
        order_details_page.get_full_page_screenshot(f'order_{number}_details_schedule_action_history')
        attach_and_assert_checks(checks, f"Order {number} Preferred Delivery Schedule and Action History")

    # Step 4: Save the order result
    with allure.step("Step 4: Save the order result"):
        save_orders_result()

    # Step 5: Order Date
    with allure.step("Step 5: Verify the Order Date (date the order was submitted)"):
        attach_and_assert_checks(last_step_checks, f"Order {number} details Order Date")


def verify_order_preview(page, number):
    # Preview of order <number>: order document (PDF) address, letter pad, status, Purchase Order, item, totals
    item = requisition_items[number - 1]
    other_item = requisition_items[2 - number]
    order = orders[number]
    if order.get("removed"):
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    assert order.get("order_details_links"), f"Order {number}: order details links are not verified"
    order_details_page = OrderDetails(page)
    order_reference_number = order["order_reference_number"]

    # Step 1: Preview, download the order document (PDF) and check the preview address
    with allure.step("Step 1: Click Preview, download the order document and verify the preview address"):
        preview_tab = open_erp_requisition(order_details_page.open_order_preview)
        preview = {"url": preview_tab.url}
        order_document = order_details_page.download_order_document(
            preview_tab, DOWNLOAD_DIR, f"order_document_{order_reference_number.replace('/', '_')}.pdf")
        preview["order_document"] = order_document.name
        allure.attach.file(str(order_document), name=f"Order {number} document - {order_document.name}")
        preview_parameters = {key: values[0] for key, values in parse_qs(urlparse(preview_tab.url).query).items()}
        tracking_number = base64.b64decode(preview_parameters.get("trackingNumber", "")).decode("utf-8", "ignore")
        preview_status = base64.b64decode(preview_parameters.get("Status", "")).decode("utf-8", "ignore")
        checks = []
        add_check(checks, "Order document is a PDF", "%PDF", order_document.read_bytes()[:4].decode("latin-1"),
                  order_document.read_bytes()[:4] == b"%PDF")
        add_check(checks, "Preview tracking number (order reference)", order_reference_number, tracking_number,
                  tracking_number == order_reference_number)
        add_check(checks, "Preview status (same as order details)", order["order_status"], preview_status,
                  preview_status == order["order_status"])
        add_check(checks, "Preview letter pad (BRAC)", "1", preview_parameters.get("letterPad", "-"),
                  preview_parameters.get("letterPad") == "1")
        attach_and_assert_checks(checks, f"Order {number} preview address and document")
        preview_text = order_details_page.read_order_document_text(order_document)
        preview_numbers = numbers_in_text(preview_text)
        allure.attach(preview_text, name=f"Order {number} document text", attachment_type=allure.attachment_type.TEXT)

    # Step 2: Letter pad, status, Purchase Order, item details, totals, delivery schedules
    with allure.step(f"Step 2: Verify the order document (item {number} only, totals, delivery date and place)"):
        purchase_order_match = re.search(r"Purchase Order:\s*(\S+)", preview_text)
        preview["purchase_order_number"] = purchase_order_match.group(1) if purchase_order_match else ""
        preview["amount_in_words"] = order_details_page.get_amount_in_words(preview_text)
        print(f"ORDER {number} PURCHASE ORDER NUMBER:", preview["purchase_order_number"])
        has_paisa = item_total(item) % 1 != 0
        preview_text_no_spaces = without_spaces(preview_text)
        checks = []
        add_check(checks, "Letter Pad Type (order details)", "BRAC", order["order_details_information"]["Letter Pad Type"],
                  order["order_details_information"]["Letter Pad Type"] == "BRAC")
        add_check(checks, "Purchase Order number", "shown", preview["purchase_order_number"] or "not found",
                  bool(preview["purchase_order_number"]))
        expected_texts = [("Letter pad", "BRAC"), ("Order status", order["order_status"]),
                          ("Requisition number", req_num), ("FA No.", item["agreement_number"]),
                          ("Master item", item["master_item_code"]), ("Agreement item", item["item_code"]),
                          ("Specification", item["specification"]),
                          ("UoM", order["cart_item"]["UoM"])]
        if item["cart_remarks"]:
            expected_texts.append(("Remarks (cart remarks)", item["cart_remarks"]))
        else:
            removed = without_spaces(item["remarks"]) not in preview_text_no_spaces
            add_check(checks, "Remarks (changed to empty in the cart): requisition remarks not in the document",
                      "not shown", "not shown" if removed else "shown", removed)
        expected_numbers = [("Quantity (cart quantity)", to_amount(item["cart_quantity"])),
                            ("Unit Price", to_amount(item["unit_price"])),
                            ("Total Price / Grand Total (Qty. x Unit Price)", item_total(item))]
        for schedule_number, (quantity, location, receiver) in enumerate(expected_schedules(number), start=1):
            expected_texts += [(f"Schedule {schedule_number} place", location or requisition["delivery_address"]),
                               (f"Schedule {schedule_number} receiver", receiver)]
            expected_numbers.append((f"Schedule {schedule_number} quantity", quantity))
        for check, expected in expected_texts:
            found = without_spaces(expected).lower() in preview_text_no_spaces.lower()
            add_check(checks, check, expected[:60], "on the preview" if found else "not found", found)
        for check, expected in expected_numbers:
            add_check(checks, check, expected, "on the preview" if expected in preview_numbers else "not found",
                      expected in preview_numbers)
        add_check(checks, "Amount in words (TAKA, PAISA when the total has paisa, ONLY)",
                  "... TAKA AND ... PAISA ONLY" if has_paisa else "... TAKA ONLY", preview["amount_in_words"] or "not found",
                  "TAKA" in preview["amount_in_words"] and ("PAISA" in preview["amount_in_words"]) == has_paisa
                  and preview["amount_in_words"].endswith("ONLY"))
        add_check(checks, f"Other vendor item ({other_item['item_code']}) not in this order document", "not shown",
                  "shown" if other_item["item_code"] in preview_text else "not shown",
                  other_item["item_code"] not in preview_text)
        attach_and_assert_checks(checks, f"Order {number} preview")

    # Step 3: Close the preview and save the order result
    with allure.step("Step 3: Close the preview and save the order result"):
        preview_tab.close()
        page.bring_to_front()
        order["order_preview"] = preview
        save_orders_result()


def save_orders_result():
    # Both orders of the requisition (one per vendor) for the pending approval test file
    global order_result
    order_result = {
        "requisition_number": req_num,
        "order_approver": requisition["final_approver"],
        "order_remarks": order_remarks,
        "delivery_address": requisition["delivery_address"],
        "orders": [{
            "order_reference_number": orders[number].get("order_reference_number", ""),
            "order_status": orders[number].get("order_status", ""),
            "removed_from_cart": bool(orders[number].get("removed")),
            "vendor": item["vendor"],
            "agreement_number": item["agreement_number"],
            "agreement_version": item["agreement_version"],
            "item_code": item["item_code"],
            "requisition_product_name": requisition_product_name(item),
            "master_item_code": item["master_item_code"],
            "specification": " ".join(item["specification"].split()),
            "uom": orders[number].get("cart_item", {}).get("UoM", ""),
            "cart_remarks_entered": item["cart_remarks"],
            "expected_schedules": [{"Quantity": str(quantity), "Location": location or requisition["delivery_address"],
                                    "Receiver": receiver} for quantity, location, receiver in expected_schedules(number)],
            "requisition_quantity": item["quantity"],
            "remaining_quantity": item["remaining_quantity"],
            "cart_quantity": item["cart_quantity"],
            "unit_price": item["unit_price"],
            "total_price": str(item_total(item)),
            "cart_remarks": expected_remarks_display(item["cart_remarks"]),
            "cart_attachment": item["cart_attachment"],
            "cart_changes": orders[number].get("cart_changes", {}),
            "delivery_schedule": orders[number].get("delivery_schedule", ""),
            "order_details_information": orders[number].get("order_details_information", {}),
            "order_details_product": orders[number].get("order_details_product", {}),
            "order_details_delivery_schedule": orders[number].get("order_details_delivery_schedule", []),
            "order_action_history": orders[number].get("order_action_history", []),
            "order_details_links": orders[number].get("order_details_links", {}),
            "order_preview": orders[number].get("order_preview", {}),
        } for number, item in enumerate(requisition_items, start=1)],
    }
    save_result("different_vendor_agreement_items_order_result", order_result)
    allure.attach(
        "\n".join(f"Order {number}: {order['order_reference_number'] or '-'} | {order['vendor']} | {order['item_code']} | "
                  f"cart quantity {order['cart_quantity']} | total {order['total_price']} | {order['cart_changes']}"
                  for number, order in enumerate(order_result["orders"], start=1)),
        name="Saved order result",
        attachment_type=allure.attachment_type.TEXT
    )


# ---------------- Test cases ----------------

@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Items Before Vendor Selection")
@allure.title("Test_case_1: Verify shopping cart items of 2 vendors before vendor selection")
@allure.description("Test case 1: Before the vendor selection, verify both items of the requisition (2 framework "
                    "agreements of 2 different vendors) in the shopping cart, the cart (remaining) quantity and the links.")
@pytest.mark.order(1)
def test_1_verify_cart_items_before_vendor_selection(page):
    """
    Test case 1: Verify the shopping cart items of the requisition before the vendor selection.

    Steps:
        1. Load the requisition of different_vendor_agreement_items_requisition.py
           (different_vendor_agreement_requisition_result.json): item 1 (vendor 1) and item 2 (vendor 2).
        2. Log in to the Digital Marketplace as the order initiator ('proj_user').
        3. Shopping cart, before vendor selection: both items are in the cart; the cart quantity is the requisition
           quantity, or the remaining quantity when items of the requisition were ordered before (stored);
           for each item verify the Item/Service name & Specification (requisition remarks and attachment) and the
           links: requisition number (ERP requisition details, first item), FA No., agreement item and attachment
           (same file type as the requisition attachment).
        No logout: Test case 2 continues in the shopping cart.

    All scenario values are read from .env.
    """
    global requisition, req_num, requisition_items, cart_items_before_vendor

    required_env_values = {
        "test_user_name": proj_user,
        "test_env": proj_env,
        "test_url": erp_url,
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_requisition_item_remarks": requisition_item_remarks,
        "test_requisition_item_remarks_500": requisition_item_remarks_500,
        "test_requisition_attachment_file_jpg": cart_attachment_file,
        "test_cart_item_quantity": cart_item_quantity,
        "test_order_admin_receiver": order_admin_receiver,
        "test_delivery_schedule_quantity": delivery_schedule_quantity,
        "test_delivery_location_1": manual_delivery_location_1,
        "test_delivery_location_2": manual_delivery_location_2,
        "test_receiving_pin": receiving_pin_1,
        "test_order_initiator": order_initiator,
        "test_order_remarks": order_remarks,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    check_remarks_length("test_cart_item_remarks", cart_item_remarks)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    login_page = LoginPage(page)
    home_page = HomePage(page)
    cart_page = ShoppingCart(page)

    # Step 1: Requisition from different_vendor_agreement_items_requisition.py
    with allure.step("Step 1: Load the requisition result of different_vendor_agreement_items_requisition.py"):
        requisition = load_result("different_vendor_agreement_requisition_result",
                                  created_by="different_vendor_agreement_items_requisition.py")
        req_num = requisition["requisition_number"]
        assert len(requisition["items"]) == 2, f"The requisition must have 2 items, found {len(requisition['items'])}"
        # Item remarks of the requisition file: the 500 character remarks or the short remarks (by their length)
        requisition_items = []
        for item in requisition["items"]:
            remarks = requisition_item_remarks_500 if item["remarks_length"] == len(requisition_item_remarks_500) \
                else requisition_item_remarks
            assert len(remarks) == item["remarks_length"], \
                f"{item['item_code']} remarks length {item['remarks_length']} does not match the .env remarks"
            check_remarks_length(f"{item['item_code']} remarks", remarks)
            # Cart values start as the requisition values; the cart quantity is read from the shopping cart
            requisition_items.append(dict(item, remarks=remarks, cart_remarks=remarks,
                                          cart_attachment=item["attachment_name"], cart_quantity=item["quantity"],
                                          remaining_quantity=item["quantity"]))
        assert requisition_items[0]["vendor"] != requisition_items[1]["vendor"], "The items must have different vendors"
        print("REQ NUM:", req_num)
        allure.attach(
            "\n".join(f"Item {number}: {item['vendor']} | {item['agreement_number']} | {item['item_code']} | "
                      f"quantity {item['quantity']} | unit price {item['unit_price']} | {item['attachment_name']} | "
                      f"remarks ({len(item['remarks'])} characters)" for number, item in enumerate(requisition_items, 1)),
            name="Requisition items (one order per vendor)",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 2: Log in to the Digital Marketplace
    with allure.step(f"Step 2: Log in to the Digital Marketplace as {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=proj_user, pass_word=marketplace_password)
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('order_cart_login')

    # Step 3: Shopping cart, before vendor selection
    with allure.step(f"Step 3: Verify requisition {req_num} items in the shopping cart (before vendor selection)"):
        home_page.goto_shopping_cart()
        assert cart_page.wait_for_requisition_in_cart(requisition_number=req_num), \
            f"Requisition {req_num} is not synced to the shopping cart"
        cart_page.get_full_page_screenshot('order_cart_before_vendor')
        cart_rows = get_cart_rows_by_fa(cart_page)
        missing_items = [item["agreement_number"] for item in requisition_items if item["agreement_number"] not in cart_rows]
        assert not missing_items, f"Requisition items not in the cart: {missing_items} (found {list(cart_rows)})"
        failed_items = []
        # FIFO: the items are checked from the top cart row down (requisition link: opened for the top item)
        page_items = in_page_order(list(enumerate(requisition_items, start=1)),
                                   lambda numbered: cart_rows.get(numbered[1]["agreement_number"]))
        for number, item in page_items:
            try:
                with allure.step(f"Item {number}: {item['vendor']} - {item['agreement_number']} - {item['item_code']}"):
                    # Cart quantity: the requisition quantity, or the remaining quantity when items of the
                    # requisition were ordered before
                    cart_quantity = cart_page.read_cart_item_cell(cart_rows[item["agreement_number"]])["Qty."]
                    assert Decimal(0) < to_amount(cart_quantity) <= to_amount(item["quantity"]), \
                        f"Cart quantity {cart_quantity} must be more than 0 and max the requisition quantity {item['quantity']}"
                    item["cart_quantity"] = item["remaining_quantity"] = cart_quantity
                    keep_earlier_cart_changes(cart_page, cart_rows[item["agreement_number"]], item, number)
                    allure.attach(f"Requisition quantity: {item['quantity']}\nCart (remaining) quantity: {cart_quantity}"
                                  + ("" if to_amount(cart_quantity) == to_amount(item["quantity"])
                                     else "\nPart of the requisition quantity was ordered before"),
                                  name=f"Item {number} quantity", attachment_type=allure.attachment_type.TEXT)
                    cart_items_before_vendor[item["agreement_number"]] = verify_cart_item(
                        cart_page, cart_rows[item["agreement_number"]], item, f"before_vendor_item_{number}",
                        check_erp_links=item is page_items[0][1])
            except AssertionError as error:
                failed_items.append(f"Item {number}: {error}")
        assert not failed_items, "\n".join(failed_items)


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Order 1 - Cart")
@allure.title("Test_case_2: Order 1 - select vendor 1, empty remarks, remove attachment and checkout")
@allure.description("Test case 2: Select the vendor of item 1, change the item remarks to empty and remove the "
                    "attachment (quantity not changed), verify only item 1 goes to the checkout and checkout.")
@pytest.mark.order(2)
def test_2_order_1_select_vendor_and_checkout(page):
    """
    Test case 2: Order 1 (vendor of item 1) - shopping cart.
    Continues in the shopping cart of Test case 1 (no new login).

    Steps:
        1. Select the vendor of item 1 (only this requisition stays ticked).
        2. Verify item 1 (requisition values) and its links.
        3. Change the remarks to empty, remove the attachment (pop-up Yes) and update the shopping cart; the
           quantity is not changed.
        4. Verify item 1 after the changes (remarks blank, no attachment, same quantity).
        5. Accept terms of service and checkout.
        6. Checkout: only item 1 is in the Requisition Schedule (the item of vendor 2 is not).
    """
    assert cart_items_before_vendor, "Test case 1 must pass first: shopping cart items are not verified"
    select_vendor_and_checkout(page, 1)


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 1 - Delivery Schedule Links")
@allure.title("Test_case_3: Order 1 - verify delivery schedule links")
@allure.description("Test case 3: On the delivery schedule, open the requisition details, agreement attachment and product details links (a link that is not on this step is noted) and check the item attachment.")
@pytest.mark.order(3)
def test_3_order_1_verify_delivery_schedule_links(page):
    """
    Test case 3: Order 1 (vendor of item 1) - verify delivery schedule links.
    """
    verify_checkout_page_links(page, 1, confirm_page=False)

@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 1 - Delivery Schedule")
@allure.title("Test_case_4: Order 1 - prepare delivery schedule with Auto Generate")
@allure.description("Test case 4: Verify the Requisition Schedule and the item (cart quantity, remarks), then prepare the delivery schedule (Auto Generate, receiving person 'test_order_admin_receiver').")
@pytest.mark.order(4)
def test_4_order_1_prepare_delivery_schedule(page):
    """
    Test case 4: Order 1 (vendor of item 1) - prepare delivery schedule with Auto Generate.
    """
    prepare_delivery_schedule(page, 1)

@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 1 - Confirm Order Links")
@allure.title("Test_case_5: Order 1 - verify confirm order links")
@allure.description("Test case 5: On the confirm order page, open the requisition details (ERP), download the agreement attachment, open the product details page and check the item attachment.")
@pytest.mark.order(5)
def test_5_order_1_verify_confirm_order_links(page):
    """
    Test case 5: Order 1 (vendor of item 1) - verify confirm order links.
    """
    verify_checkout_page_links(page, 1, confirm_page=True)

@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 1 - Confirm Order")
@allure.title("Test_case_6: Order 1 - confirm order")
@allure.description("Test case 6: Verify the confirm order information of this vendor's item (the other vendor's item is not in the order), confirm the order and get the order reference number.")
@pytest.mark.order(6)
def test_6_order_1_confirm_order(page):
    """
    Test case 6: Order 1 (vendor of item 1) - confirm order.
    """
    confirm_order(page, 1)

@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order 1 - Order Details Links")
@allure.title("Test_case_7: Order 1 - verify order details links")
@allure.description("Test case 7: Open the order details, download the agreement attachment (agreement number first), open the requisition details (ERP), product details page, Preferred Delivery Schedule product and requisition links, and check the item attachment.")
@pytest.mark.order(7)
def test_7_order_1_verify_order_details_links(page):
    """
    Test case 7: Order 1 (vendor of item 1) - verify order details links.
    """
    verify_order_details_links(page, 1)

@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order 1 - Order Details Information")
@allure.title("Test_case_8: Order 1 - verify order details information")
@allure.description("Test case 8: Verify the order information, product, Preferred Delivery Schedule and Action History, save the result; the Order Date is checked last.")
@pytest.mark.order(8)
def test_8_order_1_verify_order_details_information(page):
    """
    Test case 8: Order 1 (vendor of item 1) - verify order details information.
    """
    verify_order_details(page, 1)

@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order 1 - Order Preview")
@allure.title("Test_case_9: Order 1 - verify order preview")
@allure.description("Test case 9: Click Preview, download the order document and verify it (BRAC letter pad, status, Purchase Order, item 1 only, totals, amount in words, delivery schedule).")
@pytest.mark.order(9)
def test_9_order_1_verify_order_preview(page):
    """
    Test case 9: Order 1 (vendor of item 1) - verify order preview.
    """
    verify_order_preview(page, 1)

@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Order 2 - Cart")
@allure.title("Test_case_10: Order 2 - select vendor 2, update remarks, attachment and quantity, checkout")
@allure.description("Test case 10: Item 2 (vendor 2) is still in the cart and item 1 (ordered) is not; select vendor 2, "
                    "update the remarks, upload a new attachment over the requisition attachment and update the "
                    "quantity ('test_cart_item_quantity'; 0 removes the item), verify and checkout.")
@pytest.mark.order(10)
def test_10_order_2_select_vendor_and_checkout(page):
    """
    Test case 10: Order 2 (vendor of item 2) - shopping cart.

    Steps:
        1. Go to the shopping cart: item 2 of the requisition is in the cart; item 1 (order 1) is not.
        2. Select the vendor of item 2 (only this requisition ticked) and verify item 2 and its links.
        3. Update the remarks ('test_cart_item_remarks'), upload 'test_requisition_attachment_file_jpg' without
           removing the requisition attachment and update the quantity ('test_cart_item_quantity': max the cart /
           remaining quantity; 0 removes the item from the shopping cart and there is no order 2).
        4. Verify item 2 after the changes (store all values).
        5-6. Checkout: only item 2 is in the Requisition Schedule.

    All scenario values are read from .env.
    """
    assert cart_items_before_vendor, "Test case 1 must pass first: shopping cart items are not verified"
    home_page = HomePage(page)
    cart_page = ShoppingCart(page)

    # Step 1: Shopping cart after order 1
    with allure.step(f"Step 1: Item 2 of {req_num} is still in the shopping cart and item 1 (order 1) is not"):
        home_page.goto_shopping_cart()
        assert cart_page.wait_for_requisition_in_cart(requisition_number=req_num), \
            f"Requisition {req_num} (item 2) is not in the shopping cart"
        cart_rows = get_cart_rows_by_fa(cart_page)
        cart_page.get_full_page_screenshot('order_2_cart_after_order_1')
        checks = []
        add_check(checks, f"Item 2 ({requisition_items[1]['agreement_number']}) in the cart", "in the cart",
                  "in the cart" if requisition_items[1]["agreement_number"] in cart_rows else "not found",
                  requisition_items[1]["agreement_number"] in cart_rows)
        if orders[1].get("order_reference_number"):
            add_check(checks, f"Item 1 ({requisition_items[0]['agreement_number']}) not in the cart (order 1)",
                      "not in the cart", "in the cart" if requisition_items[0]["agreement_number"] in cart_rows
                      else "not in the cart", requisition_items[0]["agreement_number"] not in cart_rows)
        attach_and_assert_checks(checks, "Shopping cart after order 1")

    select_vendor_and_checkout(page, 2)


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 2 - Delivery Schedule Links")
@allure.title("Test_case_11: Order 2 - verify delivery schedule links")
@allure.description("Test case 11: On the delivery schedule, open the requisition details, agreement attachment and product details links (a link that is not on this step is noted) and check the item attachment.")
@pytest.mark.order(11)
def test_11_order_2_verify_delivery_schedule_links(page):
    """
    Test case 11: Order 2 (vendor of item 2) - verify delivery schedule links.
    """
    verify_checkout_page_links(page, 2, confirm_page=False)

@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 2 - Delivery Schedule")
@allure.title("Test_case_12: Order 2 - prepare delivery schedule")
@allure.description("Test case 12: Verify the Requisition Schedule and the item (cart quantity, remarks), then prepare the delivery schedule (quantity changed: 2 manual schedules).")
@pytest.mark.order(12)
def test_12_order_2_prepare_delivery_schedule(page):
    """
    Test case 12: Order 2 (vendor of item 2) - prepare delivery schedule.
    """
    prepare_delivery_schedule(page, 2)

@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 2 - Confirm Order Links")
@allure.title("Test_case_13: Order 2 - verify confirm order links")
@allure.description("Test case 13: On the confirm order page, open the requisition details (ERP), download the agreement attachment, open the product details page and check the item attachment.")
@pytest.mark.order(13)
def test_13_order_2_verify_confirm_order_links(page):
    """
    Test case 13: Order 2 (vendor of item 2) - verify confirm order links.
    """
    verify_checkout_page_links(page, 2, confirm_page=True)

@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Order 2 - Confirm Order")
@allure.title("Test_case_14: Order 2 - confirm order")
@allure.description("Test case 14: Verify the confirm order information of this vendor's item (the other vendor's item is not in the order), confirm the order and get the order reference number.")
@pytest.mark.order(14)
def test_14_order_2_confirm_order(page):
    """
    Test case 14: Order 2 (vendor of item 2) - confirm order.
    """
    confirm_order(page, 2)

@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order 2 - Order Details Links")
@allure.title("Test_case_15: Order 2 - verify order details links")
@allure.description("Test case 15: Open the order details, download the agreement attachment (agreement number first), open the requisition details (ERP), product details page, Preferred Delivery Schedule product and requisition links, and check the item attachment.")
@pytest.mark.order(15)
def test_15_order_2_verify_order_details_links(page):
    """
    Test case 15: Order 2 (vendor of item 2) - verify order details links.
    """
    verify_order_details_links(page, 2)

@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order 2 - Order Details Information")
@allure.title("Test_case_16: Order 2 - verify order details information")
@allure.description("Test case 16: Verify the order information, product, Preferred Delivery Schedule and Action History, save the result; the Order Date is checked last.")
@pytest.mark.order(16)
def test_16_order_2_verify_order_details_information(page):
    """
    Test case 16: Order 2 (vendor of item 2) - verify order details information.
    """
    verify_order_details(page, 2)

@allure.suite("Public Side")
@allure.feature("Order Details")
@allure.story("Order 2 - Order Preview")
@allure.title("Test_case_17: Order 2 - verify order preview, both orders and log out")
@allure.description("Test case 17: Verify the order document of order 2, then both orders of the requisition (one "
                    "order per vendor, different order numbers, order totals = cart totals), log out and save.")
@pytest.mark.order(17)
def test_17_order_2_verify_order_preview_and_both_orders(page):
    """
    Test case 17: Order 2 - order preview and both orders.

    Steps:
        1-3. Order 2 preview (item 2 with its cart values).
        4. Both orders: 2 different order reference numbers, each with the vendor of its own; order 1 total +
           order 2 total = the cart totals (cart quantity x unit price) of the 2 items.
        5. Log out and save the order result.
    """
    if not orders[2].get("removed"):
        verify_order_preview(page, 2)

        # Step 4: One order per vendor
        with allure.step("Step 4: Verify both orders of the requisition (one order per vendor)"):
            checks = []
            references = [orders[number].get("order_reference_number", "") for number in (1, 2)]
            add_check(checks, "2 different order reference numbers", "different", " / ".join(references),
                      all(references) and references[0] != references[1])
            for number, item in enumerate(requisition_items, start=1):
                information = orders[number].get("order_details_information", {})
                add_check(checks, f"Order {number} Vendor Name", item["vendor"], information.get("Vendor Name", "-"),
                          information.get("Vendor Name", "").lower() == item["vendor"].lower())
            order_totals = [to_amount(orders[number].get("order_details_information", {}).get("Order Total", "0"))
                            for number in (1, 2)]
            cart_total = item_total(requisition_items[0]) + item_total(requisition_items[1])
            add_check(checks, "Order 1 total + order 2 total = cart totals of the 2 items", cart_total,
                      sum(order_totals), sum(order_totals) == cart_total)
            attach_and_assert_checks(checks, "Both orders of the requisition")

    # Step 5: Log out and save the order result
    with allure.step("Step 5: Log out and save the order result"):
        MainNavigationMenu(page).perform_logout()
        HomePage(page).get_full_page_screenshot('order_initiator_logout')
        save_orders_result()
        print("ORDER RESULT:", order_result)
