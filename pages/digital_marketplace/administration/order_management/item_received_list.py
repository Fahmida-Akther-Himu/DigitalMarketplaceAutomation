from playwright.sync_api import expect
from pages.digital_marketplace.administration.order_management.orders_list_management import OrdersListManagement
from utils.basic_actionsdm import BasicActionsDM


class ItemReceivedList(OrdersListManagement, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger

        self.item_received_list_submenu = page.locator('a[href="/Admin/Order/CompleteOrderItemReceivedList"]')

        self.order_number_input = page.locator('#OrderNo')
        self.search_button_for_received_item = page.locator('button[id="search-complete-order-item-received-list"]')
        self.order_view_button = page.get_by_role("link", name="View")
        self.challan_no_input = page.locator('input[id="ChallanNo"]')

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def goto_received_order_list(self):
        # self.click_on_btn(self.order_management_menu)
        self.click_on_btn(self.item_received_list_submenu)
        self.wait_for_timeout(2000)

    def search_received_order(self, received_order_number):
        self.order_number_input.click()
        self.input_in_element(self.order_number_input.nth(0), received_order_number)
        self.click_on_btn(self.search_button_for_received_item)

    def fill_received_order_number(self, order_no):
        # Order No. autocomplete: select the exact match if the dropdown is shown (no Search click)
        self.fill_autocomplete_field(self.order_number_input.first, order_no)

    def received_order_view(self):
        # self.click_on_btn(self.order_view_button.first())
        self.order_view_button.first.click()
        # self.order_view_button.nth(0).click()

    def searched_received_order(self, challan_no):
        # Challan No. autocomplete: select the exact match if the dropdown is shown
        self.fill_autocomplete_field(self.challan_no_input.first, challan_no)

    def verify_challan_in_list(self, challan_no):
        # The received challan is shown in the Item Received List grid
        expect(self.order_rows.filter(has_text=challan_no).first).to_be_visible(timeout=15000)
        print(f"Challan found in Item Received List: {challan_no}")
