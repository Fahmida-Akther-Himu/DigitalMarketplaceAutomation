import re
from playwright.sync_api import expect
from pages.digital_marketplace.home_page import HomePage
from utils.basic_actionsdm import BasicActionsDM


class OrdersListManagement(HomePage, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        self.order_management_menu = page.locator('i[class="nav-icon fas fa-shopping-cart"]')
        self.orders_submenu = page.locator('a[href="/Admin/Order/List"][class="nav-link"]')
        self.vendor_send_backs_submenu = page.locator('a[href="/Admin/Order/VendorSendBackList"]')
        self.shipments_submenu = page.locator('a[href="/Admin/Order/ShipmentList"]')
        self.shipment_receive_submenu = page.locator('a[href="/Admin/Order/CompleteShipmentList"]')

        self.item_received_list_submenu = page.locator('a[href="/Admin/Order/CompleteOrderItemReceivedList"]')
        self.order_settlement_submenu = page.locator('a[href="/Admin/Order/OrderSettlementList"]')

        self.icon_expand = page.locator('i[class="far fa-angle-down"]')
        self.order_input = page.locator('#OrderNo')
        self.order_search_button = page.locator('button[id="search-orders"]')
        # Order number autocomplete dropdown and orders grid rows
        self.order_number_suggestions = page.locator(
            "ul.ui-autocomplete:visible li, .tt-menu:visible .tt-suggestion, .k-list-container:visible li")
        self.order_rows = page.locator("table tbody tr")
        # Sidebar Orders link (also matches when it is the active menu item)
        self.orders_nav_link = page.locator('a.nav-link[href="/Admin/Order/List"]').first
        # self.order = page.get_by_role("textbox", name="Order")
        # self.order_input = page.locator("#OrderNo")

        self.order_view_button = page.get_by_role("link", name="View")
        # self.acknowledge_button = page.get_by_role("link", name=re.compile(r"Acknowledge", re.I))
        # self.acknowledge_button = page.get_by_role("link", name="Acknowledge")
        # self.acknowledge_button = page.locator('div.float-right:nth-child(3) > a:nth-child(1)')
        # self.acknowledge_button = page.locator('a[onclick^="openAcknowledgementModal("]')
        self.acknowledge_button = page.get_by_role("link", name="Acknowledge")
        self.acknowledge_popup_title = page.locator("modal-title", has_text="Are you sure?")
        self.close_button = page.get_by_role("button", name="×")

        self.confirm_acknowledge_yes_button = page.locator('button[type="submit"][onclick="acknowledgeSubmit()"]')

        self.edit_review_button = page.locator('a[class="btn btn-success"][onclick^="setLocation"]')

        # self.framework_order_no = page.locator('h1[class="float-left"]')

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def goto_administration_order_list(self):
        self.click_on_btn(self.order_management_menu)
        self.click_on_btn(self.orders_submenu)
        self.wait_for_timeout(2000)

    def search_order(self, order_no):
        self.order_input.click()
        self.input_in_element(self.order_input, order_no)
        self.click_on_btn(self.order_search_button)

    def order_details_view(self):
        # self.click_on_btn(self.order_view_button.first())
        self.order_view_button.first.click()

    def vendor_acknowledgment(self):
        self.click_on_btn(self.acknowledge_button)

        # def confirmation_acknowledgment_by_yes(self):
        #     self.click_on_btn(self.acknowledge_button)
        #     self.click_on_btn(self.confirm_acknowledge_yes_button)
        #     self.wait_for_timeout(5000)
        #     # framework_order_number = self.page.locator("text=Order Details -").text_content()
        #     # # self.wait_to_load_element(self.order_locator)
        #     # get_framework_order_number = framework_order_number.split("-")[-1].strip()
        #     # print(get_framework_order_number)
        #     # return get_framework_order_number

        framework_order_number = self.page.locator(
            'div.card-body:nth-child(6) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)').text_content()
        # self.wait_to_load_element(self.order_locator)
        get_framework_order_number = framework_order_number
        print(get_framework_order_number)
        return get_framework_order_number

    def click_order_management_menu(self):
        self.click_on_btn(self.order_management_menu)

    def open_order_management_menu_if_collapsed(self, submenu):
        # Order Management menu toggles: click it only when the submenu is hidden
        if not submenu.is_visible():
            self.click_order_management_menu()

    # Use for search grid open
    def open_search_grid(self):
        self.click_on_btn(self.icon_expand)

    # Use for test purpose
    def input_fill(self):
        # self.click_on_btn(self.order)
        # self.input_in_element(self.order, "Fill")
        # self.page.locator("i.far.fa-angle-down").click()
        self.page.wait_for_selector("#OrderNo", state="visible")
        # Optional: wait until not disabled
        self.page.wait_for_function(
            "document.querySelector('#OrderNo') && !document.querySelector('#OrderNo').disabled")

        # Click and fill
        self.order_input.click(force=True)  # force in case something is overlapping
        self.order_input.fill("2025/TRN-2668")

    def open_search_panel_if_closed(self):
        # Search panel is collapsible: open it only if the Order field is not visible
        self.open_search_panel_if_collapsed(self.order_input)

    def search_order_from_dropdown(self, order_no):
        # Type the order number, click it in the dropdown if the page shows one, then Search again
        self.fill_autocomplete_field(self.order_input, order_no)
        self.move_mouse_away()
        self.click_on_btn(self.order_search_button)
        self.wait_for_timeout(3000)

    def verify_order_in_list(self, order_no):
        # The searched order is shown in the orders grid
        expect(self.order_rows.filter(has_text=order_no).first).to_be_visible(timeout=15000)
        print(f"Order found in orders list: {order_no}")

    def goto_orders_list(self):
        # Why: the Order Management menu toggles, so it is clicked only when Orders is hidden; When: opening the
        # Orders list from any administration page (vendor Orders list path)
        self.open_order_management_menu_if_collapsed(self.orders_nav_link)
        self.click_on_btn(self.orders_nav_link)
        self.page.wait_for_load_state("domcontentloaded")
        self.wait_for_timeout(2000)

    def order_list_row(self, order_no):
        # Why: the row of an order in the Orders grid (order reference or framework order number); When: Orders list
        # path to the order details
        return self.order_rows.filter(has_text=order_no).first

    def show_all_orders(self):
        # Why: the Order field may not find an order by its reference, so the list is shown without filters;
        # When: Orders list path when the searched order is not in the grid
        self.order_input.fill("")
        self.click_on_btn(self.order_search_button)
        self.wait_for_timeout(3000)

    def open_order_from_list(self, order_no):
        # Why: View of the order row opens its order details; When: Orders list path to the order details
        self.click_on_btn(self.order_list_row(order_no).locator("a, button").filter(has_text="View").first)
        self.page.wait_for_load_state("domcontentloaded")
        self.wait_for_timeout(3000)

    def read_order_list_row(self, order_no):
        # Why: the Orders grid columns (Framework Order No, Reference #, Order status, Shipping status, ...) of an
        # order row, read by their header titles; When: Shipping status before and after the vendor acknowledgement
        row = self.order_list_row(order_no)
        headers = [" ".join(text.split()) for text in row.locator("xpath=ancestor::table[1]//th").all_inner_texts()]
        cells = row.locator("td")
        values = {title: " ".join(cells.nth(index).inner_text().split())
                  for index, title in enumerate(headers) if title and index < cells.count()}
        print(f"Orders list row {order_no}: {values}")
        return values

    @staticmethod
    def read_table_rows(table):
        # Why: the rows of a table as {header title: cell text} (cell lines kept with "\n"), read by the header
        # titles, not by position; When: receive page, receive popup and item receive details tables
        headers = [" ".join(text.split()) for text in table.locator("th").all_inner_texts()]
        rows = []
        for row in table.locator("tbody tr").all():
            cells = row.locator("td")
            if cells.count() < 2:
                continue
            texts = ["\n".join(" ".join(line.split()) for line in cell.splitlines() if line.strip())
                     for cell in cells.all_inner_texts()]
            # Cells by position of their header title (a checkbox column has an empty title and is left out)
            rows.append({title: texts[index] for index, title in enumerate(headers) if title and index < len(texts)})
        return rows

    @staticmethod
    def parse_item_cell(cell_text):
        # Why: the "Item/Service name & Specification" cell is "[master] name - REQ.. / FA: .. / Specification:
        # ([FWI..] - product name - location ) specification / Remarks: .. / Attachment:"; When: receive pages.
        # Returns {"Master item", "Requisition", "FA No.", "Agreement item", "Product name", "Specification", "Remarks"}
        lines = [line.strip() for line in cell_text.splitlines() if line.strip()]
        title = lines[0] if lines else ""
        agreement_index = next((i for i, line in enumerate(lines) if line.startswith("([")), None)
        agreement = re.match(r"^\(\s*\[(\w+)\]\s*-\s*(.*?)\s*\)$", lines[agreement_index]) \
            if agreement_index is not None else None
        remarks_index = next((i for i, line in enumerate(lines) if line.startswith("Remarks")), len(lines))
        attachment_index = next((i for i, line in enumerate(lines) if line.startswith("Attachment")), len(lines))
        specification_start = agreement_index + 1 if agreement_index is not None else remarks_index
        remarks_lines = [lines[remarks_index].split(":", 1)[-1]] + lines[remarks_index + 1:attachment_index] \
            if remarks_index < len(lines) else []
        master_item = re.match(r"^(\[\w+\])", title)
        requisition = re.search(r"REQ\d+", title)
        return {
            "Master item": master_item.group(1) if master_item else "",
            "Requisition": requisition.group(0) if requisition else "",
            "FA No.": next((line.split(":", 1)[1].strip() for line in lines if line.startswith("FA:")), ""),
            "Agreement item": agreement.group(1) if agreement else "",
            "Product name": agreement.group(2) if agreement else "",
            "Specification": " ".join(lines[specification_start:remarks_index]),
            "Remarks": " ".join(" ".join(remarks_lines).split()),
        }
