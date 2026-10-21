from dotenv import load_dotenv
import os
import re
import base64
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs

import pytest
import allure

load_dotenv()

# Vendor order acknowledgement of the order approved by
# order_approval/item_remarks_and_attachment_upload_order_approval.py (reads its saved result).
# Order of 8 items of one framework agreement and one vendor (items 1-7 with an attachment, item 8 without attachment
# and with 500 character remarks), one auto generated delivery schedule per item.
# Run in a new browser session: the ERP redirect (Test case 7) and the Print document (Test case 12) are checked
# without an ERP login.
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
from utils.remarks_rules import same_remarks
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


# Order status after the vendor acknowledgement (business workflow)
VENDOR_ACKNOWLEDGED_STATUS = "Vendor Acknowledged"
# Orders list Shipping status before and after the vendor acknowledgement (business workflow)
SHIPPING_STATUS_BEFORE_ACKNOWLEDGEMENT = "Not yet shipped"
SHIPPING_STATUS_AFTER_ACKNOWLEDGEMENT = "Shipped"
# Framework Order No. values that mean "not generated yet"
# Shipping status check after the acknowledgement (Shipped, depends on the system cut-off date): reported in Test
# case 11 and asserted at the end of Test case 14 so the journey continues
known_issue_checks = []
NOT_GENERATED_VALUES = ("", "-", "n/a", "null")

# Approved order (item_remarks_and_attachment_upload_order_approval_result.json) and vendor username (Test case 1)
vendor_order = {}
vendor_username = ''
# Orders waiting for the vendor acknowledgement on the vendor dashboard (Test case 2 and 11)
pending_acknowledgement_count_before = None
NO_PENDING_ACKNOWLEDGEMENT_MESSAGE = "No order is waiting for vendor acknowledgement"
# Vendor order details before the acknowledgement (Test case 3-8)
vendor_order_url = ''
information_before_acknowledgement = {}
products_before_acknowledgement = []
schedules_before_acknowledgement = []
orders_list_path_verified = False
erp_redirect_checks = []
vendor_order_links = {}
# Acknowledgement (Test case 9-12)
framework_order_no = ''
status_after_acknowledgement = ''
details_after_acknowledgement = {}
acknowledged_order_found_in_list = False
vendor_order_document = {}
# ERP framework (work) order (Test case 13) and the vendor result for the next test file (Test case 14)
erp_framework_order = {}
vendor_acknowledgement_result = {}


def vendor_order_reference():
    # Why: the order reference number of the approved order; When: every vendor test
    return vendor_order["order_reference_number"]


def order_items():
    # Why: the 8 items of the approved order (item code, master item, specification, remarks, attachment, UoM,
    # quantity, prices); When: product, schedule and order document checks
    return vendor_order["items"]


def items_total():
    # Why: the order total is the sum of the item totals (Qty. x Unit Price); When: order document checks
    return sum((to_amount(item["total_price"]) for item in order_items()), Decimal("0.00"))


def saved_product_name(item):
    # Why: the product name ("item name - delivery location") of an item of the approved order details, e.g.
    # "([FWI049375] - BYA FR Skin Coated - Project Site )" -> "BYA FR Skin Coated - Project Site"; When: vendor
    # product checks
    agreement_item = vendor_order["details_after_approval"]["products"][f"item {item['number']}"]["Agreement item"]
    match = re.match(r"^\(\s*\[\w+\]\s*-\s*(.*?)\s*\)$", agreement_item)
    return match.group(1) if match else agreement_item


def receiver_name(receiver_info):
    # Why: the vendor Delivery Info shows the receiver name without the PIN; When: vendor schedule checks.
    # "(00292909) - MD. YUSUF KHAN HRIDOY, Field Organiser, ..." -> "MD. YUSUF KHAN HRIDOY"
    return receiver_info.split(") -", 1)[-1].split(",")[0].strip()


def same_schedule(rows, quantity):
    # Why: schedule rows can be in another order; the row with the same quantity is the same schedule; When: vendor
    # schedule checks
    return next((row for row in rows if to_amount(row.get("Quantity", "0")) == to_amount(quantity)), {})


def check_vendor_order_information(page, expected_status):
    # Why: the vendor order details must be the approved order (order reference, vendor, status); When: before and
    # after the acknowledgement. Returns (checks, information)
    details_page = OrderDetailsAdministration(page)
    information = {"Order Status": details_page.read_order_info("Order Status"),
                   "Framework Order No.": details_page.read_order_info("Framework Order"),
                   "Vendor Name": details_page.read_order_info("Vendor Name")}
    print("VENDOR ORDER INFORMATION:", information)
    reference_shown = vendor_order_reference() in details_page.page_text()
    checks = [
        new_check("Order reference number on the order details", vendor_order_reference(),
                  "shown" if reference_shown else "not shown", reference_shown),
        new_check("Order Status", expected_status, information["Order Status"] or "-",
                  information["Order Status"].lower() == expected_status.lower()),
        new_check("Vendor Name", vendor_order["vendor"], information["Vendor Name"] or "-",
                  information["Vendor Name"].lower() == vendor_order["vendor"].lower()),
    ]
    return checks, information


def check_vendor_products(page):
    # Why: every product and Preferred Delivery Schedule row must be the approved order: for each item the product
    # name ("item name - delivery location") = its schedule product name, specification, UoM, quantity, prices, remarks
    # and attachment; When: before and after the acknowledgement. Returns (checks, products, schedules)
    details_page = OrderDetailsAdministration(page)
    products = [details_page.read_admin_product_row(row) for row in details_page.admin_product_rows()]
    schedules = details_page.read_admin_delivery_schedules()
    print("VENDOR ORDER PRODUCTS:", products)
    print("VENDOR ORDER DELIVERY SCHEDULES:", schedules)
    checks = [
        new_check("Products (items of the order)", len(order_items()), len(products), len(products) == len(order_items())),
        new_check("Preferred Delivery Schedules (one per item)", len(order_items()), len(schedules),
                  len(schedules) == len(order_items())),
    ]
    for item in order_items():
        number = item["number"]
        product = next((row for row in products if row["Agreement item"] == item["item_code"]), {})
        product_name = saved_product_name(item)
        total = to_amount(item["total_price"])
        has_attachment = bool(item["attachment"])
        checks += [
            new_check(f"Item {number} Agreement item", item["item_code"], product.get("Agreement item") or "not found",
                      bool(product)),
            new_check(f"Item {number} Master item", item["master_item_code"], product.get("Master item") or "-",
                      product.get("Master item") == item["master_item_code"]),
            new_check(f"Item {number} Requisition number", vendor_order["requisition_number"],
                      product.get("Requisition") or "-", product.get("Requisition") == vendor_order["requisition_number"]),
            new_check(f"Item {number} FA No.", vendor_order["agreement_number"], product.get("FA No.") or "-",
                      product.get("FA No.") == vendor_order["agreement_number"]),
            new_check(f"Item {number} Product name (item name - delivery location)", product_name,
                      product.get("Product name") or "-", product.get("Product name") == product_name),
            new_check(f"Item {number} Specification", item["specification"], product.get("Specification") or "-",
                      without_spaces(product.get("Specification")) == without_spaces(item["specification"])),
            new_check(f"Item {number} Remarks", item["remarks"][:60], (product.get("Remarks") or "-")[:60],
                      same_remarks(item["remarks"], product.get("Remarks", ""))),
            new_check(f"Item {number} Item attachment", "shown" if has_attachment else "not shown",
                      "shown" if product.get("Attachment") else "not shown", product.get("Attachment") == has_attachment),
            new_check(f"Item {number} UoM", item["uom"], product.get("UoM") or "-", product.get("UoM") == item["uom"]),
            new_check(f"Item {number} Quantity", item["quantity"], product.get("Quantity") or "-",
                      bool(product) and to_amount(product["Quantity"]) == to_amount(item["quantity"])),
            new_check(f"Item {number} Unit Price (Incl. VAT & TAX)", item["unit_price"], product.get("Unit Price") or "-",
                      bool(product) and to_amount(product["Unit Price"]) == to_amount(item["unit_price"])),
            new_check(f"Item {number} Total Price (Incl. VAT & TAX) = Qty. x Unit Price", total,
                      product.get("Total Price") or "-", bool(product) and to_amount(product["Total Price"]) == total),
        ]
        # The item schedule: same quantity as the item (one auto generated schedule per item)
        schedule = same_schedule(schedules, item["quantity"])
        saved = same_schedule(vendor_order["details_after_approval"]["delivery_schedule"], item["quantity"])
        receiver = receiver_name(receiver_of(saved))
        checks += [
            new_check(f"Item {number} schedule Quantity", item["quantity"], schedule.get("Quantity", "not found"),
                      bool(schedule)),
            new_check(f"Item {number} schedule product name (= Products product name)", product_name,
                      schedule.get("Product") or "-", schedule.get("Product") == product_name),
            new_check(f"Item {number} schedule requisition", vendor_order["requisition_number"],
                      schedule.get("Requisition") or "-", schedule.get("Requisition") == vendor_order["requisition_number"]),
            new_check(f"Item {number} schedule Delivery Date", saved.get("Delivery Date", "-"),
                      schedule.get("Delivery Date") or "-", schedule.get("Delivery Date") == saved.get("Delivery Date")),
            new_check(f"Item {number} schedule Delivery Location", vendor_order["delivery_address"],
                      schedule.get("Delivery Location") or "-",
                      without_spaces(vendor_order["delivery_address"]).lower()
                      in without_spaces(schedule.get("Delivery Location")).lower()),
            new_check(f"Item {number} schedule receiving person (Delivery Info)", receiver,
                      schedule.get("Delivery Info") or "-",
                      bool(receiver) and receiver.lower() in schedule.get("Delivery Info", "").lower()),
        ]
    return checks, products, schedules


def check_order_document_text(text, label):
    # Why: the order document (vendor Print or ERP Preview) must show the order: Framework Order No., requisition, FA
    # No., delivery place and for each item the master item, agreement item, specification, remarks, UoM, quantity
    # and prices, and the Grand Total; When: Test case 12 and 13
    numbers = numbers_in_text(text)
    expected_texts = [("Framework Order No.", framework_order_no),
                      ("Requisition number", vendor_order["requisition_number"]),
                      ("FA No.", vendor_order["agreement_number"]),
                      ("Delivery place (requisition delivery address)", vendor_order["delivery_address"])]
    expected_numbers = [("Grand Total (sum of the items)", items_total())]
    for item in order_items():
        number = item["number"]
        expected_texts += [(f"Item {number} Master item", item["master_item_code"]),
                           (f"Item {number} Agreement item", item["item_code"]),
                           (f"Item {number} Specification", item["specification"]),
                           (f"Item {number} Remarks", item["remarks"]),
                           (f"Item {number} UoM", item["uom"])]
        expected_numbers += [(f"Item {number} Quantity", to_amount(item["quantity"])),
                             (f"Item {number} Unit Price", to_amount(item["unit_price"])),
                             (f"Item {number} Total Price (Qty. x Unit Price)", to_amount(item["total_price"]))]
    checks = []
    for check, value in expected_texts:
        found = without_spaces(value).lower() in without_spaces(text).lower()
        checks.append(new_check(f"{label}: {check}", value[:60], "on the document" if found else "not found", found))
    for check, value in expected_numbers:
        checks.append(new_check(f"{label}: {check}", value, "on the document" if value in numbers else "not found",
                                value in numbers))
    return checks


def attach_known_issue_checks(checks, title):
    # Why: the Shipping status check must not stop the next tests; it is reported now and asserted at the end of the
    # file; When: Shipping status after the acknowledgement (expected "Shipped")
    allure.attach("\n".join(f"{check}: expected {expected} | actual {actual} | {result}"
                            for check, expected, actual, result in checks),
                  name=title, attachment_type=allure.attachment_type.TEXT)
    known_issue_checks.extend(check for check in checks if check[3] == "FAIL")


def check_framework_link(page, link, label):
    # Why: an FA No. link opens the agreement attachment (downloaded and attached to the report) or the ERP page with a
    # message (existing rule); When: Framework Agreement Number of the agreement information (Test case 5) and the
    # product FA No. links (Test case 8). Returns (checks, result)
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


@allure.suite("Administration")
@allure.feature("Customers")
@allure.story("Vendor Username")
@allure.title("Test_case_1: Retrieve the order vendor username")
@allure.description("Test case 1: Log in as the marketplace admin, search the order vendor in Customers > Customers, "
                    "verify the vendor row and store the vendor username for the vendor login.")
@pytest.mark.order(1)
def test_1_retrieve_order_vendor_username(page):
    """
    Test case 1: Vendor username from Marketplace Administration (same as marketplace_staging_sanity.py Test case 19).

    Steps:
        1. Load the approved order (item_remarks_and_attachment_upload_order_approval_result.json) in 'vendor_order'.
        2. Log in to the Digital Marketplace as the admin ('test_order_admin') and open Administration.
        3. Customers > Customers: search the order vendor by name.
        4. Verify the vendor row (User Info has the vendor name, User Group has Vendors) and store its Username in
           'vendor_username'.
        5. Log out from Administration.

    All scenario values are read from .env.
    """
    global vendor_order, vendor_username
    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_order_admin": marketplace_admin,
        "test_stg_vendor_pass": vendor_password,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    login_page = LoginPage(page)
    customers_page = Customers(page)

    # Step 1: Approved order
    with allure.step("Step 1: Load the order approval result"):
        vendor_order = load_result("item_remarks_and_attachment_upload_order_approval_result",
                                   created_by="item_remarks_and_attachment_upload_order_approval.py")
        print("ORDER REFERENCE NUMBER:", vendor_order_reference())
        print("ORDER VENDOR:", vendor_order["vendor"])
        print("ORDER STATUS:", vendor_order["order_status"])
        allure.attach(f"Order: {vendor_order_reference()}\nVendor: {vendor_order['vendor']}\n"
                      f"Order status: {vendor_order['order_status']}", name="Approved order",
                      attachment_type=allure.attachment_type.TEXT)
        assert "approved" in vendor_order["order_status"].lower(), \
            f"Order {vendor_order_reference()} is not approved: {vendor_order['order_status']}"

    # Step 2: Admin login and Administration
    with allure.step(f"Step 2: Log in to the Digital Marketplace as admin {marketplace_admin}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_marketplace_login(user_name=marketplace_admin, pass_word=marketplace_password)
        login_page.navigate_to_url(marketplace_url_qa.rstrip("/") + "/Admin")
        customers_page.get_full_page_screenshot('remarks_vendor_ack_admin_login')

    # Step 3: Customers > Customers, search the vendor
    with allure.step(f"Step 3: Customers > Customers: search vendor {vendor_order['vendor']}"):
        customers_page.view_customers_list()
        customers_page.search_customer_by_first_name(vendor_order["vendor"])
        customers_page.get_full_page_screenshot('remarks_vendor_ack_customer_search')

    # Step 4: Verify the vendor row and store the username
    with allure.step("Step 4: Verify the vendor row and store the vendor username"):
        customer_rows = customers_page.get_customer_rows(vendor_order["vendor"])
        vendor_rows = [row for row in customer_rows if vendor_order["vendor"].lower() in row["User Info"].lower()
                       and "vendors" in row["User Group"].lower()]
        vendor_username = vendor_rows[0]["Username"] if vendor_rows else ""
        print("CUSTOMER ROWS:", customer_rows)
        print("VENDOR USERNAME:", vendor_username)
        checks = [
            new_check("Vendor rows (User Info = order vendor, User Group = Vendors)", 1, len(vendor_rows),
                      len(vendor_rows) == 1),
            new_check("Vendor username", "shown", vendor_username or "-", bool(vendor_username)),
            new_check("Vendor User Info", vendor_order["vendor"], vendor_rows[0]["User Info"] if vendor_rows else "-",
                      bool(vendor_rows)),
        ]
        customers_page.get_full_page_screenshot('remarks_vendor_ack_vendor_username')
        attach_and_assert_checks(checks, "Order vendor username")

    # Step 5: Log out from Administration
    with allure.step("Step 5: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        customers_page.get_full_page_screenshot('remarks_vendor_ack_admin_logout')


@allure.suite("Vendor Dashboard")
@allure.feature("Vendor Login")
@allure.story("Vendor Access")
@allure.title("Test_case_2: Vendor login opens Marketplace Administration")
@allure.description("Test case 2: Log in as the order vendor with the vendor login: the vendor is taken to the "
                    "Marketplace Administration (vendor dashboard).")
@pytest.mark.order(2)
def test_2_vendor_login_opens_administration(page):
    """
    Test case 2: Vendor login. Uses the vendor username of Test case 1.

    Steps:
        1. Log in with the vendor login ('vendor_username', 'test_stg_vendor_pass').
        2. Verify the vendor is on Marketplace Administration (/Admin) with the Pending Acknowledgement Orders list.
        3. Count the orders waiting for the vendor acknowledgement ('pending_acknowledgement_count_before'); with no
           order the report shows "No order is waiting for vendor acknowledgement".
        No logout: Test case 3 continues in the vendor session. No ERP login is done for the vendor.
    """
    global pending_acknowledgement_count_before
    assert vendor_username, "Test case 1 must pass first: no vendor username"
    login_page = LoginPage(page)
    vendor_dashboard = VendorDashboard(page)

    # Step 1: Vendor login
    with allure.step(f"Step 1: Log in as vendor {vendor_username}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_vendor_login(user_name=vendor_username, pass_word=vendor_password)
        page.wait_for_load_state("domcontentloaded")
        vendor_dashboard.get_full_page_screenshot('remarks_vendor_ack_vendor_login')

    # Step 2: Marketplace Administration
    with allure.step("Step 2: Verify the vendor is on Marketplace Administration"):
        vendor_dashboard.print_card_title()
        vendor_dashboard.print_table_data()
        dashboard_shown = vendor_dashboard.card_title.is_visible()
        checks = [
            new_check("Vendor page (Marketplace Administration)", "/Admin", page.url, "/admin" in page.url.lower()),
            new_check("Pending Acknowledgement Orders list", "shown", "shown" if dashboard_shown else "not shown",
                      dashboard_shown),
        ]
        vendor_dashboard.get_full_page_screenshot('remarks_vendor_ack_vendor_dashboard')
        attach_and_assert_checks(checks, "Vendor login")

    # Step 3: Orders waiting for the vendor acknowledgement
    with allure.step("Step 3: Count the orders waiting for the vendor acknowledgement"):
        pending_acknowledgement_count_before = vendor_dashboard.pending_acknowledgement_count()
        pending_text = (f"Orders waiting for vendor acknowledgement: {pending_acknowledgement_count_before}"
                        if pending_acknowledgement_count_before else NO_PENDING_ACKNOWLEDGEMENT_MESSAGE)
        print("PENDING ACKNOWLEDGEMENT ORDERS:", pending_text)
        allure.attach(f"Vendor: {vendor_username}\n{pending_text}", name="Pending vendor acknowledgement orders",
                      attachment_type=allure.attachment_type.TEXT)
        vendor_dashboard.get_full_page_screenshot('remarks_vendor_ack_pending_count_before')


@allure.suite("Vendor Dashboard")
@allure.feature("Pending Acknowledgement Orders")
@allure.story("Order Details Path 1")
@allure.title("Test_case_3: Open order details from the vendor dashboard")
@allure.description("Test case 3: Find the order in the Pending Acknowledgement Orders list, verify the vendor "
                    "actions (View, Acknowledge, Send Back; not clicked) and open the order details with View.")
@pytest.mark.order(3)
def test_3_open_order_details_from_vendor_dashboard(page):
    """
    Test case 3: Path 1, Vendor Dashboard > Pending Acknowledgement Orders > View.

    Steps:
        1. Find the order reference number in the Pending Acknowledgement Orders list and read its actions
           (Acknowledge and Send Back are not clicked).
        2. Click View and verify the order details of the order are opened; store the order details address.
    """
    global vendor_order_url
    assert vendor_username, "Test case 1 must pass first: no vendor username"
    vendor_dashboard = VendorDashboard(page)

    # Step 1: Order row and its actions
    with allure.step(f"Step 1: Find order {vendor_order_reference()} in the Pending Acknowledgement Orders list"):
        order_row = vendor_dashboard.pending_acknowledgement_row(vendor_order_reference())
        row_shown = order_row.count() > 0
        actions = VendorDashboard.row_actions(order_row) if row_shown else []
        print("DASHBOARD ORDER ACTIONS:", actions)
        checks = [new_check("Order in Pending Acknowledgement Orders", vendor_order_reference(),
                            "found" if row_shown else "not found", row_shown)]
        checks += [new_check(f"Dashboard action '{action}'", "shown", "shown" if action in actions else "not shown",
                             action in actions) for action in ("View", "Acknowledge", "Send Back")]
        vendor_dashboard.get_full_page_screenshot('remarks_vendor_ack_dashboard_order_row')

    # Step 2: View > order details
    with allure.step("Step 2: Click View and verify the order details are opened"):
        if row_shown:
            vendor_dashboard.click_action_for_order(order_reference=vendor_order_reference())
            page.wait_for_load_state("domcontentloaded")
            vendor_dashboard.wait_for_timeout(3000)
        vendor_order_url = page.url
        print("VENDOR ORDER DETAILS:", vendor_order_url)
        reference_shown = vendor_order_reference() in OrderDetailsAdministration(page).page_text()
        checks += [
            new_check("Order details page", "/Admin/Order/Edit/", vendor_order_url, "/admin/order/edit/" in vendor_order_url.lower()),
            new_check("Order details of the order", vendor_order_reference(), "shown" if reference_shown else "not shown",
                      reference_shown),
        ]
        vendor_dashboard.get_full_page_screenshot('remarks_vendor_ack_dashboard_order_details')
        attach_and_assert_checks(checks, "Path 1: Vendor Dashboard > View")


@allure.suite("Vendor Dashboard")
@allure.feature("Order Details")
@allure.story("Order Information Before Acknowledgement")
@allure.title("Test_case_4: Verify order information before acknowledgement")
@allure.description("Test case 4: Before the acknowledgement the Framework Order No. is not generated, the status is "
                    "the approved status and the Acknowledge and Send Back actions are shown (not clicked).")
@pytest.mark.order(4)
def test_4_verify_order_information_before_acknowledgement(page):
    """
    Test case 4: Order information before the acknowledgement. Continues on the order details of Test case 3.

    Steps:
        1. Order reference number, Order Status (= approved status) and Vendor Name; store the information.
        2. Framework Order No. is not generated; Acknowledge and Send Back are shown (not clicked).
    """
    global information_before_acknowledgement
    assert vendor_order_url, "Test case 3 must pass first: order details not opened"

    # Step 1-2: Order information and actions
    with allure.step("Step 1-2: Verify the order information and the vendor actions before the acknowledgement"):
        checks, information = check_vendor_order_information(page, vendor_order["order_status"])
        actions = OrderDetailsAdministration(page).visible_actions()
        print("FRAMEWORK ORDER NO. BEFORE ACKNOWLEDGEMENT:", information["Framework Order No."] or "not generated")
        print("ORDER STATUS BEFORE ACKNOWLEDGEMENT:", information["Order Status"])
        print("ORDER DETAILS ACTIONS:", actions)
        checks += [
            new_check("Framework Order No. (not generated before the acknowledgement)", "not generated",
                      information["Framework Order No."] or "not generated",
                      information["Framework Order No."].lower() in NOT_GENERATED_VALUES),
            new_check("Order details action 'Acknowledge'", "shown", "shown" if "Acknowledge" in actions else "not shown",
                      "Acknowledge" in actions),
            new_check("Order details action 'Send Back' (not clicked)", "shown",
                      "shown" if "Send Back" in actions else "not shown", "Send Back" in actions),
        ]
        information_before_acknowledgement = information
        OrderDetailsAdministration(page).get_full_page_screenshot('remarks_vendor_ack_information_before')
        attach_and_assert_checks(checks, "Order information before the acknowledgement")


@allure.suite("Vendor Dashboard")
@allure.feature("Order Details")
@allure.story("Products Before Acknowledgement")
@allure.title("Test_case_5: Verify products and delivery schedule before acknowledgement")
@allure.description("Test case 5: Read every product (product name 'item name - delivery location', specification) "
                    "and Preferred Delivery Schedule row, verify them against the approved order and store them.")
@pytest.mark.order(5)
def test_5_verify_products_before_acknowledgement(page):
    """
    Test case 5: Products and Preferred Delivery Schedule before the acknowledgement. Continues on the order details.

    Steps:
        1. Every product row: master item, requisition, FA No., agreement item, product name, specification, remarks,
           attachment, UoM, quantity, unit price and total price = the approved order; store the products.
        2. Every Preferred Delivery Schedule row: product name (= Products product name), requisition, quantity,
           delivery date, location and receiving person = the approved order; store the schedules.
        3. Agreement information: store the Framework Agreement Number (= the order FA No.), click it and verify it
           as the Products FA No. link (agreement attachment downloaded, or the ERP page with a message).
    """
    global products_before_acknowledgement, schedules_before_acknowledgement
    assert information_before_acknowledgement, "Test case 4 must pass first: order information not verified"

    # Step 1-2: Products and Preferred Delivery Schedule
    with allure.step("Step 1-2: Verify and store the products and the Preferred Delivery Schedule"):
        checks, products, schedules = check_vendor_products(page)
        allure.attach("\n".join(" | ".join(f"{key}: {value}" for key, value in row.items()) for row in products + schedules),
                      name="Products and Preferred Delivery Schedule (before acknowledgement)",
                      attachment_type=allure.attachment_type.TEXT)
        OrderDetailsAdministration(page).get_full_page_screenshot('remarks_vendor_ack_products_before')
        attach_and_assert_checks(checks, "Products and Preferred Delivery Schedule before the acknowledgement")
        products_before_acknowledgement = products
        schedules_before_acknowledgement = schedules

    # Step 3: Framework Agreement Number of the agreement information
    with allure.step("Step 3: Store, click and verify the Framework Agreement Number"):
        details_page = OrderDetailsAdministration(page)
        agreement_number = details_page.read_order_info("Framework Agreement Number")
        agreement_link = details_page.agreement_number_link()
        print("FRAMEWORK AGREEMENT NUMBER:", agreement_number)
        checks = [
            new_check("Framework Agreement Number", vendor_order["agreement_number"], agreement_number or "-",
                      agreement_number == vendor_order["agreement_number"]),
            new_check("Framework Agreement Number link", "shown", "shown" if agreement_link.count() else "not shown",
                      agreement_link.count() > 0),
        ]
        if agreement_link.count():
            link_checks, result = check_framework_link(page, agreement_link, "Framework Agreement Number link")
            checks += link_checks
            vendor_order_links["Framework Agreement Number"] = {**result, "number": agreement_number}
        details_page.get_full_page_screenshot('remarks_vendor_ack_agreement_number_checked')
        attach_and_assert_checks(checks, "Framework Agreement Number (agreement information)")


@allure.suite("Vendor Side")
@allure.feature("Order Management")
@allure.story("Order Details Path 2")
@allure.title("Test_case_6: Open order details from Order Management > Orders")
@allure.description("Test case 6: Find the order in Order Management > Orders (search, or the list without filters), "
                    "verify its actions (not clicked) and open the same order details with View.")
@pytest.mark.order(6)
def test_6_open_order_details_from_orders_list(page):
    """
    Test case 6: Path 2, Order Management > Orders > View.

    Steps:
        1. Order Management > Orders; search the order reference number (when it is not found, the list is shown
           without filters), read the actions of the order row (not clicked) and verify the Shipping status is
           "Not yet shipped".
        2. Click View: the same order details as Path 1 are opened.
    """
    global orders_list_path_verified
    assert products_before_acknowledgement, "Test case 5 must pass first: products not verified"
    orders_list = OrdersListManagement(page)

    # Step 1: Orders list and the order row
    with allure.step(f"Step 1: Order Management > Orders: find order {vendor_order_reference()}"):
        orders_list.goto_orders_list()
        orders_list.open_search_panel_if_closed()
        orders_list.search_order_from_dropdown(order_no=vendor_order_reference())
        if not orders_list.order_list_row(vendor_order_reference()).is_visible():
            print("Order not found by its reference: the list is shown without filters")
            orders_list.show_all_orders()
        order_row = orders_list.order_list_row(vendor_order_reference())
        row_shown = order_row.is_visible()
        actions = VendorDashboard.row_actions(order_row) if row_shown else []
        row_values = orders_list.read_order_list_row(vendor_order_reference()) if row_shown else {}
        shipping_status = row_values.get("Shipping status", "")
        print("ORDERS LIST ACTIONS:", actions)
        print("SHIPPING STATUS BEFORE ACKNOWLEDGEMENT:", shipping_status)
        checks = [new_check("Order in Order Management > Orders", vendor_order_reference(),
                            "found" if row_shown else "not found", row_shown),
                  new_check("Orders list action 'View'", "shown", "shown" if "View" in actions else "not shown",
                            "View" in actions),
                  new_check("Shipping status (before the acknowledgement)", SHIPPING_STATUS_BEFORE_ACKNOWLEDGEMENT,
                            shipping_status or "-",
                            shipping_status.lower() == SHIPPING_STATUS_BEFORE_ACKNOWLEDGEMENT.lower())]
        orders_list.get_full_page_screenshot('remarks_vendor_ack_orders_list_row')

    # Step 2: View > the same order details
    with allure.step("Step 2: Click View and verify the same order details are opened"):
        if row_shown:
            orders_list.open_order_from_list(vendor_order_reference())
        checks.append(new_check("Order details (= Path 1 order details)", vendor_order_url, page.url,
                                page.url.split("?")[0].lower() == vendor_order_url.split("?")[0].lower()))
        details_actions = OrderDetailsAdministration(page).visible_actions()
        checks += [new_check(f"Order details action '{action}' (not clicked)", "shown",
                             "shown" if action in details_actions else "not shown", action in details_actions)
                   for action in ("Acknowledge", "Send Back")]
        orders_list.get_full_page_screenshot('remarks_vendor_ack_orders_list_order_details')
        attach_and_assert_checks(checks, "Path 2: Order Management > Orders > View")
        orders_list_path_verified = True


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("ERP Access Restriction")
@allure.title("Test_case_7: Requisition links open the ERP login page")
@allure.description("Test case 7: The requisition number links of Products and Preferred Delivery Schedule open the "
                    "ERP login page of this environment (the vendor cannot open the ERP requisition).")
@pytest.mark.order(7)
def test_7_verify_requisition_links_open_erp_login(page):
    """
    Test case 7: ERP redirect and access restriction. Continues on the order details of Test case 6.

    Steps:
        1. Every product requisition link opens the ERP login page of this environment; the tabs are closed.
        2. Every Preferred Delivery Schedule requisition link opens the ERP login page; the tabs are closed and the
           order details are shown again.
    """
    global erp_redirect_checks
    assert orders_list_path_verified, "Test case 6 must pass first: Orders list path not verified"
    details_page = OrderDetailsAdministration(page)
    checks = []

    # Step 1: Products requisition links
    with allure.step("Step 1: Products requisition links open the ERP login page"):
        for number, row in enumerate(details_page.admin_product_rows(), start=1):
            link = details_page.product_requisition_link(row)
            checks.append(new_check(f"Product {number} requisition link", vendor_order["requisition_number"],
                                    "shown" if link.count() else "not shown", link.count() > 0))
            if link.count():
                checks += check_erp_login_redirect(page, link, f"Product {number} requisition link",
                                                   f'remarks_vendor_ack_product_{number}_requisition_erp')

    # Step 2: Preferred Delivery Schedule requisition links
    with allure.step("Step 2: Preferred Delivery Schedule requisition links open the ERP login page"):
        schedule_links = details_page.schedule_requisition_links()
        checks.append(new_check("Preferred Delivery Schedule requisition links (one per item)", len(order_items()),
                                len(schedule_links), len(schedule_links) == len(order_items())))
        for number, link in enumerate(schedule_links, start=1):
            checks += check_erp_login_redirect(page, link, f"Schedule {number} requisition link",
                                               f'remarks_vendor_ack_schedule_{number}_requisition_erp')
        details_page.get_full_page_screenshot('remarks_vendor_ack_requisition_links_checked')
        erp_redirect_checks = checks
        attach_and_assert_checks(checks, "Requisition links (ERP login page)")


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Framework Agreement and Item Attachment")
@allure.title("Test_case_8: Verify FA No. link and item attachment")
@allure.description("Test case 8: The FA No. link of every product opens the agreement attachment (or the ERP page "
                    "with a message, existing rule) and the item attachment is downloaded (same file type as the cart "
                    "attachment).")
@pytest.mark.order(8)
def test_8_verify_fa_link_and_item_attachment(page):
    """
    Test case 8: FA No. link and item attachment. Continues on the order details of Test case 7.

    Steps:
        1. Every product FA No. link: the agreement attachment is downloaded, or the ERP page shows a message.
        2. Every product item attachment is downloaded (same file type as the uploaded attachment of its item);
           an item without attachment shows no attachment.
    """
    global vendor_order_links
    assert erp_redirect_checks, "Test case 7 must pass first: requisition links not verified"
    details_page = OrderDetailsAdministration(page)
    checks = []

    for number, row in enumerate(details_page.admin_product_rows(), start=1):
        # Step 1: FA No. link
        with allure.step(f"Step 1: Product {number} FA No. link"):
            framework_link = details_page.product_framework_link(row)
            checks.append(new_check(f"Product {number} FA No. link", vendor_order["agreement_number"],
                                    "shown" if framework_link.count() else "not shown", framework_link.count() > 0))
            if framework_link.count():
                link_checks, result = check_framework_link(page, framework_link, f"Product {number} FA No. link")
                checks += link_checks
                vendor_order_links[f"Product {number} FA No."] = result

        # Step 2: Item attachment (the item of this product row, found by its agreement item)
        with allure.step(f"Step 2: Product {number} item attachment"):
            agreement_item = details_page.read_admin_product_row(row)["Agreement item"]
            item = next((item for item in order_items() if item["item_code"] == agreement_item), {})
            expected_attachment = item.get("attachment", "")
            attachment = details_page.product_attachment(row)
            if expected_attachment and attachment.count():
                saved_file = details_page.save_attachment_from_icon(attachment.first, DOWNLOAD_DIR)
                allure.attach.file(str(saved_file), name=f"Item attachment - {saved_file.name}")
                vendor_order_links[f"Product {number} attachment"] = saved_file.name
                checks.append(new_check(f"Product {number} ({agreement_item}) item attachment (same file type as "
                                        f"the uploaded attachment)", expected_attachment, saved_file.name,
                                        same_file_type(saved_file, expected_attachment)))
            else:
                checks.append(new_check(f"Product {number} ({agreement_item}) item attachment",
                                        "shown" if expected_attachment else "not shown",
                                        "shown" if attachment.count() else "not shown",
                                        bool(attachment.count()) == bool(expected_attachment)))
    details_page.get_full_page_screenshot('remarks_vendor_ack_fa_and_attachment_checked')
    attach_and_assert_checks(checks, "FA No. link and item attachment")


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Acknowledgement")
@allure.title("Test_case_9: Acknowledge the order")
@allure.description("Test case 9: Acknowledge > Yes on the order details; click the Framework Order No. and the "
                    "Order Status once to show them, and store both values.")
@pytest.mark.order(9)
def test_9_acknowledge_order(page):
    """
    Test case 9: Vendor acknowledgement. Continues on the order details of Test case 8.

    Steps:
        1. Acknowledge > Yes.
        2. Click the Framework Order No. once and the Order Status once (show them); store 'framework_order_no' and
           'status_after_acknowledgement'.
    """
    global framework_order_no, status_after_acknowledgement
    assert vendor_order_links, "Test case 8 must pass first: FA No. link and attachment not verified"
    details_page = OrderDetailsAdministration(page)

    # Step 1: Acknowledge > Yes
    with allure.step(f"Step 1: Acknowledge order {vendor_order_reference()}"):
        details_page.acknowledge_order()
        details_page.get_full_page_screenshot('remarks_vendor_ack_acknowledged')

    # Step 2: Framework Order No. and Order Status (one click each)
    with allure.step("Step 2: Click the Framework Order No. and the Order Status once and store them"):
        framework_order_no = details_page.read_order_info("Framework Order")
        status_after_acknowledgement = details_page.read_order_info("Order Status")
        if framework_order_no:
            details_page.click_order_info_once("Framework Order")
            details_page.get_full_page_screenshot('remarks_vendor_ack_framework_order_no_clicked')
        details_page.click_order_info_once("Order Status")
        details_page.get_full_page_screenshot('remarks_vendor_ack_order_status_clicked')
        print("FRAMEWORK ORDER NO:", framework_order_no)
        print("ORDER STATUS AFTER ACKNOWLEDGEMENT:", status_after_acknowledgement)
        checks = [
            new_check("Framework Order No. (generated)", "generated", framework_order_no or "not generated",
                      framework_order_no.lower() not in NOT_GENERATED_VALUES),
            new_check("Order Status", VENDOR_ACKNOWLEDGED_STATUS, status_after_acknowledgement or "-",
                      status_after_acknowledgement.lower() == VENDOR_ACKNOWLEDGED_STATUS.lower()),
        ]
        attach_and_assert_checks(checks, "Vendor acknowledgement")


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Details After Acknowledgement")
@allure.title("Test_case_10: Verify order details after acknowledgement")
@allure.description("Test case 10: After the acknowledgement the order information shows the Framework Order No. and "
                    "Vendor Acknowledged, Acknowledge and Send Back are not shown, and products and schedule are not "
                    "changed.")
@pytest.mark.order(10)
def test_10_verify_order_details_after_acknowledgement(page):
    """
    Test case 10: Order details after the acknowledgement. Continues on the order details of Test case 9.

    Steps:
        1. Order information: status Vendor Acknowledged, Framework Order No. (= Test case 9), vendor; Acknowledge
           and Send Back are not shown, Print is shown.
        2. Products and Preferred Delivery Schedule = the approved order and = before the acknowledgement.
    """
    global details_after_acknowledgement
    assert framework_order_no and VENDOR_ACKNOWLEDGED_STATUS.lower() == status_after_acknowledgement.lower(), \
        "Test case 9 must pass first: order not acknowledged"
    details_page = OrderDetailsAdministration(page)

    # Step 1: Order information and actions
    with allure.step("Step 1: Verify the order information and the actions after the acknowledgement"):
        checks, information = check_vendor_order_information(page, VENDOR_ACKNOWLEDGED_STATUS)
        actions = details_page.visible_actions()
        checks += [
            new_check("Framework Order No.", framework_order_no, information["Framework Order No."] or "-",
                      information["Framework Order No."] == framework_order_no),
            new_check("Order details action 'Acknowledge' (after the acknowledgement)", "not shown",
                      "shown" if "Acknowledge" in actions else "not shown", "Acknowledge" not in actions),
            new_check("Order details action 'Send Back' (after the acknowledgement)", "not shown",
                      "shown" if "Send Back" in actions else "not shown", "Send Back" not in actions),
            new_check("Order details action 'Print'", "shown", "shown" if "Print" in actions else "not shown",
                      "Print" in actions),
        ]
        details_page.get_full_page_screenshot('remarks_vendor_ack_information_after')
        attach_and_assert_checks(checks, "Order information after the acknowledgement")

    # Step 2: Products and Preferred Delivery Schedule
    with allure.step("Step 2: Verify the products and the Preferred Delivery Schedule after the acknowledgement"):
        checks, products, schedules = check_vendor_products(page)
        checks += [
            new_check("Products (= before the acknowledgement)", "same", "same" if products == products_before_acknowledgement
                      else "changed", products == products_before_acknowledgement),
            new_check("Preferred Delivery Schedule (= before the acknowledgement)", "same",
                      "same" if schedules == schedules_before_acknowledgement else "changed",
                      schedules == schedules_before_acknowledgement),
        ]
        details_page.get_full_page_screenshot('remarks_vendor_ack_products_after')
        attach_and_assert_checks(checks, "Products and Preferred Delivery Schedule after the acknowledgement")
        details_after_acknowledgement = {"information": information, "products": products, "delivery_schedule": schedules}


@allure.suite("Vendor Side")
@allure.feature("Order Management")
@allure.story("Acknowledged Order Search")
@allure.title("Test_case_11: Verify acknowledged order in the lists")
@allure.description("Test case 11: The acknowledged order is not in the Pending Acknowledgement Orders list, is found "
                    "by its Framework Order No. in Order Management > Orders and opens the same order details.")
@pytest.mark.order(11)
def test_11_verify_acknowledged_order_in_lists(page):
    """
    Test case 11: Acknowledged order in the vendor lists.

    Steps:
        1. Dashboard: the order is not in the Pending Acknowledgement Orders list and the number of orders waiting
           for the vendor acknowledgement is one less than in Test case 2.
        2. Order Management > Orders: search the Framework Order No. (dropdown), verify the order row and the
           Shipping status is "Shipped".
        3. View: the same order details are opened.
    """
    global acknowledged_order_found_in_list
    assert details_after_acknowledgement, "Test case 10 must pass first: order details after acknowledgement not verified"
    vendor_dashboard = VendorDashboard(page)
    orders_list = OrdersListManagement(page)

    # Step 1: Not in the Pending Acknowledgement Orders list
    with allure.step("Step 1: The order is not in the Pending Acknowledgement Orders list"):
        vendor_dashboard.goto_dashboard()
        page.wait_for_load_state("domcontentloaded")
        vendor_dashboard.print_card_title()
        still_pending = vendor_dashboard.pending_acknowledgement_row(vendor_order_reference()).count() > 0
        pending_count_after = vendor_dashboard.pending_acknowledgement_count()
        pending_text = (f"Orders waiting for vendor acknowledgement: {pending_count_after}"
                        if pending_count_after else NO_PENDING_ACKNOWLEDGEMENT_MESSAGE)
        print("PENDING ACKNOWLEDGEMENT ORDERS AFTER ACKNOWLEDGEMENT:", pending_text)
        allure.attach(f"Before the acknowledgement: {pending_acknowledgement_count_before}\n"
                      f"After the acknowledgement: {pending_text}", name="Pending vendor acknowledgement orders",
                      attachment_type=allure.attachment_type.TEXT)
        checks = [new_check("Order in Pending Acknowledgement Orders (after the acknowledgement)", "not shown",
                            "shown" if still_pending else "not shown", not still_pending),
                  new_check("Pending acknowledgement orders (before - 1)", pending_acknowledgement_count_before - 1,
                            pending_count_after, pending_count_after == pending_acknowledgement_count_before - 1)]
        vendor_dashboard.get_full_page_screenshot('remarks_vendor_ack_dashboard_after')

    # Step 2: Orders list search by the Framework Order No.
    with allure.step(f"Step 2: Search framework order {framework_order_no} in Order Management > Orders"):
        orders_list.goto_orders_list()
        orders_list.open_search_panel_if_closed()
        orders_list.search_order_from_dropdown(order_no=framework_order_no)
        row_shown = orders_list.order_list_row(framework_order_no).is_visible()
        row_values = orders_list.read_order_list_row(framework_order_no) if row_shown else {}
        shipping_status = row_values.get("Shipping status", "")
        print("SHIPPING STATUS AFTER ACKNOWLEDGEMENT:", shipping_status)
        checks.append(new_check("Order in Orders list (Framework Order No.)", framework_order_no,
                                "found" if row_shown else "not found", row_shown))
        # Business rule "Shipped" after the acknowledgement (system cut-off date): the check is reported here and
        # asserted at the end of Test case 14
        attach_known_issue_checks([new_check("Shipping status (after the acknowledgement)",
                                             SHIPPING_STATUS_AFTER_ACKNOWLEDGEMENT, shipping_status or "-",
                                             shipping_status.lower() == SHIPPING_STATUS_AFTER_ACKNOWLEDGEMENT.lower())],
                                  "Shipping status after the acknowledgement")
        orders_list.get_full_page_screenshot('remarks_vendor_ack_orders_list_framework_order')

    # Step 3: View > the same order details
    with allure.step("Step 3: Open the order details with View"):
        if row_shown:
            orders_list.open_order_from_list(framework_order_no)
        checks.append(new_check("Order details (= the acknowledged order)", vendor_order_url, page.url,
                                page.url.split("?")[0].lower() == vendor_order_url.split("?")[0].lower()))
        orders_list.get_full_page_screenshot('remarks_vendor_ack_order_details_again')
        attach_and_assert_checks(checks, "Acknowledged order in the vendor lists")
        acknowledged_order_found_in_list = True


@allure.suite("Vendor Side")
@allure.feature("Order Details")
@allure.story("Order Document")
@allure.title("Test_case_12: Print and download the order document")
@allure.description("Test case 12: Print opens the order document (ERP) without an ERP login; download it and verify "
                    "it against the order, then log out the vendor.")
@pytest.mark.order(12)
def test_12_print_and_download_order_document(page):
    """
    Test case 12: Order document. Continues on the order details of Test case 11.

    Steps:
        1. Click Print: the order document opens without the ERP login page; download it (PDF).
        2. Verify the document: Framework Order No., requisition, FA No., master item, agreement item, specification,
           remarks, UoM, quantity, unit price, total and the delivery places.
        3. Log out from Administration.
    """
    global vendor_order_document
    assert acknowledged_order_found_in_list, "Test case 11 must pass first: acknowledged order not found"
    details_page = OrderDetailsAdministration(page)
    reference = vendor_order_reference()

    # Step 1: Print and download
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
        details_page.get_full_page_screenshot('remarks_vendor_ack_print')
        checks = [
            new_check("Order document opened without ERP login", "no ERP login page", print_url[:120],
                      not login_page_shown),
            new_check("Order document on ERP of this environment", urlparse(erp_url).netloc, urlparse(print_url).netloc,
                      urlparse(print_url).netloc == urlparse(erp_url).netloc),
            new_check("Order document downloaded (PDF)", "%PDF", order_document.read_bytes()[:4].decode("latin-1"),
                      order_document.read_bytes()[:4] == b"%PDF"),
        ]
        if tracking_number:
            checks.append(new_check("Document tracking number (order reference)", reference, tracking_number,
                                    tracking_number == reference))

    # Step 2: Document content
    with allure.step("Step 2: Verify the order document content"):
        text = OrderDetails.read_order_document_text(order_document) if checks[2][3] == "PASS" else ""
        allure.attach(text, name="Order document text", attachment_type=allure.attachment_type.TEXT)
        checks += check_order_document_text(text, "Vendor Print")
        vendor_order_document = {"url": print_url, "order_document": order_document.name,
                                 "tracking_number": tracking_number}

    # Step 3: Vendor logout (checks are asserted after the logout)
    with allure.step("Step 3: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        details_page.get_full_page_screenshot('remarks_vendor_ack_vendor_logout')
        attach_and_assert_checks(checks, "Order document (Print)")


@allure.suite("Purchase Order")
@allure.feature("Framework Order")
@allure.story("Framework Order List")
@allure.title("Test_case_13: Verify the framework order in ERP")
@allure.description("Test case 13: The Framework Order No. generated by the acknowledgement is in the ERP Framework "
                    "Order List (work order) and its details show the order vendor.")
@pytest.mark.order(13)
def test_13_verify_framework_order_in_erp(page, new_tab):
    """
    Test case 13: ERP integration (same as marketplace_staging_sanity.py Test case 22).

    Steps:
        1. Log in to ERP as the procurement admin ('test_proc_admin', ResetHub) and go to Procurement.
        2. Framework Order List: search the Framework Order No.
        3. Open the framework order details: Framework Order No. and vendor are shown.
        4. Click Preview: download and store the marketplace order document, verify it against the order and verify
           the order status "Vendor Acknowledged" is not shown on it; close the tabs.
        5. Exit and log out from ERP.
    """
    global erp_framework_order
    assert vendor_order_document, "Test case 12 must pass first: order document not verified"
    assert proc_admin, "Missing in .env: test_proc_admin"
    dashboard_page = DashboardPage(page)
    framework_order_list_page = FrameworkOrderListPage(page)

    # Step 1: ERP login as the procurement admin
    with allure.step(f"Step 1: Log in to ERP as procurement admin {proc_admin}"):
        reset_page = ResetHubPage(page)
        reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=proc_admin))
        dashboard_page.goto_procurement()
        dashboard_page.get_full_page_screenshot('remarks_vendor_ack_proc_admin_dashboard')

    # Step 2: Framework Order List
    with allure.step(f"Step 2: Search framework order {framework_order_no} in Framework Order List"):
        ProcurementHomePage(page).navigate_to_framework_order_list()
        framework_order_list_page.search_framework_order(fa_order_no=framework_order_no)
        framework_order_list_page.get_full_page_screenshot('remarks_vendor_ack_erp_framework_order_search')

    # Step 3: Framework order details
    with allure.step(f"Step 3: Open framework order {framework_order_no} details"):
        details_tab = new_tab(lambda p: framework_order_list_page.click_framework_order(framework_order_no=framework_order_no))
        details_tab.wait_for_timeout(5000)
        details_text = " ".join(details_tab.locator("body").inner_text().split())
        RequisitionDetailsInformation(details_tab).get_full_page_screenshot('remarks_vendor_ack_erp_framework_order_details')
        details_url = details_tab.url
        checks = [
            new_check("ERP framework order (work order) in Framework Order List", framework_order_no, "found", True),
            new_check("ERP framework order details - Framework Order No.", framework_order_no,
                      "shown" if framework_order_no in details_text else "not shown", framework_order_no in details_text),
            new_check("ERP framework order details - vendor", vendor_order["vendor"],
                      "shown" if vendor_order["vendor"].lower() in details_text.lower() else "not shown",
                      vendor_order["vendor"].lower() in details_text.lower()),
        ]

    # Step 4: ERP Preview: open, download and verify the marketplace order document
    with allure.step("Step 4: Click Preview, download and verify the order document (ERP)"):
        preview_tab, pdf_url = FrameworkOrderListPage(details_tab).open_order_preview()
        preview_url = preview_tab.url
        reference = vendor_order_reference()
        erp_document = DOWNLOAD_DIR / f"erp_order_document_{reference.replace('/', '_')}.pdf"
        erp_document.write_bytes(preview_tab.context.request.get(pdf_url).body() if pdf_url else b"")
        print(f"ERP order document saved: {erp_document}")
        allure.attach.file(str(erp_document), name=f"ERP order document - {erp_document.name}")
        parameters = {key: values[0] for key, values in parse_qs(urlparse(pdf_url).query).items()}
        document_status = base64.b64decode(parameters.get("Status", "")).decode("utf-8", "ignore")
        preview_tab.close()
        is_pdf = erp_document.read_bytes()[:4] == b"%PDF"
        text = OrderDetails.read_order_document_text(erp_document) if is_pdf else ""
        allure.attach(text, name="ERP order document text", attachment_type=allure.attachment_type.TEXT)
        status_shown = VENDOR_ACKNOWLEDGED_STATUS.lower() in text.lower()
        print("ERP ORDER DOCUMENT:", erp_document.name, "| status parameter:", document_status or "-")
        checks += [
            new_check("ERP order document downloaded (PDF)", "%PDF", erp_document.read_bytes()[:4].decode("latin-1"),
                      is_pdf),
            new_check(f"ERP order document: order status '{VENDOR_ACKNOWLEDGED_STATUS}' not shown", "not shown",
                      "shown" if status_shown else "not shown", not status_shown),
        ]
        checks += check_order_document_text(text, "ERP Preview")
        RequisitionDetailsInformation(details_tab).get_full_page_screenshot('remarks_vendor_ack_erp_order_preview')
        details_tab.close()
        page.bring_to_front()
        attach_and_assert_checks(checks, "Framework order in ERP and order document")
        erp_framework_order = {"framework_order_no": framework_order_no, "url": details_url,
                               "order_document": erp_document.name, "document_status": document_status,
                               "preview_url": preview_url}

    # Step 5: Exit and log out from ERP
    with allure.step("Step 4: Exit and log out from ERP"):
        navigation_bar = MainNavigationBar(page)
        navigation_bar.exit()
        navigation_bar.logout_visible()
        navigation_bar.get_full_page_screenshot('remarks_vendor_ack_proc_admin_logout')


@allure.suite("Vendor Side")
@allure.feature("Order Acknowledgement")
@allure.story("Vendor Acknowledgement Result")
@allure.title("Test_case_14: Save the vendor acknowledgement result")
@allure.description("Test case 14: Save the vendor acknowledgement result (vendor username, Framework Order No., "
                    "status, products, schedule, order document) for the next phase.")
@pytest.mark.order(14)
def test_14_save_vendor_acknowledgement_result(page):
    """
    Test case 14: Save the vendor acknowledgement result
    (item_remarks_and_attachment_upload_vendor_acknowledgement_result.json), then assert the Shipping status check
    ("Shipped" after the acknowledgement).
    """
    global vendor_acknowledgement_result
    assert erp_framework_order, "Test case 13 must pass first: framework order not verified in ERP"

    with allure.step("Step 1: Save the vendor acknowledgement result"):
        vendor_acknowledgement_result = {
            **vendor_order,
            "vendor_username": vendor_username,
            "vendor_order_url": vendor_order_url,
            "framework_order_no": framework_order_no,
            "order_status": status_after_acknowledgement,
            "information_before_acknowledgement": information_before_acknowledgement,
            "products_before_acknowledgement": products_before_acknowledgement,
            "schedules_before_acknowledgement": schedules_before_acknowledgement,
            "details_after_acknowledgement": details_after_acknowledgement,
            "vendor_order_links": vendor_order_links,
            "vendor_order_document": vendor_order_document,
            "erp_framework_order": erp_framework_order,
        }
        save_result("item_remarks_and_attachment_upload_vendor_acknowledgement_result", vendor_acknowledgement_result)
        print("VENDOR ACKNOWLEDGEMENT RESULT:", vendor_acknowledgement_result)
        allure.attach("\n".join(f"{key}: {value}" for key, value in vendor_acknowledgement_result.items()),
                      name="Saved vendor acknowledgement result", attachment_type=allure.attachment_type.TEXT)

    # Step 2: Shipping status check after the acknowledgement (Test case 11)
    with allure.step("Step 2: Assert the Shipping status check"):
        print("SHIPPING STATUS CHECK FAILURES:", known_issue_checks or "none")
        attach_and_assert_checks(known_issue_checks, "Shipping status after the acknowledgement")
