from dotenv import load_dotenv
import os
from pathlib import Path

import pytest
import allure

load_dotenv()

# Digital Marketplace (staging)
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
# Item attachment of the order (uploaded in the shopping cart by single_whitelisted_agreement_item_order.py)
order_attachment_file = os.getenv("test_requisition_attachment_file")
# Approval message when the order approver has no email address (staging email configuration)
EMAIL_NOT_SENT_MESSAGE = "Email sent failed"
# Project root is 3 levels up: testcases/order_approval/<this file>
DOWNLOAD_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "downloads"

from utils.test_data_store import load_result, save_result
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.my_account.pending_approval_orders import PendingApprovalOrders
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails
from brac_digital_marketplace.testcases.order_creation.order_page_links import check_order_details_page_links, \
    read_requisition_from_link, requisition_product_name_checks
from brac_digital_marketplace.testcases.order_creation.order_details_checks import check_order_information, \
    check_product, check_delivery_schedules, check_action_history, check_order_preview, to_amount, new_check, \
    without_spaces, receiver_of

# Order of single_whitelisted_agreement_item_order.py (single_whitelisted_order_result.json)
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


def expected_order(order_status):
    # Why: the values the order details and the order document must show (saved by the order test file);
    # When: order details and preview checks before and after the approval
    return {
        "order_reference_number": order_reference_number, "requisition_number": order["requisition_number"],
        "agreement_number": order["agreement_number"], "order_status": order_status,
        "order_remarks": order["order_remarks"], "vendor": order["vendor"],
        "master_item_code": order["master_item_code"], "item_code": order["item_code"],
        "specification": order["specification"], "remarks": order["cart_remarks"], "uom": order["uom"],
        "quantity": order["cart_quantity"], "unit_price": order["unit_price"], "schedules": order["expected_schedules"],
    }


def verify_order_details(page, order_status, label):
    # Why: the order details must be the order that was created (information, product, Preferred Delivery Schedule
    # and Action History); When: before and after the approval. Returns the order details
    expected = expected_order(order_status)
    details = {}
    approved = "approved" in order_status.lower()
    with allure.step(f"Verify the order information ({label})"):
        checks, details["information"] = check_order_information(page, expected)
        checks += [
            new_check("Order Date (details = pending approval list)", list_order_date,
                      details["information"]["Order Date"], details["information"]["Order Date"] == list_order_date),
            new_check("Order Date (= order details of the order initiator)",
                      order["order_details"]["information"]["Order Date"], details["information"]["Order Date"],
                      details["information"]["Order Date"] == order["order_details"]["information"]["Order Date"]),
            new_check("Order Total (details = pending approval list)", list_order_total,
                      details["information"]["Order Total"],
                      to_amount(details["information"]["Order Total"]) == to_amount(list_order_total)),
        ]
        PendingApprovalOrders(page).get_full_page_screenshot(f'{label}_order_information')
        attach_and_assert_checks(checks, f"Order information ({label})")
    with allure.step(f"Verify the product and the Sub-Total ({label})"):
        checks, details["product"] = check_product(page, expected)
        attach_and_assert_checks(checks, f"Order product ({label})")
    with allure.step(f"Verify the Preferred Delivery Schedule ({label})"):
        checks, details["delivery_schedule"] = check_delivery_schedules(page, expected["schedules"])
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


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Orders")
@allure.title("Test_case_1: Verify order in pending approval list")
@allure.description("Test case 1: Search the whitelisted item marketplace order once in the order approver's Pending "
                    "Approval Orders list and store its Order Date and Order Total.")
@pytest.mark.order(1)
def test_1_verify_order_in_pending_approval_list(page):
    """
    Test case 1: Verify the order in the approver's Pending Approval Orders list
    (same as marketplace_staging_sanity.py Test case 13).

    Steps:
        1. Load the order of single_whitelisted_agreement_item_order.py
           (single_whitelisted_order_result.json) and store it in 'order'.
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
        "test_requisition_attachment_file": order_attachment_file,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    login_page = LoginPage(page)
    home_page = HomePage(page)
    pending_approval_orders = PendingApprovalOrders(page)

    # Step 1: Order from single_whitelisted_agreement_item_order.py
    with allure.step("Step 1: Load the order result of single_whitelisted_agreement_item_order.py"):
        order = load_result("single_whitelisted_order_result", created_by="single_whitelisted_agreement_item_order.py")
        missing_order_values = [key for key in ("expected_schedules", "order_details", "uom", "cart_remarks",
                                                "requisition_product_name")
                                if key not in order]
        assert not missing_order_values, \
            f"Run single_whitelisted_agreement_item_order.py first (order result has no {', '.join(missing_order_values)})"
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
                    "verify the order information, product, Preferred Delivery Schedule and Action History before "
                    "the approval.")
@pytest.mark.order(2)
def test_2_open_pending_approval_order_details(page):
    """
    Test case 2: Pending approval order details. Continues from the search result of Test case 1 (no new search).

    Steps:
        1. Open the order details from the pending approval list.
        2. Order information (Submitted for Approval; Order Date and Order Total = pending approval list; Order
           Date = the Order Date of the order initiator's order details),
           product, Preferred Delivery Schedule, Action History and Order Date (= the date the order was submitted).
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
@allure.description("Test case 3: Download the agreement attachment (agreement number first), open the requisition "
                    "details (ERP), open the product details page and download the item attachment.")
@pytest.mark.order(3)
def test_3_verify_pending_approval_order_details_links(page):
    """
    Test case 3: Pending approval order details links. Continues on the order details page of Test case 2.

    Steps:
        1. Agreement attachment download: first the agreement number of the order information, then the product
           FA link.
        2. Requisition details (ERP; the ERP login is done as the order approver with the ResetHub link when it is
           shown; all opened tabs closed).
        3. Product details page and item attachment download (same file type as 'test_requisition_attachment_file').
        4. Preferred Delivery Schedule heading links: product details page and requisition "(Req: ...)" (ERP
           requisition details; all opened tabs closed).

    All scenario values are read from .env.
    """
    global order_details_links
    assert details_before_approval, "Test case 2 must pass first: order details are not verified"

    # Step 1-3: Order details links and item attachment
    with allure.step("Step 1-3: Download the agreement attachment, open the requisition details and product details, "
                     "download the item attachment"):
        link_checks, order_details_links = check_order_details_page_links(
            page, order["requisition_number"], order["agreement_number"], order["item_code"], order_attachment_file,
            'pending_approval_order_details', DOWNLOAD_DIR, erp_user=order_approver,
            requisition_product_name=order["requisition_product_name"])
        attach_and_assert_checks(link_checks, "Pending approval order details links and item attachment")

    # Step 4: Preferred Delivery Schedule heading links (product details page and requisition)
    with allure.step("Step 4: Verify the Preferred Delivery Schedule product name and open the requisition link"):
        order_details_page = OrderDetails(page)
        schedule_requisition, opened_tabs = read_requisition_from_link(
            page, lambda: order_details_page.open_link_all_tabs(
                order_details_page.delivery_schedule_requisition_link(order["requisition_number"])),
            'pending_approval_schedule_erp_requisition', erp_user=order_approver)
        order_details_links["Delivery schedule requisition"] = schedule_requisition["req_no"]
        checks = [
            *requisition_product_name_checks(page.locator("body"), order["requisition_product_name"],
                                             "Preferred Delivery Schedule"),
            new_check("Preferred Delivery Schedule requisition link (ERP REQ. No)", order["requisition_number"],
                      schedule_requisition["req_no"], schedule_requisition["req_no"] == order["requisition_number"]),
            new_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1),
        ]
        PendingApprovalOrders(page).get_full_page_screenshot('pending_approval_order_links_checked')
        attach_and_assert_checks(checks, "Pending approval Preferred Delivery Schedule links")


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Order Delivery Schedule")
@allure.title("Test_case_4: Verify the delivery schedule is the schedule of the order")
@allure.description("Test case 4: The Preferred Delivery Schedule of the pending approval order is the delivery "
                    "schedule created with the order (single_whitelisted_agreement_item_order.py).")
@pytest.mark.order(4)
def test_4_verify_delivery_schedule_of_the_order(page):
    """
    Test case 4: Preferred Delivery Schedule = the schedule created with the order. Continues on the order details.

    Steps:
        1. Every Preferred Delivery Schedule row (Quantity, Delivery Date, Location, Receiver Info) is the same as
           the row saved by the order test file.
    """
    global delivery_schedule
    assert order_details_links, "Test case 3 must pass first: order details links are not verified"

    # Step 1: Delivery schedule of the approver = delivery schedule of the order
    with allure.step("Step 1: Compare the Preferred Delivery Schedule with the schedule created with the order"):
        delivery_schedule = details_before_approval["delivery_schedule"]
        order_schedule = order["order_details"]["delivery_schedule"]
        checks = [new_check("Delivery schedules", len(order_schedule), len(delivery_schedule),
                            len(delivery_schedule) == len(order_schedule))]
        for number, (order_row, approver_row) in enumerate(zip(order_schedule, delivery_schedule), start=1):
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
@allure.description("Test case 6: After the approval, verify the order status, Order Date, order information, "
                    "product, Preferred Delivery Schedule and Action History (submitted and approved).")
@pytest.mark.order(6)
def test_6_verify_approved_order_details(page):
    """
    Test case 6: Approved order details. Continues on the order details page of Test case 5.

    Steps:
        1. Order information (Order Approved; Order Date and Order Total = pending approval list; Order Date = the
           Order Date of the order initiator's order details), product,
           Preferred Delivery Schedule, Action History (submitted by the requisition initiator, approved by the
           order approver) and Order Date (= the date the order was submitted).
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
                    "status, Purchase Order number, item, totals, amount in words, delivery date and place), then log "
                    "out and save the order approval result.")
@pytest.mark.order(7)
def test_7_verify_approved_order_preview(page):
    """
    Test case 7: Approved order preview. Continues on the order details page of Test case 6.

    Steps:
        1. Click Preview (ERP; log in as the order approver with the ResetHub link when the ERP login page is
           shown): download the order document and verify the preview address (order reference, approved status,
           BRAC letter pad), the Purchase Order number, the item details, totals, amount in words and the delivery
           schedule.
        2. Log out from the Digital Marketplace.
        3. Save the order approval result (single_whitelisted_order_approval_result.json).
    """
    global order_preview, order_approval_result
    assert details_after_approval, "Test case 6 must pass first: approved order details are not verified"
    pending_approval_orders = PendingApprovalOrders(page)

    # Step 1: Preview and order document
    with allure.step("Step 1: Click Preview, download the order document and verify it"):
        checks, order_preview = check_order_preview(page, expected_order(approved_order_status), DOWNLOAD_DIR,
                                                    erp_user=order_approver)
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
        save_result("single_whitelisted_order_approval_result", order_approval_result)
        print("ORDER APPROVAL RESULT:", order_approval_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in order_approval_result.items()),
            name="Saved order approval result",
            attachment_type=allure.attachment_type.TEXT
        )
