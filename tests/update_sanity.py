from dotenv import load_dotenv
import os
import re
import random
import string
from decimal import Decimal, InvalidOperation
from datetime import datetime
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
from pages.digital_marketplace.public_side.my_account.pending_approval_orders import PendingApprovalOrders
from pages.digital_marketplace.public_side.my_account.orders_public_store import OrdersPublicStore
from pages.digital_marketplace.public_side.my_account.my_delegated_orders import MyDelegatedOrders
from pages.digital_marketplace.public_side.my_account.all_order_for_admin import AllOrderForAdminPage
from pages.digital_marketplace.administration.customers import Customers
from pages.digital_marketplace.administration.vendor_dashboard import VendorDashboard
from pages.digital_marketplace.administration.order_management.order_details_administration import \
    OrderDetailsAdministration
from pages.digital_marketplace.administration.order_management.orders_list_management import OrdersListManagement
from pages.digital_marketplace.administration.order_management.receivable_order_list import ReceivableOrderList
from pages.digital_marketplace.administration.order_management.item_received_list import ItemReceivedList
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_order_list import FrameworkOrderListPage
from pages.erp_procurement.my_dashboard.table_of_authority.authority_delegation.delegation_of_authority import \
    DelegationOfAuthority
from pages.erp_procurement.my_dashboard.table_of_authority.authority_delegation.delegation_of_authority_list import \
    DelegationOfAuthorityListPage
from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.my_dashboard.procurement.requisition.create_requisition import CreateRequisition
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_list import RequisitionList
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_approve_list import RequisitionApproveList
from pages.erp_procurement.my_dashboard.procurement.requisition.requisition_details_information import \
    RequisitionDetailsInformation
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.item_receive.itemreceivelist import ItemReceiveList
from pages.erp_procurement.my_dashboard.procurement.bill_payable.create_vendor_bill_payable import \
    CreateVendorBillPayable
from pages.erp_procurement.my_dashboard.procurement.bill_payable.vendor_billing_list import VendorBillingList
from pages.erp_procurement.my_dashboard.procurement.bill_payable.bill_details_information import \
    BillDetailsInformation
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
# Delegation of Authority (Test case 14-16)
delegated_approver = os.getenv("test_delegated_approver")
module_selection = os.getenv("test_module_selection")
dm_order_approval_category = os.getenv("test_dm_order_approval_category")
# Marketplace admin and vendor (Test case 19-21)
dm_admin = os.getenv("test_order_admin")
stg_vendor_pass = os.getenv("test_stg_vendor_pass")
# Framework order and item receiving (Test case 22-24)
proc_admin = os.getenv("test_proc_admin")
sso_login_receiver_pin = os.getenv("test_sso_login_receiver_pin")
# Bill payable (Test case 30-37)
bill_creator = os.getenv("test_bill_creator")
bill_recommender = os.getenv("test_bill_recommender")
bill_type = os.getenv("test_bill_type")
bill_attachment_file = os.getenv("test_bill_attachment_file")

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
receiving_remarks = os.getenv("test_receiving_remarks")
partial_receiving_remarks = os.getenv("test_partial_receiving_remarks")
# Item receiving by the order initiator (Test case 25-28)
partial_receive_quantity = os.getenv("test_partial_receive_quantity")
receiving_attachment_file_partial = os.getenv("test_receiving_attachment_file_partial")
receiving_attachment_file_remaining = os.getenv("test_receiving_attachment_file_remaining")

# Attachment and remarks rules
UTILS_DIR = Path(__file__).resolve().parents[1] / "utils"
ALLOWED_ATTACHMENT_TYPES = {".docx", ".pdf", ".xls", ".jpg", ".png", ".ppt", ".zip", ".pptx"}
MAX_ATTACHMENT_SIZE_MB = 20
MAX_REQUISITION_REMARKS_LENGTH = 300
MAX_ITEM_REMARKS_LENGTH = 500
MIN_RECEIVING_REMARKS_LENGTH = 3
MAX_RECEIVING_REMARKS_LENGTH = 255

# Marketplace global variable
initial_wishlist_count = 0
agreement_vendor_name = ''
# Order vendor from the requisition FA No link (same as sanity.py), used in the shopping cart
order_vendor = ''
# Marketplace order (Test case 12)
order_reference_number = ''
order_status = ''
actual_approver_pending_approval_orders = ''
# Delegation (same as sanity.py)
delegated_order_count_before_delegation = ''
removed_current_date_delegations = []
delegation_remarks = str(random.randint(10000, 99999))
delegated_order_count_after_delegation = ''
delegated_order_status = ''
# Vendor acknowledgement (Test case 19-21)
vendor_login_id = ''
framework_order_no = ''
vendor_acknowledged_order_status = ''
# Item receiving: challan numbers are generated after the framework order is known (DM_4552KEs5Pm)
challan_num_for_receiver = ''
challan_num_for_order_initiator = ''
challan_num_for_order_initiator_2 = ''
# Bill payable: bill number generated after the framework order is known (DM_Bill4556xyZ7k)
bill_num = ''
billed_challan = ''
bill_recommender_1 = ''
bill_recommender_2 = ''
bill_recommender_3 = ''
final_bill_status = ''
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
        1. Log in to ERP (ResetHub link) and open
           Procurement > Requisition > Create Requisition.
        2. Select Head Office, Project, Source of Fund and enter Remarks (max 300 characters).
        3. Search and select Item Information.
        4. Click Get wishlist.
        5. Find the Wishlist item added in Test Case 1 (FA No + FWA code, next page if needed)
           and click that row. Verify that Quantity is the same as the Wishlist quantity.
        6. Click Amount radio button, then Quantity radio button; verify Quantity is unchanged.
        7. Select GL Code.
        8. Add attachment from utils (max 20 MB; DOCX, PDF, XLS, JPG, PNG, PPT, ZIP, PPTX).
        9. Add item remarks (max 500 characters), click Add to grid and verify the item row
           (Quantity and Unit Price) in the Requisition Detail Information List.
        10. Set the same schedule (today).
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

    # Step 1: Log in to ERP and open Create Requisition
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

    # Step 4: Click the Get wishlist
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
        1. Set the same schedule (today).
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
    Test Case 5: Identify and capture the first approver of the submitted requisition.

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
    # ERP login with the ResetHub link
    reset_page = ResetHubPage(page)
    link = reset_page.generate_reset_link(
        env=proj_env,
        username=user_name,
    )
    reset_page.open_generated_link(link)
    assert isinstance(link, str) and link.startswith("http")
    print(f"Logging in as user: {user_name}")


def generate_challan_number():
    # DM_ + framework (work) order last 4 digits + random characters, e.g. DM_4552KEs5Pm
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"DM_{framework_order_no[-4:]}{random_part}"


def check_receiving_remarks_length(env_name, remarks):
    # Received Remarks: minimum 3, maximum 255 characters
    assert MIN_RECEIVING_REMARKS_LENGTH <= len(remarks) <= MAX_RECEIVING_REMARKS_LENGTH, \
        f"{env_name} must be {MIN_RECEIVING_REMARKS_LENGTH}-{MAX_RECEIVING_REMARKS_LENGTH} characters, " \
        f"found {len(remarks)}"


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
    Test case 10: Prepare the shopping cart for checkout (with 2 items).

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
        assert cart_page.wait_for_requisition_in_cart(requisition_number=req_num), \
            f"Requisition {req_num} is not synced to the shopping cart"
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
    Test case 11: Prepare the order delivery schedule (with 2 items).

    Steps:
        1. Click Auto Generate: the second item gets its delivery schedule.
        2. First item (updated cart quantity): schedule quantity, expected date, location 1 and
           receiving person 1, then Add Schedule.
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
    Test case 12: Confirm the marketplace order.

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


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("Pending Approval Orders")
@allure.title("Test_case_13: Verify order in pending approval list")
@allure.description("Test case 13: Verify Marketplace Order in Approver's Pending Approval List")
@pytest.mark.order(13)
def test_13_verify_order_in_pending_approval_list(page):
    """
    Test case 13: Verify the marketplace order in the approver's Pending Approval list (same as sanity.py test 10).

    Steps:
        1. Log in to the Digital Marketplace as the order approver ('approver_id_2').
        2. Go to Orders > Pending Approval Orders.
        3. Get the pending approval order count ('actual_approver_pending_approval_orders').
        4. Search the order reference number ('order_reference_number') and verify the order is in the list.
        5. Log out from the Digital Marketplace.
    """
    global actual_approver_pending_approval_orders
    assert order_reference_number, "Test case 12 must pass first: no order reference number available"
    assert approver_id_2, "Test case 7 must pass first: no order approver available"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    pending_approval_orders = PendingApprovalOrders(page)

    # Step 1: Log in as the order approver
    with allure.step(f"Step 1: Log in to the Digital Marketplace as order approver {approver_id_2}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=approver_id_2, pass_word=marketplace_password)
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('order_approver_login')

    # Step 2: Orders > Pending Approval Orders
    with allure.step("Step 2: Go to Orders > Pending Approval Orders"):
        home_page.goto_order_list()
        home_page.goto_pending_approval_orders_list()
        home_page.get_full_page_screenshot('pending_approval_orders')

    # Step 3: Pending approval order count
    with allure.step("Step 3: Get pending approval order count"):
        actual_approver_pending_approval_orders = pending_approval_orders.get_pending_approval_order_count(
            pending_approval_order_count=actual_approver_pending_approval_orders)
        allure.attach(
            f"Order approver: {approver_id_2}\nPending approval orders: {actual_approver_pending_approval_orders}",
            name="Pending approval orders count",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 4: Search the order and verify it is in the list
    with allure.step(f"Step 4: Search order {order_reference_number} in Pending Approval Orders"):
        pending_approval_orders.search_order_input(reference_number=order_reference_number)
        pending_approval_orders.click_order_search_button()
        pending_approval_orders.verify_order_in_list(reference_number=order_reference_number)
        allure.attach(
            f"Order {order_reference_number} found in the pending approval list of {approver_id_2}",
            name="Order found",
            attachment_type=allure.attachment_type.TEXT
        )
        pending_approval_orders.get_full_page_screenshot('pending_approval_order_search')

    # Step 5: Log out from the Digital Marketplace
    with allure.step("Step 5: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        home_page.get_full_page_screenshot('order_approver_logout')


@allure.suite("Table of Authority")
@allure.feature("Delegation of Authority")
@allure.story("DM Order Approval Delegation")
@allure.title("Test_case_14: Remove current date delegation before creating delegation")
@allure.description("Test case 14: Check the Delegation Of Authority List for a delegation of the delegated approver "
                    "in the current date range and remove it before creating a new delegation.")
@pytest.mark.order(14)
def test_14_remove_current_date_delegation_before_creation(page):
    """
    Test case 14: Remove the current date delegation before creating a new delegation.

    Steps:
        1. Log in to ERP as the order approver ('approver_id_2', delegator).
        2. Go to the Delegation Of Authority List and search the delegated approver by PIN.
        3. If a delegation for the current date range is present (Start Date <= today <= End Date),
           remove it (Remove > Delete item(s)) and verify the deleted message.
           If not present, continue.
        4. Exit and log out from ERP.
    """
    global removed_current_date_delegations
    assert approver_id_2, "Test case 7 must pass first: no order approver available"
    assert delegated_approver, "Missing in .env: test_delegated_approver"

    proc_dashboard_page = DashboardPage(page)
    delegation_list_page = DelegationOfAuthorityListPage(page)

    # Step 1: Log in to ERP as the order approver (delegator)
    with allure.step(f"Step 1: Log in to ERP as order approver {approver_id_2}"):
        erp_login(page, approver_id_2)
        proc_dashboard_page.get_full_page_screenshot('delegator_login')

    # Step 2: Delegation Of Authority List and search the delegated approver
    with allure.step(f"Step 2: Search delegated approver {delegated_approver} in Delegation Of Authority List"):
        # Directly from the dashboard to the Delegation Of Authority List
        proc_dashboard_page.navigate_to_delegation_of_authority_list()
        delegation_list_page.wait_for_timeout(2000)
        delegation_list_page.search_by_delegated_approver_by_PIN(PIN=delegated_approver)
        delegation_list_page.get_full_page_screenshot('delegation_list_before_creation')

    # Step 3: Remove the current date delegation if present
    with allure.step("Step 3: Remove current date delegation if present"):
        removed_current_date_delegations = delegation_list_page.remove_current_date_delegations(
            PIN=delegated_approver
        )
        allure.attach(
            f"Delegated approver: {delegated_approver}\n"
            + (f"Removed current date delegation(s): {', '.join(removed_current_date_delegations)}"
               if removed_current_date_delegations else "No delegation for the current date"),
            name="Current date delegation",
            attachment_type=allure.attachment_type.TEXT
        )
        delegation_list_page.get_full_page_screenshot('delegation_list_current_date_removed')

    # Step 4: Exit and log out from ERP
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'delegator_logout_after_removal')


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("My Delegated Orders")
@allure.title("Test_case_15: Verify delegated orders before delegation")
@allure.description("Test case 15: Verify My Delegated Orders Information Before Delegation")
@pytest.mark.order(15)
def test_15_verify_delegated_orders_before_delegation(page):
    """
    Test case 15: Verify My Delegated Orders before delegation.

    Steps:
        1. Log in to the Digital Marketplace as the delegated approver ('delegated_approver').
        2. Go to Orders and open My Delegated Orders if available; store the delegated order count.
        3. Log out from the Digital Marketplace.
    """
    global delegated_order_count_before_delegation
    assert delegated_approver, "Missing in .env: test_delegated_approver"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    my_account_orders_list = OrdersPublicStore(page)

    # Step 1: Log in as the delegated approver
    with allure.step(f"Step 1: Log in to the Digital Marketplace as delegated approver {delegated_approver}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=delegated_approver, pass_word=marketplace_password)
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('delegated_approver_login')

    # Step 2: Orders > My Delegated Orders
    with allure.step("Step 2: Go to Orders > My Delegated Orders and get delegated order count"):
        home_page.goto_order_list()
        delegated_order_count_before_delegation = my_account_orders_list.go_to_my_delegated_orders_if_available()
        print("DELEGATED ORDER COUNT BEFORE DELEGATION:", delegated_order_count_before_delegation)
        allure.attach(
            f"Delegated approver: {delegated_approver}\n"
            f"Delegated orders before delegation: {delegated_order_count_before_delegation}",
            name="Delegated orders count before delegation",
            attachment_type=allure.attachment_type.TEXT
        )
        my_account_orders_list.get_full_page_screenshot('delegated_orders_before_delegation')

    # Step 3: Log out from the Digital Marketplace
    with allure.step("Step 3: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        home_page.get_full_page_screenshot('delegated_approver_logout')


@allure.suite("Table of Authority")
@allure.feature("Delegation of Authority")
@allure.story("DM Order Approval Delegation")
@allure.title("Test_case_16: Create order approval delegation")
@allure.description("Test case 16: Create DM Order Approval Delegation with TOA Category")
@pytest.mark.order(16)
def test_16_create_order_approval_delegation(page):
    """
    Test case 16: Create DM Order Approval Delegation with TOA Category (same as sanity.py test 12).

    Steps:
        1. Log in to ERP as the order approver ('approver_id_2') and go to Delegation Of Authority.
        2. Select the delegated approver, TOA Category Required, module and DM Order Approval category,
           start and end date (today) and remarks ('delegation_remarks'), then Create and confirm.
        3. Go to Delegation Of Authority List and search the delegated approver by PIN.
        4. Exit and log out from ERP.
    """
    required_env_values = {
        "test_delegated_approver": delegated_approver,
        "test_module_selection": module_selection,
        "test_dm_order_approval_category": dm_order_approval_category,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    assert approver_id_2, "Test case 7 must pass first: no order approver available"

    proc_dashboard_page = DashboardPage(page)
    delegation_page = DelegationOfAuthority(page)
    delegation_list_page = DelegationOfAuthorityListPage(page)

    # Step 1: Log in as the order approver and go to Delegation Of Authority
    with allure.step(f"Step 1: Log in to ERP as order approver {approver_id_2} and go to Delegation Of Authority"):
        erp_login(page, approver_id_2)
        proc_dashboard_page.navigate_to_delegation_of_authority()
        proc_dashboard_page.get_full_page_screenshot('delegation_of_authority')

    # Step 2: Create DM Order Approval delegation
    with allure.step(f"Step 2: Create DM Order Approval delegation to {delegated_approver}"):
        delegation_page.select_delegated_employee(employee_search_text=delegated_approver)
        delegation_page.select_toa_category_required()
        delegation_page.select_module(module_name=module_selection)
        delegation_page.search_and_add_toa_category(category_name=dm_order_approval_category)
        delegation_date = delegation_page.select_date()
        delegation_page.select_start_date(delegation_date)
        delegation_page.select_end_date(delegation_date)
        delegation_page.enter_remarks(remarks=delegation_remarks)
        delegation_page.get_full_page_screenshot('delegation_form')
        delegation_page.click_create_button_and_delegation_confirmation()
        allure.attach(
            f"Delegator: {approver_id_2}\nDelegated approver: {delegated_approver}\nModule: {module_selection}\n"
            f"TOA category: {dm_order_approval_category}\nDate: {delegation_date}\nRemarks: {delegation_remarks}",
            name="Created delegation",
            attachment_type=allure.attachment_type.TEXT
        )
        delegation_page.get_full_page_screenshot('delegation_created')

    # Step 3: Delegation Of Authority List and search the delegated approver
    with allure.step(f"Step 3: Search delegated approver {delegated_approver} in Delegation Of Authority List"):
        delegation_list_page.go_to_delegation_of_authority_list()
        delegation_list_page.wait_for_timeout(2000)
        delegation_list_page.search_by_delegated_approver_by_PIN(PIN=delegated_approver)
        delegation_list_page.get_full_page_screenshot('delegation_list_after_creation')

    # Step 4: Exit and log out from ERP
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'delegator_logout')


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("My Delegated Orders")
@allure.title("Test_case_17: Verify delegated order after delegation")
@allure.description("Test case 17: My Delegated Orders verify by Delegated Approver after Delegation creation")
@pytest.mark.order(17)
def test_17_verify_delegated_order_after_delegation(page):
    """
    Test case 17: Verify the delegated order after delegation.

    Steps:
        1. Log in to the Digital Marketplace as the delegated approver ('delegated_approver').
        2. Go to Orders > My Delegated Orders; the delegated order count after delegation must be
           more than the count before delegation (Test case 15).
        3. Search the order reference number and verify the order is in My Delegated Orders; view order info.
        No logout: Test case 18 approves the order in the same session.
    """
    global delegated_order_count_after_delegation
    assert order_reference_number, "Test case 12 must pass first: no order reference number available"
    assert delegated_order_count_before_delegation != '', \
        "Test case 15 must pass first: no delegated order count before delegation"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    my_account_orders_list = OrdersPublicStore(page)
    my_delegated_orders = MyDelegatedOrders(page)

    # Step 1: Log in as the delegated approver
    with allure.step(f"Step 1: Log in to the Digital Marketplace as delegated approver {delegated_approver}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=delegated_approver, pass_word=marketplace_password)
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('delegated_approver_login_after_delegation')

    # Step 2: My Delegated Orders count after delegation
    with allure.step("Step 2: Go to Orders > My Delegated Orders and verify the delegated order count"):
        home_page.goto_order_list()
        delegated_order_count_after_delegation = my_account_orders_list.go_to_my_delegated_orders_if_available()
        print("DELEGATED ORDER COUNT AFTER DELEGATION:", delegated_order_count_after_delegation)
        allure.attach(
            f"Before delegation (Test case 15): {delegated_order_count_before_delegation}\n"
            f"After delegation: {delegated_order_count_after_delegation}",
            name="Delegated orders count",
            attachment_type=allure.attachment_type.TEXT
        )
        my_account_orders_list.get_full_page_screenshot('delegated_orders_after_delegation')
        assert delegated_order_count_after_delegation > delegated_order_count_before_delegation, \
            f"Delegated order count after delegation ({delegated_order_count_after_delegation}) is not more " \
            f"than before delegation ({delegated_order_count_before_delegation})"

    # Step 3: Search the delegated order and verify it is in the list
    with allure.step(f"Step 3: Search delegated order {order_reference_number}"):
        my_delegated_orders.search_delegated_order(delegated_order_reference_number=order_reference_number)
        my_delegated_orders.click_delegated_order_search_button()
        my_delegated_orders.verify_delegated_order_in_list(reference_number=order_reference_number)
        my_delegated_orders.view_delegated_order_info_toggle()
        allure.attach(
            f"Order {order_reference_number} found in My Delegated Orders of {delegated_approver}",
            name="Delegated order found",
            attachment_type=allure.attachment_type.TEXT
        )
        my_delegated_orders.get_full_page_screenshot('delegated_order_search')


@allure.suite("Public Side")
@allure.feature("My Account")
@allure.story("My Delegated Orders")
@allure.title("Test_case_18: Approve delegated marketplace order")
@allure.description("Test case 18: Approve Delegated Order by Delegated User")
@pytest.mark.order(18)
def test_18_approve_delegated_marketplace_order(page):
    """
    Test case 18: Approve the delegated order (same as sanity.py test 14).
    Continues in the Digital Marketplace session of Test case 17 (delegated approver).

    Steps:
        1. Open the delegated order details.
        2. Approve the order and get the order status; if the order is not approved,
           record the status and the page message (why the approval failed).
        3. Log out from the Digital Marketplace.
    """
    global delegated_order_status
    assert order_reference_number, "Test case 12 must pass first: no order reference number available"

    my_delegated_orders = MyDelegatedOrders(page)

    # Step 1: Delegated order details
    with allure.step(f"Step 1: Open delegated order details of {order_reference_number}"):
        my_delegated_orders.goto_delegated_order_details(reference_number=order_reference_number)
        my_delegated_orders.get_full_page_screenshot('delegated_order_details')

    # Step 2: Approve the order and get the status (record why if not approved)
    with allure.step(f"Step 2: Approve delegated order {order_reference_number}"):
        delegated_order_status, page_messages = my_delegated_orders.approve_delegated_order_with_result()
        my_delegated_orders.get_full_page_screenshot('delegated_order_approved')
        allure.attach(
            f"Order reference number: {order_reference_number}\nOrder status: {delegated_order_status}\n"
            f"Page message: {'; '.join(page_messages) if page_messages else '-'}",
            name="Order status after delegated approval",
            attachment_type=allure.attachment_type.TEXT
        )
        assert "approved" in delegated_order_status.lower(), \
            f"Delegated order {order_reference_number} is not approved. Order status: '{delegated_order_status}'. " \
            f"Reason (page message): {'; '.join(page_messages) if page_messages else 'no message shown'}"

    # Step 3: Log out from the Digital Marketplace
    with allure.step("Step 3: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        my_delegated_orders.get_full_page_screenshot('delegated_approver_logout')


@allure.suite("Administration")
@allure.feature("Customers")
@allure.story("Vendor Information")
@allure.title("Test_case_19: Retrieve order vendor credentials")
@allure.description("Test case 19: Retrieve vendor credentials for a specific marketplace order.")
@pytest.mark.order(19)
def test_19_retrieve_order_vendor_credentials(page):
    """
    Test case 19: Retrieve the order vendor credentials.

    Steps:
        1. Log in to the Digital Marketplace as the admin ('dm_admin').
        2. All Orders (admin): search the order reference number and open the order details.
        3. Admin dashboard > Customers: search the order vendor ('order_vendor') and store the vendor
           login ID in 'vendor_login_id'.
        4. Log out from Administration.
    """
    global vendor_login_id
    assert order_reference_number, "Test case 12 must pass first: no order reference number available"
    assert order_vendor, "Test case 9 must pass first: no order vendor available"
    assert dm_admin, "Missing in .env: test_order_admin"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    all_orders = AllOrderForAdminPage(page)
    customers_page = Customers(page)

    # Step 1: Log in as the admin
    with allure.step(f"Step 1: Log in to the Digital Marketplace as admin {dm_admin}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=dm_admin, pass_word=marketplace_password)
        home_page.get_full_page_screenshot('admin_login')

    # Step 2: All Orders (admin) and order details
    with allure.step(f"Step 2: Search order {order_reference_number} in All Orders and open order details"):
        home_page.goto_all_orders_for_admin()
        all_orders.admin_order_search(search_number=order_reference_number)
        all_orders.get_full_page_screenshot('admin_order_search')
        all_orders.admin_goes_to_order_details()
        all_orders.get_full_page_screenshot('admin_order_details')

    # Step 3: Customers > vendor login ID
    with allure.step(f"Step 3: Get vendor login ID of {order_vendor}"):
        all_orders.goto_admin_dashboard()
        customers_page.view_customers_list()
        customers_page.search_vendor(customer_name=order_vendor)
        customers_page.wait_for_timeout(5000)
        vendor_login_id = customers_page.search_customers()
        assert vendor_login_id, f"Vendor login ID not found for {order_vendor}"
        print("VENDOR LOGIN ID:", vendor_login_id)
        allure.attach(
            f"Order vendor: {order_vendor}\nVendor login ID: {vendor_login_id}",
            name="Order vendor login ID",
            attachment_type=allure.attachment_type.TEXT
        )
        customers_page.get_full_page_screenshot('vendor_login_id')

    # Step 4: Log out from Administration
    with allure.step("Step 4: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        home_page.get_full_page_screenshot('admin_logout')


@allure.suite("Vendor Dashboard")
@allure.feature("Order Details")
@allure.story("Order Acknowledgement")
@allure.title("Test_case_20: Acknowledge marketplace order")
@allure.description("Test case 20: Marketplace vendor acknowledgement process.")
@pytest.mark.order(20)
def test_20_acknowledge_marketplace_order(page):
    """
    Test case 20: Vendor acknowledges the marketplace order.

    Steps:
        1. Log in as the vendor ('vendor_login_id') and view the vendor dashboard.
        2. Open the order ('order_reference_number') from the dashboard.
        3. Acknowledge > Yes; store the framework order number ('framework_order_no') and the
           acknowledged order status ('vendor_acknowledged_order_status').
        4. Go back to the order list.
        No logout: Test case 21 searches the order in the same session.
    """
    global framework_order_no, vendor_acknowledged_order_status
    assert vendor_login_id, "Test case 19 must pass first: no vendor login ID available"
    assert stg_vendor_pass, "Missing in .env: test_stg_vendor_pass"

    login_page = LoginPage(page)
    vendor_dashboard = VendorDashboard(page)
    order_details_administration = OrderDetailsAdministration(page)

    # Step 1: Log in as the vendor
    with allure.step(f"Step 1: Log in as vendor {vendor_login_id}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_vendor_login(user_name=vendor_login_id, pass_word=stg_vendor_pass)
        vendor_dashboard.print_card_title()
        vendor_dashboard.print_table_data()
        vendor_dashboard.get_full_page_screenshot('vendor_dashboard')

    # Step 2: Open the order from the dashboard
    with allure.step(f"Step 2: Open order {order_reference_number}"):
        assert vendor_dashboard.click_action_for_order(order_reference=order_reference_number), \
            f"Order {order_reference_number} not found in the vendor dashboard"
        vendor_dashboard.wait_for_timeout(5000)
        vendor_dashboard.get_full_page_screenshot('vendor_order_details')

    # Step 3: Acknowledge and get the framework order number and order status
    with allure.step(f"Step 3: Acknowledge order {order_reference_number}"):
        framework_order_no, vendor_acknowledged_order_status = \
            order_details_administration.acknowledge_order_with_status()
        assert framework_order_no, "Framework order number not displayed after acknowledgement"
        print("FRAMEWORK ORDER NO:", framework_order_no)
        print("ACKNOWLEDGED ORDER STATUS:", vendor_acknowledged_order_status)
        allure.attach(
            f"Order reference number: {order_reference_number}\nFramework order number: {framework_order_no}\n"
            f"Order status after acknowledgement: {vendor_acknowledged_order_status}",
            name="Vendor acknowledgement",
            attachment_type=allure.attachment_type.TEXT
        )
        order_details_administration.get_full_page_screenshot('vendor_order_acknowledged')

    # Step 4: Back to the order list
    with allure.step("Step 4: Go back to the order list"):
        order_details_administration.click_back_to_order_list()
        order_details_administration.get_full_page_screenshot('vendor_order_list')


@allure.suite("Vendor Side")
@allure.feature("Order Management")
@allure.story("Order Search")
@allure.title("Test_case_21: Verify acknowledged order in orders list")
@allure.description("Test case 21: Vendor acknowledged order search process.")
@pytest.mark.order(21)
def test_21_verify_acknowledged_order_in_order_list(page):
    """
    Test case 21: Verify the acknowledged order in the vendor orders list (same as sanity.py test 17).
    Continues in the vendor session of Test case 20.

    Steps:
        1. Open the Search panel if it is closed.
        2. Start date and End date = today, click Search.
        3. Enter the framework order number ('framework_order_no'), select it from the dropdown,
           click Search again and verify the order is in the list.
        4. Log out from Administration.
    """
    assert framework_order_no, "Test case 20 must pass first: no framework order number available"

    orders_list_management = OrdersListManagement(page)
    current_date = datetime.today().strftime("%m-%d-%Y")

    # Step 1: Search panel
    with allure.step("Step 1: Open the Search panel if it is closed"):
        orders_list_management.open_search_panel_if_closed()
        orders_list_management.get_full_page_screenshot('vendor_orders_search_panel')

    # Step 2: Date range = today
    with allure.step(f"Step 2: Search orders for today ({current_date})"):
        orders_list_management.fill_date_range(start_date=current_date, end_date=current_date)
        orders_list_management.click_on_btn(orders_list_management.order_search_button)
        orders_list_management.wait_for_timeout(3000)
        orders_list_management.get_full_page_screenshot('vendor_orders_today')

    # Step 3: Framework order number from the dropdown, Search again, verify
    with allure.step(f"Step 3: Search framework order {framework_order_no}"):
        orders_list_management.search_order_from_dropdown(order_no=framework_order_no)
        orders_list_management.verify_order_in_list(order_no=framework_order_no)
        allure.attach(
            f"Framework order {framework_order_no} ({order_reference_number}) found in the vendor orders list",
            name="Acknowledged order found",
            attachment_type=allure.attachment_type.TEXT
        )
        orders_list_management.get_full_page_screenshot('vendor_acknowledged_order_search')

    # Step 4: Log out from Administration
    with allure.step("Step 4: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        orders_list_management.get_full_page_screenshot('vendor_logout')


@allure.suite("Purchase Order")
@allure.feature("Framework Order")
@allure.story("Framework Order List")
@allure.title("Test_case_22: View marketplace framework order details")
@allure.description("Test case 22: View marketplace framework order details in the procurement system.")
@pytest.mark.order(22)
def test_22_view_marketplace_framework_order_details(page, new_tab):
    """
    Test case 22: View the marketplace framework order in procurement.

    Steps:
        1. Log in to ERP as the procurement admin ('proc_admin') and go to Procurement.
        2. Go to Framework Order List and search the framework order ('framework_order_no').
        3. Open the framework order details in a new tab, then close the tab.
        4. Exit and log out from ERP.
    """
    assert framework_order_no, "Test case 20 must pass first: no framework order number available"
    assert proc_admin, "Missing in .env: test_proc_admin"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    framework_order_list_page = FrameworkOrderListPage(page)

    # Step 1: Log in as the procurement admin
    with allure.step(f"Step 1: Log in to ERP as procurement admin {proc_admin}"):
        erp_login(page, proc_admin)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('proc_admin_dashboard')

    # Step 2: Framework Order List and search the framework order
    with allure.step(f"Step 2: Search framework order {framework_order_no} in Framework Order List"):
        proc_home_page.navigate_to_framework_order_list()
        framework_order_list_page.search_framework_order(fa_order_no=framework_order_no)
        framework_order_list_page.get_full_page_screenshot('framework_order_search')

    # Step 3: Framework order details in a new tab
    with allure.step(f"Step 3: Open framework order {framework_order_no} details"):
        details_tab = new_tab(
            lambda p: framework_order_list_page.click_framework_order(framework_order_no=framework_order_no))
        details_tab.wait_for_timeout(5000)
        details_tab.screenshot(path=os.getcwd() + "/screenshots_taken/framework_order_details.png", full_page=True)
        allure.attach(
            f"Framework order number: {framework_order_no}\nOrder reference number: {order_reference_number}",
            name="Framework order",
            attachment_type=allure.attachment_type.TEXT
        )
        details_tab.close()
        page.bring_to_front()

    # Step 4: Exit and log out from ERP
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'proc_admin_logout')


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Receivable Order List")
@allure.title("Test_case_23: Receive item as designated receiver")
@allure.description("Test case 23: Marketplace item receipt process by the designated receiver.")
@pytest.mark.order(23)
def test_23_receive_item_as_designated_receiver(page):
    """
    Test case 23: The designated receiver receives the item.

    Steps:
        1. Log in to the Digital Marketplace as the designated receiver ('sso_login_receiver_pin')
           and go to Administration.
        2. Order Management > Receivable Order List: date range today, search the framework order and view it.
        3. Enter the challan number ('challan_num_for_receiver'), select all items, add attachment and
           receiving remarks ('receiving_remarks').
        4. Open the item receive popup and confirm.
        No logout: Test case 24 verifies the receipt in the same session.
    """
    assert framework_order_no, "Test case 20 must pass first: no framework order number available"
    required_env_values = {
        "test_sso_login_receiver_pin": sso_login_receiver_pin,
        "test_receiving_remarks": receiving_remarks,
        "test_requisition_attachment_file": requisition_attachment_file,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    check_receiving_remarks_length("test_receiving_remarks", receiving_remarks)

    global challan_num_for_receiver
    challan_num_for_receiver = generate_challan_number()
    login_page = LoginPage(page)
    home_page = HomePage(page)
    orders_list_management = OrdersListManagement(page)
    receivable_order_list = ReceivableOrderList(page)
    attachment_path = UTILS_DIR / requisition_attachment_file
    current_date = datetime.today().strftime("%m-%d-%Y")

    # Step 1: Log in as the designated receiver
    with allure.step(f"Step 1: Log in to the Digital Marketplace as designated receiver {sso_login_receiver_pin}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=sso_login_receiver_pin, pass_word=marketplace_password)
        home_page.goto_administration()
        home_page.wait_for_timeout(2000)
        home_page.get_full_page_screenshot('receiver_administration')

    # Step 2: Receivable Order List and view the framework order
    with allure.step(f"Step 2: Search framework order {framework_order_no} in Receivable Order List"):
        orders_list_management.click_order_management_menu()
        receivable_order_list.goto_receivable_order_list()
        receivable_order_list.open_search_panel_if_collapsed(receivable_order_list.order_input)
        receivable_order_list.fill_date_range(start_date=current_date, end_date=current_date)
        receivable_order_list.search_receivable_order(receivable_order_number=framework_order_no)
        receivable_order_list.get_full_page_screenshot('receiver_receivable_order_search')
        receivable_order_list.receivable_order_view()

    # Step 3: Challan number, items, attachment and remarks
    with allure.step(f"Step 3: Enter challan {challan_num_for_receiver}, select items, attachment and remarks"):
        receivable_order_list.challan_no_input(fill_challan_no=challan_num_for_receiver)
        print("RECEIVER CHALLAN NUMBER:", challan_num_for_receiver)
        receivable_order_list.all_item_select.click()
        assert receivable_order_list.receiving_upload_attachment(str(attachment_path)), "File upload failed"
        receivable_order_list.wait_for_timeout(5000)
        receivable_order_list.input_received_remarks(receiving_remarks=receiving_remarks)
        allure.attach(
            f"Framework order number: {framework_order_no}\nChallan number: {challan_num_for_receiver}\n"
            f"Attachment: {attachment_path.name}\nRemarks: {receiving_remarks}",
            name="Receiver challan number",
            attachment_type=allure.attachment_type.TEXT
        )
        receivable_order_list.get_full_page_screenshot('receiver_receive_items')

    # Step 4: Item receive popup and confirm
    with allure.step("Step 4: Open item receive popup and confirm"):
        receivable_order_list.open_item_receive_popup()
        receivable_order_list.get_full_page_screenshot('receiver_receive_popup')
        receivable_order_list.confirm_receivable_order()
        receivable_order_list.get_full_page_screenshot('receiver_items_received')


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Item Received List")
@allure.title("Test_case_24: Verify designated receiver item receipt")
@allure.description("Test case 24: Item received information verify by receiver.")
@pytest.mark.order(24)
def test_24_verify_designated_receiver_item_receipt(page):
    """
    Test case 24: Verify the designated receiver item receipt (same as sanity.py test 20).
    Continues in the session of Test case 23 (designated receiver).

    Steps:
        1. Item Received List: date range today, search the framework order and the challan number.
        2. Verify the received order is in the list and view it.
        3. Log out from Administration.
    """
    assert framework_order_no, "Test case 20 must pass first: no framework order number available"

    item_received_list = ItemReceivedList(page)
    current_date = datetime.today().strftime("%m-%d-%Y")

    # Step 1: Search the received order with the challan number
    with allure.step(f"Step 1: Search received order {framework_order_no} with challan {challan_num_for_receiver}"):
        item_received_list.open_search_panel_if_collapsed(item_received_list.order_number_input)
        item_received_list.fill_date_range(start_date=current_date, end_date=current_date)
        item_received_list.fill_received_order_number(order_no=framework_order_no)
        item_received_list.searched_received_order(challan_no=challan_num_for_receiver)
        item_received_list.search_button_for_received_item.click()
        item_received_list.wait_for_timeout(3000)
        item_received_list.get_full_page_screenshot('receiver_item_received_search')

    # Step 2: Verify the received order and view it
    with allure.step(f"Step 2: Verify received order {framework_order_no} and view it"):
        item_received_list.verify_order_in_list(order_no=framework_order_no)
        allure.attach(
            f"Framework order {framework_order_no} with challan {challan_num_for_receiver} "
            f"found in Item Received List",
            name="Received order found",
            attachment_type=allure.attachment_type.TEXT
        )
        item_received_list.order_view_button.first.click()
        item_received_list.wait_for_timeout(5000)
        item_received_list.get_full_page_screenshot('receiver_item_received_details')

    # Step 3: Log out from Administration
    with allure.step("Step 3: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        item_received_list.get_full_page_screenshot('receiver_logout')


def receive_order_items(page, challan_no, attachment_path, remarks, screenshot_prefix, partial_quantity=None):
    """
    Receivable Order List: search the framework order (date range today), view it, enter the challan,
    select all items, (optionally) change the first item's quantity, attachment, remarks and confirm.
    """
    orders_list_management = OrdersListManagement(page)
    receivable_order_list = ReceivableOrderList(page)
    current_date = datetime.today().strftime("%m-%d-%Y")

    with allure.step(f"Search framework order {framework_order_no} in Receivable Order List"):
        orders_list_management.open_order_management_menu_if_collapsed(
            receivable_order_list.receivable_order_list_submenu)
        receivable_order_list.goto_receivable_order_list()
        receivable_order_list.open_search_panel_if_collapsed(receivable_order_list.order_input)
        receivable_order_list.fill_date_range(start_date=current_date, end_date=current_date)
        receivable_order_list.search_receivable_order(receivable_order_number=framework_order_no)
        receivable_order_list.get_full_page_screenshot(f'{screenshot_prefix}_receivable_order_search')
        receivable_order_list.receivable_order_view()

    with allure.step(f"Enter challan {challan_no} and select all items"):
        receivable_order_list.challan_no_input(fill_challan_no=challan_no)
        print("ORDER INITIATOR CHALLAN NUMBER:", challan_no)
        receivable_order_list.all_item_select.click()
        receivable_order_list.wait_for_timeout(3000)
        if partial_quantity:
            receivable_order_list.input_first_item_quantity_to_receive(received_quantity=partial_quantity)
            print(f"First item Quantity to Receive: {partial_quantity}")
        receivable_order_list.get_full_page_screenshot(f'{screenshot_prefix}_items_selected')

    with allure.step(f"Add attachment {attachment_path.name} and remarks '{remarks}'"):
        assert receivable_order_list.receiving_upload_attachment(str(attachment_path)), "File upload failed"
        receivable_order_list.wait_for_timeout(3000)
        receivable_order_list.input_received_remarks(receiving_remarks=remarks)
        allure.attach(
            f"Framework order number: {framework_order_no}\nChallan number: {challan_no}\n"
            f"First item quantity: {partial_quantity or 'remaining quantity'}\n"
            f"Attachment: {attachment_path.name}\nRemarks: {remarks}",
            name="Item receive information",
            attachment_type=allure.attachment_type.TEXT
        )
        receivable_order_list.get_full_page_screenshot(f'{screenshot_prefix}_receive_items')

    with allure.step("Open item receive popup and confirm"):
        receivable_order_list.open_item_receive_popup()
        receivable_order_list.get_full_page_screenshot(f'{screenshot_prefix}_receive_popup')
        receivable_order_list.confirm_receivable_order()
        receivable_order_list.get_full_page_screenshot(f'{screenshot_prefix}_items_received')


def verify_item_receipt(page, challan_no, screenshot_prefix):
    """
    Item Received List: date range today, search the framework order and challan, verify and view it.
    """
    orders_list_management = OrdersListManagement(page)
    item_received_list = ItemReceivedList(page)
    current_date = datetime.today().strftime("%m-%d-%Y")

    with allure.step(f"Search framework order {framework_order_no} with challan {challan_no} in Item Received List"):
        orders_list_management.open_order_management_menu_if_collapsed(item_received_list.item_received_list_submenu)
        item_received_list.goto_received_order_list()
        item_received_list.open_search_panel_if_collapsed(item_received_list.order_number_input)
        item_received_list.fill_date_range(start_date=current_date, end_date=current_date)
        item_received_list.fill_received_order_number(order_no=framework_order_no)
        item_received_list.searched_received_order(challan_no=challan_no)
        item_received_list.search_button_for_received_item.click()
        item_received_list.wait_for_timeout(3000)
        item_received_list.get_full_page_screenshot(f'{screenshot_prefix}_item_received_search')

    with allure.step(f"Verify challan {challan_no} in Item Received List and view it"):
        item_received_list.verify_challan_in_list(challan_no=challan_no)
        allure.attach(
            f"Framework order {framework_order_no} with challan {challan_no} found in Item Received List",
            name="Received challan found",
            attachment_type=allure.attachment_type.TEXT
        )
        item_received_list.order_view_button.first.click()
        item_received_list.wait_for_timeout(5000)
        item_received_list.get_full_page_screenshot(f'{screenshot_prefix}_item_received_details')


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Receivable Order List")
@allure.title("Test_case_25: Partially receive item as order initiator")
@allure.description("Test case 25: Partial item receipt by the order initiator acting as receiver.")
@pytest.mark.order(25)
def test_25_partially_receive_item_as_order_initiator(page):
    """
    Test case 25: The order initiator partially receives the items (same as sanity.py test 21).

    Steps:
        1. Log in to the Digital Marketplace as the order initiator ('proj_user') and go to Administration.
        2. Receivable Order List: Search panel, date range today, search the framework order and view it.
        3. Enter the challan number ('challan_num_for_order_initiator'), select all items and enter the
           first item's partial quantity ('partial_receive_quantity').
        4. Add attachment and partial receiving remarks (3-255 characters).
        5. Open the item receive popup and confirm.
        No logout: Test case 26 verifies the receipt in the same session.
    """
    global challan_num_for_order_initiator
    assert framework_order_no, "Test case 20 must pass first: no framework order number available"
    required_env_values = {
        "test_user_name": proj_user,
        "test_partial_receive_quantity": partial_receive_quantity,
        "test_partial_receiving_remarks": partial_receiving_remarks,
        "test_receiving_attachment_file_partial": receiving_attachment_file_partial,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    check_receiving_remarks_length("test_partial_receiving_remarks", partial_receiving_remarks)
    attachment_path = UTILS_DIR / receiving_attachment_file_partial
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"

    challan_num_for_order_initiator = generate_challan_number()
    login_page = LoginPage(page)
    home_page = HomePage(page)

    # Step 1: Log in as the order initiator
    with allure.step(f"Step 1: Log in to the Digital Marketplace as order initiator {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=proj_user, pass_word=marketplace_password)
        home_page.goto_administration()
        home_page.wait_for_timeout(2000)
        home_page.get_full_page_screenshot('order_initiator_administration')

    # Step 2-5: Partially receive the items
    with allure.step(f"Step 2: Partially receive framework order {framework_order_no} "
                     f"with challan {challan_num_for_order_initiator}"):
        receive_order_items(
            page,
            challan_no=challan_num_for_order_initiator,
            attachment_path=attachment_path,
            remarks=partial_receiving_remarks,
            screenshot_prefix='order_initiator_partial',
            partial_quantity=partial_receive_quantity
        )


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Item Received List")
@allure.title("Test_case_26: Verify partial item receipt")
@allure.description("Test case 26: Partial item received information verify by the order initiator.")
@pytest.mark.order(26)
def test_26_verify_partial_item_receipt(page):
    """
    Test case 26: Verify the partial item receipt (same as sanity.py test 22).

    Steps:
        1. Item Received List: Search panel, date range today, search the framework order and the
           challan number ('challan_num_for_order_initiator').
        2. Verify the challan is in the list and view it.
    """
    assert challan_num_for_order_initiator, "Test case 25 must pass first: no order initiator challan available"
    verify_item_receipt(page, challan_no=challan_num_for_order_initiator,
                        screenshot_prefix='order_initiator_partial')


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Receivable Order List")
@allure.title("Test_case_27: Receive remaining item as order initiator")
@allure.description("Test case 27: Remaining item receipt by the order initiator.")
@pytest.mark.order(27)
def test_27_receive_remaining_item_as_order_initiator(page):
    """
    Test case 27: The order initiator receives the remaining items (same as sanity.py test 23).

    Steps:
        1. Receivable Order List: Search panel, date range today, search the framework order and view it.
        2. Enter the second challan number ('challan_num_for_order_initiator_2') and select all items
           (remaining quantity).
        3. Add attachment and receiving remarks ('receiving_remarks', 3-255 characters).
        4. Open the item receive popup and confirm.
    """
    global challan_num_for_order_initiator_2
    assert challan_num_for_order_initiator, "Test case 25 must pass first: no order initiator challan available"
    required_env_values = {
        "test_receiving_remarks": receiving_remarks,
        "test_receiving_attachment_file_remaining": receiving_attachment_file_remaining,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    check_receiving_remarks_length("test_receiving_remarks", receiving_remarks)
    attachment_path = UTILS_DIR / receiving_attachment_file_remaining
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"

    challan_num_for_order_initiator_2 = generate_challan_number()

    # Step 1-4: Receive the remaining items
    with allure.step(f"Step 1: Receive remaining items of {framework_order_no} "
                     f"with challan {challan_num_for_order_initiator_2}"):
        receive_order_items(
            page,
            challan_no=challan_num_for_order_initiator_2,
            attachment_path=attachment_path,
            remarks=receiving_remarks,
            screenshot_prefix='order_initiator_remaining'
        )


@allure.suite("Administration")
@allure.feature("Order Management")
@allure.story("Item Received List")
@allure.title("Test_case_28: Verify final item receipt")
@allure.description("Test case 28: Final item received information verify by the order initiator.")
@pytest.mark.order(28)
def test_28_verify_final_item_receipt(page):
    """
    Test case 28: Verify the final item receipt (same as sanity.py test 24).

    Steps:
        1. Item Received List: Search panel, date range today, search the framework order and the
           challan number ('challan_num_for_order_initiator_2').
        2. Verify the challan is in the list and view it.
        3. Log out from Administration.
    """
    assert challan_num_for_order_initiator_2, "Test case 27 must pass first: no second challan available"
    verify_item_receipt(page, challan_no=challan_num_for_order_initiator_2,
                        screenshot_prefix='order_initiator_remaining')

    # Log out from Administration
    with allure.step("Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        HomePage(page).get_full_page_screenshot('order_initiator_receiving_logout')


@allure.suite("Item Receive")
@allure.feature("Item Receive List")
@allure.story("Item Receive Details Information")
@allure.title("Test_case_29: View marketplace item receipt details in ERP")
@allure.description("Test case 29: View marketplace item receive details in the procurement system.")
@pytest.mark.order(29)
def test_29_view_marketplace_item_receipt_details(page):
    """
    Test case 29: View marketplace item receive details in ERP (same as sanity.py test 25).

    Steps:
        1. Log in to ERP as the procurement admin ('proc_admin') and go to Procurement.
        2. Item Receive > Item Receive List and search the framework order.
        3. Open the item receive (MRR) details.
        4. Exit and log out from ERP.
    """
    assert framework_order_no, "Test case 20 must pass first: no framework order number available"
    assert proc_admin, "Missing in .env: test_proc_admin"

    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    proc_item_receive_list_page = ItemReceiveList(page)

    # Step 1: Log in as the procurement admin
    with allure.step(f"Step 1: Log in to ERP as procurement admin {proc_admin}"):
        erp_login(page, proc_admin)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('proc_admin_item_receive_dashboard')

    # Step 2: Item Receive List and search the framework order
    with allure.step(f"Step 2: Search framework order {framework_order_no} in Item Receive List"):
        proc_home_page.goto_item_receive_list()
        proc_home_page.get_full_page_screenshot('proc_item_receive_list')
        proc_item_receive_list_page.search_item_receive_order(receivable_item=framework_order_no)
        proc_item_receive_list_page.get_full_page_screenshot('proc_item_receive_search')

    # Step 3: Item receive (MRR) details
    with allure.step(f"Step 3: Open item receive details of {framework_order_no}"):
        proc_item_receive_list_page.item_receive_details_view()
        proc_item_receive_list_page.get_full_page_screenshot('proc_item_receive_details')
        allure.attach(
            f"Framework order number: {framework_order_no}\nChallans: {challan_num_for_receiver}, "
            f"{challan_num_for_order_initiator}, {challan_num_for_order_initiator_2}",
            name="Item receive details",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 4: Exit and log out from ERP
    with allure.step("Step 4: Exit and log out from ERP"):
        erp_logout(page, 'proc_admin_item_receive_logout')


def generate_bill_number():
    # DM_Bill + framework (work) order last 4 digits + random characters, e.g. DM_Bill4556xyZ7k
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    return f"DM_Bill{framework_order_no[-4:]}{random_part}"


def find_bill_approver(page, label, screenshot_name):
    # Vendor Billing List: search the bill and get the current approver ID from the status column
    vendor_billing_list_page = VendorBillingList(page)
    vendor_billing_list_page.search_bill(bill_num)
    approver = str(int(vendor_billing_list_page.find_approver_id(bill_num)))
    print(f"{label}: {approver}")
    allure.attach(f"Bill number: {bill_num}\n{label}: {approver}", name=label,
                  attachment_type=allure.attachment_type.TEXT)
    vendor_billing_list_page.get_full_page_screenshot(screenshot_name)
    return approver


def approve_bill_in_new_tab(page, new_tab, screenshot_prefix, attachment_path=None):
    # Open the bill details in a new tab, (first recommender: attachment and bill type), approve and close
    vendor_billing_list_page = VendorBillingList(page)
    bill_tab = new_tab(lambda p: vendor_billing_list_page.click_on_bill_num(bill_num))
    bill_details_information_page = BillDetailsInformation(bill_tab)
    bill_details_information_page.wait_for_timeout(5000)
    if attachment_path:
        bill_details_information_page.upload_document(str(attachment_path))
        bill_details_information_page.select_bill_type(bill_type)
        print(f"Bill attachment: {attachment_path.name}, bill type: {bill_type}")
    bill_details_information_page.get_full_page_screenshot(f'{screenshot_prefix}_bill_details')
    bill_details_information_page.approve_bill()
    bill_details_information_page.get_full_page_screenshot(f'{screenshot_prefix}_bill_approved')
    bill_tab.close()
    page.bring_to_front()


@allure.suite("Bill Payable")
@allure.feature("Create Vendor Bill Payable")
@allure.story("Framework Order Bill")
@allure.title("Test_case_30: Create and submit marketplace bill")
@allure.description("Test case 30: Bill creation and submission for the Marketplace item receive in ERP.")
@pytest.mark.order(30)
def test_30_create_and_submit_marketplace_bill(page):
    """
    Test case 30: Create and submit the marketplace bill (same as sanity.py test 26).

    Steps:
        1. Log in to ERP as the bill creator ('bill_creator') and go to Procurement.
        2. Bill Payable > Create Vendor Bill Payable (Framework Order).
        3. Search the vendor ('order_vendor'), select the framework order and the first challan found.
        4. Bill number (DM_Bill + work order last 4 digits + random characters), bill date and
           bill receive date (today).
        5. Select all items and the recommender ('bill_recommender').
        6. Submit and confirm.
        No logout: Test case 31 verifies the bill in the same session.
    """
    global bill_num, billed_challan
    assert framework_order_no, "Test case 20 must pass first: no framework order number available"
    assert order_vendor, "Test case 9 must pass first: no order vendor available"
    required_env_values = {
        "test_bill_creator": bill_creator,
        "test_bill_recommender": bill_recommender,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    bill_num = generate_bill_number()
    proc_dashboard_page = DashboardPage(page)
    proc_home_page = ProcurementHomePage(page)
    create_vendor_bill = CreateVendorBillPayable(page)

    # Step 1: Log in as the bill creator
    with allure.step(f"Step 1: Log in to ERP as bill creator {bill_creator}"):
        erp_login(page, bill_creator)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('bill_creator_dashboard')

    # Step 2: Create Vendor Bill Payable for a framework order
    with allure.step("Step 2: Go to Bill Payable > Create Vendor Bill Payable (Framework Order)"):
        proc_home_page.goto_bill_payable()
        create_vendor_bill.vendor_bill_payable_information_for_framework_order()
        create_vendor_bill.get_full_page_screenshot('create_vendor_bill')

    # Step 3: Vendor, framework order and the first challan found
    with allure.step(f"Step 3: Select vendor {order_vendor}, order {framework_order_no} and a challan"):
        create_vendor_bill.search_vendor(vendor_name=order_vendor)
        create_vendor_bill.select_order_no(order_num=framework_order_no)
        billed_challan = create_vendor_bill.select_first_challan_found(
            challan_prefix=f"DM_{framework_order_no[-4:]}")
        create_vendor_bill.get_full_page_screenshot('bill_vendor_order_challan')

    # Step 4: Bill number, bill date and bill receive date
    with allure.step(f"Step 4: Enter bill number {bill_num}, bill date and bill receive date"):
        create_vendor_bill.bill_number(bill_no_1=bill_num)
        print("BILL NUMBER:", bill_num)
        create_vendor_bill.bill_date_with_text(create_vendor_bill.select_date())
        create_vendor_bill.bill_receive_date_with_text(create_vendor_bill.select_date())

    # Step 5: Select all items and the recommender
    with allure.step(f"Step 5: Select all items and recommender {bill_recommender}"):
        create_vendor_bill.select_all_items()
        create_vendor_bill.Bill_recommender2_selecting(recommender=bill_recommender)
        allure.attach(
            f"Bill number: {bill_num}\nVendor: {order_vendor}\nFramework order: {framework_order_no}\n"
            f"Challan: {billed_challan}\nRecommender: {bill_recommender}",
            name="Bill information",
            attachment_type=allure.attachment_type.TEXT
        )
        create_vendor_bill.get_full_page_screenshot('bill_information')

    # Step 6: Submit and confirm
    with allure.step("Step 6: Submit the bill and confirm"):
        create_vendor_bill.submit_bill()
        create_vendor_bill.get_full_page_screenshot('bill_submit_confirmation')
        create_vendor_bill.confirm_submission()
        create_vendor_bill.get_full_page_screenshot('bill_submitted')


@allure.suite("Bill Payable")
@allure.feature("Vendor Billing List")
@allure.story("Bill Details Information")
@allure.title("Test_case_31: Verify submitted bill and find first recommender")
@allure.description("Test case 31: Verify the submitted bill and find the first recommender.")
@pytest.mark.order(31)
def test_31_verify_submitted_bill_and_recommender(page):
    """
    Test case 31: Verify the submitted bill and find the first recommender (same as sanity.py test 27).

    Steps:
        1. Bill Payable > Vendor Billing List.
        2. Search the bill and get the first recommender ('bill_recommender_1').
    """
    global bill_recommender_1
    assert bill_num, "Test case 30 must pass first: no bill number available"
    vendor_billing_list_page = VendorBillingList(page)

    # Step 1: Vendor Billing List
    with allure.step("Step 1: Go to Bill Payable > Vendor Billing List"):
        vendor_billing_list_page.go_to_billing_list()
        vendor_billing_list_page.get_full_page_screenshot('vendor_billing_list')

    # Step 2: Search the bill and get the first recommender
    with allure.step(f"Step 2: Search bill {bill_num} and get the first recommender"):
        bill_recommender_1 = find_bill_approver(page, "Bill recommender 1", 'bill_recommender_1')


@allure.suite("Bill Payable")
@allure.feature("Vendor Billing List")
@allure.story("Bill Details Information")
@allure.title("Test_case_32: Approve bill as first recommender")
@allure.description("Test case 32: Approve the bill as the first recommender.")
@pytest.mark.order(32)
def test_32_approve_bill_as_first_recommender(page, new_tab):
    """
    Test case 32: The first recommender approves the bill (same as sanity.py test 28).
    Continues in the session of Test case 31.

    Steps:
        1. Open the bill details in a new tab.
        2. Upload the attachment ('bill_attachment_file') and select the bill type ('bill_type').
        3. Approve the bill and close the tab.
    """
    assert bill_recommender_1, "Test case 31 must pass first: no first recommender available"
    required_env_values = {
        "test_bill_type": bill_type,
        "test_bill_attachment_file": bill_attachment_file,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    attachment_path = UTILS_DIR / bill_attachment_file
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"

    # Step 1-3: Bill details, attachment, bill type and approve
    with allure.step(f"Step 1: Approve bill {bill_num} with attachment {attachment_path.name} "
                     f"and bill type {bill_type}"):
        approve_bill_in_new_tab(page, new_tab, 'bill_recommender_1', attachment_path=attachment_path)


@allure.suite("Bill Payable")
@allure.feature("Vendor Billing List")
@allure.story("Bill Details Information")
@allure.title("Test_case_33: Identify second bill recommender")
@allure.description("Test case 33: Identify the second bill recommender.")
@pytest.mark.order(33)
def test_33_identify_second_bill_recommender(page):
    """
    Test case 33: Identify the second bill recommender (same as sanity.py test 29).

    Steps:
        1. Search the bill and get the second recommender ('bill_recommender_2').
        2. Exit and log out from ERP.
    """
    global bill_recommender_2
    assert bill_num, "Test case 30 must pass first: no bill number available"

    # Step 1: Search the bill and get the second recommender
    with allure.step(f"Step 1: Search bill {bill_num} and get the second recommender"):
        page.reload()
        bill_recommender_2 = find_bill_approver(page, "Bill recommender 2", 'bill_recommender_2')

    # Step 2: Exit and log out
    with allure.step("Step 2: Exit and log out from ERP"):
        erp_logout(page, 'bill_creator_logout')


@allure.suite("Bill Payable")
@allure.feature("Vendor Billing List")
@allure.story("Bill Details Information")
@allure.title("Test_case_34: Approve bill as second recommender")
@allure.description("Test case 34: Approve the bill as the second recommender.")
@pytest.mark.order(34)
def test_34_approve_bill_as_second_recommender(page, new_tab):
    """
    Test case 34: The second recommender approves the bill (same as sanity.py test 30).

    Steps:
        1. Log in to ERP as the second recommender ('bill_recommender_2') and go to Procurement.
        2. Bill Payable > Vendor Billing List and search the bill.
        3. Open the bill details in a new tab, approve and close the tab.
    """
    assert bill_recommender_2, "Test case 33 must pass first: no second recommender available"
    proc_dashboard_page = DashboardPage(page)
    vendor_billing_list_page = VendorBillingList(page)

    # Step 1: Log in as the second recommender
    with allure.step(f"Step 1: Log in to ERP as second recommender {bill_recommender_2}"):
        erp_login(page, bill_recommender_2)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('bill_recommender_2_dashboard')

    # Step 2: Vendor Billing List and search the bill
    with allure.step(f"Step 2: Search bill {bill_num} in Vendor Billing List"):
        vendor_billing_list_page.go_to_billing_list()
        vendor_billing_list_page.search_bill(bill_num)
        vendor_billing_list_page.get_full_page_screenshot('bill_recommender_2_search')

    # Step 3: Approve the bill
    with allure.step(f"Step 3: Approve bill {bill_num} as second recommender"):
        approve_bill_in_new_tab(page, new_tab, 'bill_recommender_2')


@allure.suite("Bill Payable")
@allure.feature("Vendor Billing List")
@allure.story("Bill Details Information")
@allure.title("Test_case_35: Identify final bill approver")
@allure.description("Test case 35: Identify the final bill approver.")
@pytest.mark.order(35)
def test_35_identify_final_bill_approver(page):
    """
    Test case 35: Identify the final bill approver (same as sanity.py test 31).

    Steps:
        1. Reload, search the bill and get the final approver ('bill_recommender_3').
        2. Exit and log out from ERP.
    """
    global bill_recommender_3
    assert bill_num, "Test case 30 must pass first: no bill number available"

    # Step 1: Search the bill and get the final approver
    with allure.step(f"Step 1: Search bill {bill_num} and get the final approver"):
        page.reload()
        bill_recommender_3 = find_bill_approver(page, "Bill final approver", 'bill_final_approver')

    # Step 2: Exit and log out
    with allure.step("Step 2: Exit and log out from ERP"):
        erp_logout(page, 'bill_recommender_2_logout')


@allure.suite("Bill Payable")
@allure.feature("Vendor Billing List")
@allure.story("Bill Details Information")
@allure.title("Test_case_36: Approve bill as final approver")
@allure.description("Test case 36: Approve the bill as the final approver.")
@pytest.mark.order(36)
def test_36_approve_bill_as_final_approver(page, new_tab):
    """
    Test case 36: The final approver approves the bill (same as sanity.py test 32).

    Steps:
        1. Log in to ERP as the final approver ('bill_recommender_3') and go to Procurement.
        2. Bill Payable > Vendor Billing List and search the bill.
        3. Open the bill details in a new tab, approve and close the tab.
    """
    assert bill_recommender_3, "Test case 35 must pass first: no final approver available"
    proc_dashboard_page = DashboardPage(page)
    vendor_billing_list_page = VendorBillingList(page)

    # Step 1: Log in as the final approver
    with allure.step(f"Step 1: Log in to ERP as final approver {bill_recommender_3}"):
        erp_login(page, bill_recommender_3)
        proc_dashboard_page.goto_procurement()
        proc_dashboard_page.get_full_page_screenshot('bill_final_approver_dashboard')

    # Step 2: Vendor Billing List and search the bill
    with allure.step(f"Step 2: Search bill {bill_num} in Vendor Billing List"):
        vendor_billing_list_page.go_to_billing_list()
        vendor_billing_list_page.search_bill(bill_num)
        vendor_billing_list_page.get_full_page_screenshot('bill_final_approver_search')

    # Step 3: Approve the bill
    with allure.step(f"Step 3: Approve bill {bill_num} as final approver"):
        approve_bill_in_new_tab(page, new_tab, 'bill_final_approver')


@allure.suite("Bill Payable")
@allure.feature("Vendor Billing List")
@allure.story("Bill Status")
@allure.title("Test_case_37: Find bill status after final approval")
@allure.description("Test case 37: Find the final bill status after the final approval.")
@pytest.mark.order(37)
def test_37_find_bill_status_after_final_approval(page):
    """
    Test case 37: Find the final bill status (same as sanity.py test 33).

    Steps:
        1. Reload, search the bill and get the final bill status.
        2. Exit and log out from ERP.
    """
    global final_bill_status
    assert bill_num, "Test case 30 must pass first: no bill number available"
    vendor_billing_list_page = VendorBillingList(page)

    # Step 1: Search the bill and get the final status
    with allure.step(f"Step 1: Search bill {bill_num} and get the final bill status"):
        page.reload()
        vendor_billing_list_page.wait_for_timeout(5000)
        vendor_billing_list_page.search_bill(bill_num)
        final_bill_status = vendor_billing_list_page.find_bill_status(bill_num).strip()
        print("FINAL BILL STATUS:", final_bill_status)
        allure.attach(
            f"Bill number: {bill_num}\nChallan: {billed_challan}\nFinal bill status: {final_bill_status}",
            name="Final bill status",
            attachment_type=allure.attachment_type.TEXT
        )
        vendor_billing_list_page.get_full_page_screenshot('bill_final_status')

    # Step 2: Exit and log out
    with allure.step("Step 2: Exit and log out from ERP"):
        erp_logout(page, 'bill_final_approver_logout')
