import os
import re

from utils.basic_actionsdm import BasicActionsDM


class ManageExternalConfig(BasicActionsDM):
    # Administration > Configuration > Settings > Manage External Config: External API grid (API Name, External API URL,
    # External API Key, Edit / Update / Cancel per row), Keyword search and page size
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        # Menu: Configuration > Settings > Manage External Config
        self.configuration_menu = page.locator("a.nav-link", has_text=re.compile(r"^\s*Configuration\s*$"))
        self.settings_menu = page.locator("a.nav-link", has_text=re.compile(r"^\s*Settings\s*$"))
        self.manage_external_config_link = page.locator('a[href="/Admin/Setting/ManageExternalConfig"]')
        self.page_heading = page.locator("h1", has_text="Manage External Config").first
        # Search
        self.keyword_input = page.locator("#Keyword")
        self.search_button = page.get_by_role("button", name="Search")
        # Grid (DataTables)
        self.grid_rows = page.locator("#manage-grid tbody tr")
        self.key_cells = page.locator("#manage-grid td[data-columnname='Key']")
        self.page_size_select = page.locator("select[name='manage-grid_length']")
        self.grid_info = page.locator("#manage-grid_info")
        self.next_page_item = page.locator("#manage-grid_next")
        self.next_page_link = page.locator("#manage-grid_next a")
        # Notification after Update ("Data updated successfully." or an error)
        self.visible_alerts = page.locator(".alert:visible, [role='alert']:visible, .toast:visible")

    def open_manage_external_config(self):
        # Why: the page is opened from the Administration menu like a user; the menus toggle, so each one is clicked
        # only when its submenu is hidden; When: start of the External API configuration check
        if not self.manage_external_config_link.is_visible():
            if not self.settings_menu.is_visible():
                self.configuration_menu.click()
            self.settings_menu.click()
        self.manage_external_config_link.click()
        self.page.wait_for_load_state("domcontentloaded")
        self.wait_for_grid()
        # The menu is shown from the top again: the mouse would hover another menu item (e.g. Customer settings); it
        # is moved onto the grid item count on the right, away from the menu (hovering the small sidebar opens it
        # over the page)
        self.grid_info.hover()

    def grid_counts(self):
        # Why: the grid info "1-25 of 25 items" gives the first and last shown record and the total number of
        # records; When: page size, search and count checks. Returns (first, last, total), (0, 0, 0) when empty
        numbers = [int(number) for number in re.findall(r"\d+", self.grid_info.inner_text())]
        return tuple(numbers[:3]) if len(numbers) >= 3 else (0, 0, 0)

    def wait_for_grid(self, timeout_ms=30000):
        # Why: the grid is redrawn after the page size, a search, a page change or an Update; the rows are read only
        # when the shown rows match the grid info; When: after every grid action
        self.page.wait_for_timeout(1500)
        for _ in range(timeout_ms // 500):
            first, last, total = self.grid_counts()
            shown = len(self.read_rows())
            if (total == 0 and shown == 0) or (total and shown == last - first + 1):
                return
            self.page.wait_for_timeout(500)
        raise AssertionError(f"Manage External Config grid not refreshed: {self.grid_info.inner_text()}")

    def show_items(self, count):
        # Why: the grid shows 15 records by default; a bigger page size shows all of them; When: before reading rows
        self.page_size_select.select_option(str(count))
        self.wait_for_grid()

    def read_rows(self):
        # Why: API Name, External API URL and External API Key of the shown rows (the "no data" row is skipped);
        # When: reading the grid
        rows = []
        for row in self.grid_rows.all():
            name_cell = row.locator("td[data-columnname='Name']")
            if not name_cell.count():
                continue
            rows.append({"name": " ".join(name_cell.inner_text().split()),
                         "url": row.locator("td[data-columnname='Url']").inner_text().strip(),
                         "key": row.locator("td[data-columnname='Key']").inner_text().strip()})
        return rows

    def read_all_rows(self, page_size=100):
        # Why: every record of the grid (page size 100, then the next pages when there are more records);
        # When: verification and search checks
        self.show_items(page_size)
        rows = self.read_rows()
        while "disabled" not in (self.next_page_item.get_attribute("class") or ""):
            self.next_page_link.click()
            self.wait_for_grid()
            rows += self.read_rows()
        return rows

    def row_of(self, api_name):
        # Why: a record is found by its exact API Name (never by row position); When: Edit / Update of that record
        return self.grid_rows.filter(has=self.page.locator(
            "td[data-columnname='Name']", has_text=re.compile(rf"^\s*{re.escape(api_name)}\s*$")))

    def edit_record(self, api_name):
        # Why: Edit of the row of this API Name turns its URL and Key cells into inputs; When: updating a record
        self.row_of(api_name).locator("a[id^='buttonEdit_manage_grid']").click()
        self.row_of(api_name).locator("td[data-columnname='Url'] input").wait_for(state="visible", timeout=10000)

    def is_in_edit_mode(self, api_name):
        # Why: only the row of this API Name must be in edit mode (URL and Key inputs, Update shown); When: before the
        # new values are entered
        row = self.row_of(api_name)
        return (row.count() == 1 and row.get_attribute("editState") == "editState"
                and row.locator("td[data-columnname='Url'] input").is_visible()
                and row.locator("td[data-columnname='Key'] input").is_visible()
                and row.locator("a[id^='buttonConfirm_manage_grid']").is_visible())

    def fill_record(self, api_name, url, key):
        # Why: the expected URL and key are entered in the row of this API Name (a blank key clears the field);
        # When: updating a record in edit mode
        row = self.row_of(api_name)
        row.locator("td[data-columnname='Url'] input").fill(url)
        row.locator("td[data-columnname='Key'] input").fill(key)

    def click_update(self, api_name):
        # Why: Update saves the row of this API Name (a modified row must never be left unsaved); When: after the
        # values are entered
        self.row_of(api_name).locator("a[id^='buttonConfirm_manage_grid']").click()

    def read_notification(self, timeout_ms=15000):
        # Why: the confirmation ("Data updated successfully.") or error message shown after Update; When: after Update
        for _ in range(timeout_ms // 500):
            texts = [" ".join(text.split()) for text in self.visible_alerts.all_inner_texts() if text.strip()]
            if texts:
                return " | ".join(texts)
            self.page.wait_for_timeout(500)
        return ""

    def search_keyword(self, keyword):
        # Why: the grid can be searched by a Keyword (e.g. an External API Key); a blank keyword shows all records;
        # When: search by External API Key check
        self.keyword_input.fill(keyword)
        self.search_button.click()
        self.wait_for_grid()

    def get_masked_screenshot(self, name):
        # Why: screenshots must not show API keys: the text of the External API Key cells (and their inputs) and of
        # the Keyword box is made invisible only for the screenshot (no colour block, the page looks normal);
        # When: every screenshot of this page
        screenshot_path = os.getcwd() + "/screenshots_taken/" + name + ".png"
        self.page.screenshot(path=screenshot_path, full_page=True, timeout=60000, style=self.HIDE_KEYS_STYLE)

    # CSS used only during the screenshot: the key text is transparent
    HIDE_KEYS_STYLE = ("#manage-grid td[data-columnname='Key'], #manage-grid td[data-columnname='Key'] input, #Keyword "
                       "{ color: transparent !important; text-shadow: none !important; }")
