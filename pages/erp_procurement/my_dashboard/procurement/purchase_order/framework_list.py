from utils.basic_actionsdm import BasicActionsDM


class FrameworkList(BasicActionsDM):
    def __init__(self, page, logger=None):
        super().__init__(page)
        self.logger = logger
        self.page = page

        # self.vendor_info = page.locator('//*[@id="proposal-process"]/div[1]/div/div[4]/div/div/div[2]')
        self.search_framework_number = page.locator("input[id='keywords']")
        self.search_icon = page.locator("span[class='ui-button-icon-primary ui-icon ui-icon-search']")

        self.approval_pending_checkbox = page.locator("input[id='isOnAuthorization']")
        self.agreement_expired_checkbox = page.locator("input[id='isOnExpired']")
        self.agreement_on_live_checkbox = page.locator("input[id='isOnlive']")
        self.debar_or_banned_checkbox = page.locator("input[id='isDebar']")

        self.hub_selection = page.locator("select[id='hub']")
        self.fa_no_link = page.locator("a[style='text-decoration: underline;'][onclick^='showDetails']")
        self.status_cell = page.locator("td[aria-describedby='frameworkListGrid_status']")

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)

    def get_status_info(self):
        # unique locator for the status column
        status_cell = self.page.locator("td[aria-describedby='frameworkListGrid_status']")

        status_text = status_cell.inner_text()
        print(status_text)
        # status_text = status_cell.inner_text().strip()

        # If no bracketed ID exists, print only the status and exit
        if "[" not in status_text or "]" not in status_text:
            print("Status: \n", status_text)
            return status_text

        # Otherwise extract the bracketed ID
        approver_id = status_text.split("[")[1].split("]")[0]

        print("Status: \n", status_text)
        print("Approver ID: \n", approver_id)

        return approver_id

    def get_status_info_1(self):
        # unique locator for the status column
        status_cell = self.page.locator("td[aria-describedby='frameworkListGrid_status']")

        # full text
        status_text = status_cell.inner_text()
        print("Status Full Text:\n", status_text)

        # extract approver id (text inside [])
        approver_id = ""
        if "[" in status_text and "]" in status_text:
            approver_id = status_text.split("[")[1].split("]")[0]

        print("Approver ID:", approver_id)

        # check if PIN or something else exists
        if "pin" in status_text.lower():
            print("Pin: Available")
        else:
            print("Pin: Not available")

        return approver_id

    def agreement_status_print(self):
        status_text = self.status_cell.text_content()
        print(status_text)

        def extract_approver_id(text: str) -> str:
            if '[' in text and ']' in text:
                return text.split('[')[1].split(']')[0]
            return ""

        approver_id = extract_approver_id(status_text)
        print("Approver ID:", approver_id)

    def search_agreement(self, search_framework_agreement):
        self.search_framework_number.click()
        self.search_framework_number.clear()
        self.input_in_element(self.search_framework_number, search_framework_agreement)
        self.search_icon.click()

    def find_agreement_approver_info(self):
        agreement_status_value = self.agreement_status.text_content()
        print("Agreement status value:", agreement_status_value)

    def find_agreement_approver_id_2(self) -> str:
        agreement_status_value = self.agreement_status.text_content()
        print("Agreement status value:", agreement_status_value)
        agreement_approver_id = agreement_status_value.split('[')[-1].split(']')[0]
        # approver_id = status_value.split('[')[-1].split(']')[0]
        print("Agreement approver ID(without type cust): " + agreement_approver_id)
        return agreement_approver_id

    def find_agreement_approver_id_3(self):
        approver_locator = self.page.locator("//table//tr[1]/td[5]")
        return approver_locator.inner_text().strip()

    def find_agreement_approver_id_1(self):
        # Print for debug
        row_text = self.page.locator("//table//tr[1]").inner_text()
        print("DEBUG ROW:", row_text)

        # FIX COLUMN INDEX HERE
        approver = self.page.locator("//table//tr[1]/td[5]").inner_text().strip()
        print("DEBUG Approver ID:", approver)

        return approver
