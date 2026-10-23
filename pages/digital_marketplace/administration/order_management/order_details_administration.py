import re

from pages.digital_marketplace.administration.order_management.orders_list_management import OrdersListManagement
from pages.digital_marketplace.administration.vendor_dashboard import VendorDashboard
from utils.basic_actionsdm import BasicActionsDM


class OrderDetailsAdministration(VendorDashboard, OrdersListManagement, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger

        # self.acknowledge_button = page.locator('a[onclick^="openAcknowledgementModal("]')
        self.acknowledge_button = page.get_by_role("link", name="Acknowledge")
        self.acknowledge_popup_title = page.locator("modal-title", has_text="Are you sure?")
        self.close_button = page.get_by_role("button", name="×")

        # self.confirm_acknowledge_yes_button = page.locator('button[type="submit"][onclick^="acknowledgeSubmit"]')
        self.yes_button = page.get_by_role("button", name="Yes")
        self.edit_review_button = page.locator('a[class="btn btn-success"][onclick^="setLocation"]')

        self.back_to_order_list = page.get_by_role("link", name="back to order list")

        # Framework order number and order status after acknowledgement (same locators as sanity.py)
        self.framework_order_number_text = page.locator(
            'div.card-body:nth-child(6) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > '
            'div:nth-child(2) > div:nth-child(1)')
        self.acknowledged_order_status_text = page.locator(
            '//*[@id="order-info"]/div[5]/div[1]/div/div[5]/div[2]/div')

        # Vendor order details read by labels and table headers (vendor acknowledgement tests)
        self.products_table = page.locator("table").filter(has=page.locator("th", has_text="Item/Service name"))
        self.delivery_schedule_table = page.locator("table").filter(has=page.locator("th", has_text="Delivery Location"))
        self.print_button = page.locator("a:visible, button:visible").filter(
            has_text=re.compile(r"^\s*Print\s*$", re.I)).first

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def vendor_acknowledgment(self):
        self.click_on_btn(self.acknowledge_button)

    def confirmation_acknowledgment_by_yes(self):
        self.click_on_btn(self.acknowledge_button)
        self.click_on_btn(self.yes_button)
        # self.wait_for_timeout(5000)
        framework_order_number = self.page.locator(
            'div.card-body:nth-child(6) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)').text_content()
        # self.wait_to_load_element(self.order_locator)
        get_framework_order_number = framework_order_number
        print("Get work order number: " + get_framework_order_number)
        self.wait_for_timeout(5000)
        order_status_vendor_acknowledged = self.page.locator(
            '//*[@id="order-info"]/div[5]/div[1]/div/div[5]/div[2]/div').text_content()
        order_status = order_status_vendor_acknowledged
        print("Order status: " + order_status)
        # //*[@id="order-info"]/div[5]/div[1]/div/div[5]/div[2]/div
        return get_framework_order_number

    def click_back_to_order_list(self):
        self.back_to_order_list.click()
        print("Navigated back to order list")

    def click_order_management_menu(self):
        self.click_on_btn(self.order_management_menu)

    def acknowledge_order_with_status(self):
        # Acknowledge > Yes; returns the framework order number and the acknowledged order status
        self.click_on_btn(self.acknowledge_button)
        self.click_on_btn(self.yes_button)
        framework_order_number = (self.framework_order_number_text.text_content() or "").strip()
        self.wait_for_timeout(5000)
        order_status = (self.acknowledged_order_status_text.text_content() or "").strip()
        print(f"Framework order number: {framework_order_number}")
        print(f"Acknowledged order status: {order_status}")
        return framework_order_number, order_status

    def order_info_value(self, label):
        # Why: the order information is shown as label / value rows, so the value is found by its label, not by
        # position; When: Vendor Name, Framework Order No. and Order Status before and after the acknowledgement
        label_element = self.page.locator("label").filter(has_text=re.compile(rf"^\s*{re.escape(label)}", re.I)).first
        return label_element.locator(
            "xpath=ancestor::div[contains(@class, 'form-group')][1]//div[contains(@class, 'form-text-row')]").first

    def read_order_info(self, label):
        # Why: text of an order information value, "" when the label is not shown (no framework order number yet);
        # When: vendor order information checks
        value = self.order_info_value(label)
        return " ".join(value.inner_text().split()) if value.count() else ""

    def click_order_info_once(self, label):
        # Why: one click on the value shows the viewer the generated value (plain text, no action); When: after the
        # acknowledgement (Framework Order No., Order Status)
        value = self.order_info_value(label)
        value.scroll_into_view_if_needed()
        value.click()

    def visible_actions(self, names=("Acknowledge", "Send Back", "Print")):
        # Why: the vendor actions shown on the order details page (nothing is clicked); When: before and after the
        # acknowledgement
        return [name for name in names if self.page.locator("a:visible, button:visible").filter(
            has_text=re.compile(rf"^\s*{name}\s*$", re.I)).count()]

    def page_text(self):
        # Why: the order reference number is checked anywhere on the order details; When: vendor order details checks
        return " ".join(self.page.locator("body").inner_text().split())

    @staticmethod
    def table_headers(table):
        # Why: table columns are read by their header titles, not by position; When: Products and schedule tables
        return [" ".join(text.split()) for text in table.locator("th").all_inner_texts()]

    def admin_product_rows(self):
        # Why: the item rows of the Products table (rows with cells only); When: vendor product checks
        return [row for row in self.products_table.locator("tbody tr").all() if row.locator("td").count() > 3]

    def product_attachment(self, row):
        # Why: the item attachment of a product row (shown only when the item has an attachment); When: attachment
        # check and download
        return row.locator(".item-attachment-link, [data-attachment-path], a[href*='ttachment']").filter(visible=True)

    def product_requisition_link(self, row):
        # Why: the requisition number link of a product row; When: ERP redirect check
        return row.locator("a").filter(has_text=re.compile(r"^\s*REQ\d+\s*$")).first

    def product_framework_link(self, row):
        # Why: the FA No. link of a product row; When: Framework Agreement attachment check
        return row.locator("a").filter(has_text=re.compile(r"FA-\d+")).first

    def schedule_requisition_links(self):
        # Why: the "Requisition: REQ..." links of the Preferred Delivery Schedule rows; When: ERP redirect check
        return self.delivery_schedule_table.locator("a").filter(has_text=re.compile(r"REQ\d+")).all()

    def read_admin_product_row(self, row):
        # Why: product values for the data checks; the Item/Service cell is "[master] name - REQ.. / FA: .. /
        # Specification: ([FWI..] - product name - location ) specification / Remarks: .. / Attachment:";
        # When: vendor order details before and after the acknowledgement. Returns a dict
        headers = self.table_headers(self.products_table)
        cells = row.locator("td")

        def text_of(prefix):
            # Why: one column text by its header title; When: UoM, Quantity, prices
            index = next((i for i, title in enumerate(headers) if title.lower().startswith(prefix.lower())), None)
            return " ".join(cells.nth(index).inner_text().split()) if index is not None and index < cells.count() else ""

        item_index = next((i for i, title in enumerate(headers) if title.startswith("Item/Service")), 2)
        lines = [" ".join(line.split()) for line in cells.nth(item_index).inner_text().splitlines() if line.strip()]
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
            "Title": title,
            "Master item": master_item.group(1) if master_item else "",
            "Requisition": requisition.group(0) if requisition else "",
            "FA No.": next((line.split(":", 1)[1].strip() for line in lines if line.startswith("FA:")), ""),
            "Agreement item": agreement.group(1) if agreement else "",
            "Product name": agreement.group(2) if agreement else "",
            "Specification": " ".join(lines[specification_start:remarks_index]),
            "Remarks": " ".join(" ".join(remarks_lines).split()),
            "Attachment": self.product_attachment(row).count() > 0,
            "UoM": text_of("UoM"), "Quantity": text_of("Quantity"), "Unit Price": text_of("Unit Price"),
            "Discount": text_of("Discount"), "Total Price": text_of("Total Price"),
        }

    def read_admin_delivery_schedules(self):
        # Why: the Preferred Delivery Schedule rows (Product, Quantity, Delivery Date, Delivery Location, Delivery
        # Info); the Product cell is "product name / Requisition: REQ.."; When: vendor schedule checks
        headers = self.table_headers(self.delivery_schedule_table)
        schedules = []
        for row in self.delivery_schedule_table.locator("tbody tr").all():
            cells = row.locator("td")
            if cells.count() < len(headers):
                continue
            schedule = {title: " ".join(cells.nth(index).inner_text().split()) for index, title in enumerate(headers)}
            product_lines = [" ".join(line.split()) for line in cells.nth(0).inner_text().splitlines() if line.strip()]
            requisition = re.search(r"REQ\d+", schedule.get(headers[0], ""))
            schedule["Product"] = product_lines[0] if product_lines else ""
            schedule["Requisition"] = requisition.group(0) if requisition else ""
            schedules.append(schedule)
        return schedules

    def open_print_tab(self):
        # Why: Print opens the order document (ERP) in a new tab; When: after the acknowledgement
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(self.print_button)
        print_tab = new_tab_info.value
        print_tab.wait_for_url(lambda url: url.startswith("http"), timeout=60000, wait_until="commit")
        print(f"Order document opened: {print_tab.url}")
        return print_tab

    def acknowledge_order(self):
        # Why: Acknowledge > Yes generates the framework order number; When: vendor acknowledgement (once per order)
        self.click_on_btn(self.acknowledge_button)
        self.click_on_btn(self.yes_button)
        self.page.wait_for_load_state("domcontentloaded")
        self.wait_for_timeout(5000)

    def agreement_number_link(self):
        # Why: the Framework Agreement Number link of the agreement information section; When: agreement number check
        # of the vendor order details
        return self.order_info_value("Framework Agreement Number").locator("a").first

    def expand_collapsed_cards(self):
        # Why: Administration remembers collapsed cards per user (e.g. a vendor with the Info card closed), so the order
        # information is hidden; When: right after the vendor order details are opened, before they are read
        collapsed_cards = self.page.locator(".card.collapsed-card")
        for _ in range(collapsed_cards.count()):
            card = collapsed_cards.first
            expand_button = card.locator("[data-card-widget='collapse'], .btn-tool").first
            (expand_button if expand_button.count() else card.locator(".card-header").first).click()
            self.wait_for_timeout(1000)
        print(f"Collapsed cards expanded, still collapsed: {collapsed_cards.count()}")

    def open_print_document(self):
        # Why: Print opens the order document (ERP) in a new tab, directly as a PDF or through a viewer page that loads
        # the PDF; the PDF response is caught; When: order document of the order details (receive checks).
        # Returns (print tab, PDF address; "" when no PDF was loaded in 30 seconds)
        pdf_urls = []

        def keep_pdf(response):
            # Why: the order document is a PDF response; When: every response after Print
            if "application/pdf" in response.headers.get("content-type", ""):
                pdf_urls.append(response.url)

        self.page.context.on("response", keep_pdf)
        try:
            with self.page.context.expect_page() as new_tab_info:
                self.click_on_btn(self.print_button)
            print_tab = new_tab_info.value
            print_tab.wait_for_url(lambda url: url.startswith("http"), timeout=60000, wait_until="commit")
            for _ in range(60):
                if pdf_urls:
                    break
                print_tab.wait_for_timeout(500)
        finally:
            self.page.context.remove_listener("response", keep_pdf)
        print(f"Print opened: {print_tab.url} | PDF: {pdf_urls[0] if pdf_urls else 'not loaded'}")
        return print_tab, (pdf_urls[0] if pdf_urls else "")
