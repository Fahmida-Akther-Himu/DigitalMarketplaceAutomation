import re
from pages.digital_marketplace.administration.order_management.orders_list_management import OrdersListManagement
from pathlib import Path

from utils.basic_actionsdm import BasicActionsDM


class ReceivableOrderList(OrdersListManagement, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger

        # self.order_management_menu = page.locator('i[class="nav-icon fas fa-shopping-cart"]')
        self.receivable_order_list_submenu = page.locator('a[href="/Admin/Order/ReceivableOrderList"]')
        self.order_input = page.locator('#OrderNo')
        # self.search_button = page.locator('button[id="search-orders"]')
        self.search_button = page.locator("//button[@id='search-orders']")
        self.order_view_button = page.get_by_role("link", name="View")

        self.challan_no = page.locator('textarea[id="challanNumber"]')
        self.all_item_select = page.locator('input[id="allItemSelect"]')
        self.item_select = page.locator('input[type="checkbox"]')
        self.quantity_to_receive = page.locator('input[class="qty-input commonInput"][type="number"]')
        self.received_remarks = page.locator('input[id="receivedRemarksText"]')
        self.submit_received_items = page.locator('button[id="receiveAllItems"]')

        self.x_icon = page.locator('button[class="close"]')
        self.cancel_button = page.get_by_role("button", name=re.compile(r"Cancel", re.I))
        self.confirm_button = page.locator('button[onclick="confirmReceiveSettlement()"]')

        self.receiving_attachment_upload_input = page.locator('input[id="itemAttachment"]')

        # Receive page ("Add a new item receive to order #...") of the logged-in receiver's schedules
        self.receive_page_heading = page.locator("h1").filter(has_text="item receive").first
        self.to_receive_table = page.locator("#ToReceiveItemTable")
        self.receive_order_details_link = page.locator("a[href*='/Admin/Order/Edit/']").first
        self.delivery_info_modal = page.locator("#shipmentItemModal")
        self.receive_overview_modal = page.locator("#receiveOverviewModal")
        self.challan_date_input = page.locator("#challanDateInput")
        self.receive_date_input = page.locator("#receiveDateInput")

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def goto_receivable_order_list(self):
        # self.click_on_btn(self.order_management_menu)
        self.click_on_btn(self.receivable_order_list_submenu)
        self.wait_for_timeout(2000)

    def search_receivable_order(self, receivable_order_number):
        # Order No. autocomplete: select the exact match if the dropdown is shown, then Search
        self.fill_autocomplete_field(self.order_input, receivable_order_number)
        self.search_button.click()

    def receivable_order_view(self):
        self.order_view_button.first.click()

    def challan_no_input(self, fill_challan_no):
        self.click_on_btn(self.challan_no)
        self.input_in_element(self.challan_no, fill_challan_no)
        self.wait_for_timeout(2000)

    def receivable_item_select(self):
        # self.item_select.nth(0).click()
        self.item_select.nth(1).check()

    def input_quantity_to_receive(self, received_quantity):
        self.quantity_to_receive.click()
        self.quantity_to_receive.clear()
        self.input_in_element(self.quantity_to_receive, received_quantity)
        self.wait_for_timeout(2000)

    def input_first_item_quantity_to_receive(self, received_quantity):
        # Several items can be received together: change the first item's Quantity to Receive only
        first_quantity = self.quantity_to_receive.first
        first_quantity.click()
        first_quantity.clear()
        first_quantity.fill(str(received_quantity))
        self.wait_for_timeout(2000)

    def input_received_remarks(self, receiving_remarks):
        self.click_on_btn(self.received_remarks)
        self.input_in_element(self.received_remarks, receiving_remarks)
        self.wait_for_timeout(2000)

    def open_item_receive_popup(self):
        self.click_on_btn(self.submit_received_items)

    def close_item_receive_popup(self):
        self.click_on_btn(self.cancel_button)

    def confirm_receivable_order(self):
        self.click_on_btn(self.confirm_button)
        self.wait_for_timeout(5000)

    # def upload_file_1(self, file_path: str, container: str = "#receivedRemarksDiv", index: int = 0,
    #                   timeout: int = 30000):
    #     p = Path(file_path).expanduser().resolve()
    #     if not p.exists():
    #         raise FileNotFoundError(f"File not found: {p}")
    #
    #     file_input = self.page.locator(f"{container} input[type='file']")
    #     file_input.wait_for(state="attached", timeout=timeout)
    #     file_input.set_input_files(str(p))
    #
    #     return True

    def receiving_upload_attachment(self, file_path: str, timeout: int = 10000) -> bool:
        try:
            # Ensure file exists
            p = Path(file_path).expanduser().resolve(strict=True)
            print(f"Uploading file path: {p}")

            # Wait for input to be attached in DOM
            self.receiving_attachment_upload_input.wait_for(state="attached", timeout=timeout)

            # Upload file
            self.receiving_attachment_upload_input.set_input_files(str(p))

            # Debug: check the value after upload
            input_value = self.receiving_attachment_upload_input.input_value()
            print(f"File input value: {input_value}")

            # Success if input has any non-empty value
            if input_value.strip():
                print(f"Successfully uploaded attachment name: {p.name}")
                return True

            print("File input value is empty after upload.")
            return False

        except Exception as e:
            print(f"File upload failed: {e}")
            return False

    def to_receive_rows(self):
        # Why: the schedule rows the logged-in receiver can receive (rows with cells only); When: receive page
        return [row for row in self.to_receive_table.locator("tbody tr").all() if row.locator("td").count() > 3]

    def read_to_receive_rows(self):
        # Why: every receive row by header titles + its item cell parts and the Quantity to Receive value;
        # When: receive page checks before and after the item selection
        rows = self.read_table_rows(self.to_receive_table)
        for row, row_element in zip(rows, self.to_receive_rows()):
            row.update(self.parse_item_cell(row.get("Item/Service name & Specification", "")))
            quantity_input = row_element.locator("input.commonInput").first
            row["Quantity to Receive"] = quantity_input.input_value() if quantity_input.count() else ""
            # A fully received schedule row has no checkbox (it cannot be received again)
            checkbox = row_element.locator("input[type='checkbox']")
            row["Selectable"] = checkbox.count() > 0
            row["Selected"] = checkbox.first.is_checked() if checkbox.count() else False
        return rows

    @staticmethod
    def receive_requisition_link(row):
        # Why: the requisition number link of a receive row (opens the ERP requisition); When: requisition link check
        return row.locator("a").filter(has_text=re.compile(r"^\s*REQ\d+\s*$")).first

    @staticmethod
    def select_receive_row(row):
        # Why: the receiver selects the schedule row to receive; When: before the receive popup
        row.locator("input[type='checkbox']").first.check()

    @staticmethod
    def set_row_quantity_to_receive(row, quantity):
        # Why: a partial receive changes the Quantity to Receive of the row; When: partial receive
        quantity_input = row.locator("input.commonInput").first
        quantity_input.fill("")
        quantity_input.fill(str(quantity))

    def read_row_delivery_info(self, row):
        # Why: View Details of a receive row shows the schedule Location and Delivery Info; When: receive page checks.
        # Returns {"Location", "Delivery Info"}
        # View Details is a label (not a link or button) in the receive row
        row.locator("label, a, button").filter(has_text=re.compile(r"^\s*View\s*$")).first.click()
        self.delivery_info_modal.wait_for(state="visible", timeout=10000)
        text = " ".join(self.delivery_info_modal.inner_text().split())
        location = re.search(r"Location:\s*(.*?)\s*Delivery Info:", text)
        delivery_info = re.search(r"Delivery Info:\s*(.*)$", text)
        self.delivery_info_modal.locator("button.close, [data-dismiss='modal']").first.click()
        self.delivery_info_modal.wait_for(state="hidden", timeout=10000)
        return {"Location": location.group(1) if location else "",
                "Delivery Info": delivery_info.group(1) if delivery_info else ""}

    def read_receive_dates(self):
        # Why: the Challan Date and Receive Date of the receive page (dd/mm/yyyy, the dates the receive is saved
        # with); When: before the receive popup. Returns (challan date, receive date)
        return self.challan_date_input.input_value(), self.receive_date_input.input_value()

    def read_receive_overview(self):
        # Why: the "Item receive overview" popup shows what will be received before Confirm; When: before Confirm.
        # Returns {"text": popup text, "items": rows with the item cell parts}
        self.receive_overview_modal.wait_for(state="visible", timeout=10000)
        # Received item rows only (with a Received Quantity): the popup table also has a hidden item row without
        # quantities, an empty row and the "Received Remarks" row
        items = [item for item in self.read_table_rows(self.receive_overview_modal.locator("table").last)
                 if item.get("Received Quantity")]
        for item in items:
            item.update(self.parse_item_cell(item.get("Item/Service name & Specification", "")))
        return {"text": " ".join(self.receive_overview_modal.inner_text().split()), "items": items}
