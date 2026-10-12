from urllib.parse import unquote
# import urllib2 from BeautifulSoup import BeautifulSoup soup = BeautifulSoup(urllib2.urlopen("https://www.google.com")) print soup.title.string;
import re

from pages.digital_marketplace.login_page import LoginPage
from utils.basic_actionsdm import BasicActionsDM
from pages.digital_marketplace.home_page import HomePage
from playwright.sync_api import expect


class ShoppingCart(HomePage, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        self.vendor_container = page.locator('div[id^="vendorContainer"]')
        self.selected_vendor_item = page.locator('input[id^="radio"]')
        self.requisition_locator = page.locator('a.item-requisition-link')
        # self.requisition_locator = page.locator('a[class="item-requisition-link"]')
        self.checked_requisition_locator = page.locator('input[checked="checked"][type="checkbox"]')
        self.cart_form = page.locator('form[id="shopping-cart-form"]')

        self.selected_radio = page.locator(
            "//div[input[@type='radio' and @checked='checked']]/label"
        )

        self.select_cart_terms_and_condition = page.locator('input[id="termsofservice"]')
        self.select_cart_checkout_button = page.locator('button[id="checkout"][type="submit"]')

        # self.vendor_name = "Plan for demand"
        self.remove_button = page.locator('button[name="updatecart"][class="remove-btn"]')
        # self.cart_quantity = page.locator('//*[@id="topcartlink"]/a/span[2]')
        self.logo = page.locator("a[href='/']")

        self.click_username = page.locator('.ico-account')

        self.item_remarks_textarea_locator = page.locator(
            'xpath=//strong[normalize-space(text())="Specification"]/following-sibling::textarea')
        self.item_remarks_locator = page.locator('textarea[id^="itemRemarks"]')
        self.cart_quantity_input = page.locator('input[id^="itemquantity"]')
        self.selected_item_quantity = page.locator('input[id^="itemquantity"][inputmode="numeric"]')
        # Visible item quantities only (items of unchecked requisitions are hidden in the cart)
        self.visible_item_quantity = page.locator('input[id^="itemquantity"][inputmode="numeric"]:visible')
        self.select_choose_file = page.locator('input[type="file"][name="file"][id^="itemAttachment"]')
        self.confirm_button = page.get_by_role("button", name="Confirm")
        self.cancel_button = page.get_by_role("button", name="Cancel")
        self.update_shopping_cart = page.locator('button[id="updatecart"]')
        # "Yes" button of the attachment remove confirmation pop-up
        self.attachment_remove_yes_button = page.get_by_role("button", name=re.compile(r"^\s*yes\s*$", re.IGNORECASE))

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def select_vendor_for_requisition_found(self, requisition_number: str):
        # Locate all matching requisition links
        requisition_matches = self.page.locator(f"a.item-requisition-link:has-text('{requisition_number}')")

        # Wait for the shopping cart to load the requisition
        try:
            requisition_matches.first.wait_for(state="visible", timeout=15000)
        except Exception:
            pass

        if requisition_matches.count() == 0:
            print(f"Requisition {requisition_number} not found in cart.")
            #
            self.click_on_btn(self.logo)
            self.wait_for_timeout(2000)

            # s_page = ActiveRequisitionProductList(page)
            # s_page.requisition_item_add_shopping_cart()
            return

        print(f"Found {requisition_matches.count()} match(es) for requisition: {requisition_number}")

    def select_vendor_by_name(self, vendor_name: str, requisition_number):
        # Build a locator for the vendor's radio button
        radio_button = self.page.locator(
            f"//div[starts-with(@id,'vendorContainer')]//label[contains(., '{vendor_name}')]/preceding-sibling::input[@type='radio']"
        )

        # Vendor selection loads slowly (depends on the shopping cart items): wait until it is enabled
        try:
            expect(radio_button.first).to_be_visible(timeout=60000)
            expect(radio_button.first).to_be_enabled(timeout=60000)
        except Exception:
            pass

        if radio_button.count() == 0:
            print(f"Vendor '{vendor_name}' not found.")
            return False

        print(f"Found vendor: {vendor_name}")
        # The cart page must be fully loaded first, otherwise the vendor selection is not handled by the page
        self.page.wait_for_load_state("load")
        self.wait_for_timeout(3000)
        if radio_button.first.is_checked():
            # Vendor already selected when the cart opens: fire its change event to load the vendor's items
            radio_button.first.dispatch_event("change")
        else:
            radio_button.check()
        self.wait_for_timeout(2000)
        # Shopping cart reloads for the selected vendor: wait until the item Qty. fields are shown
        self.page.wait_for_load_state("load")
        expect(self.visible_item_quantity.first).to_be_visible(timeout=60000)
        print(f"Selected radio button for vendor: {vendor_name}")

        # Find all checked requisitions
        checked_reqs = self.page.locator(
            "//input[@type='checkbox' and @checked]/following-sibling::label/strong"
        )

        req_numbers = checked_reqs.all_inner_texts()
        print(f"Found {len(req_numbers)} checked requisition(s).")

        for req_number in req_numbers:
            req_number = req_number.strip()

            if req_number != requisition_number:
                # Uncheck by finding its input based on label text
                requisition_checkbox = self.page.locator(
                    f"//label[strong[normalize-space(text())='{req_number}']]/preceding-sibling::input[@type='checkbox']"
                )
                requisition_checkbox.click()
                # The cart reloads after each uncheck: wait until it is really unchecked, click again if not
                try:
                    expect(requisition_checkbox).not_to_be_checked(timeout=15000)
                except AssertionError:
                    requisition_checkbox.click()
                    expect(requisition_checkbox).not_to_be_checked(timeout=15000)
                self.page.wait_for_load_state("load")
                print(f"Unchecked requisition: {req_number}")
            else:
                print(f"Kept requisition checked: {req_number}")

        return True

    def update_shopping_cart_value_1(self, qty_update: str):
        first_item_quantity = self.visible_item_quantity.first
        first_item_quantity.click()
        first_item_quantity.clear()
        self.input_in_element(first_item_quantity, qty_update)
        self.update_shopping_cart.click()
        self.wait_for_timeout(5000)

    def upload_attachment(self, file_path: str) -> bool:
        try:
            upload_input = self.page.locator('input[type="file"][id^="itemAttachment"]').first  # first item only
            if self.visible_item_quantity.count():
                item_id = re.sub(r"\D", "", self.visible_item_quantity.first.get_attribute("id") or "")
                if item_id:
                    upload_input = self.page.locator(f'input[type="file"]#itemAttachment{item_id}')
            confirm_button = self.page.get_by_role("button", name="Confirm")

            # Wait for the attachment input (cart reloads after vendor selection)
            try:
                upload_input.wait_for(state="attached", timeout=15000)
            except Exception:
                pass

            if upload_input.count() == 0:
                print("Upload input not found on page.")
                return False

            # Perform the upload
            upload_input.set_input_files(file_path)
            confirm_button.click()
            print(f"Uploaded file: {file_path}")
            self.wait_for_timeout(2000)
            return True

        except Exception as e:
            print(f"Failed to upload attachment: {e}")
            return False

    def update_cart_item_remarks(self, requisition_number: str, remarks_text: str):
        remarks_locator = self.page.locator(
            f"//a[normalize-space()='{requisition_number}']/ancestor::td//textarea[starts-with(@id,'itemRemarks')]"
        ).first  # first item only
        if remarks_locator.count() == 0:
            raise Exception(f"No remarks field found for requisition {requisition_number}")

        remarks_locator.fill(remarks_text)
        print(f"Updated remarks for requisition {requisition_number} with: {remarks_text}")
        return True

    def update_shopping_cart_info(self):
        self.update_shopping_cart.click()

    def remove_vendor_item(self):
        count = self.remove_button.count()
        print("Found " + str(count) + " vendor items")
        for i in range(count):
            self.remove_button.first.click()
            self.wait_for_timeout(2000)
        self.wait_for_timeout(5000)

    def select_vendor_and_checkout_cart_page(self):
        self.click_on_btn(self.vendor_selection)
        self.click_on_btn(self.selected_vendor_item)
        self.click_on_btn(self.select_cart_terms_and_condition)
        self.click_on_btn(self.select_cart_checkout_button)

    def select_vendor(self):
        self.click_on_btn(self.selected_vendor_item)
        # self.wait_for_timeout(5000)
        get_vendor_name = self.page.locator("//text()[contains(., 'Vendor')]/following::strong[1]").text_content()
        # self.wait_to_load_element(self.order_locator)
        # agreement = fa.split(":")[-1].strip()
        print(get_vendor_name)
        return get_vendor_name

    def update_shopping_cart_remarks(self):
        self.item_remarks_locator.nth(0).click()
        self.item_remarks_locator.nth(0).clear()
        self.input_in_element(self.item_remarks_locator.nth(0), "Marketplace item")

    def update_shopping_cart_value(self, qty_update):
        self.cart_quantity_input.nth(0).click()
        self.cart_quantity_input.nth(0).clear()
        self.input_in_element(self.cart_quantity_input.nth(0), qty_update)
        self.update_shopping_cart.nth(0).click()
        self.wait_for_timeout(5000)

    def upload_attachment_1(self, attachment_file):
        # self.upload_attachment.click()
        uploaded_file_name = self.upload_file(self.select_choose_file, attachment_file)
        print(f"Uploaded file name: {uploaded_file_name}")
        self.confirm_button.click()

    def cart_page_checkout(self):
        self.click_on_btn(self.select_cart_terms_and_condition)
        self.click_on_btn(self.select_cart_checkout_button)
        self.wait_for_timeout(5000)

    def goto_home_page(self):
        self.click_on_btn(self.logo)
        self.wait_for_timeout(2000)

    def goto_order_list(self):
        self.click_on_btn(self.click_username)

    # Use for review requisition item order
    def item_remarks_update_for_multiple_items(self):
        self.item_remarks_locator.nth(0).click()
        self.item_remarks_locator.nth(0).clear()
        self.input_in_element(self.item_remarks_locator.nth(0), "test remarks 1")
        self.item_remarks_locator.nth(1).click()
        self.item_remarks_locator.nth(1).clear()
        self.input_in_element(self.item_remarks_locator.nth(1), "test remarks 2")

    def update_shopping_cart_info_1(self):
        self.click_on_btn(self.update_shopping_cart)

    def update_cart_value_for_multiple_items(self):
        self.cart_quantity_input.nth(0).click()
        self.cart_quantity_input.nth(0).clear()
        self.input_in_element(self.cart_quantity_input.nth(0), "5")
        self.cart_quantity_input.nth(1).click()
        self.cart_quantity_input.nth(1).clear()
        self.input_in_element(self.cart_quantity_input.nth(1), "10")

    def item_remarks_update_for_review_order(self):
        self.item_remarks_locator.nth(0).click()
        self.item_remarks_locator.nth(0).clear()
        self.input_in_element(self.item_remarks_locator.nth(0), "Review Order item test remarks 1")

    def update_cart_value_for_review_order(self):
        self.cart_quantity_input.nth(0).click()
        self.cart_quantity_input.nth(0).clear()
        self.input_in_element(self.cart_quantity_input.nth(0), "9")
        self.cart_quantity_input.nth(1).click()
        self.cart_quantity_input.nth(1).clear()
        self.input_in_element(self.cart_quantity_input.nth(1), "6")

    def wait_for_requisition_in_cart(self, requisition_number: str, max_wait_seconds: int = 300,
                                     reload_every_seconds: int = 30) -> bool:
        # The approved requisition is synced from ERP to the shopping cart after some time:
        # reload the cart until the requisition is shown (or max_wait_seconds is reached)
        requisition_link = self.page.locator(f"a.item-requisition-link:has-text('{requisition_number}')")
        waited_seconds = 0
        while True:
            try:
                requisition_link.first.wait_for(state="visible", timeout=15000)
                print(f"Requisition {requisition_number} found in cart after about {waited_seconds} seconds")
                return True
            except Exception:
                pass
            if waited_seconds >= max_wait_seconds:
                print(f"Requisition {requisition_number} not in cart after {max_wait_seconds} seconds")
                return False
            print(f"Requisition {requisition_number} not in cart yet, reloading the shopping cart...")
            self.wait_for_timeout(reload_every_seconds * 1000)
            waited_seconds += reload_every_seconds + 15
            self.page.reload(wait_until="load")

    # ---------------- Cart item information (Item/Service name & Specification, UoM, Qty., Prices) ----------------

    def get_cart_item_row(self, requisition_number, item_code):
        # Cart row of this requisition and agreement item, e.g. REQ20260019046 and FWI044809
        return self.page.locator("tr").filter(
            has=self.page.locator("a.item-requisition-link", has_text=requisition_number)
        ).filter(has_text=f"[{item_code}]").first

    def read_cart_item(self, item_row):
        # Columns: SL | Image | Item/Service name & Specification | UoM | Qty. | Unit Price | Total Price | Remove
        cells = item_row.locator("td")
        framework_link = item_row.locator("a.item-framework-link")
        # Specification: the lines between "([item code] - product)" and "Remarks:"
        item_lines = [line.strip() for line in cells.nth(2).inner_text().splitlines() if line.strip()]
        start = next(index for index, line in enumerate(item_lines) if line.startswith("(["))
        end = next((index for index, line in enumerate(item_lines) if line.startswith("Remarks")), len(item_lines))
        quantity_input = cells.nth(4).locator("input:visible")
        quantity = quantity_input.first.input_value() if quantity_input.count() else cells.nth(4).inner_text()
        return {
            "FA No.": framework_link.get_attribute("data-framework-number"),
            "FA link text": framework_link.inner_text().strip(),
            "Specification": " ".join(item_lines[start + 1:end]),
            "UoM": cells.nth(3).inner_text().strip(),
            "Qty.": quantity.strip(),
            "Unit Price": cells.nth(5).inner_text().replace("BDT", "").strip(),
            "Total Price": cells.nth(6).inner_text().replace("BDT", "").strip(),
        }

    def open_cart_item_framework_document(self, item_row):
        # The FA link opens the Framework Agreement document in a new tab
        with self.page.context.expect_page() as new_page_info:
            item_row.locator("a.item-framework-link").click()
        document_tab = new_page_info.value
        document_tab.wait_for_load_state("domcontentloaded")
        return document_tab

    # ---------------- Cart item links, attachment and quantity (order creation journey) ----------------

    def select_vendor_keep_only_requisition(self, vendor_name, requisition_number, max_attempts_per_requisition=3):
        # Select the vendor and keep only this requisition ticked; works with any number of requisitions in the
        # shopping cart (business data). Each untick reloads the cart, so the click does not wait for that reload.
        radio_button = self.page.locator(
            f"//div[starts-with(@id,'vendorContainer')]//label[contains(., '{vendor_name}')]"
            f"/preceding-sibling::input[@type='radio']").first
        expect(radio_button, f"Vendor '{vendor_name}' not found in the shopping cart").to_be_visible(timeout=60000)
        expect(radio_button).to_be_enabled(timeout=60000)
        self.page.wait_for_load_state("load")
        if radio_button.is_checked():
            # Vendor already selected when the cart opens: fire its change event to load the vendor's items
            radio_button.dispatch_event("change")
        else:
            radio_button.check(no_wait_after=True)
        self.page.wait_for_load_state("load", timeout=60000)
        expect(self.visible_item_quantity.first).to_be_visible(timeout=60000)
        print(f"Selected vendor: {vendor_name}")

        requisition_checkboxes = self.page.locator(
            "//input[@type='checkbox'][following-sibling::label/strong]")
        attempts = {}
        while True:
            self.page.wait_for_load_state("load", timeout=60000)
            ticked_others = []
            for index in range(requisition_checkboxes.count()):
                checkbox = requisition_checkboxes.nth(index)
                number = " ".join(checkbox.locator("xpath=following-sibling::label/strong").first.inner_text().split())
                if number != requisition_number and checkbox.is_checked():
                    ticked_others.append(number)
            if not ticked_others:
                break
            other_number = ticked_others[0]
            attempts[other_number] = attempts.get(other_number, 0) + 1
            assert attempts[other_number] <= max_attempts_per_requisition,                 f"Requisition {other_number} is still ticked after {max_attempts_per_requisition} attempts"
            other_checkbox = self.page.locator(
                f"//label[strong[normalize-space(text())='{other_number}']]/preceding-sibling::input[@type='checkbox']")
            other_checkbox.click(no_wait_after=True)
            try:
                expect(other_checkbox).not_to_be_checked(timeout=30000)
            except AssertionError:
                print(f"Requisition {other_number} not unticked yet, checking again")
            self.page.wait_for_load_state("load", timeout=60000)
            print(f"Unticked requisition: {other_number}")

        own_checkbox = self.page.locator(
            f"//label[strong[normalize-space(text())='{requisition_number}']]/preceding-sibling::input[@type='checkbox']")
        expect(own_checkbox, f"Requisition {requisition_number} must stay ticked").to_be_checked(timeout=30000)
        expect(self.visible_item_quantity.first).to_be_visible(timeout=60000)
        print(f"Only requisition {requisition_number} is ticked for vendor {vendor_name}")
        return True

    def get_requisition_cart_rows(self, requisition_number):
        # Cart rows (items) of the requisition: innermost item rows only (the vendor's items can be inside
        # an outer table row after the vendor selection)
        rows = self.page.locator("tr:has(span.product-remarks):not(:has(tr))").filter(
            has=self.page.locator("a.item-requisition-link", has_text=requisition_number))
        expect(rows.first).to_be_visible(timeout=30000)
        return [rows.nth(index) for index in range(rows.count())]

    @staticmethod
    def get_cart_item_id(item_row):
        # Cart item id, e.g. 19566 from <span id="remarkSpan19566">
        return re.sub(r"\D", "", item_row.locator("span.product-remarks").first.get_attribute("id") or "")

    def get_cart_item_cell(self, item_row):
        # Item/Service name & Specification cell: the td with the requisition link
        # (found by content: the column position changes after the vendor selection)
        return item_row.locator("td").filter(has=self.page.locator("a.item-requisition-link")).first

    def read_cart_item_cell(self, item_row):
        # Item/Service name & Specification cell, UoM, Qty. and prices of a cart row
        cell = self.get_cart_item_cell(item_row)
        heading = " ".join((cell.locator("span").first.inner_text() or "").split())
        requisition_link = cell.locator("a.item-requisition-link")
        agreement_item_link = cell.locator('a[target="_blank"]').first
        attachment_icon = cell.locator("i.item-attachment-link")
        item_lines = [line.strip() for line in cell.inner_text().splitlines() if line.strip()]
        start = next(index for index, line in enumerate(item_lines) if line.startswith("(["))
        end = next((index for index, line in enumerate(item_lines) if line.startswith("Remarks")), len(item_lines))
        item_id = self.get_cart_item_id(item_row)
        quantity_input = self.page.locator(f"#itemquantity{item_id}")
        quantity = quantity_input.input_value() if quantity_input.is_visible() else \
            self.page.locator(f"#quantitySpan{item_id}").inner_text()
        cart_item = {
            "Master item": heading.split(" - ")[0].strip(),
            "Requisition": " ".join(requisition_link.inner_text().split()),
            "Requisition ERP URL": requisition_link.get_attribute("data-url"),
            "FA No.": cell.locator("a.item-framework-link").get_attribute("data-framework-number"),
            "Agreement item code": (agreement_item_link.get_attribute("href") or "").strip("/"),
            "Agreement item name": " ".join(agreement_item_link.inner_text().split()),
            "Specification": " ".join(item_lines[start + 1:end]),
            "Remarks": " ".join(cell.locator("span.product-remarks").inner_text().split()),
            "Attachment path": attachment_icon.first.get_attribute("data-attachment-path") if attachment_icon.count() else "",
            "UoM": " ".join(item_row.locator("span.sku").first.inner_text().split()),
            "Qty.": quantity.strip(),
            "Unit Price": item_row.locator("span.product-unit-price").inner_text().replace("BDT", "").strip(),
            "Total Price": item_row.locator("span.product-subtotal").inner_text().replace("BDT", "").strip(),
        }
        print(f"Cart item: {cart_item}")
        return cart_item

    @staticmethod
    def cart_requisition_link(item_row):
        # Why: the requisition link of a cart item can open 1 or 2 ERP tabs; When: link checks that close every tab
        return item_row.locator("a.item-requisition-link").first

    def open_cart_requisition_link(self, item_row):
        # Requisition number link: opens the ERP requisition details in a new tab
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(item_row.locator("a.item-requisition-link"))
        requisition_tab = new_tab_info.value
        requisition_tab.wait_for_load_state("domcontentloaded")
        return requisition_tab

    def open_cart_agreement_item(self, item_row):
        # Agreement item name link: opens the item details page in a new tab
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(self.get_cart_item_cell(item_row).locator('a[target="_blank"]').first)
        item_tab = new_tab_info.value
        item_tab.wait_for_load_state("domcontentloaded")
        return item_tab

    def download_cart_attachment(self, item_row, save_folder):
        # Why: check the cart item attachment without showing the file in the browser; When: cart attachment checks
        return self.save_attachment_from_icon(item_row.locator("i.item-attachment-link").first, save_folder)

    def remove_cart_attachment(self, item_row):
        # Remove the item attachment: the remove link opens a confirmation pop-up;
        # store its text, click Yes and return the confirmation text
        item_id = self.get_cart_item_id(item_row)
        self.click_on_btn(self.page.locator(f"#itemAttachmentRemove{item_id}"))
        yes_button = self.attachment_remove_yes_button.first
        expect(yes_button, "Attachment remove confirmation pop-up not shown").to_be_visible(timeout=15000)
        confirmation_popup = yes_button.locator("xpath=ancestor::div[2]")
        confirmation_text = " ".join(confirmation_popup.inner_text().split())
        self.click_on_btn(yes_button)
        # The attachment icon is hidden (not deleted) after the remove
        expect(item_row.locator("i.item-attachment-link").first).to_be_hidden(timeout=15000)
        print(f"Cart attachment removed: {confirmation_text}")
        return confirmation_text

    def upload_cart_item_attachment(self, item_row, file_path):
        # Upload a new attachment for the cart item and confirm it
        item_id = self.get_cart_item_id(item_row)
        self.page.locator(f"#itemAttachment{item_id}").set_input_files(str(file_path))
        self.click_on_btn(self.confirm_button.first)
        expect(item_row.locator("i.item-attachment-link").first).to_be_visible(timeout=30000)
        print(f"Cart attachment uploaded: {file_path}")

    def update_cart_item_quantity(self, item_row, quantity):
        # New Qty. of the cart item and Update shopping cart
        item_id = self.get_cart_item_id(item_row)
        quantity_input = self.page.locator(f"#itemquantity{item_id}")
        quantity_input.fill("")
        self.input_in_element(quantity_input, quantity)
        self.click_on_btn(self.update_shopping_cart)
        self.page.wait_for_load_state("load")
        self.wait_for_timeout(3000)
        print(f"Cart item {item_id} quantity updated to {quantity}")

    def fill_cart_item_remarks(self, item_row, remarks):
        # New remarks of the cart item (0 to 500 characters); saved with Update shopping cart
        item_id = self.get_cart_item_id(item_row)
        remarks_input = self.page.locator(f"#itemRemarks{item_id}")
        remarks_input.fill(remarks)
        print(f"Cart item {item_id} remarks: {remarks}")

    def get_cart_item_remarks_input(self, item_row):
        # Text in the remarks field of the cart item
        item_id = self.get_cart_item_id(item_row)
        return self.page.locator(f"#itemRemarks{item_id}").input_value()
