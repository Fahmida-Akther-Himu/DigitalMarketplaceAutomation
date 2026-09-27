import re
from decimal import Decimal

from utils.basic_actionsdm import BasicActionsDM
from playwright.sync_api import expect


def to_number(value):
    # "BDT 1,931.28" -> 1931.28, "500.99" -> 500.99
    # Decimal keeps 18-digit quantities (e.g. 999999999999999999.99) exact
    cleaned = re.sub(r"[^\d.]", "", str(value))
    return Decimal(cleaned) if cleaned else Decimal("0")


class WishlistPage(BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger

        # Wishlist page
        self.page_title = page.locator("div.wishlist-page div.page-title h1")
        self.wishlist_rows = page.locator("div.wishlist-page table.cart tbody tr")
        self.no_data_message = page.locator("div.wishlist-page div.no-data")
        # Only the "UPDATE WISHLIST" button (the row Remove "x" button also submits name='updatecart')
        self.update_wishlist_button = page.locator("div.wishlist-page").get_by_role(
            "button", name=re.compile(r"^\s*update wishlist\s*$", re.IGNORECASE))

        # Columns inside a wishlist row
        self.product_name = "td.product a.product-name"
        self.unit_price = "td.unit-price"
        self.quantity_input = "td.quantity input.qty-input"
        self.subtotal = "td.subtotal"

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def verify_wishlist_page_opened(self):
        expect(self.page).to_have_url(re.compile(r"/wishlist", re.IGNORECASE))
        expect(self.page_title).to_be_visible()
        print(f"Wishlist page title: {self.page_title.text_content().strip()}")

    def get_wishlist_row(self, product_name):
        # Exact match on product name, so similar product names are not picked
        exact_product_name = re.compile(rf"^\s*{re.escape(product_name)}\s*$")
        return self.wishlist_rows.filter(
            has=self.page.locator(self.product_name, has_text=exact_product_name)
        )

    def get_wishlist_product_count(self):
        product_count = self.wishlist_rows.count()
        print(f"Wishlist product count: {product_count}")
        return product_count

    def get_product_details(self, product_name):
        wishlist_row = self.get_wishlist_row(product_name)
        # Exactly one row: the product is present and not duplicated
        expect(wishlist_row).to_have_count(1)

        product_details = {
            "name": wishlist_row.locator(self.product_name).inner_text().strip(),
            "unit_price": wishlist_row.locator(self.unit_price).inner_text().strip(),
            "quantity": wishlist_row.locator(self.quantity_input).input_value().strip(),
            "subtotal": wishlist_row.locator(self.subtotal).inner_text().strip(),
        }
        print(f"Wishlist product details: {product_details}")
        return product_details

    def verify_product_in_wishlist(self, product_name, expected_price=None, expected_quantity=None):
        product_details = self.get_product_details(product_name)
        assert product_details["name"] == product_name, \
            f"Product name mismatch: expected '{product_name}', found '{product_details['name']}'"
        if expected_price is not None:
            assert to_number(product_details["unit_price"]) == to_number(expected_price), \
                f"Price mismatch for '{product_name}': expected {expected_price}, " \
                f"found {product_details['unit_price']}"
        if expected_quantity is not None:
            assert to_number(product_details["quantity"]) == to_number(expected_quantity), \
                f"Quantity mismatch for '{product_name}': expected {expected_quantity}, " \
                f"found {product_details['quantity']}"
        return product_details

    def get_product_quantity(self, product_name):
        wishlist_row = self.get_wishlist_row(product_name)
        expect(wishlist_row).to_have_count(1)
        quantity_field = wishlist_row.locator(self.quantity_input)
        self.click_on_btn(quantity_field)
        self.move_mouse_away()
        quantity = to_number(quantity_field.input_value())
        print(f"Current wishlist quantity of '{product_name}': {quantity:.2f}")
        return quantity

    def update_product_quantity(self, product_name, quantity):
        wishlist_row = self.get_wishlist_row(product_name)
        expect(wishlist_row).to_have_count(1)
        wishlist_row.locator(self.quantity_input).fill(str(quantity))
        self.click_on_btn(self.update_wishlist_button)
        self.move_mouse_away()
        self.page.wait_for_load_state("networkidle")
        print(f"Updated wishlist quantity of '{product_name}' to {quantity}")
