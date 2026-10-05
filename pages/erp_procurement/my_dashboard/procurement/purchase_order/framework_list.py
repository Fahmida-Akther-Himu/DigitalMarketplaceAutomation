import re
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
        # Framework List grid rows, pager (page size and Next) and paging info
        self.agreement_rows = page.locator("#frameworkListGrid tr.jqgrow")
        self.page_size_select = page.locator("#frameworkListGridPager select.ui-pg-selbox")
        self.next_page_button = page.locator("#frameworkListGridPager #next")
        self.paging_info = page.locator("#frameworkListGridPager .ui-paging-info")
        self.price_review_legend = page.locator("span.item-legend.price_review_item")

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

    def search_agreement_with_enter(self, search_framework_agreement):
        # The FA No. search filters the list after Enter (wait until the list is fully loaded first)
        self.agreement_rows.first.wait_for(state="visible", timeout=60000)
        self.wait_for_timeout(3000)
        self.search_framework_number.click()
        self.search_framework_number.fill(search_framework_agreement)
        self.search_framework_number.press("Enter")
        self.wait_for_timeout(5000)

    def find_exact_agreement_row(self, base_fa_no, max_pages=20, exact_version=False):
        # Exact base FA No. with an optional ERP version (/V1, /V2 ...), never BPD/2026/FA-50, FA-51 ...
        # exact_version=True: only this exact FA No. (no other version)
        version_part = "" if exact_version else "(/V\\d+)?"
        fa_no_pattern = re.compile(rf"^\s*{re.escape(base_fa_no)}{version_part}\s*$")
        agreement_row = self.agreement_rows.filter(
            has=self.page.locator("td[aria-describedby='frameworkListGrid_agreementNo']", has_text=fa_no_pattern))
        # Not on this page: go to the next page and check again
        for _ in range(max_pages):
            if agreement_row.count():
                break
            print(f"Agreement {base_fa_no} not found in: {self.paging_info.inner_text()}")
            if "ui-state-disabled" in (self.next_page_button.get_attribute("class") or ""):
                break
            self.next_page_button.click()
            self.wait_for_timeout(5000)
        assert agreement_row.count(), f"Agreement {base_fa_no} not found in the Framework List"
        agreement_row = agreement_row.first
        fa_no = agreement_row.locator("td[aria-describedby='frameworkListGrid_agreementNo']").inner_text().strip()
        print(f"Agreement found: {fa_no} ({self.paging_info.inner_text()})")
        return agreement_row, fa_no

    def get_row_initiator(self, agreement_row):
        # Initiator column, e.g. "[00000761]-Md. Yusuf Ali Bhuiyan Manager, Procurement" -> ("761", name)
        initiator_text = agreement_row.locator(
            "td[aria-describedby='frameworkListGrid_initiatorName']").inner_text().strip()
        initiator_pin = initiator_text.split("[")[1].split("]")[0]
        initiator_name = initiator_text.split("]-", 1)[1].splitlines()[0].strip()
        print(f"Agreement initiator: {initiator_pin} - {initiator_name}")
        return str(int(initiator_pin)), initiator_name

    def get_row_status_info(self, agreement_row):
        # Status column, e.g. "Reviewer[00260331]-MAHADE HASSAN SHARKAR Manager, Procurement"
        status_text = agreement_row.locator("td[aria-describedby='frameworkListGrid_status']").inner_text().strip()
        status_info = {"Agreement Status": " ".join(status_text.split()), "Reviewer PIN": "",
                       "Reviewer Name": "", "Reviewer Designation": ""}
        if "[" in status_text and "]" in status_text:
            status_info["Agreement Status"] = status_text.split("[")[0].strip()
            status_info["Reviewer PIN"] = str(int(status_text.split("[")[1].split("]")[0]))
            person_lines = [line.strip() for line in status_text.split("]", 1)[1].lstrip("-").splitlines()
                            if line.strip()]
            status_info["Reviewer Name"] = person_lines[0] if person_lines else ""
            status_info["Reviewer Designation"] = " ".join(person_lines[1:])
        for label, value in status_info.items():
            print(f"{label}: {value}")
        return status_info

    def get_price_review_legend_color(self):
        # Colour box of the "Price to be reviewed" legend in the Framework List header
        return self.price_review_legend.evaluate("box => getComputedStyle(box).backgroundColor")

    def get_row_color(self, agreement_row):
        # Background colour of the agreement row (row colour, or its first cell colour)
        return agreement_row.evaluate("""(row) => {
            const rowColor = getComputedStyle(row).backgroundColor;
            const cellColor = getComputedStyle(row.cells[1] || row.cells[0]).backgroundColor;
            return rowColor !== 'rgba(0, 0, 0, 0)' ? rowColor : cellColor;
        }""")
