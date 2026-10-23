from dotenv import load_dotenv
import os
from pathlib import Path

import pytest
import allure

load_dotenv()

# Digital Marketplace (staging)
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
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
from brac_digital_marketplace.testcases.order_creation.order_page_links import check_order_details_page_links, \
    read_requisition_from_link, requisition_product_name_checks
from brac_digital_marketplace.testcases.order_creation.order_details_checks import check_order_information, \
    check_delivery_schedules, check_action_history, check_order_preview, to_amount, new_check, without_spaces, \
    receiver_of

# Orders of different_vendor_agreement_items_order.py (different_vendor_agreement_items_order_result.json):
# one order per vendor of the same requisition (order 1: cart remarks empty, attachment removed, Auto Generate
# schedule; order 2: cart remarks, new attachment and quantity, 2 manual schedules). Both orders are approved by the
# same order approver, one after the other.
order_result = {}
order_approver = ''
# Approval of each order: {1: {...}, 2: {...}} (pending list info, details before/after approval, links, approval,
# preview)
approvals = {1: {}, 2: {}}
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


def order_of(number):
    # Why: the saved values of order <number> (vendor 1 or 2); When: every test of that order. An order of an item
    # removed from the shopping cart (quantity 0) does not exist: its tests are skipped
    assert order_result, "Test case 1 must pass first: the order result is not loaded"
    order = order_result["orders"][number - 1]
    if order["removed_from_cart"]:
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    return order


def expected_order(number, order_status):
    # Why: the values the order details and the order document must show (saved by the order test file);
    # When: order information and preview checks of order <number> before and after the approval
    order = order_of(number)
    return {
        "order_reference_number": order["order_reference_number"], "requisition_number": order_result["requisition_number"],
        "agreement_number": order["agreement_number"], "order_status": order_status,
        "order_remarks": order_result["order_remarks"], "vendor": order["vendor"],
        "master_item_code": order["master_item_code"], "item_code": order["item_code"],
        "specification": order["specification"], "remarks": order["cart_remarks_entered"], "uom": order["uom"],
        "quantity": order["cart_quantity"], "unit_price": order["unit_price"], "schedules": order["expected_schedules"],
        "has_attachment": bool(order["cart_attachment"]),
    }


def check_product_of(page, number):
    # Why: the product of order <number> is the item of that vendor with its cart values (order 1: empty cart remarks
    # shown blank or N/A and the attachment removed -> no attachment icon); When: order details checks.
    # Returns (checks, product)
    order = order_of(number)
    order_details_page = OrderDetails(page)
    product_rows = order_details_page.get_product_rows()
    product = order_details_page.read_product_row(product_rows[0])
    product["Sub-Total"] = order_details_page.get_sub_total()
    total = to_amount(order["total_price"])
    remarks_ok = same_remarks(order["cart_remarks_entered"], product["Remarks"]) or \
        (not order["cart_remarks_entered"] and not product["Remarks"].strip())
    checks = [
        new_check("Products (one item of this vendor)", 1, len(product_rows), len(product_rows) == 1),
        new_check("Master item", order["master_item_code"], product["Master item"],
                  product["Master item"].startswith(order["master_item_code"])),
        new_check("Requisition number", order_result["requisition_number"], product["Requisition"],
                  product["Requisition"] == order_result["requisition_number"]),
        new_check("FA No.", order["agreement_number"], product["FA No."], product["FA No."] == order["agreement_number"]),
        new_check("Agreement item", order["item_code"], product["Agreement item"],
                  order["item_code"] in product["Agreement item"]),
        new_check("Specification", order["specification"], product["Specification"],
                  product["Specification"] == order["specification"]),
        new_check("Remarks (cart remarks; empty -> blank or N/A)", order["cart_remarks_entered"][:60] or "blank or N/A",
                  product["Remarks"][:60] or "(blank)", remarks_ok),
        new_check("Attachment icon", "shown" if order["cart_attachment"] else "not shown (removed in the cart)",
                  "shown" if product["Attachment icon"] else "not shown",
                  product["Attachment icon"] == bool(order["cart_attachment"])),
        new_check("UoM", order["uom"], product["UoM"], product["UoM"] == order["uom"]),
        new_check("Quantity (cart quantity)", order["cart_quantity"], product["Quantity"],
                  to_amount(product["Quantity"]) == to_amount(order["cart_quantity"])),
        new_check("Unit Price", order["unit_price"], product["Unit Price"],
                  to_amount(product["Unit Price"]) == to_amount(order["unit_price"])),
        new_check("Total Price (Qty. x Unit Price)", total, product["Total Price"], to_amount(product["Total Price"]) == total),
        new_check("Sub-Total", total, product["Sub-Total"], to_amount(product["Sub-Total"]) == total),
    ]
    return checks, product


def verify_order_details(page, number, order_status, label):
    # Why: the order details of order <number> must be the order that was created (information, product, Preferred
    # Delivery Schedule and Action History); When: before and after the approval. Returns the order details
    order = order_of(number)
    approval = approvals[number]
    details = {}
    approved = "approved" in order_status.lower()
    with allure.step(f"Verify the order information ({label})"):
        checks, details["information"] = check_order_information(page, expected_order(number, order_status))
        initiator_order_date = order["order_details_information"]["Order Date"]
        checks += [
            new_check("Order Date (details = pending approval list)", approval["list_order_date"],
                      details["information"]["Order Date"], details["information"]["Order Date"] == approval["list_order_date"]),
            new_check("Order Date (= order details of the order initiator)", initiator_order_date,
                      details["information"]["Order Date"], details["information"]["Order Date"] == initiator_order_date),
            new_check("Order Total (details = pending approval list)", approval["list_order_total"],
                      details["information"]["Order Total"],
                      to_amount(details["information"]["Order Total"]) == to_amount(approval["list_order_total"])),
        ]
        PendingApprovalOrders(page).get_full_page_screenshot(f'order_{number}_{label}_order_information')
        attach_and_assert_checks(checks, f"Order {number} information ({label})")
    with allure.step(f"Verify the product and the Sub-Total ({label})"):
        checks, details["product"] = check_product_of(page, number)
        attach_and_assert_checks(checks, f"Order {number} product ({label})")
    with allure.step(f"Verify the Preferred Delivery Schedule ({label})"):
        checks, details["delivery_schedule"] = check_delivery_schedules(page, order["expected_schedules"])
        attach_and_assert_checks(checks, f"Order {number} Preferred Delivery Schedule ({label})")
    with allure.step(f"Store and verify the Action History and the Order Date ({label})"):
        checks, details["action_history"] = check_action_history(
            page, details["information"]["Order Date"], order_approver if approved else None)
        allure.attach(
            "\n".join(" | ".join(f"{title}: {value}" for title, value in row.items()) for row in details["action_history"]),
            name=f"Order {number} Action History ({label})",
            attachment_type=allure.attachment_type.TEXT
        )
        PendingApprovalOrders(page).get_full_page_screenshot(f'order_{number}_{label}_action_history')
        attach_and_assert_checks(checks, f"Order {number} Action History and Order Date ({label})")
    return details


def find_order_in_pending_list(page, number):
    # Why: each order is searched once in the order approver's Pending Approval Orders list; When: the first test of
    # order <number> (Order Date and Order Total of the list are stored)
    order = order_of(number)
    approval = approvals[number]
    home_page = HomePage(page)
    pending_approval_orders = PendingApprovalOrders(page)
    reference = order["order_reference_number"]

    with allure.step(f"Go to Orders > Pending Approval Orders and get the pending approval order count"):
        home_page.goto_order_list()
        home_page.goto_pending_approval_orders_list()
        approval["pending_approval_order_count"] = pending_approval_orders.get_pending_approval_order_count(
            pending_approval_order_count='')
        print(f"PENDING APPROVAL ORDER COUNT (order {number}):", approval["pending_approval_order_count"])
        home_page.get_full_page_screenshot(f'order_{number}_pending_approval_orders')

    with allure.step(f"Search order {number} ({reference}) once and store Order Date and Order Total"):
        pending_approval_orders.search_order_input(reference_number=reference)
        pending_approval_orders.click_order_search_button()
        pending_approval_orders.verify_order_in_list(reference_number=reference)
        order_summary = pending_approval_orders.get_order_summary_from_list()
        approval["list_order_date"] = order_summary["order_date"]
        approval["list_order_total"] = order_summary["order_total"]
        approval["found_in_pending_list"] = True
        print(f"ORDER {number} LIST ORDER DATE / TOTAL:", approval["list_order_date"], approval["list_order_total"])
        allure.attach(
            f"Order {reference} ({order['vendor']}) found in the pending approval list of {order_approver}\n"
            f"Order Date: {approval['list_order_date']}\nOrder Total: {approval['list_order_total']}",
            name=f"Order {number} pending approval list info",
            attachment_type=allure.attachment_type.TEXT
        )
        pending_approval_orders.get_full_page_screenshot(f'order_{number}_pending_approval_order_info')


def open_details_before_approval(page, number):
    # Why: the pending approval order details must be the created order before the approval; When: the second test
    # of order <number> (opened from the search result, no new search)
    order_of(number)
    approval = approvals[number]
    assert approval.get("found_in_pending_list"), f"Order {number} is not found in the pending approval list"
    pending_approval_orders = PendingApprovalOrders(page)
    with allure.step(f"Step 1: Open the order details of order {number}"):
        pending_approval_orders.goto_pending_approval_order_details()
        pending_approval_orders.get_full_page_screenshot(f'order_{number}_pending_approval_order_details')
    with allure.step("Step 2: Verify the order details before the approval"):
        approval["details_before_approval"] = verify_order_details(page, number, order_of(number)["order_status"],
                                                                   'before_approval')


def verify_details_links(page, number):
    # Why: the pending approval order details of order <number> must link (in page order) to the agreement
    # attachment, requisition (ERP), product page, item attachment and the Preferred Delivery Schedule product and
    # requisition; When: the links test of order <number>
    order = order_of(number)
    approval = approvals[number]
    assert approval.get("details_before_approval"), f"Order {number}: order details are not verified"
    requisition_number = order_result["requisition_number"]

    with allure.step("Step 1-3: Download the agreement attachment, open the requisition details and product details, "
                     "download the item attachment (no attachment icon when it was removed in the cart)"):
        link_checks, links = check_order_details_page_links(
            page, requisition_number, order["agreement_number"], order["item_code"], order["cart_attachment"],
            f'order_{number}_pending_approval_order_details', DOWNLOAD_DIR, erp_user=order_approver,
            requisition_product_name=order["requisition_product_name"])
        attach_and_assert_checks(link_checks, f"Order {number} pending approval order details links and item attachment")

    with allure.step("Step 4: Verify the Preferred Delivery Schedule product name and open the requisition link"):
        order_details_page = OrderDetails(page)
        schedule_requisition, opened_tabs = read_requisition_from_link(
            page, lambda: order_details_page.open_link_all_tabs(
                order_details_page.delivery_schedule_requisition_link(requisition_number)),
            f'order_{number}_pending_approval_schedule_erp_requisition', erp_user=order_approver)
        links["Delivery schedule requisition"] = schedule_requisition["req_no"]
        approval["order_details_links"] = links
        checks = requisition_product_name_checks(page.locator("body"), order["requisition_product_name"],
                                                 "Preferred Delivery Schedule")
        checks += [
            new_check("Preferred Delivery Schedule requisition link (ERP REQ. No)", requisition_number,
                      schedule_requisition["req_no"], schedule_requisition["req_no"] == requisition_number),
            new_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1),
        ]
        PendingApprovalOrders(page).get_full_page_screenshot(f'order_{number}_pending_approval_order_links_checked')
        attach_and_assert_checks(checks, f"Order {number} pending approval Preferred Delivery Schedule links")


def verify_schedule_is_order_schedule(page, number):
    # Why: the Preferred Delivery Schedule the approver sees must be the schedule created with order <number>;
    # When: the delivery schedule test of order <number>
    order = order_of(number)
    approval = approvals[number]
    assert approval.get("order_details_links"), f"Order {number}: order details links are not verified"
    with allure.step("Step 1: Compare the Preferred Delivery Schedule with the schedule created with the order"):
        delivery_schedule = approval["details_before_approval"]["delivery_schedule"]
        order_schedule = order["order_details_delivery_schedule"]
        checks = [new_check("Delivery schedules", len(order_schedule), len(delivery_schedule),
                            len(delivery_schedule) == len(order_schedule))]
        for schedule_number, order_row in enumerate(order_schedule, start=1):
            # The schedule rows can be in another order: the approver's row with the same quantity
            approver_row = next((row for row in delivery_schedule
                                 if to_amount(row.get("Quantity", "0")) == to_amount(order_row.get("Quantity", "0"))), {})
            for column in ("Quantity", "Delivery Date", "Location"):
                checks.append(new_check(f"Schedule {schedule_number} {column}", order_row.get(column, "-"),
                                        approver_row.get(column, "-"),
                                        without_spaces(order_row.get(column)) == without_spaces(approver_row.get(column))))
            # Receiving person: "Receiver Info" (order initiator) = "Delivery Info" (order approver)
            checks.append(new_check(f"Schedule {schedule_number} receiving person", receiver_of(order_row) or "-",
                                    receiver_of(approver_row) or "-",
                                    without_spaces(receiver_of(order_row)) == without_spaces(receiver_of(approver_row))))
        approval["delivery_schedule"] = delivery_schedule
        PendingApprovalOrders(page).get_full_page_screenshot(f'order_{number}_pending_approval_delivery_schedule')
        attach_and_assert_checks(checks, f"Order {number} Preferred Delivery Schedule = schedule of the order")


def approve_order(page, number):
    # Why: the order approver approves order <number>; an email failure message (approver without email address) is
    # an email configuration note, not a failure; When: the approval test of order <number>
    order = order_of(number)
    approval = approvals[number]
    assert approval.get("delivery_schedule"), f"Order {number}: delivery schedule is not verified"
    pending_approval_orders = PendingApprovalOrders(page)
    with allure.step(f"Step 1: Approve order {number} ({order['order_reference_number']})"):
        approval["approved_order_status"], page_messages = pending_approval_orders.approve_order_with_result()
        approval["approval_confirmation_message"] = message = "; ".join(page_messages)
        print(f"ORDER {number} APPROVED ORDER STATUS:", approval["approved_order_status"])
        print(f"ORDER {number} APPROVAL CONFIRMATION MESSAGE:", message)
        pending_approval_orders.get_full_page_screenshot(f'order_{number}_approved')
        if EMAIL_NOT_SENT_MESSAGE.lower() in message.lower():
            allure.attach(f"{message}\nEmail configuration issue: the order approver has no email address, so the "
                          f"approval email is not sent. The order approval itself is done.",
                          name=f"Order {number} email configuration note", attachment_type=allure.attachment_type.TEXT)
        checks = [
            new_check("Approval confirmation message", "Order Approved", message or "-",
                      "order approved" in message.lower()),
            new_check("Order status", "Order Approved", approval["approved_order_status"],
                      "approved" in approval["approved_order_status"].lower()),
        ]
        attach_and_assert_checks(checks, f"Order {number} approval")


def verify_approved_details(page, number):
    # Why: after the approval, order <number> details must show the approved order and the approval row of the
    # Action History; When: the approved order details test of order <number>
    order_of(number)
    approval = approvals[number]
    approved_status = approval.get("approved_order_status", "")
    assert "approved" in approved_status.lower(), f"Order {number} is not approved"
    with allure.step("Step 1: Verify the order details after the approval"):
        approval["details_after_approval"] = details = verify_order_details(page, number, approved_status,
                                                                            'after_approval')
    with allure.step("Step 2: Verify the approval row of the Action History"):
        approval_rows = [row for row in details["action_history"] if order_approver in row.get("Action Taken By", "")]
        approval_row = approval_rows[-1] if approval_rows else {}
        details["approval_action"] = approval_row
        print(f"ORDER {number} APPROVAL ACTION HISTORY:", approval_row)
        allure.attach(" | ".join(f"{title}: {value}" for title, value in approval_row.items()) or "not found",
                      name=f"Order {number} Action History - approval row", attachment_type=allure.attachment_type.TEXT)
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
        PendingApprovalOrders(page).get_full_page_screenshot(f'order_{number}_after_approval_action_history')
        attach_and_assert_checks(checks, f"Order {number} Action History after the approval")


def verify_approved_preview(page, number):
    # Why: the order document of approved order <number> must show the approved order; When: the preview test of
    # order <number> (the order approval result is saved after it)
    order_of(number)
    approval = approvals[number]
    assert approval.get("details_after_approval"), f"Order {number}: approved order details are not verified"
    with allure.step(f"Step 1: Click Preview, download the order document of order {number} and verify it"):
        checks, approval["order_preview"] = check_order_preview(
            page, expected_order(number, approval["approved_order_status"]), DOWNLOAD_DIR, erp_user=order_approver)
        attach_and_assert_checks(checks, f"Order {number} approved order preview")
    with allure.step("Step 2: Save the order approval result"):
        save_approval_result()


def save_approval_result():
    # Why: the approval of both orders for the next test file; When: after the preview of each order
    global order_approval_result
    order_approval_result = {
        **order_result,
        "orders": [{**order, "approval": approvals[number]}
                   for number, order in enumerate(order_result["orders"], start=1)],
    }
    save_result("different_vendor_agreement_items_order_approval_result", order_approval_result)
    allure.attach(
        "\n".join(f"Order {number}: {order['order_reference_number'] or '-'} | {order['vendor']} | "
                  f"{approvals[number].get('approved_order_status', 'not approved')}"
                  for number, order in enumerate(order_result["orders"], start=1)),
        name="Saved order approval result",
        attachment_type=allure.attachment_type.TEXT
    )


# ---------------- Order 1 (vendor of item 1) ----------------

@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Orders")
@allure.title("Test_case_1: Order 1 - verify order in pending approval list")
@allure.description("Test case 1: Load both orders of the different vendor requisition, log in as the order approver "
                    "and search order 1 (vendor of item 1) once in the Pending Approval Orders list.")
@pytest.mark.order(1)
def test_1_order_1_verify_order_in_pending_approval_list(page):
    """
    Test case 1: Order 1 in the approver's Pending Approval Orders list.

    Steps:
        1. Load the orders of different_vendor_agreement_items_order.py
           (different_vendor_agreement_items_order_result.json): one order per vendor.
        2. Log in to the Digital Marketplace as the order approver ('order_approver').
        3. Go to Orders > Pending Approval Orders and get the pending approval order count.
        4. Search order 1 once, verify it is in the list and store its Order Date and Order Total.
        No logout: Test case 2 opens the order details from this search result.

    All scenario values are read from .env.
    """
    global order_result, order_approver

    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Orders from different_vendor_agreement_items_order.py
    with allure.step("Step 1: Load the order result of different_vendor_agreement_items_order.py"):
        order_result = load_result("different_vendor_agreement_items_order_result",
                                   created_by="different_vendor_agreement_items_order.py")
        missing_values = [key for key in ("order_remarks", "delivery_address") if key not in order_result]
        missing_values += [key for key in ("agreement_number", "specification", "uom", "cart_remarks_entered",
                                           "expected_schedules") if key not in order_result["orders"][0]]
        assert not missing_values, \
            f"Run different_vendor_agreement_items_order.py first (order result has no {', '.join(missing_values)})"
        order_approver = order_result["order_approver"]
        print("ORDERS:", [order["order_reference_number"] for order in order_result["orders"]])
        print("ORDER APPROVER:", order_approver)
        allure.attach(
            "\n".join(f"Order {number}: {order['order_reference_number'] or '-'} | {order['vendor']} | "
                      f"{order['item_code']} | total {order['total_price']}"
                      for number, order in enumerate(order_result["orders"], start=1)),
            name="Order result",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 2: Log in as the order approver
    with allure.step(f"Step 2: Log in to the Digital Marketplace as order approver {order_approver}"):
        login_page = LoginPage(page)
        home_page = HomePage(page)
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=order_approver, pass_word=marketplace_password)
        print(f"Logging in to the Digital Marketplace as: {order_approver}")
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('order_approver_login')

    # Step 3-4: Pending approval list and order 1
    find_order_in_pending_list(page, 1)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Details")
@allure.title("Test_case_2: Order 1 - open pending approval order details")
@allure.description("Test case 2: Open order 1 from the search result and verify the order information, product (cart "
                    "remarks empty, attachment removed), Preferred Delivery Schedule and Action History before the "
                    "approval.")
@pytest.mark.order(2)
def test_2_order_1_open_pending_approval_order_details(page):
    """
    Test case 2: Order 1 pending approval order details (from the search result of Test case 1).

    Steps:
        1. Open the order details.
        2. Order information (Order Date and Order Total = pending approval list; Order Date = the order initiator's
           order details), product (cart remarks empty: blank or N/A; attachment removed: no icon), Preferred
           Delivery Schedule (auto generated), Action History and Order Date.
    """
    open_details_before_approval(page, 1)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Details Links")
@allure.title("Test_case_3: Order 1 - verify pending approval order details links")
@allure.description("Test case 3: Order 1 links in page order: agreement attachment, requisition (ERP), product FA, "
                    "product page, no attachment icon (removed in the cart), Preferred Delivery Schedule links.")
@pytest.mark.order(3)
def test_3_order_1_verify_pending_approval_order_details_links(page):
    """
    Test case 3: Order 1 pending approval order details links.

    Steps:
        1-3. Agreement attachment (order information first), requisition (ERP; ResetHub login as the order approver;
             all tabs closed), product FA link, product page; the attachment was removed in the cart: no icon.
        4. Preferred Delivery Schedule product and requisition links.
    """
    verify_details_links(page, 1)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Delivery Schedule")
@allure.title("Test_case_4: Order 1 - verify the delivery schedule is the schedule of the order")
@allure.description("Test case 4: The Preferred Delivery Schedule of order 1 is the schedule created with the order.")
@pytest.mark.order(4)
def test_4_order_1_verify_delivery_schedule_of_the_order(page):
    """
    Test case 4: Order 1 Preferred Delivery Schedule = the schedule created with the order.

    Steps:
        1. Every row (Quantity, Delivery Date, Location, receiving person) is the row saved by the order test file.
    """
    verify_schedule_is_order_schedule(page, 1)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Order Approval")
@allure.title("Test_case_5: Order 1 - approve marketplace order")
@allure.description("Test case 5: Approve order 1 and verify the approval confirmation message and the order status.")
@pytest.mark.order(5)
def test_5_order_1_approve_marketplace_order(page):
    """
    Test case 5: Approve order 1.

    Steps:
        1. Approve; the message must say the order is approved ("Email sent failed due to null address" is an
           email configuration note, not a failure).
    """
    approve_order(page, 1)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Approved Order Details")
@allure.title("Test_case_6: Order 1 - verify approved order details")
@allure.description("Test case 6: After the approval, verify order 1 details and the approval row of the Action History.")
@pytest.mark.order(6)
def test_6_order_1_verify_approved_order_details(page):
    """
    Test case 6: Order 1 approved order details.

    Steps:
        1. Order information (Order Approved), product, Preferred Delivery Schedule, Action History and Order Date.
        2. Approval row: User Type "Requisition Approver", Order Status "Order Approved", the order approver, Time.
    """
    verify_approved_details(page, 1)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Approved Order Preview")
@allure.title("Test_case_7: Order 1 - verify approved order preview")
@allure.description("Test case 7: Order 1 preview: download the order document and verify it, then save the result.")
@pytest.mark.order(7)
def test_7_order_1_verify_approved_order_preview(page):
    """
    Test case 7: Order 1 approved order preview.

    Steps:
        1. Preview (ERP; ResetHub login as the order approver): order reference, approved status, BRAC letter pad,
           Purchase Order number, item, totals, amount in words, delivery date and place.
        2. Save the order approval result.
        No logout: Test case 8 continues with order 2.
    """
    verify_approved_preview(page, 1)


# ---------------- Order 2 (vendor of item 2) ----------------

@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Orders")
@allure.title("Test_case_8: Order 2 - verify order in pending approval list")
@allure.description("Test case 8: Go to the Pending Approval Orders list again and search order 2 (vendor of item 2) "
                    "once.")
@pytest.mark.order(8)
def test_8_order_2_verify_order_in_pending_approval_list(page):
    """
    Test case 8: Order 2 in the approver's Pending Approval Orders list (same login as order 1).

    Steps:
        1. Go to Orders > Pending Approval Orders and get the pending approval order count.
        2. Search order 2 once, verify it is in the list and store its Order Date and Order Total.
    """
    assert order_result, "Test case 1 must pass first: the order result is not loaded"
    find_order_in_pending_list(page, 2)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Details")
@allure.title("Test_case_9: Order 2 - open pending approval order details")
@allure.description("Test case 9: Open order 2 from the search result and verify the order information, product (cart "
                    "remarks, new attachment, cart quantity), Preferred Delivery Schedule and Action History before "
                    "the approval.")
@pytest.mark.order(9)
def test_9_order_2_open_pending_approval_order_details(page):
    """
    Test case 9: Order 2 pending approval order details (from the search result of Test case 8).

    Steps:
        1. Open the order details.
        2. Order information, product (cart remarks, cart attachment icon, cart quantity), Preferred Delivery
           Schedule (2 manual schedules), Action History and Order Date.
    """
    open_details_before_approval(page, 2)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Details Links")
@allure.title("Test_case_10: Order 2 - verify pending approval order details links")
@allure.description("Test case 10: Order 2 links in page order: agreement attachment, requisition (ERP), product FA, "
                    "product page, item attachment (the cart attachment), Preferred Delivery Schedule links.")
@pytest.mark.order(10)
def test_10_order_2_verify_pending_approval_order_details_links(page):
    """
    Test case 10: Order 2 pending approval order details links.

    Steps:
        1-3. Agreement attachment, requisition (ERP), product FA link, product page and item attachment (same file
             type as the cart attachment).
        4. Preferred Delivery Schedule product and requisition links.
    """
    verify_details_links(page, 2)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Delivery Schedule")
@allure.title("Test_case_11: Order 2 - verify the delivery schedule is the schedule of the order")
@allure.description("Test case 11: The Preferred Delivery Schedule of order 2 is the schedule created with the order.")
@pytest.mark.order(11)
def test_11_order_2_verify_delivery_schedule_of_the_order(page):
    """
    Test case 11: Order 2 Preferred Delivery Schedule = the schedule created with the order.

    Steps:
        1. Every row (Quantity, Delivery Date, Location, receiving person) is the row saved by the order test file.
    """
    verify_schedule_is_order_schedule(page, 2)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Order Approval")
@allure.title("Test_case_12: Order 2 - approve marketplace order")
@allure.description("Test case 12: Approve order 2 and verify the approval confirmation message and the order status.")
@pytest.mark.order(12)
def test_12_order_2_approve_marketplace_order(page):
    """
    Test case 12: Approve order 2.

    Steps:
        1. Approve; the message must say the order is approved (email failure = email configuration note).
    """
    approve_order(page, 2)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Approved Order Details")
@allure.title("Test_case_13: Order 2 - verify approved order details")
@allure.description("Test case 13: After the approval, verify order 2 details and the approval row of the Action History.")
@pytest.mark.order(13)
def test_13_order_2_verify_approved_order_details(page):
    """
    Test case 13: Order 2 approved order details.

    Steps:
        1. Order information (Order Approved), product, Preferred Delivery Schedule, Action History and Order Date.
        2. Approval row: User Type "Requisition Approver", Order Status "Order Approved", the order approver, Time.
    """
    verify_approved_details(page, 2)


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Approved Order Preview")
@allure.title("Test_case_14: Order 2 - verify approved order preview, both orders approved and log out")
@allure.description("Test case 14: Order 2 preview, then both orders of the requisition are approved (one order per "
                    "vendor), log out and save the order approval result.")
@pytest.mark.order(14)
def test_14_order_2_verify_approved_order_preview_and_both_orders(page):
    """
    Test case 14: Order 2 approved order preview and both orders.

    Steps:
        1-2. Order 2 preview (order document) and save the order approval result.
        3. Both orders of the requisition are approved (each with its own vendor).
        4. Log out from the Digital Marketplace and save the order approval result.
    """
    verify_approved_preview(page, 2)

    # Step 3: Both orders approved
    with allure.step("Step 3: Verify both orders of the requisition are approved"):
        checks = []
        for number, order in enumerate(order_result["orders"], start=1):
            if order["removed_from_cart"]:
                continue
            status = approvals[number].get("approved_order_status", "")
            checks.append(new_check(f"Order {number} ({order['vendor']}) status", "Order Approved",
                                    status or "not approved", "approved" in status.lower()))
        attach_and_assert_checks(checks, "Both orders of the requisition approved")

    # Step 4: Log out and save
    with allure.step("Step 4: Log out from the Digital Marketplace and save the order approval result"):
        MainNavigationMenu(page).perform_logout()
        PendingApprovalOrders(page).get_full_page_screenshot('order_approver_logout')
        save_approval_result()
        print("ORDER APPROVAL RESULT:", order_approval_result)
