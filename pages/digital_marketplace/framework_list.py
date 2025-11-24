from re import search

from pages.digital_marketplace.framework_information import FrameworkInformation
from utils.basic_actionsdm import BasicActionsDM


class FrameworkList(BasicActionsDM):
    def __init__(self, page):
        super().__init__(page)
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

        # self.agreement_status = page.locator("//table[@id='frameworkListGrid']/tbody/tr[2]/child::td[14]")

        # self.status_cell = page.locator(
        #     "#frameworkListGrid tbody tr:first-child td[aria-describedby='frameworkListGrid_status']"
        # )

    # def get_agreement_status_info(self) -> dict:
    #     # Wait until at least one row is visible
    #     self.page.wait_for_selector("#frameworkListGrid tbody tr:first-child td", timeout=60000)
    #     # Unique locator for status column
    #     # status_cell = self.page.locator(
    #     #     "#frameworkListGrid tbody tr:first-child td[aria-describedby='frameworkListGrid_status']"
    #     # )
    #     status_cell = self.page.locator("#frameworkListGrid tbody tr").first.locator("td").nth(6)
    #     self.wait_for_timeout(3000)
    #
    #     # Get full raw text
    #     raw_text = status_cell.inner_text(timeout=30000).strip()
    #     print("RAW STATUS TEXT:", raw_text)
    #
    #     # Split lines
    #     lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    #
    #     result = {
    #         "status": None,
    #         "approver_id": None,
    #         "name": None,
    #         "designation": None,
    #         "pin": None,
    #         "full_text": raw_text
    #     }
    #
    #     # 1) Extract Status (line 1)
    #     if len(lines) > 0:
    #         result["status"] = lines[0]
    #
    #     # 2) Extract Approver ID + Name
    #     # Looks like:  [00260331]-MD. MAHADE HASSAN SHARKAR
    #     import re
    #     match = re.search(r"\[(\d+)\]-(.+)", raw_text)
    #     if match:
    #         result["approver_id"] = match.group(1).strip()
    #         result["name"] = match.group(2).strip()
    #
    #     # 3) Extract designation (bottom line)
    #     if len(lines) >= 3:
    #         result["designation"] = lines[-1]
    #
    #     # 4) Extract PIN if present (SU003435 pattern)
    #     pin_match = re.search(r"\b[A-Z]{2}\d{6}\b", raw_text)
    #     if pin_match:
    #         result["pin"] = pin_match.group(0)
    #
    #     print("PARSED STATUS INFO:", result)
    #     return result
    #
    # def find_agreement_approver_id(self):
    #     status_cell = self.page.locator(
    #         "#frameworkListGrid tbody tr:first-child td[aria-describedby='frameworkListGrid_status']"
    #     )
    #
    #     status_cell.wait_for()  # ensure row is loaded
    #
    #     text = status_cell.inner_text().strip()
    #     print("STATUS TEXT:", text)
    #
    #     import re
    #     match = re.search(r"\[(\d+)\]", text)
    #     if not match:
    #         raise ValueError(f"Approver ID not found in status cell: {text}")
    #
    #     return match.group(1)

    # def find_agreement_approver_id(self) -> str:
    #     # Unique locator for status column (first row)
    #     status_cell = self.page.locator(
    #         "#frameworkListGrid tbody tr[1] td[aria-describedby='frameworkListGrid_status']"
    #     )
    #
    #     full_text = status_cell.inner_text().strip()
    #     print("STATUS FULL TEXT:", full_text)
    #
    #     # Extract ID in brackets: [00260331]
    #     match = re.search(r"\[(\d+)\]", full_text)
    #
    #     if match:
    #         approver_id = match.group(1)
    #         print("EXTRACTED APPROVER ID:", approver_id)
    #         return approver_id
    #     else:
    #         raise ValueError(f"Approver ID not found in status text: {full_text}")

    def search_agreement(self, search_framework_agreement):
        self.search_framework_number.click()
        self.search_framework_number.clear()
        self.input_in_element(self.search_framework_number, search_framework_agreement)
        self.search_icon.click()

    def find_agreement_approver_info(self):
        agreement_status_value = self.agreement_status.text_content()
        print("Agreement status value:", agreement_status_value)

    #
    # def find_agreement_status(self) -> str:
    #     status_value = self.requisition_status.text_content()
    #     print("Requisition Status: " + status_value)
    #     return status_value

    def find_agreement_approver_id_2(self) -> str:
        agreement_status_value = self.agreement_status.text_content()
        print("Agreement status value:", agreement_status_value)
        agreement_approver_id = agreement_status_value.split('[')[-1].split(']')[0]
        # approver_id = status_value.split('[')[-1].split(']')[0]
        print("Agreement approver ID(without type cust): " + agreement_approver_id)
        return agreement_approver_id

    #
    # row = self.page.locator("//table//tr[1]").inner_text()
    # print("DEBUG ROW TEXT:", row)
    #
    # def find_agreement_approver_id_1(self):
    #     locator = self.page.locator("//table//tr[1]/td[14]")  # Example: 5th column
    #     approver_text = locator.inner_text().strip()
    #     print("Approver ID text:", approver_text)
    #     return approver_text

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

    # def find_approver_id(self) -> str:
    #     status_value = self.requisition_status.text_content()
    #     approver_id = status_value.split('[')[-1].split(']')[0]
    #     print("Approver ID: " + approver_id)
    #     return approver_id
