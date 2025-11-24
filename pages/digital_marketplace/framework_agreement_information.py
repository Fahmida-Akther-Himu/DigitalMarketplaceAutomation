import re
import os
from utils.basic_actionsdm import BasicActionsDM
from datetime import datetime


class FrameworkAgreementInformation(BasicActionsDM):

    def __init__(self, page):
        super().__init__(page)

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
