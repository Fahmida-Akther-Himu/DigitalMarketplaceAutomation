import re
from decimal import Decimal

from playwright.sync_api import expect
from utils.basic_actionsdm import BasicActionsDM


class RequisitionDetailsInformation(BasicActionsDM):

    def __init__(self, page, logger=None):
        super().__init__(page)

        self.page = page
        self.logger = logger
        self.fa_no_hyperlink = page.locator('a[style="text-decoration: underline;"][onclick^="showFrameworkDetails("]')
        # Requisition information (REQ. No, Status, ...)
        self.details_content = page.locator("body")

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def open_framework_details(self):
        self.click_on_btn(self.fa_no_hyperlink.first)
        self.move_mouse_away()

    @staticmethod
    def _row_numbers(item_row):
        # Numeric cells of a row (Quantity, Unit Price, ...), compared as numbers (281.4 = 281.40)
        row_numbers = set()
        for cell_text in item_row.locator("td").all_inner_texts():
            if re.fullmatch(r"\s*[\d,]+(\.\d+)?\s*", cell_text):
                row_numbers.add(Decimal(cell_text.strip().replace(",", "")))
        return row_numbers

    def verify_requisition_details(self, requisition_number, fa_no, item_code, quantity, unit_price):
        # REQ. No on the details page
        expect(self.details_content).to_contain_text(requisition_number, timeout=30000)

        # Requisition Details row of the Framework Agreement item:
        # FA. No | Budget Code | Item Name | M.Unit | Quantity | Unit Price | Total Price
        # Exact FA No, e.g. "BPD/2026/FA-5 (Both)" matches BPD/2026/FA-5 but not BPD/2026/FA-50
        fa_no_link = self.fa_no_hyperlink.filter(has_text=re.compile(rf"^\s*{re.escape(fa_no)}(\s|$|/)"))
        expect(fa_no_link).to_have_count(1)
        item_row = fa_no_link.locator("xpath=ancestor::tr[1]")
        expected_details = {
            "Requisition number": requisition_number,
            "FA. No": fa_no,
            "Item": item_code,
            "Quantity": quantity,
            "Unit Price": unit_price,
        }
        expect(item_row, f"Item '{item_code}' not found in requisition details").to_contain_text(str(item_code))

        # Quantity and Unit Price compared as numbers (the page may show 281.4 for 281.40)
        row_numbers = self._row_numbers(item_row)
        for label in ("Quantity", "Unit Price"):
            assert Decimal(str(expected_details[label])) in row_numbers, \
                f"{label} '{expected_details[label]}' not found in requisition details: {sorted(row_numbers)}"

        self.highlight_element(item_row)
        details_text = " | ".join(text.strip() for text in item_row.locator("td").all_inner_texts() if text.strip())
        print(f"Requisition details verified: {details_text}")
        return details_text

    def verify_requisition_item(self, requisition_number, fa_no, item_code, quantity, unit_price):
        # For requisitions with several items of the same FA No:
        # find the row with this item code, quantity and unit price
        expect(self.details_content).to_contain_text(requisition_number, timeout=30000)

        fa_no_links = self.fa_no_hyperlink.filter(has_text=re.compile(rf"^\s*{re.escape(fa_no)}(\s|$|/)"))
        expect(fa_no_links.first).to_be_visible()
        matching_rows = []
        for index in range(fa_no_links.count()):
            item_row = fa_no_links.nth(index).locator("xpath=ancestor::tr[1]")
            row_text = " ".join(item_row.locator("td").all_inner_texts())
            row_numbers = self._row_numbers(item_row)
            if str(item_code) in row_text and Decimal(str(quantity)) in row_numbers \
                    and Decimal(str(unit_price)) in row_numbers:
                matching_rows.append(item_row)
        assert len(matching_rows) == 1, \
            f"Expected 1 row of {fa_no} with item {item_code}, quantity {quantity} and unit price {unit_price}, " \
            f"found {len(matching_rows)}"

        item_row = matching_rows[0]
        self.highlight_element(item_row)
        details_text = " | ".join(text.strip() for text in item_row.locator("td").all_inner_texts() if text.strip())
        print(f"Requisition item verified: {details_text}")
        return details_text

    def verify_requisition_item_count(self, fa_no, expected_count):
        fa_no_links = self.fa_no_hyperlink.filter(has_text=re.compile(rf"^\s*{re.escape(fa_no)}(\s|$|/)"))
        expect(fa_no_links).to_have_count(expected_count)
        print(f"Requisition items of {fa_no}: {expected_count}")
