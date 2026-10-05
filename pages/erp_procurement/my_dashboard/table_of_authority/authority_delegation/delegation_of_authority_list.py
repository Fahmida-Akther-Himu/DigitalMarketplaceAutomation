# import pages.login_page
import re
from datetime import datetime

from playwright.sync_api import expect
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

        # Delegation Of Authority grid rows (SL | Delegated User | PIN | Start Date | End Date | Remove)
        self.delegation_rows = page.locator("table[role='grid'] tr.jqgrow")
        # Delete alert: "Delete item(s)" and success message
        self.delete_items_button = page.get_by_role("button", name="Delete item(s)")
        self.delete_success_message = page.locator("#jGrowl").get_by_text(
            "Delegation Of Authority deleted successfully")

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

    def get_current_date_delegation_row(self, PIN: str):
        # First row of the delegated approver whose Start Date <= today <= End Date (dates dd-mm-yyyy)
        today = datetime.today().date()
        self.wait_for_timeout(2000)
        for index in range(self.delegation_rows.count()):
            row = self.delegation_rows.nth(index)
            row_text = row.inner_text()
            dates = re.findall(r"\d{2}-\d{2}-\d{4}", row_text)
            if PIN not in row_text or len(dates) < 2:
                continue
            start_date = datetime.strptime(dates[0], "%d-%m-%Y").date()
            end_date = datetime.strptime(dates[1], "%d-%m-%Y").date()
            if start_date <= today <= end_date:
                print(f"Current date delegation found: {dates[0]} to {dates[1]}")
                return row, f"{dates[0]} to {dates[1]}"
        return None, None

    def remove_current_date_delegations(self, PIN: str):
        # Remove every delegation of the delegated approver for the current date; returns removed date ranges
        removed_delegations = []
        while True:
            row, date_range = self.get_current_date_delegation_row(PIN)
            if row is None:
                break
            self.highlight_element(row)
            self.click_on_btn(row.get_by_text("Remove", exact=True))
            self.click_on_btn(self.delete_items_button)
            expect(self.delete_success_message).to_be_visible(timeout=15000)
            print(f"Delegation removed: {date_range}")
            removed_delegations.append(date_range)
        return removed_delegations
