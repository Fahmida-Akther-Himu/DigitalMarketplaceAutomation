from dotenv import load_dotenv
import os
import re
from decimal import Decimal
from pathlib import Path

import pytest
import allure

load_dotenv()

# ERP Procurement staging (ResetHub login)
proj_env = os.getenv("test_env")
proj_user = os.getenv("test_user_name")
proc_admin = os.getenv("test_proc_admin")
# Framework agreement used in framework_agreement_amendment.py (base FA No., ERP may add /V1, /V2 ...)
agreement_number = os.getenv("test_agreement_number")
# Requisition information
requisition_project_name = os.getenv("test_requisition_project_name")
requisition_funding_source = os.getenv("test_requisition_funding_source")
requisition_funding_remarks = os.getenv("test_requisition_funding_remarks")
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
schedule_address = os.getenv("test_schedule_address")
# Item 1 and Item 2 requisition data
REQUISITION_ITEMS = [
    {"master_item": os.getenv("test_master_item_1"), "master_item_full_path": os.getenv("test_master_item_1_full_path"),
     "gl_code": os.getenv("test_item_gl_code_1"), "quantity": os.getenv("test_requisition_item_1_quantity"),
     "attachment": os.getenv("test_requisition_attachment_file")},
    {"master_item": os.getenv("test_master_item_2"), "master_item_full_path": os.getenv("test_master_item_2_full_path"),
     "gl_code": os.getenv("test_item_gl_code_2"), "quantity": os.getenv("test_requisition_item_2_quantity"),
     "attachment": os.getenv("test_requisition_attachment_file_2")},
]
ITEMS_TO_USE = 2
# Project root is 3 levels up: testcases/marketplace_requisition_creation/<this file>
UTILS_DIR = Path(__file__).resolve().parents[3] / "utils"

from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_list import FrameworkList
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_information import FrameworkInformation
from pages.erp_procurement.my_dashboard.procurement.requisition.create_requisition import CreateRequisition
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_list import RequisitionList
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_approve_list import RequisitionApproveList
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation

# Amended agreement data (Test case 1)
agreement_fa_no = ''
agreement_vendor = ''
agreement_items = []
# Requisition (Test cases 2-4)
requisition_items = []
req_num = ''
req_submission_message = ''
# Requisition approval (Test cases 5-9)
approver_id = ''
approver_id_2 = ''
approved_req_status = ''


def erp_login(page, user_name):
    # ERP login with the ResetHub link
    reset_page = ResetHubPage(page)
    link = reset_page.generate_reset_link(env=proj_env, username=user_name)
    reset_page.open_generated_link(link)
    assert isinstance(link, str) and link.startswith("http")
    print(f"Logging in as user: {user_name}")


def erp_logout(page, screenshot_name):
    # Exit and log out from ERP
    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot(screenshot_name)
    m_page.wait_for_timeout(2000)


def item_code_of(item_name):
    # "[FWI044746]-Basin Waste 4"" -> "FWI044746"
    return item_name.split("]")[0].lstrip("[").strip()


@allure.suite("Requisition")
@allure.feature("Framework Agreement Requisition")
@allure.story("Amended Agreement Data")
@allure.title("Test_case_1: Get the amended framework agreement items")
@allure.description("Test case 1: The admin opens the framework agreement used in the amendment test and stores "
                    "its first two items (the amended items) for the requisition.")
@pytest.mark.order(1)
def test_1_get_amended_agreement_items(page, new_tab):
    """
    Test case 1: Get the amended framework agreement items.

    Steps:
        1. Log in to ERP as the admin ('proc_admin') and go to the Framework List.
        2. Search the agreement ('agreement_number') and open the exact agreement.
        3. Store the FA No. and the first two items (the items updated in the amendment).
        4. Exit and log out from ERP.
    """
    global agreement_fa_no, agreement_vendor, agreement_items
    required_env_values = {"test_env": proj_env, "test_proc_admin": proc_admin,
                           "test_agreement_number": agreement_number}
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    base_fa_no = agreement_number.strip().split("/V")[0]
    framework_list = FrameworkList(page)

    # Step 1: Log in as the admin
    with allure.step(f"Step 1: Log in to ERP as admin {proc_admin} and go to the Framework List"):
        erp_login(page, proc_admin)
        DashboardPage(page).goto_procurement()
        ProcurementHomePage(page).goto_framework_agreement_list()

    # Step 2: Open the exact agreement
    with allure.step(f"Step 2: Search agreement {base_fa_no} and open it"):
        framework_list.search_agreement_with_enter(base_fa_no)
        agreement_row, agreement_fa_no = framework_list.find_exact_agreement_row(base_fa_no)
        agreement_tab = new_tab(lambda p: agreement_row.locator("a[onclick^='showDetails']").click())
        agreement_tab.wait_for_timeout(5000)
        framework_info = FrameworkInformation(agreement_tab)
        framework_info.get_full_page_screenshot('requisition_amended_agreement')

    # Step 3: First two items (the amended items)
    with allure.step(f"Step 3: Store the first two items of {agreement_fa_no}"):
        agreement_vendor = framework_info.get_framework_information_values()["Vendor"]
        item_rows = framework_info.get_item_rows()
        agreement_items = [framework_info.get_item_values(item_rows.nth(index)) for index in range(ITEMS_TO_USE)]
        for index, item in enumerate(agreement_items, start=1):
            print(f"Amended item {index}: {item}")
            allure.attach("\n".join(f"{label}: {'' if value is None else value}" for label, value in item.items()),
                          name=f"Amended item {index}", attachment_type=allure.attachment_type.TEXT)
        agreement_tab.close()
        page.bring_to_front()

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_admin_logout')


def add_agreement_item_to_requisition(create_requisition_page, index):
    # Item Information > Active Framework Agreement > amended item > quantity, GL code, attachment, remarks > grid
    requisition_data = REQUISITION_ITEMS[index - 1]
    agreement_item = agreement_items[index - 1]
    item_code = item_code_of(agreement_item["Item Name"])
    base_fa_no = agreement_number.strip().split("/V")[0]
    attachment_path = UTILS_DIR / requisition_data["attachment"]
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"

    with allure.step(f"Search and select Item Information {requisition_data['master_item_full_path']}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=requisition_data["master_item"],
            item_info_2=requisition_data["master_item_full_path"]
        )

    with allure.step(f"Select amended item {item_code} of {base_fa_no}"):
        applicable_for = create_requisition_page.search_active_framework(agreement_number=base_fa_no)
        selected_item = create_requisition_page.select_active_framework_item_by_code(
            agreement_number=base_fa_no, item_code=item_code)
        # Same amended agreement version as Test case 1, e.g. BPD/2026/FA-5/V9
        assert selected_item["fa_no"] == agreement_fa_no, \
            f"Item {item_code} is from {selected_item['fa_no']}, not the amended version {agreement_fa_no}"
        create_requisition_page.get_full_page_screenshot(f'framework_requisition_item_{index}_selected')

    with allure.step(f"Enter quantity {requisition_data['quantity']}, GL code {requisition_data['gl_code']}, "
                     f"attachment {attachment_path.name} and remarks"):
        create_requisition_page.finalize_item_quantity(item_quantity=requisition_data["quantity"])
        create_requisition_page.reset_cost_allocation_by_quantity()
        create_requisition_page.setting_item_gl_code(gl_code=requisition_data["gl_code"])
        assert create_requisition_page.upload_requisition_item_document(str(attachment_path)), \
            f"Attachment upload failed: {attachment_path.name}"
        create_requisition_page.setting_item_remarks(item_remarks=requisition_item_remarks)

    with allure.step(f"Add to grid and verify the amended Unit Price {agreement_item['Unit Price']}"):
        create_requisition_page.add_item_requisition_details_information_list()
        grid_item = create_requisition_page.verify_grid_item(
            quantity=Decimal(requisition_data["quantity"]),
            unit_price=agreement_item["Unit Price"]
        )
        create_requisition_page.verify_grid_row_count(expected_count=index)
        create_requisition_page.get_full_page_screenshot(f'framework_requisition_item_{index}_grid')
        allure.attach(
            f"Agreement: {selected_item['fa_no']} (Applicable For: {applicable_for})\n"
            f"Item: {agreement_item['Item Name']}\nAmended Unit Price: {agreement_item['Unit Price']}\n"
            f"Requisition grid: {grid_item}",
            name=f"Requisition item {index}", attachment_type=allure.attachment_type.TEXT)
    return {"item": agreement_item["Item Name"], "unit_price": agreement_item["Unit Price"],
            "quantity": requisition_data["quantity"], "grid": grid_item}


@allure.suite("Requisition")
@allure.feature("Framework Agreement Requisition")
@allure.story("Create Requisition")
@allure.title("Test_case_2: Create requisition with amended Item 1")
@allure.description("Test case 2: The requisition initiator creates a requisition and adds amended Item 1 of the "
                    "framework agreement with its amended Unit Price.")
@pytest.mark.order(2)
def test_2_create_requisition_with_amended_item_1(page):
    """
    Test case 2: Create the requisition with amended Item 1.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and open Create Requisition.
        2. Head Office, project, source of fund and remarks.
        3. Item 1: master item 1, the amended Item 1 of the agreement, quantity, GL code, attachment, remarks.
        4. Add to grid and verify the grid Unit Price = amended Unit Price.
        No logout: Test case 3 adds Item 2 to the same requisition.
    """
    global requisition_items
    assert len(agreement_items) == ITEMS_TO_USE, "Test case 1 must pass first: no amended agreement items"
    required_env_values = {
        "test_user_name": proj_user,
        "test_requisition_project_name": requisition_project_name,
        "test_requisition_funding_source": requisition_funding_source,
        "test_requisition_funding_remarks": requisition_funding_remarks,
        "test_requisition_item_remarks": requisition_item_remarks,
        "test_requisition_item_1_quantity": REQUISITION_ITEMS[0]["quantity"],
        "test_requisition_item_2_quantity": REQUISITION_ITEMS[1]["quantity"],
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Log in and open Create Requisition
    with allure.step(f"Step 1: Log in to ERP as {proj_user} and open Create Requisition"):
        erp_login(page, proj_user)
        DashboardPage(page).goto_procurement()
        ProcurementHomePage(page).navigate_to_create_requisition()
        create_requisition_page.validate()

    # Step 2: Requisition information
    with allure.step("Step 2: Select Head Office, Project, Source of Fund and enter Remarks"):
        create_requisition_page.setting_requisition_for(project_name=requisition_project_name)
        create_requisition_page.setting_requisition_information(
            fund_source=requisition_funding_source,
            fund_remarks=requisition_funding_remarks
        )
        create_requisition_page.get_full_page_screenshot('framework_requisition_information')

    # Step 3-4: Item 1
    with allure.step(f"Step 3: Add amended Item 1 {agreement_items[0]['Item Name']}"):
        requisition_items = [add_agreement_item_to_requisition(create_requisition_page, 1)]


@allure.suite("Requisition")
@allure.feature("Framework Agreement Requisition")
@allure.story("Create Requisition")
@allure.title("Test_case_3: Add amended Item 2 to the requisition")
@allure.description("Test case 3: Add amended Item 2 of the framework agreement to the same requisition with its "
                    "amended Unit Price.")
@pytest.mark.order(3)
def test_3_add_amended_item_2(page):
    """
    Test case 3: Add amended Item 2 (continues in the requisition of Test case 2).

    Steps:
        1. Item 2: master item 2, the amended Item 2 of the agreement, quantity, GL code, attachment, remarks.
        2. Add to grid, verify the grid Unit Price = amended Unit Price and 2 items in the grid.
    """
    assert len(requisition_items) == 1, "Test case 2 must pass first: Item 1 is not added"

    # Step 1-2: Item 2
    with allure.step(f"Step 1: Add amended Item 2 {agreement_items[1]['Item Name']}"):
        requisition_items.append(add_agreement_item_to_requisition(CreateRequisition(page), 2))


@allure.suite("Requisition")
@allure.feature("Framework Agreement Requisition")
@allure.story("Submit Requisition")
@allure.title("Test_case_4: Submit the requisition with the amended items")
@allure.description("Test case 4: Set the delivery schedule and Head Office location, submit the requisition and "
                    "store the requisition number.")
@pytest.mark.order(4)
def test_4_submit_requisition(page):
    """
    Test case 4: Submit the requisition (continues in the requisition of Test cases 2-3).

    Steps:
        1. Same schedule (today) and Head Office delivery location ('schedule_address').
        2. Submit and store the requisition number.
        No logout: Test case 5 continues in the initiator session.
    """
    global req_num, req_submission_message
    assert len(requisition_items) == ITEMS_TO_USE, "Test case 3 must pass first: Item 2 is not added"
    assert schedule_address, "Missing in .env: test_schedule_address"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Schedule and delivery location
    with allure.step(f"Step 1: Set same schedule (today) and delivery location Head Office - {schedule_address}"):
        create_requisition_page.setting_same_schedule_for_date()
        create_requisition_page.setting_location_for_head_office(address=schedule_address)
        create_requisition_page.get_full_page_screenshot('framework_requisition_schedule')

    # Step 2: Submit
    with allure.step("Step 2: Submit the requisition"):
        req_submission_message, req_num = create_requisition_page.submit_requisition_with_message()
        assert req_num, "Requisition number not displayed after Submit"
        print("REQ NUM:", req_num)
        create_requisition_page.get_full_page_screenshot('framework_requisition_submitted')
        allure.attach(
            f"Requisition number: {req_num}\nMessage: {req_submission_message}\nAgreement: {agreement_fa_no}\n"
            + "\n".join(f"Item: {item['item']} | Quantity: {item['quantity']} | Amended Unit Price: "
                        f"{item['unit_price']}" for item in requisition_items),
            name="Submitted requisition", attachment_type=allure.attachment_type.TEXT)


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Requisition Approver")
@allure.title("Test_case_5: Identify first approver")
@allure.description("Test case 5: Identify and capture the first approver of the submitted requisition.")
@pytest.mark.order(5)
def test_5_identify_first_approver(page):
    """
    Test case 5: Identify the first approver (continues in the initiator session of Test case 4).

    Steps:
        1. Go to Requisition > Requisition List.
        2. Search the submitted requisition ('req_num').
        3. Get the first layer approver ID ('approver_id') and status.
        4. Exit and log out from ERP.
    """
    global approver_id
    assert req_num, "Test case 4 must pass first: no requisition number available"

    create_requisition_page = CreateRequisition(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Requisition > Requisition List
    with allure.step("Step 1: Go to Requisition > Requisition List"):
        create_requisition_page.navigate_to_requisition_list()
        requisition_list_page.get_full_page_screenshot('framework_requisition_list')

    # Step 2: Search the submitted requisition
    with allure.step(f"Step 2: Search requisition {req_num}"):
        requisition_list_page.search_requisition(req_num)
        requisition_list_page.get_full_page_screenshot('framework_requisition_list_search')

    # Step 3: First layer approver ID and status
    with allure.step(f"Step 3: Get first layer approver ID and status of {req_num}"):
        approver_id = str(int(requisition_list_page.find_approver_id()))
        req_status = requisition_list_page.find_requisition_status()
        print("APPROVER ID:", approver_id)
        allure.attach(f"Requisition number: {req_num}\nFirst approver ID: {approver_id}\nStatus: {req_status}",
                      name="First approver ID and status", attachment_type=allure.attachment_type.TEXT)
        requisition_list_page.get_full_page_screenshot('framework_requisition_first_approver_id')

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'framework_requisition_initiator_logout')


@allure.suite("Requisition")
@allure.feature("Requisition Approve List")
@allure.story("First Layer Approval")
@allure.title("Test_case_6: Approve requisition as first approver")
@allure.description("Test case 6: Log in as the first approver and approve the submitted requisition.")
@pytest.mark.order(6)
def test_6_approve_requisition_as_first_approver(page):
    """
    Test case 6: The first approver approves the requisition.

    Steps:
        1. Log in to ERP as the first approver ('approver_id') and go to Procurement.
        2. Requisition Approve List: search the requisition ('req_num').
        3. Select the requisition and approve it.
        4. Exit and log out.
    """
    assert req_num and approver_id, "Test case 5 must pass first: no requisition number/approver ID available"

    proc_dashboard_page = DashboardPage(page)
    requisition_approve_list_page = RequisitionApproveList(page)

    # Step 1: Log in as the first approver
    with allure.step(f"Step 1: Log in to ERP as first approver {approver_id}"):
        erp_login(page, approver_id)
        proc_dashboard_page.menu_click_procurement_hyperlink()
        proc_dashboard_page.get_full_page_screenshot('framework_requisition_first_approver_login')

    # Step 2: Requisition Approve List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition Approve List"):
        ProcurementHomePage(page).navigate_to_requisition_approve_list()
        requisition_approve_list_page.search_requisition(req_num)
        requisition_approve_list_page.get_full_page_screenshot('framework_requisition_first_approver_search')

    # Step 3: Approve
    with allure.step(f"Step 3: Approve requisition {req_num} as first approver"):
        requisition_approve_list_page.select_requisition()
        requisition_approve_list_page.approve_requisition()
        allure.attach(f"Requisition number: {req_num}\nApproved by first approver: {approver_id}",
                      name="First layer approval", attachment_type=allure.attachment_type.TEXT)
        requisition_approve_list_page.get_full_page_screenshot('framework_requisition_first_approver_approved')
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'framework_requisition_first_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Second Layer Approval")
@allure.title("Test_case_7: Identify second approver")
@allure.description("Test case 7: Identify and capture the second (final) approver of the requisition.")
@pytest.mark.order(7)
def test_7_identify_second_approver(page):
    """
    Test case 7: Identify the second (final) approver.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Requisition List: search the requisition ('req_num').
        3. Get the second (final) layer approver ID ('approver_id_2') and status.
        4. Exit and log out.
    """
    global approver_id_2
    assert req_num, "Test case 4 must pass first: no requisition number available"

    requisition_list_page = RequisitionList(page)

    # Step 1: Log in as the requisition initiator
    with allure.step(f"Step 1: Log in to ERP as requisition initiator {proj_user}"):
        erp_login(page, proj_user)
        DashboardPage(page).goto_procurement()

    # Step 2: Requisition List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition List"):
        ProcurementHomePage(page).navigate_to_requisition_list()
        requisition_list_page.search_requisition(req_num)
        requisition_list_page.get_full_page_screenshot('framework_requisition_second_approver_search')

    # Step 3: Second (final) layer approver ID
    with allure.step("Step 3: Get the second (final) layer approver ID"):
        approver_id_2 = str(int(requisition_list_page.find_approver_id()))
        second_layer_status = requisition_list_page.find_requisition_status()
        print("APPROVER ID 2:", approver_id_2)
        allure.attach(f"Requisition number: {req_num}\nSecond approver ID: {approver_id_2}\n"
                      f"Status: {second_layer_status}",
                      name="Second approver ID and status", attachment_type=allure.attachment_type.TEXT)
        requisition_list_page.get_full_page_screenshot('framework_requisition_second_approver_id')

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'framework_requisition_second_approver_identify_logout')


@allure.suite("Requisition")
@allure.feature("Requisition Approve List")
@allure.story("Second Layer Approval")
@allure.title("Test_case_8: Approve requisition as final approver")
@allure.description("Test case 8: Log in as the second (final) approver and approve the requisition.")
@pytest.mark.order(8)
def test_8_approve_requisition_as_final_approver(page):
    """
    Test case 8: The final approver approves the requisition.

    Steps:
        1. Log in to ERP as the final approver ('approver_id_2') and go to Procurement.
        2. Requisition Approve List: search the requisition ('req_num').
        3. Select the requisition and approve it.
        4. Exit and log out.
    """
    assert req_num and approver_id_2, "Test case 7 must pass first: no requisition number/second approver available"

    proc_dashboard_page = DashboardPage(page)
    requisition_approve_list_page = RequisitionApproveList(page)

    # Step 1: Log in as the final approver
    with allure.step(f"Step 1: Log in to ERP as final approver {approver_id_2}"):
        erp_login(page, approver_id_2)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('framework_requisition_final_approver_login')

    # Step 2: Requisition Approve List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition Approve List"):
        ProcurementHomePage(page).navigate_to_requisition_approve_list()
        requisition_approve_list_page.search_requisition(req_num)
        requisition_approve_list_page.get_full_page_screenshot('framework_requisition_final_approver_search')

    # Step 3: Approve
    with allure.step(f"Step 3: Approve requisition {req_num} as final approver"):
        requisition_approve_list_page.select_requisition()
        requisition_approve_list_page.approve_requisition()
        allure.attach(f"Requisition number: {req_num}\nApproved by final approver: {approver_id_2}",
                      name="Final layer approval", attachment_type=allure.attachment_type.TEXT)
        requisition_approve_list_page.get_full_page_screenshot('framework_requisition_final_approver_approved')
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'framework_requisition_final_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Requisition Status")
@allure.title("Test_case_9: Requisition initiator gets approval status")
@allure.description("Test case 9: Log in as the requisition initiator, get the approval status and verify the "
                    "requisition details (FA No, items, quantities, amended unit prices) and the agreement vendor.")
@pytest.mark.order(9)
def test_9_requisition_initiator_gets_approval_status(page, new_tab):
    """
    Test case 9: The requisition initiator gets the approval status.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Requisition List: search the requisition ('req_num') and get its approval status.
        3. Open the requisition details in a new tab and verify both amended items
           (FA No, item, quantity, amended unit price).
        4. Open the FA No link in a new tab and verify the agreement version and vendor are the amended
           agreement version and vendor (Test case 1).
        5. Close the tabs, exit and log out.
    """
    global approved_req_status
    assert req_num, "Test case 4 must pass first: no requisition number available"

    base_fa_no = agreement_number.strip().split("/V")[0]
    requisition_list_page = RequisitionList(page)

    # Step 1: Log in as the requisition initiator
    with allure.step(f"Step 1: Log in to ERP as requisition initiator {proj_user}"):
        erp_login(page, proj_user)
        DashboardPage(page).goto_procurement()

    # Step 2: Approval status
    with allure.step(f"Step 2: Get approval status of requisition {req_num}"):
        ProcurementHomePage(page).navigate_to_requisition_list()
        requisition_list_page.search_requisition(req_num)
        approved_req_status = requisition_list_page.find_requisition_status()
        print("REQ STATUS:", approved_req_status)
        allure.attach(f"Requisition number: {req_num}\nStatus: {approved_req_status}",
                      name="Requisition approval status", attachment_type=allure.attachment_type.TEXT)
        requisition_list_page.get_full_page_screenshot('framework_requisition_approval_status')

    # Step 3: Requisition details: both amended items
    with allure.step(f"Step 3: Verify requisition details of {req_num} (2 amended items)"):
        details_tab = new_tab(lambda p: requisition_list_page.goto_requisition_details_information())
        requisition_details_page = RequisitionDetailsInformation(details_tab)
        requisition_details_page.verify_requisition_item_count(fa_no=base_fa_no, expected_count=ITEMS_TO_USE)
        verified_items = []
        for index in range(ITEMS_TO_USE):
            # Master item code, e.g. "[22245]" from "[22245]-Pen Box-(...)"
            master_item_code = re.search(r"\[[^\]]+\]", REQUISITION_ITEMS[index]["master_item_full_path"]).group(0)
            verified_items.append(requisition_details_page.verify_requisition_item(
                requisition_number=req_num,
                fa_no=base_fa_no,
                item_code=master_item_code,
                quantity=Decimal(REQUISITION_ITEMS[index]["quantity"]),
                unit_price=agreement_items[index]["Unit Price"]
            ))
        allure.attach(f"Requisition number: {req_num}\nStatus: {approved_req_status}\nFA. No: {base_fa_no}\n"
                      + "\n".join(f"Item {index + 1}: {details}" for index, details in enumerate(verified_items)),
                      name="Verified requisition details", attachment_type=allure.attachment_type.TEXT)
        requisition_details_page.get_full_page_screenshot('framework_requisition_details_verified')

    # Step 4: Vendor of the FA No link = agreement vendor
    with allure.step(f"Step 4: Verify agreement version {agreement_fa_no} and vendor {agreement_vendor}"):
        framework_tab = new_tab(lambda p: requisition_details_page.open_framework_details())
        requisition_vendor_name = FrameworkInformation(framework_tab).get_vendor_info()
        requisition_fa_no = FrameworkInformation(framework_tab).get_field_value("FA No.")
        assert requisition_fa_no == agreement_fa_no, \
            f"Requisition agreement version {requisition_fa_no} is not the amended version {agreement_fa_no}"
        assert agreement_vendor.lower() in requisition_vendor_name.lower(), \
            f"Requisition vendor '{requisition_vendor_name}' is not the agreement vendor '{agreement_vendor}'"
        allure.attach(f"Amended agreement version (Test case 1): {agreement_fa_no}\n"
                      f"Requisition agreement version (FA No link): {requisition_fa_no}\n"
                      f"Agreement vendor (Test case 1): {agreement_vendor}\n"
                      f"Requisition vendor (FA No link): {requisition_vendor_name}",
                      name="Verified vendor", attachment_type=allure.attachment_type.TEXT)
        FrameworkInformation(framework_tab).get_full_page_screenshot('framework_requisition_vendor_verified')

    # Step 5: Close the tabs, exit and log out
    with allure.step("Step 5: Close requisition details tabs, exit and log out from ERP"):
        framework_tab.close()
        details_tab.close()
        page.bring_to_front()
        erp_logout(page, 'framework_requisition_initiator_final_logout')
