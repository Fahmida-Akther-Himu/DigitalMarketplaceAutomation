from dotenv import load_dotenv
import os
from pathlib import Path

import html
import random
import re
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP

import pytest
import allure

load_dotenv()

# ERP Procurement staging (ResetHub login)
proj_env = os.getenv("test_env")
# Admin user who finds the agreement initiator
proc_admin = os.getenv("test_proc_admin")
# Marketplace whitelisted Framework Agreement (base FA No., ERP may add /V1, /V2 ...)
agreement_number = os.getenv("test_agreement_number")
# Amendment comment (global, reused throughout the automation)
amendment_comment = os.getenv("test_amendment_comment")
MAX_AMENDMENT_COMMENT_LENGTH = 300
# Number of Framework Item Details rows captured before the amendment
ITEMS_TO_CAPTURE = 2
# Agreement status after the amendment is started (status column starts with it)
EXPECTED_STATUS_AFTER_AMENDMENT = "Reviewed"
# Agreement edit comment (global, max 300 characters) and the status before Edit (Test case 5)
agreement_edit_comment = os.getenv("test_agreement_edit_comment")
EXPECTED_STATUS_BEFORE_EDIT = "Reviewed"
# Amendment updates (Test case 6)
end_date_years = os.getenv("test_end_date_years")
amendment_attachment_file = os.getenv("test_amendment_attachment_file")
# Item 1 specification (global, max 500 characters)
item_updated_specification = os.getenv("test_item_updated_specification")
MAX_SPECIFICATION_LENGTH = 500
# Unit Price change for Item 1 (+) and Item 2 (-), e.g. 100.99
unit_price_change = os.getenv("test_unit_price_change")
# Item 2 new Unit Price range (2 decimals, e.g. 10.00 - 10.99)
item_2_unit_price_min = os.getenv("test_item_2_unit_price_min")
item_2_unit_price_max = os.getenv("test_item_2_unit_price_max")
MOQ_AFTER_AMENDMENT = "1"
# Output Document users (Test case 8)
amended_agreement_recommender = os.getenv("test_amended_agreement_recommender")
amended_agreement_approver = os.getenv("test_amended_agreement_approver")
# Approval comment (global, max 300 characters) and the final status (Test cases 10-11)
agreement_approval_comment = os.getenv("test_agreement_approval_comment")
EXPECTED_FINAL_STATUS = "Approved"
# Framework List legend for an agreement whose price review date is reached (Test case 12)
PRICE_TO_BE_REVIEWED_LEGEND = "Price to be reviewed"
# Project root is 3 levels up: testcases/Framework_agreement/<this file>
UTILS_DIR = Path(__file__).resolve().parents[3] / "utils"

from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_list import FrameworkList
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_information import FrameworkInformation
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_agreement_information import \
    FrameworkAgreementInformation

# Agreement global variables (Test case 1)
agreement_fa_no = ''
agreement_initiator_id = ''
agreement_initiator_name = ''
# Pre-amendment data (Test case 2): kept unchanged for the ERP after amendment / Marketplace comparison
agreement_tab = None
framework_info_before = {}
attachment_before = None
attachment_before_message = ''
items_before = []
marketplace_products_before = []
amendment_message = ''
# Status and reviewer after the amendment (Test case 4): reviewer is used in the next chunk
agreement_status_info = {}
# Amendment edit page (Test case 5): opened, not modified
edit_page_tab = None
agreement_status_before_edit = ''
# Amendment updates (Test case 6): previous/updated values for the ERP and Marketplace verification
amendment_updates = {}
item_updates = []
# Browser alert messages on the amendment edit page (Test cases 6-8)
edit_page_dialog_messages = []
# Update & Next (Test case 7)
update_next_confirmation_message = ''
# Output Document and submission (Test case 8)
selected_recommender_info = ''
selected_approver_info = ''
role_validation_alert_message = ''
submit_confirmation_message = ''
final_submission_message = ''
submitted_agreement_no = ''
# Approval status after submission (Test case 9): next approval user for the approval chunk
amended_agreement_status = ''
next_approval_user_pin = ''
next_approval_user_name = ''
next_approval_user_role = ''
# Recommender and approver approval (Test cases 10-11)
recommender_approval_message = ''
approver_pin = ''
approver_name = ''
approver_approval_message = ''
final_agreement_status = ''
# Price to be reviewed colour (Test case 12)
price_review_row_color = ''


def erp_login(page, user_name):
    # ERP login with the ResetHub link
    reset_page = ResetHubPage(page)
    link = reset_page.generate_reset_link(env=proj_env, username=user_name)
    reset_page.open_generated_link(link)
    assert isinstance(link, str) and link.startswith("http")
    print(f"Logging in as user: {user_name}")


def attach_stored_information(title, values):
    # One click in the report shows all stored values of this group in a table
    rows = "".join(f"<tr><th style='text-align:left;padding:4px 12px'>{html.escape(str(label))}</th>"
                   f"<td style='padding:4px 12px'>{html.escape('' if value is None else str(value))}</td></tr>"
                   for label, value in values.items())
    allure.attach(f"<h3>{html.escape(title)}</h3><table border='1' style='border-collapse:collapse'>"
                  f"{rows}</table>", name=title, attachment_type=allure.attachment_type.HTML)


def erp_logout(page, screenshot_name):
    # Exit and log out from ERP
    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot(screenshot_name)
    m_page.wait_for_timeout(2000)


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Framework List")
@allure.title("Test_case_1: Find the framework agreement initiator")
@allure.description("Test case 1: The admin searches the Marketplace whitelisted Framework Agreement in the "
                    "Framework List and gets the initiator who will initiate the amendment.")
@pytest.mark.order(1)
def test_1_find_framework_agreement_initiator(page):
    """
    Test case 1: Find the framework agreement initiator.

    Steps:
        1. Log in to ERP as the admin ('proc_admin') and go to Procurement.
        2. Purchase Order > Framework Agreement > Framework List.
        3. Search the agreement ('agreement_number') and find the exact agreement row
           (base FA No. with an optional /V1, /V2 version; next pages / page size 100 if needed).
        4. Get the initiator from the Initiator column and store it with the full ERP FA No.
        5. Exit and log out from ERP.
    """
    global agreement_fa_no, agreement_initiator_id, agreement_initiator_name
    required_env_values = {
        "test_env": proj_env,
        "test_proc_admin": proc_admin,
        "test_agreement_number": agreement_number,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    base_fa_no = agreement_number.strip().split("/V")[0]
    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    framework_list = FrameworkList(page)

    # Step 1: Log in as the admin
    with allure.step(f"Step 1: Log in to ERP as admin {proc_admin}"):
        erp_login(page, proc_admin)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('agreement_admin_dashboard')

    # Step 2: Framework List
    with allure.step("Step 2: Go to Purchase Order > Framework Agreement > Framework List"):
        proc_home_page.goto_framework_agreement_list()
        framework_list.get_full_page_screenshot('agreement_framework_list')

    # Step 3: Search the agreement and find the exact agreement row
    with allure.step(f"Step 3: Search agreement {base_fa_no} and find the exact agreement"):
        framework_list.search_agreement_with_enter(base_fa_no)
        agreement_row, agreement_fa_no = framework_list.find_exact_agreement_row(base_fa_no)
        framework_list.highlight_element(agreement_row)
        framework_list.get_full_page_screenshot('agreement_found')

    # Step 4: Initiator of the agreement
    with allure.step(f"Step 4: Get the initiator of {agreement_fa_no}"):
        agreement_initiator_id, agreement_initiator_name = framework_list.get_row_initiator(agreement_row)
        print("AGREEMENT FA NO:", agreement_fa_no)
        print("AGREEMENT INITIATOR:", agreement_initiator_id, "-", agreement_initiator_name)
        allure.attach(
            f"Agreement searched: {base_fa_no}\nERP FA No.: {agreement_fa_no}\n"
            f"Initiator ID: {agreement_initiator_id}\nInitiator name: {agreement_initiator_name}",
            name="Agreement initiator",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 5: Exit and log out
    with allure.step("Step 5: Exit and log out from ERP"):
        erp_logout(page, 'agreement_admin_logout')


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Pre-amendment Data Capture")
@allure.title("Test_case_2: Capture framework agreement data before the amendment")
@allure.description("Test case 2: The initiator opens the exact framework agreement and captures the framework "
                    "information, attachment and the first two items (with delivery location) before the amendment.")
@pytest.mark.order(2)
def test_2_capture_agreement_data_before_amendment(page, new_tab):
    """
    Test case 2: Capture the pre-amendment data.

    Steps:
        1. Log in to ERP as the agreement initiator (Test case 1) and go to the Framework List.
        2. Search the agreement, find the exact agreement and open it in a new tab.
        3. Capture FA No., vendor name, From/To/Price Review Date, Applicable For and approver name.
        4. Download the existing attachment (record the message if there is no attachment).
        5. Capture the first two items and the delivery location of each item (item details popup).
        6. One-click report views: Framework Information, Item 1, Item 2 and all stored information.
        No logout: Test case 3 starts the amendment on the same agreement tab.
    """
    global agreement_tab, framework_info_before, attachment_before, attachment_before_message, items_before, \
        marketplace_products_before
    assert agreement_initiator_id, "Test case 1 must pass first: no agreement initiator available"

    base_fa_no = agreement_number.strip().split("/V")[0]
    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    framework_list = FrameworkList(page)

    # Step 1: Log in as the agreement initiator
    with allure.step(f"Step 1: Log in to ERP as agreement initiator {agreement_initiator_id} "
                     f"({agreement_initiator_name})"):
        erp_login(page, agreement_initiator_id)
        proc_dashboard_page.goto_procurement()
        proc_home_page.goto_framework_agreement_list()
        framework_list.get_full_page_screenshot('agreement_initiator_framework_list')

    # Step 2: Find the exact agreement and open it
    with allure.step(f"Step 2: Search agreement {base_fa_no} and open the exact agreement"):
        framework_list.search_agreement_with_enter(base_fa_no)
        agreement_row, fa_no_in_list = framework_list.find_exact_agreement_row(base_fa_no)
        agreement_tab = new_tab(lambda p: agreement_row.locator("a[onclick^='showDetails']").click())
        agreement_tab.wait_for_timeout(5000)
        framework_info = FrameworkInformation(agreement_tab)
        framework_info.get_full_page_screenshot('agreement_details_before_amendment')

    # Step 3: Framework information
    with allure.step(f"Step 3: Capture framework information of {fa_no_in_list}"):
        framework_info_before = framework_info.get_framework_information_values()

    # Step 4: Attachment before the amendment
    with allure.step("Step 4: Download the existing attachment"):
        attachment_before, attachment_before_message = framework_info.download_attachment(
            os.path.join(os.getcwd(), "artifacts", "downloads", "before_amendment"))
        if attachment_before:
            allure.attach.file(attachment_before,
                               name=f"Attachment before amendment - {Path(attachment_before).name}")

    # Step 5: First two items and their delivery locations
    with allure.step("Step 5: Capture the first two items and their delivery locations"):
        item_rows = framework_info.get_item_rows()
        assert item_rows.count() >= ITEMS_TO_CAPTURE, \
            f"Expected at least {ITEMS_TO_CAPTURE} items in Framework Item Details, found {item_rows.count()}"
        items_before = []
        marketplace_products_before = []
        for index in range(ITEMS_TO_CAPTURE):
            item_row = item_rows.nth(index)
            item_values = framework_info.get_item_values(item_row)
            item_values["Delivery Location"] = framework_info.get_item_delivery_location(item_row)
            # Marketplace shows the product as Product Name - Delivery Location
            item_values["Marketplace Product"] = f"{item_values['Item Name']} - {item_values['Delivery Location']}"
            items_before.append(item_values)
            marketplace_products_before.append(item_values["Marketplace Product"])
            print(f"Item {index + 1}: {item_values}")

    # Step 6: One-click views of the stored information
    with allure.step("Step 6: Stored information (one click per group)"):
        framework_values = dict(framework_info_before)
        framework_values["Attachment"] = attachment_before_message
        attach_stored_information("Framework Information - View Stored Information", framework_values)
        for index, item_values in enumerate(items_before, start=1):
            attach_stored_information(f"Item {index} - View Stored Information", item_values)
        all_stored_information = {f"Framework - {label}": value for label, value in framework_values.items()}
        for index, item_values in enumerate(items_before, start=1):
            all_stored_information.update({f"Item {index} - {label}": value for label, value in item_values.items()})
        attach_stored_information("All Stored Information (Before Amendment)", all_stored_information)


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Start Amendment")
@allure.title("Test_case_3: Enter the amendment comment and click Amendment")
@allure.description("Test case 3: After all pre-amendment data is captured, the initiator enters the global "
                    "amendment comment (max 300 characters) and clicks Amendment.")
@pytest.mark.order(3)
def test_3_start_agreement_amendment(page):
    """
    Test case 3: Start the amendment (continues on the agreement tab of Test case 2).

    Steps:
        1. Validate the global amendment comment (max 300 characters) and enter it in Comments.
        2. Click Amendment and record the confirmation message.
    """
    global amendment_message
    assert agreement_tab and framework_info_before and len(items_before) == ITEMS_TO_CAPTURE, \
        "Test case 2 must pass first: pre-amendment data is not captured"
    assert amendment_comment, "Missing in .env: test_amendment_comment"
    assert len(amendment_comment) <= MAX_AMENDMENT_COMMENT_LENGTH, \
        f"test_amendment_comment must be max {MAX_AMENDMENT_COMMENT_LENGTH} characters, found {len(amendment_comment)}"

    framework_info = FrameworkInformation(agreement_tab)

    # Step 1: Amendment comment
    with allure.step(f"Step 1: Enter amendment comment '{amendment_comment}' ({len(amendment_comment)} characters)"):
        framework_info.enter_agreement_comments(comments=amendment_comment)
        framework_info.get_full_page_screenshot('agreement_amendment_comment')

    # Step 2: Amendment
    with allure.step("Step 2: Click Amendment"):
        amendment_message = framework_info.confirm_agreement_amendment_with_message()
        framework_info.get_full_page_screenshot('agreement_amendment_confirmed')
        attach_stored_information("Amendment - View Stored Information",
                                  {"Comment": amendment_comment, "Confirmation message": amendment_message})


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Amendment Status")
@allure.title("Test_case_4: Verify the agreement status and reviewer after the amendment")
@allure.description("Test case 4: Back in the Framework List, search the same agreement and capture the "
                    "agreement status and reviewer information after initiating the amendment.")
@pytest.mark.order(4)
def test_4_verify_agreement_status_and_reviewer(page):
    """
    Test case 4: Agreement status and reviewer after the amendment.

    Steps:
        1. Close the Framework Agreement details tab and return to the Framework List.
        2. Search the same base FA No. and find the exact agreement.
        3. Capture Agreement Status, Reviewer PIN, Reviewer Name and Reviewer Designation (one grouped output).
        4. Validate the agreement moved to the review status.
        No logout: the reviewer is used in the next automation chunk.
    """
    global agreement_status_info
    assert amendment_message, "Test case 3 must pass first: the amendment is not started"

    base_fa_no = agreement_number.strip().split("/V")[0]
    framework_list = FrameworkList(page)

    # Step 1: Close the details tab and return to the Framework List
    with allure.step("Step 1: Close the Framework Agreement details tab and return to the Framework List"):
        if agreement_tab and not agreement_tab.is_closed():
            agreement_tab.close()
        page.bring_to_front()
        page.reload()
        page.wait_for_timeout(5000)
        framework_list.get_full_page_screenshot('agreement_framework_list_after_amendment')

    # Step 2: Search the same agreement
    with allure.step(f"Step 2: Search agreement {base_fa_no} and find the exact agreement"):
        framework_list.search_agreement_with_enter(base_fa_no)
        agreement_row, fa_no_in_list = framework_list.find_exact_agreement_row(base_fa_no)
        framework_list.highlight_element(agreement_row)
        framework_list.get_full_page_screenshot('agreement_status_after_amendment')

    # Step 3: Status and reviewer
    with allure.step(f"Step 3: Capture the status and reviewer of {fa_no_in_list}"):
        agreement_status_info = framework_list.get_row_status_info(agreement_row)
        attach_stored_information("Agreement Status and Reviewer - View Stored Information",
                                  dict({"FA No.": fa_no_in_list}, **agreement_status_info))

    # Step 4: Validate the review status
    with allure.step(f"Step 4: Validate status '{agreement_status_info['Agreement Status']}' is the review status"):
        assert agreement_status_info["Agreement Status"].lower().startswith(EXPECTED_STATUS_AFTER_AMENDMENT.lower()), \
            f"Agreement {fa_no_in_list} is not in '{EXPECTED_STATUS_AFTER_AMENDMENT}' status after the amendment: " \
            f"{agreement_status_info['Agreement Status']}"
        assert agreement_status_info["Reviewer PIN"], f"No reviewer found for {fa_no_in_list}"


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Open Amendment Edit Page")
@allure.title("Test_case_5: Open the amended framework agreement edit page")
@allure.description("Test case 5: Open the amended framework agreement, validate its status, enter the edit "
                    "comment and click Edit to open the amendment edit page (no data is modified).")
@pytest.mark.order(5)
def test_5_open_amended_agreement_edit_page(page, new_tab):
    """
    Test case 5: Open the amended agreement and its edit page (continues after Test case 4).

    Steps:
        1. From the Framework List search result, open the same agreement (FA No. link) in a new tab
           (log in as the reviewer first if the reviewer is not the logged-in user).
        2. Confirm the Framework Information page shows the correct agreement.
        3. Capture and validate the current status (Reviewed (Amendment)).
        4. Enter the global edit comment (max 300 characters).
        5. Click Edit.
        6. Verify the Framework Agreement amendment/edit page is opened.
        7. Confirm the correct FA No. on the edit page. No agreement data is modified here.
    """
    global edit_page_tab, agreement_status_before_edit
    assert agreement_status_info.get("Reviewer PIN"), "Test case 4 must pass first: no reviewer available"
    assert agreement_edit_comment, "Missing in .env: test_agreement_edit_comment"
    assert len(agreement_edit_comment) <= MAX_AMENDMENT_COMMENT_LENGTH, \
        f"test_agreement_edit_comment must be max {MAX_AMENDMENT_COMMENT_LENGTH} characters, " \
        f"found {len(agreement_edit_comment)}"

    base_fa_no = agreement_number.strip().split("/V")[0]
    reviewer_pin = agreement_status_info["Reviewer PIN"]
    framework_list = FrameworkList(page)

    # Step 1: Open the agreement from the Framework List search result
    with allure.step(f"Step 1: Open agreement {base_fa_no} from the Framework List as reviewer {reviewer_pin} "
                     f"({agreement_status_info['Reviewer Name']})"):
        if reviewer_pin != agreement_initiator_id:
            # The Edit button is for the reviewer: log in as the reviewer
            erp_logout(page, 'agreement_initiator_logout_before_review')
            erp_login(page, reviewer_pin)
            DashboardPage(page).goto_procurement()
            ProcurementHomePage(page).goto_framework_agreement_list()
            framework_list.search_agreement_with_enter(base_fa_no)
        agreement_row, fa_no_in_list = framework_list.find_exact_agreement_row(base_fa_no)
        edit_page_tab = new_tab(lambda p: agreement_row.locator("a[onclick^='showDetails']").click())
        edit_page_tab.wait_for_timeout(5000)
        framework_info = FrameworkInformation(edit_page_tab)

    # Step 2: Correct agreement opened
    with allure.step(f"Step 2: Confirm Framework Information of {fa_no_in_list} is opened"):
        fa_no_on_page = framework_info.get_field_value("FA No.")
        framework_info.get_full_page_screenshot('amended_agreement_information')
        assert fa_no_on_page.split("/V")[0] == base_fa_no, \
            f"Wrong agreement opened: expected {base_fa_no}, found {fa_no_on_page}"

    # Step 3: Current status
    with allure.step("Step 3: Capture and validate the current agreement status"):
        agreement_status_before_edit = framework_info.get_field_value("Status")
        print("AGREEMENT STATUS BEFORE EDIT:", agreement_status_before_edit)
        assert EXPECTED_STATUS_BEFORE_EDIT.lower() in agreement_status_before_edit.lower(), \
            f"Agreement {fa_no_on_page} status is not '{EXPECTED_STATUS_BEFORE_EDIT}': {agreement_status_before_edit}"

    # Step 4: Edit comment
    with allure.step(f"Step 4: Enter comment '{agreement_edit_comment}' ({len(agreement_edit_comment)} characters)"):
        framework_info.enter_agreement_comments(comments=agreement_edit_comment)
        framework_info.get_full_page_screenshot('amended_agreement_edit_comment')

    # Step 5: Edit
    with allure.step("Step 5: Click Edit"):
        framework_info.edit_button.click()
        edit_page_tab.wait_for_load_state("load")

    # Step 6-7: Amendment edit page with the correct FA No.
    with allure.step("Step 6: Verify the Framework Agreement amendment edit page shows the correct FA No."):
        framework_agreement_information = FrameworkAgreementInformation(edit_page_tab)
        fwa_no_on_edit_page = framework_agreement_information.get_fwa_no()
        framework_agreement_information.get_screen_shot('amended_agreement_edit_page')
        attach_stored_information("Amendment Edit Page - View Stored Information", {
            "FA No. (Framework Information)": fa_no_on_page,
            "Status before edit": agreement_status_before_edit,
            "Edit comment": agreement_edit_comment,
            "FWA No. (edit page)": fwa_no_on_edit_page,
            "Edit page URL": edit_page_tab.url,
        })
        assert "/frameworkAgreement/show/" in edit_page_tab.url, \
            f"Framework Agreement edit page is not opened: {edit_page_tab.url}"
        assert fwa_no_on_edit_page.split("/V")[0] == base_fa_no, \
            f"Wrong FA No. on the edit page: expected {base_fa_no}, found {fwa_no_on_edit_page}"


def item_code_of(item_name):
    # "[FWI044746]-Basin Waste 4"" -> "[FWI044746]"
    return item_name.split("]")[0] + "]" if item_name.startswith("[") else item_name


def to_price(value):
    # Price text -> Decimal with 2 decimal places (e.g. "17" -> 17.00)
    return Decimal(str(value).replace(",", "").strip() or "0").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def update_item_price(agreement_information, item_row, increase):
    # Item 1: add test_unit_price_change (on MRP Price when MRP pricing is used, otherwise on Unit Price).
    # Item 2: new Unit Price = random 2-decimal price in the .env range (MRP pricing: MRP set for that price).
    # Returns the Unit Price shown by the system.
    price_fields = agreement_information.get_item_price_fields(item_row)
    mrp_pricing = price_fields["mode"] == "MRP + Discount"
    if increase:
        price_field = price_fields["mrp"] if mrp_pricing else price_fields["unit_price"]
        new_value = to_price(price_field.input_value()) + Decimal(unit_price_change)
        agreement_information.set_input_value(price_field, f"{new_value:.2f}")
    else:
        min_cents = int(Decimal(item_2_unit_price_min) * 100)
        max_cents = int(Decimal(item_2_unit_price_max) * 100)
        new_price = Decimal(random.randint(min_cents, max_cents - 1)) / 100
        if mrp_pricing:
            # Discount must stay between 0 and 100: keep it and set MRP so that Unit Price = new price
            discount = Decimal(price_fields["discount"].input_value().strip())
            mrp = (new_price / (1 - discount / 100)).quantize(Decimal("0.01"), rounding=ROUND_UP)
            agreement_information.set_input_value(price_fields["mrp"], f"{mrp:.2f}")
        else:
            agreement_information.set_input_value(price_fields["unit_price"], f"{new_price:.2f}")
    return price_fields["mode"], to_price(agreement_information.get_item_unit_price(item_row, price_fields))


def check_moq_zero_rule(agreement_information, item_row, dialog_messages):
    # MOQ = 0 must be rejected: capture the alert/message, then set MOQ = 1
    moq_input = agreement_information.get_item_moq_input(item_row)
    messages_before = len(dialog_messages)
    agreement_information.set_input_value(moq_input, "0")
    moq_message = " | ".join(dialog_messages[messages_before:]) or agreement_information.get_visible_message() \
        or "No validation message shown"
    print(f"MOQ = 0 validation message: {moq_message}")
    agreement_information.set_input_value(moq_input, MOQ_AFTER_AMENDMENT)
    final_moq = moq_input.input_value().strip()
    assert final_moq == MOQ_AFTER_AMENDMENT, f"MOQ must be {MOQ_AFTER_AMENDMENT}, found {final_moq}"
    return moq_message, final_moq


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Update Amendment Information")
@allure.title("Test_case_6: Update the framework agreement and items for the amendment")
@allure.description("Test case 6: On the amendment edit page update End Date, Price Review Date, attachment, "
                    "Applicable For and the two stored items (specification, unit price, MOQ), and store every "
                    "previous/updated value for the ERP and Marketplace verification. Update & Next is not clicked.")
@pytest.mark.order(6)
def test_6_update_framework_amendment_information(page):
    """
    Test case 6: Update the amendment information (continues on the edit page of Test case 5).

    Steps:
        1. End Date = today + 'test_end_date_years' years.
        2. Price Review Date: a past date first (capture the validation message), then today.
        3. Upload the amendment attachment ('test_amendment_attachment_file').
        4. Applicable For: store the previous value and select Both.
        5. Item 1: replace the specification (global, max 500 characters), increase the Unit Price.
        6. Item 2: keep the specification, decrease the Unit Price.
        7. MOQ for both items: 0 (capture the alert/message), then 1.
        8. Store previous/updated values: specification, unit price, agreement version, attachment.
        Update & Next is not clicked here (submission is the next chunk).
    """
    global amendment_updates, item_updates
    assert edit_page_tab and not edit_page_tab.is_closed(), "Test case 5 must pass first: no amendment edit page"
    assert len(items_before) == ITEMS_TO_CAPTURE, "Test case 2 must pass first: no stored items"
    required_env_values = {
        "test_end_date_years": end_date_years,
        "test_amendment_attachment_file": amendment_attachment_file,
        "test_item_updated_specification": item_updated_specification,
        "test_unit_price_change": unit_price_change,
        "test_item_2_unit_price_min": item_2_unit_price_min,
        "test_item_2_unit_price_max": item_2_unit_price_max,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    assert len(item_updated_specification) <= MAX_SPECIFICATION_LENGTH, \
        f"test_item_updated_specification must be max {MAX_SPECIFICATION_LENGTH} characters, " \
        f"found {len(item_updated_specification)}"
    # Unit price change: positive number with max 2 decimals (e.g. 100.99), no characters/negative value
    assert re.fullmatch(r"\d+(\.\d{1,2})?", unit_price_change) and Decimal(unit_price_change) > 0, \
        f"test_unit_price_change must be a positive price with max 2 decimals (e.g. 100.99), found {unit_price_change}"
    attachment_path = UTILS_DIR / amendment_attachment_file
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"

    agreement_information = FrameworkAgreementInformation(edit_page_tab)
    # Browser alerts on the edit page (registered once for Test cases 6-8): record the message and accept it
    global edit_page_dialog_messages
    dialog_messages = edit_page_dialog_messages
    edit_page_tab.on("dialog", lambda dialog: (dialog_messages.append(dialog.message), dialog.accept()))
    today = datetime.today()
    amendment_updates = {}

    # Step 1: End Date
    with allure.step(f"Step 1: Set End Date to {end_date_years} years from today"):
        end_date = today.replace(year=today.year + int(end_date_years))
        amendment_updates["End Date"] = {"previous": framework_info_before["To Date"],
                                         "updated": agreement_information.pick_date(
                                             agreement_information.end_date_picker,
                                             agreement_information.end_date, end_date)}
        assert amendment_updates["End Date"]["updated"] == end_date.strftime("%d-%m-%Y"), \
            f"End Date must be {end_date:%d-%m-%Y}, found {amendment_updates['End Date']['updated']}"
        agreement_information.get_screen_shot('amendment_end_date')

    # Step 2: Price Review Date (past date validation, then today)
    with allure.step("Step 2: Price Review Date: validate a past date, then set today"):
        messages_before = len(dialog_messages)
        past_date = today - timedelta(days=1)
        past_date_result = agreement_information.pick_date(
            agreement_information.price_review_date_picker, agreement_information.price_review_date, past_date)
        if past_date_result is None:
            price_review_message = "Past date is disabled in the date picker"
        else:
            price_review_message = " | ".join(dialog_messages[messages_before:]) \
                or agreement_information.get_visible_message() or "No validation message shown"
        print(f"Price Review Date {past_date:%d-%m-%Y} validation: {price_review_message}")
        agreement_information.get_screen_shot('amendment_price_review_past_date')
        amendment_updates["Price Review Date validation"] = {"previous": f"{past_date:%d-%m-%Y}",
                                                             "updated": price_review_message}
        amendment_updates["Price Review Date"] = {"previous": framework_info_before["Price Review Date"],
                                                  "updated": agreement_information.pick_date(
                                                      agreement_information.price_review_date_picker,
                                                      agreement_information.price_review_date, today)}
        assert amendment_updates["Price Review Date"]["updated"] == today.strftime("%d-%m-%Y"), \
            f"Price Review Date must be {today:%d-%m-%Y}, found {amendment_updates['Price Review Date']['updated']}"

    # Step 3: Amendment attachment
    with allure.step(f"Step 3: Upload amendment attachment {attachment_path.name}"):
        selected_attachment = agreement_information.upload_amendment_attachment(str(attachment_path))
        assert selected_attachment.endswith(attachment_path.name), \
            f"Attachment {attachment_path.name} is not selected, found '{selected_attachment}'"
        amendment_updates["Attachment"] = {
            "previous": Path(attachment_before).name if attachment_before else attachment_before_message,
            "updated": selected_attachment}

    # Step 4: Applicable For
    with allure.step("Step 4: Applicable For: store the previous value and select Both"):
        previous_applicable_for = agreement_information.get_selected_applicable_for()
        updated_applicable_for = agreement_information.select_applicable_for_both()
        assert updated_applicable_for == "Both", f"Applicable For is not Both: {updated_applicable_for}"
        amendment_updates["Applicable For"] = {"previous": previous_applicable_for, "updated": updated_applicable_for}
        amendment_updates["Agreement Version"] = {"previous": agreement_fa_no,
                                                  "updated": agreement_information.get_fwa_no()}
        agreement_information.get_screen_shot('amendment_header_updated')

    # Step 5-7: Items (Item 1: new specification + higher price, Item 2: same specification + lower price)
    item_updates = []
    for index, item_before in enumerate(items_before, start=1):
        increase = index == 1
        with allure.step(f"Step {4 + index}: Item {index} {item_before['Item Name']}: "
                         f"{'replace specification, increase' if increase else 'keep specification, decrease'} "
                         f"Unit Price, MOQ 0 -> {MOQ_AFTER_AMENDMENT}"):
            item_code = item_code_of(item_before["Item Name"])
            item_row = agreement_information.get_item_row(item_code)
            updated_specification = agreement_information.update_item_specification(
                item_row, item_code, item_updated_specification if increase else None)
            price_before = to_price(item_before["Unit Price"])
            pricing_mode, updated_price = update_item_price(agreement_information, item_row, increase)
            if not increase:
                assert Decimal(item_2_unit_price_min) <= updated_price <= Decimal(item_2_unit_price_max), \
                    f"Item 2 Unit Price must be {item_2_unit_price_min} - {item_2_unit_price_max}, found {updated_price}"
            else:
                assert updated_price > price_before, \
                    f"Item 1 Unit Price must be higher than {price_before}, found {updated_price}"
            moq_message, final_moq = check_moq_zero_rule(agreement_information, item_row, dialog_messages)
            item_update = {
                "Item Name": item_before["Item Name"],
                "Specification": {"previous": item_before["Specification"], "updated": updated_specification},
                "Unit Price": {"previous": f"{price_before:.2f}", "updated": f"{updated_price:.2f}"},
                "Pricing": pricing_mode,
                "MOQ": {"previous": item_before["MOQ"], "updated": final_moq},
                "MOQ = 0 validation message": moq_message,
            }
            item_updates.append(item_update)
            agreement_information.get_screen_shot(f'amendment_item_{index}_updated')
            attach_stored_information(f"Item {index} - Updated Information (previous / updated)", {
                label: (f"{value['previous']}  ->  {value['updated']}" if isinstance(value, dict) else value)
                for label, value in item_update.items()})

    # Step 8: Previous / updated values (one click)
    with allure.step("Step 8: Store previous/updated values"):
        attach_stored_information("Amendment Updates (previous / updated)", {
            label: f"{value['previous']}  ->  {value['updated']}" for label, value in amendment_updates.items()})
        print("AMENDMENT UPDATES:", amendment_updates)
        print("ITEM UPDATES:", item_updates)


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Update & Next")
@allure.title("Test_case_7: Click Update & Next on the amendment edit page")
@allure.description("Test case 7: After the amendment information is updated, click Update & Next, confirm the "
                    "confirmation (if shown) and wait for the Output Document page.")
@pytest.mark.order(7)
def test_7_click_update_and_next(page):
    """
    Test case 7: Update & Next (continues on the edit page of Test case 6).

    Steps:
        1. Click Update & Next >>.
        2. If a confirmation dialog/message appears: capture the exact message and confirm it.
        3. Wait until the Output Document page is loaded and record the system message.
    """
    global update_next_confirmation_message
    assert amendment_updates and len(item_updates) == ITEMS_TO_CAPTURE, \
        "Test case 6 must pass first: the amendment information is not updated"

    agreement_information = FrameworkAgreementInformation(edit_page_tab)
    # Alerts are recorded by the handler registered in Test case 6
    dialog_messages = edit_page_dialog_messages

    # Step 1: Update & Next
    with allure.step("Step 1: Click Update & Next >>"):
        agreement_information.get_screen_shot('amendment_before_update_and_next')
        agreement_information.update_and_next_button.click()
        edit_page_tab.wait_for_timeout(3000)

    # Step 2: Confirmation (browser alert or confirmation popup)
    with allure.step("Step 2: Capture and confirm the confirmation message (if shown)"):
        popup_message = agreement_information.confirm_visible_popup()
        update_next_confirmation_message = " | ".join(dialog_messages + ([popup_message] if popup_message else [])) \
            or "No confirmation shown"
        print("UPDATE & NEXT CONFIRMATION:", update_next_confirmation_message)

    # Step 3: Output Document page (the message is read first, so a failure shows the ERP message)
    with allure.step("Step 3: Wait for the Output Document page"):
        update_message = agreement_information.get_visible_message() or "No message shown"
        output_document_opened = agreement_information.is_output_document_page_opened()
        agreement_information.get_screen_shot('amendment_after_update_and_next')
        assert output_document_opened, f"Output Document page is not opened after Update & Next: {update_message}"
        print("UPDATE & NEXT MESSAGE:", update_message)
        agreement_information.get_screen_shot('amendment_output_document_page')
        attach_stored_information("Update & Next - View Stored Information", {
            "FA No.": amendment_updates["Agreement Version"]["updated"],
            "Confirmation message": update_next_confirmation_message,
            "System message": update_message,
            "Page URL": edit_page_tab.url,
        })


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Output Document and Submit")
@allure.title("Test_case_8: Update the Output Document and submit the amendment")
@allure.description("Test case 8: Set the Recommender and Approver on the Output Document page (capture the "
                    "role validation alert if shown), submit the amendment and return to the Framework List tab.")
@pytest.mark.order(8)
def test_8_update_output_document_and_submit_amendment(page):
    """
    Test case 8: Output Document and submission (continues on the Output Document page of Test case 7).

    Steps:
        1. Recommender: select the checkbox only if not selected, select the configured Recommender by PIN.
        2. Approver: clear and select the configured Approver by PIN.
        3. Role validation alert (Recommender role > Approver role): capture it and stop.
        4. Submit > Submit Confirmation (capture message) > Submit > capture the final message.
        5. Close the amendment tab and return to the previous (Framework List) tab.
    """
    global selected_recommender_info, selected_approver_info, role_validation_alert_message, \
        submit_confirmation_message, final_submission_message, submitted_agreement_no
    assert update_next_confirmation_message, "Test case 7 must pass first: the Output Document page is not opened"
    required_env_values = {
        "test_amended_agreement_recommender": amended_agreement_recommender,
        "test_amended_agreement_approver": amended_agreement_approver,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    agreement_information = FrameworkAgreementInformation(edit_page_tab)
    # Alerts are recorded by the handler registered in Test case 6
    dialog_messages = edit_page_dialog_messages

    # Step 1: Recommender and Approver
    with allure.step(f"Step 1: Select Recommender {amended_agreement_recommender} and "
                     f"Approver {amended_agreement_approver}"):
        messages_before = len(dialog_messages)
        agreement_information.ensure_recommender_checked()
        selected_recommender_info = agreement_information.select_user_by_pin(
            agreement_information.recommender_textbox, amended_agreement_recommender)
        selected_approver_info = agreement_information.select_user_by_pin(
            agreement_information.approver_textbox, amended_agreement_approver)
        agreement_information.get_screen_shot('amendment_recommender_approver')

    # Step 2: Role validation alert (ERP decides the Recommender/Approver hierarchy)
    with allure.step("Step 2: Check the Recommender/Approver role validation"):
        role_validation_alert_message = " | ".join(dialog_messages[messages_before:]) or "No role validation alert"
        print("ROLE VALIDATION:", role_validation_alert_message)
        assert len(dialog_messages) == messages_before, \
            f"ERP does not accept Recommender {amended_agreement_recommender} / Approver " \
            f"{amended_agreement_approver}: {role_validation_alert_message}"

    # Step 3: Submit
    with allure.step("Step 3: Submit the amendment"):
        submit_confirmation_message, final_submission_message = agreement_information.submit_with_confirmation()
        agreement_information.get_screen_shot('amendment_submitted')
        assert "success" in final_submission_message.lower(), \
            f"Amendment is not submitted: {final_submission_message}"
        submitted_agreement_no = amendment_updates["Agreement Version"]["updated"]
        attach_stored_information("Submission - View Stored Information", {
            "Agreement No.": submitted_agreement_no,
            "Recommender": selected_recommender_info,
            "Approver": selected_approver_info,
            "Update & Next confirmation": update_next_confirmation_message,
            "Role validation alert": role_validation_alert_message,
            "Submit confirmation": submit_confirmation_message,
            "Final message": final_submission_message,
        })

    # Step 4: Close the amendment tab and return to the previous tab
    with allure.step("Step 4: Close the amendment tab and return to the Framework List tab"):
        edit_page_tab.close()
        page.bring_to_front()
        assert page.evaluate("() => document.visibilityState") == "visible", "The previous tab is not active"
        print(f"Active tab: {page.url}")


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Approval Status")
@allure.title("Test_case_9: Get the amended agreement approval status and next approval user")
@allure.description("Test case 9: Search the submitted agreement (exact FA No.) in the Framework List and store "
                    "the current status and the user responsible for the next approval.")
@pytest.mark.order(9)
def test_9_get_amended_agreement_approval_status(page):
    """
    Test case 9: Approval status after submission (continues on the Framework List tab of Test case 8).

    Steps:
        1. Search the exact submitted agreement number.
        2. Capture the status and the responsible user from the Status column.
        3. Store the responsible user as the next approval user (PIN, name, role).
    """
    global amended_agreement_status, next_approval_user_pin, next_approval_user_name, next_approval_user_role
    assert submitted_agreement_no and final_submission_message, "Test case 8 must pass first: no submitted agreement"
    framework_list = FrameworkList(page)

    # Step 1: Search the exact agreement number
    with allure.step(f"Step 1: Search agreement {submitted_agreement_no} (exact FA No.)"):
        page.reload()
        page.wait_for_timeout(5000)
        framework_list.search_agreement_with_enter(submitted_agreement_no)
        agreement_row, fa_no_in_list = framework_list.find_exact_agreement_row(submitted_agreement_no)
        framework_list.highlight_element(agreement_row)
        framework_list.get_full_page_screenshot('amended_agreement_approval_status')

    # Step 2: Status and the responsible user (the next approval user)
    with allure.step(f"Step 2: Capture the status and the responsible user of {fa_no_in_list}"):
        status_info = framework_list.get_row_status_info(agreement_row)
        amended_agreement_status = status_info["Agreement Status"]
        next_approval_user_pin = status_info["Reviewer PIN"]
        next_approval_user_name = status_info["Reviewer Name"]
        next_approval_user_role = status_info["Reviewer Designation"]
        print(f"NEXT APPROVAL USER: {next_approval_user_pin} - {next_approval_user_name} ({amended_agreement_status})")
        attach_stored_information("Approval Status - View Stored Information", {
            "Agreement No.": fa_no_in_list,
            "Agreement Status": amended_agreement_status,
            "Next approval user PIN": next_approval_user_pin,
            "Next approval user name": next_approval_user_name,
            "Next approval user role": next_approval_user_role,
        })
        assert next_approval_user_pin, f"No responsible user in the status of {fa_no_in_list}: {amended_agreement_status}"


def approve_agreement_as(page, new_tab, user_pin, role):
    # Log in as the user, open the exact agreement, enter the approval comment and approve.
    # Returns the approval message and the status/next user shown in the Framework List afterwards.
    framework_list = FrameworkList(page)
    erp_login(page, user_pin)
    DashboardPage(page).goto_procurement()
    ProcurementHomePage(page).goto_framework_agreement_list()
    framework_list.search_agreement_with_enter(submitted_agreement_no)
    agreement_row, fa_no_in_list = framework_list.find_exact_agreement_row(submitted_agreement_no)

    agreement_tab = new_tab(lambda p: agreement_row.locator("a[onclick^='showDetails']").click())
    agreement_tab.wait_for_timeout(5000)
    framework_info = FrameworkInformation(agreement_tab)
    framework_info.enter_agreement_comments(comments=agreement_approval_comment)
    framework_info.get_full_page_screenshot(f'amendment_{role}_approval_comment')
    approval_message = framework_info.confirm_agreement_approval().strip()
    framework_info.get_full_page_screenshot(f'amendment_{role}_approved')
    agreement_tab.close()
    page.bring_to_front()

    page.reload()
    page.wait_for_timeout(5000)
    framework_list.search_agreement_with_enter(submitted_agreement_no)
    agreement_row, fa_no_in_list = framework_list.find_exact_agreement_row(submitted_agreement_no)
    framework_list.get_full_page_screenshot(f'amendment_status_after_{role}_approval')
    return approval_message, framework_list.get_row_status_info(agreement_row)


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Recommender Approval")
@allure.title("Test_case_10: Recommender approves the amended framework agreement")
@allure.description("Test case 10: Log out as the amendment initiator, log in as the next approval user "
                    "(recommender), approve the agreement and get the next approval user (approver).")
@pytest.mark.order(10)
def test_10_recommender_approves_amended_agreement(page, new_tab):
    """
    Test case 10: Recommender approval (continues on the Framework List tab of Test case 9).

    Steps:
        1. Exit and log out as the amendment initiator.
        2. Log in as the next approval user (Test case 9), open the agreement, enter the approval comment, approve.
        3. Get the status and the next approval user (approver) from the Framework List, then log out.
    """
    global recommender_approval_message, approver_pin, approver_name
    assert next_approval_user_pin, "Test case 9 must pass first: no next approval user"
    assert agreement_approval_comment, "Missing in .env: test_agreement_approval_comment"
    assert len(agreement_approval_comment) <= MAX_AMENDMENT_COMMENT_LENGTH, \
        f"test_agreement_approval_comment must be max {MAX_AMENDMENT_COMMENT_LENGTH} characters"

    # Step 1: Log out as the amendment initiator
    with allure.step("Step 1: Exit and log out as the amendment initiator"):
        erp_logout(page, 'amendment_initiator_logout')

    # Step 2: Recommender approval
    with allure.step(f"Step 2: Log in as recommender {next_approval_user_pin} ({next_approval_user_name}) "
                     f"and approve {submitted_agreement_no}"):
        recommender_approval_message, status_info = approve_agreement_as(
            page, new_tab, next_approval_user_pin, "recommender")
        print("RECOMMENDER APPROVAL MESSAGE:", recommender_approval_message)

    # Step 3: Next approval user (approver)
    with allure.step("Step 3: Get the next approval user (approver) and log out"):
        approver_pin = status_info["Reviewer PIN"]
        approver_name = status_info["Reviewer Name"]
        attach_stored_information("Recommender Approval - View Stored Information", {
            "Agreement No.": submitted_agreement_no,
            "Recommender": f"{next_approval_user_pin} - {next_approval_user_name}",
            "Approval comment": agreement_approval_comment,
            "Approval message": recommender_approval_message,
            "Status after approval": status_info["Agreement Status"],
            "Next approval user (approver)": f"{approver_pin} - {approver_name}",
        })
        erp_logout(page, 'amendment_recommender_logout')
        assert approver_pin, f"No approver in the status of {submitted_agreement_no}: {status_info['Agreement Status']}"


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Approver Approval")
@allure.title("Test_case_11: Approver approves the amended framework agreement")
@allure.description("Test case 11: Log in as the approver, approve the amended agreement and verify the final "
                    "agreement status.")
@pytest.mark.order(11)
def test_11_approver_approves_amended_agreement(page, new_tab):
    """
    Test case 11: Approver approval (after Test case 10).

    Steps:
        1. Log in as the approver (Test case 10), open the agreement, enter the approval comment, approve.
        2. Verify the final agreement status is approved, then log out.
    """
    global approver_approval_message, final_agreement_status
    assert approver_pin, "Test case 10 must pass first: no approver"

    # Step 1: Approver approval
    with allure.step(f"Step 1: Log in as approver {approver_pin} ({approver_name}) and approve {submitted_agreement_no}"):
        approver_approval_message, status_info = approve_agreement_as(page, new_tab, approver_pin, "approver")
        print("APPROVER APPROVAL MESSAGE:", approver_approval_message)

    # Step 2: Final status
    with allure.step("Step 2: Verify the final agreement status and log out"):
        final_agreement_status = status_info["Agreement Status"]
        print("FINAL AGREEMENT STATUS:", final_agreement_status)
        attach_stored_information("Approver Approval - View Stored Information", {
            "Agreement No.": submitted_agreement_no,
            "Approver": f"{approver_pin} - {approver_name}",
            "Approval comment": agreement_approval_comment,
            "Approval message": approver_approval_message,
            "Final agreement status": final_agreement_status,
        })
        erp_logout(page, 'amendment_approver_logout')
        assert EXPECTED_FINAL_STATUS.lower() in final_agreement_status.lower(), \
            f"Agreement {submitted_agreement_no} is not approved: {final_agreement_status}"


@allure.suite("Framework Agreement")
@allure.feature("Framework Agreement Amendment")
@allure.story("Price to be Reviewed")
@allure.title("Test_case_12: Approved agreement row shows the 'Price to be reviewed' colour")
@allure.description("Test case 12: After the amendment is submitted and approved, search the agreement in the "
                    "Framework List and verify its row colour matches the 'Price to be reviewed' legend colour.")
@pytest.mark.order(12)
def test_12_verify_price_to_be_reviewed_color(page):
    """
    Test case 12: 'Price to be reviewed' colour (after Test case 11).

    Steps:
        1. Log in to ERP as the admin ('proc_admin') and go to the Framework List.
        2. Search the approved agreement.
        3. Compare the agreement row colour with the 'Price to be reviewed' legend colour, then log out.
    """
    global price_review_row_color
    assert final_agreement_status, "Test case 11 must pass first: the agreement is not approved"
    framework_list = FrameworkList(page)

    # Step 1: Log in as the admin
    with allure.step(f"Step 1: Log in to ERP as admin {proc_admin} and go to the Framework List"):
        erp_login(page, proc_admin)
        DashboardPage(page).goto_procurement()
        ProcurementHomePage(page).goto_framework_agreement_list()

    # Step 2: Search the approved agreement
    with allure.step(f"Step 2: Search agreement {submitted_agreement_no}"):
        framework_list.search_agreement_with_enter(submitted_agreement_no)
        agreement_row, fa_no_in_list = framework_list.find_exact_agreement_row(submitted_agreement_no)
        framework_list.get_full_page_screenshot('agreement_price_to_be_reviewed_color')

    # Step 3: Row colour = 'Price to be reviewed' legend colour
    with allure.step(f"Step 3: Verify {fa_no_in_list} row colour is '{PRICE_TO_BE_REVIEWED_LEGEND}'"):
        legend_color = framework_list.get_price_review_legend_color()
        price_review_row_color = framework_list.get_row_color(agreement_row)
        print(f"Legend colour: {legend_color}, row colour: {price_review_row_color}")
        attach_stored_information("Price to be Reviewed - View Stored Information", {
            "Agreement No.": fa_no_in_list,
            "Price Review Date": amendment_updates["Price Review Date"]["updated"],
            "Legend colour (Price to be reviewed)": legend_color,
            "Agreement row colour": price_review_row_color,
        })
        erp_logout(page, 'agreement_price_review_logout')
        assert legend_color and price_review_row_color == legend_color, \
            f"Agreement {fa_no_in_list} row colour {price_review_row_color} does not match " \
            f"'{PRICE_TO_BE_REVIEWED_LEGEND}' colour {legend_color}"
