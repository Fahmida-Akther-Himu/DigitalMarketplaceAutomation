from dotenv import load_dotenv
import os
import re
import base64
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs

import pytest
import allure

load_dotenv()

# Vendor order acknowledgement of the 2 orders approved by
# order_approval/different_vendor_agreement_items_order_approval.py (reads its saved result): one order per vendor
# (order 1: vendor of item 1, order 2: vendor of item 2), each vendor logs in and acknowledges its own order.
# Test case 1: the admin gets both vendor usernames (one login). Test case 2-12: vendor 1 acknowledges order 1
# (until Print, then logout); Test case 13-23: vendor 2 acknowledges order 2 (same steps). Test case 24: ERP login
# once, both framework orders verified. Test case 25: save the result.
# Run in a new browser session: the ERP redirect and the Print document are checked without an ERP login.
# Digital Marketplace
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
# Marketplace admin (vendor username), vendor password (same as the sanity vendor login), ERP procurement admin
# (framework order in ERP), ResetHub environment and ERP address
marketplace_admin = os.getenv("test_order_admin")
vendor_password = os.getenv("test_stg_vendor_pass")
proc_admin = os.getenv("test_proc_admin")
proj_env = os.getenv("test_env")
erp_url = os.getenv("test_url")
# Project root is 3 levels up: testcases/order_acknowledgement/<this file>
DOWNLOAD_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "downloads"

from utils.test_data_store import load_result, save_result
from utils.attachment_rules import same_file_type
from utils.remarks_rules import same_remarks, expected_remarks_display
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails
from pages.digital_marketplace.administration.customers import Customers
from pages.digital_marketplace.administration.vendor_dashboard import VendorDashboard
from pages.digital_marketplace.administration.order_management.orders_list_management import OrdersListManagement
from pages.digital_marketplace.administration.order_management.order_details_administration import \
    OrderDetailsAdministration
from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_order_list import FrameworkOrderListPage
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from brac_digital_marketplace.testcases.order_creation.order_page_links import wait_for_erp_address, close_tabs, \
    framework_link_result
from brac_digital_marketplace.testcases.order_creation.order_details_checks import to_amount, new_check, \
    without_spaces, receiver_of, order_total, numbers_in_text

# Order status after the vendor acknowledgement (business workflow)
VENDOR_ACKNOWLEDGED_STATUS = "Vendor Acknowledged"
# Orders list Shipping status before and after the vendor acknowledgement (business workflow)
SHIPPING_STATUS_BEFORE_ACKNOWLEDGEMENT = "Not yet shipped"
SHIPPING_STATUS_AFTER_ACKNOWLEDGEMENT = "Shipped"
# Framework Order No. values that mean "not generated yet"
NOT_GENERATED_VALUES = ("", "-", "n/a", "null")
NO_PENDING_ACKNOWLEDGEMENT_MESSAGE = "No order is waiting for vendor acknowledgement"

# Approved orders (different_vendor_agreement_items_order_approval_result.json, loaded in Test case 1)
approval_result = {}
# Vendor acknowledgement values of order 1 and order 2 (vendor username, order details, Framework Order No., ...)
acknowledgements = {1: {}, 2: {}}
# Vendor acknowledgement result of both orders for the next test file
vendor_acknowledgement_result = {}


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
    # Why: the saved values of approved order <number> (vendor 1 or 2); When: every test of that order. An order of
    # an item removed from the shopping cart (quantity 0) does not exist: its tests are skipped
    assert approval_result, "Test case 1 must pass first: the order approval result is not loaded"
    order = approval_result["orders"][number - 1]
    if order["removed_from_cart"]:
        pytest.skip(f"Item {number} was removed from the shopping cart (quantity 0): no order {number}")
    return order


def order_numbers():
    # Why: the orders that exist (an item removed from the shopping cart has no order); When: the admin and ERP steps
    # that work on both orders in one login
    return [number for number, order in enumerate(approval_result["orders"], start=1) if not order["removed_from_cart"]]


def reference_of(number):
    # Why: the order reference number of order <number>; When: every vendor step of that order
    return order_of(number)["order_reference_number"]


def saved_product_name(number):
    # Why: the product name ("item name - delivery location") of order <number>, stored from the Active Requisition
    # Product List and carried forward by the order and approval files; When: product checks
    return order_of(number)["requisition_product_name"]


def expected_vendor_remarks(order):
    # Why: blank requisition remarks are integrated as "N/A" / "n/a", but remarks removed in the marketplace shopping
    # cart are always shown blank (business rule); When: vendor product remarks check
    if order["cart_changes"].get("remarks") == "(empty)":
        return ""
    return expected_remarks_display(order["cart_remarks_entered"])


def saved_schedules(number):
    # Why: the Preferred Delivery Schedule rows of approved order <number> (date, location, receiver); When: schedule
    # checks
    return order_of(number)["approval"]["details_after_approval"]["delivery_schedule"]


def receiver_name(receiver_info):
    # Why: the vendor Delivery Info shows the receiver name without the PIN; When: vendor schedule checks.
    # "(00292909) - MD. YUSUF KHAN HRIDOY, Field Organiser, ..." -> "MD. YUSUF KHAN HRIDOY"
    return receiver_info.split(") -", 1)[-1].split(",")[0].strip()


def same_schedule(rows, quantity):
    # Why: schedule rows can be in another order; the row with the same quantity is the same schedule; When: vendor
    # schedule checks
    return next((row for row in rows if to_amount(row.get("Quantity", "0")) == to_amount(quantity)), {})


def check_vendor_order_information(page, number, expected_status):
    # Why: the vendor order details must be approved order <number> (order reference, vendor, status); When: before
    # and after the acknowledgement. Returns (checks, information)
    order = order_of(number)
    details_page = OrderDetailsAdministration(page)
    information = {"Order Status": details_page.read_order_info("Order Status"),
                   "Framework Order No.": details_page.read_order_info("Framework Order"),
                   "Vendor Name": details_page.read_order_info("Vendor Name")}
    print(f"ORDER {number} VENDOR ORDER INFORMATION:", information)
    reference_shown = reference_of(number) in details_page.page_text()
    checks = [
        new_check("Order reference number on the order details", reference_of(number),
                  "shown" if reference_shown else "not shown", reference_shown),
        new_check("Order Status", expected_status, information["Order Status"] or "-",
                  information["Order Status"].lower() == expected_status.lower()),
        new_check("Vendor Name", order["vendor"], information["Vendor Name"] or "-",
                  information["Vendor Name"].lower() == order["vendor"].lower()),
    ]
    return checks, information


def check_vendor_products(page, number):
    # Why: the product and every Preferred Delivery Schedule row must be approved order <number>: product name
    # ("item name - delivery location") = the schedule product name, specification, UoM, quantity, prices, remarks
    # and attachment; When: before and after the acknowledgement. Returns (checks, products, schedules)
    order = order_of(number)
    details_page = OrderDetailsAdministration(page)
    products = [details_page.read_admin_product_row(row) for row in details_page.admin_product_rows()]
    schedules = details_page.read_admin_delivery_schedules()
    print(f"ORDER {number} VENDOR ORDER PRODUCTS:", products)
    print(f"ORDER {number} VENDOR ORDER DELIVERY SCHEDULES:", schedules)
    product = next((row for row in products if row["Agreement item"] == order["item_code"]), {})
    product_name = saved_product_name(number)
    total = order_total({"quantity": order["cart_quantity"], "unit_price": order["unit_price"]})
    has_attachment = bool(order["cart_attachment"])
    checks = [
        new_check("Products (items of the order)", 1, len(products), len(products) == 1),
        new_check("Agreement item", order["item_code"], product.get("Agreement item") or "not found", bool(product)),
        new_check("Master item", order["master_item_code"], product.get("Master item") or "-",
                  product.get("Master item") == order["master_item_code"]),
        new_check("Requisition number", approval_result["requisition_number"], product.get("Requisition") or "-",
                  product.get("Requisition") == approval_result["requisition_number"]),
        new_check("FA No.", order["agreement_number"], product.get("FA No.") or "-",
                  product.get("FA No.") == order["agreement_number"]),
        new_check("Product name (item name - delivery location)", product_name, product.get("Product name") or "-",
                  product.get("Product name") == product_name),
        new_check("Specification", order["specification"], product.get("Specification") or "-",
                  without_spaces(product.get("Specification")) == without_spaces(order["specification"])),
        new_check("Remarks (removed in the cart = blank; blank requisition remarks = N/A)",
                  expected_vendor_remarks(order) or "(blank)", product.get("Remarks") or "(blank)",
                  same_remarks(order["cart_remarks_entered"], product.get("Remarks", "")) if expected_vendor_remarks(order)
                  else not " ".join((product.get("Remarks") or "").split())),
        new_check("Item attachment", "shown" if has_attachment else "not shown",
                  "shown" if product.get("Attachment") else "not shown", product.get("Attachment") == has_attachment),
        new_check("UoM", order["uom"], product.get("UoM") or "-", product.get("UoM") == order["uom"]),
        new_check("Quantity (cart quantity)", order["cart_quantity"], product.get("Quantity") or "-",
                  bool(product) and to_amount(product["Quantity"]) == to_amount(order["cart_quantity"])),
        new_check("Unit Price (Incl. VAT & TAX)", order["unit_price"], product.get("Unit Price") or "-",
                  bool(product) and to_amount(product["Unit Price"]) == to_amount(order["unit_price"])),
        new_check("Total Price (Incl. VAT & TAX) = Qty. x Unit Price", total, product.get("Total Price") or "-",
                  bool(product) and to_amount(product["Total Price"]) == total),
        new_check("Preferred Delivery Schedules", len(order["expected_schedules"]), len(schedules),
                  len(schedules) == len(order["expected_schedules"])),
    ]
    for schedule_number, expected in enumerate(order["expected_schedules"], start=1):
        schedule = same_schedule(schedules, expected["Quantity"])
        saved = same_schedule(saved_schedules(number), expected["Quantity"])
        receiver = receiver_name(receiver_of(saved))
        checks += [
            new_check(f"Schedule {schedule_number} Quantity", expected["Quantity"], schedule.get("Quantity", "not found"),
                      bool(schedule)),
            new_check(f"Schedule {schedule_number} product name (= Products product name)", product_name,
                      schedule.get("Product") or "-", schedule.get("Product") == product_name),
            new_check(f"Schedule {schedule_number} requisition", approval_result["requisition_number"],
                      schedule.get("Requisition") or "-",
                      schedule.get("Requisition") == approval_result["requisition_number"]),
            new_check(f"Schedule {schedule_number} Delivery Date", saved.get("Delivery Date", "-"),
                      schedule.get("Delivery Date") or "-", schedule.get("Delivery Date") == saved.get("Delivery Date")),
            new_check(f"Schedule {schedule_number} Delivery Location", expected["Location"][:60],
                      (schedule.get("Delivery Location") or "-")[:60],
                      without_spaces(expected["Location"]).lower()
                      in without_spaces(schedule.get("Delivery Location")).lower()),
            new_check(f"Schedule {schedule_number} receiving person (Delivery Info)", receiver,
                      schedule.get("Delivery Info") or "-",
                      bool(receiver) and receiver.lower() in schedule.get("Delivery Info", "").lower()),
        ]
    return checks, products, schedules


def check_order_document_text(number, text, label):
    # Why: the order document (vendor Print or ERP Preview) of order <number> must show the order: Framework Order No.,
    # requisition, FA No., item, specification, remarks, UoM, quantity, prices and the delivery places; When: Print
    # and ERP Preview steps
    order = order_of(number)
    numbers = numbers_in_text(text)
    expected_texts = [("Framework Order No.", acknowledgements[number]["framework_order_no"]),
                      ("Requisition number", approval_result["requisition_number"]),
                      ("FA No.", order["agreement_number"]),
                      ("Master item", order["master_item_code"]),
                      ("Agreement item", order["item_code"]),
                      ("Specification", order["specification"]), ("UoM", order["uom"])]
    # Blank cart remarks are shown as "N/A" on the pages; only entered remarks are checked on the document
    if order["cart_remarks_entered"]:
        expected_texts.append(("Remarks", order["cart_remarks_entered"]))
    expected_texts += [(f"Schedule {schedule_number} place", schedule["Location"])
                       for schedule_number, schedule in enumerate(order["expected_schedules"], start=1)]
    checks = []
    for check, value in expected_texts:
        found = without_spaces(value).lower() in without_spaces(text).lower()
        checks.append(new_check(f"{label}: {check}", value[:60], "on the document" if found else "not found", found))
    expected_numbers = [("Quantity", to_amount(order["cart_quantity"])),
                        ("Unit Price", to_amount(order["unit_price"])),
                        ("Total Price (Qty. x Unit Price)", order_total({"quantity": order["cart_quantity"],
                                                                       "unit_price": order["unit_price"]}))]
    for check, value in expected_numbers:
        checks.append(new_check(f"{label}: {check}", value, "on the document" if value in numbers else "not found",
                                value in numbers))
    return checks


def check_framework_link(page, link, label):
    # Why: an FA No. link opens the agreement attachment (downloaded and attached to the report) or the ERP page with a
    # message (existing rule); When: Framework Agreement Number of the agreement information and the product FA No.
    # link. Returns (checks, result)
    with page.context.expect_page() as framework_tab_info:
        OrderDetailsAdministration(page).click_on_btn(link)
    framework_tab = framework_tab_info.value
    framework_tab.wait_for_load_state("domcontentloaded")
    result = framework_link_result(framework_tab, DOWNLOAD_DIR)
    if result.get("downloaded"):
        allure.attach.file(str(DOWNLOAD_DIR / result["downloaded"]), name=f"{label} - {result['downloaded']}")
    close_tabs([framework_tab], page)
    print(f"{label}: {result.get('downloaded') or result.get('message', '')[:80] or result['url']}")
    checks = [new_check(f"{label} (attachment, or ERP message)", "opened",
                        result.get("downloaded") or result.get("message", "")[:80] or result["url"], result["passed"])]
    return checks, result


def check_erp_login_redirect(page, link, name, screenshot_name):
    # Why: a requisition link must open the ERP login page of this environment (the vendor has no ERP login);
    # When: Products and Preferred Delivery Schedule requisition links of the vendor order details
    details_page = OrderDetailsAdministration(page)
    erp_tabs = details_page.open_link_in_new_tabs(link)
    wait_for_erp_address(erp_tabs[0])
    try:
        erp_tabs[0].wait_for_url(lambda url: "/openid-connect/auth" in url, timeout=30000, wait_until="commit")
    except Exception:
        print(f"{name}: the ERP login page address was not shown in 30 seconds")
    erp_tabs[0].bring_to_front()
    opened_url = erp_tabs[0].url
    login_page_shown = RequisitionDetailsInformation(erp_tabs[0]).is_erp_login_page()
    RequisitionDetailsInformation(erp_tabs[0]).get_full_page_screenshot(screenshot_name)
    close_tabs(erp_tabs, page)
    print(f"{name}: {opened_url} (ERP login page: {login_page_shown})")
    erp_host = urlparse(erp_url).netloc
    return [
        new_check(f"{name} opens the ERP login page (requisition not shown)", "ERP login page", opened_url[:120],
                  login_page_shown),
        new_check(f"{name} ERP of this environment", erp_host, opened_url[:120], erp_host in unquote(opened_url)),
        new_check(f"{name} tabs closed", "all", f"{len(erp_tabs)} tab(s) closed", len(page.context.pages) == 1),
    ]


# ---------------- Steps of one order (number = 1 or 2) ----------------

def retrieve_vendor_usernames(page):
    # Why: each vendor logs in with its username from Administration > Customers; the admin logs in once and stores the
    # usernames of the vendors of both orders; When: first test, before the vendors acknowledge
    global approval_result
    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_order_admin": marketplace_admin,
        "test_stg_vendor_pass": vendor_password,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    approval_result = load_result("different_vendor_agreement_items_order_approval_result",
                                  created_by="different_vendor_agreement_items_order_approval.py")
    login_page = LoginPage(page)
    customers_page = Customers(page)

    with allure.step("Step 1: Approved orders of both vendors"):
        for number in order_numbers():
            order = order_of(number)
            approved_status = order["approval"].get("approved_order_status", "")
            print(f"ORDER {number}:", reference_of(number), "|", order["vendor"], "|", approved_status)
            allure.attach(f"Order {number}: {reference_of(number)}\nVendor: {order['vendor']}\nOrder status: {approved_status}",
                          name=f"Approved order {number}", attachment_type=allure.attachment_type.TEXT)
            assert "approved" in approved_status.lower(), f"Order {reference_of(number)} is not approved: {approved_status}"

    with allure.step(f"Step 2: Log in to the Digital Marketplace as admin {marketplace_admin}"):
        # A new session: a previous user may still be logged in
        page.context.clear_cookies()
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_marketplace_login(user_name=marketplace_admin, pass_word=marketplace_password)
        login_page.navigate_to_url(marketplace_url_qa.rstrip("/") + "/Admin")
        customers_page.get_full_page_screenshot('different_vendor_ack_admin_login')

    checks = []
    for number in order_numbers():
        order = order_of(number)
        ack = acknowledgements[number]
        with allure.step(f"Step 3: Order {number}: Customers > Customers: search vendor {order['vendor']} and store its username"):
            # Administration home first: the Customers menu is closed again (clicking it when open would close it)
            login_page.navigate_to_url(marketplace_url_qa.rstrip("/") + "/Admin")
            customers_page.view_customers_list()
            customers_page.search_customer_by_first_name(order["vendor"])
            customers_page.get_full_page_screenshot(f'different_vendor_ack_{number}_customer_search')
            customer_rows = customers_page.get_customer_rows(order["vendor"])
            vendor_rows = [row for row in customer_rows if order["vendor"].lower() in row["User Info"].lower()
                           and "vendors" in row["User Group"].lower()]
            ack["vendor_username"] = vendor_rows[0]["Username"] if vendor_rows else ""
            print(f"ORDER {number} VENDOR USERNAME:", ack["vendor_username"])
            order_checks = [
                new_check(f"Order {number} vendor rows (User Info = order vendor, User Group = Vendors)", 1,
                          len(vendor_rows), len(vendor_rows) == 1),
                new_check(f"Order {number} vendor username", "shown", ack["vendor_username"] or "-",
                          bool(ack["vendor_username"])),
            ]
            customers_page.get_full_page_screenshot(f'different_vendor_ack_{number}_vendor_username')
            allure.attach("\n".join(f"{check}: expected {expected} | actual {actual} | {result}"
                                    for check, expected, actual, result in order_checks),
                          name=f"Order {number} vendor username", attachment_type=allure.attachment_type.TEXT)
            checks += order_checks

    with allure.step("Step 4: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        customers_page.get_full_page_screenshot('different_vendor_ack_admin_logout')
        attach_and_assert_checks(checks, "Vendor usernames of both orders")


def vendor_login(page, number):
    # Why: the vendor of order <number> works on Marketplace Administration; the orders waiting for its
    # acknowledgement are counted; When: first test of each order
    ack = acknowledgements[number]
    order_of(number)
    assert ack.get("vendor_username"), f"Order {number}: vendor username not retrieved"
    login_page = LoginPage(page)
    vendor_dashboard = VendorDashboard(page)

    with allure.step(f"Step 1: Log in as vendor {ack['vendor_username']}"):
        # A new session: the other vendor or the admin may still be logged in (a failed step skips its logout)
        page.context.clear_cookies()
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_vendor_login(user_name=ack["vendor_username"], pass_word=vendor_password)
        page.wait_for_load_state("domcontentloaded")
        vendor_dashboard.get_full_page_screenshot(f'different_vendor_ack_{number}_vendor_login')

    with allure.step("Step 2: Verify the vendor is on Marketplace Administration"):
        vendor_dashboard.print_card_title()
        dashboard_shown = vendor_dashboard.card_title.is_visible()
        checks = [
            new_check("Vendor page (Marketplace Administration)", "/Admin", page.url, "/admin" in page.url.lower()),
            new_check("Pending Acknowledgement Orders list", "shown", "shown" if dashboard_shown else "not shown",
                      dashboard_shown),
        ]
        vendor_dashboard.get_full_page_screenshot(f'different_vendor_ack_{number}_vendor_dashboard')
        attach_and_assert_checks(checks, f"Order {number} vendor login")

    with allure.step("Step 3: Count the orders waiting for the vendor acknowledgement"):
        ack["pending_count_before"] = vendor_dashboard.pending_acknowledgement_count()
        pending_text = (f"Orders waiting for vendor acknowledgement: {ack['pending_count_before']}"
                        if ack["pending_count_before"] else NO_PENDING_ACKNOWLEDGEMENT_MESSAGE)
        print(f"ORDER {number} PENDING ACKNOWLEDGEMENT ORDERS:", pending_text)
        allure.attach(f"Vendor: {ack['vendor_username']}\n{pending_text}", name="Pending vendor acknowledgement orders",
                      attachment_type=allure.attachment_type.TEXT)


def open_details_from_dashboard(page, number):
    # Why: Path 1, Vendor Dashboard > Pending Acknowledgement Orders > View opens order <number>; When: second test of
    # each order
    ack = acknowledgements[number]
    order_of(number)
    assert "pending_count_before" in ack, f"Order {number}: vendor is not logged in"
    vendor_dashboard = VendorDashboard(page)

    with allure.step(f"Step 1: Find order {reference_of(number)} in the Pending Acknowledgement Orders list"):
        order_row = vendor_dashboard.pending_acknowledgement_row(reference_of(number))
        row_shown = order_row.count() > 0
        actions = VendorDashboard.row_actions(order_row) if row_shown else []
        print(f"ORDER {number} DASHBOARD ACTIONS:", actions)
        checks = [new_check("Order in Pending Acknowledgement Orders", reference_of(number),
                            "found" if row_shown else "not found", row_shown)]
        checks += [new_check(f"Dashboard action '{action}'", "shown", "shown" if action in actions else "not shown",
                             action in actions) for action in ("View", "Acknowledge", "Send Back")]
        vendor_dashboard.get_full_page_screenshot(f'different_vendor_ack_{number}_dashboard_order_row')

    with allure.step("Step 2: Click View and verify the order details are opened"):
        if row_shown:
            vendor_dashboard.click_action_for_order(order_reference=reference_of(number))
            page.wait_for_load_state("domcontentloaded")
            vendor_dashboard.wait_for_timeout(3000)
            # A vendor's Administration can keep the Info card collapsed: open it before reading the order details
            OrderDetailsAdministration(page).expand_collapsed_cards()
        ack["order_url"] = page.url
        reference_shown = reference_of(number) in OrderDetailsAdministration(page).page_text()
        checks += [
            new_check("Order details page", "/Admin/Order/Edit/", page.url, "/admin/order/edit/" in page.url.lower()),
            new_check("Order details of the order", reference_of(number), "shown" if reference_shown else "not shown",
                      reference_shown),
        ]
        vendor_dashboard.get_full_page_screenshot(f'different_vendor_ack_{number}_dashboard_order_details')
        attach_and_assert_checks(checks, f"Order {number} Path 1: Vendor Dashboard > View")


def verify_information_before(page, number):
    # Why: before the acknowledgement order <number> has no Framework Order No., the approved status and the
    # Acknowledge and Send Back actions (not clicked); When: third test of each order
    ack = acknowledgements[number]
    order = order_of(number)
    assert ack.get("order_url"), f"Order {number}: order details not opened"

    with allure.step("Step 1-2: Verify the order information and the vendor actions before the acknowledgement"):
        checks, information = check_vendor_order_information(page, number, order["approval"]["approved_order_status"])
        actions = OrderDetailsAdministration(page).visible_actions()
        checks += [
            new_check("Framework Order No. (not generated before the acknowledgement)", "not generated",
                      information["Framework Order No."] or "not generated",
                      information["Framework Order No."].lower() in NOT_GENERATED_VALUES),
            new_check("Order details action 'Acknowledge'", "shown", "shown" if "Acknowledge" in actions else "not shown",
                      "Acknowledge" in actions),
            new_check("Order details action 'Send Back' (not clicked)", "shown",
                      "shown" if "Send Back" in actions else "not shown", "Send Back" in actions),
        ]
        ack["information_before"] = information
        OrderDetailsAdministration(page).get_full_page_screenshot(f'different_vendor_ack_{number}_information_before')
        attach_and_assert_checks(checks, f"Order {number} information before the acknowledgement")


def verify_products_before(page, number):
    # Why: the product, Preferred Delivery Schedule and Framework Agreement Number of order <number> before the
    # acknowledgement (stored for the checks after it); When: fourth test of each order
    ack = acknowledgements[number]
    order = order_of(number)
    assert ack.get("information_before"), f"Order {number}: order information not verified"

    with allure.step("Step 1-2: Verify and store the product and the Preferred Delivery Schedule"):
        checks, products, schedules = check_vendor_products(page, number)
        OrderDetailsAdministration(page).get_full_page_screenshot(f'different_vendor_ack_{number}_products_before')
        attach_and_assert_checks(checks, f"Order {number} product and Preferred Delivery Schedule before the acknowledgement")
        ack["products_before"] = products
        ack["schedules_before"] = schedules
        ack["links"] = {}

    with allure.step("Step 3: Store, click and verify the Framework Agreement Number"):
        details_page = OrderDetailsAdministration(page)
        agreement_number = details_page.read_order_info("Framework Agreement Number")
        agreement_link = details_page.agreement_number_link()
        print(f"ORDER {number} FRAMEWORK AGREEMENT NUMBER:", agreement_number)
        checks = [
            new_check("Framework Agreement Number", order["agreement_number"], agreement_number or "-",
                      agreement_number == order["agreement_number"]),
            new_check("Framework Agreement Number link", "shown", "shown" if agreement_link.count() else "not shown",
                      agreement_link.count() > 0),
        ]
        if agreement_link.count():
            link_checks, result = check_framework_link(page, agreement_link, "Framework Agreement Number link")
            checks += link_checks
            ack["links"]["Framework Agreement Number"] = {**result, "number": agreement_number}
        details_page.get_full_page_screenshot(f'different_vendor_ack_{number}_agreement_number_checked')
        attach_and_assert_checks(checks, f"Order {number} Framework Agreement Number")


def open_details_from_orders_list(page, number):
    # Why: Path 2, Order Management > Orders > View opens the same order details; the Shipping status is
    # "Not yet shipped" before the acknowledgement; When: fifth test of each order
    ack = acknowledgements[number]
    order_of(number)
    assert ack.get("products_before"), f"Order {number}: product not verified"
    orders_list = OrdersListManagement(page)

    with allure.step(f"Step 1: Order Management > Orders: find order {reference_of(number)}"):
        orders_list.goto_orders_list()
        orders_list.open_search_panel_if_closed()
        orders_list.search_order_from_dropdown(order_no=reference_of(number))
        if not orders_list.order_list_row(reference_of(number)).is_visible():
            print("Order not found by its reference: the list is shown without filters")
            orders_list.show_all_orders()
        order_row = orders_list.order_list_row(reference_of(number))
        row_shown = order_row.is_visible()
        actions = VendorDashboard.row_actions(order_row) if row_shown else []
        shipping_status = (orders_list.read_order_list_row(reference_of(number)) if row_shown else {}).get(
            "Shipping status", "")
        print(f"ORDER {number} SHIPPING STATUS BEFORE ACKNOWLEDGEMENT:", shipping_status)
        checks = [new_check("Order in Order Management > Orders", reference_of(number),
                            "found" if row_shown else "not found", row_shown),
                  new_check("Orders list action 'View'", "shown", "shown" if "View" in actions else "not shown",
                            "View" in actions),
                  new_check("Shipping status (before the acknowledgement)", SHIPPING_STATUS_BEFORE_ACKNOWLEDGEMENT,
                            shipping_status or "-",
                            shipping_status.lower() == SHIPPING_STATUS_BEFORE_ACKNOWLEDGEMENT.lower())]
        orders_list.get_full_page_screenshot(f'different_vendor_ack_{number}_orders_list_row')

    with allure.step("Step 2: Click View and verify the same order details are opened"):
        if row_shown:
            orders_list.open_order_from_list(reference_of(number))
            OrderDetailsAdministration(page).expand_collapsed_cards()
        checks.append(new_check("Order details (= Path 1 order details)", ack["order_url"], page.url,
                                page.url.split("?")[0].lower() == ack["order_url"].split("?")[0].lower()))
        orders_list.get_full_page_screenshot(f'different_vendor_ack_{number}_orders_list_order_details')
        attach_and_assert_checks(checks, f"Order {number} Path 2: Order Management > Orders > View")
        ack["orders_list_path_verified"] = True


def verify_requisition_links(page, number):
    # Why: the requisition links of order <number> open the ERP login page (the vendor cannot open the ERP
    # requisition); When: sixth test of each order
    ack = acknowledgements[number]
    order = order_of(number)
    assert ack.get("orders_list_path_verified"), f"Order {number}: Orders list path not verified"
    details_page = OrderDetailsAdministration(page)
    checks = []

    with allure.step("Step 1: Products requisition link opens the ERP login page"):
        for product_number, row in enumerate(details_page.admin_product_rows(), start=1):
            link = details_page.product_requisition_link(row)
            checks.append(new_check(f"Product {product_number} requisition link", approval_result["requisition_number"],
                                    "shown" if link.count() else "not shown", link.count() > 0))
            if link.count():
                checks += check_erp_login_redirect(page, link, f"Product {product_number} requisition link",
                                                   f'different_vendor_ack_{number}_product_requisition_erp')

    with allure.step("Step 2: Preferred Delivery Schedule requisition links open the ERP login page"):
        schedule_links = details_page.schedule_requisition_links()
        checks.append(new_check("Preferred Delivery Schedule requisition links", len(order["expected_schedules"]),
                                len(schedule_links), len(schedule_links) == len(order["expected_schedules"])))
        for schedule_number, link in enumerate(schedule_links, start=1):
            checks += check_erp_login_redirect(page, link, f"Schedule {schedule_number} requisition link",
                                               f'different_vendor_ack_{number}_schedule_{schedule_number}_requisition_erp')
        attach_and_assert_checks(checks, f"Order {number} requisition links (ERP login page)")
        ack["erp_redirect_verified"] = True


def verify_fa_link_and_attachment(page, number):
    # Why: the FA No. link of order <number> opens the agreement attachment (or the ERP page with a message) and the
    # item attachment is the cart attachment (same file type; none when it was removed in the cart); When: seventh
    # test of each order
    ack = acknowledgements[number]
    order = order_of(number)
    assert ack.get("erp_redirect_verified"), f"Order {number}: requisition links not verified"
    details_page = OrderDetailsAdministration(page)
    checks = []

    for product_number, row in enumerate(details_page.admin_product_rows(), start=1):
        with allure.step(f"Step 1: Product {product_number} FA No. link"):
            framework_link = details_page.product_framework_link(row)
            checks.append(new_check(f"Product {product_number} FA No. link", order["agreement_number"],
                                    "shown" if framework_link.count() else "not shown", framework_link.count() > 0))
            if framework_link.count():
                link_checks, result = check_framework_link(page, framework_link, f"Product {product_number} FA No. link")
                checks += link_checks
                ack["links"][f"Product {product_number} FA No."] = result

        with allure.step(f"Step 2: Product {product_number} item attachment"):
            attachment = details_page.product_attachment(row)
            if order["cart_attachment"] and attachment.count():
                saved_file = details_page.save_attachment_from_icon(attachment.first, DOWNLOAD_DIR)
                allure.attach.file(str(saved_file), name=f"Item attachment - {saved_file.name}")
                ack["links"][f"Product {product_number} attachment"] = saved_file.name
                checks.append(new_check(f"Product {product_number} item attachment (same file type as the cart "
                                        f"attachment)", order["cart_attachment"], saved_file.name,
                                        same_file_type(saved_file, order["cart_attachment"])))
            else:
                checks.append(new_check(f"Product {product_number} item attachment",
                                        "shown" if order["cart_attachment"] else "not shown",
                                        "shown" if attachment.count() else "not shown",
                                        bool(attachment.count()) == bool(order["cart_attachment"])))
    details_page.get_full_page_screenshot(f'different_vendor_ack_{number}_fa_and_attachment_checked')
    attach_and_assert_checks(checks, f"Order {number} FA No. link and item attachment")
    ack["fa_and_attachment_verified"] = True


def acknowledge(page, number):
    # Why: Acknowledge > Yes generates the Framework Order No. of order <number>; the Framework Order No. and the
    # Order Status are clicked once to show them; When: eighth test of each order
    ack = acknowledgements[number]
    order_of(number)
    assert ack.get("fa_and_attachment_verified"), f"Order {number}: FA No. link and attachment not verified"
    details_page = OrderDetailsAdministration(page)

    with allure.step(f"Step 1: Acknowledge order {reference_of(number)}"):
        details_page.acknowledge_order()
        details_page.get_full_page_screenshot(f'different_vendor_ack_{number}_acknowledged')

    with allure.step("Step 2: Click the Framework Order No. and the Order Status once and store them"):
        ack["framework_order_no"] = details_page.read_order_info("Framework Order")
        ack["status_after"] = details_page.read_order_info("Order Status")
        if ack["framework_order_no"]:
            details_page.click_order_info_once("Framework Order")
        details_page.click_order_info_once("Order Status")
        details_page.get_full_page_screenshot(f'different_vendor_ack_{number}_framework_order_no_and_status')
        print(f"ORDER {number} FRAMEWORK ORDER NO:", ack["framework_order_no"])
        print(f"ORDER {number} STATUS AFTER ACKNOWLEDGEMENT:", ack["status_after"])
        checks = [
            new_check("Framework Order No. (generated)", "generated", ack["framework_order_no"] or "not generated",
                      ack["framework_order_no"].lower() not in NOT_GENERATED_VALUES),
            new_check("Order Status", VENDOR_ACKNOWLEDGED_STATUS, ack["status_after"] or "-",
                      ack["status_after"].lower() == VENDOR_ACKNOWLEDGED_STATUS.lower()),
        ]
        attach_and_assert_checks(checks, f"Order {number} vendor acknowledgement")


def verify_details_after(page, number):
    # Why: after the acknowledgement order <number> shows the Framework Order No. and Vendor Acknowledged, no
    # Acknowledge / Send Back, and the product and schedule are not changed; When: ninth test of each order
    ack = acknowledgements[number]
    order_of(number)
    assert ack.get("framework_order_no") and ack.get("status_after", "").lower() == VENDOR_ACKNOWLEDGED_STATUS.lower(), \
        f"Order {number}: order not acknowledged"
    details_page = OrderDetailsAdministration(page)

    with allure.step("Step 1: Verify the order information and the actions after the acknowledgement"):
        checks, information = check_vendor_order_information(page, number, VENDOR_ACKNOWLEDGED_STATUS)
        actions = details_page.visible_actions()
        checks += [
            new_check("Framework Order No.", ack["framework_order_no"], information["Framework Order No."] or "-",
                      information["Framework Order No."] == ack["framework_order_no"]),
            new_check("Order details action 'Acknowledge' (after the acknowledgement)", "not shown",
                      "shown" if "Acknowledge" in actions else "not shown", "Acknowledge" not in actions),
            new_check("Order details action 'Send Back' (after the acknowledgement)", "not shown",
                      "shown" if "Send Back" in actions else "not shown", "Send Back" not in actions),
            new_check("Order details action 'Print'", "shown", "shown" if "Print" in actions else "not shown",
                      "Print" in actions),
        ]
        details_page.get_full_page_screenshot(f'different_vendor_ack_{number}_information_after')
        attach_and_assert_checks(checks, f"Order {number} information after the acknowledgement")

    with allure.step("Step 2: Verify the product and the Preferred Delivery Schedule after the acknowledgement"):
        checks, products, schedules = check_vendor_products(page, number)
        checks += [
            new_check("Product (= before the acknowledgement)", "same",
                      "same" if products == ack["products_before"] else "changed", products == ack["products_before"]),
            new_check("Preferred Delivery Schedule (= before the acknowledgement)", "same",
                      "same" if schedules == ack["schedules_before"] else "changed", schedules == ack["schedules_before"]),
        ]
        details_page.get_full_page_screenshot(f'different_vendor_ack_{number}_products_after')
        attach_and_assert_checks(checks, f"Order {number} product and Preferred Delivery Schedule after the acknowledgement")
        ack["details_after"] = {"information": information, "products": products, "delivery_schedule": schedules}


def verify_acknowledged_order_in_lists(page, number):
    # Why: acknowledged order <number> leaves the Pending Acknowledgement Orders list (count - 1) and is found by its
    # Framework Order No. in Orders with Shipping status "Shipped"; When: tenth test of each order
    ack = acknowledgements[number]
    order_of(number)
    assert ack.get("details_after"), f"Order {number}: order details after the acknowledgement not verified"
    vendor_dashboard = VendorDashboard(page)
    orders_list = OrdersListManagement(page)

    with allure.step("Step 1: The order is not in the Pending Acknowledgement Orders list"):
        vendor_dashboard.goto_dashboard()
        page.wait_for_load_state("domcontentloaded")
        vendor_dashboard.print_card_title()
        still_pending = vendor_dashboard.pending_acknowledgement_row(reference_of(number)).count() > 0
        pending_count_after = vendor_dashboard.pending_acknowledgement_count()
        pending_text = (f"Orders waiting for vendor acknowledgement: {pending_count_after}"
                        if pending_count_after else NO_PENDING_ACKNOWLEDGEMENT_MESSAGE)
        print(f"ORDER {number} PENDING ACKNOWLEDGEMENT ORDERS AFTER ACKNOWLEDGEMENT:", pending_text)
        allure.attach(f"Before the acknowledgement: {ack['pending_count_before']}\nAfter the acknowledgement: "
                      f"{pending_text}", name="Pending vendor acknowledgement orders",
                      attachment_type=allure.attachment_type.TEXT)
        checks = [new_check("Order in Pending Acknowledgement Orders (after the acknowledgement)", "not shown",
                            "shown" if still_pending else "not shown", not still_pending),
                  new_check("Pending acknowledgement orders (before - 1)", ack["pending_count_before"] - 1,
                            pending_count_after, pending_count_after == ack["pending_count_before"] - 1)]
        vendor_dashboard.get_full_page_screenshot(f'different_vendor_ack_{number}_dashboard_after')

    with allure.step(f"Step 2: Search framework order {ack['framework_order_no']} in Order Management > Orders"):
        orders_list.goto_orders_list()
        orders_list.open_search_panel_if_closed()
        orders_list.search_order_from_dropdown(order_no=ack["framework_order_no"])
        row_shown = orders_list.order_list_row(ack["framework_order_no"]).is_visible()
        shipping_status = (orders_list.read_order_list_row(ack["framework_order_no"]) if row_shown else {}).get(
            "Shipping status", "")
        print(f"ORDER {number} SHIPPING STATUS AFTER ACKNOWLEDGEMENT:", shipping_status)
        checks += [new_check("Order in Orders list (Framework Order No.)", ack["framework_order_no"],
                             "found" if row_shown else "not found", row_shown),
                   new_check("Shipping status (after the acknowledgement)", SHIPPING_STATUS_AFTER_ACKNOWLEDGEMENT,
                             shipping_status or "-",
                             shipping_status.lower() == SHIPPING_STATUS_AFTER_ACKNOWLEDGEMENT.lower())]
        orders_list.get_full_page_screenshot(f'different_vendor_ack_{number}_orders_list_framework_order')

    with allure.step("Step 3: Open the order details with View"):
        if row_shown:
            orders_list.open_order_from_list(ack["framework_order_no"])
            OrderDetailsAdministration(page).expand_collapsed_cards()
        checks.append(new_check("Order details (= the acknowledged order)", ack["order_url"], page.url,
                                page.url.split("?")[0].lower() == ack["order_url"].split("?")[0].lower()))
        orders_list.get_full_page_screenshot(f'different_vendor_ack_{number}_order_details_again')
        attach_and_assert_checks(checks, f"Order {number} acknowledged order in the vendor lists")
        ack["found_in_list"] = True


def print_order_document(page, number):
    # Why: Print opens the order document of order <number> (ERP) without an ERP login; it is downloaded and verified;
    # the vendor logs out after it; When: eleventh test of each order
    ack = acknowledgements[number]
    order_of(number)
    assert ack.get("found_in_list"), f"Order {number}: acknowledged order not found in the lists"
    details_page = OrderDetailsAdministration(page)
    reference = reference_of(number)

    with allure.step("Step 1: Click Print and download the order document"):
        print_tab = details_page.open_print_tab()
        print_url = print_tab.url
        login_page_shown = RequisitionDetailsInformation(print_tab).is_erp_login_page()
        order_document = OrderDetails.download_order_document(
            print_tab, DOWNLOAD_DIR, f"vendor_order_document_{reference.replace('/', '_')}.pdf")
        allure.attach.file(str(order_document), name=f"Order document - {order_document.name}")
        parameters = {key: values[0] for key, values in parse_qs(urlparse(print_url).query).items()}
        tracking_number = base64.b64decode(parameters.get("trackingNumber", "")).decode("utf-8", "ignore")
        close_tabs([print_tab], page)
        is_pdf = order_document.read_bytes()[:4] == b"%PDF"
        checks = [
            new_check("Order document opened without ERP login", "no ERP login page", print_url[:120],
                      not login_page_shown),
            new_check("Order document on ERP of this environment", urlparse(erp_url).netloc, urlparse(print_url).netloc,
                      urlparse(print_url).netloc == urlparse(erp_url).netloc),
            new_check("Order document downloaded (PDF)", "%PDF", order_document.read_bytes()[:4].decode("latin-1"), is_pdf),
        ]
        if tracking_number:
            checks.append(new_check("Document tracking number (order reference)", reference, tracking_number,
                                    tracking_number == reference))

    with allure.step("Step 2: Verify the order document content"):
        text = OrderDetails.read_order_document_text(order_document) if is_pdf else ""
        allure.attach(text, name="Order document text", attachment_type=allure.attachment_type.TEXT)
        checks += check_order_document_text(number, text, "Vendor Print")
        ack["order_document"] = {"url": print_url, "order_document": order_document.name,
                                 "tracking_number": tracking_number}

    with allure.step("Step 3: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        details_page.get_full_page_screenshot(f'different_vendor_ack_{number}_vendor_logout')
        attach_and_assert_checks(checks, f"Order {number} order document (Print)")


def verify_framework_order_of(page, new_tab, number):
    # Why: the Framework Order No. of order <number> is in the ERP Framework Order List (work order) with its vendor,
    # and the ERP Preview order document does not show "Vendor Acknowledged"; When: ERP test, for each acknowledged
    # order (ERP already logged in). Returns checks
    ack = acknowledgements[number]
    order = order_of(number)
    framework_order_list_page = FrameworkOrderListPage(page)
    framework_order_no = ack["framework_order_no"]

    with allure.step(f"Order {number}: search framework order {framework_order_no} in Framework Order List"):
        framework_order_list_page.search_framework_order(fa_order_no=framework_order_no)
        framework_order_list_page.get_full_page_screenshot(f'different_vendor_ack_{number}_erp_framework_order_search')

    with allure.step(f"Order {number}: open framework order {framework_order_no} details"):
        details_tab = new_tab(lambda p: framework_order_list_page.click_framework_order(framework_order_no=framework_order_no))
        details_tab.wait_for_timeout(5000)
        details_text = " ".join(details_tab.locator("body").inner_text().split())
        RequisitionDetailsInformation(details_tab).get_full_page_screenshot(
            f'different_vendor_ack_{number}_erp_framework_order_details')
        details_url = details_tab.url
        checks = [
            new_check("ERP framework order (work order) in Framework Order List", framework_order_no, "found", True),
            new_check("ERP framework order details - Framework Order No.", framework_order_no,
                      "shown" if framework_order_no in details_text else "not shown", framework_order_no in details_text),
            new_check("ERP framework order details - vendor", order["vendor"],
                      "shown" if order["vendor"].lower() in details_text.lower() else "not shown",
                      order["vendor"].lower() in details_text.lower()),
        ]

    with allure.step(f"Order {number}: click Preview, download and verify the order document (ERP)"):
        preview_tab, pdf_url = FrameworkOrderListPage(details_tab).open_order_preview()
        erp_document = DOWNLOAD_DIR / f"erp_order_document_{reference_of(number).replace('/', '_')}.pdf"
        erp_document.write_bytes(preview_tab.context.request.get(pdf_url).body() if pdf_url else b"")
        allure.attach.file(str(erp_document), name=f"ERP order document - {erp_document.name}")
        preview_tab.close()
        is_pdf = erp_document.read_bytes()[:4] == b"%PDF"
        text = OrderDetails.read_order_document_text(erp_document) if is_pdf else ""
        allure.attach(text, name="ERP order document text", attachment_type=allure.attachment_type.TEXT)
        status_shown = VENDOR_ACKNOWLEDGED_STATUS.lower() in text.lower()
        print(f"ORDER {number} ERP ORDER DOCUMENT:", erp_document.name)
        checks += [
            new_check("ERP order document downloaded (PDF)", "%PDF", erp_document.read_bytes()[:4].decode("latin-1"),
                      is_pdf),
            new_check(f"ERP order document: order status '{VENDOR_ACKNOWLEDGED_STATUS}' not shown", "not shown",
                      "shown" if status_shown else "not shown", not status_shown),
        ]
        checks += check_order_document_text(number, text, "ERP Preview")
        details_tab.close()
        page.bring_to_front()
        allure.attach("\n".join(f"{check}: expected {expected} | actual {actual} | {result}"
                                for check, expected, actual, result in checks),
                      name=f"Order {number} framework order in ERP and order document",
                      attachment_type=allure.attachment_type.TEXT)
        ack["erp_framework_order"] = {"framework_order_no": framework_order_no, "url": details_url,
                                      "order_document": erp_document.name}

    return checks


def verify_framework_orders_in_erp(page, new_tab):
    # Why: after both vendors acknowledged and printed their orders, the procurement admin logs in to ERP once and
    # verifies both framework orders; When: after the last vendor test
    assert proc_admin, "Missing in .env: test_proc_admin"
    dashboard_page = DashboardPage(page)
    acknowledged = [number for number in order_numbers() if acknowledgements[number].get("order_document")]
    checks = [new_check(f"Order {number} acknowledged and printed by its vendor", "yes",
                        "yes" if number in acknowledged else "no", number in acknowledged) for number in order_numbers()]

    with allure.step(f"Step 1: Log in to ERP as procurement admin {proc_admin}"):
        reset_page = ResetHubPage(page)
        reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=proc_admin))
        dashboard_page.goto_procurement()

    for number in acknowledged:
        with allure.step(f"Step 2: Order {number}: framework order {acknowledgements[number]['framework_order_no']} in ERP"):
            ProcurementHomePage(page).navigate_to_framework_order_list()
            checks += verify_framework_order_of(page, new_tab, number)

    with allure.step("Step 3: Exit and log out from ERP"):
        navigation_bar = MainNavigationBar(page)
        navigation_bar.exit()
        navigation_bar.logout_visible()
        navigation_bar.get_full_page_screenshot('different_vendor_ack_proc_admin_logout')
        attach_and_assert_checks(checks, "Framework orders of both vendors in ERP")


def save_acknowledgement_result():
    # Why: the vendor acknowledgement of both orders for the next test file; When: last test, after the ERP checks
    global vendor_acknowledgement_result
    assert approval_result, "Test case 1 must pass first: the order approval result is not loaded"
    not_in_erp = [number for number in order_numbers() if not acknowledgements[number].get("erp_framework_order")]
    assert not not_in_erp, f"Order(s) {not_in_erp}: framework order not verified in ERP"
    with allure.step("Step 1: Save the vendor acknowledgement result"):
        vendor_acknowledgement_result = {
            **approval_result,
            "orders": [{**order, "acknowledgement": acknowledgements[order_number]}
                       for order_number, order in enumerate(approval_result["orders"], start=1)],
        }
        save_result("different_vendor_agreement_items_vendor_acknowledgement_result", vendor_acknowledgement_result)
        allure.attach(
            "\n".join(f"Order {order_number}: {order['order_reference_number'] or '-'} | {order['vendor']} | "
                      f"{acknowledgements[order_number].get('framework_order_no', 'not acknowledged')}"
                      for order_number, order in enumerate(approval_result["orders"], start=1)),
            name="Saved vendor acknowledgement result", attachment_type=allure.attachment_type.TEXT)


# ---------------- Order 1 (vendor of item 1) ----------------

@allure.suite("Administration")
@allure.feature("Customers")
@allure.story("Vendor Username")
@allure.title("Test_case_1: Retrieve the vendor usernames of both orders")
@allure.description("Test case 1: Load the approved orders, log in once as the marketplace admin and store the "
                    "usernames of the vendors of order 1 and order 2 (Customers > Customers).")
@pytest.mark.order(1)
def test_1_retrieve_vendor_usernames_of_both_orders(page):
    """Test case 1: Vendor usernames of both orders from Marketplace Administration (all values from .env)."""
    retrieve_vendor_usernames(page)


@allure.suite("Vendor Dashboard")
@allure.feature("Vendor Login")
@allure.story("Vendor Access")
@allure.title("Test_case_2: Order 1 - vendor login opens Marketplace Administration")
@allure.description("Test case 2: The vendor of order 1 logs in and is on Marketplace Administration; the orders "
                    "waiting for its acknowledgement are counted.")
@pytest.mark.order(2)
def test_2_order_1_vendor_login_opens_administration(page):
    """Test case 2: Order 1 vendor login and pending acknowledgement count."""
    vendor_login(page, 1)


@allure.suite("Vendor Dashboard")
@allure.feature("Pending Acknowledgement Orders")
@allure.story("Order Details Path 1")
@allure.title("Test_case_3: Order 1 - open order details from the vendor dashboard")
@allure.description("Test case 3: Find order 1 in Pending Acknowledgement Orders, verify the actions (not clicked) and "
                    "open the order details with View.")
@pytest.mark.order(3)
def test_3_order_1_open_order_details_from_vendor_dashboard(page):
    """Test case 3: Order 1 Path 1, Vendor Dashboard > View."""
    open_details_from_dashboard(page, 1)


@allure.suite("Vendor Dashboard")
@allure.feature("Order Details")
@allure.story("Order Information Before Acknowledgement")
@allure.title("Test_case_4: Order 1 - verify order information before acknowledgement")
@allure.description("Test case 4: Order 1 has no Framework Order No., the approved status and Acknowledge / Send Back.")
@pytest.mark.order(4)
def test_4_order_1_verify_order_information_before_acknowledgement(page):
    """Test case 4: Order 1 information before the acknowledgement."""
    verify_information_before(page, 1)


@allure.suite("Vendor Dashboard")
@allure.feature("Order Details")
@allure.story("Products Before Acknowledgement")
@allure.title("Test_case_5: Order 1 - verify product, delivery schedule and agreement before acknowledgement")
@allure.description("Test case 5: Verify and store the product, Preferred Delivery Schedule and Framework Agreement "
                    "Number of order 1.")
@pytest.mark.order(5)
def test_5_order_1_verify_products_before_acknowledgement(page):
    """Test case 5: Order 1 product, Preferred Delivery Schedule and Framework Agreement Number."""
    verify_products_before(page, 1)


@allure.suite("Vendor Side")
@allure.feature("Order Management")
@allure.story("Order Details Path 2")
@allure.title("Test_case_6: Order 1 - open order details from Order Management > Orders")
@allure.description("Test case 6: Find order 1 in Orders (Shipping status Not yet shipped) and open the same order "
                    "details with View.")
@pytest.mark.order(6)
def test_6_order_1_open_order_details_from_orders_list(page):
    """Test case 6: Order 1 Path 2, Order Management > Orders > View."""
    open_details_from_orders_list(page, 1)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("ERP Access Restriction")
@allure.title("Test_case_7: Order 1 - requisition links open the ERP login page")
@allure.description("Test case 7: The requisition links of order 1 open the ERP login page of this environment.")
@pytest.mark.order(7)
def test_7_order_1_verify_requisition_links_open_erp_login(page):
    """Test case 7: Order 1 ERP redirect and access restriction."""
    verify_requisition_links(page, 1)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Framework Agreement and Item Attachment")
@allure.title("Test_case_8: Order 1 - verify FA No. link and item attachment")
@allure.description("Test case 8: The FA No. link of order 1 and its item attachment (none when removed in the cart).")
@pytest.mark.order(8)
def test_8_order_1_verify_fa_link_and_item_attachment(page):
    """Test case 8: Order 1 FA No. link and item attachment."""
    verify_fa_link_and_attachment(page, 1)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Acknowledgement")
@allure.title("Test_case_9: Order 1 - acknowledge the order")
@allure.description("Test case 9: Acknowledge > Yes on order 1; store the Framework Order No. and the Order Status.")
@pytest.mark.order(9)
def test_9_order_1_acknowledge_order(page):
    """Test case 9: Order 1 vendor acknowledgement."""
    acknowledge(page, 1)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Details After Acknowledgement")
@allure.title("Test_case_10: Order 1 - verify order details after acknowledgement")
@allure.description("Test case 10: Order 1 shows the Framework Order No. and Vendor Acknowledged, product and schedule "
                    "are not changed.")
@pytest.mark.order(10)
def test_10_order_1_verify_order_details_after_acknowledgement(page):
    """Test case 10: Order 1 details after the acknowledgement."""
    verify_details_after(page, 1)


@allure.suite("Vendor Side")
@allure.feature("Order Management")
@allure.story("Acknowledged Order Search")
@allure.title("Test_case_11: Order 1 - verify acknowledged order in the lists")
@allure.description("Test case 11: Order 1 leaves Pending Acknowledgement Orders and is found by its Framework Order "
                    "No. in Orders (Shipping status Shipped).")
@pytest.mark.order(11)
def test_11_order_1_verify_acknowledged_order_in_lists(page):
    """Test case 11: Order 1 in the vendor lists after the acknowledgement."""
    verify_acknowledged_order_in_lists(page, 1)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Document")
@allure.title("Test_case_12: Order 1 - print and download the order document")
@allure.description("Test case 12: Print opens the order 1 document without an ERP login; download and verify it, then "
                    "log out the vendor.")
@pytest.mark.order(12)
def test_12_order_1_print_and_download_order_document(page):
    """Test case 12: Order 1 order document (Print)."""
    print_order_document(page, 1)


# ---------------- Order 2 (vendor of item 2) ----------------

@allure.suite("Vendor Dashboard")
@allure.feature("Vendor Login")
@allure.story("Vendor Access")
@allure.title("Test_case_13: Order 2 - vendor login opens Marketplace Administration")
@allure.description("Test case 13: The vendor of order 2 logs in and is on Marketplace Administration; the orders "
                    "waiting for its acknowledgement are counted.")
@pytest.mark.order(13)
def test_13_order_2_vendor_login_opens_administration(page):
    """Test case 13: Order 2 vendor login and pending acknowledgement count."""
    vendor_login(page, 2)


@allure.suite("Vendor Dashboard")
@allure.feature("Pending Acknowledgement Orders")
@allure.story("Order Details Path 1")
@allure.title("Test_case_14: Order 2 - open order details from the vendor dashboard")
@allure.description("Test case 14: Find order 2 in Pending Acknowledgement Orders, verify the actions (not clicked) and "
                    "open the order details with View.")
@pytest.mark.order(14)
def test_14_order_2_open_order_details_from_vendor_dashboard(page):
    """Test case 14: Order 2 Path 1, Vendor Dashboard > View."""
    open_details_from_dashboard(page, 2)


@allure.suite("Vendor Dashboard")
@allure.feature("Order Details")
@allure.story("Order Information Before Acknowledgement")
@allure.title("Test_case_15: Order 2 - verify order information before acknowledgement")
@allure.description("Test case 15: Order 2 has no Framework Order No., the approved status and Acknowledge / Send Back.")
@pytest.mark.order(15)
def test_15_order_2_verify_order_information_before_acknowledgement(page):
    """Test case 15: Order 2 information before the acknowledgement."""
    verify_information_before(page, 2)


@allure.suite("Vendor Dashboard")
@allure.feature("Order Details")
@allure.story("Products Before Acknowledgement")
@allure.title("Test_case_16: Order 2 - verify product, delivery schedule and agreement before acknowledgement")
@allure.description("Test case 16: Verify and store the product, Preferred Delivery Schedule and Framework Agreement "
                    "Number of order 2.")
@pytest.mark.order(16)
def test_16_order_2_verify_products_before_acknowledgement(page):
    """Test case 16: Order 2 product, Preferred Delivery Schedule and Framework Agreement Number."""
    verify_products_before(page, 2)


@allure.suite("Vendor Side")
@allure.feature("Order Management")
@allure.story("Order Details Path 2")
@allure.title("Test_case_17: Order 2 - open order details from Order Management > Orders")
@allure.description("Test case 17: Find order 2 in Orders (Shipping status Not yet shipped) and open the same order "
                    "details with View.")
@pytest.mark.order(17)
def test_17_order_2_open_order_details_from_orders_list(page):
    """Test case 17: Order 2 Path 2, Order Management > Orders > View."""
    open_details_from_orders_list(page, 2)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("ERP Access Restriction")
@allure.title("Test_case_18: Order 2 - requisition links open the ERP login page")
@allure.description("Test case 18: The requisition links of order 2 open the ERP login page of this environment.")
@pytest.mark.order(18)
def test_18_order_2_verify_requisition_links_open_erp_login(page):
    """Test case 18: Order 2 ERP redirect and access restriction."""
    verify_requisition_links(page, 2)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Framework Agreement and Item Attachment")
@allure.title("Test_case_19: Order 2 - verify FA No. link and item attachment")
@allure.description("Test case 19: The FA No. link of order 2 and its item attachment (none when removed in the cart).")
@pytest.mark.order(19)
def test_19_order_2_verify_fa_link_and_item_attachment(page):
    """Test case 19: Order 2 FA No. link and item attachment."""
    verify_fa_link_and_attachment(page, 2)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Acknowledgement")
@allure.title("Test_case_20: Order 2 - acknowledge the order")
@allure.description("Test case 20: Acknowledge > Yes on order 2; store the Framework Order No. and the Order Status.")
@pytest.mark.order(20)
def test_20_order_2_acknowledge_order(page):
    """Test case 20: Order 2 vendor acknowledgement."""
    acknowledge(page, 2)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Details After Acknowledgement")
@allure.title("Test_case_21: Order 2 - verify order details after acknowledgement")
@allure.description("Test case 21: Order 2 shows the Framework Order No. and Vendor Acknowledged, product and schedule "
                    "are not changed.")
@pytest.mark.order(21)
def test_21_order_2_verify_order_details_after_acknowledgement(page):
    """Test case 21: Order 2 details after the acknowledgement."""
    verify_details_after(page, 2)


@allure.suite("Vendor Side")
@allure.feature("Order Management")
@allure.story("Acknowledged Order Search")
@allure.title("Test_case_22: Order 2 - verify acknowledged order in the lists")
@allure.description("Test case 22: Order 2 leaves Pending Acknowledgement Orders and is found by its Framework Order "
                    "No. in Orders (Shipping status Shipped).")
@pytest.mark.order(22)
def test_22_order_2_verify_acknowledged_order_in_lists(page):
    """Test case 22: Order 2 in the vendor lists after the acknowledgement."""
    verify_acknowledged_order_in_lists(page, 2)


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Document")
@allure.title("Test_case_23: Order 2 - print and download the order document")
@allure.description("Test case 23: Print opens the order 2 document without an ERP login; download and verify it, then "
                    "log out the vendor.")
@pytest.mark.order(23)
def test_23_order_2_print_and_download_order_document(page):
    """Test case 23: Order 2 order document (Print)."""
    print_order_document(page, 2)


# ---------------- ERP and result (both orders) ----------------

@allure.suite("Purchase Order")
@allure.feature("Framework Order")
@allure.story("Framework Order List")
@allure.title("Test_case_24: Verify the framework orders of both vendors in ERP")
@allure.description("Test case 24: The procurement admin logs in to ERP once; the Framework Order No. of order 1 and "
                    "order 2 are in the ERP Framework Order List; the ERP Preview documents do not show Vendor "
                    "Acknowledged.")
@pytest.mark.order(24)
def test_24_verify_framework_orders_in_erp(page, new_tab):
    """Test case 24: Both framework orders and their ERP Preview documents (one ERP login)."""
    verify_framework_orders_in_erp(page, new_tab)


@allure.suite("Vendor Side")
@allure.feature("Order Acknowledgement")
@allure.story("Vendor Acknowledgement Result")
@allure.title("Test_case_25: Save the vendor acknowledgement result")
@allure.description("Test case 25: Save the vendor acknowledgement result of both orders.")
@pytest.mark.order(25)
def test_25_save_vendor_acknowledgement_result(page):
    """Test case 25: Save the vendor acknowledgement result (different_vendor_agreement_items_vendor_acknowledgement_result.json)."""
    save_acknowledgement_result()
