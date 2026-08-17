import os
from playwright.sync_api import expect
from utils.basic_actionsdm import BasicActionsDM
from pages.erp_procurement.procurement_home_page import ProcurementHomePage


class CreateRequisition(ProcurementHomePage, BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger
        # Validating page has been redirected correctly
        self.validation_point = page.get_by_role("heading", name="Create Requisition")

        # Elements for requisition for
        self.head_office_selector = page.locator("#self")
        self.project_name_dropdown_selector = page.locator("#projectInfoDiv_arrow")

        # Hidden project for
        self.selected_project_name = page.locator('//*[@id="projectInfoDiv_hidden"]')

        # Elements for requisition information
        self.fund_source_selector = page.locator("#sourceOfFundDiv_input")
        self.fund_source_remarks_selector = page.locator("//*[@id='remarks']")
        self.fund_source_dropdown_selector = page.locator('#sourceOfFundDiv_arrow')
        self.fund_container = page.locator('#sourceOfFundDiv_ctr')

        # Elements for requisition details
        self.item_info_selector = page.locator("//*[@id='itemInfo']")
        self.item_measure_selector = page.locator("#mUnitDiv_arrow")
        self.item_tor_selector = page.locator("//*[@id='itemSpecification']")
        self.item_qty_selector = page.locator("#quantity")
        self.item_unit_price_selector = page.locator("#unitPrice")
        self.item_info_for_active = page.locator(
            "/html/body/div[2]/div[2]/div/div[1]/div[1]/form[1]/div[1]/div/div[1]/div[1]/div[2]/div[1]/div/ul/li/a")

        # All active framework agreement locator
        self.active_agreement_button = page.locator('#check-agreement-button')
        self.fa_agreement_input = page.locator('input#faAgreementNo')
        self.find_button = page.locator('//*[@id="find-button-requisitionList"]')
        # self.agreement_item_selector = page.locator("tr.jqgrow")
        self.agreement_item_selector = page.locator("#gview_frameworkListGrid table#frameworkListGrid tbody tr.jqgrow")

        # Elements for "requisition for?"
        self.gl_code_dropdown = page.locator("#glInfo_0Div_arrow")
        self.selected_gl_code = page.locator('//*[@id="glInfo_0Div"]')
        self.gl_input = page.locator("div[id^='glInfo_'] input[id$='_input']")
        self.ref_code_dropdown = page.locator("#refCodeId_0Div_arrow")
        self.ref_code_input = page.locator("#refCodeId_0Div_input")
        self.req_for_remarks_selector = page.locator("#reqDetailsRemarks")
        self.add_to_grid_button = page.locator("input#addToGrid")

        # Same schedule selector
        self.select_same_schedule = page.locator('//*[@id="useDefault"]')
        self.date_picker_icon = page.locator("img.ui-datepicker-trigger")
        self.today = page.locator(".ui-datepicker-calendar .ui-state-highlight")
        self.delivery_store_select = page.locator("#defaultDeliveryStoreId")
        self.location_input = page.locator("#defaultDeliveryPlace")

        # element to save or submit the requisition
        self.save_button = page.locator("#create-button-requisition")
        self.submit_button = page.locator("#submit2-button-requisition")
        self.submit_confirmation_button = page.locator("button:has-text('Submit')")

        self.submit_confirmation_btn_selector = page.locator("//div[@role='dialog']//following::button")
        self.requisition_number = page.locator('//*[@id="jGrowl"]/div[2]/div[3]')
        # self.message_text = page.locator('//div[@class="jGrowl-notification"]//div[@class="message"]')

        self.proc_item_requisition = page.locator('//div[text()="Requisition"]')
        self.requisition_list_page = page.locator('/html/body/div[1]/div/div[5]/div[1]/div/ul/li[11]/ul/li[3]/a')
        # self.requisition_list = page.locator(
        #     '//div[text()="Requisition"]//following-sibling::ul//child::span[text()="Requisition List"]')
        self.requisition_list = page.locator(
            '//a[@href="#!requisition/list"]//span[text()="Requisition List"]'
        )
        self.active_framework_list = page.locator('id="fancybox-content"')
        self.application_for_selector = page.locator('#applicableForId')

        self.get_wishlist_button = page.locator("#check-wishList-button")
        self.browse_button = page.locator('//*[@id="selector-member-photo-input"]/div/span/span')

    def upload_requisition_item_document(self, file_path: str) -> bool:
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)

            print(f"Uploading file from : {file_path}")

            # Wait for OS file picker
            with self.page.expect_file_chooser() as fc_info:
                self.browse_button.click()

            file_chooser = fc_info.value
            file_chooser.set_files(file_path)

            # Click Confirm if required
            confirm_btn = self.page.get_by_role("button", name="Confirm")
            if confirm_btn.is_visible():
                confirm_btn.click()

            self.wait_for_timeout(2000)
            return True

        except Exception as e:
            print(f"File upload failed: {e}")
            return False

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def validate(self):
        expect(self.validation_point).to_be_visible()

    def navigate_to_requisition_list(self):
        self.proc_item_requisition.click()
        self.requisition_list.click()
        self.wait_for_timeout(2000)

    def setting_requisition_for(self, project_name):
        self.head_office_selector.click()  # selecting Head Office
        self.project_name_dropdown_selector.click()  # clicking on project name dropdown
        self.page.get_by_text(project_name).click()  # selecting given project name

    def setting_requisition_information(self, fund_source, fund_remarks):
        self.fund_source_selector.fill(fund_source)
        self.page.keyboard.press(" ")
        self.page.get_by_text(fund_source, exact=True).click()
        self.fund_source_remarks_selector.fill(fund_remarks)

    # Item details for single item selection
    def setting_requisition_details(self, item_info_1, item_info_2):
        self.item_info_selector.click()
        self.item_info_selector.fill(item_info_1)
        self.page.keyboard.press(' ')
        self.wait_for_timeout(2500)
        self.page.get_by_text(item_info_2).click()
        # self.item_measure_selector.click()
        # self.page.locator('//*[@id="17"]').click()
        # self.item_tor_selector.fill(item_tor)
        # self.item_qty_selector.fill(qty)
        # self.item_unit_price_selector.fill(unit_price)

    def setting_active_framework_list(self, agreement_info):
        self.character_input(self.fa_agreement_input, agreement_info)
        # self.wait_for_timeout(3000)
        self.page.get_by_text(agreement_info, exact=True).click()
        self.wait_for_timeout(2500)
        self.find_button.click()

    def setting_requisition_details_item_selection(self, item_information):
        self.item_info_selector.click()
        self.character_input(self.item_info_selector, item_information)
        # self.item_info_selector.fill(item_information)
        # self.wait_for_timeout(2500)
        self.page.get_by_text(item_information).click()
        self.wait_for_timeout(2500)

    def setting_active_framework_list_1(self, agreement_info):
        popup = self.page.locator(
            "div.main_container:has(h1:has-text('Active Framework List'))"
        )

        # Clear and search again (important for 2nd item)
        fa_input = popup.locator("input#faAgreementNo")
        fa_input.fill("")
        fa_input.fill(agreement_info)

        # Click framework from GRID only
        popup.locator(
            "#frameworkListGrid td[aria-describedby='frameworkListGrid_agreementNo'] a"
        ).filter(has_text=agreement_info).first.click()

        popup.locator("#find-button-requisitionList").click()

    def setting_application_for_both(self):
        self.application_for_selector.click()
        self.select_from_list_by_value(self.application_for_selector, "3")
        self.find_button.click()

    def setting_application_for_ho(self):
        self.application_for_selector.click()
        self.select_from_list_by_value(self.application_for_selector, "1")
        self.find_button.click()

    def setting_application_for_hcmp(self):
        self.application_for_selector.click()
        self.select_from_list_by_value(self.application_for_selector, "2")
        self.find_button.click()

    def finalize_item_quantity(self, item_quantity):
        self.input_in_element(self.item_qty_selector, item_quantity)
        self.wait_for_timeout(2500)

    def setting_requisition_for_details_1(self, gl_code):
        self.gl_code_dropdown.click()
        self.character_input(self.gl_input, gl_code)

    def setting_requisition_for_details(self, gl_code, item_remarks):
        self.gl_code_dropdown.click()
        self.wait_for_timeout(5000)
        self.gl_input.click()
        self.character_input(self.gl_input, gl_code)
        self.page.get_by_text(gl_code).click()
        self.req_for_remarks_selector.fill(item_remarks)
        self.add_to_grid_button.click()

    def finalize_item_unit_price(self, unit_price):
        self.item_unit_price_selector.click()
        self.item_unit_price_selector.clear()
        self.input_in_element(self.item_unit_price_selector, unit_price)

    def setting_item_gl_code(self, gl_code):
        self.gl_code_dropdown.click()
        self.wait_for_timeout(2500)
        self.gl_input.click()
        self.character_input(self.gl_input, gl_code)
        self.page.get_by_text(gl_code).click()

    def setting_item_remarks(self, item_remarks):
        self.req_for_remarks_selector.fill(item_remarks)

    def add_item_requisition_details_information_list(self):
        self.add_to_grid_button.click()

    def setting_same_schedule_for_date(self):
        self.click_on_btn(self.select_same_schedule)
        self.click_on_btn(self.date_picker_icon)
        self.click_on_btn(self.today)
        self.wait_for_timeout(2000)

    def setting_location_for_head_office(self, address):
        self.delivery_store_select.click()
        self.select_from_list_by_value(self.delivery_store_select, "1")
        self.location_input.click()
        self.input_in_element(self.location_input, address)

    def setting_location_for_central_store(self, address):
        self.delivery_store_select.click()
        self.select_from_list_by_value(self.delivery_store_select, "2")
        self.location_input.click()
        self.input_in_element(self.location_input, address)

    def setting_location_for_other_location(self, address):
        self.delivery_store_select.click()
        self.select_from_list_by_value(self.delivery_store_select, "-1")
        self.location_input.click()
        self.input_in_element(self.location_input, address)

    def setting_save_requisition(self) -> str:
        self.save_button.click()
        self.wait_to_load_element(self.requisition_number)
        value = self.requisition_number.text_content()
        print("Draft Requisition Number:" + value)
        return value.split(' ')[-1]
        # print("Last Value: " + val[-1])

    def submit_requisition(self) -> str:
        self.submit_button.click()
        self.wait_to_load_element(self.submit_confirmation_button)
        self.submit_confirmation_button.click()
        self.wait_to_load_element(self.requisition_number)
        value = self.requisition_number.text_content()
        return value.split(' ')[-1]

    def setting_requisition_for_details_2(self, gl_code, item_remarks):
        self.gl_code_dropdown.click()
        self.wait_for_timeout(5000)
        self.page.get_by_text(gl_code).click()
        self.req_for_remarks_selector.fill(item_remarks)
        self.add_to_grid_button.click()
