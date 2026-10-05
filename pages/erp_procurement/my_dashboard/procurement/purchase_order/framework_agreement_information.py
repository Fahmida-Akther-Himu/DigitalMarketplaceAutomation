from playwright.sync_api import expect
import re
import os
from utils.basic_actionsdm import BasicActionsDM
from datetime import datetime


class FrameworkAgreementInformation(BasicActionsDM):

    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger

        self.start_date = page.locator('input[id="startDate"]')
        self.start_date_picker = page.locator('#startDate + img.ui-datepicker-trigger')
        self.end_date = page.locator('input[id="endDate"]')
        self.end_date_picker = page.locator('#endDate + img.ui-datepicker-trigger')
        self.price_review_date = page.locator('input[id="priceReviewDate"]')
        self.price_review_date_picker = page.locator('#priceReviewDate + img.ui-datepicker-trigger')
        self.current_date = page.locator('.ui-datepicker-calendar .ui-state-highlight')

        self.month_selector = page.locator('#ui-datepicker-div select.ui-datepicker-month')
        self.year_selector = page.locator('#ui-datepicker-div select.ui-datepicker-year')

        # Applicable For radio buttons (value 3 = Both, 1 = HO, 2 = HCMP)
        self.applicable_for_both = page.locator("input[type='radio'][name='hubApplicableForId'][value='3']")
        self.applicable_for_ho = page.locator("input[type='radio'][name='hubApplicableForId'][value='1']")
        self.applicable_for_hcmp = page.locator("input[type='radio'][name='hubApplicableForId'][value='2']")
        # or,
        # self.applicable_for_both = page.locator("//input[@type='radio' and @name='hubApplicableForId' and @value='3']")
        # self.applicable_for_ho = page.locator("//input[@type='radio' and @name='hubApplicableForId' and @value='1']")
        # self.applicable_for_hcmp = page.locator("//input[@type='radio' and @name='hubApplicableForId' and @value='2']")

        self.upload_file_input = page.locator("input#faDocInput")
        self.upload_browse_button = page.locator("#selector-faDocInput span.ui-button")
        self.uploaded_attachment_name = page.locator("#faDocUpload")

        self.upload_excel_input = page.locator("input#faExcelInput")
        self.upload_button = page.locator("#selector-faExcelInput span.ui-button")

        self.remarks = page.locator('textarea[id="remarks"][placeholder="Max length 250"]')

        self.update_and_next_button = page.locator('input[id="save-button-framework"][value="Update & Next >>"]')
        self.table_rows = page.locator("#frameworkDetailsGrid tr.jqgrow")
        self.rows = page.locator("#frameworkDetailsGrid tr.jqgrow")
        self.editable_unit_price_locator = page.locator('[class="numericUnitPrice"][id^="unitPrice"]')

        self.recommender_checkbox = page.locator('input[id="isRecommender"]')
        self.recommender_textbox = page.locator('[id="recommenderIdDiv_input"]')
        self.recommender_dropdown_arrow = page.locator('[id="recommenderIdDiv_arrow"]')

        self.approver_textbox = page.locator('[id="signatoryMemberDiv_input"]')
        self.approver_dropdown_arrow = page.locator('[id="signatoryMemberDiv_arrow"]')

        self.update_button = page.locator('[type="button"][Value="Update"]')
        self.submit_button = page.locator('[type="button"][id="submit-button-letterBody"][Value="Submit"]')
        # self.submit_confirmation_button = page.locator("#dialog-confirm-frameworkSubmit >> button:has-text('Submit')")
        self.submit_confirmation_button = page.locator(
            "div.ui-dialog-buttonpane.ui-widget-content.ui-helper-clearfix >> button:has-text('Submit')")
        self.cancel_button = page.locator("#dialog-confirm-frameworkSubmit >> button:has-text('Cancel')")
        self.agreement_submission_message = page.locator(
            "#jGrowl .jGrowl-notification.success .message"
        )
        self.agreement_status_message = page.locator(
            ".jGrowl-notification.success .message"
        )
        self.moq_entry = page.locator('[id^="quantity"]')
        # Amendment edit page: page messages and the item Specification/TOR popup
        self.page_messages = page.locator("#jGrowl .jGrowl-notification .message")
        self.specification_popup_textarea = page.locator("#fancybox-content textarea").first
        self.specification_popup_add_to_grid = page.locator("#fancybox-content").get_by_role(
            "button", name="Add to Grid")
        # Confirmation popup (Update & Next / Submit Confirmation)
        self.confirmation_popup = page.locator(".ui-dialog:visible").last

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def modify_item_unit_price(self, unit_price):
        self.editable_unit_price_locator.first.click()
        self.editable_unit_price_locator.first.clear()
        self.input_in_element(self.editable_unit_price_locator.first, unit_price)
        # self._log(self.editable_unit_price_locator.first, unit_price)

    def modify_agreement_moq(self, value):
        self.moq_entry.first.click()
        self.moq_entry.first.clear()
        self.input_in_element(self.moq_entry.first, value)

    def print_item_details(self):
        rows = self.page.locator("#frameworkDetailsGrid tr.jqgrow")

        row_count = rows.count()
        print("Rows: ", row_count)
        # if row_count == 0:
        #     print("No items found in the grid.")
        #     return
        #
        # for i in range(row_count):
        #     row = rows.nth(i)
        #     # print("Total item count: " + row)
        #
        #     item_name = self.page.locator('a[id^="itemLink"]').inner_text().strip()
        #     # item_name = self.page.locator("td[aria-describedby='frameworkDetailsGrid_itemName']").inner_text().strip()
        #     # spec = self.row.locator("td[aria-describedby='frameworkDetailsGrid_itemSpecification']").inner_text().strip()
        #     # uom = self.row.locator("td[aria-describedby='frameworkDetailsGrid_uom']").inner_text().strip()
        #     # unit_price = self.row.locator("td[aria-describedby='frameworkDetailsGrid_unitPrice']").input_value()
        #     # moq = self.row.locator("td[aria-describedby='frameworkDetailsGrid_moq']").input_value()
        #
        #     print(f"\nRow {i + 1}")
        #     print(f"Item Name: {item_name}\n")
        # print(f"Specification: {spec}")
        # print(f"UoM: {uom}")
        # print(f"Unit Price: {unit_price}")
        # print(f"MOQ: {moq}")

    def print_table_data(self, only_status=False):
        rows = self.table_rows.all()

        if not rows:
            print("No records found in the table")
            return

        for idx, row in enumerate(rows, start=1):
            # Extract all cell texts inside the row
            cells = row.locator("td").all()

            if only_status:
                # Example: status cell might be the 'action' column with Reject button
                # Modify this selector if your status column is different
                status_cell = row.locator("td[aria-describedby='frameworkDetailsGrid_action']")
                if status_cell.count() > 0:
                    print(f"Row {idx} Status:", status_cell.inner_text())
                else:
                    print(f"Row {idx} Status: N/A")
            else:
                # Print complete row text
                row_text = row.inner_text().replace("\n", " | ")
                print(f"Row {idx}: {row_text}")

    def select_start_date(self):
        """
                Selects the current date in the price review date picker.
                Handles cases where the date picker opens in past or future months/years.
                """
        # Open the date picker
        self.start_date_picker.click()

        # Get today's month/year
        today = datetime.today()
        current_month = today.strftime("%b")  # e.g., "Nov"
        current_year = str(today.year)

        # Ensure the calendar is showing the current month/year
        selected_month = self.month_selector.input_value()
        selected_year = self.year_selector.input_value()

        if selected_month != current_month or selected_year != current_year:
            # Select the correct month and year from dropdowns
            self.month_selector.select_option(label=current_month)
            self.year_selector.select_option(current_year)

        # Now click the current day (highlighted date)
        if self.current_date.is_visible():
            self.current_date.click()
        else:
            # fallback if "today" highlight not visible — find by number
            today_day = str(today.day)
            self.page.locator(f'//td/a[text()="{today_day}"]').click()

        # Optional: wait for picker to close or field to update
        self.wait_for_timeout(1000)

    def select_end_date(self):
        # Open the date picker
        self.end_date_picker.click()

        # Get current year and month
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Target: 5 years later
        target_year = current_year + 5
        target_month = current_month

        # Wait to ensure the picker is ready
        self.wait_for_timeout(1000)

        # Select year and month
        self.year_selector.select_option(str(target_year))
        self.month_selector.select_option(str(target_month - 1))  # 0-indexed in jQuery UI

        # Select the same day (or first day if not available)
        current_day = datetime.now().day
        day_locator = self.page.locator(
            f"//table[contains(@class,'ui-datepicker-calendar')]//a[text()='{current_day}']"
        )
        if day_locator.count() > 0:
            day_locator.first.click()
        else:
            # fallback: select first available date
            self.page.locator("//table[contains(@class,'ui-datepicker-calendar')]//a").first.click()

        self.wait_for_timeout(1000)

    def select_price_review_date(self):
        """
                Selects the current date in the price review date picker.
                Handles cases where the date picker opens in past or future months/years.
                """
        # Open the date picker
        self.price_review_date_picker.click()

        # Get today's month/year
        today = datetime.today()
        current_month = today.strftime("%b")  # e.g., "Nov"
        current_year = str(today.year)

        # Ensure the calendar is showing the current month/year
        selected_month = self.month_selector.input_value()
        selected_year = self.year_selector.input_value()

        if selected_month != current_month or selected_year != current_year:
            # Select the correct month and year from dropdowns
            self.month_selector.select_option(label=current_month)
            self.year_selector.select_option(current_year)

        # Now click the current day (highlighted date)
        if self.current_date.is_visible():
            self.current_date.click()
        else:
            # fallback if "today" highlight not visible — find by number
            today_day = str(today.day)
            self.page.locator(f'//td/a[text()="{today_day}"]').click()

        # Optional: wait for picker to close or field to update
        self.wait_for_timeout(1000)

    def upload_framework_document(self, file_path):
        print(f"Uploading file from : {file_path}")
        if os.path.exists(file_path):
            uploaded_file_name = self.upload_attachment_file(self.upload_file_input, file_path)
            # uploaded_file_name = self.upload_attachment_file(self.upload_browse_button, file_path)
            print(f"Uploaded file name: {uploaded_file_name}")
        else:
            print(f"File not found at path: {file_path}")

    def upload_excel_document(self, file_path):
        print(f"Uploading file from : {file_path}")
        if os.path.exists(file_path):
            uploaded_excel_file_name = self.upload_attachment_file(self.upload_excel_input, file_path)
            print(f"Uploaded excel file name: {uploaded_excel_file_name}")
        else:
            print(f"Excel file not found at path: {file_path}")

    def enter_remarks(self, remarks):
        self.remarks.click()
        self.remarks.clear()
        self.input_in_element(self.remarks, remarks)
        self.wait_for_timeout(2000)

    def update_agreement(self) -> str:
        self.update_and_next_button.click()

        # Wait for toast message to appear
        self.agreement_status_message.wait_for(state="visible", timeout=15000)

        status_value = self.agreement_status_message.text_content()

        # agreement_status = status_value.split("Agreement Number:")[-1].strip()

        print("Updated agreement status: " + status_value)
        # logger.step(message)

        return status_value

    def amended_agreement_submission(self):
        # Click main submit
        self.submit_button.click()

        # Wait for confirmation dialog and confirm
        self.wait_to_load_element(self.submit_confirmation_button)
        self.submit_confirmation_button.click()
        # Wait for toast message to appear
        self.agreement_status_message.wait_for(state="visible", timeout=15000)

        submitted_status_value = self.agreement_status_message.text_content()

        # agreement_status = status_value.split("Agreement Number:")[-1].strip()

        print("Submitted agreement status: " + submitted_status_value)
        # logger.step(message)

        return submitted_status_value

    def recommender_selection(self, agreement_recommender):
        self.recommender_dropdown_arrow.click()
        self.recommender_textbox.click()
        self.recommender_textbox.clear()
        self.character_input(self.recommender_textbox, agreement_recommender)
        self.page.get_by_text(agreement_recommender).click()
        # self.wait_to_load_element(2000)

    def approver_selection(self, agreement_approver):
        self.approver_dropdown_arrow.click()
        self.approver_textbox.click()
        self.approver_textbox.clear()
        self.character_input(self.approver_textbox, agreement_approver)
        self.page.get_by_text(agreement_approver).click()
        # self.wait_to_load_element(2000)

    def amended_agreement_submission_1(self) -> str:
        self.submit_button.click()
        self.wait_to_load_element(self.submit_confirmation_button)
        self.submit_confirmation_button.click()
        self.wait_to_load_element(self.agreement_submission_message)
        value = self.agreement_submission_message.text_content()
        return value.split(' ')[-1]

    def recommender_checkbox_selection(self):
        """
        Checks the current status of recommender checkbox,
        clicks ONLY if it's unchecked, otherwise just prints status.
        """

        self._log("Recommender selection started")
        print("Recommender selection started..")

        # Ensure the checkbox is visible before interacting
        # self.recommender_checkbox.wait_for(state="visible")

        # Check current state
        is_checked = self.recommender_checkbox.is_checked()
        status = "CHECKED" if is_checked else "UNCHECKED"

        # Print & log current status
        print(f"Recommender checkbox is currently: {status}")

        if self.logger:
            self.logger.info(f"Recommender checkbox status before action: {status}")

        # CONDITIONAL ACTION
        if not is_checked:
            print("Checkbox is UNCHECKED → Clicking now...")
            self.recommender_checkbox.click()

            # Verify new state after click
            new_state = self.recommender_checkbox.is_checked()
            new_status = "CHECKED" if new_state else "UNCHECKED"

            print(f"Recommender checkbox status after click: {new_status}")

            if self.logger:
                self.logger.info(f"Recommender checkbox status after click: {new_status}")

        else:
            # If already checked → DO NOT CLICK
            print("Checkbox is already CHECKED → No action needed")

            if self.logger:
                self.logger.info("Recommender checkbox already CHECKED → No action taken")

    def recommender_checkbox_selection_1(self):
        """
        Checks the current status of recommender checkbox,
        prints the status, and toggles it.
        """

        self._log("Recommender selection started")
        print("Recommender selection started..")  # Console print

        # Ensure the checkbox is visible before interacting
        self.recommender_checkbox.wait_for(state="visible")

        # Check current state
        is_checked = self.recommender_checkbox.is_checked()

        # Print & log current status
        status = "CHECKED" if is_checked else "UNCHECKED"
        print(f"Recommender checkbox is currently: {status}")

        if self.logger:
            # self.logger.step(f"Recommender checkbox status before click: {status}")
            print(f"Recommender checkbox status before click: {status}")
            self.logger.info(f"Recommender checkbox status before click..: {status}")

        # Toggle checkbox
        self.recommender_checkbox.click()

        # Verify new state after click
        new_state = self.recommender_checkbox.is_checked()
        new_status = "CHECKED" if new_state else "UNCHECKED"

        print(f"Recommender checkbox status after click: {new_status}")
        # self.logger.step(f"Recommender checkbox status after click: {new_status}")

        if self.logger:
            # self.logger.step(f"Recommender checkbox status after click: {new_status}")
            # print(f"Recommender checkbox status after click: {new_status}")
            self.logger.info(f"Recommender checkbox status after click: {new_status}")

    def get_fwa_no(self):
        # Edit page loaded (Update & Next >> shown): FWA No. is the read-only input holding the FA number
        self.update_and_next_button.wait_for(state="visible", timeout=30000)
        input_values = self.page.locator("input[type='text'], input:not([type])").evaluate_all(
            "inputs => inputs.map(input => input.value.trim()).filter(value => /\\/FA-\\d+/.test(value))")
        fwa_no = input_values[0] if input_values else ""
        print(f"FWA No. on the amendment page: {fwa_no}")
        return fwa_no

    # ---------------- Amendment edit page: header and item updates ----------------

    def pick_date(self, date_picker_icon, date_field, target_date):
        # Date picker: select year, month and day. Returns the date shown in the field,
        # or None when the day is disabled in the date picker.
        date_picker_icon.click()
        self.year_selector.select_option(str(target_date.year))
        self.month_selector.select_option(str(target_date.month - 1))  # jQuery UI months start at 0
        day_link = self.page.locator(
            f"#ui-datepicker-div td:not(.ui-state-disabled) a:text-is('{target_date.day}')")
        if not day_link.count():
            self.page.keyboard.press("Escape")
            return None
        day_link.first.click()
        self.wait_for_timeout(1500)
        return date_field.input_value().strip()

    def get_visible_message(self):
        # Validation/notification message shown on the page (jGrowl), if any
        messages = [text.strip() for text in self.page_messages.all_inner_texts() if text.strip()]
        return messages[-1] if messages else ""

    def get_selected_applicable_for(self):
        for label, radio in (("Both", self.applicable_for_both), ("HO", self.applicable_for_ho),
                             ("HCMP", self.applicable_for_hcmp)):
            if radio.is_checked():
                return label
        return ""

    def select_applicable_for_both(self):
        self.applicable_for_both.check()
        self.wait_for_timeout(1000)
        return self.get_selected_applicable_for()

    def upload_amendment_attachment(self, file_path):
        # Add Attachment / Browse: select the file and confirm it is selected
        self.upload_file_input.set_input_files(file_path)
        # Uploaded file name saved by the system, e.g. 1791111020002.upload_file.pdf
        expect(self.uploaded_attachment_name).not_to_have_value("", timeout=30000)
        selected_file = self.uploaded_attachment_name.input_value().strip()
        print(f"Amendment attachment selected: {selected_file}")
        return selected_file

    def get_item_row(self, item_code):
        # Item row of the stored item (matched by its item code, e.g. [FWI044746])
        item_row = self.rows.filter(has_text=item_code).first
        item_row.wait_for(state="visible", timeout=30000)
        return item_row

    def update_item_specification(self, item_row, item_code, new_specification=None):
        # Item/Sub-Category Name > Specification/TOR popup > (replace specification) > Add to Grid
        item_row.locator("a", has_text=item_code).first.click()
        self.specification_popup_textarea.wait_for(state="visible", timeout=15000)
        if new_specification is not None:
            self.specification_popup_textarea.fill("")
            self.specification_popup_textarea.fill(new_specification)
        final_specification = self.specification_popup_textarea.input_value().strip()
        self.get_screen_shot('amendment_item_specification_popup')
        self.specification_popup_add_to_grid.click()
        self.specification_popup_textarea.wait_for(state="hidden", timeout=10000)
        return final_specification

    def get_item_price_fields(self, item_row):
        # MRP Price and Discount(%) inputs (MRP pricing) or the Unit Price input (direct pricing)
        mrp_discount_inputs = item_row.locator(
            "input[type='text']:visible:not([id^='unitPrice']):not([id^='quantity'])")
        unit_price_input = item_row.locator("input[id^='unitPrice']:visible")
        if mrp_discount_inputs.count() >= 2:
            return {"mode": "MRP + Discount", "mrp": mrp_discount_inputs.nth(0),
                    "discount": mrp_discount_inputs.nth(1), "unit_price": None}
        return {"mode": "Unit Price", "mrp": None, "discount": None, "unit_price": unit_price_input.first}

    def set_input_value(self, input_field, value):
        # Clear and type the value like a user (the item grid keeps only typed values)
        input_field.click()
        input_field.fill("")
        input_field.press_sequentially(value, delay=100)
        input_field.press("Tab")
        self.wait_for_timeout(1500)

    def get_item_unit_price(self, item_row, price_fields):
        # Unit Price shown by the system (input for direct pricing, calculated cell for MRP pricing)
        if price_fields["unit_price"] is not None:
            return price_fields["unit_price"].input_value().strip()
        return item_row.locator("td[aria-describedby$='_unitPrice']").inner_text().strip()

    def get_item_moq_input(self, item_row):
        return item_row.locator("input[id^='quantity']").first

    # ---------------- Output Document: confirmation, Recommender, Approver, Submit ----------------

    def confirm_visible_popup(self):
        # Confirmation popup (jQuery UI dialog): returns its message after clicking the confirm button
        if not self.confirmation_popup.count():
            return ""
        popup_message = self.confirmation_popup.locator(".ui-dialog-content").inner_text().strip()
        self.confirmation_popup.locator(".ui-dialog-buttonpane button").first.click()
        self.wait_for_timeout(2000)
        return popup_message

    def is_output_document_page_opened(self):
        # Output Document page loaded: Approver field shown
        try:
            self.approver_textbox.wait_for(state="visible", timeout=60000)
        except Exception:
            return False
        self.wait_for_timeout(2000)
        return True

    def ensure_recommender_checked(self):
        # Select the Recommender checkbox only if it is not selected (clicking again would deselect it)
        was_checked = self.recommender_checkbox.is_checked()
        if not was_checked:
            self.recommender_checkbox.check()
            self.wait_for_timeout(1000)
        print(f"Recommender checkbox: {'already selected' if was_checked else 'selected now'}")
        return was_checked

    def select_user_by_pin(self, user_textbox, user_pin):
        # Clear the field, type the PIN and select the exact suggestion of this PIN
        user_textbox.click()
        user_textbox.fill("")
        user_textbox.fill(user_pin[:-1])
        user_textbox.press_sequentially(user_pin[-1])
        user_suggestion = self.page.get_by_text(re.compile(rf"\[{re.escape(user_pin)}\]")).locator("visible=true").first
        user_suggestion.wait_for(state="visible", timeout=15000)
        user_suggestion.click()
        self.wait_for_timeout(2000)
        selected_user = user_textbox.input_value().strip()
        print(f"Selected user for {user_pin}: {selected_user}")
        return selected_user

    def submit_with_confirmation(self):
        # Submit > Submit Confirmation popup (message) > Submit > final notification
        self.submit_button.click()
        self.submit_confirmation_button.wait_for(state="visible", timeout=15000)
        submit_confirmation_message = self.confirmation_popup.locator(".ui-dialog-content").inner_text().strip()
        print(f"Submit confirmation message: {submit_confirmation_message}")
        self.submit_confirmation_button.click()
        self.agreement_status_message.wait_for(state="visible", timeout=30000)
        final_submission_message = " ".join(self.agreement_status_message.last.inner_text().split())
        print(f"Final submission message: {final_submission_message}")
        return submit_confirmation_message, final_submission_message
