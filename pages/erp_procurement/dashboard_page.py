from utils.basic_actionsdm import BasicActionsDM
from playwright.sync_api import expect


class DashboardPage(BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger
        # write down all the elements here with locator format
        self.myDashboardItem_modal = page.locator('id=modal')
        self.myDashboardItem_HRM = page.locator('xpath=//*[contains(text(),"HRM")]')
        self.myDashboardItem_ePMS = page.locator('xpath=//*[contains(text(),"ePMS")]')
        self.myDashboardItem_EDMS = page.locator('xpath=//*[contains(text(),"EDMS")]')
        self.myDashboardItem_procurement = page.locator('xpath=//*[contains(text(),"PROCUREMENT")]')
        # self.myDashboardItem_procurement = page.locator('/html/body/div[2]/div[2]/div/div/div[2]/div[3]/div/a')
        # self.myDashboardItem_procurement = page.locator('//a[contains(@class, "moreInfoBoxShow") and text()="PROCUREMENT"]')
        self.myDashboardItem_eTender = page.locator('xpath=//*[contains(text(),"E-Tender")]')
        self.myDashboardItem_Marketplace = page.locator('xpath=//*[contains(text(),"Marketplace")]')
        self.myDashboardItem_FIXEDASSET = page.locator('xpath=//*[contains(text(),"FIXED ASSET")]')
        self.myDashboardItem_MICROFINANCE = page.locator('xpath=//*[contains(text(),"MICROFINANCE")]')
        self.myDashboardItem_ACCOUNTING = page.locator('xpath=//*[contains(text(),"ACCOUNTING")]')
        self.myDashboardItem_Budget = page.locator('xpath=//*[contains(text(),"Budget")]')
        self.myDashboardItem_FINANCIALCONSOLIDATION = page.locator(
            'xpath=//*[contains(text(),"FINANCIAL CONSOLIDATION")]')
        self.myDashboardItem_MyBRAC = page.locator('xpath=//*[contains(text(),"My BRAC")]')
        self.myDashboardItem_MyDesk = page.locator('xpath=//*[contains(text(),"My Desk")]')
        self.myDashboardItem_CareersPortal = page.locator('xpath=//*[contains(text(),"Careers Portal")]')
        self.myDashboardItem_eRecruitment = page.locator('xpath=//*[contains(text(),"eRecruitment")]')
        self.myDashboardItem_PERFORMANCEDASHBOARD = page.locator('xpath=//*[contains(text(),"PERFORMANCE DASHBOARD")]')
        self.myDashboardItem_HRAnalyticsDASHBOARD = page.locator('xpath=//*[contains(text(),"HR Analytics ")]')
        self.myDashboardItem_HOFAMS = page.locator('xpath=//*[contains(text(),"HO FAMS")]')
        self.myDashboardItem_MonthlyMFReportingTool = page.locator(
            'xpath=//*[contains(text(),"Monthly MF Reporting Tool")]')
        self.myDashboardItem_Brac_Inventory = page.locator('xpath=//*[contains(text(),"Brac Inventory")]')
        self.add_banner = page.locator('#modals')
        self.close_modal = page.locator('button[class="close-button"][data-close-button=""]')
        self.click_procurement_hyperlink = page.locator('a[href="/procurementDashboard/myDashboard"]')
        # Table of Authority menu
        self.table_of_authority = page.locator(
            '//div[normalize-space()="Table Of Authority"]'
        )

        # Authority Delegation submenu
        self.authority_delegation = page.locator(
            '//span[normalize-space()="Authority Delegation"]'
        )

        # Create Delegation of Authority
        # Delegation Of Authority
        self.delegation_of_authority = page.locator(
            '//span[@class="menuTxtSpan" and normalize-space()="Delegation Of Authority"]/parent::a'
        )

        # Delegation Of Authority List
        self.delegation_of_authority_list = page.locator(
            '//span[@class="menuTxtSpan" and normalize-space()="Delegation Of Authority List"]/parent::a'
        )

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def closing_add(self) -> None:
        self.wait_to_load_element(self.add_banner)
        self.get_full_page_screenshot('add_bannar')
        self.page.keyboard.press('Enter')
        self.get_full_page_screenshot('add_bannar2')

    def goto_procurement(self) -> None:
        self.click_on_btn(self.myDashboardItem_procurement)

    def menu_click_procurement_hyperlink(self):
        self.click_on_btn(self.click_procurement_hyperlink)

    def navigate_to_delegation_of_authority(self):
        self._log("Opening Table of Authority menu")
        self.table_of_authority.click()

        self._log("Opening Authority Delegation submenu")
        self.authority_delegation.click()

        self._log("Opening Delegation of Authority page")
        self.delegation_of_authority.click()

        expect(
            self.page.get_by_role(
                "heading",
                name="Create Delegation Of Authority"
            )
        ).to_be_visible(timeout=10000)

    def navigate_to_delegation_of_authority_list(self):
        self._log("Opening Table of Authority menu")
        self.table_of_authority.click()

        self._log("Opening Authority Delegation submenu")
        self.authority_delegation.click()

        self._log("Opening Delegation of Authority List")
        self.delegation_of_authority_list.click()
