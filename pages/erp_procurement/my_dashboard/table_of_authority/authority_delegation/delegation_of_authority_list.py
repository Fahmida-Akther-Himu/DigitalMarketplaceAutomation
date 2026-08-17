# import pages.login_page
from utils.basic_actionsdm import BasicActionsDM


class DelegationOfAuthorityListPage(BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger

        # Table Of Authority
        self.table_of_authority = page.locator(
            '//div[normalize-space()="Table Of Authority"]'
        )

        # Authority Delegation
        self.authority_delegation = page.locator(
            '//span[@class="menuTxtSpan" and normalize-space()="Authority Delegation"]'
        )

        self.delegation_of_authority_list = page.locator(
            '#wrapper ul.main_top_navigation '
            'a[href="#!delegationOfAuthority/delegationList"]'
        )

        self.search_delegated_approver = page.locator('#employeeInfo')
        self.delegation_list_table = page.get_by_role("grid")

        # Visible autocomplete dropdown
        self.delegated_approver_autocomplete = page.locator(
            'ul.ui-autocomplete[role="listbox"]:visible'
        )

    ##################### small helper so we can log easily #####################

    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def go_to_delegation_of_authority_list(self):
        # self._log("Opening Table of Authority menu")
        self.table_of_authority.click()

        # self._log("Opening Authority Delegation submenu")
        self.authority_delegation.click()

        # self._log("Opening Delegation of Authority List")
        self.delegation_of_authority_list.click()

    def search_by_delegated_approver_by_PIN(self, PIN: str):
        self.search_delegated_approver.click()
        # self.search_delegated_approver.clear()
        # self.input_in_element(self.search_delegated_approver, PIN)
        self.search_delegated_approver.fill(PIN)
        self.page.keyboard.type(" ")
        self.page.keyboard.press("Backspace")
        # Find exact PIN only inside grid cells
        # search_employee = self.page.get_by_role(
        #     "gridcell",
        #     name=PIN,
        #     exact=True
        # ).click()
        #
        # search_employee.wait_for(
        #     state="visible",
        #     timeout=2000
        # )
        # Wait for autocomplete dropdown
        self.delegated_approver_autocomplete.wait_for(
            state="visible",
            timeout=10000
        )

        # Find the autocomplete item containing the PIN
        employee_option = (
            self.delegated_approver_autocomplete
            .locator("li.ui-menu-item")
            .filter(has_text=PIN)
        )

        employee_option.wait_for(
            state="visible",
            timeout=10000
        )

        employee_option.click()

        self._log(
            f"Delegated approver found successfully with PIN: {PIN}"
        )

        print(
            f"Delegated approver found successfully with PIN: {PIN}"
        )
