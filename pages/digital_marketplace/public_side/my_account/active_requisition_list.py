import re

from utils.basic_actionsdm import BasicActionsDM
from pages.digital_marketplace.home_page import HomePage

from playwright.sync_api import expect


class ActiveRequisitionListPage(HomePage, BasicActionsDM):
    # def __init__(self, driver):
    #     super(ActiveRequisitionListPage, self).__init__(driver)
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        self.order_requisition_number = page.locator('input[id="searchOrderInput"]')
        self.search_button = page.locator('button[class="button"]')

        self.requisition_hyperlink = page.locator(
            'a[href^="/Requisition/ActiveRequisitionProductList?requisitionId"]')
        # Need to change child id when using from table child = row
        # self.requisition_hyperlink = page.locator('.data-table > tbody:nth-child(2) > tr:nth-child(1)')
        self.add_to_cart_button = page.locator('button[id="addToCartBtn-7323"]')
        self.close_button = page.locator('.close')

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def search_order_requisition_number(self, requisition_number):
        self.input_in_element(self.order_requisition_number, requisition_number)
        self.search_button.click()
        print("Searching requisition number " + requisition_number)

    def goto_active_requisition_product_list(self):
        self.click_on_btn(self.requisition_hyperlink)
        self.wait_for_timeout(2000)

    def verify_requisition_in_list(self, requisition_number):
        # The requisition row is shown in the Active Requisition List
        requisition_row = self.page.locator("tr").filter(has_text=requisition_number).last
        expect(requisition_row, f"{requisition_number} not shown in the Active Requisition List").to_be_visible(
            timeout=15000)
        print(f"Requisition {requisition_number} shown in the Active Requisition List")

    def get_requisition_budget(self, requisition_number):
        # Total Budget and Remaining Budget of the requisition row (column titles from the table header)
        requisition_table = self.page.locator("table").filter(has_text="Total Budget").last
        expect(requisition_table).to_be_visible(timeout=15000)
        headers = [" ".join(text.split()) for text in requisition_table.locator("tr").first.locator("th, td").all_inner_texts()]
        requisition_row = requisition_table.locator("tr").filter(has_text=requisition_number).last
        cells = [" ".join(text.split()) for text in requisition_row.locator("td").all_inner_texts()]
        row_values = dict(zip(headers, cells))
        budget = {"total_budget": row_values.get("Total Budget", ""),
                  "remaining_budget": row_values.get("Remaining Budget", "")}
        print(f"Budget of {requisition_number}: {budget}")
        return budget

    def open_erp_view(self, requisition_number):
        # ERP View column: VIEW button of the requisition row opens the ERP requisition details in a new tab
        requisition_row = self.page.locator("tr").filter(has_text=requisition_number).last
        view_button = requisition_row.locator("a, button", has_text=re.compile(r"^\s*view\s*$", re.IGNORECASE)).first
        expect(view_button, f"ERP View button not found for {requisition_number}").to_be_visible(timeout=15000)
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(view_button)
        erp_tab = new_tab_info.value
        erp_tab.wait_for_load_state("domcontentloaded")
        print(f"ERP View of {requisition_number}: {erp_tab.url}")
        return erp_tab

    # Need change requisition id when requisition number will be changed
    def goto_active_requisition_product_list_stg(self):
        self.navigate_to_url(
            "https://stgmarketplace.brac.net/Requisition/ActiveRequisitionProductList?requisitionId=3568")

    def requisition_item_add_shopping_cart(self):
        self.click_on_btn(self.add_to_cart_button)
        self.wait_for_timeout(5000)
