import re
from urllib.parse import unquote

from pypdf import PdfReader

from playwright.sync_api import expect
from pages.digital_marketplace.public_side.my_account.pending_approval_orders import PendingApprovalOrders


class OrderDetails(PendingApprovalOrders):
    # Order details page (/orderdetails/{id}): Order information, Product(s), Preferred Delivery Schedule and
    # Action History. The order information fields, the Preferred Delivery Schedule and the Action History are
    # read with the methods of PendingApprovalOrders (same order details layout).
    def __init__(self, page, logger=None):
        super().__init__(page, logger)
        self.page = page
        self.logger = logger
        # Product(s) table (SL | Item/Service name & Specification | UoM | Quantity | Unit Price | Total Price)
        self.product_table = page.locator("table").filter(has_text="Item/Service name & Specification").last
        self.product_attachment_icon = page.locator("i.fa-paperclip:visible")
        # Preferred Delivery Schedule headings "<product> - <REQ>": the product links (not the requisition links),
        # between the "Preferred Delivery Schedule" and "Action History" titles, in page order
        self.delivery_schedule_product_links = page.locator(
            "xpath=//*[normalize-space()='Preferred Delivery Schedule']/following::a[@target='_blank']"
            "[not(contains(@class,'requisition-link'))][following::*[normalize-space()='Action History']]")

    def get_product_rows(self):
        # Product rows as {column title: cell}, column titles from the first row
        expect(self.product_table).to_be_visible(timeout=30000)
        rows = self.product_table.locator("tr")
        headers = [" ".join(text.split()) for text in rows.first.locator("th, td").all_inner_texts()]
        product_rows = []
        for index in range(1, rows.count()):
            cells = rows.nth(index).locator("td")
            if cells.count() >= len(headers):
                product_rows.append({header: cells.nth(column) for column, header in enumerate(headers)})
        print(f"Order details products: {len(product_rows)}")
        return product_rows

    def get_sub_total(self):
        # Visible Sub-Total (Incl. VAT & TAX) value below the Product(s) table
        sub_total_label = self.page.locator("td:visible", has_text="Sub-Total").last
        expect(sub_total_label).to_be_visible(timeout=15000)
        sub_total = " ".join(sub_total_label.locator("xpath=following-sibling::td[1]").inner_text().split())
        print(f"Order details Sub-Total: {sub_total}")
        return sub_total

    @staticmethod
    def cell_text(cell):
        return " ".join((cell.inner_text() or "").split())

    def read_product_row(self, product_row):
        # Item/Service name & Specification cell and UoM, Quantity, Unit Price, Total Price of a product row
        item_cell = next(cell for title, cell in product_row.items() if title.startswith("Item/Service"))
        lines = [line.strip() for line in item_cell.inner_text().splitlines() if line.strip()]
        heading = lines[0]
        fa_line = next((line for line in lines if line.startswith("FA:")), "")
        start = next(index for index, line in enumerate(lines) if line.startswith("(["))
        remarks_at = next((index for index, line in enumerate(lines) if line.startswith("Remarks")), len(lines))
        attachment_at = next((index for index, line in enumerate(lines) if line.startswith("Attachment")), len(lines))
        values = {title: self.cell_text(cell) for title, cell in product_row.items()}
        product = {
            "Master item": heading.split(" - ")[0].strip(),
            "Requisition": heading.split(" - ")[-1].strip(),
            "FA No.": fa_line.replace("FA:", "").strip(),
            "Agreement item": lines[start],
            "Specification": " ".join(lines[start + 1:remarks_at]),
            "Remarks": " ".join(lines[remarks_at + 1:attachment_at]),
            # Items without attachment can have a hidden attachment icon: visible icons only
            "Attachment icon": item_cell.locator("i.fa-paperclip:visible").count() > 0,
            "UoM": next(value for title, value in values.items() if title.startswith("UoM")),
            "Quantity": next(value for title, value in values.items() if title.startswith("Quantity")),
            "Unit Price": next(value for title, value in values.items() if title.startswith("Unit Price")),
            "Total Price": next(value for title, value in values.items() if title.startswith("Total Price")),
        }
        print(f"Order details product: {product}")
        return product

    def open_product_link(self, product_row, link_text):
        # A link of the Item/Service name & Specification cell (requisition, FA, agreement item) in a new tab
        item_cell = next(cell for title, cell in product_row.items() if title.startswith("Item/Service"))
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(item_cell.locator("a", has_text=link_text).first)
        new_tab = new_tab_info.value
        new_tab.wait_for_load_state("domcontentloaded")
        return new_tab

    def get_all_preferred_delivery_schedules(self):
        # Preferred Delivery Schedule rows of all products (a schedule table per product), between the
        # "Preferred Delivery Schedule" and "Action History" titles; schedule rows only (with a Quantity)
        schedule_tables = self.page.locator(
            "xpath=//*[normalize-space()='Preferred Delivery Schedule']/following::table[not(.//table)]"
            "[following::*[normalize-space()='Action History']]")
        expect(schedule_tables.first).to_be_visible(timeout=15000)
        schedule_rows = []
        for index in range(schedule_tables.count()):
            schedule_rows += [row for row in self.read_table_rows(schedule_tables.nth(index)) if row.get("Quantity")]
        print(f"Preferred Delivery Schedule (all products): {schedule_rows}")
        return schedule_rows

    @staticmethod
    def product_link(product_row, link_text):
        # A link of the Item/Service name & Specification cell of a product row (requisition, FA, agreement item)
        item_cell = next(cell for title, cell in product_row.items() if title.startswith("Item/Service"))
        return item_cell.locator("a", has_text=link_text).first

    def delivery_schedule_requisition_link(self, requisition_number):
        # Preferred Delivery Schedule heading "<product> - <REQ>": the requisition link (ERP requisition details)
        return self.page.locator("a.requisition-link", has_text=requisition_number).last

    def open_link_all_tabs(self, link, wait_after_ms=5000):
        # Why: order details links (requisition) open 1 or 2 new tabs; When: the order details link checks;
        # returns all new tabs
        return self.open_link_in_new_tabs(link, wait_after_ms)

    def open_header_framework_link(self, fa_no):
        # Order information "Framework Agreement: <FA No.>" link (exact FA No. text, not the product "FA: ..." link)
        header_link = self.page.locator("a").filter(has_text=re.compile(rf"^\s*{re.escape(fa_no)}\s*$")).first
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(header_link)
        framework_tab = new_tab_info.value
        framework_tab.wait_for_load_state("domcontentloaded")
        return framework_tab

    def open_delivery_schedule_product_link(self, product_name):
        # Preferred Delivery Schedule heading "<product> - <REQ>": the product link (product details page);
        # the last product link of the page (the first one is in the Product(s) table)
        product_link = self.page.locator('a[target="_blank"]', has_text=product_name).last
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(product_link)
        product_tab = new_tab_info.value
        product_tab.wait_for_load_state("domcontentloaded")
        return product_tab

    def open_delivery_schedule_product_link_by_index(self, index):
        # Product link of the Preferred Delivery Schedule heading at a position (products can have the same name)
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(self.delivery_schedule_product_links.nth(index))
        product_tab = new_tab_info.value
        product_tab.wait_for_load_state("domcontentloaded")
        return product_tab

    def open_delivery_schedule_requisition_link(self, requisition_number):
        # Preferred Delivery Schedule heading "<product> - <REQ>": the requisition link (ERP requisition details)
        requisition_link = self.page.locator("a.requisition-link", has_text=requisition_number).last
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(requisition_link)
        requisition_tab = new_tab_info.value
        requisition_tab.wait_for_load_state("domcontentloaded")
        return requisition_tab

    def download_product_attachment(self, save_folder, index=0):
        # Attachment (paperclip) icon at a position of the page; returns the saved file path
        return self.download_attachment_from_icon(self.product_attachment_icon.nth(index), save_folder)

    def download_product_row_attachment(self, product_row, save_folder):
        # Attachment (paperclip) icon of a product row; returns the saved file path
        item_cell = next(cell for title, cell in product_row.items() if title.startswith("Item/Service"))
        return self.download_attachment_from_icon(item_cell.locator("i.fa-paperclip:visible").first, save_folder)

    def download_attachment_from_icon(self, attachment_icon, save_folder):
        # Why: check an order details attachment without showing the file in the browser; When: order details
        # attachment checks (by position or by product row)
        return self.save_attachment_from_icon(attachment_icon, save_folder)

    def open_order_preview(self):
        # Preview button: opens the order document (ERP) in a new tab
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(self.preview_button.first)
        preview_tab = new_tab_info.value
        # The order document is a PDF (no page load events): wait for its address only
        preview_tab.wait_for_url(lambda url: url.startswith("http"), timeout=60000, wait_until="commit")
        print(f"Order preview opened: {preview_tab.url}")
        return preview_tab

    @staticmethod
    def download_order_document(preview_tab, save_folder, file_name):
        # The preview is the order document (PDF, ERP printPurchaseOrder): save it; returns the saved file path
        response = preview_tab.context.request.get(preview_tab.url)
        saved_file = save_folder / file_name
        saved_file.write_bytes(response.body())
        print(f"Order document saved: {saved_file} ({response.headers.get('content-type', '')})")
        return saved_file

    @staticmethod
    def get_amount_in_words(document_text):
        # Amount in words after the Grand Total of the order document, e.g.
        # "Grand Total 7889857.96 : SEVENTY EIGHT LAKH ... TAKAIn Word AND NINETY SIX PAISA ONLY"
        # -> "SEVENTY EIGHT LAKH ... TAKA AND NINETY SIX PAISA ONLY" (the "In Word" label is removed)
        amount_match = re.search(r"Grand Total\s*[\d,.]+\s*:\s*(.+?ONLY)", document_text)
        if not amount_match:
            return ""
        return " ".join(amount_match.group(1).replace("In Word", " ").split())

    @staticmethod
    def read_order_document_text(document_file):
        # Text of all pages of the order document PDF, on one line
        reader = PdfReader(str(document_file))
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        return " ".join(text.split())
