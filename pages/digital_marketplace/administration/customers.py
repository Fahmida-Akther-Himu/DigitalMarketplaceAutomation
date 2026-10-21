from symtable import Class

# from pages.digital_marketplace.home_page import HomePage
from utils.basic_actionsdm import BasicActionsDM

from playwright.sync_api import expect


class Customers(BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        self.customers_menu = page.locator('i[class="nav-icon far fa-user"]')
        self.customers_submenu = page.locator('a[href="/Admin/Customer/List"]')

        # Customer search parameter
        self.first_name = page.locator('input[id="SearchFirstName"]')
        self.last_name = page.locator('input[id="SearchLastName"]')
        self.email = page.locator('input[id="SearchEmail"]')
        self.username = page.locator('input[id="SearchUsername"]')
        self.ip_address = page.locator('input[id="SearchIpAddress"]')
        self.dob_month = page.locator('input[id="SearchMonthOfBirth"]')
        self.dob_day = page.locator('input[id="SearchDayOfBirth"]')
        self.user_group = page.locator('.k-multiselect-wrap')

        self.customer_search_button = page.locator('button[id="search-customers"]')
        # Customers grid rows: checkbox | Username | User Info. | User Group | Active | Edit
        self.customer_rows = page.locator("table tbody tr")

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def view_customers_list(self):
        self.customers_menu.click()
        # self.wait_for_timeout(5000)
        self.customers_submenu.click()
        # self.wait_for_timeout(5000)

    def search_vendor(self, customer_name):
        self.first_name.click()
        self.input_in_element(self.first_name, customer_name)
        # self.wait_for_timeout(5000)

    def search_customers(self):
        self.customer_search_button.click()
        self.wait_for_timeout(5000)
        username = self.page.locator("td").nth(1).inner_text()

        print(username)
        return username

    def search_customer_by_first_name(self, first_name):
        # Why: the vendor is searched by its name in the First name field (same as the sanity Test case 19);
        # When: retrieving the vendor username before the vendor login
        self.search_vendor(customer_name=first_name)
        self.click_on_btn(self.customer_search_button)
        self.wait_for_timeout(5000)

    def get_customer_rows(self, name):
        # Why: the search can show more customers than the vendor, so every row with the name is read and checked;
        # When: after search_customer_by_first_name. Returns [{"Username", "User Info", "User Group"}]
        rows = self.customer_rows.filter(has_text=name)
        return [self.read_customer_row(rows.nth(index)) for index in range(rows.count())]

    @staticmethod
    def read_customer_row(row):
        # Why: Username, User Info. and User Group of one customers grid row; When: get_customer_rows
        cells = row.locator("td")
        return {title: " ".join(cells.nth(index).inner_text().split())
                for index, title in ((1, "Username"), (2, "User Info"), (3, "User Group"))}
