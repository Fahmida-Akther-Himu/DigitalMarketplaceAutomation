from urllib.parse import unquote
import re
from pages.digital_marketplace.public_side.shopping_cart import ShoppingCart
from utils.basic_actionsdm import BasicActionsDM
# from pages.digital_marketplace.home_page import HomePage
from datetime import datetime, timedelta
from playwright.sync_api import expect


class CheckoutPage(ShoppingCart, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        # prepare the delivery schedule
        # self.schedule_quantity = page.locator('input[type="number"]')
        self.fractional_schedule_quantity = page.locator('input[type="text"][id^="quantity"]')
        self.schedule_expected_date = page.locator('input[type="date"][class="todayDate"]')
        self.schedule_expected_location = page.locator('input[id^="location"]')
        self.schedule_receiving_person_pin = page.locator('input[id^="deliveryInfo"]')
        # Auto Generate schedule button and Receiving Person of the auto generated schedule row
        self.auto_generate_button = page.get_by_role("button", name="Auto Generate")
        self.generated_schedule_receiving_person = page.locator(
            'tr:has(button.removeScheduleButton) input[type="text"]').last
        # Receiving Person of all auto generated schedule rows (one row per item)
        self.generated_schedule_receiving_persons = page.locator(
            'tr:has(button.removeScheduleButton) input[type="text"]')

        # self.click_add_schedule_button = page.locator('button[id^="addScheduleButton"]')
        self.click_add_schedule_button = page.locator('button[id^="addScheduleButton"][class="button1"]')
        self.continue_button = page.locator('#chkContinue')

        # Confirm order window
        self.order_remarks = page.locator('#confirmOrderRemarks')
        self.checkbox = page.locator('#termsofservice')
        self.confirm_button = page.get_by_role("button", name="Confirm")
        self.view_order_details = page.locator("//a[contains(text(),'Click here for order details.')]")
        # self.view_order_details_another = page.locator("a", has_text="Click here for order details."||"div.details-link", has_text="Click here for order details.")

        # Review order locator
        self.schedule_delete_icon = page.locator('button[class="removeScheduleButton"]')
        self.schedule_edit_button = page.locator('button[class="editScheduleButton"][type="button"]')
        self.update_schedule_button = page.locator('button[id^="updateScheduleButton"][class="button1"]')
        self.preview_button = page.locator('a.print-order-button', has_text="Preview")
        # Requisition Schedule table of the Delivery Schedule step (Item, Quantity, Unit of Measure, ...)
        self.requisition_schedule_table = page.locator("table").filter(has_text="Unit of Measure").first
        self.item_attachment_icon = page.locator("i.fa-paperclip:visible")

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    # def update_quantity(self, quantity):
    #     self.schedule_quantity.clear()
    #     self.wait_for_timeout(3000)
    #     self.input_in_element(self.schedule_quantity, quantity)
    #     self.wait_for_timeout(3000)
    def fractional_schedule_update_quantity(self, delivery_schedule_quantity):
        self.fractional_schedule_quantity.first.clear()
        self.wait_for_timeout(3000)
        self.input_in_element(self.fractional_schedule_quantity.first, delivery_schedule_quantity)
        self.wait_for_timeout(3000)

    def update_expected_date(self):
        self.schedule_expected_date.first.click()
        expected_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.schedule_expected_date.first.fill(expected_date)
        self.wait_for_timeout(5000)
        print(f"Filled expected date with: {expected_date}")

    def delivery_schedule_preparation(self, location, pin):
        self.input_in_element(self.schedule_expected_location.first, location)
        self.page.wait_for_timeout(3000)
        self.input_in_element(self.schedule_receiving_person_pin.first, pin)
        self.page.keyboard.press('Enter')
        self.page.wait_for_timeout(5000)

    # concatenated
    def fillup_receiving_pin(self):
        pin_digits = ['0', '0', '0', '0', '6', '0', '0', '8']

        self.click_on_btn(self.schedule_receiving_person_pin)

        for digit in pin_digits:
            self.schedule_receiving_person_pin.type(digit)
            self.wait_for_timeout(200)
        # self.wait_for_timeout(5000)
        self.page.keyboard.press("Enter")
        self.wait_for_timeout(10000)

    def click_add_schedule_btn(self):
        self.click_on_btn(self.click_add_schedule_button.nth(0))
        # self.wait_for_timeout(5000)

    def click_continue(self):
        self.click_on_btn(self.continue_button)

    def auto_generate_schedule(self):
        self.click_on_btn(self.auto_generate_button)
        self.move_mouse_away()
        self.wait_for_timeout(3000)

    def fill_generated_schedule_receiving_person(self, pin):
        # Receiving Person of the auto generated schedule row
        self.input_in_element(self.generated_schedule_receiving_person, pin)
        self.page.keyboard.press('Enter')
        self.page.wait_for_timeout(5000)

    def click_continue_when_enabled(self):
        # Continue is enabled only after all delivery schedule information is complete
        expect(self.continue_button).to_be_visible(timeout=30000)
        expect(self.continue_button).to_be_enabled(timeout=30000)
        self.click_on_btn(self.continue_button)

    def fillup_order_remarks(self, input_remarks):
        self.click_on_btn(self.order_remarks)
        self.order_remarks.clear()
        self.input_in_element(self.order_remarks, input_remarks)
        self.wait_for_timeout(2000)

    def select_terms_of_service(self):
        self.click_on_btn(self.checkbox)
        # self.wait_for_timeout(2000)

    def confirm_order(self):
        self.click_on_btn(self.confirm_button)
        self.wait_for_timeout(5000)
        order_locator = self.page.locator("text=ORDER REFERENCE NO:").text_content()
        # self.wait_to_load_element(self.order_locator)
        order_reference_number = order_locator.split(":")[-1].strip()
        print("Order reference number: " + order_reference_number)
        return order_reference_number

    def goto_public_side_order_details_view(self):
        self.click_on_btn(self.view_order_details)
        self.wait_for_timeout(2000)
        order_status_pending = self.page.locator("text=Order Status:").text_content()
        order_status = order_status_pending.split(":")[-1].strip()
        print("Order status: " + order_status)
        return order_status

    def delivery_schedule_preparation_item_1(self, location, pin):
        self.click_on_btn(self.schedule_quantity.nth(0))
        self.click_on_btn(self.schedule_expected_date.nth(0))
        self.input_in_element(self.schedule_expected_location.nth(0), location)
        self.page.wait_for_timeout(5000)
        self.input_in_element(self.schedule_receiving_person_pin.nth(0), pin)
        self.page.keyboard.press('Enter')
        self.page.wait_for_timeout(5000)
        self.click_on_btn(self.click_add_schedule_button.nth(0))

    def delivery_schedule_preparation_item_2(self, location, pin):
        self.click_on_btn(self.schedule_quantity.nth(1))
        self.click_on_btn(self.schedule_expected_date.nth(1))
        self.input_in_element(self.schedule_expected_location.nth(1), location)
        self.page.wait_for_timeout(5000)
        self.input_in_element(self.schedule_receiving_person_pin.nth(1), pin)
        self.page.keyboard.press('Enter')
        self.page.wait_for_timeout(5000)
        self.click_on_btn(self.click_add_schedule_button.nth(1))

    # Use for delete review item
    def update_delivery_location_for_review_order_item_1(self):
        self.schedule_expected_location.nth(0).click()
        self.input_in_element(self.schedule_expected_location.nth(0), "Savar, Dhaka")
        self.schedule_receiving_person_pin.nth(0).click()

    def update_receiving_person_info_for_review_order(self, pin):
        self.input_in_element(self.schedule_receiving_person_pin.nth(0), pin)
        self.page.keyboard.press('Enter')
        self.page.wait_for_timeout(5000)
        self.click_on_btn(self.click_add_schedule_button.nth(0))

    def update_delivery_schedule_for_review_order(self):
        self.click_on_btn(self.schedule_quantity.nth(1))
        self.schedule_quantity.nth(1).clear()
        self.input_in_element(self.schedule_quantity.nth(1), "7")
        self.schedule_expected_date.nth(1).click()
        self.wait_for_timeout(5000)
        next_date = (datetime.strptime("2025-08-14", "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        self.schedule_expected_date.nth(1).fill(next_date)

    def update_delivery_location_for_review_order_item_2(self):
        self.schedule_expected_location.nth(1).click()
        self.schedule_expected_location.nth(1).clear()
        self.input_in_element(self.schedule_expected_location.nth(1), "Cumilla")

    def add_remaining_schedule_item_for_review_order(self, pin):
        self.input_in_element(self.schedule_expected_location.nth(1), "Rampura, Dhaka")
        self.page.wait_for_timeout(5000)
        self.input_in_element(self.schedule_receiving_person_pin.nth(1), pin)
        self.page.keyboard.press('Enter')
        self.page.wait_for_timeout(5000)

    def fillup_order_remarks_for_review_order(self):
        self.click_on_btn(self.order_remarks)
        self.order_remarks.clear()
        self.input_in_element(self.order_remarks, 'The initiator places the order for review again.')
        self.wait_for_timeout(2000)

    # ---------------- Delivery schedule and confirm order checks (order creation journey) ----------------

    def get_requisition_schedule_rows(self):
        # Requisition Schedule rows as {column title: cell text}
        expect(self.requisition_schedule_table).to_be_visible(timeout=30000)
        rows = self.requisition_schedule_table.locator("tr")
        headers = [" ".join(text.split()) for text in rows.first.locator("th, td").all_inner_texts()]
        schedule_rows = []
        for index in range(1, rows.count()):
            cells = [" ".join(text.split()) for text in rows.nth(index).locator("td").all_inner_texts()]
            if len(cells) >= len(headers):
                schedule_rows.append(dict(zip(headers, cells)))
        print(f"Requisition Schedule: {schedule_rows}")
        return schedule_rows

    def get_page_text(self):
        # Visible text of the checkout page on one line per element
        return " ".join(self.page.locator("body").inner_text().split())

    def download_checkout_attachment(self, save_folder, index=0):
        # Why: check an item attachment of the checkout without showing the file in the browser;
        # When: delivery schedule and confirm order attachment checks (index: the n-th attachment icon)
        return self.save_attachment_from_icon(self.item_attachment_icon.nth(index), save_folder)

    def open_checkout_framework_link(self, fa_no):
        # Framework Agreement link of the confirm order step: opens the agreement attachment in a new tab
        with self.page.context.expect_page() as new_tab_info:
            # FA No. has "/" (e.g. BPD/2026/FA-48): the link is found by its text
            self.click_on_btn(self.page.locator("a", has_text=fa_no).first)
        framework_tab = new_tab_info.value
        framework_tab.wait_for_load_state("domcontentloaded")
        return framework_tab

    def wait_for_confirm_order_step(self):
        # After Continue the Confirm order step loads ("Loading next step..."): wait for its order remarks field
        expect(self.order_remarks).to_be_visible(timeout=60000)
        self.wait_for_timeout(2000)

    def fill_all_generated_schedule_receiving_persons(self, pin):
        # Receiving Person of every auto generated schedule row (rows already filled are not changed);
        # returns the number of rows filled
        filled_rows = 0
        for index in range(self.generated_schedule_receiving_persons.count()):
            receiving_person = self.generated_schedule_receiving_persons.nth(index)
            if receiving_person.input_value().strip():
                continue
            self.input_in_element(receiving_person, pin)
            self.page.keyboard.press('Enter')
            self.page.wait_for_timeout(3000)
            filled_rows += 1
        print(f"Auto generated schedule rows filled with receiving person {pin}: {filled_rows}")
        return filled_rows

    def checkout_link(self, link_text, index=0):
        # Visible link of the checkout page by its text (requisition number, FA No., product name); index: the n-th
        # link with this text, used when items have the same product name
        return self.page.locator("a:visible", has_text=link_text).nth(index)

    def count_checkout_links(self, link_text):
        # Number of visible links with this text: used to open every product link when items share a product name
        return self.page.locator("a:visible", has_text=link_text).count()

    def has_checkout_link(self, link_text):
        return self.page.locator("a:visible", has_text=link_text).count() > 0

    def open_checkout_link_all_tabs(self, link_text, wait_after_ms=5000, index=0):
        # Why: checkout links (requisition, product) open 1 or 2 new tabs; When: the confirm order link checks
        # (index: the n-th link with this text); returns all new tabs
        return self.open_link_in_new_tabs(self.checkout_link(link_text, index), wait_after_ms)

    # ---------------- Confirm order: header, item rows and delivery schedules (order creation journey) ----------------

    def confirm_item_rows(self, requisition_number):
        # Why: the confirm order links and item details are checked row by row (top row first); When: confirm order
        # link and item checks. Item details rows with the requisition link (outer layout rows are not taken)
        return self.page.locator("tr:visible").filter(
            has=self.page.locator("a", has_text=requisition_number)).filter(
            has_text="Specification").filter(has_not=self.page.locator("tr")).all()

    @staticmethod
    def confirm_row_link(item_row, link_text):
        # Why: every item row has its own requisition, "FA:" and product links; When: opening the links of one row
        return item_row.locator("a", has_text=link_text).first

    @staticmethod
    def confirm_row_attachment_icon(item_row):
        # Why: the attachment of one item row (business rule: an item without attachment shows no icon; the hidden
        # icon of such a row is not counted); When: the attachment check of that row
        return item_row.locator("i.fa-paperclip:visible")

    def confirm_header_framework_link(self, fa_no):
        # Why: the order header Framework Agreement link (the item rows have "FA: ..." links with the same FA No.);
        # When: the first confirm order link checks
        return self.page.locator("a:visible", has_text=fa_no).filter(has_not_text="FA:")

    def read_confirm_item_row(self, item_row):
        # Why: the values of one item row by column title; When: confirm order item details checks
        headers = [" ".join(text.split())
                   for text in item_row.locator("xpath=ancestor::table[1]//tr[1]/*").all_inner_texts()]
        cells = [" ".join(text.split()) for text in item_row.locator("xpath=./td").all_inner_texts()]
        item = {}
        for header, cell in zip(headers, cells):
            name = next((key for key in ("Item/Service", "UoM", "Qty", "Unit Price", "Total Price")
                         if header.startswith(key)), header)
            item[name] = cell
        print(f"Confirm order item row: {item}")
        return item

    def read_confirm_order_header(self):
        # Why: the order header (agreement, vendor, requisition) of the confirm order step; When: confirm order
        # header checks. Returns {label: value} ("not found" when the label is not shown)
        labels = ("Framework Agreement", "Vendor Name", "Vendor Email Address", "Vendor Contact Number",
                  "Requisition No", "Requisition Date")
        any_label = "|".join(labels)
        page_text = self.get_page_text()
        header = {}
        for label in labels:
            match = re.search(rf"{label}\s*:\s*(.*?)\s*(?=(?:{any_label})\s*:|Item details|$)", page_text)
            header[label] = match.group(1) if match else "not found"
        print(f"Confirm order header: {header}")
        return header

    def get_confirm_schedule_rows(self):
        # Why: the Expected Delivery date and place rows of every item; When: confirm order delivery schedule checks.
        # Returns [{column title: cell text}]
        schedule_rows = []
        tables = self.page.locator("table:visible").filter(has_text="Receiver Info").filter(
            has_not=self.page.locator("table"))
        for table in tables.all():
            rows = table.locator("tr")
            headers = [" ".join(text.split()) for text in rows.first.locator("th, td").all_inner_texts()]
            for index in range(1, rows.count()):
                cells = [" ".join(text.split()) for text in rows.nth(index).locator("td").all_inner_texts()]
                if len(cells) >= len(headers):
                    schedule_rows.append(dict(zip(headers, cells)))
        print(f"Confirm order schedules: {schedule_rows}")
        return schedule_rows
