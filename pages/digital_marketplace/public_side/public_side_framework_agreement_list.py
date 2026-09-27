import re

from utils.basic_actionsdm import BasicActionsDM
from playwright.sync_api import expect, TimeoutError as PlaywrightTimeoutError



class PublicSideFrameAgreementListPage(BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        # self    = page
        self.logger = logger

        self.search_agreement_locator = page.locator("input[id='seachKeyword']")
        self.agreement_search_button = page.locator("button[class='search-box-button']")
        self.agreement_view_hyperlink = page.locator("[class='button'][href^='/FrameworkProductList/']")
        self.product_links = page.locator("table.data-table tbody tr td:first-child a")
        self.back_to_active_agreement_list = page.locator("a[href='/FrameworkAgreementList']")
        # Agreement list table rows (FA No | Vendor | From Date | Till Date | Action)
        self.agreement_rows = page.locator("table tbody tr")

        # product details locator for add to wishlist
        self.item_add_to_wishlist = page.locator("div.add-to-wishlist button")
        # self.item_add_to_wishlist = page.locator("[id^='add-to-wishlist-button']")
        self.success_notification = page.locator("#bar-notification .bar-notification.success")
        self.success_message = page.locator("#bar-notification .bar-notification.success p.content")
        # self.success_message = self.success_notification.locator("p.content")
        self.wishlist_link = self.success_notification.locator("a[href='/wishlist']")
        self.close_notification = self.success_notification.locator("span.close")

        # Framework Product List table (Product Name | Specification | Price | Fwa Product Code)
        self.product_rows = page.locator("table.data-table tbody tr")

        # Product Details page
        self.product_details_name = page.locator("div.overview div.product-name h1")
        self.product_quantity_input = page.locator("div.overview input.qty-input")
        self.product_add_to_wishlist_button = page.locator(
            "div.overview div.add-to-wishlist button.add-to-wishlist-button")
        # Result of Add to wishlist: success / warning / error bar
        self.notification_bar = page.locator("#bar-notification .bar-notification")
        self.notification_message = self.notification_bar.locator("p.content")
        self.notification_close_button = self.notification_bar.locator("span.close")
        ##################### small helper so we can log easily #####################

    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def search_agreement(self, agreement_number):
        self.click_on_btn(self.search_agreement_locator)
        self.search_agreement_locator.clear()
        self.input_in_element(self.search_agreement_locator, agreement_number)
        self.click_on_btn(self.agreement_search_button)
        self.move_mouse_away()
        # self.wait_to_load_element(self.success_message)
        # value = self.success_message.text_content()
        # return value.split(' ')[-1]

    def get_search_result_rows(self, agreement_number):
        # All rows containing the searched FA No (may include BPD/2026/FA-50, FA-58, ...)
        return self.agreement_rows.filter(has_text=agreement_number)

    def get_exact_agreement_row(self, agreement_number):
        # Exact match on FA No, so BPD/2026/FA-5 does not match BPD/2026/FA-50
        exact_fa_no = re.compile(rf"^\s*{re.escape(agreement_number)}\s*$")
        return self.agreement_rows.filter(
            has=self.page.locator("td:nth-child(1)", has_text=exact_fa_no)
        )

    def get_agreement_vendor_name(self, agreement_number):
        agreement_row = self.get_exact_agreement_row(agreement_number)
        vendor_name = agreement_row.locator("td:nth-child(2)").inner_text().strip()
        print(f"Vendor name for {agreement_number}: {vendor_name}")
        return vendor_name

    def view_agreement_products(self, agreement_number):
        agreement_row = self.get_exact_agreement_row(agreement_number)
        self.click_on_btn(agreement_row.locator("a[href^='/FrameworkProductList/']"))
        self.move_mouse_away()

    def get_framework_products(self, max_products=2):
        # First 'max_products' rows of the Framework Product List (or fewer if not available)
        expect(self.product_rows.first).to_be_visible()
        product_count = min(self.product_rows.count(), max_products)

        framework_products = []
        for index in range(product_count):
            cells = self.product_rows.nth(index).locator("td")
            framework_products.append({
                "product_name": cells.nth(0).inner_text().strip(),
                "specification": cells.nth(1).inner_text().strip(),
                "price": cells.nth(2).inner_text().strip(),
                "fwa_product_code": cells.nth(3).inner_text().strip(),
            })
        print(f"Framework products: {framework_products}")
        return framework_products

    def open_product_details(self, product_name):
        exact_product_name = re.compile(rf"^\s*{re.escape(product_name)}\s*$")
        self.click_on_btn(self.product_links.filter(has_text=exact_product_name))
        # The mouse would otherwise rest on the product picture and show its title tooltip
        self.move_mouse_away()
        expect(self.product_details_name).to_have_text(exact_product_name)

    def add_product_to_wishlist_with_quantity(self, quantity, screenshot_name=None):
        """
        Enters the quantity, clicks Add to wishlist and returns the displayed result:
        {"type": "success" | "warning" | "error" | "alert", "message": "..."}
        A browser alert/confirm (if shown) is accepted and its message is returned.
        'screenshot_name' captures the page while the message is displayed.
        """
        dialog_messages = []

        def accept_dialog(dialog):
            dialog_messages.append(dialog.message)
            dialog.accept()

        self.page.on("dialog", accept_dialog)
        try:
            self.product_quantity_input.fill(str(quantity))
            self.click_on_btn(self.product_add_to_wishlist_button)
            self.move_mouse_away()
            try:
                self.notification_bar.wait_for(state="visible", timeout=15000)
            except PlaywrightTimeoutError:
                if not dialog_messages:
                    raise
        finally:
            self.page.remove_listener("dialog", accept_dialog)

        if dialog_messages:
            result = {"type": "alert", "message": dialog_messages[-1].strip()}
        else:
            bar_class = self.notification_bar.get_attribute("class") or ""
            result_type = next((t for t in ("success", "warning", "error") if t in bar_class), "success")
            result = {"type": result_type, "message": self.notification_message.inner_text().strip()}
            if screenshot_name:
                self.get_full_page_screenshot(screenshot_name)
            # Confirm/close the notification
            if self.notification_close_button.is_visible():
                self.notification_close_button.click()
                self.move_mouse_away()

        print(f"Add to wishlist {result['type']} message: {result['message']}")
        return result

    def product_add_to_wishlist(self):
        self.click_on_btn(self.item_add_to_wishlist)
        # wait for visible success message
        self.success_message.wait_for(state="visible")
        value = self.success_message.text_content().strip()
        print(f"Success Message: {value}")

        return value