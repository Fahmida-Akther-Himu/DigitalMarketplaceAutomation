from dotenv import load_dotenv
import os

import pytest
import allure

load_dotenv()

# ERP Procurement Staging External Connection (Procurement > Setup > External Connection): the eTender, HoFin and
# Digital Marketplace integration values must be the expected Staging values from .env, the 3 integration checkboxes
# (IsETender, IsHoFin, IsMarketPlace) must be selected and the E-Tender / HoFin / MarketPlace IP Address fields must use
# the system generated Proxy IP. When the Proxy IP is missing, a whitelisted Framework Agreement is pushed to DM (once)
# and the Proxy IP is checked again. Update is always clicked, then the saved values are checked after a reload.
# Keys and the password are never shown: report and logs show "set (N characters)", screenshots hide them.
# ERP user (ResetHub) and environment
erp_user = os.getenv("test_erp_external_connection_user")
proj_env = os.getenv("test_env")
# Whitelisted Framework Agreement pushed to DM when the Proxy IP is missing
whitelisted_agreement_number = os.getenv("test_whitelisted_agreement_number")

from pages.erp_procurement.reset_hub_page import ResetHubPage
from pages.erp_procurement.dashboard_page import DashboardPage
from pages.erp_procurement.procurement_home_page import ProcurementHomePage
from pages.erp_procurement.main_navigation_bar import MainNavigationBar
from pages.erp_procurement.my_dashboard.procurement.setup.external_connection import ExternalConnection
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_list import FrameworkList
from pages.erp_procurement.my_dashboard.procurement.purchase_order.framework_information import FrameworkInformation
from brac_digital_marketplace.testcases.order_creation.order_details_checks import new_check

# The IP Address fields that must use the system Proxy IP
PROXY_IP = "PROXY_IP"
# Expected value of every text field: the .env key (or the system Proxy IP)
EXPECTED_ENV_KEYS = {
    "eTender API Integration URL": "test_erp_ext_etender_api_url",
    "eTender Base URL": "test_erp_ext_etender_base_url",
    "eTender Access Key": "test_erp_ext_etender_access_key",
    "eTender (restTender) E-Tender IP Address": PROXY_IP,
    "eTender (restTender) Key (API Consumer)": "test_erp_ext_etender_api_consumer_key",
    "HoFin API Integration URL": "test_erp_ext_hofin_api_url",
    "HoFin Finance Access Key": "test_erp_ext_hofin_access_key",
    "HoFin (restPayment) HoFin IP Address": PROXY_IP,
    "HoFin (restPayment) Key (API Consumer)": "test_erp_ext_hofin_api_consumer_key",
    "MarketPlace API Integration URL": "test_erp_ext_dm_api_url",
    "MarketPlace Server IP Address": "test_erp_ext_dm_server_url",
    "DMP Start Date": "test_erp_ext_dm_start_date",
    "DMP Role IDP ID": "test_erp_ext_dm_role_idp_id",
    "MarketPlace (dmpApi) MarketPlace IP Address": PROXY_IP,
    "MarketPlace (dmpApi) Key (API Consumer)": "test_erp_ext_dm_dmp_api_key",
    "MarketPlace (ProcApiInfo) Username": "test_erp_ext_dm_username",
    "MarketPlace (ProcApiInfo) Password": "test_erp_ext_dm_password",
}
# Push to DM success message (business message of the Framework Agreement page)
PUSH_TO_DM_SUCCESS_TEXT = "successfully pushed"

# Expected values from .env (Test case 1), page values and results of each step
expected_values = {}
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


def is_secret(label):
    # Why: keys and the password are never shown; When: every value in a check or log
    return "Key" in label or "Password" in label


def shown(label, value):
    # Why: the value as it may be shown (secrets: blank / set (N characters)); When: every value in a check or log
    if not is_secret(label):
        return value or "blank"
    return "blank" if not value else f"set ({len(value)} characters)"


def expected_of(label, proxy_ip):
    # Why: the expected value of a field: the system Proxy IP for the IP Address fields, otherwise the .env value;
    # When: verification and update
    return proxy_ip if EXPECTED_ENV_KEYS[label] == PROXY_IP else expected_values[label]


def config_checks(connection_page, proxy_ip, label_prefix):
    # Why: every text field must have its expected value and every required checkbox must be selected;
    # When: before the update (to find what to change) and after the reload (saved values). Returns checks
    fields = connection_page.read_text_fields()
    checks = [new_check(f"{label_prefix} {label} checkbox", "selected", "selected" if selected else "not selected",
                        selected) for label, selected in connection_page.read_checkboxes().items()]
    for label, value in fields.items():
        expected = expected_of(label, proxy_ip)
        checks.append(new_check(f"{label_prefix} {label}", shown(label, expected), shown(label, value), value == expected))
    return checks


def log_in_and_open_external_connection(page):
    # Why: the ERP user logs in (ResetHub) and opens Procurement > Setup > External Connection; When: Test case 2
    page.context.clear_cookies()
    reset_page = ResetHubPage(page)
    reset_page.open_generated_link(reset_page.generate_reset_link(env=proj_env, username=erp_user))
    DashboardPage(page).goto_procurement()
    connection_page = ExternalConnection(page)
    connection_page.open_external_connection()
    return connection_page


def push_whitelisted_agreement_to_dm(page, new_tab):
    # Why: the Proxy IP is generated by the Marketplace integration; when it is missing, a whitelisted Framework
    # Agreement is pushed to DM once and the real message is captured; When: Test case 3 (Proxy IP missing only).
    # Returns (checks, message)
    framework_list = FrameworkList(page)
    ProcurementHomePage(page).goto_framework_agreement_list()
    framework_list.search_agreement_with_enter(whitelisted_agreement_number)
    agreement_row, fa_no = framework_list.find_exact_agreement_row(whitelisted_agreement_number)
    framework_list.get_full_page_screenshot('erp_external_connection_framework_list')
    agreement_tab = new_tab(lambda p: agreement_row.locator("a[onclick^='showDetails']").click())
    agreement_tab.wait_for_timeout(5000)
    details_text = " ".join(agreement_tab.locator("body").inner_text().split())
    framework_info = FrameworkInformation(agreement_tab)
    message = framework_info.push_to_dm_with_message()
    framework_info.get_full_page_screenshot('erp_external_connection_push_to_dm')
    print(f"PUSH TO DM {fa_no}: {message}")
    checks = [
        new_check("Framework Agreement Details of the whitelisted agreement", whitelisted_agreement_number,
                  "shown" if whitelisted_agreement_number in details_text else "not shown",
                  whitelisted_agreement_number in details_text),
        new_check("Push to DM message type", "success", message["type"] or "no message", message["type"] == "success"),
        new_check("Push to DM message", f"... {PUSH_TO_DM_SUCCESS_TEXT} ...", message["text"] or "no message",
                  PUSH_TO_DM_SUCCESS_TEXT in message["text"].lower()),
    ]
    agreement_tab.close()
    page.bring_to_front()
    return checks, message


@allure.suite("ERP Procurement")
@allure.feature("Setup")
@allure.story("External Connection")
@allure.title("Test_case_1: Load the expected External Connection values from .env")
@allure.description("Test case 1: Every expected eTender, HoFin and Digital Marketplace value is in .env (secrets shown "
                    "masked); the IP Address fields use the system Proxy IP.")
@pytest.mark.order(1)
def test_1_load_expected_external_connection_values(page):
    """Test case 1: test_erp_ext_* values, the ERP user and the whitelisted agreement from .env."""
    global expected_values
    required_env_values = {"test_erp_external_connection_user": erp_user, "test_env": proj_env,
                           "test_whitelisted_agreement_number": whitelisted_agreement_number}
    required_env_values.update({env_key: os.getenv(env_key) for env_key in EXPECTED_ENV_KEYS.values()
                                if env_key != PROXY_IP})
    missing_env_values = [name for name, value in required_env_values.items() if not value]
    assert not missing_env_values, f"Missing in .env: {', '.join(missing_env_values)}"
    with allure.step("Step 1: Read the expected values"):
        expected_values = {label: os.getenv(env_key).strip() for label, env_key in EXPECTED_ENV_KEYS.items()
                           if env_key != PROXY_IP}
        lines = [f"{label}: {'system Proxy IP' if env_key == PROXY_IP else shown(label, expected_values[label])}"
                 for label, env_key in EXPECTED_ENV_KEYS.items()]
        print("EXPECTED EXTERNAL CONNECTION:", len(lines), "fields")
        allure.attach("\n".join(lines), name="Expected External Connection values",
                      attachment_type=allure.attachment_type.TEXT)


@allure.suite("ERP Procurement")
@allure.feature("Setup")
@allure.story("External Connection")
@allure.title("Test_case_2: ERP login and open External Connection")
@allure.description("Test case 2: The ERP user logs in and opens Procurement > Setup > External Connection; the current "
                    "configuration is captured (secrets masked).")
@pytest.mark.order(2)
def test_2_open_external_connection(page):
    """Test case 2: ERP login ('test_erp_external_connection_user', ResetHub) and External Connection page."""
    assert expected_values, "Test case 1 must pass first: the expected values are not loaded"
    with allure.step("Step 1: Log in and open Setup > External Connection"):
        connection_page = log_in_and_open_external_connection(page)
        connection_page.get_masked_screenshot('erp_external_connection_before')
    with allure.step("Step 2: Capture the current configuration"):
        ips = connection_page.read_system_ips()
        fields = connection_page.read_text_fields()
        boxes = connection_page.read_checkboxes()
        latest_transaction = connection_page.latest_transaction_number.input_value().strip()
        allure.attach("\n".join([f"{name}: {value or 'blank'}" for name, value in ips.items()]
                                + [f"{label} checkbox: {'selected' if selected else 'not selected'}"
                                   for label, selected in boxes.items()]
                                + [f"{label}: {shown(label, value)}" for label, value in fields.items()]
                                + [f"HoFin Latest Transaction Number (read only): {latest_transaction or 'blank'}"]),
                      name="Current External Connection", attachment_type=allure.attachment_type.TEXT)
        print("SYSTEM IPS:", ips, "| CHECKBOXES:", boxes, "| LATEST TRANSACTION:", latest_transaction)
        checks = [new_check("External Connection page", "checkETenderConnection", page.url,
                            "checketenderconnection" in page.url.lower())]
        attach_and_assert_checks(checks, "External Connection page")
    results["page_opened"] = True


@allure.suite("ERP Procurement")
@allure.feature("Setup")
@allure.story("External Connection")
@allure.title("Test_case_3: System generated Proxy IP (Push to DM when it is missing)")
@allure.description("Test case 3: The system generated Proxy IP is reused when it is shown; when it is missing, the "
                    "whitelisted Framework Agreement is pushed to DM once, the message is captured and the Proxy IP is "
                    "checked again on External Connection.")
@pytest.mark.order(3)
def test_3_system_proxy_ip(page, new_tab):
    """Test case 3: Proxy IP available (reused) or Push to DM workflow; never an assumed IP."""
    assert results.get("page_opened"), "Test case 2 must pass first: External Connection is not opened"
    connection_page = ExternalConnection(page)
    proxy_ip = connection_page.read_system_ips()["Proxy IP"]
    if proxy_ip:
        with allure.step(f"Step 1: Proxy IP {proxy_ip} is available: reused (no Push to DM)"):
            print("PROXY IP: available", proxy_ip)
            allure.attach(f"System Proxy IP: {proxy_ip}\nPush to DM: not needed", name="Proxy IP",
                          attachment_type=allure.attachment_type.TEXT)
        results["proxy_ip"] = proxy_ip
        return

    with allure.step(f"Step 1: Proxy IP missing: push {whitelisted_agreement_number} to DM"):
        checks, message = push_whitelisted_agreement_to_dm(page, new_tab)
        allure.attach(f"Type: {message['type'] or '-'}\nMessage: {message['text'] or 'no message'}",
                      name="Push to DM message", attachment_type=allure.attachment_type.TEXT)
    with allure.step("Step 2: Back to External Connection and read the Proxy IP again"):
        connection_page.open_external_connection()
        proxy_ip = connection_page.read_system_ips()["Proxy IP"]
        connection_page.get_masked_screenshot('erp_external_connection_after_push_to_dm')
        print("PROXY IP after Push to DM:", proxy_ip or "still missing")
        checks.append(new_check("System Proxy IP after Push to DM", "available", proxy_ip or "missing", bool(proxy_ip)))
    results["proxy_ip"] = proxy_ip
    attach_and_assert_checks(checks, "Proxy IP (Push to DM)")


@allure.suite("ERP Procurement")
@allure.feature("Setup")
@allure.story("External Connection")
@allure.title("Test_case_4: Verify the External Connection configuration")
@allure.description("Test case 4: The 3 integration checkboxes and every eTender, HoFin and Digital Marketplace value "
                    "are compared with .env (IP Address fields with the Proxy IP); mismatches are listed for the update.")
@pytest.mark.order(4)
def test_4_verify_external_connection(page):
    """Test case 4: PASS / MISMATCH per field (a mismatch is updated in Test case 5, not a failure here)."""
    assert results.get("proxy_ip"), "Test case 3 must pass first: no system Proxy IP"
    connection_page = ExternalConnection(page)
    with allure.step("Step 1: Compare the checkboxes and fields with the expected values"):
        checks = config_checks(connection_page, results["proxy_ip"], "Before:")
        to_update = [check[0].replace("Before: ", "") for check in checks if check[3] == "FAIL"]
        results["to_update"] = to_update
        print("EXTERNAL CONNECTION:", len(checks) - len(to_update), "PASS |", len(to_update), "to update", to_update)
        allure.attach("\n".join(f"{check[0]}: {'PASS' if check[3] == 'PASS' else 'MISMATCH, update needed'} "
                                f"(expected {check[1]}, found {check[2]})" for check in checks),
                      name="External Connection verification (before update)",
                      attachment_type=allure.attachment_type.TEXT)


@allure.suite("ERP Procurement")
@allure.feature("Setup")
@allure.story("External Connection")
@allure.title("Test_case_5: Select the checkboxes, correct the values and click Update")
@allure.description("Test case 5: Select every required checkbox that is not selected (never deselect), enter the "
                    "expected value in every wrong field (Proxy IP in the IP Address fields) and always click Update; "
                    "the response must be a success.")
@pytest.mark.order(5)
def test_5_update_external_connection(page):
    """Test case 5: Update is clicked even when every value is already correct."""
    assert "to_update" in results, "Test case 4 must pass first: the configuration is not verified"
    connection_page = ExternalConnection(page)
    proxy_ip = results["proxy_ip"]
    changed = []
    with allure.step("Step 1: Select the required checkboxes and correct the wrong values"):
        for label, selected in connection_page.read_checkboxes().items():
            if not selected:
                connection_page.select_checkbox(label)
                changed.append(f"{label} checkbox selected")
        for label, value in connection_page.read_text_fields().items():
            expected = expected_of(label, proxy_ip)
            if value != expected:
                connection_page.set_text_field(label, expected)
                changed.append(f"{label}: {shown(label, value)} -> {shown(label, expected)}")
        print("EXTERNAL CONNECTION CHANGES:", changed or "none")
        allure.attach("\n".join(changed) or "none (every value already correct; Update is still clicked)",
                      name="Changes before Update", attachment_type=allure.attachment_type.TEXT)
        connection_page.get_masked_screenshot('erp_external_connection_before_update')
    with allure.step("Step 2: Click Update and capture the response"):
        connection_page.click_update()
        message = connection_page.read_notification()
        connection_page.get_masked_screenshot('erp_external_connection_updated')
        print("UPDATE RESPONSE:", message)
        allure.attach(f"Type: {message['type'] or '-'}\nMessage: {message['text'] or 'no message'}",
                      name="Update response", attachment_type=allure.attachment_type.TEXT)
        checks = [new_check("Update response type", "success", message["type"] or "no message",
                            message["type"] == "success")]
        results["changes"] = changed
        attach_and_assert_checks(checks, "External Connection Update")
    results["updated"] = True


@allure.suite("ERP Procurement")
@allure.feature("Setup")
@allure.story("External Connection")
@allure.title("Test_case_6: Reload External Connection and verify the saved values")
@allure.description("Test case 6: Reopen External Connection and verify the 3 checkboxes, every expected value and the "
                    "Proxy IP in the IP Address fields are saved.")
@pytest.mark.order(6)
def test_6_verify_saved_external_connection(page):
    """Test case 6: Final PASS / FAIL per field after the page is reopened."""
    assert results.get("updated"), "Test case 5 must pass first: Update is not done"
    connection_page = ExternalConnection(page)
    with allure.step("Step 1: Reload the page and open External Connection again"):
        page.reload()
        page.wait_for_load_state("domcontentloaded")
        connection_page.open_external_connection()
        connection_page.get_masked_screenshot('erp_external_connection_saved')
    with allure.step("Step 2: Verify the saved configuration"):
        proxy_ip = connection_page.read_system_ips()["Proxy IP"]
        checks = [new_check("System Proxy IP (same as before the update)", results["proxy_ip"], proxy_ip or "missing",
                            proxy_ip == results["proxy_ip"])]
        checks += config_checks(connection_page, results["proxy_ip"], "Saved:")
        allure.attach(f"Changed in this run: {', '.join(results['changes']) or 'none'}", name="Saved summary",
                      attachment_type=allure.attachment_type.TEXT)
        attach_and_assert_checks(checks, "External Connection verification (saved)")


@allure.suite("ERP Procurement")
@allure.feature("Setup")
@allure.story("External Connection")
@allure.title("Test_case_7: Exit and log out from ERP")
@allure.description("Test case 7: Exit and log out from ERP after the verification and the update.")
@pytest.mark.order(7)
def test_7_log_out(page):
    """Test case 7: ERP logout."""
    with allure.step("Step 1: Exit and log out from ERP"):
        navigation_bar = MainNavigationBar(page)
        navigation_bar.exit()
        navigation_bar.logout_visible()
        navigation_bar.get_full_page_screenshot('erp_external_connection_logout')
