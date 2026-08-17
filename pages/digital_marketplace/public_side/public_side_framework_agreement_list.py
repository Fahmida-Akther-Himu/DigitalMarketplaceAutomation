from utils.basic_actionsdm import BasicActionsDM
from playwright.sync_api import expect



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

        # product details locator for add to wishlist
        self.item_add_to_wishlist = page.locator("div.add-to-wishlist button")
        # self.item_add_to_wishlist = page.locator("[id^='add-to-wishlist-button']")
        self.success_notification = page.locator("#bar-notification .bar-notification.success")
        self.success_message = page.locator("#bar-notification .bar-notification.success p.content")
        # self.success_message = self.success_notification.locator("p.content")
        self.wishlist_link = self.success_notification.locator("a[href='/wishlist']")
        self.close_notification = self.success_notification.locator("span.close")
        ##################### small helper so we can log easily #####################

    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def search_agreement(self, agreement_number):
        self.click_on_btn(self.search_agreement_locator)
        self.search_agreement_locator.clear()
        self.input_in_element(self.search_agreement_locator, agreement_number)
        self.click_on_btn(self.agreement_search_button)
        # self.wait_to_load_element(self.success_message)
        # value = self.success_message.text_content()
        # return value.split(' ')[-1]

    def product_add_to_wishlist(self):
        self.click_on_btn(self.item_add_to_wishlist)
        # wait for visible success message
        self.success_message.wait_for(state="visible")
        value = self.success_message.text_content().strip()
        print(f"Success Message: {value}")

        return value