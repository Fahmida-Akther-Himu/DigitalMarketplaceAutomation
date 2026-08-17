import re
from itertools import count

from utils.basic_actionsdm import BasicActionsDM
from pages.digital_marketplace.home_page import HomePage


class MyDelegatedOrders(HomePage, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        #   Write down all the elements here with locator format
        # Goto my delegated orders menu/page
        self.my_delegated_orders = page.locator("a[href='/customer/PendingApprovalOrdersForDelegation']",
                                                has_text="My Delegated Orders")

        # Search delegated order reference number
        self.search_order_reference_number = page.get_by_placeholder('Order Reference Number')
        self.delegated_order_search_button = page.locator('button[class="button"][type="submit"]')

        # Go to my delegated order details
        self.delegated_order_details_button = page.get_by_role("button", name="Details")
        # self.approve_order_button = page.locator('a[id="approve-order-btn"]')
        # self.details_button = page.get_by_role("button", name="Details")
        # self.approve_order_button = page.get_by_role("link", name="Approve Order")
        self.approve_delegated_order_button = page.locator('a[id="approve-order-btn"]')

        self.delegated_order_yes_button = page.locator('button[onclick="yes(event)"]')
        # self.yes_button = page.get_by_role("button", name="YES")
        self.popup_close_button = page.locator("button.modal-close.modal-toggle")

        self.goto_order_list = page.locator("a.ico-account")

        # Order review
        self.delegated_order_review_button = page.locator('a[id="ReviewEditBtn"]')
        self.delegated_order_review_confirm_button = page.locator('button[class="button-2 review-confirm-button"]')
        self.enter_delegated_order_review_reasons = page.locator('textarea[id="reviewRemarks"]')

        # Preview locator
        self.preview_button_for_delegated_order = page.get_by_role("link", name="Preview")
        self.cancel_print_button_for_delegated_order = page.get_by_role("button", name="Cancel")

        # Order rejection locator
        self.reject_delegated_order_button = page.get_by_role("link", name="Reject Order")
        self.cancellation_remarks_for_delegated_order = page.locator("textarea[name='cancelRemarks']")

        self.delegated_order_toggle_button = page.locator('button[class="toggle-button collapsed-button btn"]')

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def search_delegated_order(self, delegated_order_reference_number):
        self.search_order_reference_number.click()
        self.input_in_element(self.search_order_reference_number, delegated_order_reference_number)

    def click_delegated_order_search_button(self):
        self.click_on_btn(self.delegated_order_search_button)

    def view_delegated_order_info_toggle(self):
        self.delegated_order_toggle_button.click()

    def goto_my_delegated_order_details(self):
        self.click_on_btn(self.delegated_order_details_button)

    def approve_my_delegated_order(self):
        self.click_on_btn(self.approve_delegated_order_button)
        self.click_on_btn(self.delegated_order_yes_button)
        self.wait_for_timeout(2000)
        delegated_order_status_approved = self.page.locator("text=Order Status:").text_content()
        delegated_order_status = delegated_order_status_approved.split(":")[-1].strip()
        print("Order status: " + delegated_order_status)
        return delegated_order_status

    def open_review_popup_for_delegated_order(self):
        self.click_on_btn(self.delegated_order_review_button)
        self.wait_for_timeout(2000)

    # Click on Review confirm without filling mandatory field
    def check_review_mandatory_validation_for_delegated_order(self):
        self.click_on_btn(self.delegated_order_review_confirm_button)
        self.wait_for_timeout(2000)
        # try:
        #     # Expect validation error to appear
        #     validation_error = self.page.locator("span.review-error-message")
        #     expect(validation_error).to_be_visible()
        #     self.get_full_page_screenshot('check_review_mandatory_validation')
        #     expect(validation_error).to_have_text(re.compile(r"Please fill out this field.", re.I))
        # except Exception as e:
        #     raise AssertionError(f"Mandatory validation check failed: {e}")

    def check_minimum_characters_validation_for_delegated_order(self):
        self.input_in_element(self.enter_delegated_order_review_reasons, '!')
        self.enter_delegated_order_review_reasons.clear()
        self.input_in_element(self.enter_delegated_order_review_reasons, 'ab')
        # self.click_on_btn(self.enter_review_reasons)
        self.wait_for_timeout(2000)
        self.click_on_btn(self.delegated_order_review_confirm_button)

    def check_max_min_characters_validation_for_delegated_order(self):
        self.enter_delegated_order_review_reasons.clear()
        characters = "Test delegated order review remarks !@# 1234567890"
        self.input_in_element(self.enter_delegated_order_review_reasons, characters)
        if (len(characters) >= 3) and (len(characters) <= 255):
            print(len(characters))
        elif len(characters) == 2:
            print(len(characters))
        elif len(characters) == 1:
            print(len(characters))
        elif len(characters) == 0:
            print(len(characters))
        else:
            print("Sorry!")
        self.wait_for_timeout(5000)

    def confirm_delegated_order_review(self):
        self.click_on_btn(self.delegated_order_review_confirm_button)

    def remove_review_popup(self):
        self.click_on_btn(self.popup_close_button)
        self.wait_for_timeout(2000)

    def delegated_order_review(self):
        self.click_on_btn(self.delegated_order_review_button)
        self.wait_for_timeout(2000)
        # self.input_in_element(self.enter_delegated_order_review_reasons,
        #                       'Send back reasons~!@#$%^&*()_+}{|”:?><~`,./’;[]=-\Docx word“confirm” is a verb in its present tense, meaning that it happens right now currently. the word “confirmed” is this same word in the past tense, meaning that confirmation occurred in the past. 2556')
        self.click_on_btn(self.delegated_order_review_confirm_button)

    def open_delegated_order_preview(self):
        self.click_on_btn(self.preview_button_for_delegated_order)
        self.wait_for_timeout(2000)
        # self.click_on_btn(self.cancel_print_button_for_delegated_order)
        # self.wait_for_timeout(2000)

    def open_delegated_order_rejection_popup(self):
        self.click_on_btn(self.reject_delegated_order_button)
        self.wait_for_timeout(2000)

    def remove_delegated_order_rejection_popup(self):
        self.click_on_btn(self.popup_close_button)
        self.wait_for_timeout(2000)

    def check_minimum_characters_validation_for_delegated_order_rejection(self):
        # self.click_on_btn(self.delegated_order_yes_button)
        self.input_in_element(self.cancellation_remarks_for_delegated_order, '')
        self.click_on_btn(self.delegated_order_yes_button)
        self.wait_for_timeout(2000)
        self.input_in_element(self.cancellation_remarks_for_delegated_order, '1')
        self.click_on_btn(self.delegated_order_yes_button)
        self.wait_for_timeout(2000)
        self.input_in_element(self.cancellation_remarks_for_delegated_order, 'a@')
        self.click_on_btn(self.delegated_order_yes_button)
        self.wait_for_timeout(2000)

    def rejection_max_characters_input_for_delegated_order(self):
        characters = "test delegation order rejection"
        # characters = "Delegation order rejection remarks or reasons~!@#$%^&*()_+}{|”:?><~`,./’;[]=-\Docx word“confirm” is a verb in its present tense, meaning that it happens right now currently. the word “confirmed” is this same word in the past tense, meaning that confirmation occurred in the past. 2556test"
        self.input_in_element(self.cancellation_remarks_for_delegated_order, characters)
        if (len(characters) >= 3) and (len(characters) <= 256):
            print(len(characters))
        else:
            print("Sorry!")
        self.wait_for_timeout(5000)

    def confirm_delegated_order_rejection(self):
        self.click_on_btn(self.delegated_order_yes_button)
        self.wait_for_timeout(2000)

    def get_my_delegated_orders_count(self, my_delegated_orders_count):
        text = self.my_delegated_orders.inner_text().strip()

        match = re.search(r"\((\d+)\)", text)

        if not match:
            raise AssertionError(
                f"Pending Approval Order count not found in text: {text}"
            )

        my_delegated_orders_count = int(match.group(1))
        print(f"Pending Approval Order Count: {my_delegated_orders_count}")
        return my_delegated_orders_count
