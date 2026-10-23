from dotenv import load_dotenv
import os
import random
import string
from datetime import datetime
from pathlib import Path

import pytest
import allure

load_dotenv()

# Item receive of the order acknowledged by
# order_acknowledgement/item_remarks_and_attachment_upload_order_acknowledgement.py (reads its saved result): 8 items of
# one framework agreement and one vendor, one auto generated schedule per item, every schedule received by the order
# initiator. The order initiator receives every item in its own full receive (8 receives, 8 challans); each receive
# has the attachment type of its item's requisition attachment (PDF, JPG, PNG, XLS, PPTX, DOCX, ZIP), the item without
# attachment is received without attachment. Every receive row is checked against its own order item (agreement item +
# master item). Every challan is verified in the Item Received List and the item receive details; the order details
# status and order document are verified once while Partially Received (first receive) and once Settled (last
# receive); then the item receives (MRR) in ERP.
# Digital Marketplace
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
# Order initiator (receives every schedule in one full receive), BRAC SSO login of the initiator
order_initiator = os.getenv("test_order_initiator")
proj_user = os.getenv("test_user_name")
# Receive remarks (3-255 characters); the attachment of each receive is the requisition attachment of its item
receiving_remarks = os.getenv("test_receiving_remarks")
# ERP procurement admin (item receive / MRR in ERP), ResetHub environment
proc_admin = os.getenv("test_proc_admin")
proj_env = os.getenv("test_env")
# Project root is 3 levels up: testcases/receivable_order/<this file>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
UTILS_DIR = PROJECT_ROOT / "utils"
DOWNLOAD_DIR = PROJECT_ROOT / "artifacts" / "downloads"

from utils.test_data_store import load_result, save_result
from utils.remarks_rules import same_remarks
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails
from pages.digital_marketplace.administration.order_management.orders_list_management import OrdersListManagement
from pages.digital_marketplace.administration.order_management.receivable_order_list import ReceivableOrderList
from pages.digital_marketplace.administration.order_management.item_received_list import ItemReceivedList
from pages.digital_marketplace.administration.order_management.order_details_administration import \
    OrderDetailsAdministration
from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.item_receive.item_receive_list import ItemReceiveList
from brac_digital_marketplace.testcases.order_creation.order_page_links import read_requisition_from_link, close_tabs
from brac_digital_marketplace.testcases.order_creation.order_details_checks import to_amount, new_check, \
    without_spaces, receiver_of

# Receiving remarks length (business rule)
MIN_RECEIVING_REMARKS_LENGTH = 3
MAX_RECEIVING_REMARKS_LENGTH = 255
# Challan No. length (business rule)
MAX_CHALLAN_LENGTH = 255
# Order status after a receive with remaining quantity, and after the last receive (settled)
ORDER_STATUS_PARTIALLY_RECEIVED = "Partially received"
ORDER_STATUS_SETTLED_WORD = "settled"

# Acknowledged order (item_remarks_and_attachment_upload_vendor_acknowledgement_result.json, Test case 1)
order = {}
# Received quantity of every schedule so far (by schedule quantity), and every receive (challan) done
received_by_schedule = {}
receives = []
# Receive page opened by the current receiver (Test case 2, 6), ERP item receives (Test case 11)
receive_page_checked = {}
erp_item_receives = {}
receive_result = {}
# Requisition link checks of the receive page: the requisition number is shown as a link; when clicking it opens no
# page, the check is reported where it is made and asserted at the end of Test case 6 so the receive continues
requisition_link_checks_of_file = []


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


def framework_order_no():
    # Why: the Framework Order No. generated by the vendor acknowledgement; When: every receive step
    return order["framework_order_no"]


def order_items():
    # Why: the items of the order (item code, master item, FA, product name, specification, remarks, unit price,
    # quantity, total) saved by the approval and acknowledgement files; When: receive checks
    return order["items"]


def item_of(row):
    # Why: a receive / popup / receive details row is the order item with the same agreement item and master item;
    # When: receive checks. Returns the order item ({} when not found)
    return next((item for item in order_items() if item["item_code"] == row.get("Agreement item")
                 and item["master_item_code"] == row.get("Master item")), {})


def saved_schedules():
    # Why: the Preferred Delivery Schedule rows of the approved order (quantity, delivery date, location, receiver);
    # When: receive plan, delivery information and receiver name checks
    return order["details_after_approval"]["delivery_schedule"]


def expected_schedules():
    # Why: every schedule with its receiving person PIN, e.g. "(00292909) - MD. ..." -> "00292909"; When: receive plan
    # and the "fully received" check
    return [{"Quantity": row["Quantity"], "Location": row["Location"],
             "Receiver": receiver_of(row).split(")", 1)[0].strip("( ")} for row in saved_schedules()]


def login_id(pin):
    # Why: BRAC SSO login uses the PIN without leading zeros ("00292909" -> "292909"); When: receiver logins
    return str(int(pin))


def schedules_of(pin):
    # Why: the schedules of one receiving person (each receiver sees only its own schedules); When: receive steps
    return [schedule for schedule in expected_schedules() if schedule["Receiver"] == pin]


def saved_schedule(quantity):
    # Why: the order details schedule row of a schedule quantity (delivery date, location, receiver info);
    # When: View Details (delivery information) check
    return next((row for row in saved_schedules() if to_amount(row["Quantity"]) == to_amount(quantity)), {})


def receiver_name_of(pin):
    # Why: pages show the receiving person by name; the name is in the schedule Receiver Info, e.g.
    # "(00292909) - MD. YUSUF KHAN HRIDOY, Field Organiser, ..." -> "MD. YUSUF KHAN HRIDOY"; When: Action History check
    row = next((row for row in saved_schedules() if f"({pin})" in receiver_of(row)), {})
    return receiver_of(row).split(") -", 1)[-1].split(",")[0].strip()


def remaining_of(quantity):
    # Why: the quantity of a schedule not received yet; When: receive page and popup checks
    return to_amount(quantity) - received_by_schedule.get(str(to_amount(quantity)), to_amount("0"))


def generate_challan_number():
    # Why: a new challan per receive, same format as marketplace_staging_sanity.py: DM_ + framework order last 4
    # digits + random characters (max 255 characters); When: every receive
    challan = f"DM_{framework_order_no()[-4:]}{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    assert len(challan) <= MAX_CHALLAN_LENGTH, f"Challan No. longer than {MAX_CHALLAN_LENGTH} characters"
    return challan


def check_remarks_length(env_name, remarks):
    # Why: receiving remarks must be 3-255 characters (business rule); When: before every receive
    assert MIN_RECEIVING_REMARKS_LENGTH <= len(remarks) <= MAX_RECEIVING_REMARKS_LENGTH, \
        f"{env_name} must be {MIN_RECEIVING_REMARKS_LENGTH}-{MAX_RECEIVING_REMARKS_LENGTH} characters, found {len(remarks)}"


def date_range():
    # Why: the receive lists are searched with Start date and End date = today (mm-dd-yyyy), same as
    # marketplace_staging_sanity.py; When: list searches
    today = datetime.today().strftime("%m-%d-%Y")
    return today, today


def log_in_to_administration(page, pin, label):
    # Why: a receiving person logs in with BRAC SSO and goes to Administration; When: start of every receive
    login_page = LoginPage(page)
    home_page = HomePage(page)
    # A previous receiver may still be logged in (a failed step skips its logout): start a new session
    page.context.clear_cookies()
    login_page.navigate_to_url(marketplace_url_qa)
    login_page.perform_marketplace_login(user_name=login_id(pin), pass_word=marketplace_password)
    home_page.goto_administration()
    home_page.wait_for_timeout(2000)
    home_page.get_full_page_screenshot(f'item_remarks_receive_{label}_administration')


def log_in_to_erp_as_order_initiator(page):
    # Why: the order document is an ERP page; a receiver may have no ERP Procurement access, so the order initiator is
    # logged in to ERP (ResetHub link in a new tab) before Print; When: before the order document of every receive
    erp_tab = page.context.new_page()
    reset_page = ResetHubPage(erp_tab)
    reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=proj_user))
    erp_tab.close()
    page.bring_to_front()
    print(f"ERP login as the order initiator {proj_user} for the order document")


def check_receive_item(item, label, quantity_label):
    # Why: an item row of the receive page / popup / receive details must be its order item (master item,
    # requisition, FA No., product name, specification, remarks, unit price); When: receive checks
    order_item = item_of(item)
    return [
        new_check(f"{label} FA No.", order["agreement_number"], item.get("FA No.") or "-",
                  item.get("FA No.") == order["agreement_number"]),
        new_check(f"{label} order item (agreement item + master item)", "an item of the order",
                  f"{item.get('Agreement item') or '-'} {item.get('Master item') or '-'}", bool(order_item)),
        new_check(f"{label} requisition", order["requisition_number"], item.get("Requisition") or "-",
                  item.get("Requisition") == order["requisition_number"]),
        new_check(f"{label} product name (item name - delivery location)", order_item.get("requisition_product_name", "-"),
                  item.get("Product name") or "-",
                  bool(order_item) and item.get("Product name") == order_item["requisition_product_name"]),
        new_check(f"{label} specification", order_item.get("specification", "-"), item.get("Specification") or "-",
                  bool(order_item) and without_spaces(item.get("Specification")) == without_spaces(order_item["specification"])),
        new_check(f"{label} remarks", (order_item.get("remarks") or "-")[:60], (item.get("Remarks") or "-")[:60],
                  bool(order_item) and same_remarks(order_item["remarks"], item.get("Remarks", ""))),
        new_check(f"{label} unit price", order_item.get("unit_price", "-"), item.get("Unit Price (Incl. VAT & TAX)") or "-",
                  bool(order_item) and to_amount(item.get("Unit Price (Incl. VAT & TAX)") or "0") == to_amount(order_item["unit_price"])),
    ]


def check_requisition_link(page, row, pin, label):
    # Why: the requisition number link of a receive row must show the order requisition and open its ERP requisition
    # (ERP login with the ResetHub link as the receiver when the ERP login page is shown); When: before and after the
    # item selection. The designated receiver only checks the link text (no click). When the order initiator's click
    # opens no page, the check is kept for the end of Test case 6. Returns checks
    receivable_order_list = ReceivableOrderList(page)
    link = receivable_order_list.receive_requisition_link(row)
    link_text = " ".join(link.inner_text().split()) if link.count() else ""
    checks = [new_check(f"Requisition link {label} (text)", order["requisition_number"], link_text or "not shown",
                        link_text == order["requisition_number"])]
    # The designated receiver does not click the requisition link (user rule): only the order initiator opens it
    if pin != order_initiator:
        print(f"Requisition link {label}: not clicked by the designated receiver")
        return checks
    try:
        with page.context.expect_page(timeout=10000):
            link.click()
        opened = True
    except Exception:
        opened = False
    if not opened:
        print(f"Requisition link {label}: no page opened")
        no_page_check = new_check(f"Requisition link {label} opens the ERP requisition", "ERP requisition opened",
                                  "no page opened", False)
        requisition_link_checks_of_file.append(no_page_check)
        allure.attach(f"{no_page_check[0]}: expected {no_page_check[1]} | actual {no_page_check[2]} | FAIL",
                      name=f"Requisition link {label}", attachment_type=allure.attachment_type.TEXT)
        return checks
    close_tabs([tab for tab in page.context.pages if tab != page], page)
    erp_requisition, opened_tabs = read_requisition_from_link(
        page, lambda: receivable_order_list.open_link_in_new_tabs(link),
        f'item_remarks_receive_{label}_erp_requisition', erp_user=login_id(pin))
    return checks + [
        new_check(f"Requisition link {label} (ERP REQ. No)", order["requisition_number"], erp_requisition["req_no"],
                  erp_requisition["req_no"] == order["requisition_number"]),
        new_check(f"Requisition link {label} tabs closed", "all", f"{opened_tabs} tab(s) closed",
                  len(page.context.pages) == 1),
    ]


def open_receive_page(page, pin, label, full_checks=True):
    # Why: Receivable Order List: search the framework order, verify its row, open it with View and verify the receive
    # page (order, vendor, the receiver's schedule rows; with full_checks also the delivery information and the
    # requisition link before the selection); When: start of every receive
    orders_list = OrdersListManagement(page)
    receivable_order_list = ReceivableOrderList(page)
    start_date, end_date = date_range()

    with allure.step(f"Search framework order {framework_order_no()} in Receivable Order List and verify its row"):
        orders_list.open_order_management_menu_if_collapsed(receivable_order_list.receivable_order_list_submenu)
        receivable_order_list.goto_receivable_order_list()
        receivable_order_list.open_search_panel_if_collapsed(receivable_order_list.order_input)
        receivable_order_list.fill_date_range(start_date=start_date, end_date=end_date)
        receivable_order_list.search_receivable_order(receivable_order_number=framework_order_no())
        receivable_order_list.wait_for_timeout(3000)
        row_shown = receivable_order_list.order_list_row(framework_order_no()).is_visible()
        list_row = receivable_order_list.read_order_list_row(framework_order_no()) if row_shown else {}
        order_total = sum((to_amount(item["total_price"]) for item in order_items()), to_amount("0"))
        checks = [
            new_check("Order in Receivable Order List", framework_order_no(), "found" if row_shown else "not found",
                      row_shown),
            new_check("Reference #", order["order_reference_number"], list_row.get("Reference #", "-"),
                      list_row.get("Reference #") == order["order_reference_number"]),
            new_check("Vendor Name", order["vendor"], list_row.get("Vendor Name", "-"),
                      list_row.get("Vendor Name", "").lower() == order["vendor"].lower()),
            new_check("Order total", order_total.quantize(to_amount("0")), list_row.get("Order total", "-"),
                      bool(list_row) and to_amount(list_row.get("Order total")) == order_total),
            new_check("Order status (receivable)", "Vendor Acknowledged / Partially received",
                      list_row.get("Order status", "-"), bool(list_row.get("Order status"))),
        ]
        receivable_order_list.get_full_page_screenshot(f'item_remarks_receive_{label}_receivable_order_list')
        attach_and_assert_checks(checks, f"Receivable Order List ({label})")

    with allure.step("Open the order with View and verify the receive page before the item selection"):
        receivable_order_list.receivable_order_view()
        page.wait_for_load_state("domcontentloaded")
        receivable_order_list.to_receive_table.wait_for(state="visible", timeout=30000)
        heading = " ".join(receivable_order_list.receive_page_heading.inner_text().split())
        rows = receivable_order_list.read_to_receive_rows()
        print(f"RECEIVE PAGE ({label}):", rows)
        expected_schedules = schedules_of(pin)
        shown_quantities = [to_amount(row.get("Schedule Qty") or "0") for row in rows]
        checks = [new_check("Receive page of the framework order", framework_order_no(), heading,
                            framework_order_no() in heading)]
        # Every schedule of the receiver is shown and can be received
        checks += [new_check(f"Schedule {schedule['Quantity']} of the receiver shown", schedule["Quantity"],
                             "shown" if to_amount(schedule["Quantity"]) in shown_quantities else "not shown",
                             to_amount(schedule["Quantity"]) in shown_quantities) for schedule in expected_schedules]
        # Every shown row: order item, received / remaining quantity; a row without checkbox is fully received
        for row in rows:
            quantity = row.get("Schedule Qty") or "0"
            remaining = remaining_of(quantity)
            checks += check_receive_item(row, f"Schedule {quantity}", "Schedule Qty")
            checks += [
                new_check(f"Schedule {quantity} Total Received Qty", to_amount(quantity) - remaining,
                          row.get("Total Received Qty", "-"), to_amount(row.get("Total Received Qty") or "0") == to_amount(quantity) - remaining),
                new_check(f"Schedule {quantity} Remaining Qty", remaining, row.get("Remaining Qty", "-"),
                          to_amount(row.get("Remaining Qty") or "0") == remaining),
            ]
            if row["Selectable"]:
                checks += [
                    new_check(f"Schedule {quantity} Quantity to Receive (default = remaining)", remaining,
                              row.get("Quantity to Receive") or "-", to_amount(row["Quantity to Receive"] or "0") == remaining),
                    new_check(f"Schedule {quantity} not selected", "not selected",
                              "selected" if row["Selected"] else "not selected", not row["Selected"]),
                ]
            else:
                checks.append(new_check(f"Schedule {quantity} without checkbox (fully received)", 0, remaining, remaining == 0))
        receivable_order_list.get_full_page_screenshot(f'item_remarks_receive_{label}_receive_page')
        attach_and_assert_checks(checks, f"Receive page ({label})")

    if not full_checks:
        receive_page_checked[label] = True
        return

    with allure.step("View Details: delivery location and receiving person of every schedule row"):
        checks = []
        for row_element, row in zip(receivable_order_list.to_receive_rows(), rows):
            saved = saved_schedule(row.get("Schedule Qty") or "0")
            delivery = receivable_order_list.read_row_delivery_info(row_element)
            receiver = receiver_of(saved).split(") -", 1)[-1].split(",")[0].strip()
            checks += [
                new_check(f"Schedule {row.get('Schedule Qty')} Location", saved.get("Location", "-"), delivery["Location"] or "-",
                          without_spaces(saved.get("Location")).lower() in without_spaces(delivery["Location"]).lower()),
                new_check(f"Schedule {row.get('Schedule Qty')} Delivery Info (receiving person)", receiver,
                          delivery["Delivery Info"] or "-", bool(receiver) and receiver.lower() in delivery["Delivery Info"].lower()),
            ]
        attach_and_assert_checks(checks, f"Receive page delivery information ({label})")

    with allure.step("Requisition link before the item selection"):
        checks = check_requisition_link(page, receivable_order_list.to_receive_rows()[0], pin, f"{label} before selection")
        attach_and_assert_checks(checks, f"Requisition link before the item selection ({label})")
    receive_page_checked[label] = True


def receive_items(page, pin, label, attachment_file, remarks, partial_quantity=None, only_item=None,
                  check_links=True):
    # Why: select the receiver's schedule rows (only_item: the row of one order item; otherwise all items, optionally
    # a partial quantity of the first row), requisition link after the selection (check_links), challan, attachment
    # (none when attachment_file is empty) and remarks; verify the receive popup (item, quantities, challan, remarks)
    # before Confirm; When: every receive. Returns the receive (challan, quantities, ...)
    receivable_order_list = ReceivableOrderList(page)
    attachment_path = UTILS_DIR / attachment_file if attachment_file else None
    assert attachment_path is None or attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"
    challan_no = generate_challan_number()

    with allure.step("Select the items to receive (one item, or all items as in the sanity file)"):
        row_elements = receivable_order_list.to_receive_rows()
        if only_item:
            item_row = next(element for element, row in zip(row_elements, receivable_order_list.read_to_receive_rows())
                            if item_of(row) == only_item)
            receivable_order_list.select_receive_row(item_row)
        else:
            receivable_order_list.all_item_select.click()
        receivable_order_list.wait_for_timeout(3000)
        if partial_quantity:
            first_selectable = next(element for element, row in zip(row_elements, receivable_order_list.read_to_receive_rows())
                                    if row["Selected"])
            receivable_order_list.set_row_quantity_to_receive(first_selectable, partial_quantity)
        rows = [row for row in receivable_order_list.read_to_receive_rows() if row["Selected"]]
        quantities = {str(to_amount(row["Schedule Qty"])): to_amount(row["Quantity to Receive"] or "0") for row in rows}
        print(f"QUANTITIES TO RECEIVE ({label}):", quantities)
        checks = [new_check("Selected rows", 1 if only_item else "all receivable", len(rows),
                            len(rows) == 1 if only_item else bool(rows))]
        if only_item:
            checks.append(new_check("Selected row = the item to receive", only_item["item_code"],
                                    rows[0].get("Agreement item") if rows else "-",
                                    bool(rows) and item_of(rows[0]) == only_item))
        receivable_order_list.get_full_page_screenshot(f'item_remarks_receive_{label}_items_selected')
        attach_and_assert_checks(checks, f"Item selection ({label})")

    if check_links:
        with allure.step("Requisition link after the item selection"):
            checks = check_requisition_link(page, receivable_order_list.to_receive_rows()[0], pin, f"{label} after selection")
            attach_and_assert_checks(checks, f"Requisition link after the item selection ({label})")

    with allure.step(f"Challan {challan_no}, attachment {attachment_path.name if attachment_path else '(none)'} and remarks"):
        receivable_order_list.challan_no_input(fill_challan_no=challan_no)
        if attachment_path:
            assert receivable_order_list.receiving_upload_attachment(str(attachment_path)), "File upload failed"
            receivable_order_list.wait_for_timeout(3000)
        receivable_order_list.input_received_remarks(receiving_remarks=remarks)
        challan_date, receive_date = receivable_order_list.read_receive_dates()
        print(f"CHALLAN ({label}):", challan_no, "| challan date:", challan_date, "| receive date:", receive_date)
        receivable_order_list.get_full_page_screenshot(f'item_remarks_receive_{label}_receive_values')

    with allure.step("Open the receive popup and verify it before Confirm"):
        receivable_order_list.open_item_receive_popup()
        overview = receivable_order_list.read_receive_overview()
        print(f"RECEIVE POPUP ({label}):", overview)
        checks = [
            new_check("Popup Order No.", framework_order_no(), "shown" if framework_order_no() in overview["text"] else "not shown",
                      framework_order_no() in overview["text"]),
            new_check("Popup Vendor", order["vendor"], "shown" if order["vendor"] in overview["text"] else "not shown",
                      order["vendor"] in overview["text"]),
            new_check("Popup Challan No.", challan_no, "shown" if challan_no in overview["text"] else "not shown",
                      challan_no in overview["text"]),
            new_check("Popup Receive Date (receive page)", receive_date, "shown" if receive_date in overview["text"] else "not shown",
                      receive_date in overview["text"]),
            new_check("Popup Received Remarks", remarks, "shown" if without_spaces(remarks) in without_spaces(overview["text"]) else "not shown",
                      without_spaces(remarks) in without_spaces(overview["text"])),
            new_check("Popup items (selected rows)", len(rows), len(overview["items"]), len(overview["items"]) == len(rows)),
        ]
        for number, item in enumerate(overview["items"], start=1):
            schedule_quantity = rows[number - 1]["Schedule Qty"] if number <= len(rows) else "0"
            quantity = quantities.get(str(to_amount(schedule_quantity)), to_amount("0"))
            remaining_after = remaining_of(schedule_quantity) - quantity
            checks += check_receive_item(item, f"Popup item {number}", "Received Quantity")
            checks += [
                new_check(f"Popup item {number} Received Quantity", quantity, item.get("Received Quantity", "-"),
                          to_amount(item.get("Received Quantity") or "0") == quantity),
                new_check(f"Popup item {number} Remaining Quantity", remaining_after, item.get("Remaining Quantity", "-"),
                          to_amount(item.get("Remaining Quantity") or "0") == remaining_after),
            ]
        receivable_order_list.get_full_page_screenshot(f'item_remarks_receive_{label}_receive_popup')
        attach_and_assert_checks(checks, f"Receive popup ({label})")

    with allure.step("Confirm the receive"):
        receivable_order_list.confirm_receivable_order()
        receivable_order_list.get_full_page_screenshot(f'item_remarks_receive_{label}_received')
        for schedule_quantity, quantity in quantities.items():
            received_by_schedule[schedule_quantity] = received_by_schedule.get(schedule_quantity, to_amount("0")) + quantity
    receive = {"label": label, "receiver": pin, "challan_no": challan_no, "receive_date": receive_date,
               "challan_date": challan_date,
               "remarks": remarks, "attachment": attachment_path.name if attachment_path else "",
               "quantities": {key: str(value) for key, value in quantities.items()},
               "total_received": str(sum(quantities.values(), to_amount("0")))}
    receives.append(receive)
    return receive


def verify_receive(page, receive, pin, expected_order_status, log_out, check_order_details=True):
    # Why: a confirmed receive must be in the Item Received List (row and status), its item receive details (values,
    # items, Action History) and (check_order_details) the order details (order status, order document); When: after
    # every receive
    orders_list = OrdersListManagement(page)
    item_received_list = ItemReceivedList(page)
    start_date, end_date = date_range()
    label = receive["label"]

    with allure.step(f"Item Received List: search {framework_order_no()} and challan {receive['challan_no']}"):
        orders_list.open_order_management_menu_if_collapsed(item_received_list.item_received_list_submenu)
        item_received_list.goto_received_order_list()
        item_received_list.open_search_panel_if_collapsed(item_received_list.order_number_input)
        item_received_list.fill_date_range(start_date=start_date, end_date=end_date)
        item_received_list.fill_received_order_number(order_no=framework_order_no())
        item_received_list.searched_received_order(challan_no=receive["challan_no"])
        item_received_list.search_button_for_received_item.click()
        item_received_list.wait_for_timeout(3000)
        row_shown = item_received_list.order_list_row(receive["challan_no"]).is_visible()
        row = item_received_list.read_order_list_row(receive["challan_no"]) if row_shown else {}
        receive["item_receive_no"] = row.get("Item Receive #", "")
        receive["status"] = row.get("Status", "")
        print(f"ITEM RECEIVED LIST ROW ({label}):", row)
        checks = [
            new_check("Received challan in Item Received List", receive["challan_no"], "found" if row_shown else "not found",
                      row_shown),
            new_check("Item Receive #", f"{framework_order_no()}-<n>", receive["item_receive_no"] or "-",
                      receive["item_receive_no"].startswith(framework_order_no() + "-")),
            new_check("Order #", framework_order_no(), row.get("Order #", "-"), row.get("Order #") == framework_order_no()),
            new_check("Item Receive Date (= Receive Date)", receive["receive_date"], row.get("Item Receive Date", "-"),
                      row.get("Item Receive Date") == receive["receive_date"]),
            new_check("Vendor Name", order["vendor"], row.get("Vendor Name", "-"),
                      row.get("Vendor Name", "").lower() == order["vendor"].lower()),
            new_check("Challan Date (= receive page Challan Date)", receive["challan_date"], row.get("Challan Date", "-"),
                      row.get("Challan Date") == receive["challan_date"]),
            new_check("Total Received Qty", receive["total_received"], row.get("Total Received Qty", "-"),
                      bool(row) and to_amount(row["Total Received Qty"]) == to_amount(receive["total_received"])),
            new_check("Status", "shown", receive["status"] or "-", bool(receive["status"])),
        ]
        item_received_list.get_full_page_screenshot(f'item_remarks_receive_{label}_item_received_list')
        attach_and_assert_checks(checks, f"Item Received List ({label})")

    with allure.step("Open the item receive details and verify them"):
        item_received_list.open_order_from_list(receive["challan_no"])
        items = item_received_list.read_receive_detail_items()
        history, history_remarks = item_received_list.read_action_history()
        details = {label_name: item_received_list.read_receive_detail(label_name)
                   for label_name in ("Item Receive No", "Order No", "Vendor", "Status")}
        details["Challan No"] = item_received_list.read_receive_detail_challan_no()
        # Action Taken By shows the receiver name (from the schedule Receiver Info), not the PIN
        receiver = receiver_name_of(pin)
        print(f"ITEM RECEIVE DETAILS ({label}):", details, items, history, history_remarks)
        last_action = history[-1] if history else {}
        checks = [
            new_check("Item Receive No.", receive["item_receive_no"], details["Item Receive No"] or "-",
                      details["Item Receive No"] == receive["item_receive_no"]),
            new_check("Order No.", framework_order_no(), details["Order No"] or "-", framework_order_no() in details["Order No"]),
            new_check("Vendor", order["vendor"], details["Vendor"] or "-", details["Vendor"].lower() == order["vendor"].lower()),
            new_check("Status (= Item Received List)", receive["status"], details["Status"] or "-",
                      details["Status"] == receive["status"]),
            new_check("Challan No.", receive["challan_no"], details["Challan No"] or "-", details["Challan No"] == receive["challan_no"]),
            new_check("Received items", len(receive["quantities"]), len(items), len(items) == len(receive["quantities"])),
            new_check("Action History - Item Receive", "Item Receive", last_action.get("Action Name", "-"),
                      last_action.get("Action Name") == "Item Receive"),
            new_check("Action History - taken by the receiver", receiver, last_action.get("Action Taken By", "-"),
                      bool(receiver) and receiver.lower() in last_action.get("Action Taken By", "").lower()),
            new_check("Action History - date (= Receive Date)", receive["receive_date"], last_action.get("Action Taken Date & Time", "-"),
                      last_action.get("Action Taken Date & Time", "").startswith(receive["receive_date"])),
            new_check("Action History - Receive Remarks", receive["remarks"], history_remarks or "-",
                      without_spaces(receive["remarks"]) in without_spaces(history_remarks)),
        ]
        for number, item in enumerate(items, start=1):
            quantity = to_amount(receive["quantities"].get(str(to_amount(item.get("Schedule Qty") or "0")), "0"))
            checks += check_receive_item(item, f"Received item {number}", "Received Qty")
            checks.append(new_check(f"Received item {number} Received Qty (schedule {item.get('Schedule Qty')})", quantity,
                                    item.get("Received Qty", "-"), to_amount(item.get("Received Qty") or "0") == quantity))
        item_received_list.get_full_page_screenshot(f'item_remarks_receive_{label}_item_receive_details')
        attach_and_assert_checks(checks, f"Item receive details ({label})")

    if check_order_details:
        with allure.step("Order No. link: order details in a new tab, order status and order document"):
            with page.context.expect_page() as order_tab_info:
                item_received_list.receive_details_order_link.click()
            order_tab = order_tab_info.value
            order_tab.wait_for_load_state("domcontentloaded")
            order_details_page = OrderDetailsAdministration(order_tab)
            order_details_page.expand_collapsed_cards()
            order_status = order_details_page.read_order_info("Order Status")
            print(f"ORDER STATUS ({label}):", order_status)
            receive["order_status"] = order_status
            order_details_page.get_full_page_screenshot(f'item_remarks_receive_{label}_order_details')
            # The order document is opened with the order initiator logged in to ERP
            log_in_to_erp_as_order_initiator(page)
            print_tab, pdf_url = order_details_page.open_print_document()
            receive["print_url"] = print_tab.url
            order_document = DOWNLOAD_DIR / f"receive_{label}_order_document_{order['order_reference_number'].replace('/', '_')}.pdf"
            order_document.write_bytes(print_tab.context.request.get(pdf_url).body() if pdf_url else b"")
            allure.attach.file(str(order_document), name=f"Order document - {order_document.name}")
            is_pdf = order_document.read_bytes()[:4] == b"%PDF"
            text = OrderDetails.read_order_document_text(order_document) if is_pdf else ""
            allure.attach(text, name=f"Order document text ({label})", attachment_type=allure.attachment_type.TEXT)
            receive["order_document"] = order_document.name
            print_tab.close()
            order_tab.close()
            page.bring_to_front()
            status_ok = (expected_order_status.lower() in order_status.lower()) if expected_order_status != ORDER_STATUS_SETTLED_WORD \
                else ORDER_STATUS_SETTLED_WORD in order_status.lower()
            checks = [
                new_check("Order details Order Status", expected_order_status, order_status or "-", status_ok),
                new_check("Order document downloaded (PDF)", "%PDF", order_document.read_bytes()[:4].decode("latin-1"), is_pdf),
                new_check("Order document Framework Order No.", framework_order_no(),
                          "on the document" if framework_order_no() in text else "not found", framework_order_no() in text),
                new_check("Order document requisition", order["requisition_number"],
                          "on the document" if order["requisition_number"] in text else "not found",
                          order["requisition_number"] in text),
                new_check("Order tabs closed", "all", f"{len(page.context.pages)} tab(s) open", len(page.context.pages) == 1),
            ]
            attach_and_assert_checks(checks, f"Order details and order document ({label})")

    if log_out:
        with allure.step("Log out from Administration"):
            MainNavigationMenu(page).logout_from_administration()
            HomePage(page).get_full_page_screenshot(f'item_remarks_receive_{label}_logout')


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Receivable Order List")
@allure.title("Test_case_1: Order initiator - open and verify the receive page")
@allure.description("Test case 1: Load the acknowledged order (8 items, every schedule received by the order "
                    "initiator), log in as the order initiator, find the framework order in the Receivable Order List, "
                    "open it and verify the receive page (all 8 schedule rows).")
@pytest.mark.order(1)
def test_1_order_initiator_opens_receive_page(page):
    """
    Test case 1: Load the vendor acknowledgement result
    (item_remarks_and_attachment_upload_vendor_acknowledgement_result.json); every schedule is received by the order
    initiator ('test_order_initiator'). Log in, Receivable Order List (row data), View, receive page checks (8 rows:
    product name, specification, remarks, quantities, delivery information, requisition link before the selection).

    All scenario values are read from .env.
    """
    global order
    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa, "test_marketplace_password": marketplace_password,
        "test_order_initiator": order_initiator, "test_user_name": proj_user, "test_env": proj_env,
        "test_receiving_remarks": receiving_remarks,
        "test_proc_admin": proc_admin,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    check_remarks_length("test_receiving_remarks", receiving_remarks)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with allure.step("Step 1: Load the vendor acknowledgement result and the receive plan"):
        order = load_result("item_remarks_and_attachment_upload_vendor_acknowledgement_result",
                            created_by="item_remarks_and_attachment_upload_order_acknowledgement.py")
        assert order.get("framework_order_no"), "The order is not acknowledged (no Framework Order No.)"
        initiator_schedules = schedules_of(order_initiator)
        plan = (f"{order_initiator} (order initiator): schedules {[schedule['Quantity'] for schedule in initiator_schedules]}"
                f" (one full receive per item, attachments {[item['attachment'] or '(none)' for item in order_items()]})")
        print("RECEIVE PLAN:", plan)
        allure.attach(f"Order: {order['order_reference_number']}\nFramework Order No.: {framework_order_no()}\n"
                      f"Vendor: {order['vendor']}\n{plan}", name="Receive plan", attachment_type=allure.attachment_type.TEXT)
        assert len(initiator_schedules) == len(expected_schedules()), \
            "Every schedule must be received by the order initiator (other receiving persons found)"

    log_in_to_administration(page, order_initiator, "item_1")
    open_receive_page(page, order_initiator, "item_1")


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Receivable Order List")
@allure.title("Test_case_2: Receive the first item and verify the receipt (Partially Received)")
@allure.description("Test case 2: The order initiator receives the first item in full (its requisition attachment "
                    "type); the challan is verified in the Item Received List and the item receive details, and the "
                    "order details show Partially Received (order document downloaded once).")
@pytest.mark.order(2)
def test_2_receive_first_item(page):
    """Test case 2: first item: full receive (requisition link after the selection, popup checks) and receipt checks."""
    assert receive_page_checked.get("item_1"), "Test case 1 must pass first: receive page not verified"
    first_item = order_items()[0]
    receive = receive_items(page, order_initiator, "item_1", first_item["attachment"], receiving_remarks,
                            only_item=first_item)
    verify_receive(page, receive, order_initiator, ORDER_STATUS_PARTIALLY_RECEIVED, log_out=False)


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Receivable Order List")
@allure.title("Test_case_3: Receive the middle items one by one and verify each receipt")
@allure.description("Test case 3: Every item between the first and the last is received in full in its own receive "
                    "(its requisition attachment type, none for an item without attachment); every challan is "
                    "verified in the Item Received List and the item receive details.")
@pytest.mark.order(3)
def test_3_receive_middle_items(page):
    """Test case 3: items 2 to n-1: one receive each (receive page, popup, Item Received List, item receive details)."""
    assert any(receive["label"] == "item_1" and receive.get("status") for receive in receives), \
        "Test case 2 must pass first: first item receipt not verified"
    for item in order_items()[1:-1]:
        label = f"item_{item['number']}"
        with allure.step(f"Item {item['number']} ({item['item_code']}): receive {item['quantity']} with "
                         f"attachment {item['attachment'] or '(none)'}"):
            open_receive_page(page, order_initiator, label, full_checks=False)
            receive = receive_items(page, order_initiator, label, item["attachment"], receiving_remarks,
                                    only_item=item, check_links=False)
            verify_receive(page, receive, order_initiator, ORDER_STATUS_PARTIALLY_RECEIVED, log_out=False,
                           check_order_details=False)


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Item Received List")
@allure.title("Test_case_4: Receive the last item and verify the receipt (order settled)")
@allure.description("Test case 4: The last item is received in full; the challan is verified, the order details show "
                    "the settled status (order document downloaded), every schedule is fully received and the order "
                    "initiator logs out.")
@pytest.mark.order(4)
def test_4_receive_last_item(page):
    """Test case 4: last item receive, settled order details and document, every schedule fully received, logout."""
    assert len(receives) == len(order_items()) - 1, "Test case 3 must pass first: not every middle item is received"
    last_item = order_items()[-1]
    label = f"item_{last_item['number']}"
    open_receive_page(page, order_initiator, label, full_checks=False)
    receive = receive_items(page, order_initiator, label, last_item["attachment"], receiving_remarks,
                            only_item=last_item, check_links=False)
    verify_receive(page, receive, order_initiator, ORDER_STATUS_SETTLED_WORD, log_out=True)
    checks = [new_check(f"Schedule {schedule['Quantity']} fully received", schedule["Quantity"],
                        received_by_schedule.get(str(to_amount(schedule["Quantity"])), "0"),
                        remaining_of(schedule["Quantity"]) == 0) for schedule in expected_schedules()]
    attach_and_assert_checks(checks, "Every schedule fully received")


@allure.suite("Item Receive")
@allure.feature("Item Receive List")
@allure.story("Item Receive Details Information")
@allure.title("Test_case_5: Verify the item receives (MRR) in ERP")
@allure.description("Test case 5: In ERP the Item Receive List shows one item receive (MRR) per challan of the "
                    "framework order; every MRR details page shows the framework order and its challan.")
@pytest.mark.order(5)
def test_5_verify_item_receives_in_erp(page):
    """
    Test case 5: ERP item receive (same as marketplace_staging_sanity.py Test case 29) with data checks.

    Steps:
        1. Log in to ERP as the procurement admin ('test_proc_admin', ResetHub) and go to Procurement.
        2. Item Receive > Item Receive List: search the framework order; one MRR per challan.
        3. Open every MRR details: framework order and one of the challans are shown; close the tab.
        4. Exit and log out from ERP.
    """
    global erp_item_receives
    final = receives[-1] if len(receives) == len(order_items()) else None
    assert final and final.get("order_status"), "Test case 4 must pass first: last receipt not verified"
    dashboard_page = DashboardPage(page)
    item_receive_list = ItemReceiveList(page)

    with allure.step(f"Step 1: Log in to ERP as procurement admin {proc_admin}"):
        reset_page = ResetHubPage(page)
        reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=proc_admin))
        dashboard_page.goto_procurement()

    with allure.step(f"Step 2: Search framework order {framework_order_no()} in Item Receive List"):
        ProcurementHomePage(page).goto_item_receive_list()
        item_receive_list.search_item_receive_order(receivable_item=framework_order_no())
        item_receive_list.wait_for_timeout(3000)
        list_text = item_receive_list.list_text()
        mrr_count = item_receive_list.mrr_links().count()
        item_receive_list.get_full_page_screenshot('item_remarks_receive_erp_item_receive_list')
        checks = [new_check("ERP item receives (one MRR per challan)", len(receives), mrr_count, mrr_count == len(receives)),
                  new_check("ERP Item Receive List - framework order", framework_order_no(),
                            "shown" if framework_order_no() in list_text else "not shown", framework_order_no() in list_text)]

    with allure.step("Step 3: Open every MRR details and verify the framework order and the challan"):
        challans_found = []
        for index in range(mrr_count):
            link = item_receive_list.mrr_links().nth(index)
            mrr_no = " ".join(link.inner_text().split())
            with page.context.expect_page() as mrr_tab_info:
                link.click()
            mrr_tab = mrr_tab_info.value
            mrr_tab.wait_for_load_state("domcontentloaded")
            mrr_tab.wait_for_timeout(5000)
            mrr_text = " ".join(mrr_tab.locator("body").inner_text().split())
            ItemReceiveList(mrr_tab).get_full_page_screenshot(f'item_remarks_receive_erp_mrr_{index + 1}')
            challan = next((receive["challan_no"] for receive in receives if receive["challan_no"] in mrr_text), "")
            challans_found.append(challan)
            erp_item_receives[mrr_no] = {"challan_no": challan}
            checks += [
                new_check(f"MRR {mrr_no} - framework order", framework_order_no(),
                          "shown" if framework_order_no() in mrr_text else "not shown", framework_order_no() in mrr_text),
                new_check(f"MRR {mrr_no} - challan of the order", "a challan of the order", challan or "not found", bool(challan)),
            ]
            mrr_tab.close()
            page.bring_to_front()
        checks.append(new_check("Every challan has an MRR", ", ".join(receive["challan_no"] for receive in receives),
                                ", ".join(challans_found) or "-",
                                sorted(challans_found) == sorted(receive["challan_no"] for receive in receives)))
        attach_and_assert_checks(checks, "ERP item receives (MRR)")

    with allure.step("Step 4: Exit and log out from ERP"):
        navigation_bar = MainNavigationBar(page)
        navigation_bar.exit()
        navigation_bar.logout_visible()
        navigation_bar.get_full_page_screenshot('item_remarks_receive_erp_logout')


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Receive Result")
@allure.title("Test_case_6: Save the receive result")
@allure.description("Test case 6: Save the receive result (challans, quantities, statuses, order documents, MRR) for "
                    "the next phase (bill payable).")
@pytest.mark.order(6)
def test_6_save_receive_result(page):
    """
    Test case 6: Save item_remarks_and_attachment_upload_receive_result.json, then assert the requisition link
    checks of the receive page (the requisition link must open the ERP requisition).
    """
    global receive_result
    assert erp_item_receives, "Test case 5 must pass first: ERP item receives not verified"
    with allure.step("Step 1: Save the receive result"):
        receive_result = {**order, "receives": receives, "erp_item_receives": erp_item_receives,
                          "received_by_schedule": {key: str(value) for key, value in received_by_schedule.items()}}
        save_result("item_remarks_and_attachment_upload_receive_result", receive_result)
        allure.attach("\n".join(f"{receive['label']}: {receive['challan_no']} | {receive['total_received']} | "
                                f"{receive.get('status')} | {receive.get('order_status')}" for receive in receives),
                      name="Saved receive result", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Step 2: Assert the requisition link checks of the receive page"):
        print("REQUISITION LINK CHECKS:", requisition_link_checks_of_file or "none")
        attach_and_assert_checks(requisition_link_checks_of_file, "Requisition link of the receive page")
