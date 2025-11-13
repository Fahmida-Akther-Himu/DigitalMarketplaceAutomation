from re import search

from pages.digital_marketplace.framework_information import FrameworkInformation
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
        self.agreement_on_live_checkbox = page.locator("input[id='isOnlive']")
        self.debar_or_banned_checkbox = page.locator("input[id='isDebar']")

        self.hub_selection = page.locator("select[id='hub']")
        self.fa_no_link = page.locator("a[style='text-decoration: underline;'][onclick^='showDetails']")

        self.agreement_status = page.locator("//table[@id='frameworkListGrid']/tbody/tr[2]/child::td[14]")

    def search_agreement(self, search_framework_agreement):
        self.search_framework_number.click()
        self.search_framework_number.clear()
        self.input_in_element(self.search_framework_number, search_framework_agreement)
        self.search_icon.click()

    def find_agreement_approver_info(self):
        agreement_status_value = self.agreement_status.text_content()
        print("Agreement status value:", agreement_status_value)

    def find_agreement_approver_id(self) -> str:
        agreement_status_value = self.agreement_status.text_content()
        # print("Agreement status value:", agreement_status_value)
        agreement_approver_id = agreement_status_value.split('[')[-1].split(']')[0]
        print("Agreement approver ID(without type cust): " + agreement_approver_id)
        return agreement_approver_id

    # def find_approver_id(self) -> str:
    #     status_value = self.requisition_status.text_content()
    #     approver_id = status_value.split('[')[-1].split(']')[0]
    #     print("Approver ID: " + approver_id)
    #     return approver_id
