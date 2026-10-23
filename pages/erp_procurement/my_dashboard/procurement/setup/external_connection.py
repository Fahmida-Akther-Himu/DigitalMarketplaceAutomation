import os

from utils.basic_actionsdm import BasicActionsDM


class ExternalConnection(BasicActionsDM):
    # ERP Procurement > Setup > External Connection: Public / Private / Proxy IP, eTender, HoFin and Digital Marketplace
    # integration fields (by id), the 3 integration checkboxes and Update
    # Text fields checked by the automation (field id): the 3 IP Address fields use the system Proxy IP
    TEXT_FIELDS = {
        "eTender API Integration URL": "eTenderIPAddressId",
        "eTender Base URL": "eTenderBaseIPAddressId",
        "eTender Access Key": "eTenderConnectionIPAddressId",
        "eTender (restTender) E-Tender IP Address": "ApiETenderIpAddressId",
        "eTender (restTender) Key (API Consumer)": "ApiETenderKeyId",
        "HoFin API Integration URL": "HoFinIPAddressId",
        "HoFin Finance Access Key": "hoFinConnectionIPAddressId",
        "HoFin (restPayment) HoFin IP Address": "ApiHoFinIpAddressId",
        "HoFin (restPayment) Key (API Consumer)": "ApiHoFinKeyId",
        "MarketPlace API Integration URL": "marketPlaceIPAddressId",
        "MarketPlace Server IP Address": "marketPlaceConnectionIPAddressId",
        "DMP Start Date": "dmpStartDateId",
        "DMP Role IDP ID": "dmpRoleIDId",
        "MarketPlace (dmpApi) MarketPlace IP Address": "ApiDmpIpAddressId",
        "MarketPlace (dmpApi) Key (API Consumer)": "ApiDmpKeyId",
        "MarketPlace (ProcApiInfo) Username": "marketPlaceUserNameId",
        "MarketPlace (ProcApiInfo) Password": "marketPlacePasswordId",
    }
    # Required integration checkboxes (must stay selected)
    CHECKBOXES = {"IsETender": "isETenderId", "IsHoFin": "isHoFinId", "IsMarketPlace": "isMarketPlaceId"}
    # Fields that hold secrets (hidden in screenshots, never shown in the report)
    SECRET_FIELDS = ["eTenderConnectionIPAddressId", "ApiETenderKeyId", "hoFinConnectionIPAddressId", "ApiHoFinKeyId",
                     "ApiDmpKeyId", "marketPlacePasswordId", "ApiInventoryKeyId"]
    # CSS used only during the screenshot: the secret field text is transparent
    HIDE_SECRETS_STYLE = ", ".join(f"#{field}" for field in SECRET_FIELDS) + \
        " { color: transparent !important; text-shadow: none !important; }"

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        # Menu: Setup > External Connection
        self.setup_menu = page.locator('//div[text()="Setup"]')
        self.external_connection_link = page.locator('a.routable[href="#!tenderReport/checkETenderConnection"]:visible')
        self.page_heading = page.locator("text=External Connection").last
        # System IPs (read only)
        self.public_ip = page.locator("#publicIpId")
        self.private_ip = page.locator("#privateIpId")
        self.proxy_ip = page.locator("#proxyIPId")
        self.latest_transaction_number = page.locator("#thirdPartyBillPayableLastTransactionId")
        self.update_button = page.locator("#checkETenderConnection")
        # ERP notification (jGrowl) after Update / Push to DM
        self.notifications = page.locator("div#jGrowl div.jGrowl-notification")

    def open_external_connection(self):
        # Why: the page is opened from the Procurement menu like a user (Setup > External Connection); When: start of
        # the check and after Push to DM
        self.setup_menu.click()
        self.external_connection_link.first.click()
        self.proxy_ip.wait_for(state="visible", timeout=60000)
        self.page.wait_for_timeout(3000)

    def field(self, field_id):
        # Why: one field of the page by its id; When: reading and updating the fields
        return self.page.locator(f"#{field_id}")

    def read_text_fields(self):
        # Why: the current value of every checked text field; When: before and after the update
        return {label: self.field(field_id).input_value().strip() for label, field_id in self.TEXT_FIELDS.items()}

    def read_checkboxes(self):
        # Why: the state of the 3 required integration checkboxes; When: before and after the update
        return {label: self.field(field_id).is_checked() for label, field_id in self.CHECKBOXES.items()}

    def read_system_ips(self):
        # Why: the system Public / Private / Proxy IP shown at the top of the page; When: Proxy IP check
        return {"Public IP": self.public_ip.input_value().strip(), "Private IP": self.private_ip.input_value().strip(),
                "Proxy IP": self.proxy_ip.input_value().strip()}

    def select_checkbox(self, label):
        # Why: a required checkbox is selected only when it is not selected yet (never deselected); When: update
        checkbox = self.field(self.CHECKBOXES[label])
        if not checkbox.is_checked():
            checkbox.check()
        return checkbox.is_checked()

    def set_text_field(self, label, value):
        # Why: the expected value is entered in a field; When: update of a wrong or missing value
        self.field(self.TEXT_FIELDS[label]).fill(value)

    def click_update(self):
        # Why: Update saves the External Connection (always clicked, also when nothing changed); When: update step
        self.update_button.scroll_into_view_if_needed()
        self.update_button.click()

    def read_notification(self, timeout_ms=20000):
        # Why: the message shown after Update / Push to DM (header, text and its type: success / error / warning);
        # When: after Update and Push to DM. Returns {"type", "text"} ({"type": "", "text": ""} when none)
        for _ in range(timeout_ms // 500):
            if self.notifications.count():
                notification = self.notifications.last
                classes = notification.get_attribute("class") or ""
                kind = next((name for name in ("success", "error", "warning", "info") if name in classes), "")
                return {"type": kind, "text": " ".join(notification.inner_text().replace("×", " ").split())}
            self.page.wait_for_timeout(500)
        return {"type": "", "text": ""}

    def get_masked_screenshot(self, name):
        # Why: screenshots must not show keys or the password: their text is transparent only for the screenshot;
        # When: every screenshot of this page
        screenshot_path = os.getcwd() + "/screenshots_taken/" + name + ".png"
        self.page.screenshot(path=screenshot_path, full_page=True, timeout=60000, style=self.HIDE_SECRETS_STYLE)
