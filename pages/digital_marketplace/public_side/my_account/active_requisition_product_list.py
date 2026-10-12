import re
from pages.digital_marketplace.home_page import HomePage
from utils.basic_actionsdm import BasicActionsDM
from playwright.sync_api import expect


# from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class ActiveRequisitionProductList(HomePage, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.page = page
        self.logger = logger
        # self.product_history = page.locator('a[href*="requisitionProductId={product_id}"]')
        self.history_link = page.locator('a[href^="/Requisition/History?requisitionProductId="]')
        # Staging use
        # self.add_to_cart_button = page.locator('button[id="addToCartBtn-7323"]')
        # self.add_to_cart_button = page.locator('button[id^="addToCartBtn-"]')
        self.add_to_cart_button = page.locator('button[type="button"][class="button-1 save-customer-info-button"]')

        self.close_button = page.locator('.close')
        self.shopping_cart = page.locator('a[class="ico-cart"]')

        self.back_to_product_history = page.locator('a[href^="/Requisition/ActiveRequisitionProductList?"]')
        # Active Requisition Product List table (Sub-Category, Product, ..., FwA No., History, Action)
        self.product_list_table = page.locator("table").filter(has_text="Sub-Category").last

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def requisition_item_add_shopping_cart(self):
        self.click_on_btn(self.add_to_cart_button)

    def goto_shopping_cart(self):
        self.click_on_btn(self.shopping_cart)
        self.wait_for_timeout(5000)

    def view_product_switch_history(self):
        self.click_on_btn(self.history_link)
        self.wait_for_timeout(2000)

    def get_product_history_count(self):
        # One History link per requisition product
        return self.history_link.count()

    def view_product_switch_history_by_index(self, index):
        # History of one product when the requisition has several products
        self.click_on_btn(self.history_link.nth(index))
        self.wait_for_timeout(2000)

    def go_to_product_history(self):
        self.click_on_btn(self.back_to_product_history)

    @staticmethod
    def table_rows(table):
        # Data rows of a table as {column title: cell}, column titles from the first row
        expect(table).to_be_visible(timeout=30000)
        headers = [" ".join(text.split()) for text in table.locator("tr").first.locator("th, td").all_inner_texts()]
        table_rows = []
        for row in table.locator("tr").all()[1:]:
            cells = row.locator("td")
            if cells.count() >= len(headers):
                table_rows.append({header: cells.nth(index) for index, header in enumerate(headers)})
        return table_rows

    @staticmethod
    def cell_text(cell):
        # Cell text on one line, e.g. "Angle Valve\n- Any Where" -> "Angle Valve - Any Where"
        return " ".join((cell.inner_text() or "").split())

    def get_product_rows(self):
        # Product rows of the Active Requisition Product List: {column title: cell}
        product_rows = self.table_rows(self.product_list_table)
        print(f"Active Requisition Product List rows: {len(product_rows)}")
        return product_rows

    def open_link_and_back(self, cell, back_page_table, screenshot_name):
        # Open the link of a cell (same tab), take a screenshot, go back and wait for the previous table
        link = cell.locator("a").first
        expect(link, "No link in the cell").to_be_visible(timeout=15000)
        link_text = " ".join((link.inner_text() or "").split())
        self.click_on_btn(link)
        self.page.wait_for_load_state("domcontentloaded")
        opened_url = self.page.url
        self.get_full_page_screenshot(screenshot_name)
        print(f"Opened '{link_text}': {opened_url}")
        self.page.go_back()
        self.page.wait_for_load_state("domcontentloaded")
        expect(back_page_table).to_be_visible(timeout=30000)
        return {"link_text": link_text, "opened_url": opened_url}

    def open_fwa_attachment(self, cell, screenshot_name):
        # FwA No. link opens the agreement attachment in a new tab:
        # available -> the file is shown/downloaded; not available -> ERP page with a message
        link = cell.locator("a").first
        expect(link, "FwA No. is not a link").to_be_visible(timeout=15000)
        fwa_no = " ".join((link.inner_text() or "").split())
        with self.page.context.expect_page() as new_tab_info:
            self.click_on_btn(link)
        attachment_tab = new_tab_info.value
        attachment_tab.wait_for_load_state("domcontentloaded")
        attachment_url = attachment_tab.url
        response = attachment_tab.context.request.get(attachment_url)
        content_type = response.headers.get("content-type", "")
        attachment = {
            "fwa_no": fwa_no,
            "attachment_url": attachment_url,
            "available": response.ok and "text/html" not in content_type,
            "file_name": attachment_url.split("/")[-1],
            "message": "",
        }
        if not attachment["available"]:
            attachment["message"] = " ".join(attachment_tab.locator("body").inner_text().split())
        attachment_tab.screenshot(path=f"screenshots_taken/{screenshot_name}.png", full_page=True)
        attachment_tab.close()
        self.page.bring_to_front()
        print(f"FwA attachment: {attachment}")
        return attachment

    # Finds the row with the given requisition ID in the Active Requisition List.
    # If the Total Budget equals the Remaining Budget, click the requisition link.
    def click_requisition_if_budget_matches(self, requisition_id: str):
        try:
            row = self.page.locator(
                'tr',
                has=self.page.locator(f'a[href*="requisitionId={requisition_id}"]')
            )

            if row.count() == 0:
                print(f"[ActiveRequisitionList] Row not found for requisitionId={requisition_id}")
                return False
            # strip means remove any leading and trailing whitespace characters (spaces,tabs,newlines)
            total_budget_text = row.locator('td').nth(3).text_content().strip()
            remaining_budget_text = row.locator('td').nth(4).text_content().strip()

            # 1,00,000.00 = 100000
            total_budget = float(total_budget_text.replace(",", ""))
            remaining_budget = float(remaining_budget_text.replace(",", ""))

            if total_budget == remaining_budget:
                print(f"[ActiveRequisitionList] Budgets match ({total_budget}) — clicking requisition link.")
                row.locator(f'a[href*="requisitionId={requisition_id}"]').click()
                self.wait_for_timeout(2000)
                return True

            else:
                print(
                    f"[ActiveRequisitionList] Budgets do NOT match: Total={total_budget}, Remaining={remaining_budget}")
                return False

        except Exception as e:
            print(f"[ActiveRequisitionList] Error occurred: {e}")
            return False
