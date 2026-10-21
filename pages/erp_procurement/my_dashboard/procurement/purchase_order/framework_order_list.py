from utils.basic_actionsdm import BasicActionsDM
from pages.erp_procurement.procurement_home_page import ProcurementHomePage


class FrameworkOrderListPage(ProcurementHomePage, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger
        self.page = page
        self.search_box = page.locator("input[placeholder='Search Framework Order No']")
        self.search_button = page.locator("span[onclick='getFrameWorkOrderList(true)']")
        self.table_rows = page.locator("#pending-acknowledgement-report-grid tbody tr")

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def search_framework_order(self, fa_order_no: str):
        self.search_box.fill(fa_order_no)
        self.search_button.click()
        self.page.wait_for_timeout(1000)
        print(f"Searched for Framework Order No. : {fa_order_no}")

    def click_framework_order_1(self):
        self.link.click()

    def click_framework_order(self, framework_order_no: str):
        link = self.page.locator(f"//a[contains(text(),'{framework_order_no}')]")
        link.wait_for(state="visible", timeout=5000)
        link.click()
        print(f"Opened Marketplace framework order details: {framework_order_no}")

    def open_order_preview(self):
        # Why: Preview of the ERP Framework Order Details opens a PDF viewer tab that loads the marketplace order
        # document (PDF); When: ERP framework order check after the vendor acknowledgement (procurement admin).
        # Returns (viewer tab, address of the loaded PDF; "" when no PDF was loaded in 60 seconds)
        preview_button = self.page.locator(
            "input[value='Preview']:visible, button:visible:has-text('Preview'), a:visible:has-text('Preview')").first
        pdf_urls = []

        def keep_pdf(response):
            # Why: the viewer loads the order document as a PDF response; When: every response after Preview
            if "application/pdf" in response.headers.get("content-type", ""):
                pdf_urls.append(response.url)

        self.page.context.on("response", keep_pdf)
        try:
            with self.page.context.expect_page() as new_tab_info:
                preview_button.click()
            preview_tab = new_tab_info.value
            preview_tab.wait_for_url(lambda url: url.startswith("http"), timeout=60000, wait_until="commit")
            for _ in range(120):
                if pdf_urls:
                    break
                preview_tab.wait_for_timeout(500)
        finally:
            self.page.context.remove_listener("response", keep_pdf)
        print(f"ERP order document opened: {preview_tab.url}")
        print(f"ERP order document PDF: {pdf_urls[0] if pdf_urls else 'not loaded'}")
        return preview_tab, (pdf_urls[0] if pdf_urls else "")
