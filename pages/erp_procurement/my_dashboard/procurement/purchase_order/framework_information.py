import re

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
