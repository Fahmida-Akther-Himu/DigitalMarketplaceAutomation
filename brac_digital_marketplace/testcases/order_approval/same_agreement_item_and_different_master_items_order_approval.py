from dotenv import load_dotenv
import os
import re
import base64
from decimal import Decimal
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import pytest
import allure

load_dotenv()

# Digital Marketplace (staging)
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
# Receiving person of the auto generated delivery schedules of the order
order_initiator = os.getenv("test_order_initiator")
# Approval message when the order approver has no email address (staging email configuration)
EMAIL_NOT_SENT_MESSAGE = "Email sent failed"
# Project root is 3 levels up: testcases/order_approval/<this file>
DOWNLOAD_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "downloads"

from utils.test_data_store import load_result, save_result
from utils.remarks_rules import same_remarks
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.my_account.pending_approval_orders import PendingApprovalOrders
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails
from brac_digital_marketplace.testcases.order_creation.order_page_links import \
    check_order_details_all_products_links, read_requisition_from_link, find_product_row
from brac_digital_marketplace.testcases.order_creation.order_details_checks import ORDER_INFORMATION_FIELDS, \
    check_delivery_schedules, check_action_history, open_preview_tab, to_amount, numbers_in_text, new_check, \
    without_spaces, receiver_of

# Order of same_agreement_item_and_different_master_items_order.py
# (same_agreement_item_and_different_master_items_order_result.json): the same agreement item of one framework
# agreement and one vendor with 2 different master items (PDF and DOCX attachment), auto generated delivery
# schedules. Both items have the same agreement item code: each product is found by its master item.
order = {}
order_reference_number = ''
order_approver = ''
# Pending approval list (Test case 1): the order is searched once
pending_approval_order_count = ''
order_found_in_pending_list = False
list_order_date = ''
list_order_total = ''
# Pending approval order details (Test case 2-4)
details_before_approval = {}
order_details_links = {}
delivery_schedule = []
# Order approval (Test case 5-7)
approved_order_status = ''
approval_confirmation_message = ''
details_after_approval = {}
order_preview = {}
# Order approval result for the next test file
order_approval_result = {}


def attach_and_assert_checks(checks, title):
    # Why: list the checks of a step in the report (expected / actual / result); When: after the checks of a
    # step; the test fails if any check failed
    allure.attach(
        "\n".join(f"{check}: expected {expected} | actual {actual} | {result}" for check, expected, actual, result in checks),
        name=title,
        attachment_type=allure.attachment_type.TEXT
    )
    failed_checks = [f"{check}: expected {expected}, found {actual}"
                     for check, expected, actual, result in checks if result == "FAIL"]
    assert not failed_checks, f"{title}:\n" + "\n".join(failed_checks)


def order_total():
    # Why: the order total is the sum of the 2 item totals (Qty. x Unit Price); When: order information, Sub-Total
    # and preview checks
    return sum((to_amount(item["total_price"]) for item in order["items"]), Decimal("0.00"))


def expected_schedules():
    # Why: the Preferred Delivery Schedule must be the auto generated schedules of the order (requisition quantity,
    # requisition delivery address, receiver 'test_order_initiator'); When: order details and preview checks
    return [{"Quantity": item["quantity"], "Location": order["delivery_address"], "Receiver": order_initiator}
            for item in order["items"]]


def check_information(page, order_status):
    # Why: the order information must be the order that was created; When: order details checks before and after
    # the approval. Returns (checks, order information)
    information = {label: OrderDetails(page).get_order_field(label) for label in ORDER_INFORMATION_FIELDS}
    print("ORDER DETAILS INFORMATION:", information)
    initiator_order_date = order["order_details_information"]["Order Date"]
    checks = [
        new_check("Order Reference No", order_reference_number, information["Order Reference No"],
                  information["Order Reference No"] == order_reference_number),
        new_check("Framework Agreement", order["agreement_number"], information["Framework Agreement"],
                  information["Framework Agreement"] == order["agreement_number"]),
        new_check("Order Status", order_status, information["Order Status"],
                  order_status.lower() in information["Order Status"].lower()),
        new_check("Order Total (sum of the 2 items)", order_total(), information["Order Total"],
                  to_amount(information["Order Total"]) == order_total()),
        new_check("Order Total (details = pending approval list)", list_order_total, information["Order Total"],
                  to_amount(information["Order Total"]) == to_amount(list_order_total)),
        new_check("Order Remarks", order["order_remarks"], information["Order Remarks"],
                  " ".join(information["Order Remarks"].split()) == " ".join(order["order_remarks"].split())),
        new_check("Vendor Name", order["vendor"], information["Vendor Name"],
                  information["Vendor Name"].lower() == order["vendor"].lower()),
        new_check("Letter Pad Type", "BRAC", information["Letter Pad Type"], information["Letter Pad Type"] == "BRAC"),
        new_check("Order Date (details = pending approval list)", list_order_date, information["Order Date"],
                  information["Order Date"] == list_order_date),
        new_check("Order Date (= order details of the order initiator)", initiator_order_date,
                  information["Order Date"], information["Order Date"] == initiator_order_date),
    ]
    return checks, information


def check_products(page):
    # Why: the 2 products of the order must be the requisition items (each found by agreement item and master item);
    # When: order details checks before and after the approval. Returns (checks, products by item number)
    order_details_page = OrderDetails(page)
    product_rows = order_details_page.get_product_rows()
    sub_total = order_details_page.get_sub_total()
    checks = [new_check("Products", len(order["items"]), len(product_rows), len(product_rows) == len(order["items"]))]
    products, used_rows = {}, set()
    for item in order["items"]:
        number = item["number"]
        product_row, product = find_product_row(order_details_page, item, used_rows)
        checks.append(new_check(f"Item {number} product row (master item {item['master_item_code']})", "shown",
                                "shown" if product_row else "not found", bool(product_row)))
        if not product_row:
            continue
        products[f"item {number}"] = product
        total = to_amount(item["total_price"])
        checks += [
            new_check(f"Item {number} Master item", item["master_item_code"], product["Master item"],
                      product["Master item"].startswith(item["master_item_code"])),
            new_check(f"Item {number} Requisition number", order["requisition_number"], product["Requisition"],
                      product["Requisition"] == order["requisition_number"]),
            new_check(f"Item {number} FA No.", order["agreement_number"], product["FA No."],
                      product["FA No."] == order["agreement_number"]),
            new_check(f"Item {number} Specification", item["specification"], product["Specification"],
                      product["Specification"] == item["specification"]),
            new_check(f"Item {number} Remarks", item["remarks"][:60], product["Remarks"][:60],
                      same_remarks(item["remarks"], product["Remarks"])),
            new_check(f"Item {number} Attachment icon", "shown" if item["attachment"] else "not shown",
                      "shown" if product["Attachment icon"] else "not shown",
                      product["Attachment icon"] == bool(item["attachment"])),
            new_check(f"Item {number} UoM", item["uom"], product["UoM"], product["UoM"] == item["uom"]),
            new_check(f"Item {number} Quantity (requisition quantity)", item["quantity"], product["Quantity"],
                      to_amount(product["Quantity"]) == to_amount(item["quantity"])),
            new_check(f"Item {number} Unit Price", item["unit_price"], product["Unit Price"],
                      to_amount(product["Unit Price"]) == to_amount(item["unit_price"])),
            new_check(f"Item {number} Total Price (Qty. x Unit Price)", total, product["Total Price"],
                      to_amount(product["Total Price"]) == total),
        ]
    checks.append(new_check("Sub-Total (sum of the 2 items)", order_total(), sub_total,
                            to_amount(sub_total) == order_total()))
    return checks, products


def verify_order_details(page, order_status, label):
    # Why: the order details must be the order that was created (information, 2 products, Preferred Delivery
    # Schedule and Action History); When: before and after the approval. Returns the order details
    details = {}
    approved = "approved" in order_status.lower()
    with allure.step(f"Verify the order information ({label})"):
        checks, details["information"] = check_information(page, order_status)
        PendingApprovalOrders(page).get_full_page_screenshot(f'{label}_order_information')
        attach_and_assert_checks(checks, f"Order information ({label})")
    with allure.step(f"Verify the 2 products and the Sub-Total ({label})"):
        checks, details["products"] = check_products(page)
        PendingApprovalOrders(page).get_full_page_screenshot(f'{label}_order_products')
        attach_and_assert_checks(checks, f"Order products ({label})")
    with allure.step(f"Verify the Preferred Delivery Schedule ({label})"):
        checks, details["delivery_schedule"] = check_delivery_schedules(page, expected_schedules())
        attach_and_assert_checks(checks, f"Preferred Delivery Schedule ({label})")
    with allure.step(f"Store and verify the Action History and the Order Date ({label})"):
        checks, details["action_history"] = check_action_history(
            page, details["information"]["Order Date"], order_approver if approved else None)
        allure.attach(
            "\n".join(" | ".join(f"{title}: {value}" for title, value in row.items()) for row in details["action_history"]),
            name=f"Action History ({label})",
            attachment_type=allure.attachment_type.TEXT
        )
        PendingApprovalOrders(page).get_full_page_screenshot(f'{label}_action_history')
        attach_and_assert_checks(checks, f"Action History and Order Date ({label})")
    return details


def check_preview(page, order_status):
    # Why: the order document (preview PDF) must show the order: BRAC letter pad, status, Purchase Order number, the
    # 2 items, Grand Total, amount in words and the delivery schedules; When: approved order preview check.
    # Returns (checks, preview)
    order_details_page = OrderDetails(page)
    preview_tab = open_preview_tab(page, erp_user=order_approver)
    order_document = order_details_page.download_order_document(
        preview_tab, DOWNLOAD_DIR, f"order_document_{order_reference_number.replace('/', '_')}_approved.pdf")
    allure.attach.file(str(order_document), name=f"Order document - {order_document.name}")
    parameters = {key: values[0] for key, values in parse_qs(urlparse(preview_tab.url).query).items()}
    tracking_number = base64.b64decode(parameters.get("trackingNumber", "")).decode("utf-8", "ignore")
    preview_status = base64.b64decode(parameters.get("Status", "")).decode("utf-8", "ignore")
    preview = {"url": preview_tab.url, "order_document": order_document.name}
    preview_tab.close()
    page.bring_to_front()

    text = order_details_page.read_order_document_text(order_document)
    numbers = numbers_in_text(text)
    allure.attach(text, name="Order document text", attachment_type=allure.attachment_type.TEXT)
    purchase_order = re.search(r"Purchase Order:\s*(\S+)", text)
    preview["purchase_order_number"] = purchase_order.group(1) if purchase_order else ""
    preview["amount_in_words"] = amount_in_words = order_details_page.get_amount_in_words(text)
    has_paisa = order_total() % 1 != 0
    print("PURCHASE ORDER NUMBER:", preview["purchase_order_number"])

    checks = [
        new_check("Order document is a PDF", "%PDF", order_document.read_bytes()[:4].decode("latin-1"),
                  order_document.read_bytes()[:4] == b"%PDF"),
        new_check("Preview tracking number (order reference)", order_reference_number, tracking_number,
                  tracking_number == order_reference_number),
        new_check("Preview status (order status)", order_status, preview_status,
                  order_status.lower() in preview_status.lower()),
        new_check("Preview letter pad (BRAC)", "1", parameters.get("letterPad", "-"), parameters.get("letterPad") == "1"),
        new_check("Purchase Order number", "shown", preview["purchase_order_number"] or "not found",
                  bool(preview["purchase_order_number"])),
        new_check("Amount in words (TAKA, PAISA when the total has paisa, ONLY)",
                  "... TAKA AND ... PAISA ONLY" if has_paisa else "... TAKA ONLY", amount_in_words or "not found",
                  "TAKA" in amount_in_words and ("PAISA" in amount_in_words) == has_paisa
                  and amount_in_words.endswith("ONLY")),
    ]
    expected_texts = [("Letter pad", "BRAC"), ("Order status", order_status),
                      ("Requisition number", order["requisition_number"]), ("FA No.", order["agreement_number"]),
                      ("Attachment", "Downloadable from the system"),
                      ("Delivery place (requisition delivery address)", order["delivery_address"]),
                      ("Receiver", order_initiator)]
    expected_numbers = [("Grand Total (sum of the 2 items)", order_total())]
    for item in order["items"]:
        number = item["number"]
        expected_texts += [(f"Item {number} Master item", item["master_item_code"]),
                           (f"Item {number} Agreement item", item["item_code"]),
                           (f"Item {number} Specification", item["specification"]),
                           (f"Item {number} Remarks", item["remarks"]),
                           (f"Item {number} UoM", item["uom"])]
        expected_numbers += [(f"Item {number} Quantity / schedule quantity", to_amount(item["quantity"])),
                             (f"Item {number} Unit Price", to_amount(item["unit_price"])),
                             (f"Item {number} Total Price (Qty. x Unit Price)", to_amount(item["total_price"]))]
    for check, value in expected_texts:
        found = without_spaces(value).lower() in without_spaces(text).lower()
        checks.append(new_check(check, value[:60], "on the preview" if found else "not found", found))
    for check, value in expected_numbers:
        checks.append(new_check(check, value, "on the preview" if value in numbers else "not found", value in numbers))
    return checks, preview


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Orders")
@allure.title("Test_case_1: Verify order in pending approval list")
@allure.description("Test case 1: Search the marketplace order of the 2 items (same agreement item, different "
                    "master items) once in the order approver's Pending Approval Orders list and store its Order Date "
                    "and Order Total.")
@pytest.mark.order(1)
def test_1_verify_order_in_pending_approval_list(page):
    """
    Test case 1: Verify the order in the approver's Pending Approval Orders list
    (same as marketplace_staging_sanity.py Test case 13).

    Steps:
        1. Load the order of same_agreement_item_and_different_master_items_order.py
           (same_agreement_item_and_different_master_items_order_result.json) and store it in 'order'.
        2. Log in to the Digital Marketplace as the order approver ('order_approver').
        3. Go to Orders > Pending Approval Orders.
        4. Get the pending approval order count ('pending_approval_order_count').
        5. Search the order reference number once, verify the order is in the list, click the arrow icon and
           store the Order Date ('list_order_date') and Order Total ('list_order_total').
        No logout: Test case 2 opens the order details from this search result.

    All scenario values are read from .env.
    """
    global order, order_reference_number, order_approver, pending_approval_order_count, \
        order_found_in_pending_list, list_order_date, list_order_total

    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_order_initiator": order_initiator,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    login_page = LoginPage(page)
    home_page = HomePage(page)
    pending_approval_orders = PendingApprovalOrders(page)

    # Step 1: Order from same_agreement_item_and_different_master_items_order.py
    with allure.step("Step 1: Load the order result of same_agreement_item_and_different_master_items_order.py"):
        order = load_result("same_agreement_item_and_different_master_items_order_result",
                            created_by="same_agreement_item_and_different_master_items_order.py")
        missing_order_values = [key for key in ("order_remarks", "delivery_address", "order_details_information",
                                                "order_details_delivery_schedule") if key not in order]
        missing_order_values += [key for key in ("master_item_code", "specification", "uom")
                                 if order.get("items") and key not in order["items"][0]]
        assert not missing_order_values, \
            f"Run same_agreement_item_and_different_master_items_order.py first (order result has no {', '.join(missing_order_values)})"
        order_reference_number = order["order_reference_number"]
        order_approver = order["order_approver"]
        print("ORDER REFERENCE NUMBER:", order_reference_number)
        print("ORDER APPROVER:", order_approver)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in order.items()),
            name="Order result",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 2: Log in as the order approver
    with allure.step(f"Step 2: Log in to the Digital Marketplace as order approver {order_approver}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=order_approver, pass_word=marketplace_password)
        print(f"Logging in to the Digital Marketplace as: {order_approver}")
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('order_approver_login')

    # Step 3: Orders > Pending Approval Orders
    with allure.step("Step 3: Go to Orders > Pending Approval Orders"):
        home_page.goto_order_list()
        home_page.goto_pending_approval_orders_list()
        home_page.get_full_page_screenshot('pending_approval_orders')

    # Step 4: Pending approval order count
    with allure.step("Step 4: Get pending approval order count"):
        pending_approval_order_count = pending_approval_orders.get_pending_approval_order_count(
            pending_approval_order_count=pending_approval_order_count)
        print("PENDING APPROVAL ORDER COUNT:", pending_approval_order_count)
        allure.attach(
            f"Order approver: {order_approver}\nPending approval orders: {pending_approval_order_count}",
            name="Pending approval orders count",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 5: Search the order once, verify it is in the list and store its Order Date and Order Total
    with allure.step(f"Step 5: Search order {order_reference_number} once and store Order Date and Order Total"):
        pending_approval_orders.search_order_input(reference_number=order_reference_number)
        pending_approval_orders.click_order_search_button()
        pending_approval_orders.verify_order_in_list(reference_number=order_reference_number)
        order_found_in_pending_list = True
        order_summary = pending_approval_orders.get_order_summary_from_list()
        list_order_date = order_summary["order_date"]
        list_order_total = order_summary["order_total"]
        print("LIST ORDER DATE:", list_order_date)
        print("LIST ORDER TOTAL:", list_order_total)
        allure.attach(
            f"Order {order_reference_number} found in the pending approval list of {order_approver}\n"
            f"Order Date: {list_order_date}\nOrder Total: {list_order_total}",
            name="Pending approval list order info",
            attachment_type=allure.attachment_type.TEXT
        )
        pending_approval_orders.get_full_page_screenshot('pending_approval_order_info')


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Details")
@allure.title("Test_case_2: Open pending approval order details")
@allure.description("Test case 2: Open the order details from the search result of Test case 1 (no new search) and "
                    "verify the order information, the 2 products, Preferred Delivery Schedule and Action History "
                    "before the approval.")
@pytest.mark.order(2)
def test_2_open_pending_approval_order_details(page):
    """
    Test case 2: Pending approval order details. Continues from the search result of Test case 1 (no new search).

    Steps:
        1. Open the order details from the pending approval list.
        2. Order information (Submitted for Approval; Order Date and Order Total = pending approval list; Order
           Date = the Order Date of the order initiator's order details), the 2 products (each found by master item:
           master item, requisition, FA, specification, remarks, attachment icon, UoM, quantity, prices) and the Sub-Total,
           Preferred Delivery Schedule (2 auto generated schedules), Action History and Order Date (= the date the
           order was submitted).
    """
    global details_before_approval
    assert order_found_in_pending_list, "Test case 1 must pass first: order not found in the pending approval list"
    pending_approval_orders = PendingApprovalOrders(page)

    # Step 1: Open the order details from the search result of Test case 1
    with allure.step(f"Step 1: Open order details of {order_reference_number}"):
        pending_approval_orders.goto_pending_approval_order_details()
        pending_approval_orders.get_full_page_screenshot('pending_approval_order_details')

    # Step 2: Order details before the approval
    with allure.step("Step 2: Verify the order details before the approval"):
        details_before_approval = verify_order_details(page, order["order_status"], 'before_approval')


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Details Links")
@allure.title("Test_case_3: Verify pending approval order details links")
@allure.description("Test case 3: In page order, download the agreement attachment (agreement number first), open "
                    "the requisition details (ERP), then for every product from the top the FA link, product details "
                    "page and item attachment, and the Preferred Delivery Schedule product and requisition links.")
@pytest.mark.order(3)
def test_3_verify_pending_approval_order_details_links(page):
    """
    Test case 3: Pending approval order details links. Continues on the order details page of Test case 2.

    Steps:
        1-3. Agreement attachment download (the agreement number of the order information first), requisition
             details (ERP; the ERP login is done as the order approver with the ResetHub link when it is shown; all
             opened tabs closed), then every product from the top: FA link, product details page and item
             attachment (the requisition attachment of that item, same file type).
        4. Preferred Delivery Schedule product links (2, top link first): the product details page of the agreement item.
        5. Preferred Delivery Schedule requisition link "(Req: ...)": ERP requisition details (all opened tabs closed).

    All scenario values are read from .env.
    """
    global order_details_links
    assert details_before_approval, "Test case 2 must pass first: order details are not verified"
    order_details_page = OrderDetails(page)

    # Step 1-3: Order details links and item attachments in page order
    with allure.step("Step 1-3: Download the agreement attachment, open the requisition details, then each product's "
                     "FA link, product details and item attachment"):
        link_checks, order_details_links = check_order_details_all_products_links(
            page, order["requisition_number"], [order["agreement_number"]],
            [{"item_code": item["item_code"], "master_item_code": item["master_item_code"],
              "attachment_name": item["attachment"]} for item in order["items"]],
            'pending_approval_order_details', DOWNLOAD_DIR, erp_user=order_approver)
        attach_and_assert_checks(link_checks, "Pending approval order details links and item attachments")

    # Step 4: Preferred Delivery Schedule product links (top link first)
    with allure.step("Step 4: Open the 2 Preferred Delivery Schedule product links (product details pages)"):
        checks = []
        schedule_item_urls = []
        item_codes_not_opened = [item["item_code"] for item in order["items"]]
        for index in range(len(order["items"])):
            schedule_item_tab = order_details_page.open_delivery_schedule_product_link_by_index(index)
            schedule_item_urls.append(schedule_item_tab.url)
            HomePage(schedule_item_tab).get_full_page_screenshot(f'pending_approval_schedule_product_{index + 1}_page')
            order_details_page.close_opened_tabs([schedule_item_tab])
            opened_code = next((code for code in item_codes_not_opened
                                if code.lower() in schedule_item_urls[-1].lower()), "")
            checks.append(new_check(f"Preferred Delivery Schedule product link {index + 1}", "a page of an order item",
                                    schedule_item_urls[-1], bool(opened_code)))
            if opened_code:
                item_codes_not_opened.remove(opened_code)
        checks.append(new_check("Preferred Delivery Schedule product links of all items", "none missing",
                                ", ".join(item_codes_not_opened) or "none missing", not item_codes_not_opened))
        order_details_links["Delivery schedule product pages"] = schedule_item_urls
        attach_and_assert_checks(checks, "Pending approval Preferred Delivery Schedule product links")

    # Step 5: Preferred Delivery Schedule requisition link
    with allure.step(f"Step 5: Open the Preferred Delivery Schedule requisition link {order['requisition_number']} (ERP)"):
        schedule_requisition, opened_tabs = read_requisition_from_link(
            page, lambda: order_details_page.open_link_all_tabs(
                order_details_page.delivery_schedule_requisition_link(order["requisition_number"])),
            'pending_approval_schedule_erp_requisition', erp_user=order_approver)
        order_details_links["Delivery schedule requisition"] = schedule_requisition["req_no"]
        checks = [
            new_check("Preferred Delivery Schedule requisition link (ERP REQ. No)", order["requisition_number"],
                      schedule_requisition["req_no"], schedule_requisition["req_no"] == order["requisition_number"]),
            new_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1),
        ]
        PendingApprovalOrders(page).get_full_page_screenshot('pending_approval_order_links_checked')
        attach_and_assert_checks(checks, "Pending approval Preferred Delivery Schedule requisition link")


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Delivery Schedule")
@allure.title("Test_case_4: Verify the delivery schedule is the schedule of the order")
@allure.description("Test case 4: The Preferred Delivery Schedule of the pending approval order is the delivery "
                    "schedule created with the order (same_agreement_item_and_different_master_items_order.py).")
@pytest.mark.order(4)
def test_4_verify_delivery_schedule_of_the_order(page):
    """
    Test case 4: Preferred Delivery Schedule = the schedule created with the order. Continues on the order details.

    Steps:
        1. Every Preferred Delivery Schedule row (Quantity, Delivery Date, Location, receiving person) is the same as
           the row saved by the order test file (2 auto generated schedules).
    """
    global delivery_schedule
    assert order_details_links, "Test case 3 must pass first: order details links are not verified"

    # Step 1: Delivery schedule of the approver = delivery schedule of the order
    with allure.step("Step 1: Compare the Preferred Delivery Schedule with the schedule created with the order"):
        delivery_schedule = details_before_approval["delivery_schedule"]
        order_schedule = order["order_details_delivery_schedule"]
        checks = [new_check("Delivery schedules", len(order_schedule), len(delivery_schedule),
                            len(delivery_schedule) == len(order_schedule))]
        used_rows = []
        for number, order_row in enumerate(order_schedule, start=1):
            # The schedule rows can be in another order: the approver's row with the same quantity (each row once)
            approver_row = next((row for row in delivery_schedule if row not in used_rows
                                 and to_amount(row.get("Quantity", "0")) == to_amount(order_row.get("Quantity", "0"))), {})
            if approver_row:
                used_rows.append(approver_row)
            for column in ("Quantity", "Delivery Date", "Location"):
                checks.append(new_check(f"Schedule {number} {column}", order_row.get(column, "-"),
                                        approver_row.get(column, "-"),
                                        without_spaces(order_row.get(column)) == without_spaces(approver_row.get(column))))
            # Receiving person: "Receiver Info" (order initiator) = "Delivery Info" (order approver)
            checks.append(new_check(f"Schedule {number} receiving person", receiver_of(order_row) or "-",
                                    receiver_of(approver_row) or "-",
                                    without_spaces(receiver_of(order_row)) == without_spaces(receiver_of(approver_row))))
        PendingApprovalOrders(page).get_full_page_screenshot('pending_approval_delivery_schedule')
        attach_and_assert_checks(checks, "Preferred Delivery Schedule = schedule of the order")


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Order Approval")
@allure.title("Test_case_5: Approve marketplace order")
@allure.description("Test case 5: Approve the order and verify the approval confirmation message and the order "
                    "status (an email failure message is an email configuration note, not a failure).")
@pytest.mark.order(5)
def test_5_approve_marketplace_order(page):
    """
    Test case 5: Approve the order. Continues on the order details page of Test case 4 (order approver).

    Steps:
        1. Approve the order; store the order status ('approved_order_status') and the approval confirmation
           message ('approval_confirmation_message'). The message must say the order is approved;
           "Email sent failed due to null address" (approver without email address) is noted as an email
           configuration issue, not a failure.
    """
    global approved_order_status, approval_confirmation_message
    assert delivery_schedule, "Test case 4 must pass first: delivery schedule is not verified"
    pending_approval_orders = PendingApprovalOrders(page)

    # Step 1: Approve the order, store the status and the approval confirmation message
    with allure.step(f"Step 1: Approve order {order_reference_number}"):
        approved_order_status, page_messages = pending_approval_orders.approve_order_with_result()
        approval_confirmation_message = "; ".join(page_messages)
        print("APPROVED ORDER STATUS:", approved_order_status)
        print("APPROVAL CONFIRMATION MESSAGE:", approval_confirmation_message)
        pending_approval_orders.get_full_page_screenshot('order_approved')
        if EMAIL_NOT_SENT_MESSAGE.lower() in approval_confirmation_message.lower():
            allure.attach(f"{approval_confirmation_message}\nEmail configuration issue: the order approver has no email "
                          f"address, so the approval email is not sent. The order approval itself is done.",
                          name="Email configuration note", attachment_type=allure.attachment_type.TEXT)
        checks = [
            new_check("Approval confirmation message", "Order Approved", approval_confirmation_message or "-",
                      "order approved" in approval_confirmation_message.lower()),
            new_check("Order status", "Order Approved", approved_order_status,
                      "approved" in approved_order_status.lower()),
        ]
        attach_and_assert_checks(checks, "Order approval")


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Approved Order Details")
@allure.title("Test_case_6: Verify approved order details")
@allure.description("Test case 6: After the approval, verify the order status, Order Date, order information, the 2 "
                    "products, Preferred Delivery Schedule and Action History (submitted and approved).")
@pytest.mark.order(6)
def test_6_verify_approved_order_details(page):
    """
    Test case 6: Approved order details. Continues on the order details page of Test case 5.

    Steps:
        1. Order information (Order Approved; Order Date and Order Total = pending approval list; Order Date = the
           Order Date of the order initiator's order details), the 2 products and the Sub-Total, Preferred Delivery
           Schedule, Action History (submitted by the requisition initiator, approved by the order approver) and
           Order Date (= the date the order was submitted).
        2. Action History after the approval (stored): the approval row is User Type "Requisition Approver",
           Order Status "Order Approved", Action Taken By the order approver and the approval time.
    """
    global details_after_approval
    assert "approved" in approved_order_status.lower(), "Test case 5 must pass first: order is not approved"

    # Step 1: Order details after the approval
    with allure.step("Step 1: Verify the order details after the approval"):
        details_after_approval = verify_order_details(page, approved_order_status, 'after_approval')

    # Step 2: Action History after the approval: the approval row of the order approver (stored)
    with allure.step("Step 2: Verify the approval row of the Action History"):
        approval_rows = [row for row in details_after_approval["action_history"]
                         if order_approver in row.get("Action Taken By", "")]
        approval_row = approval_rows[-1] if approval_rows else {}
        details_after_approval["approval_action"] = approval_row
        print("APPROVAL ACTION HISTORY:", approval_row)
        allure.attach(" | ".join(f"{title}: {value}" for title, value in approval_row.items()) or "not found",
                      name="Action History - approval row", attachment_type=allure.attachment_type.TEXT)
        checks = [
            new_check("Approval row - User Type", "Requisition Approver", approval_row.get("User Type", "-"),
                      approval_row.get("User Type") == "Requisition Approver"),
            new_check("Approval row - Order Status", "Order Approved", approval_row.get("Order Status", "-"),
                      approval_row.get("Order Status") == "Order Approved"),
            new_check("Approval row - Action Taken By (order approver)", order_approver,
                      approval_row.get("Action Taken By", "-"), bool(approval_row)),
            new_check("Approval row - Time (approval date)", "shown", approval_row.get("Time", "-"),
                      bool(approval_row.get("Time"))),
        ]
        PendingApprovalOrders(page).get_full_page_screenshot('after_approval_action_history')
        attach_and_assert_checks(checks, "Action History after the approval")


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Approved Order Preview")
@allure.title("Test_case_7: Verify approved order preview and save the order approval result")
@allure.description("Test case 7: Click Preview, download the order document and verify it (BRAC letter pad, approved "
                    "status, Purchase Order number, the 2 items, Grand Total, amount in words, delivery date and "
                    "place), then log out and save the order approval result.")
@pytest.mark.order(7)
def test_7_verify_approved_order_preview(page):
    """
    Test case 7: Approved order preview. Continues on the order details page of Test case 6.

    Steps:
        1. Click Preview (ERP; log in as the order approver with the ResetHub link when the ERP login page is
           shown): download the order document and verify the preview address (order reference, approved status,
           BRAC letter pad), the Purchase Order number, the 2 items (master item, agreement item, specification,
           remarks, UoM, quantity, prices), Grand Total, amount in words and the delivery schedules.
        2. Log out from the Digital Marketplace.
        3. Save the order approval result (same_agreement_item_and_different_master_items_order_approval_result.json).
    """
    global order_preview, order_approval_result
    assert details_after_approval, "Test case 6 must pass first: approved order details are not verified"
    pending_approval_orders = PendingApprovalOrders(page)

    # Step 1: Preview and order document
    with allure.step("Step 1: Click Preview, download the order document and verify it"):
        checks, order_preview = check_preview(page, approved_order_status)
        attach_and_assert_checks(checks, "Approved order preview")

    # Step 2: Log out from the Digital Marketplace
    with allure.step("Step 2: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        pending_approval_orders.get_full_page_screenshot('order_approver_logout')

    # Step 3: Save the order approval result for the next test file
    with allure.step("Step 3: Save the order approval result"):
        order_approval_result = {
            **order,
            "order_status": approved_order_status,
            "approval_confirmation_message": approval_confirmation_message,
            "order_date": list_order_date,
            "order_total": list_order_total,
            "details_before_approval": details_before_approval,
            "order_details_links": order_details_links,
            "details_after_approval": details_after_approval,
            "order_preview": order_preview,
        }
        save_result("same_agreement_item_and_different_master_items_order_approval_result", order_approval_result)
        print("ORDER APPROVAL RESULT:", order_approval_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in order_approval_result.items()),
            name="Saved order approval result",
            attachment_type=allure.attachment_type.TEXT
        )
