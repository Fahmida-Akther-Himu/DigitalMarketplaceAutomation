import os
import re
from urllib.parse import urljoin, unquote

from utils.basic_actionsdm import BasicActionsDM


class FrameworkInformation(BasicActionsDM):

    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger
        self.page = page
        self.vendor_info = page.locator('//*[@id="proposal-process"]/div[1]/div/div[4]/div/div/div[2]')
        self.agreement_date = page.locator('//*[@id="proposal-process"]/div[1]/div/div[6]/div[1]/div/div[2]')
        self.price_review_date = page.locator('//*[@id="proposal-process"]/div[1]/div/div[6]/div[2]/div/div[2]')
        self.from_date = page.locator('//*[@id="proposal-process"]/div[1]/div/div[8]/div[1]/div/div[2]')
        self.to_date = page.locator('//*[@id="proposal-process"]/div[1]/div/div[8]/div[2]/div/div[2]')
        self.agreement_attachment_icon = page.locator(
            '//*[@id="proposal-process"]/div[1]/div/div[12]/div[1]/div/div[2]/a/img')

        self.framework_item_details = page.locator(
            "//div[@class='col-lg-12 col-md-12 col-sm-12 label-new' and normalize-space(text())='Framework Item Details']")
        self.item_details_info = page.locator("div.content-new table.simple-table-css")

        self.comments = page.locator('textarea[id="comments"][placeholder="Max size of comments 300 characters"]')
        self.go_to_list_button = page.locator('input[type="button"][value="Go to List"]')
        self.amendment_button = page.locator('input[type="button"][id="amendment"]')
        self.success_message = page.locator("div#jGrowl div.jGrowl-notification.success div.message")
        # Item details popup (Item Name link): fancybox with Lead Time, Brand Name and Delivery Location
        self.item_popup = page.locator("#fancybox-wrap")
        self.item_popup_delivery_location = page.locator(
            "xpath=//div[@id='fancybox-content']//label[normalize-space(.)='Delivery Location']"
            "/following-sibling::div[contains(@class,'element-input')][1]")
        self.item_popup_close_button = page.locator("#fancybox-close")

        self.submit_button = page.locator('input[id="submit-button-invProcurementRequirement"][value="Submit"]')
        self.edit_button = page.locator('input[id="edit-button-invProcurementRequirement"][value="Edit"]')
        self.approve_button = page.locator('[id="approve"]')
        self.review_button = page.locator('[id="review"]')
        self.reject_button = page.locator('[id="reject"]')
        self.reject_with_noal_button = page.locator('[id="reject5"]')
        # self.comment_button = page.locator('textarea[id="comments"]')

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def get_vendor_info(self):
        self.vendor_info.click()
        vendor = self.vendor_info.inner_text()
        vendor_name = vendor.split(":")[0].strip()
        print("Requisition vendor name: " + vendor_name)
        return vendor_name

    def get_framework_information(self):
        self.agreement_date.click()
        framework_agreement_date = self.agreement_date.inner_text()
        print("Framework information: " + framework_agreement_date)
        self.price_review_date.click()
        framework_price_review_date = self.price_review_date.inner_text()
        print("Framework price review date: " + framework_price_review_date)
        self.from_date.click()
        framework_from_date = self.from_date.inner_text()
        print("Framework from date: " + framework_from_date)
        self.to_date.click()
        framework_to_date = self.to_date.inner_text()
        print("Framework to date: " + framework_to_date)

    def print_agreement_date(self):
        self.agreement_date.click()
        print("Agreement date: " + self.agreement_date.inner_text())

    def print_price_review_date(self):
        self.price_review_date.click()
        print("Price review date: " + self.price_review_date.inner_text())

    def print_from_date(self):
        self.from_date.click()
        print("From date: " + self.from_date.inner_text())

    def print_to_date(self):
        self.to_date.click()
        print("To date: " + self.to_date.inner_text())
        self.wait_for_timeout(2000)

    def go_to_framework_list(self):
        self.go_to_list_button.click()
        self.wait_for_timeout(2000)

    def print_framework_item_details(self):
        print("Framework item details: " + self.framework_item_details.inner_text())

    def enter_agreement_comments(self, comments):
        self.comments.click()
        self.comments.clear()
        self.input_in_element(self.comments, comments)

    def confirm_agreement_amendment(self):
        self.amendment_button.click()
        text = self.success_message.inner_text()
        print("Amendment confirmation full message:", text)

    def print_item_details_1(self):
        rows = self.item_details_info.all()
        if not rows:
            print("No records found in the table")
        else:
            for idx, row in enumerate(rows, start=1):
                print(f"Row {idx}:", row.inner_text())

    def print_item_details_2(self):
        rows = self.item_details_info.all('tr')
        if not rows:
            print("No records found in the table")
        else:
            for idx, row in enumerate(rows, start=1):
                print(f"Row {idx}:", row.inner_text())

    def confirm_agreement_approval(self) -> str:
        self.approve_button.click()
        self.success_message.wait_for(state="visible", timeout=15000)
        approval_status_message = self.success_message.text_content()
        print("Agreement confirmation full message:", approval_status_message)
        return approval_status_message

    # ---------------- Pre-amendment data capture ----------------

    def get_field_value(self, label):
        # Header field value: <div class="label-new">Label</div> + next <div class="content-new">Value</div>
        value_cell = self.page.locator(
            f"xpath=//div[contains(@class,'label-new') and normalize-space(.)='{label}']"
            f"/following-sibling::div[contains(@class,'content-new')][1]").first
        value_cell.wait_for(state="visible", timeout=30000)
        return value_cell.inner_text().strip()

    def get_framework_information_values(self):
        # FA No., vendor name only, dates, Applicable For and approver name only
        vendor_info = self.get_field_value("Vendor Info.")
        approver_info = self.get_field_value("Approver")
        framework_values = {
            "FA No.": self.get_field_value("FA No."),
            "Vendor": vendor_info.split(":")[0].strip(),
            "From Date": self.get_field_value("From Date"),
            "To Date": self.get_field_value("To Date"),
            "Price Review Date": self.get_field_value("Price Review Date"),
            "Applicable For": self.get_field_value("Applicable For"),
            # "[00153860]-Imran Hossen" -> "Imran Hossen"
            "Approver": approver_info.split("]-", 1)[-1].splitlines()[0].strip() if approver_info else "",
        }
        for label, value in framework_values.items():
            print(f"{label}: {value}")
        return framework_values

    def download_attachment(self, download_dir):
        # Download the existing attachment; returns (file path or None, message)
        attachment_link = self.page.locator(
            "xpath=//div[contains(@class,'label-new') and normalize-space(.)='Attachment']"
            "/following-sibling::div[contains(@class,'content-new')][1]//a").first
        if not attachment_link.count():
            message = "No attachment link on the Framework Information page"
            print(message)
            return None, message
        attachment_url = attachment_link.get_attribute("href")
        response = self.page.request.get(urljoin(self.page.url, attachment_url))
        content_type = response.headers.get("content-type", "")
        if not response.ok or "text/html" in content_type:
            # No file: the system shows a page/message instead of the attachment
            message = f"Attachment not downloaded ({response.status}): {response.text()[:300]}"
            print(message)
            return None, message
        # File name from the filePath parameter, e.g. ...readFileStream?filePath=.../1790052285453.2.png
        file_name = unquote(attachment_url).split("filePath=")[-1].split("/")[-1] or "framework_attachment"
        os.makedirs(download_dir, exist_ok=True)
        file_path = os.path.join(download_dir, file_name)
        with open(file_path, "wb") as attachment_file:
            attachment_file.write(response.body())
        message = f"Attachment downloaded: {file_name}"
        print(message)
        return file_path, message

    def get_item_rows(self):
        # Framework Item Details rows (SL, NOAL View, Tender Ref. No., Item Name, ..., Unit Price)
        return self.item_details_info.locator("tr").filter(
            has=self.page.locator("a[onclick^='showAdditionalInfo']"))

    def get_item_values(self, item_row):
        # Item Name, Specification, UoM, MOQ, MRP Price, Discount (%), Unit Price (MRP/Discount may be blank)
        # Columns are read from the Item Name cell (some stages show an extra checkbox column before it)
        cells = [cell.strip() for cell in item_row.locator("td").all_inner_texts()]
        item_name = item_row.locator("a[onclick^='showAdditionalInfo']").inner_text().strip()
        name_index = cells.index(item_name)
        return {
            "Item Name": item_name,
            "Specification": cells[name_index + 1],
            "UoM": cells[name_index + 2],
            "MOQ": cells[name_index + 3],
            "MRP Price": cells[name_index + 4] or None,
            "Discount (%)": cells[name_index + 5] or None,
            "Unit Price": cells[name_index + 6],
        }

    def get_item_delivery_location(self, item_row):
        # Item Name > item details popup (fancybox) > Delivery Location > close the popup
        item_row.locator("a[onclick^='showAdditionalInfo']").click()
        self.item_popup.wait_for(state="visible", timeout=15000)
        delivery_location = self.item_popup_delivery_location.inner_text().strip()
        self.get_full_page_screenshot('agreement_item_popup')
        if self.item_popup_close_button.is_visible():
            self.item_popup_close_button.click()
        else:
            self.page.keyboard.press("Escape")
        self.item_popup.wait_for(state="hidden", timeout=10000)
        print(f"Delivery Location: {delivery_location}")
        return delivery_location

    def confirm_agreement_amendment_with_message(self):
        # Click Amendment and return the confirmation message
        self.amendment_button.click()
        self.success_message.wait_for(state="visible", timeout=15000)
        amendment_message = self.success_message.inner_text().strip()
        print("Amendment confirmation message:", amendment_message)
        return amendment_message
