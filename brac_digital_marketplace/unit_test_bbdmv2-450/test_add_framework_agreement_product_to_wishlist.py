from dotenv import load_dotenv
import os
import re
import random
from decimal import Decimal, InvalidOperation
import pytest
import allure

load_dotenv()

from playwright.sync_api import expect

from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.public_side.public_side_framework_agreement_list import \
    PublicSideFrameAgreementListPage
from pages.digital_marketplace.public_side.wishlist_page import WishlistPage

# Procurement information
proj_user = os.getenv("test_user_name")

# Marketplace information
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")

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

# Marketplace global variable
initial_wishlist_count = 0
agreement_vendor_name = ''
framework_products = []
selected_product = {}
wishlist_quantity = ''
wishlist_message = {}
product_already_in_wishlist = False
updated_wishlist_count = 0
existing_wishlist_quantity = ''
updated_wishlist_quantity = ''


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
@allure.story("Add Framework Agreement Product(s) to Wishlist")
@allure.title("Add Framework Agreement Product(s) to Wishlist")
@allure.description("Verify that the user can add product(s) from an Active Framework Agreement to the Wishlist "
                    "and validate the product information, quantity, and Wishlist count.")
@pytest.mark.order(1)
def test_add_framework_agreement_product_to_wishlist(page):
    """
    Add Framework Agreement Product(s) to Wishlist.

    Steps:
        1. Log in to the Digital Marketplace as 'proj_user' (00006008) using SSO,
           retrieve the initial Wishlist count, and store it in 'initial_wishlist_count'.
        2. Navigate to All Framework Agreements.
        3. Search for the specified Active Framework Agreement (BPD/2026/FA-5).
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

    All scenario values are read from .env.
    """
    global initial_wishlist_count, agreement_vendor_name, framework_products, selected_product, \
        wishlist_quantity, wishlist_message, product_already_in_wishlist, updated_wishlist_count, \
        existing_wishlist_quantity, updated_wishlist_quantity

    # All scenario values must come from .env
    required_env_values = {
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
        assert active_framework_agreement, "test_active_framework_agreement is not set in .env"
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

    # Step 7: Store the first two products (or the first one) and open the first product's details
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
