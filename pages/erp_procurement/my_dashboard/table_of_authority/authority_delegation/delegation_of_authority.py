# from pages.digital_marketplace.dashboard_page import DashboardPage
# from pages.procurement_home_page import ProcurementHomePage

from playwright.sync_api import expect
from pathlib import Path

from pages.erp_procurement.procurement_home_page import ProcurementHomePage


class DelegationOfAuthority(ProcurementHomePage):
    def __init__(self, page, logger=None):
        super().__init__(page, logger)

        self.logger = logger

        # ============================================================
        # Page validation locators
        # ============================================================

        self.page_heading = page.get_by_role(
            "heading",
            name="Create Delegation Of Authority",
            exact=True
        )

        self.delegation_form = page.locator(
            "#gFormDelegationOfAuthority"
        )

        self.delegated_employee_input = page.locator(
            "#employeeInfo"
        )

        self.employee_autocomplete_list = page.locator("li.ui-menu-item")

        self.employee_search_button = page.locator(
            "#search-btn-employee-register-id"
        )

        # ============================================================
        # TOA Category locators
        # ============================================================

        self.toa_category_required_checkbox = page.locator(
            "#categoryNotReq"
        )
        self.module_info_container = page.locator(
            "#moduleInfo"
        )

        self.module_info_dropdown = page.locator(
            "#moduleInfoId"
        )

        # self.toa_category_required_search = page.locator('input[class="search empty ui-widget-content ui-corner-all"]')
        # TOA Category container
        self.toa_category_container = self.page.locator(
            "#toaCategory-map-ajax"
        )

        # Available TOA category section
        self.toa_category_available_section = (
            self.toa_category_container.locator(
                "div.available"
            )
        )

        # Unique TOA category search field
        self.toa_category_required_search = (
            self.toa_category_available_section.locator(
                "input.search"
            )
        )

        # Available TOA category list
        self.toa_category_available_list = (
            self.toa_category_available_section.locator(
                "ul.available.connected-list"
            )
        )
        # Selected TOA category section
        self.toa_category_selected_section = (
            self.toa_category_container.locator(
                "div.selected"
            )
        )

        # Selected TOA category list
        self.toa_category_selected_list = (
            self.toa_category_selected_section.locator(
                "ul.selected.connected-list"
            )
        )

        # Selected item count
        self.selected_toa_category_count = (
            self.toa_category_selected_section.locator(
                "span.count"
            )

        )

        # ============================================================
        # Date locators
        # ============================================================

        self.start_date_input = page.locator(
            "#startDate"
        )

        self.start_date_calendar_icon = page.locator(
            '#startDate + img.ui-datepicker-trigger'
        )

        self.end_date_input = page.locator(
            "#endDate"
        )

        self.end_date_calendar_icon = page.locator(
            '#endDate + img.ui-datepicker-trigger'
        )

        self.date_picker = page.locator(
            "#ui-datepicker-div"
        )

        # ============================================================
        # Project-Department Mapping locator
        # ============================================================
        self.project_department_mapping_checkbox = page.locator(
            'input[type="checkbox"][onclick*="project"]'
        )
        self.project_department_mapping_checkbox_1 = page.locator(
            'projectDeptNotReq')

        # ============================================================
        # Remarks and action button locators
        # ============================================================

        self.remarks_input = page.locator(
            "#remarks"
        )

        self.create_button = page.locator(
            "#create-button"
        )

        self.cancel_button = page.locator(
            'input[name="clearFormButtonHrDelegationOfAuthority"]'
        )
        # Success notification title
        self.success_notification_title = page.locator(
            "div.jGrowl-message div.header"
        )

        # Success notification message
        self.success_notification_message = page.locator(
            "div.jGrowl-message div.message"
        )

        self.toast_msg = page.locator('//*[@id="jGrowl"]/div[2]/div[3]')

    ##################### small helper so we can log easily #####################

    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    # ================================================================
    # Page validation
    # ================================================================

    def validate(self):
        self._log("Validating Delegation of Authority page")

        expect(self.page_heading).to_be_visible(timeout=10000)
        expect(self.delegation_form).to_be_visible(timeout=10000)
        expect(self.delegated_employee_input).to_be_visible(timeout=10000)
        expect(self.create_button).to_be_visible(timeout=10000)

    # ================================================================
    # Step 2: Select delegated employee
    # ================================================================

    def select_delegated_employee(self, employee_search_text: str):
        self._log(
            f"Selecting delegated employee: {employee_search_text}"
        )

        self.delegated_employee_input.click()
        self.delegated_employee_input.fill(employee_search_text)
        self.page.keyboard.type(" ")
        self.page.keyboard.press("Backspace")
        employee_option = self.page.get_by_text(employee_search_text)
        employee_option.wait_for(state="visible", timeout=5000)
        employee_option.hover()
        employee_option.click()

    # ================================================================
    # Step 3: Select Is TOA Category Required
    # ================================================================

    def select_toa_category_required(self):
        self._log("Selecting Is TOA Category Required")

        self.toa_category_required_checkbox.check()

        expect(
            self.toa_category_required_checkbox
        ).to_be_checked()

        expect(
            self.module_info_container
        ).to_be_visible(timeout=10000)

        expect(
            self.module_info_dropdown
        ).to_be_visible(timeout=10000)

    # ================================================================
    # Step 4: Select procurement module
    # ================================================================

    def select_module_without_mapping(self, module_name: str):
        self._log(f"Selecting module: {module_name}")

        self.module_info_dropdown.select_option(
            label=module_name
        )
        selected_option = self.module_info_dropdown.locator(
            "option:checked"
        )

        expect(
            selected_option
        ).to_have_text(module_name)

        # expect(
        #     self.module_info_dropdown
        # ).to_have_value("6")

        self.wait_for_timeout(5000)

    # ============
    # with mapping
    # ============
    def select_module(self, module_name: str):
        """
        Select module from 'Module Info' dropdown.

        Available modules:
            -Select Module Info-
            application-common
            complaint-management
            Human Resources
            Microfinance
            Accounts
            procurement
            Administration
            Budget
            Fixed Asset
            Admin
            Inventory
            ePMS
        """

        self._log(f"Selecting module: {module_name}")

        module_value_map = {
            "-Select Module Info-": "null",
            "application-common": "1",
            "complaint-management": "2",
            "Human Resources": "3",
            "Microfinance": "4",
            "Accounts": "5",
            "procurement": "6",
            "Administration": "7",
            "Budget": "8",
            "Fixed Asset": "9",
            "Admin": "10",
            "Inventory": "11",
            "ePMS": "31",
        }

        if module_name not in module_value_map:
            raise ValueError(
                f"Unsupported module '{module_name}'. "
                f"Available modules: {', '.join(module_value_map.keys())}"
            )

        self.module_info_dropdown.select_option(
            value=module_value_map[module_name]
        )

        expect(
            self.module_info_dropdown
        ).to_have_value(
            module_value_map[module_name]
        )

        self.wait_for_timeout(2000)

    # ================================================================
    # Steps 5 and 6:
    # Search TOA category and click the plus icon
    # ================================================================

    def search_and_add_toa_category(self, category_name: str):
        self._log(
            f"Searching TOA category: {category_name}"
        )

        self.toa_category_required_search.wait_for(
            state="visible",
            timeout=10000
        )

        self.toa_category_required_search.click()
        self.toa_category_required_search.clear()

        self.character_input(
            self.toa_category_required_search,
            category_name
        )

        available_category = (
            self.toa_category_available_list.locator(
                f'li[title*="{category_name}"]'
            )
        )

        available_category.wait_for(
            state="visible",
            timeout=10000
        )

        available_category.locator(
            "a.action span.ui-icon-plus"
        ).click()

        selected_category = (
            self.toa_category_selected_list.locator(
                f'li[title*="{category_name}"]'
            )
        )

        selected_category.wait_for(
            state="visible",
            timeout=10000
        )

    # ================================================================
    # Steps 7 and 8: Select Start Date and End Date
    # ================================================================

    def select_start_date(self, day: str):
        self._log(f"Selecting start date day: {day}")

        self.start_date_input.scroll_into_view_if_needed()
        self.start_date_input.fill(day)
        self.wait_for_timeout(2000)

    def select_end_date(self, day: str):
        self._log(f"Selecting start date day: {day}")

        self.end_date_input.scroll_into_view_if_needed()
        self.end_date_input.fill(day)
        self.wait_for_timeout(2000)

    def select_end_date_1(self, day: str):
        self._log(f"Selecting end date day: {day}")

        self.end_date_calendar_icon.click()

        expect(
            self.date_picker
        ).to_be_visible(timeout=5000)

        end_day = self.date_picker.locator(
            "td:not(.ui-datepicker-other-month) "
            f'a.ui-state-default:text-is("{day}")'
        )

        expect(end_day).to_be_visible(timeout=5000)
        end_day.click()

        expect(
            self.end_date_input
        ).not_to_have_value("")

    def enter_delegation_dates(
            self,
            start_date: str,
            end_date: str
    ):
        """
        Alternative method when the date values are known.

        Expected format:
        DD-MM-YYYY
        """

        self._log(
            f"Entering delegation dates: {start_date} to {end_date}"
        )

        self.start_date_input.fill(start_date)
        self.end_date_input.fill(end_date)

        expect(
            self.start_date_input
        ).to_have_value(start_date)

        expect(
            self.end_date_input
        ).to_have_value(end_date)

    # ================================================================
    # Step 9: Upload attachment
    # ================================================================

    def upload_delegation_attachment(
            self,
            file_path: str
    ) -> str:
        self._log(
            f"Uploading Delegation of Authority attachment: {file_path}"
        )

        attachment = Path(file_path).expanduser().resolve()

        if not attachment.exists():
            raise FileNotFoundError(
                f"Attachment file was not found: {attachment}"
            )

        self.attachment_file_input.set_input_files(
            str(attachment)
        )

        expect(
            self.uploaded_file_hidden_value
        ).not_to_have_value("", timeout=30000)

        uploaded_file_value = (
            self.uploaded_file_hidden_value.input_value()
        )

        self._log(
            f"Uploaded attachment value: {uploaded_file_value}"
        )

        return uploaded_file_value

    # ================================================================
    # Step 10: Enter remarks
    # ================================================================

    def enter_remarks(self, remarks: str):
        self._log("Entering delegation remarks")

        if len(remarks) > 500:
            raise ValueError(
                "Remarks cannot contain more than 500 characters."
            )

        self.remarks_input.fill(remarks)

        expect(
            self.remarks_input
        ).to_have_value(remarks)

    # def confirm_submission(self):
    #     self.submit_confirmation.scroll_into_view_if_needed()
    #     self.submit_confirmation.click()
    #     self.toast_msg.wait_for(state="visible", timeout=10000)
    #     toast_msg_text = self.toast_msg.text_content()
    #     print(toast_msg_text)
    #     self.wait_for_timeout(5000)

    # def verify_delegation_creation_success(self):
    #     self._log("Verifying delegation creation success message")
    #
    #     expect(
    #         self.success_notification_title
    #     ).to_be_visible(timeout=10000)
    #
    #     expect(
    #         self.success_notification_message
    #     ).to_be_visible(timeout=10000)
    #
    #     title = self.success_notification_title.inner_text().strip()
    #     message = self.success_notification_message.inner_text().strip()
    #
    #     success_message = f"{title} - {message}"
    #
    #     # Print in terminal
    #     print(f"\n[SUCCESS] {success_message}")
    #
    #     # Log in report/logger
    #     self._log(success_message)
    #
    #     return success_message

    # ================================================================
    # Step 11: Click Create
    # ================================================================

    def click_create_button_and_delegation_confirmation(self):
        self._log("Clicking the Create button")

        expect(
            self.create_button
        ).to_be_enabled(timeout=10000)

        self.create_button.click()
        self.wait_for_timeout(5000)

        self.toast_msg.wait_for(state="visible", timeout=10000)
        toast_msg_text = self.toast_msg.text_content()
        print(toast_msg_text)
        self.wait_for_timeout(5000)

    # ================================================================
    # Complete business flow
    # ================================================================

    # def create_delegation_of_authority(
    #         self,
    #         employee_search_text: str,
    #         employee_full_text: str,
    #         category_name: str,
    #         start_date: str,
    #         end_date: str,
    #         attachment_path: str,
    #         remarks: str,
    #         module_name: str = "procurement"
    # ):
    #     self.select_delegated_employee(
    #         employee_search_text,
    #         employee_full_text
    #     )
    #
    #     self.select_toa_category_required()
    #
    #     self.select_module(module_name)
    #
    #     self.search_and_add_toa_category(
    #         category_name
    #     )
    #
    #     self.enter_delegation_dates(
    #         start_date,
    #         end_date
    #     )
    #
    #     self.upload_delegation_attachment(
    #         attachment_path
    #     )
    #
    #     self.enter_remarks(remarks)
    #
    #     self.click_create_button()
