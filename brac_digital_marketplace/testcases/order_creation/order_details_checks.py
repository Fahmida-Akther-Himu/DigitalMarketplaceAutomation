# Order details and order preview checks of one-item orders, used by the order creation test file (order initiator)
# and the order approval test file (order approver): order information, product, Preferred Delivery Schedule, Action
# History and the order document (preview PDF).
from dotenv import load_dotenv
import os
import re
import base64
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse, parse_qs

import allure

load_dotenv()

from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from pages.digital_marketplace.public_side.my_account.order_details import OrderDetails
from brac_digital_marketplace.testcases.order_creation.order_page_links import wait_for_erp_address

proj_user = os.getenv("test_user_name")
proj_env = os.getenv("test_env")

ORDER_INFORMATION_FIELDS = ("Order Reference No", "Framework Agreement", "Order Date", "Order Status", "Order Total",
                            "Letter Pad Type", "Order Remarks", "Vendor Name", "Programme Name")


def to_amount(value):
    # Why: amounts and quantities are shown with "BDT" and commas; When: comparing numbers. "BDT 5,080.00" -> 5080.00
    return Decimal(str(value).replace("BDT", "").replace(",", "").strip()).quantize(Decimal("0.01"))


def numbers_in_text(text):
    # Why: the order document shows numbers in different formats (10.5, 5080); When: checking the preview numbers
    numbers = set()
    for number in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            numbers.add(Decimal(number.replace(",", "")))
        except InvalidOperation:
            pass
    return numbers


def without_spaces(text):
    # Why: long texts (address, remarks) wrap differently on each page; When: comparing them without spaces
    return "".join((text or "").split())


def new_check(check, expected, actual, passed):
    # Why: one expected/actual check row for the report; When: every order details and preview check
    return check, expected, actual, "PASS" if passed else "FAIL"


def order_total(expected):
    # Why: the order total is the cart quantity x unit price; When: order information, product and preview checks
    return (to_amount(expected["quantity"]) * to_amount(expected["unit_price"])).quantize(Decimal("0.01"))


def check_order_information(page, expected):
    # Why: the order information must be the order that was created; When: order details checks (initiator and
    # approver). expected: order_reference_number, agreement_number, order_status, order_remarks, vendor, quantity,
    # unit_price. Returns (checks, order information)
    order_details_page = OrderDetails(page)
    information = {label: order_details_page.get_order_field(label) for label in ORDER_INFORMATION_FIELDS}
    print("ORDER DETAILS INFORMATION:", information)
    checks = [
        new_check("Order Reference No", expected["order_reference_number"], information["Order Reference No"],
                  information["Order Reference No"] == expected["order_reference_number"]),
        new_check("Framework Agreement", expected["agreement_number"], information["Framework Agreement"],
                  information["Framework Agreement"] == expected["agreement_number"]),
        new_check("Order Status", expected["order_status"], information["Order Status"],
                  expected["order_status"].lower() in information["Order Status"].lower()),
        new_check("Order Total (Qty. x Unit Price)", order_total(expected), information["Order Total"],
                  to_amount(information["Order Total"]) == order_total(expected)),
        new_check("Order Remarks", expected["order_remarks"], information["Order Remarks"],
                  " ".join(information["Order Remarks"].split()) == " ".join(expected["order_remarks"].split())),
        new_check("Vendor Name", expected["vendor"], information["Vendor Name"],
                  information["Vendor Name"].lower() == expected["vendor"].lower()),
        new_check("Letter Pad Type", "BRAC", information["Letter Pad Type"], information["Letter Pad Type"] == "BRAC"),
    ]
    return checks, information


def check_product(page, expected):
    # Why: the product of the order must be the requisition item with its cart values; When: order details checks.
    # expected: master_item_code, requisition_number, agreement_number, item_code, specification, remarks, uom,
    # quantity, unit_price. Returns (checks, product)
    order_details_page = OrderDetails(page)
    product_rows = order_details_page.get_product_rows()
    product = order_details_page.read_product_row(product_rows[0])
    product["Sub-Total"] = order_details_page.get_sub_total()
    total = order_total(expected)
    checks = [
        new_check("Products (one item)", 1, len(product_rows), len(product_rows) == 1),
        new_check("Master item", expected["master_item_code"], product["Master item"],
                  product["Master item"].startswith(expected["master_item_code"])),
        new_check("Requisition number", expected["requisition_number"], product["Requisition"],
                  product["Requisition"] == expected["requisition_number"]),
        new_check("FA No.", expected["agreement_number"], product["FA No."],
                  product["FA No."] == expected["agreement_number"]),
        new_check("Agreement item", expected["item_code"], product["Agreement item"],
                  expected["item_code"] in product["Agreement item"]),
        new_check("Specification", expected["specification"], product["Specification"],
                  product["Specification"] == " ".join(expected["specification"].split())),
        new_check("Remarks (cart remarks)", expected["remarks"], product["Remarks"],
                  product["Remarks"] == " ".join(expected["remarks"].split())),
        new_check("Attachment icon", "shown", "shown" if product["Attachment icon"] else "not shown",
                  product["Attachment icon"]),
        new_check("UoM", expected["uom"], product["UoM"], product["UoM"] == expected["uom"]),
        new_check("Quantity (cart quantity)", expected["quantity"], product["Quantity"],
                  to_amount(product["Quantity"]) == to_amount(expected["quantity"])),
        new_check("Unit Price", expected["unit_price"], product["Unit Price"],
                  to_amount(product["Unit Price"]) == to_amount(expected["unit_price"])),
        new_check("Total Price (Qty. x Unit Price)", total, product["Total Price"],
                  to_amount(product["Total Price"]) == total),
        new_check("Sub-Total", total, product["Sub-Total"], to_amount(product["Sub-Total"]) == total),
    ]
    return checks, product


def receiver_of(schedule_row):
    # Why: the receiving person column is "Receiver Info" on the order initiator's order details and "Delivery Info"
    # on the order approver's order details; When: Preferred Delivery Schedule checks
    return schedule_row.get("Receiver Info") or schedule_row.get("Delivery Info") or ""


def check_delivery_schedules(page, expected_schedules):
    # Why: the Preferred Delivery Schedule must be the schedule of the order; When: order details checks.
    # expected_schedules: [{"Quantity", "Location", "Receiver"}]. Returns (checks, schedule rows)
    schedules = OrderDetails(page).get_all_preferred_delivery_schedules()
    checks = [new_check("Delivery schedules", len(expected_schedules), len(schedules),
                        len(schedules) == len(expected_schedules))]
    for number, expected in enumerate(expected_schedules, start=1):
        schedule = next((row for row in schedules
                         if to_amount(row.get("Quantity", "0")) == to_amount(expected["Quantity"])), {})
        checks += [
            new_check(f"Schedule {number} Quantity", expected["Quantity"], schedule.get("Quantity", "not found"),
                      bool(schedule)),
            new_check(f"Schedule {number} Location", expected["Location"], schedule.get("Location", "-"),
                      without_spaces(expected["Location"]).lower() in without_spaces(schedule.get("Location")).lower()),
            new_check(f"Schedule {number} receiving person", expected["Receiver"], receiver_of(schedule) or "-",
                      expected["Receiver"] in receiver_of(schedule)),
        ]
    return checks, schedules


def check_action_history(page, order_date, order_approver=None):
    # Why: the Action History shows who submitted (and approved) the order, and the Order Date is the date it was
    # submitted; When: order details checks before and after the approval. Returns (checks, action history)
    action_history = OrderDetails(page).get_action_history()
    print("ACTION HISTORY:", action_history)
    submitted_rows = [row for row in action_history if row.get("Order Status") == "Submitted for Approval"
                      and proj_user in row.get("Action Taken By", "")]
    submitted_date = submitted_rows[0].get("Time", "").split(" ")[0] if submitted_rows else ""
    checks = [
        new_check("Action History - Submitted for Approval by the requisition initiator", proj_user,
                  submitted_rows[0]["Action Taken By"] if submitted_rows else "-", bool(submitted_rows)),
        new_check("Order Date (date the order was submitted)", submitted_date, order_date, order_date == submitted_date),
    ]
    if order_approver:
        approved_rows = [row for row in action_history if "approved" in row.get("Order Status", "").lower()
                         and order_approver in row.get("Action Taken By", "")]
        checks.append(new_check("Action History - Order Approved by the order approver", order_approver,
                                approved_rows[0]["Action Taken By"] if approved_rows else "-", bool(approved_rows)))
    return checks, action_history


def open_preview_tab(page, erp_user=None):
    # Why: Preview opens the ERP order document, and ERP may show its login page first; When: order preview checks.
    # erp_user: the user logged in to the marketplace (ResetHub login as the same user)
    order_details_page = OrderDetails(page)
    preview_tab = order_details_page.open_order_preview()
    wait_for_erp_address(preview_tab)
    if RequisitionDetailsInformation(preview_tab).is_erp_login_page():
        reset_page = ResetHubPage(preview_tab)
        reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=erp_user or proj_user))
        preview_tab.close()
        page.bring_to_front()
        preview_tab = order_details_page.open_order_preview()
        wait_for_erp_address(preview_tab)
    return preview_tab


def check_order_preview(page, expected, save_folder, erp_user=None):
    # Why: the order document (preview PDF) must show the order: BRAC letter pad, status, Purchase Order number, item,
    # totals, amount in words and the delivery schedule; When: order preview checks (initiator and approver).
    # expected: the order details expected values + order_status and schedules. Returns (checks, preview)
    order_details_page = OrderDetails(page)
    preview_tab = open_preview_tab(page, erp_user)
    reference = expected["order_reference_number"]
    order_document = order_details_page.download_order_document(
        preview_tab, save_folder, f"order_document_{reference.replace('/', '_')}.pdf")
    allure.attach.file(str(order_document), name=f"Order document - {order_document.name}")
    parameters = {key: values[0] for key, values in parse_qs(urlparse(preview_tab.url).query).items()}
    tracking_number = base64.b64decode(parameters.get("trackingNumber", "")).decode("utf-8", "ignore")
    preview_status = base64.b64decode(parameters.get("Status", "")).decode("utf-8", "ignore")
    preview_tab.close()
    page.bring_to_front()

    text = order_details_page.read_order_document_text(order_document)
    numbers = numbers_in_text(text)
    allure.attach(text, name="Order document text", attachment_type=allure.attachment_type.TEXT)
    purchase_order = re.search(r"Purchase Order:\s*(\S+)", text)
    amount_in_words = order_details_page.get_amount_in_words(text)
    total = order_total(expected)
    has_paisa = total % 1 != 0
    preview = {"url": preview_tab.url, "order_document": order_document.name,
               "purchase_order_number": purchase_order.group(1) if purchase_order else "",
               "amount_in_words": amount_in_words}
    print("PURCHASE ORDER NUMBER:", preview["purchase_order_number"])

    checks = [
        new_check("Order document is a PDF", "%PDF", order_document.read_bytes()[:4].decode("latin-1"),
                  order_document.read_bytes()[:4] == b"%PDF"),
        new_check("Preview tracking number (order reference)", reference, tracking_number, tracking_number == reference),
        new_check("Preview status (order status)", expected["order_status"], preview_status,
                  expected["order_status"].lower() in preview_status.lower()),
        new_check("Preview letter pad (BRAC)", "1", parameters.get("letterPad", "-"), parameters.get("letterPad") == "1"),
        new_check("Purchase Order number", "shown", preview["purchase_order_number"] or "not found",
                  bool(preview["purchase_order_number"])),
        new_check("Amount in words (TAKA, PAISA when the total has paisa, ONLY)",
                  "... TAKA AND ... PAISA ONLY" if has_paisa else "... TAKA ONLY", amount_in_words or "not found",
                  "TAKA" in amount_in_words and ("PAISA" in amount_in_words) == has_paisa
                  and amount_in_words.endswith("ONLY")),
    ]
    expected_texts = [("Letter pad", "BRAC"), ("Order status", expected["order_status"]),
                      ("Requisition number", expected["requisition_number"]), ("FA No.", expected["agreement_number"]),
                      ("Master item", expected["master_item_code"]), ("Agreement item", expected["item_code"]),
                      ("Specification", expected["specification"]), ("Remarks", expected["remarks"]),
                      ("UoM", expected["uom"]), ("Attachment", "Downloadable from the system")]
    expected_numbers = [("Quantity", to_amount(expected["quantity"])), ("Unit Price", to_amount(expected["unit_price"])),
                        ("Total Price / Grand Total (Qty. x Unit Price)", total)]
    for number, schedule in enumerate(expected["schedules"], start=1):
        expected_texts += [(f"Schedule {number} place", schedule["Location"]),
                           (f"Schedule {number} receiver", schedule["Receiver"])]
        expected_numbers.append((f"Schedule {number} quantity", to_amount(schedule["Quantity"])))
    for check, value in expected_texts:
        found = without_spaces(value).lower() in without_spaces(text).lower()
        checks.append(new_check(check, value[:60], "on the preview" if found else "not found", found))
    for check, value in expected_numbers:
        checks.append(new_check(check, value, "on the preview" if value in numbers else "not found", value in numbers))
    return checks, preview
