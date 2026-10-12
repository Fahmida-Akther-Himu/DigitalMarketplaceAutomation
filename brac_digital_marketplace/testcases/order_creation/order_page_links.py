# Requisition, Framework Agreement, product details and attachment links of the checkout pages (Delivery Schedule,
# Confirm order) and of the order details page (order initiator or order approver), checked the same way as on the
# shopping cart page. Used by the order creation and order approval test files.
from dotenv import load_dotenv
import os
from pathlib import Path
from urllib.parse import urlparse, unquote

import allure

load_dotenv()

from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.public_side.shopping_cart import ShoppingCart
from pages.digital_marketplace.public_side.checkout_page import CheckoutPage
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails
from utils.attachment_rules import same_file_type

proj_user = os.getenv("test_user_name")
proj_env = os.getenv("test_env")
# ERP staging address: requisition and FA links open ERP pages
erp_url = os.getenv("test_url")


def wait_for_erp_address(erp_tab):
    # ERP pages (requisition, preview) may never finish loading: used to wait only until the ERP address opens
    erp_tab.wait_for_url(lambda url: urlparse(url).netloc == urlparse(erp_url).netloc, timeout=60000,
                         wait_until="commit")


def close_tabs(tabs, page):
    # Why: a link can open 1 or 2 tabs; When: after reading the opened page, to close them all and go back
    HomePage(page).close_opened_tabs(tabs)


def framework_link_result(framework_tab, save_folder=None):
    # Why: the FA link opens the agreement attachment, or an ERP staging page with a message when it is not
    # available; When: every Framework Agreement link check. save_folder: the available attachment is downloaded
    response = framework_tab.context.request.get(framework_tab.url)
    available = response.ok and "text/html" not in response.headers.get("content-type", "")
    message = "" if available else " ".join(framework_tab.locator("body").inner_text().split())
    on_erp = urlparse(framework_tab.url).netloc == urlparse(erp_url).netloc
    result = {"url": framework_tab.url, "available": available, "message": message,
              "passed": available or (on_erp and bool(message)), "downloaded": ""}
    if available and save_folder:
        saved_file = Path(save_folder) / unquote(framework_tab.url).split("/")[-1].split("?")[0]
        saved_file.write_bytes(response.body())
        result["downloaded"] = saved_file.name
        result["passed"] = saved_file.stat().st_size > 0
        print(f"Agreement attachment downloaded: {saved_file}")
    return result


def read_requisition_from_link(page, open_link_tabs, screenshot_name, erp_user=None):
    # Why: a requisition link opens the ERP requisition details in 1 or 2 tabs and may show the ERP login page first;
    # When: every requisition link check (checkout and order details pages). erp_user: the user logged in to the
    # marketplace (ResetHub login as the same user). Returns (ERP requisition information, number of opened tabs)
    erp_tabs = open_link_tabs()
    for erp_tab in erp_tabs:
        wait_for_erp_address(erp_tab)
    if any(RequisitionDetailsInformation(erp_tab).is_erp_login_page() for erp_tab in erp_tabs):
        reset_page = ResetHubPage(erp_tabs[0])
        reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=erp_user or proj_user))
        close_tabs(erp_tabs, page)
        erp_tabs = open_link_tabs()
        for erp_tab in erp_tabs:
            wait_for_erp_address(erp_tab)
    # With 2 opened tabs the first one can be behind the second one: bring it to the front before reading it
    erp_tabs[0].bring_to_front()
    # ERP staging can be slow: wait up to 60 seconds, then reload the ERP tab once and wait again
    if not RequisitionDetailsInformation(erp_tabs[0]).wait_for_requisition_details(timeout=60000):
        print("Requisition details not shown after 60 seconds: the ERP tab is reloaded once")
        erp_tabs[0].reload(wait_until="commit")
        RequisitionDetailsInformation(erp_tabs[0]).wait_for_requisition_details(timeout=60000)
    erp_information = RequisitionDetailsInformation(erp_tabs[0]).get_requisition_information()
    RequisitionDetailsInformation(erp_tabs[0]).get_full_page_screenshot(screenshot_name)
    opened_tabs = len(erp_tabs)
    close_tabs(erp_tabs, page)
    print(f"Requisition link: {opened_tabs} tab(s) opened and closed")
    return erp_information, opened_tabs


def open_product_link(checkout_page, page, product_name, index, screenshot_name):
    # Product details link (n-th link of this product name) opens the agreement item page: used to read its address
    product_tabs = checkout_page.open_checkout_link_all_tabs(product_name, index=index)
    product_tabs[0].wait_for_load_state("domcontentloaded")
    product_url = product_tabs[0].url
    HomePage(product_tabs[0]).get_full_page_screenshot(screenshot_name)
    close_tabs(product_tabs, page)
    return product_url


def check_checkout_page_links(page, requisition_number, agreement_numbers, products, label, links_required=True,
                              save_folder=None):
    # Links of a checkout page, opened in page order (first in, first out):
    # - Framework Agreement of the header (each FA No.): the agreement attachment (downloaded) or an ERP message
    # - requisition number: ERP requisition details (ResetHub login when the ERP login page is shown); the link can
    #   open 2 ERP tabs: all opened tabs are closed before going back
    # - "FA: ..." link of each item: the agreement attachment (downloaded) or an ERP message
    # - product details: every product link, the agreement item page of each item
    #   (products: {product name: [item codes of the items with this product name]})
    # links_required: a missing link fails the check (Confirm order); otherwise it is noted in the report
    # Returns (checks, links); checks are (check, expected, actual, "PASS"/"FAIL")
    checkout_page = CheckoutPage(page)
    checks, links = [], {}

    def add_check(check, expected, actual, passed):
        # One expected/actual check row: used for each link of the page
        checks.append((check, expected, actual, "PASS" if passed else "FAIL"))

    def link_missing(name, link_text):
        # A link is not on the page: fails on Confirm order, only noted on the Delivery Schedule
        links[name] = f"no link '{link_text}' on this page"
        if links_required:
            add_check(f"{name} link", "shown", "not found", False)

    def open_framework_link(agreement_number, index, name):
        # One Framework Agreement link (the n-th link with this FA No.): the agreement attachment is downloaded
        framework_tabs = checkout_page.open_checkout_link_all_tabs(agreement_number, index=index)
        result = framework_link_result(framework_tabs[0], save_folder)
        close_tabs(framework_tabs, page)
        links[name] = result
        add_check(name, "agreement attachment or ERP message",
                  (result["downloaded"] or "available") if result["available"] else result["message"][:80] or result["url"],
                  result["passed"])

    agreement_numbers = list(dict.fromkeys(agreement_numbers))

    # 1. Framework Agreement links of the order header (the first link of each FA No.)
    for agreement_number in agreement_numbers:
        if checkout_page.has_checkout_link(agreement_number):
            open_framework_link(agreement_number, 0, f"Framework Agreement link {agreement_number} (header)")
        else:
            link_missing(f"Framework Agreement {agreement_number}", agreement_number)

    # 2. Requisition number link of the item: ERP requisition details (all opened tabs closed)
    if checkout_page.has_checkout_link(requisition_number):
        erp_information, opened_tabs = read_requisition_from_link(
            page, lambda: checkout_page.open_checkout_link_all_tabs(requisition_number), f'{label}_erp_requisition')
        links["Requisition"] = {"req_no": erp_information["req_no"], "tabs_opened": opened_tabs}
        add_check("Requisition link (ERP REQ. No)", requisition_number, erp_information["req_no"],
                  erp_information["req_no"] == requisition_number)
        add_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1)
    else:
        link_missing("Requisition", requisition_number)

    # 3. "FA: ..." links of the items (the next links of each FA No.)
    for agreement_number in agreement_numbers:
        for index in range(1, checkout_page.count_checkout_links(agreement_number)):
            open_framework_link(agreement_number, index, f"Framework Agreement link {agreement_number} (item FA {index})")

    # 4. Product details links: every product link of the page (one per item; items with the same product name have
    # one link each, opened by position); together they must open the page of every item
    for product_name, item_codes in products.items():
        if not checkout_page.has_checkout_link(product_name):
            link_missing(f"Product {product_name}", product_name)
            continue
        link_count = checkout_page.count_checkout_links(product_name)
        add_check(f"Product details links '{product_name}' (one per item)", len(item_codes), link_count,
                  link_count >= len(item_codes))
        items_not_opened = [code.lower() for code in item_codes]
        for index in range(min(link_count, len(item_codes))):
            product_url = open_product_link(checkout_page, page, product_name, index, f'{label}_product_{index + 1}')
            links[f"Product {product_name} ({index + 1})"] = product_url
            opened_code = next((code for code in item_codes if code.lower() in product_url.lower()), "")
            add_check(f"Product details link '{product_name}' ({index + 1})", " or ".join(dict.fromkeys(item_codes)),
                      product_url, bool(opened_code))
            if opened_code.lower() in items_not_opened:
                items_not_opened.remove(opened_code.lower())
        add_check(f"Product details links '{product_name}': page of every item", "none missing",
                  ", ".join(items_not_opened) or "none missing", not items_not_opened)

    allure.attach("\n".join(f"{name}: {value}" for name, value in links.items()), name=f"{label} links",
                  attachment_type=allure.attachment_type.TEXT)
    return checks, links


def check_confirm_order_rows_links(page, requisition_number, agreement_numbers, items, label, save_folder=None,
                                   erp_user=None):
    # Why: the confirm order links are opened in page order (first in, first out) and every item row must link to
    # its own requisition, agreement, product page and attachment; When: confirm order link checks of orders with
    # more items. items: [{"name", "agreement_number", "item_code", "product_name", "attachment_name" ("" = none)}].
    # Order: order header Framework Agreement links, then every item row from the top: requisition, "FA:", product
    # page, attachment. A header FA No. that is not shown is only noted (the header is checked with the order
    # information). Returns (checks, links)
    checkout_page = CheckoutPage(page)
    checks, links = [], {}

    def add_check(check, expected, actual, passed):
        # One expected/actual check row: used for each link of the page
        checks.append((check, expected, actual, "PASS" if passed else "FAIL"))

    def open_framework(name, framework_link):
        # One Framework Agreement link: the agreement attachment is downloaded (or the ERP staging message)
        framework_tabs = checkout_page.open_link_in_new_tabs(framework_link)
        result = framework_link_result(framework_tabs[0], save_folder)
        close_tabs(framework_tabs, page)
        links[name] = result
        add_check(name, "agreement attachment or ERP message",
                  (result["downloaded"] or "available") if result["available"] else result["message"][:80] or result["url"],
                  result["passed"])

    # 1. Framework Agreement links of the order header
    for agreement_number in dict.fromkeys(agreement_numbers):
        header_link = checkout_page.confirm_header_framework_link(agreement_number)
        if header_link.count():
            open_framework(f"Order header Framework Agreement link {agreement_number}", header_link.first)
        else:
            links[f"Order header Framework Agreement link {agreement_number}"] = "not shown in the order header"

    # 2. Every item row from the top: requisition, "FA:", product page and attachment
    item_rows = checkout_page.confirm_item_rows(requisition_number)
    add_check("Item rows", len(items), len(item_rows), len(item_rows) == len(items))
    items_not_found = list(items)
    for row_number, item_row in enumerate(item_rows, start=1):
        row_text = " ".join(item_row.inner_text().split())
        item = next((item for item in items_not_found
                     if item["agreement_number"] in row_text and item["item_code"] in row_text), None)
        add_check(f"Row {row_number} item", "an item of the order", item["name"] if item else row_text[:80], bool(item))
        if not item:
            continue
        items_not_found.remove(item)
        name = f"Row {row_number} ({item['name']})"

        erp_information, opened_tabs = read_requisition_from_link(
            page, lambda: checkout_page.open_link_in_new_tabs(checkout_page.confirm_row_link(item_row, requisition_number)),
            f'{label}_row_{row_number}_erp_requisition', erp_user)
        links[f"{name} requisition"] = {"req_no": erp_information["req_no"], "tabs_opened": opened_tabs,
                                        "requisition_date": erp_information["requisition_date"]}
        add_check(f"{name} requisition link (ERP REQ. No)", requisition_number, erp_information["req_no"],
                  erp_information["req_no"] == requisition_number)
        add_check(f"{name} requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed",
                  len(page.context.pages) == 1)

        open_framework(f"{name} FA link {item['agreement_number']}", checkout_page.confirm_row_link(item_row, "FA:"))

        product_tabs = checkout_page.open_link_in_new_tabs(checkout_page.confirm_row_link(item_row, item["product_name"]))
        product_tabs[0].wait_for_load_state("domcontentloaded")
        product_url = product_tabs[0].url
        HomePage(product_tabs[0]).get_full_page_screenshot(f'{label}_row_{row_number}_product')
        close_tabs(product_tabs, page)
        links[f"{name} product page"] = product_url
        add_check(f"{name} product page link", item["item_code"], product_url,
                  item["item_code"].lower() in product_url.lower())

        attachment_icon = checkout_page.confirm_row_attachment_icon(item_row)
        if item["attachment_name"]:
            downloaded_file = checkout_page.save_attachment_from_icon(attachment_icon.first, save_folder)
            links[f"{name} attachment"] = downloaded_file.name
            add_check(f"{name} attachment download (same file type)", item["attachment_name"], downloaded_file.name,
                      same_file_type(downloaded_file, item["attachment_name"]))
        else:
            add_check(f"{name} attachment icon", "not shown (no attachment)",
                      "shown" if attachment_icon.count() else "not shown", not attachment_icon.count())
    add_check("Items of the order on the confirm page", "none missing",
              ", ".join(item["name"] for item in items_not_found) or "none missing", not items_not_found)

    allure.attach("\n".join(f"{name}: {value}" for name, value in links.items()), name=f"{label} links",
                  attachment_type=allure.attachment_type.TEXT)
    return checks, links


def product_name_of(product):
    # Why: the product link text is the agreement item name; When: opening the product page of an order details row
    # "([FWI049375] - BYA FR Skin Coated - Project Site )" -> "BYA FR Skin Coated - Project Site"
    return product["Agreement item"].strip("() ").split("] - ", 1)[-1].strip()


def check_order_details_page_links(page, requisition_number, agreement_number, item_code, attachment_name, label,
                                   save_folder, erp_user=None):
    # Why: the order details page (order initiator or order approver) must link to the right requisition, agreement,
    # product page and attachment; When: order details and order approval checks (first product row). The links are
    # opened in page order: order information Framework Agreement, requisition, product FA, product page, attachment.
    # erp_user: the user logged in to the marketplace (ResetHub login as the same user). Returns (checks, links)
    order_details_page = OrderDetails(page)
    checks, links = [], {}

    def add_check(check, expected, actual, passed):
        # One expected/actual check row: used for each link of the page
        checks.append((check, expected, actual, "PASS" if passed else "FAIL"))

    product_row = order_details_page.get_product_rows()[0]
    product_name = product_name_of(order_details_page.read_product_row(product_row))

    def open_framework_link(name, open_framework_tab):
        # One Framework Agreement link: the agreement attachment is downloaded (or the ERP staging message)
        framework_tab = open_framework_tab()
        result = framework_link_result(framework_tab, save_folder)
        framework_tab.close()
        page.bring_to_front()
        links[name] = result
        add_check(f"{name} {agreement_number}", "agreement attachment or ERP message",
                  (result["downloaded"] or "available") if result["available"] else result["message"][:80] or result["url"],
                  result["passed"])

    # 1. Framework Agreement link of the order information: the agreement attachment is downloaded
    open_framework_link("Order information Framework Agreement link",
                        lambda: order_details_page.open_header_framework_link(agreement_number))

    # 2. Requisition number link of the product: ERP requisition details (all opened tabs closed)
    erp_information, opened_tabs = read_requisition_from_link(
        page, lambda: order_details_page.open_link_all_tabs(order_details_page.product_link(product_row, requisition_number)),
        f'{label}_erp_requisition', erp_user)
    links["Requisition"] = {"req_no": erp_information["req_no"], "tabs_opened": opened_tabs}
    add_check("Requisition link (ERP REQ. No)", requisition_number, erp_information["req_no"],
              erp_information["req_no"] == requisition_number)
    add_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1)

    # 3. "FA: ..." link of the product
    open_framework_link("Product FA link", lambda: order_details_page.open_product_link(product_row, "FA:"))

    # 4. Product page link: the agreement item page
    product_tab = order_details_page.open_product_link(product_row, product_name)
    links["Product page"] = product_tab.url
    HomePage(product_tab).get_full_page_screenshot(f'{label}_product_page')
    close_tabs([product_tab], page)
    add_check(f"Product page link '{product_name}'", item_code, links["Product page"],
              item_code.lower() in links["Product page"].lower())

    # 5. Attachment: downloaded with the same file type as the attachment of the order (no attachment: no icon)
    if attachment_name:
        downloaded_file = order_details_page.download_product_row_attachment(product_row, save_folder)
        links["Attachment"] = downloaded_file.name
        add_check("Attachment download (same file type)", attachment_name, downloaded_file.name,
                  same_file_type(downloaded_file, attachment_name))
    else:
        icon_shown = order_details_page.read_product_row(product_row)["Attachment icon"]
        add_check("Attachment icon", "not shown (no attachment)", "shown" if icon_shown else "not shown", not icon_shown)

    allure.attach("\n".join(f"{name}: {value}" for name, value in links.items()), name=f"{label} links",
                  attachment_type=allure.attachment_type.TEXT)
    return checks, links


def check_cart_item_links(page, item_row, requisition_number, item_code, attachment_name, label, save_folder,
                          erp_user=None, check_requisition=True):
    # Why: the shopping cart item must link to the right requisition, agreement, product page and attachment;
    # When: shopping cart checks (before and after the vendor selection). check_requisition=False: the requisition
    # link is not opened (items of the same requisition: opened for one item only). Returns (checks, links)
    cart_page = ShoppingCart(page)
    checks, links = [], {}

    def add_check(check, expected, actual, passed):
        # One expected/actual check row: used for each link of the cart item
        checks.append((check, expected, actual, "PASS" if passed else "FAIL"))

    # Requisition number link: ERP requisition details (all opened tabs closed)
    if check_requisition:
        erp_information, opened_tabs = read_requisition_from_link(
            page, lambda: cart_page.open_link_in_new_tabs(cart_page.cart_requisition_link(item_row)),
            f'{label}_erp_requisition', erp_user)
        links["Requisition"] = {"req_no": erp_information["req_no"], "tabs_opened": opened_tabs}
        add_check("Requisition link (ERP REQ. No)", requisition_number, erp_information["req_no"],
                  erp_information["req_no"] == requisition_number)
        add_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1)

    # Framework Agreement link: the agreement attachment or an ERP staging message
    framework_tab = cart_page.open_cart_item_framework_document(item_row)
    result = framework_link_result(framework_tab, save_folder)
    close_tabs([framework_tab], page)
    links["Framework Agreement"] = result
    add_check("Framework Agreement link", "agreement attachment or ERP message",
              (result["downloaded"] or "available") if result["available"] else result["message"][:80] or result["url"], result["passed"])

    # Product details link: the agreement item page
    product_tab = cart_page.open_cart_agreement_item(item_row)
    links["Product page"] = product_tab.url
    HomePage(product_tab).get_full_page_screenshot(f'{label}_product_page')
    close_tabs([product_tab], page)
    add_check("Product details link (agreement item page)", item_code, links["Product page"],
              item_code.lower() in links["Product page"].lower())

    # Attachment: downloaded with the same file type as the item attachment
    if attachment_name:
        downloaded_file = cart_page.download_cart_attachment(item_row, save_folder)
        links["Attachment"] = downloaded_file.name
        add_check("Attachment download (same file type)", attachment_name, downloaded_file.name,
                  same_file_type(downloaded_file, attachment_name))

    allure.attach("\n".join(f"{name}: {value}" for name, value in links.items()), name=f"{label} links",
                  attachment_type=allure.attachment_type.TEXT)
    return checks, links


def check_checkout_attachment(page, attachment_name, label, save_folder, index=0):
    # Why: the checkout steps (delivery schedule, confirm order) must show the item attachment; When: checkout
    # attachment checks. Returns (checks, downloaded file name)
    downloaded_file = CheckoutPage(page).download_checkout_attachment(save_folder, index)
    passed = same_file_type(downloaded_file, attachment_name)
    print(f"{label} attachment: {downloaded_file.name} ({'same file type' if passed else 'different file type'})")
    return [("Attachment download (same file type)", attachment_name, downloaded_file.name,
             "PASS" if passed else "FAIL")], downloaded_file.name


def in_page_order(items, row_of):
    # Why: links and attachments are opened FIFO (top row of the page first, as the user sees the page); When: before
    # opening the links of more items. row_of(item) -> the row of the item on the page (None: kept last)
    def top_of(item):
        # Position of the item row from the top of the page
        row = row_of(item)
        return row.evaluate("row => row.getBoundingClientRect().top + window.scrollY") if row else float("inf")
    return sorted(items, key=top_of)


def find_product_row(order_details_page, item, used_rows):
    # Why: items can have the same agreement item code (different master items); When: matching an item to its
    # order details product row (by agreement item code and master item code, each row used once)
    for index, product_row in enumerate(order_details_page.get_product_rows()):
        if index in used_rows:
            continue
        product = order_details_page.read_product_row(product_row)
        if item["item_code"] in product["Agreement item"] and \
                product["Master item"].startswith(item.get("master_item_code", "")):
            used_rows.add(index)
            return product_row, product
    return None, None


def check_order_details_all_products_links(page, requisition_number, agreement_numbers, items, label, save_folder,
                                           erp_user=None):
    # Why: an order with more items must link every product to its agreement attachment, product page and item
    # attachment; When: order details checks of multi-item orders (initiator or approver).
    # items: [{"item_code", "master_item_code", "attachment_name" ("" = no attachment)}]. The order information
    # Framework Agreement link of each FA is checked first ("shown" checks are named "Order information Framework
    # Agreement ... shown", so a test can check them last). Returns (checks, links)
    order_details_page = OrderDetails(page)
    checks, links = [], {}

    def add_check(check, expected, actual, passed):
        # One expected/actual check row: used for each link of the page
        checks.append((check, expected, actual, "PASS" if passed else "FAIL"))

    def open_framework(name, open_framework_tab):
        # One Framework Agreement link: the agreement attachment is downloaded (or the ERP staging message)
        framework_tab = open_framework_tab()
        result = framework_link_result(framework_tab, save_folder)
        framework_tab.close()
        page.bring_to_front()
        links[name] = result
        add_check(name, "agreement attachment or ERP message",
                  (result["downloaded"] or "available") if result["available"] else result["message"][:80] or result["url"],
                  result["passed"])

    # Framework Agreement links of the order information first: every FA No. of the order is shown and downloaded
    header_agreements = order_details_page.get_order_field("Framework Agreement")
    for agreement_number in dict.fromkeys(agreement_numbers):
        shown = agreement_number in header_agreements
        add_check(f"Order information Framework Agreement {agreement_number} shown", agreement_number,
                  header_agreements, shown)
        if shown:
            open_framework(f"Order information Framework Agreement link {agreement_number}",
                           lambda: order_details_page.open_header_framework_link(agreement_number))

    # Requisition number link (same requisition for every product): ERP requisition details, all opened tabs closed
    first_row = order_details_page.get_product_rows()[0]
    erp_information, opened_tabs = read_requisition_from_link(
        page, lambda: order_details_page.open_link_all_tabs(order_details_page.product_link(first_row, requisition_number)),
        f'{label}_erp_requisition', erp_user)
    links["Requisition"] = {"req_no": erp_information["req_no"], "tabs_opened": opened_tabs}
    add_check("Requisition link (ERP REQ. No)", requisition_number, erp_information["req_no"],
              erp_information["req_no"] == requisition_number)
    add_check("Requisition link tabs closed", "all", f"{opened_tabs} tab(s) closed", len(page.context.pages) == 1)

    # Every product row of the item
    used_rows, found_products = set(), []
    for number, item in enumerate(items, start=1):
        product_row, product = find_product_row(order_details_page, item, used_rows)
        add_check(f"Item {number} product row ({item['item_code']})", "shown", "shown" if product_row else "not found",
                  bool(product_row))
        if product_row:
            found_products.append((number, item, product_row, product))

    # Every product in page order (top product row first): product FA link, product page and item attachment
    # A product row is {column title: cell}: its first cell gives the position of the row
    for number, item, product_row, product in in_page_order(found_products, lambda found: next(iter(found[2].values()))):
        open_framework(f"Item {number} product FA link",
                       lambda: order_details_page.open_product_link(product_row, "FA:"))
        product_tab = order_details_page.open_product_link(product_row, product_name_of(product))
        links[f"Item {number} product page"] = product_tab.url
        HomePage(product_tab).get_full_page_screenshot(f'{label}_item_{number}_product_page')
        close_tabs([product_tab], page)
        add_check(f"Item {number} product page link", item["item_code"], links[f"Item {number} product page"],
                  item["item_code"].lower() in links[f"Item {number} product page"].lower())
        if item["attachment_name"]:
            downloaded_file = order_details_page.download_product_row_attachment(product_row, save_folder)
            links[f"Item {number} attachment"] = downloaded_file.name
            add_check(f"Item {number} attachment download (same file type)", item["attachment_name"],
                      downloaded_file.name, same_file_type(downloaded_file, item["attachment_name"]))
        else:
            add_check(f"Item {number} attachment icon", "not shown (no attachment)",
                      "shown" if product["Attachment icon"] else "not shown", not product["Attachment icon"])

    allure.attach("\n".join(f"{name}: {value}" for name, value in links.items()), name=f"{label} links",
                  attachment_type=allure.attachment_type.TEXT)
    return checks, links
