# this is an object of samplePage to automate, which contains all elements
# and actions could be performed, like input, verify etc.
from utils.basic_actionsdm import BasicActionsDM
from playwright.sync_api import expect


class MainNavigationBar(BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger
        # write down all the elements here with locator format
        self.exit_button = page.locator("a#btn_login.btn_user")

        # ERP header has two Logout links (small and large screen menus): the visible one
        self.logout_button = self.page.locator('a[href="/logout"]:visible').first

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    # write down all the necessary actions performed on this page as def
    def exit(self):
        # self.page.locator('#overlay.active').wait_for(state='detached', timeout=10000)
        self.exit_button.click()
        self.wait_for_timeout(1000)

    def logout(self):
        self.logout_button.click()
        self.page.context.clear_cookies()
        self.page.context.clear_permissions()

    def logout_visible(self):
        # Why: some ERP pages have two Logout links (small and large screen menus), so only the visible one is
        # clicked; When: ERP logout after the framework order check of the vendor acknowledgement test file
        self.page.locator("a[href='/logout']:visible").first.click()
        self.page.context.clear_cookies()
        self.page.context.clear_permissions()
