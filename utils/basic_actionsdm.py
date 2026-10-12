# this page contains all the common actions to be performed in this project
from playwright.sync_api import expect
from datetime import datetime, timedelta
import os
import re
from typing import Optional
from pathlib import Path
from urllib.parse import unquote


def is_element_visible(elem):
    return elem.is_visible()


class BasicActionsDM:
    def __init__(self, page):
        self.page = page

    # Current working directory = cwd
    def get_screen_shot(self, name):
        self.page.screenshot(path=os.getcwd() + "/screenshots/" + name + ".png")

    def get_full_page_screenshot(self, name):
        # Why: every test step saves a full page screenshot; the full page capture resizes the page for a moment and
        # can leave it scrolled to the top, so the scroll position is restored afterwards, and a capture that does
        # not finish in time (very long page) is saved as the visible part instead of failing the test.
        # When: after each test step.
        screenshot_path = os.getcwd() + "/screenshots_taken/" + name + ".png"
        scroll_position = self._get_scroll_position()
        try:
            self.page.screenshot(path=screenshot_path, full_page=True, timeout=60000)
        except Exception as error:
            print(f"Full page screenshot '{name}' not taken ({type(error).__name__}): the visible part is saved")
            self.page.screenshot(path=screenshot_path, timeout=30000)
        finally:
            self._restore_scroll_position(scroll_position)

    def _get_scroll_position(self):
        # Why: the page must stay where it was after a screenshot; When: before a full page screenshot
        try:
            return self.page.evaluate("() => [window.scrollX, window.scrollY]")
        except Exception:
            return None

    def _restore_scroll_position(self, scroll_position):
        # Why: the full page capture can leave the page scrolled to the top; When: after a full page screenshot
        if scroll_position is None:
            return
        try:
            self.page.evaluate("([x, y]) => window.scrollTo(x, y)", scroll_position)
        except Exception:
            pass  # the page navigated during the screenshot

    @staticmethod
    def highlight_element(elem, color="red", duration_ms=2000):
        # Outline the element only (Playwright's highlight() also shows the locator text on the page)
        elem.evaluate(
            """(el, [color, duration]) => {
                const old = el.style.outline;
                el.style.outline = `3px solid ${color}`;
                setTimeout(() => { el.style.outline = old; }, duration);
            }""",
            [color, duration_ms]
        )

    def open_search_panel_if_collapsed(self, search_field, timeout=10000):
        # Search panel may load expanded or collapsed: expand it only when the search field is hidden
        if search_field.first.is_visible():
            print("Search panel is already expanded")
        else:
            self.click_on_btn(self.page.locator('i[class="far fa-angle-down"]').first)
            print("Search panel expanded")
        expect(search_field.first).to_be_visible(timeout=timeout)

    def fill_autocomplete_field(self, field, value, wait_ms=2000):
        # Enter value -> exact match in the dropdown? select it : continue with the entered value
        field.fill(value[:-1])
        field.press_sequentially(value[-1])  # key event so the page shows its suggestions
        suggestion = self.page.locator(
            f'xpath=//*[not(self::input) and not(self::textarea) and not(ancestor::table)]'
            f'[normalize-space(text())="{value}"]').first
        try:
            suggestion.wait_for(state="visible", timeout=wait_ms)
            suggestion.click()
            print(f"Selected {value} from the dropdown")
        except Exception:
            print(f"No dropdown shown for {value}, continuing with the entered value")

    def move_mouse_away(self):
        # Move the mouse to the top-left corner so no hover tooltip stays on the page after a click
        self.page.mouse.move(0, 0)

    def navigate_to_url(self, given_url):
        self.page.goto(given_url, wait_until="networkidle", timeout=60000)

    def press_button(self, btnName):
        self.page.keyboard.press(btnName)

    def wait_for_timeout(self, timeout):
        self.page.wait_for_timeout(timeout)

    def click_requisition_and_interact_with_button(self, url: str, button_locator: str):
        self.page.goto(url)
        requisition_link = self.page.locator('a[href*="RequisitionList"]')  # Assuming this locator
        requisition_link.click()

        new_tab = self.page.context.wait_for_event('page')
        new_tab.wait_for_load_state('networkidle')
        button = new_tab.locator(button_locator)
        button.click()
        print("Button clicked in new tab")

    def verify_by_title(self, title):
        expect(self.page).to_have_title(title)

    @staticmethod
    def verify_text(self, locator, expected_text):
        # Wait until the text appears and matches
        expect(locator).to_have_text(expected_text)
        # Fetch and print the actual text
        actual_text = locator.text_content().strip()
        print(actual_text)
        return actual_text

    #
    # @staticmethod
    # def wait_to_load_element(self, elem, state="attached"):
    #     elem.wait_for(state=state)

    @staticmethod
    def wait_to_load_element(elem):
        elem.wait_for(state='visible')
        # print('waited for the elem')

    @staticmethod
    def click_on_btn(btn):
        btn.click()

    # @staticmethod
    # def wait_to_load_element(self, elem, state="attached"):
    #     elem.wait_for(state=state)

    @staticmethod
    def click_on_openLoginFormBtn(openLoginFormBtn):
        openLoginFormBtn.click()

    @staticmethod
    def click_on_btn(btn, timeout: Optional[int] = 5000):
        btn.wait_for(state='visible', timeout=timeout)
        btn.click()

    @staticmethod
    def input_in_element(elem, input_text):
        # elem.to_be_visible()
        elem.click()
        elem.fill(input_text)

    @staticmethod
    def select_from_list_by_value(elem, value):
        elem.click()
        elem.select_option(value)

    def select_from_list_by_text(self, elem, text):
        elem.wait_for(state='visible')
        self.page.wait_for_timeout(500)
        elem.fill(text)
        # Add a wait for the dropdown to appear
        self.page.wait_for_selector(f'div:text-matches("{text}", "i")', state='visible')
        # Use get_by_text with exact match and wait for it to be visible
        text_locator = self.page.get_by_text(text, exact=True)
        text_locator.wait_for(state='visible', timeout=3000)
        text_locator.click()

    # @staticmethod
    def character_input(self, locator, text, delay_ms=200):
        for char in text:
            locator.type(char, delay=delay_ms)

    def select_option_from_dropdown(self, elem, text):
        elem.wait_for(state='visible')
        elem.click()
        elem.fill(text)
        # Wait for the dropdown options to appear
        self.page.wait_for_selector(f'div:text-matches("{text}", "i")', state='visible')
        # Click on the first matching option
        self.page.get_by_text(text).click()

    # @staticmethod
    # def click_on_btn_1(locator):
    #     locator.wait_for(state="visible", timeout=5000)
    #     locator.click()

    def upload_attachment_file(self, file_input, file_path, timeout=5000):
        # Accept both locator and selector
        if isinstance(file_input, str):
            file_input = self.page.locator(file_input)

        file_input.wait_for(state="attached", timeout=timeout)
        file_input.set_input_files(file_path)
        print(f"File uploaded: {file_path}")
        return os.path.basename(file_path)

    def upload_file(self, container, file_path: str, index: int = 0, timeout: int = 30000):
        """
        Uploads a file using the hidden input inside #selector_fileId_{index}
        and waits until the corresponding hidden field is populated.
        :rtype: Any
        """
        p = Path(file_path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        # file_input = self.page.locator(f"#selector_fileId_{index} input[type='file']")
        file_input = self.page.locator(f"{container} input[type='file']")
        file_input.wait_for(state="attached", timeout=timeout)

        # This bypasses the OS dialog and triggers the 'change' event.
        file_input.set_input_files(str(p))

        # App-specific confirmation: hidden field should get a non-empty value.
        index = int(container.split("_")[-1])
        hidden_after_upload = self.page.locator(f"#fileHiddenId_{index}")
        expect(hidden_after_upload).to_have_value(re.compile(r".+"), timeout=timeout)

        # Optional: return what the app stored (filename / token, etc.)
        return hidden_after_upload.input_value()

    def clear_browser_cache(self):
        try:
            origin = self.page.evaluate("location.origin")
            self.page.evaluate("localStorage.clear(); sessionStorage:clear();")
            cdp = self.page.context.new_cdp_session(self.page)
            cdp.send(
                "Storage.clearDataForOrigin",
                {
                    "origin": origin,
                    "storageTypes": ",".join([
                        "cookies",
                        "local_storage",
                        "session_storage",
                        "indexeddb",
                        "cache_storage",
                        "service_workers"
                    ])
                }
            )

            self.page.context.clear_cookies()
            self.page.context.clear_permissions()
        except Exception as e:
            print(f"⚠️ Failed to clear cache: {e}")

    def wait_for_selector(self, locator, state='visible', timeout=5000):
        """
        Waits for a selector to reach the specified state.

        :param locator: Locator object to wait on.
        :param state: State to wait for. One of: 'attached', 'detached', 'visible', 'hidden'.
        :param timeout: Max time to wait in milliseconds.
        """
        try:
            locator.wait_for(state=state, timeout=timeout)
        except TimeoutError:
            print(f"Timeout: Locator did not become '{state}' within {timeout}ms.")

    # New Method to Fill Date Range
    def fill_date_range(self, start_date: str, end_date: str):
        start_date_field = self.page.locator('#StartDate')
        end_date_field = self.page.locator('#EndDate')

        # Fill the input fields with the provided dates
        start_date_field.fill(start_date)
        end_date_field.fill(end_date)
        # Date entry completed: End Date should not stay selected
        end_date_field.blur()

        print(f"Print searching order Start Date: {start_date}, End Date: {end_date}")

    # New Method to Validate Date Range
    def validate_date_range(self):
        """
        Validates that the StartDate is not later than the EndDate.
        """
        start_date_value = self.page.locator('#StartDate').input_value()
        end_date_value = self.page.locator('#EndDate').input_value()

        try:
            start_date = datetime.strptime(start_date_value, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_value, '%Y-%m-%d')
        except ValueError:
            print("Invalid date format. Please ensure dates are in YYYY-MM-DD format.")
            return False

        if not start_date_value or not end_date_value:
            print("Both start and end dates must be provided.")
            return False
        if start_date > end_date:
            print("Error: Start date cannot be later than the end date.")
            return False

        print(f"Validated Date Range: Start Date: {start_date}, End Date: {end_date}")
        return True

    def select_date(self, extra_days: int = 0) -> str:
        # Get current date and add extra days
        new_date = datetime.now().date() + timedelta(days=extra_days)
        # Format to 'DD-MM-YYYY' as required by the input field
        return new_date.strftime('%d-%m-%Y')

    def print_important_toast(self, toast_msg: str):
        """
        Print a toast message in bold, with a yellow highlight and black text.
        This makes it highly visible in terminal or console outputs.
        """
        highlight = "\033[1m\033[30m\033[103m"  # Bold + black text + bright yellow background
        reset = "\033[0m"

        print(f"{highlight} 🔔 {toast_msg} 🔔 {reset}")

    # ---------------- New tabs and attachments (links that open other pages or files) ----------------

    def open_link_in_new_tabs(self, link, wait_after_ms=5000):
        # Why: some links open 1 or 2 new tabs (e.g. the requisition link opens ERP twice); When: a link test must
        # read the opened page and close every tab it opened; returns all new tabs
        opened_tabs = []

        def add_tab(new_tab):
            # Why: keep every tab the link opens; When: the browser opens a new tab after the click
            opened_tabs.append(new_tab)

        self.page.context.on("page", add_tab)
        try:
            with self.page.context.expect_page():
                link.click()
            self.page.wait_for_timeout(wait_after_ms)
        finally:
            self.page.context.remove_listener("page", add_tab)
        print(f"New tabs opened: {len(opened_tabs)}")
        return opened_tabs

    def close_opened_tabs(self, tabs):
        # Why: tabs opened by a link must not stay open; When: after reading the opened page, before the next step
        for tab in tabs:
            if not tab.is_closed():
                tab.close()
        self.page.bring_to_front()

    def save_attachment_from_icon(self, attachment_icon, save_folder):
        # Why: the attachment icon opens an ERP file in a new tab, and the browser shows XLS/PPTX files as very long
        # raw text that holds the page; the tab is stopped from showing the file and the file is downloaded directly.
        # When: every attachment check (shopping cart, delivery schedule, confirm order, order details)
        file_urls, opened_tabs, downloads = [], [], []

        def stop_showing_file(route):
            # Why: the browser must not show the file in the tab; When: the new tab opens the ERP file address
            if route.request.is_navigation_request():
                file_urls.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        def add_tab(new_tab):
            # Why: the opened tab is closed after the file address is known; When: the icon opens a new tab
            opened_tabs.append(new_tab)

        def add_download(download):
            # Why: marketplace attachments are downloaded instead of opened; When: the icon starts a download
            downloads.append(download)

        self.page.context.route("**/fileStream/readFileStream**", stop_showing_file)
        self.page.context.on("page", add_tab)
        self.page.on("download", add_download)
        try:
            attachment_icon.click()
            for _ in range(60):
                if file_urls or downloads:
                    break
                self.page.wait_for_timeout(500)
        finally:
            self.page.context.unroute("**/fileStream/readFileStream**", stop_showing_file)
            self.page.context.remove_listener("page", add_tab)
            self.page.remove_listener("download", add_download)
        assert file_urls or downloads, "The attachment icon did not open or download the attachment"

        if downloads:
            saved_file = Path(save_folder) / downloads[0].suggested_filename.split(";")[0].strip()
            downloads[0].save_as(str(saved_file))
            print(f"Attachment downloaded: {saved_file}")
            return saved_file

        self.close_opened_tabs(opened_tabs)
        file_url = file_urls[0]
        saved_file = Path(save_folder) / unquote(file_url).split("/")[-1].split("?")[0]
        saved_file.write_bytes(self.page.context.request.get(file_url).body())
        print(f"Attachment saved (not shown in the browser): {file_url} -> {saved_file}")
        return saved_file
