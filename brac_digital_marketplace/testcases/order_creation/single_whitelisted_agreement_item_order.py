from dotenv import load_dotenv
import os
from pathlib import Path

import pytest
import allure

load_dotenv()

# Digital Marketplace (staging)
proj_user = os.getenv("test_user_name")
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
# Shopping cart, delivery schedule and order (same values as marketplace_staging_sanity.py)
requisition_attachment_file = os.getenv("test_requisition_attachment_file")
requisition_item_remarks = os.getenv("test_requisition_item_remarks")
order_initiator = os.getenv("test_order_initiator")
order_remarks = os.getenv("test_order_remarks")
# Project root is 3 levels up: testcases/order_creation/<this file>
UTILS_DIR = Path(__file__).resolve().parents[3] / "utils"
# Shopping cart item remarks: 0 to 500 characters, all special characters allowed
MAX_CART_ITEM_REMARKS_LENGTH = 500

from utils.test_data_store import load_result, save_result
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.public_side.shopping_cart import ShoppingCart
from pages.digital_marketplace.public_side.checkout_page import CheckoutPage

# Requisition of single_whitelisted_agreement_item_requisition.py (single_whitelisted_requisition_result.json)
requisition = {}
req_num = ''
order_vendor = ''
# Shopping cart (Test case 1): quantity is not changed, so cart total = requisition total and Auto Generate works
cart_quantity = ''
cart_item_remarks = ''
cart_attachment_name = ''
cart_checked_out = False
# Delivery schedule (Test case 2)
delivery_schedule = ''
# Marketplace order (Test case 3)
order_reference_number = ''
order_status = ''
# Order result for the pending approval test file
order_result = {}


@allure.suite("Public Side")
@allure.feature("Shopping Cart")
@allure.story("Cart Preparation")
@allure.title("Test_case_1: Prepare cart for checkout with the whitelisted item requisition")
@allure.description("Test case 1: Marketplace order initiation process by preparing the shopping cart with the "
                    "whitelisted item requisition (attachment and remarks updated, quantity unchanged).")
@pytest.mark.order(1)
def test_1_prepare_cart_for_checkout(page):
    """
    Test case 1: Prepare the shopping cart for checkout (same as marketplace_staging_sanity.py Test case 10).

    Steps:
        1. Load the requisition of single_whitelisted_agreement_item_requisition.py
           (single_whitelisted_requisition_result.json) and store it in 'requisition'.
        2. Log in to the Digital Marketplace as the order initiator ('proj_user').
        3. Go to the shopping cart and select the vendor of the requisition ('req_num').
        4. Upload attachment for the item.
        5. Update the item remarks (0 to 500 characters, all special characters allowed) and the shopping cart.
           The quantity is not changed: Auto Generate works only when the requisition total quantity
           equals the shopping cart total quantity.
        6. Accept terms of service and checkout.

    All scenario values are read from .env.
    """
    global requisition, req_num, order_vendor, cart_quantity, cart_item_remarks, cart_attachment_name, \
        cart_checked_out

    # All scenario values must come from .env
    required_env_values = {
        "test_user_name": proj_user,
        "test_marketplace_url_qa": marketplace_url_qa,
        "test_marketplace_password": marketplace_password,
        "test_requisition_attachment_file": requisition_attachment_file,
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    # Item remarks are optional: 0 to 500 characters
    cart_item_remarks = requisition_item_remarks or ''
    assert len(cart_item_remarks) <= MAX_CART_ITEM_REMARKS_LENGTH, \
        f"test_requisition_item_remarks must be max {MAX_CART_ITEM_REMARKS_LENGTH} characters, " \
        f"found {len(cart_item_remarks)}"

    attachment_path = UTILS_DIR / requisition_attachment_file
    assert attachment_path.is_file(), f"Attachment not found in utils: {attachment_path}"

    login_page = LoginPage(page)
    home_page = HomePage(page)
    cart_page = ShoppingCart(page)

    # Step 1: Requisition from single_whitelisted_agreement_item_requisition.py
    with allure.step("Step 1: Load the requisition result of single_whitelisted_agreement_item_requisition.py"):
        requisition = load_result("single_whitelisted_requisition_result",
                                  created_by="single_whitelisted_agreement_item_requisition.py")
        req_num = requisition["requisition_number"]
        order_vendor = requisition["vendor"]
        cart_quantity = requisition["item"]["quantity"]
        print("REQ NUM:", req_num)
        print("ORDER VENDOR:", order_vendor)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in requisition.items()),
            name="Requisition result",
            attachment_type=allure.attachment_type.TEXT
        )

    # Step 2: Log in to the Digital Marketplace
    with allure.step(f"Step 2: Log in to the Digital Marketplace as {proj_user}"):
        login_page.navigate_to_url(marketplace_url_qa)
        login_page.perform_login_for_sso_login(user_name=proj_user, pass_word=marketplace_password)
        print(f"Logging in to the Digital Marketplace as: {proj_user}")
        home_page.verify_welcome_message()
        home_page.get_full_page_screenshot('cart_marketplace_login')

    # Step 3: Shopping cart and vendor selection
    with allure.step(f"Step 3: Select vendor {order_vendor} for requisition {req_num}"):
        home_page.goto_shopping_cart()
        assert cart_page.wait_for_requisition_in_cart(requisition_number=req_num), \
            f"Requisition {req_num} is not synced to the shopping cart"
        cart_page.select_vendor_for_requisition_found(requisition_number=req_num)
        assert cart_page.select_vendor_by_name(vendor_name=order_vendor, requisition_number=req_num), \
            f"Vendor {order_vendor} not found in the shopping cart"
        cart_page.get_full_page_screenshot('cart_vendor_selected')

    # Step 4: Item attachment
    with allure.step(f"Step 4: Upload attachment {attachment_path.name} for the item"):
        assert cart_page.upload_attachment(str(attachment_path)), "File upload failed"
        cart_attachment_name = attachment_path.name
        print("CART ATTACHMENT:", cart_attachment_name)
        cart_page.get_full_page_screenshot('cart_attachment')

    # Step 5: Item remarks and update shopping cart (quantity unchanged)
    with allure.step(f"Step 5: Update the item remarks ({len(cart_item_remarks)} characters) and the shopping cart"):
        cart_page.update_cart_item_remarks(requisition_number=req_num, remarks_text=cart_item_remarks)
        cart_page.update_shopping_cart_info()
        print("CART QUANTITY:", cart_quantity)
        print("CART ITEM REMARKS:", cart_item_remarks)
        allure.attach(
            f"Requisition number: {req_num}\nItem: {requisition['item']['item_code']}\n"
            f"Requisition quantity = cart quantity (not changed): {cart_quantity}\n"
            f"Item remarks ({len(cart_item_remarks)} characters): {cart_item_remarks}",
            name="Shopping cart item",
            attachment_type=allure.attachment_type.TEXT
        )
        cart_page.get_full_page_screenshot('cart_updated')

    # Step 6: Accept terms of service and checkout
    with allure.step("Step 6: Accept terms of service and checkout"):
        cart_page.cart_page_checkout()
        cart_checked_out = True
        print(f"Shopping cart of requisition {req_num} checked out")
        cart_page.get_full_page_screenshot('cart_checkout')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Delivery Schedule Preparation Window")
@allure.title("Test_case_2: Prepare delivery schedule")
@allure.description("Test case 2: Preparing order delivery schedule for the whitelisted item (Auto Generate, "
                    "receiving person is the order initiator).")
@pytest.mark.order(2)
def test_2_prepare_delivery_schedule(page):
    """
    Test case 2: Prepare the order delivery schedule (single item).

    Steps:
        1. Click Auto Generate: the item gets its delivery schedule.
        2. Receiving Person 'order_initiator' in the auto generated schedule row.
        3. Wait until Continue is enabled and click Continue.

    All scenario values are read from .env.
    """
    global delivery_schedule
    assert cart_checked_out, "Test case 1 must pass first: the cart is not checked out"
    assert order_initiator, "Missing in .env: test_order_initiator"

    checkout_page = CheckoutPage(page)

    # Step 1: Auto Generate delivery schedule
    with allure.step("Step 1: Click Auto Generate"):
        checkout_page.auto_generate_schedule()
        checkout_page.get_full_page_screenshot('schedule_auto_generate')

    # Step 2: Receiving person in the auto generated schedule row
    with allure.step(f"Step 2: Receiving Person {order_initiator}"):
        checkout_page.fill_generated_schedule_receiving_person(pin=order_initiator)
        checkout_page.get_full_page_screenshot('schedule_receiving_person')

    # Step 3: Continue (enabled after all delivery schedule information is complete)
    with allure.step("Step 3: Wait until Continue is enabled and click Continue"):
        delivery_schedule = (f"Item {requisition['item']['item_code']}: auto generated schedule, "
                             f"receiving person {order_initiator}")
        print("DELIVERY SCHEDULE:", delivery_schedule)
        allure.attach(
            delivery_schedule,
            name="Delivery schedule",
            attachment_type=allure.attachment_type.TEXT
        )
        checkout_page.click_continue_when_enabled()
        checkout_page.get_full_page_screenshot('schedule_continue')


@allure.suite("Public Side")
@allure.feature("Checkout")
@allure.story("Confirm Order")
@allure.title("Test_case_3: Confirm marketplace order")
@allure.description("Test case 3: Confirm the marketplace order for the whitelisted item requisition, get the order "
                    "reference number and order status, and save the order result.")
@pytest.mark.order(3)
def test_3_confirm_marketplace_order(page):
    """
    Test case 3: Confirm the marketplace order (same as marketplace_staging_sanity.py Test case 12).

    Steps:
        1. Fill the order remarks ('test_order_remarks') and accept terms of service.
        2. Confirm the order and store the order reference number in 'order_reference_number'.
        3. Open the order details and store the order status in 'order_status'.
        4. Log out from the Digital Marketplace.
        5. Save the order result (single_whitelisted_order_result.json) for the pending approval test file.

    All scenario values are read from .env.
    """
    global order_reference_number, order_status, order_result
    assert delivery_schedule, "Test case 2 must pass first: delivery schedule is not prepared"
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
            f"Order reference number: {order_reference_number}\nOrder status: {order_status}\n"
            f"Requisition: {req_num}\nAgreement: {requisition['agreement_version']}\nVendor: {order_vendor}\n"
            f"Item {requisition['item']['item_code']}: requisition quantity {requisition['item']['quantity']}, "
            f"cart quantity {cart_quantity}, unit price {requisition['item']['unit_price']}",
            name="Order status",
            attachment_type=allure.attachment_type.TEXT
        )
        checkout_page.get_full_page_screenshot('order_details')

    # Step 4: Log out from the Digital Marketplace
    with allure.step("Step 4: Log out from the Digital Marketplace"):
        MainNavigationMenu(page).perform_logout()
        checkout_page.get_full_page_screenshot('order_initiator_logout')

    # Step 5: Save the order result for the pending approval test file
    with allure.step("Step 5: Save the order result"):
        order_result = {
            "order_reference_number": order_reference_number,
            "order_status": order_status,
            "requisition_number": req_num,
            "agreement_version": requisition["agreement_version"],
            "vendor": order_vendor,
            "order_approver": requisition["final_approver"],
            "item_code": requisition["item"]["item_code"],
            "cart_quantity": cart_quantity,
            "unit_price": requisition["item"]["unit_price"],
        }
        save_result("single_whitelisted_order_result", order_result)
        print("ORDER RESULT:", order_result)
        allure.attach(
            "\n".join(f"{key}: {value}" for key, value in order_result.items()),
            name="Saved order result",
            attachment_type=allure.attachment_type.TEXT
        )
