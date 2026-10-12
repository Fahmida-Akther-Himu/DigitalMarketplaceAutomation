from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.public_side.my_account.active_requisition_product_list import \
    ActiveRequisitionProductList
from utils.basic_actionsdm import BasicActionsDM
from playwright.sync_api import expect


class ProductSwitchHistory(ActiveRequisitionProductList):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        # Product Switch History table (Product Name, Specification, Unit Price, FwA No., Vendor Name, Date)
        self.history_table = page.locator("table").filter(has_text="Product Name").last

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def get_history_rows(self):
        # Rows of the Product Switch History: {column title: cell}
        history_rows = self.table_rows(self.history_table)
        print(f"Product Switch History rows: {len(history_rows)}")
        return history_rows

    # def view_product_history(self, product_id: str):
    #     # # product_id = "2960"
    #     # page.locator('a[href*="Requisition/History?requisitionProductId="]').click()
    #     # # self.click_on_btn(self.product_history)
    #     # # self.wait_for_timeout(2000)
    #     # product_id = "2960"
    #     history_link = page.locator(f'a[href*="Requisition/History?requisitionProductId={product_id}"]')
    #
    #     if history_link.is_visible():
    #         print("History link is visible")
    #         self.history_link.click()
    #         self.wait_for_timeout(2000)
    #     else:
    #         print("History link is not visible")
