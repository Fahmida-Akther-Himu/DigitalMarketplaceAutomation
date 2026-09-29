from dotenv import load_dotenv
import os
import re
import random
from decimal import Decimal, InvalidOperation
from pathlib import Path
import pytest
import allure

load_dotenv()

from playwright.sync_api import expect

from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.public_side_framework_agreement_list import \
    PublicSideFrameAgreementListPage
from pages.digital_marketplace.public_side.wishlist_page import WishlistPage
from pages.digital_marketplace.public_side.shopping_cart import ShoppingCart
from pages.digital_marketplace.public_side.checkout_page import CheckoutPage
from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.my_dashboard.procurement.requisition.create_requisition import CreateRequisition
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_list import RequisitionList
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_approve_list import RequisitionApproveList
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_information import FrameworkInformation

# Procurement information
proj_env = os.getenv("test_env")
proj_user = os.getenv("test_user_name")

# Marketplace information
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
# Shopping cart quantity of the first item (Test case 10)
fractional_cart_qty = os.getenv("test_fractional_cart_qty")
# Delivery schedule (Test case 11)
delivery_schedule_quantity = os.getenv("test_delivery_schedule_quantity")
manual_delivery_location_1 = os.getenv("test_delivery_location_1")
manual_delivery_location_2 = os.getenv("test_delivery_location_2")
receiving_pin_1 = os.getenv("test_receiving_pin")
order_initiator = os.getenv("test_order_initiator")

# Scenario data
active_framework_agreement = os.getenv("test_active_framework_agreement")
# Number of products to store from the Framework Product List (Step 7)
wishlist_product_count = os.getenv("test_wishlist_product_count")
# System quantity limits (maximum 18 digits with 2 decimals, e.g. 999999999999999999.99)
wishlist_min_quantity = os.getenv("test_wishlist_min_quantity")
wishlist_max_quantity = os.getenv("test_wishlist_max_quantity")
# Range of the random 2-digit fractional quantity entered in Step 8 (within the system limits)
wishlist_entry_min_quantity = os.getenv("test_wishlist_entry_min_quantity")
wishlist_entry_max_quantity = os.getenv("test_wishlist_entry_max_quantity")
# Quantity added to an existing Wishlist item in Step 11, must be more than the minimum increase
wishlist_increase_quantity = os.getenv("test_wishlist_increase_quantity")
wishlist_min_increase_quantity = os.getenv("test_wishlist_min_increase_quantity")

# Requisition information
requisition_project_name = os.getenv("test_requisition_project_name")
requisition_funding_source = os.getenv("test_requisition_funding_source")
master_item_1 = os.getenv("test_master_item_1")
master_item_1_full_path = os.getenv("test_master_item_1_full_path")
item_gl_code_1 = os.getenv("test_item_gl_code_1")
# Attachment file name in the utils folder (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX)
requisition_attachment_file = os.getenv("test_requisition_attachment_file")
# Second item (Active Framework Agreement item)
master_item_2 = os.getenv("test_master_item_2")
master_item_2_full_path = os.getenv("test_master_item_2_full_path")
item_gl_code_2 = os.getenv("test_item_gl_code_2")
requisition_item_2_quantity = os.getenv("test_requisition_item_2_quantity")
requisition_attachment_file_2 = os.getenv("test_requisition_attachment_file_2")
# Head Office delivery location
schedule_address = os.getenv("test_schedule_address")

# Remarks global variable
requisition_funding_remarks = os.getenv("test_requisition_funding_remarks")
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
order_remarks = os.getenv("test_order_remarks")

# Attachment and remarks rules
UTILS_DIR = Path(__file__).resolve().parents[1] / "utils"
ALLOWED_ATTACHMENT_TYPES = {".docx", ".pdf", ".xls", ".jpg", ".png", ".ppt", ".zip", ".pptx"}
MAX_ATTACHMENT_SIZE_MB = 20
MAX_REQUISITION_REMARKS_LENGTH = 300
MAX_ITEM_REMARKS_LENGTH = 500

# Marketplace global variable
initial_wishlist_count = 0
agreement_vendor_name = ''
# Order vendor from the requisition FA No link (same as sanity.py), used in the shopping cart
order_vendor = ''
# Marketplace order (Test case 12)
order_reference_number = ''
order_status = ''
framework_products = []
selected_product = {}
wishlist_quantity = ''
wishlist_message = {}
product_already_in_wishlist = False
updated_wishlist_count = 0
existing_wishlist_quantity = ''
updated_wishlist_quantity = ''
final_wishlist_quantity = ''

# Procurement global variable
selected_wishlist_item = {}
second_item = {}
second_item_applicable_for = ''
req_num = ''
req_submission_message = ''
approver_id = ''
req_status = ''
approver_id_2 = ''
approved_req_status = ''
verified_requisition_details = {}


def env_decimal(env_name, value):
    # .env value as an exact 2-digit fractional number, with a clear error if it is not a number
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        raise AssertionError(f"{env_name} in .env is not a valid number: {value!r}")


def random_fractional_quantity(min_quantity, max_quantity):
    # Random 2-digit fractional quantity (e.g. 500.99); Decimal keeps 18-digit values exact
    min_cents = int(Decimal(min_quantity) * 100)
    max_cents = int(Decimal(max_quantity) * 100)
    return f"{Decimal(random.randint(min_cents, max_cents)) / 100:.2f}"


@allure.suite("Public Side")
@allure.feature("Wishlist")
@allure.story("Framework Agreement Item Wishlist")
@allure.title("Test_case_1: Add framework agreement product to wishlist")
@allure.description("Test case 1: Add a Framework Agreement product to the Digital Marketplace Wishlist and store its "
                    "FWA code, vendor and final Wishlist quantity for the ERP requisition.")
@pytest.mark.order(1)
def test_1_add_framework_agreement_product_to_wishlist(page):
    """
    Test Case 1: Add Framework Agreement Product to Marketplace Wishlist.

    Steps (same as test_add_framework_agreement_product_to_wishlist.py):
        1. Log in to the Digital Marketplace as 'proj_user' using SSO,
           retrieve the initial Wishlist count, and store it in 'initial_wishlist_count'.
        2. Navigate to All Framework Agreements.
        3. Search for the specified Active Framework Agreement.
        4. Identify the correct Framework Agreement using an exact match
           (e.g. BPD/2026/FA-5, not BPD/2026/FA-50).
        5. Retrieve the Vendor Name of the exact Framework Agreement and store it in 'agreement_vendor_name'.
        6. Click the View hyperlink of the exact Framework Agreement to open the Framework Product List.
        7. Store Product Name, Specification, Price and FWA Product Code of the first
           'test_wishlist_product_count' products (or fewer if not available),
           then open the first product's details page.
        8. Enter a random 2-digit fractional quantity between 'test_wishlist_entry_min_quantity' and
           'test_wishlist_entry_max_quantity' (e.g. 100.99), click Add to Wishlist, confirm and print the message.
           If the product already exists in the Wishlist, print the alert message instead.
        9. Retrieve the updated Wishlist count and store it in 'updated_wishlist_count'.
        10. Navigate to the Wishlist page and verify the product information and quantity.
        11. If the product already existed: on the Wishlist page, get the item's current quantity,
            increase it by 'test_wishlist_increase_quantity' (2-digit fractional,
            more than 'test_wishlist_min_increase_quantity'), click Update wishlist and
            verify the item is still in the Wishlist with the new quantity.
        12. Store the final Wishlist quantity in 'final_wishlist_quantity' and log out from the Digital Marketplace.

    All scenario values are read from .env.
    """
    global initial_wishlist_count, agreement_vendor_name, framework_products, selected_product, \
        wishlist_quantity, wishlist_message, product_already_in_wishlist, updated_wishlist_count, \
        existing_wishlist_quantity, updated_wishlist_quantity, final_wishlist_quantity

    # All scenario values must come from .env
    required_env_values = {
        "test_user_name": proj_user,
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_active_framework_agreement": active_framework_agreement,
        "test_wishlist_product_count": wishlist_product_count,
        "test_wishlist_min_quantity": wishlist_min_quantity,
        "test_wishlist_max_quantity": wishlist_max_quantity,
        "test_wishlist_entry_min_quantity": wishlist_entry_min_quantity,
        "test_wishlist_entry_max_quantity": wishlist_entry_max_quantity,
        "test_wishlist_increase_quantity": wishlist_increase_quantity,
        "test_wishlist_min_increase_quantity": wishlist_min_increase_quantity,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    # Check all numeric .env values before logging in
    env_decimal("test_wishlist_increase_quantity", wishlist_increase_quantity)
    env_decimal("test_wishlist_min_increase_quantity", wishlist_min_increase_quantity)
    assert env_decimal("test_wishlist_min_quantity", wishlist_min_quantity) > 0, \
        f"test_wishlist_min_quantity must be > 0, found {wishlist_min_quantity}"
    assert env_decimal("test_wishlist_max_quantity", wishlist_max_quantity) >= Decimal(wishlist_min_quantity), \
        f"test_wishlist_max_quantity ({wishlist_max_quantity}) must be >= " \
        f"test_wishlist_min_quantity ({wishlist_min_quantity})"
    # Step 8 entry range must be inside the system limits
    assert env_decimal("test_wishlist_entry_min_quantity", wishlist_entry_min_quantity) >= \
        Decimal(wishlist_min_quantity), \
        f"test_wishlist_entry_min_quantity ({wishlist_entry_min_quantity}) must be >= " \
        f"test_wishlist_min_quantity ({wishlist_min_quantity})"
    assert env_decimal("test_wishlist_entry_max_quantity", wishlist_entry_max_quantity) <= \
        Decimal(wishlist_max_quantity), \
        f"test_wishlist_entry_max_quantity ({wishlist_entry_max_quantity}) must be <= " \
        f"test_wishlist_max_quantity ({wishlist_max_quantity})"
    assert Decimal(wishlist_entry_max_quantity) >= Decimal(wishlist_entry_min_quantity), \
        f"test_wishlist_entry_max_quantity ({wishlist_entry_max_quantity}) must be >= " \
        f"test_wishlist_entry_min_quantity ({wishlist_entry_min_quantity})"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    agreement_list_page = PublicSideFrameAgreementListPage(page)
    wishlist_page = WishlistPage(page)

    # Step 1: Log in and store the initial Wishlist count
    with allure.step(f"Step 1: Log in to the Digital Marketplace as {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(
            user_name=proj_user,
            pass_word=marketplace_password
        )
        home_page.verify_welcome_message()

    with allure.step("Step 1: Retrieve and store the initial Wishlist count"):
        initial_wishlist_count = home_page.get_wishlist_count()
        home_page.get_full_page_screenshot('wishlist_initial_count')
        allure.attach(
            str(initial_wishlist_count),
            name="Initial Wishlist count",
            attachment_type=allure.attachment_type.TEXT
        )

    assert initial_wishlist_count >= 0, f"Invalid Wishlist count: {initial_wishlist_count}"

    # Step 2: Navigate to All Framework Agreements
    with allure.step("Step 2: Navigate to All Framework Agreements"):
        home_page.go_to_all_framework_agreements_list()
        expect(page).to_have_url(re.compile(r"/FrameworkAgreementList", re.IGNORECASE))
        expect(agreement_list_page.search_agreement_locator).to_be_visible()
        agreement_list_page.get_full_page_screenshot('wishlist_all_framework_agreements')

    # Step 3: Search for the specified Active Framework Agreement
    with allure.step(f"Step 3: Search for the Active Framework Agreement {active_framework_agreement}"):
        agreement_list_page.search_agreement(agreement_number=active_framework_agreement)
        expect(agreement_list_page.get_search_result_rows(active_framework_agreement).first).to_be_visible()
        expect(agreement_list_page.agreement_view_hyperlink.first).to_be_visible()
        agreement_list_page.get_full_page_screenshot('wishlist_search_active_framework_agreement')

    # Step 4: Identify the correct Framework Agreement using an exact match
    with allure.step(f"Step 4: Identify the exact Framework Agreement {active_framework_agreement}"):
        exact_agreement_row = agreement_list_page.get_exact_agreement_row(active_framework_agreement)
        expect(exact_agreement_row).to_have_count(1)
        agreement_list_page.highlight_element(exact_agreement_row)
        agreement_list_page.get_full_page_screenshot('wishlist_exact_framework_agreement')

    # Step 5: Retrieve the Vendor Name of the exact Framework Agreement
    with allure.step(f"Step 5: Retrieve the Vendor Name of {active_framework_agreement}"):
        agreement_vendor_name = agreement_list_page.get_agreement_vendor_name(active_framework_agreement)
        assert agreement_vendor_name, f"Vendor Name not found for {active_framework_agreement}"
        allure.attach(
            agreement_vendor_name,
            name="Framework Agreement Vendor Name",
            attachment_type=allure.attachment_type.TEXT
        )
        agreement_list_page.get_full_page_screenshot('wishlist_framework_agreement_vendor_name')

    # Step 6: Click View for the exact Framework Agreement
    with allure.step(f"Step 6: Click View for {active_framework_agreement} to open the Framework Product List"):
        agreement_list_page.view_agreement_products(active_framework_agreement)
        expect(page).to_have_url(re.compile(r"/FrameworkProductList/", re.IGNORECASE))
        agreement_list_page.get_full_page_screenshot('wishlist_framework_product_list')

    # Step 7: Store the first products and open the first product's details
    with allure.step("Step 7: Store product information and open the first product's details page"):
        framework_products = agreement_list_page.get_framework_products(max_products=int(wishlist_product_count))
        assert framework_products, f"No products found for {active_framework_agreement}"
        selected_product = framework_products[0]
        allure.attach(
            "\n".join(
                f"{p['product_name']} | {p['specification']} | {p['price']} | {p['fwa_product_code']}"
                for p in framework_products
            ),
            name="Framework products (Product Name | Specification | Price | FWA Product Code)",
            attachment_type=allure.attachment_type.TEXT
        )
        agreement_list_page.open_product_details(selected_product["product_name"])
        agreement_list_page.get_full_page_screenshot('wishlist_product_details')

    # Step 8: Enter quantity, Add to wishlist, confirm and print the message
    wishlist_quantity = random_fractional_quantity(wishlist_entry_min_quantity, wishlist_entry_max_quantity)
    with allure.step(f"Step 8: Add '{selected_product['product_name']}' to Wishlist with quantity {wishlist_quantity}"):
        wishlist_message = agreement_list_page.add_product_to_wishlist_with_quantity(
            quantity=wishlist_quantity,
            screenshot_name='wishlist_add_to_wishlist_message'
        )
        product_already_in_wishlist = (
                wishlist_message["type"] != "success" or "already" in wishlist_message["message"].lower()
        )
        allure.attach(
            f"{wishlist_message['type']}: {wishlist_message['message']}",
            name="Already exists alert" if product_already_in_wishlist else "Add to wishlist confirmation",
            attachment_type=allure.attachment_type.TEXT
        )
        assert wishlist_message["message"], "No message displayed after Add to wishlist"

    # Step 9: Retrieve and store the updated Wishlist count
    with allure.step("Step 9: Retrieve and store the updated Wishlist count"):
        updated_wishlist_count = home_page.get_wishlist_count()
        allure.attach(
            f"Initial: {initial_wishlist_count}\nUpdated: {updated_wishlist_count}",
            name="Wishlist count",
            attachment_type=allure.attachment_type.TEXT
        )
        if not product_already_in_wishlist:
            assert updated_wishlist_count > initial_wishlist_count, \
                f"Wishlist count not updated: initial {initial_wishlist_count}, updated {updated_wishlist_count}"
        home_page.get_full_page_screenshot('wishlist_updated_count')

    # Step 10: Verify the product on the Wishlist page
    with allure.step("Step 10: Navigate to the Wishlist page and verify product information and quantity"):
        home_page.goto_wishlist()
        wishlist_page.verify_wishlist_page_opened()
        # Exactly one row for the product: added, and no duplicate if it already existed
        wishlist_page.verify_product_in_wishlist(
            product_name=selected_product["product_name"],
            expected_price=selected_product["price"],
            expected_quantity=None if product_already_in_wishlist else wishlist_quantity
        )
        wishlist_page.get_full_page_screenshot('wishlist_page_product_verified')

    # Step 11: If the product already existed, increase its quantity on the Wishlist page
    if product_already_in_wishlist:
        with allure.step(f"Step 11: Increase Wishlist quantity of '{selected_product['product_name']}' "
                         f"by {wishlist_increase_quantity}"):
            increase_quantity = env_decimal("test_wishlist_increase_quantity", wishlist_increase_quantity)
            assert increase_quantity > Decimal(wishlist_min_increase_quantity), \
                f"test_wishlist_increase_quantity must be more than {wishlist_min_increase_quantity}, " \
                f"found {wishlist_increase_quantity}"

            current_quantity = wishlist_page.get_product_quantity(selected_product["product_name"])
            existing_wishlist_quantity = f"{current_quantity:.2f}"
            updated_wishlist_quantity = f"{current_quantity + increase_quantity:.2f}"
            assert Decimal(updated_wishlist_quantity) >= Decimal(wishlist_min_quantity), \
                f"Updated quantity {updated_wishlist_quantity} is less than the minimum {wishlist_min_quantity}"
            assert Decimal(updated_wishlist_quantity) <= Decimal(wishlist_max_quantity), \
                f"Updated quantity {updated_wishlist_quantity} is more than the maximum {wishlist_max_quantity}"
            allure.attach(
                f"Current: {existing_wishlist_quantity}\nIncrease: {increase_quantity:.2f}\n"
                f"Updated: {updated_wishlist_quantity}",
                name="Wishlist quantity update",
                attachment_type=allure.attachment_type.TEXT
            )

            wishlist_page.update_product_quantity(
                product_name=selected_product["product_name"],
                quantity=updated_wishlist_quantity
            )
            wishlist_page.verify_product_in_wishlist(
                product_name=selected_product["product_name"],
                expected_price=selected_product["price"],
                expected_quantity=updated_wishlist_quantity
            )
            wishlist_page.get_full_page_screenshot('wishlist_page_quantity_updated')

    # Final Wishlist quantity of the product, used in the ERP requisition
    final_wishlist_quantity = updated_wishlist_quantity if product_already_in_wishlist else wishlist_quantity
    allure.attach(
        f"{selected_product['fwa_product_code']} - {selected_product['product_name']}: {final_wishlist_quantity}",
        name="Final Wishlist quantity",
        attachment_type=allure.attachment_type.TEXT
    )

    # Step 12: Log out from the Digital Marketplace
    with allure.step("Step 12: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        home_page.get_full_page_screenshot('wishlist_marketplace_logout')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Marketplace Wishlist Item")
@allure.title("Test_case_2: Create requisition with marketplace wishlist item")
@allure.description("Test case 2: Login to the ERP Procurement system, create & submit a requisition with the "
                    "Marketplace Wishlist item (same quantity as the Wishlist) and identify the first approver.")
@pytest.mark.order(2)
def test_2_create_requisition_with_wishlist_item(page):
    """
    Test Case 2: Create Requisition in ERP with the Marketplace Wishlist Item.

    Steps:
        1. Log in to ERP (ResetHub link, same as sanity.py) and open
           Procurement > Requisition > Create Requisition.
        2. Select Head Office, Project, Source of Fund and enter Remarks (max 300 characters).
        3. Search and select Item Information.
        4. Click Get wish list.
        5. Find the Wishlist item added in Test Case 1 (FA No + FWA code, next page if needed)
           and click that row. Verify that Quantity is the same as the Wishlist quantity.
        6. Click Amount radio button, then Quantity radio button; verify Quantity is unchanged.
        7. Select GL Code.
        8. Add attachment from utils (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX).
        9. Add item remarks (max 500 characters), click Add to grid and verify the item row
           (Quantity and Unit Price) in the Requisition Detail Information List.
        10. Set same schedule (today).
        11. Set delivery location: Head Office and 'test_schedule_address'.
        12. Submit the requisition, get the submission confirmation message and store the
            requisition number in 'req_num'.
        13. Go to Requisition > Requisition List.
        14. Search the created requisition 'req_num'.
        15. Get the approver ID ('approver_id') and status ('req_status') of the requisition.
        16. Exit and log out from ERP.

    All scenario values are read from .env.
    """
    global selected_wishlist_item, req_num, req_submission_message, approver_id, req_status

    # Wishlist item and quantity come from Test Case 1
    assert selected_product and final_wishlist_quantity, \
        "Test Case 1 must pass first: no Wishlist item/quantity available"

    # All scenario values must come from .env
    required_env_values = {
        "test_env": proj_env,
        "test_user_name": proj_user,
        "test_active_framework_agreement": active_framework_agreement,
        "test_requisition_project_name": requisition_project_name,
        "test_requisition_funding_source": requisition_funding_source,
        "test_requisition_funding_remarks": requisition_funding_remarks,
        "test_master_item_1": master_item_1,
        "test_master_item_1_full_path": master_item_1_full_path,
        "test_item_gl_code_1": item_gl_code_1,
        "test_requisition_attachment_file": requisition_attachment_file,
        "test_requisition_item_remarks": requisition_item_remarks,
        "test_schedule_address": schedule_address,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    # Remarks and attachment rules
    assert len(requisition_funding_remarks) <= MAX_REQUISITION_REMARKS_LENGTH, \
        f"test_requisition_funding_remarks must be max {MAX_REQUISITION_REMARKS_LENGTH} characters, " \
        f"found {len(requisition_funding_remarks)}"
    assert len(requisition_item_remarks) <= MAX_ITEM_REMARKS_LENGTH, \
        f"test_requisition_item_remarks must be max {MAX_ITEM_REMARKS_LENGTH} characters, " \
        f"found {len(requisition_item_remarks)}"
    attachment_path = UTILS_DIR / requisition_attachment_file
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"
    assert attachment_path.suffix.lower() in ALLOWED_ATTACHMENT_TYPES, \
        f"Attachment type {attachment_path.suffix} is not allowed: {sorted(ALLOWED_ATTACHMENT_TYPES)}"
    attachment_size_mb = attachment_path.stat().st_size / (1024 * 1024)
    assert attachment_size_mb <= MAX_ATTACHMENT_SIZE_MB, \
        f"Attachment must be max {MAX_ATTACHMENT_SIZE_MB} MB, found {attachment_size_mb:.2f} MB"

    reset_page = ResetHubPage(page)
    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    create_requisition_page = CreateRequisition(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Log in to ERP (same as sanity.py) and open Create Requisition
    with allure.step(f"Step 1: Log in to ERP as {proj_user} and open Create Requisition"):
        link = reset_page.generate_reset_link(
            env=proj_env,
            username=proj_user,
        )
        reset_page.open_generated_link(link)
        assert isinstance(link, str) and link.startswith("http")
        print(f"Logging in as requisition initiator: {proj_user}")

        proc_dashboard_page.goto_procurement()
        proc_home_page.navigate_to_create_requisition()
        create_requisition_page.validate()
        create_requisition_page.get_full_page_screenshot('requisition_create_requisition')

    # Step 2: Head Office, Project, Source of Fund and Remarks
    with allure.step("Step 2: Select Head Office, Project, Source of Fund and enter Remarks"):
        create_requisition_page.setting_requisition_for(project_name=requisition_project_name)
        create_requisition_page.setting_requisition_information(
            fund_source=requisition_funding_source,
            fund_remarks=requisition_funding_remarks
        )
        create_requisition_page.get_full_page_screenshot('requisition_requisition_information')

    # Step 3: Search and select Item Information
    with allure.step(f"Step 3: Search and select Item Information {master_item_1_full_path}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=master_item_1,
            item_info_2=master_item_1_full_path
        )
        create_requisition_page.get_full_page_screenshot('requisition_item_information')

    # Step 4: Click Get wish list
    with allure.step("Step 4: Click Get wish list"):
        create_requisition_page.open_wishlist()
        create_requisition_page.get_full_page_screenshot('requisition_wishlist_popup')

    # Step 5: Select the Wishlist item added in Test Case 1 and verify its quantity
    with allure.step(f"Step 5: Select wishlist item {selected_product['fwa_product_code']} "
                     f"of {active_framework_agreement}"):
        selected_wishlist_item = create_requisition_page.select_wishlist_item(
            agreement_number=active_framework_agreement,
            item_code=selected_product["fwa_product_code"]
        )
        requisition_quantity = create_requisition_page.verify_item_quantity(expected_quantity=final_wishlist_quantity)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in selected_wishlist_item.items())
            + f"\nquantity: {requisition_quantity}",
            name="Selected wishlist item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_wishlist_item_selected')

    # Step 6: Click Amount, then Quantity radio button
    with allure.step("Step 6: Click Amount radio button, then Quantity radio button"):
        create_requisition_page.reset_cost_allocation_by_quantity()
        create_requisition_page.verify_item_quantity(expected_quantity=final_wishlist_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_cost_allocation_quantity')

    # Step 7: Select GL Code
    with allure.step(f"Step 7: Select GL Code {item_gl_code_1}"):
        create_requisition_page.setting_item_gl_code(gl_code=item_gl_code_1)
        create_requisition_page.get_full_page_screenshot('requisition_gl_code')

    # Step 8: Add attachment from utils
    with allure.step(f"Step 8: Add attachment {attachment_path.name}"):
        assert create_requisition_page.upload_requisition_item_document(str(attachment_path)), \
            f"Attachment upload failed: {attachment_path.name}"
        allure.attach(
            f"{attachment_path.name} ({attachment_size_mb:.2f} MB)",
            name="Attachment",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_attachment')

    # Step 9: Add item remarks, click Add to grid and verify the item row
    with allure.step("Step 9: Add item remarks and click Add to grid"):
        create_requisition_page.setting_item_remarks(item_remarks=requisition_item_remarks)
        create_requisition_page.add_item_requisition_details_information_list()
        grid_item = create_requisition_page.verify_grid_item(
            quantity=final_wishlist_quantity,
            unit_price=selected_wishlist_item["unit_price"]
        )
        allure.attach(
            grid_item,
            name="Requisition Detail Information List item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_add_to_grid')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Active Framework Agreement Item")
@allure.title("Test_case_3: Add second item from active framework agreement")
@allure.description("Test case 3: Add a second item to the requisition with a different master item from the same "
                    "Active Framework Agreement (Applicable For: Both, then HO/HCMP), with quantity, GL code and "
                    "attachment from .env.")
@pytest.mark.order(3)
def test_3_add_second_item_from_active_framework_agreement(page):
    """
    Test Case 3: Add second item from the Active Framework Agreement.

    Steps:
        1. Search and select a different Item Information (master item 2).
        2. Click Check all active framework agreement and search the same Framework Agreement as
           Test Case 1 with Applicable For: Both. If not found, search again with HO, then HCMP.
        3. Select an item of the exact Framework Agreement that is not the Wishlist item.
        4. Enter the second item quantity from .env.
        5. Click Amount radio button, then Quantity radio button; verify Quantity is unchanged.
        6. Select a different GL Code from .env.
        7. Add attachment from utils (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX).
        8. Add item remarks (max 500 characters), click Add to grid and verify the requisition now has
           2 items (Wishlist item and second item).

    All scenario values are read from .env.
    """
    global second_item, second_item_applicable_for

    # Wishlist item comes from Test Case 1 and 2
    assert selected_product and selected_wishlist_item, \
        "Test Case 2 must pass first: Wishlist item is not added to the requisition"

    # All scenario values must come from .env
    required_env_values = {
        "test_active_framework_agreement": active_framework_agreement,
        "test_master_item_2": master_item_2,
        "test_master_item_2_full_path": master_item_2_full_path,
        "test_item_gl_code_2": item_gl_code_2,
        "test_requisition_item_2_quantity": requisition_item_2_quantity,
        "test_requisition_attachment_file_2": requisition_attachment_file_2,
        "test_requisition_item_remarks": requisition_item_remarks,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    # Second item must be different from the first item
    assert master_item_2_full_path != master_item_1_full_path, \
        "test_master_item_2_full_path must be different from test_master_item_1_full_path"
    assert item_gl_code_2 != item_gl_code_1, "test_item_gl_code_2 must be different from test_item_gl_code_1"

    # Second item quantity: 2-digit fractional number, more than 0
    second_item_quantity = env_decimal("test_requisition_item_2_quantity", requisition_item_2_quantity)
    assert second_item_quantity > 0, \
        f"test_requisition_item_2_quantity must be > 0, found {requisition_item_2_quantity}"
    assert Decimal(str(requisition_item_2_quantity)) == second_item_quantity, \
        f"test_requisition_item_2_quantity must have max 2 decimals, found {requisition_item_2_quantity}"

    # Attachment rules
    attachment_path_2 = UTILS_DIR / requisition_attachment_file_2
    assert attachment_path_2.is_file(), f"Attachment not found in utils: {attachment_path_2}"
    assert attachment_path_2.suffix.lower() in ALLOWED_ATTACHMENT_TYPES, \
        f"Attachment type {attachment_path_2.suffix} is not allowed: {sorted(ALLOWED_ATTACHMENT_TYPES)}"
    attachment_size_mb_2 = attachment_path_2.stat().st_size / (1024 * 1024)
    assert attachment_size_mb_2 <= MAX_ATTACHMENT_SIZE_MB, \
        f"Attachment must be max {MAX_ATTACHMENT_SIZE_MB} MB, found {attachment_size_mb_2:.2f} MB"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Search and select a different Item Information
    with allure.step(f"Step 1: Search and select Item Information {master_item_2_full_path}"):
        create_requisition_page.setting_requisition_details(
            item_info_1=master_item_2,
            item_info_2=master_item_2_full_path
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_information')

    # Step 2: Search the same Framework Agreement (Applicable For: Both, then HO/HCMP)
    with allure.step(f"Step 2: Search Active Framework Agreement {active_framework_agreement}"):
        second_item_applicable_for = create_requisition_page.search_active_framework(
            agreement_number=active_framework_agreement
        )
        allure.attach(
            f"{active_framework_agreement} found with Applicable For: {second_item_applicable_for}",
            name="Active Framework Agreement search",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_active_framework_search')

    # Step 3: Select an item of the Framework Agreement (not the Wishlist item)
    with allure.step(f"Step 3: Select an item of {active_framework_agreement} "
                     f"(not the Wishlist item {selected_product['fwa_product_code']})"):
        second_item = create_requisition_page.select_active_framework_item(
            agreement_number=active_framework_agreement,
            exclude_item_code=selected_product["fwa_product_code"]
        )
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in second_item.items())
            + f"\napplicable_for: {second_item_applicable_for}",
            name="Selected active framework item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_active_framework_item_selected')

    # Step 4: Enter the second item quantity from .env
    with allure.step(f"Step 4: Enter second item quantity {requisition_item_2_quantity}"):
        create_requisition_page.finalize_item_quantity(item_quantity=f"{second_item_quantity:.2f}")
        create_requisition_page.verify_item_quantity(expected_quantity=second_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_second_item_quantity')

    # Step 5: Click Amount, then Quantity radio button
    with allure.step("Step 5: Click Amount radio button, then Quantity radio button"):
        create_requisition_page.reset_cost_allocation_by_quantity()
        create_requisition_page.verify_item_quantity(expected_quantity=second_item_quantity)
        create_requisition_page.get_full_page_screenshot('requisition_second_item_cost_allocation')

    # Step 6: Select a different GL Code
    with allure.step(f"Step 6: Select GL Code {item_gl_code_2}"):
        create_requisition_page.setting_item_gl_code(gl_code=item_gl_code_2)
        create_requisition_page.get_full_page_screenshot('requisition_second_item_gl_code')

    # Step 7: Add attachment from utils
    with allure.step(f"Step 7: Add attachment {attachment_path_2.name}"):
        assert create_requisition_page.upload_requisition_item_document(str(attachment_path_2)), \
            f"Attachment upload failed: {attachment_path_2.name}"
        allure.attach(
            f"{attachment_path_2.name} ({attachment_size_mb_2:.2f} MB)",
            name="Second item attachment",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_attachment')

    # Step 8: Add item remarks, click Add to grid and verify 2 items
    with allure.step("Step 8: Add item remarks, click Add to grid and verify 2 items"):
        create_requisition_page.setting_item_remarks(item_remarks=requisition_item_remarks)
        create_requisition_page.add_item_requisition_details_information_list()
        grid_item_2 = create_requisition_page.verify_grid_item(
            quantity=second_item_quantity,
            unit_price=second_item["unit_price"]
        )
        create_requisition_page.verify_grid_row_count(expected_count=2)
        allure.attach(
            grid_item_2,
            name="Requisition Detail Information List second item",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_second_item_add_to_grid')


@allure.suite("Requisition")
@allure.feature("Create Requisition")
@allure.story("Submit Requisition")
@allure.title("Test_case_4: Submit requisition with wishlist and active framework agreement items")
@allure.description("Test case 4: Set the delivery schedule and Head Office location, submit the requisition with "
                    "2 items and get the submission confirmation message and requisition number.")
@pytest.mark.order(4)
def test_4_submit_requisition(page):
    """
    Test Case 4: Submit the requisition with the Wishlist item and the Active Framework Agreement item.

    Steps:
        1. Set same schedule (today).
        2. Set delivery location: Head Office and 'test_schedule_address'.
        3. Submit the requisition, get the submission confirmation message and store the
           requisition number in 'req_num'.

    All scenario values are read from .env.
    """
    global req_num, req_submission_message

    # Both items come from Test Case 2 and 3
    assert selected_wishlist_item and second_item, \
        "Test Case 2 and 3 must pass first: requisition items are not added"
    assert schedule_address, "Missing in .env: test_schedule_address"

    create_requisition_page = CreateRequisition(page)

    # Step 1: Same schedule for today
    with allure.step("Step 1: Set same schedule (today)"):
        create_requisition_page.setting_same_schedule_for_date()
        create_requisition_page.get_full_page_screenshot('requisition_schedule')

    # Step 2: Delivery location (Head Office)
    with allure.step(f"Step 2: Set delivery location Head Office - {schedule_address}"):
        create_requisition_page.setting_location_for_head_office(address=schedule_address)
        create_requisition_page.get_full_page_screenshot('requisition_delivery_location')

    # Step 3: Submit requisition, get the confirmation message and requisition number
    with allure.step("Step 3: Submit requisition"):
        req_submission_message, req_num = create_requisition_page.submit_requisition_with_message()
        assert req_num, "Requisition number not displayed after Submit"
        print("SUBMISSION MESSAGE:", req_submission_message)
        print("REQ NUM:", req_num)
        allure.attach(
            req_submission_message,
            name="Submission confirmation message",
            attachment_type=allure.attachment_type.TEXT
        )
        allure.attach(
            req_num,
            name="Requisition number",
            attachment_type=allure.attachment_type.TEXT
        )
        create_requisition_page.get_full_page_screenshot('requisition_submitted')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Requisition Approver")
@allure.title("Test_case_5: Identify first approver")
@allure.description("Test case 5: Identify and capture the first approver of a submitted requisition.")
@pytest.mark.order(5)
def test_5_identify_first_approver(page):
    """
    Test Case 5: Identify and capture the first approver of the submitted requisition (same as sanity.py).

    Steps:
        1. Go to Requisition > Requisition List.
        2. Search the submitted requisition ('req_num').
        3. Get the first layer approver ID ('approver_id') and status ('req_status').
        4. Exit and log out from ERP.
    """
    global approver_id, req_status

    assert req_num, "Test Case 4 must pass first: no requisition number available"

    create_requisition_page = CreateRequisition(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Requisition > Requisition List
    with allure.step("Step 1: Go to Requisition > Requisition List"):
        create_requisition_page.navigate_to_requisition_list()
        requisition_list_page.get_full_page_screenshot('requisition_list')

    # Step 2: Search the submitted requisition
    with allure.step(f"Step 2: Search requisition {req_num}"):
        requisition_list_page.search_requisition(req_num)
        requisition_list_page.get_full_page_screenshot('requisition_list_search')

    # Step 3: Get first layer approver ID and status
    with allure.step(f"Step 3: Get first layer approver ID and status of {req_num}"):
        approver_id = str(int(requisition_list_page.find_approver_id()))
        req_status = requisition_list_page.find_requisition_status()
        print("APPROVER ID:", approver_id)
        print("REQ STATUS:", req_status)
        allure.attach(
            f"Requisition number: {req_num}\nFirst approver ID: {approver_id}\nStatus: {req_status}",
            name="First approver ID and status",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_list_page.get_full_page_screenshot('requisition_first_approver_id')

    # Step 4: Exit and log out (same as sanity.py)
    with allure.step("Step 4: Exit and log out from ERP"):
        m_page = MainNavigationBar(page)
        m_page.exit()
        m_page.logout()
        m_page.get_full_page_screenshot('requisition_initiator_logout')
        m_page.wait_for_timeout(2000)


def erp_login(page, user_name):
    # ERP login with ResetHub link (same as sanity.py)
    reset_page = ResetHubPage(page)
    link = reset_page.generate_reset_link(
        env=proj_env,
        username=user_name,
    )
    reset_page.open_generated_link(link)
    assert isinstance(link, str) and link.startswith("http")
    print(f"Logging in as user: {user_name}")


def erp_logout(page, screenshot_name):
    # Exit and log out from ERP (same as sanity.py)
    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.get_full_page_screenshot(screenshot_name)
    m_page.wait_for_timeout(2000)


@allure.suite("Requisition")
@allure.feature("Requisition Approve List")
@allure.story("First Layer Approval")
@allure.title("Test_case_6: Approve requisition as first approver")
@allure.description(
    "Test case 6: Login as the first approver and approve the submitted requisition in the ERP Procurement system.")
@pytest.mark.order(6)
def test_6_approve_requisition_as_first_approver(page):
    """
    Test case 6: Login as the first approver and approve the submitted requisition.

    Steps:
        1. Log in to ERP as the first approver ('approver_id') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition and approve it.
        4. Exit and log out.
    """
    assert req_num and approver_id, "Test case 5 must pass first: no requisition number/approver ID available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_approve_list_page = RequisitionApproveList(page)

    # Step 1: Log in as the first approver
    with allure.step(f"Step 1: Log in to ERP as first approver {approver_id}"):
        erp_login(page, approver_id)
        proc_dashboard_page.menu_click_procurement_hyperlink()
        proc_dashboard_page.get_full_page_screenshot('requisition_first_approver_login')

    # Step 2: Requisition Approve List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition Approve List"):
        proc_home_page.navigate_to_requisition_approve_list()
        requisition_approve_list_page.search_requisition(req_num)
        requisition_approve_list_page.get_full_page_screenshot('requisition_first_approver_search')

    # Step 3: Select and approve the requisition
    with allure.step(f"Step 3: Approve requisition {req_num} as first approver"):
        requisition_approve_list_page.select_requisition()
        requisition_approve_list_page.approve_requisition()
        allure.attach(
            f"Requisition number: {req_num}\nApproved by first approver: {approver_id}",
            name="First layer approval",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_approve_list_page.get_full_page_screenshot('requisition_first_approver_approved')
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_first_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Second Layer Approval")
@allure.title("Test_case_7: Identify second approver")
@allure.description(
    "Test case 7: Identify and capture the second-level approver of a submitted requisition in the ERP "
    "Procurement system.")
@pytest.mark.order(7)
def test_7_identify_second_approver(page):
    """
    Test case 7: Identify and capture the second-level approver of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List and search the requisition ('req_num').
        3. Get the second (final) layer approver ID ('approver_id_2') and status.
        4. Exit and log out.
    """
    global approver_id_2
    assert req_num, "Test case 4 must pass first: no requisition number available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Log in as the requisition initiator
    with allure.step(f"Step 1: Log in to ERP as requisition initiator {proj_user}"):
        erp_login(page, proj_user)
        proc_dashboard_page.goto_procurement()

    # Step 2: Requisition List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition List"):
        proc_home_page.navigate_to_requisition_list()
        requisition_list_page.search_requisition(req_num)
        requisition_list_page.get_full_page_screenshot('requisition_second_approver_search')

    # Step 3: Get the second (final) layer approver ID
    with allure.step("Step 3: Get the second (final) layer approver ID"):
        approver_id_2 = str(int(requisition_list_page.find_approver_id()))
        second_layer_status = requisition_list_page.find_requisition_status()
        print("APPROVER ID 2:", approver_id_2)
        allure.attach(
            f"Requisition number: {req_num}\nSecond approver ID: {approver_id_2}\nStatus: {second_layer_status}",
            name="Second approver ID and status",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_list_page.get_full_page_screenshot('requisition_second_approver_id')

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_second_approver_identify_logout')


@allure.suite("Requisition")
@allure.feature("Requisition Approve List")
@allure.story("Second Layer Approval")
@allure.title("Test_case_8: Approve requisition as final approver")
@allure.description(
    "Test case 8: Login as the second-level (final) approver and approve the submitted requisition in the ERP "
    "Procurement system.")
@pytest.mark.order(8)
def test_8_approve_requisition_as_final_approver(page):
    """
    Test case 8: Login as the second-level (final) approver and approve the requisition.

    Steps:
        1. Log in to ERP as the final approver ('approver_id_2') and go to Procurement.
        2. Go to Requisition Approve List and search the requisition ('req_num').
        3. Select the requisition and approve it.
        4. Exit and log out.
    """
    assert req_num and approver_id_2, "Test case 7 must pass first: no requisition number/second approver available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_approve_list_page = RequisitionApproveList(page)

    # Step 1: Log in as the final approver
    with allure.step(f"Step 1: Log in to ERP as final approver {approver_id_2}"):
        erp_login(page, approver_id_2)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('requisition_final_approver_login')

    # Step 2: Requisition Approve List and search the requisition
    with allure.step(f"Step 2: Search requisition {req_num} in Requisition Approve List"):
        proc_home_page.navigate_to_requisition_approve_list()
        requisition_approve_list_page.search_requisition(req_num)
        requisition_approve_list_page.get_full_page_screenshot('requisition_final_approver_search')

    # Step 3: Select and approve the requisition
    with allure.step(f"Step 3: Approve requisition {req_num} as final approver"):
        requisition_approve_list_page.select_requisition()
        requisition_approve_list_page.approve_requisition()
        allure.attach(
            f"Requisition number: {req_num}\nApproved by final approver: {approver_id_2}",
            name="Final layer approval",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_approve_list_page.get_full_page_screenshot('requisition_final_approver_approved')
        requisition_approve_list_page.wait_for_timeout(2000)

    # Step 4: Exit and log out
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'requisition_final_approver_logout')


@allure.suite("Requisition")
@allure.feature("Requisition List")
@allure.story("Requisition Status")
@allure.title("Test_case_9: Requisition initiator gets approval status")
@allure.description(
    "Test case 9: Login as the requisition initiator, get the approval status of the requisition and verify the "
    "requisition details (FA No, items, quantities, unit prices) and vendor match the Marketplace Wishlist item and "
    "the Active Framework Agreement item.")
@pytest.mark.order(9)
def test_9_requisition_initiator_gets_approval_status(page, new_tab):
    """
    Test case 9: Requisition initiator gets the approval status of the requisition.

    Steps:
        1. Log in to ERP as the requisition initiator ('proj_user') and go to Procurement.
        2. Go to Requisition List, search the requisition ('req_num') and get its approval status.
        3. Open the requisition details in a new tab and verify both items of the requisition:
           the Wishlist item (Test case 2) and the Active Framework Agreement item (Test case 3)
           with their FA No, item, quantity and unit price.
        4. Open the FA No link in a new tab and verify the vendor is the same as the
           Marketplace vendor ('agreement_vendor_name', Test case 1).
        5. Close the tabs, exit and log out.
    """
    global approved_req_status, verified_requisition_details, order_vendor
    assert req_num, "Test case 4 must pass first: no requisition number available"
    assert selected_wishlist_item and second_item, "Test case 2 and 3 must pass first: requisition items not available"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    requisition_list_page = RequisitionList(page)

    # Step 1: Log in as the requisition initiator
    with allure.step(f"Step 1: Log in to ERP as requisition initiator {proj_user}"):
        erp_login(page, proj_user)
        proc_dashboard_page.goto_procurement()

    # Step 2: Requisition List, search the requisition and get its approval status
    with allure.step(f"Step 2: Get approval status of requisition {req_num}"):
        proc_home_page.navigate_to_requisition_list()
        requisition_list_page.search_requisition(req_num)
        approved_req_status = requisition_list_page.find_requisition_status()
        print("REQ STATUS:", approved_req_status)
        allure.attach(
            f"Requisition number: {req_num}\nStatus: {approved_req_status}",
            name="Requisition approval status",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_list_page.get_full_page_screenshot('requisition_approval_status')

    # Step 3: Open requisition details in a new tab and verify both items
    with allure.step(f"Step 3: Verify requisition details of {req_num} (2 items)"):
        details_tab = new_tab(lambda p: requisition_list_page.goto_requisition_details_information())
        requisition_details_page = RequisitionDetailsInformation(details_tab)
        # Master item codes, e.g. "[22245]" from "[22245]-Pen Box-(...)"
        master_item_1_code = re.search(r"\[[^\]]+\]", master_item_1_full_path).group(0)
        master_item_2_code = re.search(r"\[[^\]]+\]", master_item_2_full_path).group(0)
        second_item_quantity = env_decimal("test_requisition_item_2_quantity", requisition_item_2_quantity)

        requisition_details_page.verify_requisition_item_count(fa_no=active_framework_agreement, expected_count=2)
        wishlist_item_details = requisition_details_page.verify_requisition_item(
            requisition_number=req_num,
            fa_no=active_framework_agreement,
            item_code=master_item_1_code,
            quantity=final_wishlist_quantity,
            unit_price=selected_wishlist_item["unit_price"]
        )
        second_item_details = requisition_details_page.verify_requisition_item(
            requisition_number=req_num,
            fa_no=active_framework_agreement,
            item_code=master_item_2_code,
            quantity=second_item_quantity,
            unit_price=second_item["unit_price"]
        )
        verified_requisition_details = {
            "wishlist_item": wishlist_item_details,
            "second_item": second_item_details,
        }
        allure.attach(
            f"Requisition number: {req_num}\nStatus: {approved_req_status}\nFA. No: {active_framework_agreement}\n"
            f"Item 1 (Wishlist): {master_item_1_code}, quantity {final_wishlist_quantity}, "
            f"unit price {selected_wishlist_item['unit_price']}\n  Details row: {wishlist_item_details}\n"
            f"Item 2 (Active Framework Agreement): {master_item_2_code}, quantity {second_item_quantity}, "
            f"unit price {second_item['unit_price']}\n  Details row: {second_item_details}",
            name="Verified requisition details",
            attachment_type=allure.attachment_type.TEXT
        )
        requisition_details_page.get_full_page_screenshot('requisition_details_verified')

    # Step 4: Open the FA No link and verify the vendor is the same as the Marketplace vendor
    with allure.step(f"Step 4: Verify vendor of {active_framework_agreement} is {agreement_vendor_name}"):
        framework_tab = new_tab(lambda p: requisition_details_page.open_framework_details())
        framework_info_page = FrameworkInformation(framework_tab)
        requisition_vendor_name = framework_info_page.get_vendor_info()
        order_vendor = requisition_vendor_name
        assert agreement_vendor_name.lower() in requisition_vendor_name.lower(), \
            f"Requisition vendor '{requisition_vendor_name}' is not the same as the Marketplace vendor " \
            f"'{agreement_vendor_name}'"
        allure.attach(
            f"Marketplace vendor (Test case 1): {agreement_vendor_name}\n"
            f"Requisition vendor (FA No link): {requisition_vendor_name}",
            name="Verified vendor",
            attachment_type=allure.attachment_type.TEXT
        )
        framework_info_page.get_full_page_screenshot('requisition_vendor_verified')

    # Step 5: Close the tabs, exit and log out
    with allure.step("Step 5: Close requisition details tabs, exit and log out from ERP"):
        framework_tab.close()
        details_tab.close()
        page.bring_to_front()
        erp_logout(page, 'requisition_initiator_final_logout')


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Preparation")
@allure.title("Test_case_10: Prepare cart for checkout")
@allure.description("Test case 10: Marketplace order initiation process by preparing the shopping cart with the 2 "
                    "requisition items (first item: attachment, quantity and remarks updated).")
@pytest.mark.order(10)
def test_10_prepare_cart_for_checkout(page):
    """
    Test case 10: Prepare the shopping cart for checkout (same as sanity.py test 7, with 2 items).

    Steps:
        1. Log in to the Digital Marketplace as the order initiator ('proj_user').
        2. Go to the shopping cart and select the vendor (Test case 1) for the requisition ('req_num').
        3. Upload attachment for the first item.
        4. Update the first item quantity ('test_fractional_cart_qty').
        5. Update the first item remarks and the shopping cart.
           The second item stays as it was created in the requisition.
        6. Accept terms of service and checkout.
    """
    assert req_num and approved_req_status, "Test case 9 must pass first: requisition is not approved"
    assert fractional_cart_qty, "Missing in .env: test_fractional_cart_qty"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    cart_page = ShoppingCart(page)
    attachment_path = UTILS_DIR / requisition_attachment_file

    # Step 1: Log in to the Digital Marketplace
    with allure.step(f"Step 1: Log in to the Digital Marketplace as {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=proj_user, pass_word=marketplace_password)
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('cart_marketplace_login')

    # Step 2: Shopping cart and vendor selection
    with allure.step(f"Step 2: Select vendor {order_vendor} for requisition {req_num}"):
        home_page.goto_shopping_cart()
        cart_page.select_vendor_for_requisition_found(requisition_number=req_num)
        assert cart_page.select_vendor_by_name(vendor_name=order_vendor, requisition_number=req_num), \
            f"Vendor {order_vendor} not found in the shopping cart"
        cart_page.get_full_page_screenshot('cart_vendor_selected')

    # Step 3: First item attachment
    with allure.step(f"Step 3: Upload attachment {attachment_path.name} for the first item"):
        assert cart_page.upload_attachment(str(attachment_path)), "File upload failed"
        cart_page.get_full_page_screenshot('cart_attachment')

    # Step 4: First item quantity
    with allure.step(f"Step 4: Update the first item quantity to {fractional_cart_qty}"):
        cart_page.update_shopping_cart_value_1(qty_update=fractional_cart_qty)
        allure.attach(
            f"Requisition number: {req_num}\nFirst item cart quantity: {fractional_cart_qty}",
            name="Updated cart quantity",
            attachment_type=allure.attachment_type.TEXT
        )
        cart_page.get_full_page_screenshot('cart_quantity_updated')

    # Step 5: First item remarks and update shopping cart
    with allure.step("Step 5: Update the first item remarks and the shopping cart"):
        cart_page.update_cart_item_remarks(requisition_number=req_num, remarks_text=requisition_item_remarks)
        cart_page.update_shopping_cart_info()
        cart_page.get_full_page_screenshot('cart_updated')

    # Step 6: Accept terms of service and checkout
    with allure.step("Step 6: Accept terms of service and checkout"):
        cart_page.cart_page_checkout()
        cart_page.get_full_page_screenshot('cart_checkout')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Preparation Window")
@allure.title("Test_case_11: Prepare delivery schedule")
@allure.description("Test case 11: Preparing order delivery schedule for 2 items (Auto Generate, first item "
                    "same as sanity.py, second item receiving person).")
@pytest.mark.order(11)
def test_11_prepare_delivery_schedule(page):
    """
    Test case 11: Prepare the order delivery schedule (same as sanity.py test 8, with 2 items).

    Steps:
        1. Click Auto Generate: the second item gets its delivery schedule.
        2. First item (updated cart quantity): schedule quantity, expected date, location 1 and
           receiving person 1, then Add Schedule (same as sanity.py).
        3. First item remaining quantity: location 2 and receiving person 'order_initiator', then Add Schedule.
        4. Second item: Receiving Person 'order_initiator' in the auto generated schedule row.
        5. Wait until Continue is enabled and click Continue.
    """
    required_env_values = {
        "test_delivery_schedule_quantity": delivery_schedule_quantity,
        "test_delivery_location_1": manual_delivery_location_1,
        "test_delivery_location_2": manual_delivery_location_2,
        "test_receiving_pin": receiving_pin_1,
        "test_order_initiator": order_initiator,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    checkout_page = CheckoutPage(page)

    # Step 1: Auto Generate delivery schedule
    with allure.step("Step 1: Click Auto Generate"):
        checkout_page.auto_generate_schedule()
        checkout_page.get_full_page_screenshot('schedule_auto_generate')

    # Step 2: First item schedule (same as sanity.py)
    with allure.step(f"Step 2: First item schedule {delivery_schedule_quantity} - {manual_delivery_location_1}"):
        checkout_page.fractional_schedule_update_quantity(delivery_schedule_quantity=delivery_schedule_quantity)
        checkout_page.update_expected_date()
        checkout_page.delivery_schedule_preparation(location=manual_delivery_location_1, pin=receiving_pin_1)
        checkout_page.click_add_schedule_btn()
        checkout_page.wait_for_timeout(2000)
        checkout_page.get_full_page_screenshot('schedule_first_item_1')

    # Step 3: First item remaining quantity
    with allure.step(f"Step 3: First item remaining quantity - {manual_delivery_location_2}"):
        checkout_page.delivery_schedule_preparation(location=manual_delivery_location_2, pin=order_initiator)
        checkout_page.click_add_schedule_btn()
        checkout_page.get_full_page_screenshot('schedule_first_item_2')

    # Step 4: Second item receiving person in the auto generated schedule row
    with allure.step(f"Step 4: Second item Receiving Person {order_initiator}"):
        checkout_page.fill_generated_schedule_receiving_person(pin=order_initiator)
        checkout_page.get_full_page_screenshot('schedule_second_item')

    # Step 5: Continue (enabled after all delivery schedule information is complete)
    with allure.step("Step 5: Wait until Continue is enabled and click Continue"):
        allure.attach(
            f"First item: {delivery_schedule_quantity} to {manual_delivery_location_1} ({receiving_pin_1}), "
            f"remaining to {manual_delivery_location_2} ({order_initiator})\n"
            f"Second item: auto generated schedule, receiving person {order_initiator}",
            name="Delivery schedule",
            attachment_type=allure.attachment_type.TEXT
        )
        checkout_page.click_continue_when_enabled()
        checkout_page.get_full_page_screenshot('schedule_continue')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order")
@allure.title("Test_case_12: Confirm marketplace order")
@allure.description("Test case 12: Confirm marketplace order, get the order reference number and order status.")
@pytest.mark.order(12)
def test_12_confirm_marketplace_order(page):
    """
    Test case 12: Confirm the marketplace order (same as sanity.py test 9).

    Steps:
        1. Fill the order remarks ('order_remarks') and accept terms of service.
        2. Confirm the order and store the order reference number in 'order_reference_number'.
        3. Open the order details and store the order status in 'order_status'.
        4. Log out from the Digital Marketplace.
    """
    global order_reference_number, order_status
    assert order_remarks, "Missing in .env: test_order_remarks"

    checkout_page = CheckoutPage(page)

    # Step 1: Order remarks and terms of service
    with allure.step(f"Step 1: Fill order remarks '{order_remarks}' and accept terms of service"):
        checkout_page.fillup_order_remarks(input_remarks=order_remarks)
        checkout_page.select_terms_of_service()
        checkout_page.get_full_page_screenshot('order_remarks_terms')

    # Step 2: Confirm the order and store the order reference number
    with allure.step("Step 2: Confirm marketplace order"):
        order_reference_number = checkout_page.confirm_order()
        assert order_reference_number, "Order reference number not displayed after Confirm"
        print("ORDER REFERENCE NUMBER:", order_reference_number)
        allure.attach(
            order_reference_number,
            name="Marketplace order reference number",
            attachment_type=allure.attachment_type.TEXT
        )
        checkout_page.wait_for_timeout(2000)
        checkout_page.get_full_page_screenshot('order_confirmed')

    # Step 3: Order details and status
    with allure.step(f"Step 3: View order details of {order_reference_number}"):
        order_status = checkout_page.goto_public_side_order_details_view()
        print("ORDER STATUS:", order_status)
        allure.attach(
            f"Order reference number: {order_reference_number}\nOrder status: {order_status}",
            name="Order status",
            attachment_type=allure.attachment_type.TEXT
        )
        checkout_page.get_full_page_screenshot('order_details')

    # Step 4: Log out from the Digital Marketplace
    with allure.step("Step 4: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        checkout_page.get_full_page_screenshot('order_initiator_logout')
