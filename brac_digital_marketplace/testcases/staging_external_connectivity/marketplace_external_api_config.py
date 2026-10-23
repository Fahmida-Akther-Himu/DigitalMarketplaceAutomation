from dotenv import load_dotenv
import os

import pytest
import allure

load_dotenv()

# Marketplace Staging External API configuration (Administration > Configuration > Settings > Manage External Config):
# every API Name must have the expected External API URL and External API Key from .env (a blank expected key must
# stay blank). Only incorrect records are updated (Edit > Update in the row of that API Name), then every record is
# checked again; the records are also searched by each External API Key.
# API keys are never shown: report and logs show "blank" / "set (N characters)", screenshots mask the key cells.
# Digital Marketplace admin
marketplace_url_qa = os.getenv("test_marketplace_url_qa")
marketplace_password = os.getenv("test_marketplace_password")
marketplace_admin = os.getenv("test_order_admin")
# Expected API names (comma separated); each name has test_external_api_<name>_url and test_external_api_<name>_key
external_api_names = [name.strip() for name in (os.getenv("test_external_api_names") or "").split(",") if name.strip()]

from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu
from pages.digital_marketplace.administration.configuration.settings.manage_external_config import ManageExternalConfig
from brac_digital_marketplace.testcases.order_creation.order_details_checks import new_check

# Message shown after a successful Update (business message of the page)
UPDATE_SUCCESS_MESSAGE = "Data updated successfully."
# Grid page size used to show all records
ALL_ITEMS_PAGE_SIZE = 100

# Expected configuration from .env: {API Name: {"url", "key"}} (Test case 1)
expected_config = {}
# Records read from the grid: {API Name: {"url", "key"}} (Test case 3), API Names that need an update (Test case 4)
page_config = {}
apis_to_update = []
# Results of each step for the next tests
results = {}


def attach_and_assert_checks(checks, title):
    # Why: list the checks of a step in the report (expected / actual / result); When: after the checks of a
    # step; the test fails if any check failed
    allure.attach(
        "\n".join(f"{check}: expected {expected} | actual {actual} | {result}" for check, expected, actual, result in checks),
        name=title,
        attachment_type=allure.attachment_type.TEXT
    )
    failed_checks = [f"{check}: expected {expected}, found {actual}"
                     for check, expected, actual, result in checks if result == "FAIL"]
    assert not failed_checks, f"{title}:\n" + "\n".join(failed_checks)


def masked(key):
    # Why: API keys must not be shown in logs, screenshots or the report; only blank / length is shown; When: every
    # key in a check or log
    return "blank" if not key else f"set ({len(key)} characters)"


def key_groups():
    # Why: the distinct expected (non blank) API keys, in .env order, each with its API Names; the label never shows
    # the key; When: search by External API Key. Returns [(label, key, [API Names])]
    groups = {}
    for name, values in expected_config.items():
        if values["key"]:
            groups.setdefault(values["key"], []).append(name)
    return [(f"Key {number} ({len(key)} characters)", key, names)
            for number, (key, names) in enumerate(groups.items(), start=1)]


def blank_key_names():
    # Why: the API Names whose expected key is blank (must stay blank); When: blank key check
    return [name for name, values in expected_config.items() if not values["key"]]


def check_api(name, actual, label):
    # Why: one API record must have the expected URL and key (exact values; a blank expected key must be blank);
    # When: verification before and after the updates. Returns checks
    expected = expected_config[name]
    if actual is None:
        return [new_check(f"{label} {name}: record on the page", "shown", "missing", False)]
    return [
        new_check(f"{label} {name}: External API URL", expected["url"], actual["url"] or "blank",
                  actual["url"] == expected["url"]),
        new_check(f"{label} {name}: External API Key", masked(expected["key"]), masked(actual["key"]),
                  actual["key"] == expected["key"]),
    ]


def log_in_and_open_page(page):
    # Why: the marketplace admin logs in and opens Configuration > Settings > Manage External Config; When: Test case 2
    login_page = LoginPage(page)
    config_page = ManageExternalConfig(page)
    # A new session: a previous user may still be logged in
    page.context.clear_cookies()
    login_page.navigate_to_url(marketplace_url_qa)
    login_page.perform_marketplace_login(user_name=marketplace_admin, pass_word=marketplace_password)
    login_page.navigate_to_url(marketplace_url_qa.rstrip("/") + "/Admin")
    config_page.get_masked_screenshot('external_api_config_admin_login')
    config_page.open_manage_external_config()
    return config_page


def read_page_config(config_page, screenshot_name):
    # Why: every record of the grid by API Name (page size 100, all pages), and the total from the grid info;
    # When: before the verification and for the recheck. Returns (rows, total)
    rows = config_page.read_all_rows(ALL_ITEMS_PAGE_SIZE)
    total = config_page.grid_counts()[2]
    config_page.get_masked_screenshot(screenshot_name)
    print(f"MANAGE EXTERNAL CONFIG: {len(rows)} records read, total {total}")
    return rows, total


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_1: Load the expected External API configuration from .env")
@allure.description("Test case 1: Every expected API Name has its External API URL and External API Key in .env "
                    "(a blank key must stay blank); no API Name is repeated. Keys are shown masked.")
@pytest.mark.order(1)
def test_1_load_expected_external_api_config(page):
    """
    Test case 1: test_external_api_names and, for every name, test_external_api_<name>_url and
    test_external_api_<name>_key (a missing line fails; an empty _key means the key must be blank).
    """
    global expected_config
    required_env_values = {
        "test_marketplace_url_qa": marketplace_url_qa, "test_marketplace_password": marketplace_password,
        "test_order_admin": marketplace_admin, "test_external_api_names": ",".join(external_api_names),
    }
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"

    with allure.step("Step 1: Read the expected URL and key of every API Name"):
        repeated = sorted({name for name in external_api_names if external_api_names.count(name) > 1})
        missing_lines = [f"test_external_api_{name}_{field}" for name in external_api_names for field in ("url", "key")
                         if os.getenv(f"test_external_api_{name}_{field}") is None]
        blank_urls = [name for name in external_api_names if os.getenv(f"test_external_api_{name}_url") == ""]
        assert not missing_lines, f"Missing in .env: {', '.join(missing_lines)}"
        expected_config = {name: {"url": os.getenv(f"test_external_api_{name}_url").strip(),
                                  "key": os.getenv(f"test_external_api_{name}_key").strip()}
                           for name in external_api_names}
        summary = [f"{name}: {values['url']} | key {masked(values['key'])}" for name, values in expected_config.items()]
        print("EXPECTED EXTERNAL API CONFIG:", len(expected_config), "API Names")
        allure.attach("\n".join(summary), name=f"Expected configuration ({len(expected_config)} API Names)",
                      attachment_type=allure.attachment_type.TEXT)
        checks = [
            new_check("API Names repeated in test_external_api_names", "none", ", ".join(repeated) or "none",
                      not repeated),
            new_check("API Names with a blank expected URL", "none", ", ".join(blank_urls) or "none", not blank_urls),
        ]
        attach_and_assert_checks(checks, "Expected configuration in .env")


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_2: Admin login and open Manage External Config")
@allure.description("Test case 2: The marketplace admin logs in and opens Administration > Configuration > Settings > "
                    "Manage External Config.")
@pytest.mark.order(2)
def test_2_open_manage_external_config(page):
    """Test case 2: Admin login ('test_order_admin') and Manage External Config page."""
    assert expected_config, "Test case 1 must pass first: the expected configuration is not loaded"
    with allure.step("Step 1: Log in as the marketplace admin and open Manage External Config"):
        config_page = log_in_and_open_page(page)
        heading_shown = config_page.page_heading.is_visible()
        config_page.get_masked_screenshot('external_api_config_page')
        checks = [
            new_check("Manage External Config page", "/Admin/Setting/ManageExternalConfig", page.url,
                      "/admin/setting/manageexternalconfig" in page.url.lower()),
            new_check("Manage External Config heading", "shown", "shown" if heading_shown else "not shown",
                      heading_shown),
        ]
        attach_and_assert_checks(checks, "Manage External Config page")
    results["page_opened"] = True


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_3: Show 100 items, read every API record and count them")
@allure.description("Test case 3: Change the page size from 15 to 100, read every API record (API Name, URL, key) "
                    "and verify the total count against the grid info and the expected API Names in .env.")
@pytest.mark.order(3)
def test_3_read_all_api_records_and_count(page):
    """
    Test case 3: The default page size is 15; 100 items are shown (next pages read when there are more records).
    The records read must equal the grid total; new API Names (not in .env) and missing API Names are reported.
    """
    global page_config
    assert results.get("page_opened"), "Test case 2 must pass first: Manage External Config is not opened"
    config_page = ManageExternalConfig(page)

    with allure.step("Step 1: Default page size"):
        first, last, total = config_page.grid_counts()
        print(f"DEFAULT PAGE: records {first}-{last} of {total}")
        allure.attach(f"Records {first}-{last} of {total}", name="Default page size",
                      attachment_type=allure.attachment_type.TEXT)

    with allure.step(f"Step 2: Show {ALL_ITEMS_PAGE_SIZE} items and read every API record"):
        rows, total = read_page_config(config_page, 'external_api_config_all_items')
        names = [row["name"] for row in rows]
        repeated = sorted({name for name in names if names.count(name) > 1})
        page_config = {row["name"]: {"url": row["url"], "key": row["key"]} for row in rows}
        new_names = [name for name in page_config if name not in expected_config]
        missing_names = [name for name in expected_config if name not in page_config]
        allure.attach("\n".join(f"{row['name']}: {row['url'] or 'blank'} | key {masked(row['key'])}" for row in rows),
                      name=f"API records on the page ({len(rows)})", attachment_type=allure.attachment_type.TEXT)
        allure.attach(f"Total APIs on the page: {total}\nExpected in .env: {len(expected_config)}\n"
                      f"New API Names on the page (not in .env): {', '.join(new_names) or 'none'}\n"
                      f"Missing on the page (in .env): {', '.join(missing_names) or 'none'}",
                      name="API count", attachment_type=allure.attachment_type.TEXT)
        print(f"API COUNT: page {total} | .env {len(expected_config)} | new {new_names} | missing {missing_names}")
        checks = [
            new_check("Records read = grid total", total, len(rows), len(rows) == total),
            new_check("API Names repeated on the page", "none", ", ".join(repeated) or "none", not repeated),
            new_check("Total APIs on the page = expected API Names in .env", len(expected_config), total,
                      total == len(expected_config)),
            new_check("New API Names on the page (add them to .env)", "none", ", ".join(new_names) or "none",
                      not new_names),
            new_check("Expected API Names missing on the page", "none", ", ".join(missing_names) or "none",
                      not missing_names),
        ]
        attach_and_assert_checks(checks, "API records and count")


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_4: Verify every API URL and key against .env")
@allure.description("Test case 4: Each API record is found by its exact API Name and its External API URL and key are "
                    "compared with .env (blank keys included); the records with a mismatch are listed for the update.")
@pytest.mark.order(4)
def test_4_verify_api_url_and_key(page):
    """
    Test case 4: PASS / MISMATCH per API Name (keys masked). A mismatch is not a failure here: it is updated in
    Test case 5 and checked again in Test case 6. An expected API Name missing on the page fails.
    """
    global apis_to_update
    assert page_config, "Test case 3 must pass first: the API records are not read"
    with allure.step("Step 1: Compare every expected API Name with its record on the page"):
        lines = []
        apis_to_update = []
        missing_names = []
        for name in expected_config:
            actual = page_config.get(name)
            if actual is None:
                missing_names.append(name)
                lines.append(f"{name}: FAIL (missing on the page)")
                continue
            failed = [check for check in check_api(name, actual, "Before") if check[3] == "FAIL"]
            if failed:
                apis_to_update.append(name)
            lines.append(f"{name}: " + ("MISMATCH, update needed: " + "; ".join(
                f"{check[0].split(': ', 1)[1]} expected {check[1]}, found {check[2]}" for check in failed)
                if failed else "PASS"))
        print("API VERIFICATION:", len(expected_config) - len(apis_to_update) - len(missing_names), "PASS |",
              len(apis_to_update), "update needed |", len(missing_names), "missing")
        allure.attach("\n".join(lines), name="API verification (before update)",
                      attachment_type=allure.attachment_type.TEXT)
        allure.attach(", ".join(apis_to_update) or "none (all API records are correct)", name="API Names to update",
                      attachment_type=allure.attachment_type.TEXT)
        checks = [new_check("Expected API Names on the page", "all", ", ".join(missing_names) or "all",
                            not missing_names)]
        attach_and_assert_checks(checks, "API verification (before update)")
    results["verified"] = True


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_5: Update only the incorrect API records")
@allure.description("Test case 5: For every API record with a mismatch: Edit in the row of that API Name, verify the "
                    "edit mode, enter the expected URL and key (blank key stays blank), click Update, capture the "
                    "message and verify the saved values. No change when every record is correct.")
@pytest.mark.order(5)
def test_5_update_incorrect_api_records(page):
    """Test case 5: Conditional update; a modified record is always saved with Update."""
    assert results.get("verified"), "Test case 4 must pass first: the API records are not verified"
    config_page = ManageExternalConfig(page)
    if not apis_to_update:
        with allure.step("Step 1: Every API record is correct: no update"):
            print("API UPDATE: no update needed")
            allure.attach("Every API record has the expected URL and key: nothing is changed.",
                          name="API update", attachment_type=allure.attachment_type.TEXT)
        results["updated"] = []
        return

    checks = []
    updated = []
    for name in apis_to_update:
        expected = expected_config[name]
        with allure.step(f"Step 1: {name}: Edit, enter the expected URL and key, Update"):
            config_page.edit_record(name)
            in_edit_mode = config_page.is_in_edit_mode(name)
            config_page.get_masked_screenshot(f'external_api_config_{name}_edit_mode')
            checks.append(new_check(f"{name}: row in edit mode (URL and Key inputs, Update)", "edit mode",
                                    "edit mode" if in_edit_mode else "not in edit mode", in_edit_mode))
            try:
                config_page.fill_record(name, expected["url"], expected["key"])
            finally:
                # A modified record is never left unsaved
                config_page.click_update(name)
            message = config_page.read_notification()
            config_page.wait_for_grid()
            config_page.get_masked_screenshot(f'external_api_config_{name}_updated')
            print(f"API UPDATE {name}: {message or 'no message'}")
            checks.append(new_check(f"{name}: Update message", UPDATE_SUCCESS_MESSAGE, message or "no message",
                                    UPDATE_SUCCESS_MESSAGE.lower() in message.lower()))

        with allure.step(f"Step 2: {name}: verify the saved values"):
            saved = next((row for row in config_page.read_all_rows(ALL_ITEMS_PAGE_SIZE) if row["name"] == name), None)
            checks += check_api(name, saved, "Saved")
            updated.append(name)
    results["updated"] = updated
    attach_and_assert_checks(checks, f"API update ({len(updated)} records)")


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_6: Recheck every API record")
@allure.description("Test case 6: Reload Manage External Config, show 100 items and verify every expected API Name "
                    "has the expected URL and key (updated records and unchanged records).")
@pytest.mark.order(6)
def test_6_recheck_every_api_record(page):
    """Test case 6: Final verification of every API record (PASS / FAIL per API Name, keys masked)."""
    assert "updated" in results, "Test case 5 must pass first: the update step did not finish"
    config_page = ManageExternalConfig(page)
    with allure.step("Step 1: Reload the page and read every API record"):
        page.reload()
        page.wait_for_load_state("domcontentloaded")
        config_page.wait_for_grid()
        rows, total = read_page_config(config_page, 'external_api_config_recheck')
        final_config = {row["name"]: {"url": row["url"], "key": row["key"]} for row in rows}

    with allure.step("Step 2: Verify every expected API Name"):
        checks = []
        for name in expected_config:
            checks += check_api(name, final_config.get(name), "Final")
        updated = results["updated"]
        allure.attach(f"Updated in this run: {', '.join(updated) or 'none'}\nTotal APIs on the page: {total}",
                      name="Recheck summary", attachment_type=allure.attachment_type.TEXT)
        attach_and_assert_checks(checks, "API verification (final)")
    results["rechecked"] = True


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_7: Search the API records by External API Key")
@allure.description("Test case 7: Search with each expected External API Key: the result total, the keys and the API "
                    "Names must be exactly the .env API Names with that key; the other API Names have a blank key.")
@pytest.mark.order(7)
def test_7_search_by_external_api_key(page):
    """
    Test case 7: Keyword = each distinct expected key (labels show only the key length); a blank key cannot be
    searched, so the blank key API Names are checked in the full list (blank keyword).
    """
    assert results.get("rechecked"), "Test case 6 must pass first: the API records are not rechecked"
    config_page = ManageExternalConfig(page)
    checks = []
    for number, (label, key, names) in enumerate(key_groups(), start=1):
        with allure.step(f"Step {number}: Search {label}: {len(names)} API Names expected"):
            config_page.search_keyword(key)
            rows = config_page.read_all_rows(ALL_ITEMS_PAGE_SIZE)
            total = config_page.grid_counts()[2]
            config_page.get_masked_screenshot(f'external_api_config_search_key_{number}')
            found = [row["name"] for row in rows]
            print(f"SEARCH {label}: {total} records | {found}")
            checks += [
                new_check(f"{label}: result total", len(names), total, total == len(names)),
                new_check(f"{label}: every result has this key", "all", f"{sum(row['key'] == key for row in rows)} of {len(rows)}",
                          all(row["key"] == key for row in rows)),
                new_check(f"{label}: API Names missing in the result", "none",
                          ", ".join(name for name in names if name not in found) or "none",
                          all(name in found for name in names)),
                new_check(f"{label}: other API Names in the result", "none",
                          ", ".join(name for name in found if name not in names) or "none",
                          all(name in names for name in found)),
            ]

    with allure.step(f"Step {len(key_groups()) + 1}: Blank key: clear the keyword and check the blank key API Names"):
        config_page.search_keyword("")
        rows = config_page.read_all_rows(ALL_ITEMS_PAGE_SIZE)
        config_page.get_masked_screenshot('external_api_config_search_blank_key')
        blank_on_page = [row["name"] for row in rows if not row["key"]]
        expected_blank = blank_key_names()
        print(f"BLANK KEY: page {blank_on_page} | .env {expected_blank}")
        keyed_total = sum(len(names) for _, _, names in key_groups())
        checks += [
            new_check("Blank key: API Names with a blank key", len(expected_blank), len(blank_on_page),
                      sorted(blank_on_page) == sorted(expected_blank)),
            new_check("Blank key: expected blank but a key is set", "none",
                      ", ".join(name for name in expected_blank if name not in blank_on_page) or "none",
                      all(name in blank_on_page for name in expected_blank)),
            new_check("Blank key: blank but a key is expected", "none",
                      ", ".join(name for name in blank_on_page if name not in expected_blank) or "none",
                      all(name in expected_blank for name in blank_on_page)),
            new_check("Key groups + blank key = total APIs", len(rows), keyed_total + len(expected_blank),
                      keyed_total + len(expected_blank) == len(rows)),
        ]
    attach_and_assert_checks(checks, "Search by External API Key")


@allure.suite("Administration")
@allure.feature("Configuration")
@allure.story("Manage External Config")
@allure.title("Test_case_8: Log out from Administration")
@allure.description("Test case 8: Log out after the verification and the updates.")
@pytest.mark.order(8)
def test_8_log_out(page):
    """Test case 8: Logout from Marketplace Administration."""
    with allure.step("Step 1: Log out from Administration"):
        MainNavigationMenu(page).logout_from_administration()
        page.wait_for_timeout(2000)
        ManageExternalConfig(page).get_masked_screenshot('external_api_config_logout')
        assert "login" in page.url.lower() or "admin" not in page.url.lower(), f"Not logged out: {page.url}"
