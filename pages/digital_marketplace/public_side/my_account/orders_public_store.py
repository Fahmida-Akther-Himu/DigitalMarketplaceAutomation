import re
from pages.digital_marketplace.home_page import HomePage
from utils.basic_actionsdm import BasicActionsDM


class OrdersPublicStore(HomePage, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger
        self.search_order_input = page.locator('input[placeholder="Order Number/Reference No"]')
        self.initiator_toggle_button = page.locator('button[class="toggle-button collapsed-button btn"]')
        self.details_button = page.get_by_role("button", name="Details")
        self.order_search_button = page.locator('button[class="search-box-button"]')

        # Menu availability
        self.pending_approval_orders_menu = page.locator(
            "div.block-account-navigation li.pending-approval-orders"
        )
        self.pending_approval_orders = page.locator(
            "a[href='/customer/pendingApprovalOrders']"
        )

        # My Delegated Orders menu availability
        self.my_delegated_orders_menu = page.locator(
            "div.block-account-navigation li.pending-approval-orders-for-delegation"
        )

        # My Delegated Orders clickable link + dynamic count
        self.my_delegated_orders = page.locator(
            "a[href='/customer/PendingApprovalOrdersForDelegation']"
        )

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def search_order_no_or_reference_no(self, order_no):
        self.click_on_btn(self.search_order_input)
        self.input_in_element(self.search_order_input, order_no)
        self.click_on_btn(self.order_search_button)

    def order_info_view_by_toggle(self):
        self.initiator_toggle_button.first.click()

    def view_order_details(self):
        self.details_button.first.click()
        self.wait_for_timeout(2000)

    def check_pending_approval_orders_menu(self):
        if self.pending_approval_orders_menu.count() > 0:
            print("Pending Approval Orders menu is available.")
        else:
            print("Pending Approval Orders menu is not available.")

    # def go_to_pending_approval_orders_if_available_1(self):
    #     if self.pending_approval_orders_menu.count() > 0:
    #         print("Pending Approval Orders menu is available.")
    #         self.pending_approval_orders.click()
    #     else:
    #         print("Pending Approval Orders menu is not available.")

    def go_to_pending_approval_orders_if_available(self):
        if self.pending_approval_orders_menu.count() > 0:
            print("Pending Approval Orders menu is available.")

            # Get count before clicking/navigating
            text = self.pending_approval_orders.inner_text().strip()

            match = re.search(r"\((\d+)\)", text)

            if not match:
                raise AssertionError(
                    f"Pending Approval Order count not found in text: {text}"
                )

            pending_approval_order_count = int(match.group(1))

            print(
                f"Pending Approval Order Count: "
                f"{pending_approval_order_count}"
            )

            # Navigate after getting the count
            self.pending_approval_orders.click()

            return pending_approval_order_count

        else:
            print("Pending Approval Orders menu is not available.")
            return 0

    def go_to_my_delegated_orders_if_available(self):
        if self.my_delegated_orders_menu.count() > 0:
            print("My Delegated Orders menu is available.")

            # Get count before clicking/navigating
            text = self.my_delegated_orders.inner_text().strip()

            match = re.search(r"\((\d+)\)", text)

            if not match:
                raise AssertionError(
                    f"Pending Approval Order count not found in text: {text}"
                )

            delegated_order_count = int(match.group(1))
            # delegated_order_count = self.get_my_delegated_order_count()

            print(
                f"My Delegated Order Count: {delegated_order_count}"
            )

            self.my_delegated_orders.click()

            return delegated_order_count

        else:
            print("My Delegated Orders menu is not available.")
            return 0
