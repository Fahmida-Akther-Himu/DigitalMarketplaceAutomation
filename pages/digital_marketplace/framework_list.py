from re import search

from utils.basic_actionsdm import BasicActionsDM


class FrameworkList(BasicActionsDM):
    def __init__(self, page):
        super().__init__(page)
        self.page = page

        # self.vendor_info = page.locator('//*[@id="proposal-process"]/div[1]/div/div[4]/div/div/div[2]')
        self.search_framework_number = page.locator("input[id='keywords']")
        self.search_icon = page.locator("span[class='ui-button-icon-primary ui-icon ui-icon-search']")

        self.approval_pending_checkbox = page.locator("input[id='isOnAuthorization']")
        self.agreement_expired_checkbox = page.locator("input[id='isOnExpired']")
        self.agreement_on_live_checkbox = page.locator("input[id='isOnAuthorization']")
        self.approval_pending_checkbox = page.locator("input[id='isOnAuthorization']")

    def search_agreement(self, search_agreement):
        self.search_framework_number.click()
        self.input_in_element(self.search_framework_number, search_agreement)
        self.search_icon.click()
