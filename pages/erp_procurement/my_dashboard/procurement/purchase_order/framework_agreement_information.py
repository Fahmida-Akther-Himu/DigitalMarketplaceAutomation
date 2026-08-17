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

        self.applicable_for_both = page.locator('#radio_both')
        self.applicable_for_ho = page.locator('#radio_ho')
        self.applicable_for_hcmp = page.locator('#radio_hcmp')
        # or,
        # self.applicable_for_both = page.locator("//input[@type='radio' and @name='hubApplicableForId' and @value='3']")
        # self.applicable_for_ho = page.locator("//input[@type='radio' and @name='hubApplicableForId' and @value='1']")
        # self.applicable_for_hcmp = page.locator("//input[@type='radio' and @name='hubApplicableForId' and @value='2']")

        self.upload_file_input = page.locator("input#faDocInput")
        self.upload_browse_button = page.locator("#selector-faDocInput span.ui-button")

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
