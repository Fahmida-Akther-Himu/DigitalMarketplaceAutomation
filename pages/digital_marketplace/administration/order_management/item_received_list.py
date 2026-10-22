import re

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
        # Item receive details ("View item receive details - <Item Receive No.>")
        self.receive_details_items_table = page.locator("table").filter(has=page.locator("th", has_text="Schedule Qty")).first
        self.action_history_table = page.locator("table").filter(has=page.locator("th", has_text="Action Name")).first
        self.receive_details_order_link = page.locator("a[href*='/Admin/Order/Edit/']").first
        # Challan No. of the item receive details (same page template as the receive page)
        self.receive_details_challan_no = page.locator("#challanNumber")

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

    def read_receive_detail(self, label):
        # Why: a value of the item receive details by its label (Item Receive No., Order No. link text, Vendor,
        # Status); When: item receive details checks
        label_element = self.page.locator("label").filter(has_text=re.compile(rf"^\s*{re.escape(label)}", re.I)).first
        if not label_element.count():
            return ""
        value = label_element.locator("xpath=ancestor::div[contains(@class, 'form-group')][1]/div[contains(@class, 'col-md-9')]")
        return " ".join((value.first.inner_text() if value.count() else "").split())

    def read_receive_detail_challan_no(self):
        # Why: the Challan No. of the item receive details is a form field; When: item receive details checks
        return " ".join(self.receive_details_challan_no.first.input_value().split()) \
            if self.receive_details_challan_no.count() else ""

    def read_receive_detail_items(self):
        # Why: the received items of the item receive details (Unit Price, Schedule Qty, Received Qty) with the item
        # cell parts; When: item receive details checks
        items = self.read_table_rows(self.receive_details_items_table)
        for item in items:
            item.update(self.parse_item_cell(item.get("Item/Service name & Specification", "")))
        return items

    def read_action_history(self):
        # Why: the Action History rows (Action Name, Action Taken By, Action Taken Date & Time) and the receive remarks;
        # When: item receive details checks. Returns (rows, receive remarks)
        # Action rows have a number in Sl (the "Receive Remarks / Receive Attachment" line has none)
        rows = [row for row in self.read_table_rows(self.action_history_table) if row.get("Sl", "").isdigit()]
        text = " ".join(self.action_history_table.inner_text().split())
        remarks = re.search(r"Receive Remarks:\s*(.*?)\s*Receive Attachment:", text)
        return rows, remarks.group(1) if remarks else ""

    def page_text(self):
        # Why: whole page text for "shown on the page" checks; When: item receive details checks
        return " ".join(self.page.locator("body").inner_text().split())
