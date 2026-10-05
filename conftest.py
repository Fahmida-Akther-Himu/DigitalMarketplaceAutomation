from __future__ import annotations
from pathlib import Path
from pytest_html import extras
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Callable

import time
import shutil
import datetime
import platform
import sys
import allure
import json
import subprocess
import webbrowser
import importlib.metadata
import os
import pytest
import pyautogui

from playwright.sync_api import (
    Playwright,
    sync_playwright,
    Browser,
    BrowserContext,
    Page,
    Locator,
)

# =====================================================
# FRAMEWORK CONFIG
# =====================================================

HEADLESS = False  # set True in CI
SLOW_MO = 700  # reduce in CI


# =========================
# Auto-highlighter settings
# =========================
# fahmida
# HIGHLIGHT_ENABLED = True
# HIGHLIGHT_DURATION_MS = 500
#
# ACTION_COLORS = {
#
#     "click": "red",
#
#     "fill": "green",
#
#     "press": "red",
#
#     "hover": "blue",
#
# }
def _env_truthy(val: str | None) -> bool:
    if val is None:
        return True
    return val.strip().lower() not in {"0", "false", "off", "no"}


HIGHLIGHT_ENABLED = _env_truthy(os.getenv("HIGHLIGHT_ELEMENTS", "1"))
try:
    HIGHLIGHT_DURATION_MS = int(os.getenv("HIGHLIGHT_MS", "800"))
except ValueError:
    HIGHLIGHT_DURATION_MS = 800

ACTION_COLORS = {
    "click": "red",
    "dblclick": "red",
    "press": "red",
    "fill": "green",
    "type": "green",
    "select_option": "green",
    "focus": "green",
    "hover": "blue",
    "check": "purple",
    "uncheck": "purple",
}

# =====================================================
# SCREEN SIZE
# =====================================================

screen_width, screen_height = pyautogui.size()

# =====================================================
# ARTIFACTS
# =====================================================

ARTIFACTS_DIR = Path("artifacts")

VIDEO_DIR = (
        ARTIFACTS_DIR /
        "videos"
)

TRACE_DIR = (
        ARTIFACTS_DIR /
        "traces"
)

SCREENSHOT_DIR = (
        ARTIFACTS_DIR /
        "screenshots"
)

# =====================================================
# GLOBALS
# =====================================================

global_browser: Optional[Browser] = None

global_context: Optional[BrowserContext] = None
# Newly added below 2 lines
global_pages: list[Page] = []  # last page is the most recent
test_failures: list[dict] = []


############################################

# def pytest_sessionstart(session):
#     allure_dir = Path("allure-results")
#
#     allure_dir.mkdir(
#         parents=True,
#         exist_ok=True
#     )
#
#     # ===============================
#     # Allure Environment
#     # ===============================
#
#     load_dotenv()
#
#     base_url = os.getenv(
#         "test_marketplace_url_qa",
#         "Not Defined"
#     )
#
#     project_name = os.getenv(
#         "PROJECT_NAME",
#         "Not Defined"
#     )
#     version = os.getenv("current_version", "Not Defined")
#
#     with open(
#             allure_dir / "environment.properties",
#             "w",
#             encoding="utf-8"
#     ) as file:
#         file.write(
#             f"Project={project_name}\n"
#             f"Base URL={base_url}\n"
#             f"Environment=Staging\n"
#             f"Version={version}\n"
#             f"Browser=Chrome\n"
#             f"OS={platform.system()}\n"
#             f"Python={sys.version.split()[0]}\n"
#             f"Pytest={pytest.__version__}\n"
#             f"Playwright={importlib.metadata.version('playwright')}\n"
#             f"Allure_Pytest={importlib.metadata.version('allure-pytest')}\n"
#             f"Framework=Pytest + Playwright\n"
#         )
#
#     # ===============================
#     # Allure Categories
#     # ===============================
#
#     categories = [
#         {
#             "name": "Validation Failure",
#             "matchedStatuses": [
#                 "failed"
#             ]
#         },
#         {
#             "name": "Automation Error",
#             "matchedStatuses": [
#                 "broken"
#             ]
#         },
#         {
#             "name": "Skipped Test",
#             "matchedStatuses": [
#                 "skipped"
#             ]
#         }
#     ]
#
#     with open(
#             allure_dir / "categories.json",
#             "w",
#             encoding="utf-8"
#     ) as file:
#         json.dump(
#             categories,
#             file,
#             indent=4
#         )
#
def get_allure_results_dir(config) -> Path:
    # Same folder allure-pytest writes to (--alluredir in pytest.ini)
    return Path(
        config.getoption("allure_report_dir", None)
        or "artifacts/allure-results"
    )


def pytest_sessionstart(session):
    RESULT_DIR = get_allure_results_dir(session.config)
    REPORT_DIR = Path("artifacts/reports")
    REPORT_ZIP = Path("artifacts/DigitalMarketplace_Allure_Report.zip")
    SINGLE_REPORT = Path("artifacts/DigitalMarketplace_Allure_Report.html")

    # ==========================================
    # Remove previous run
    # ==========================================

    if RESULT_DIR.exists():
        shutil.rmtree(RESULT_DIR, ignore_errors=True)

    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR, ignore_errors=True)

    if REPORT_ZIP.exists():
        REPORT_ZIP.unlink()

    if SINGLE_REPORT.exists():
        SINGLE_REPORT.unlink()

    # Clean previous supporting artifacts
    for folder in [
        VIDEO_DIR,
        TRACE_DIR,
        SCREENSHOT_DIR
    ]:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ==========================================
    # Allure Environment
    # ==========================================

    load_dotenv()

    base_url = os.getenv(
        "test_marketplace_url_qa",
        "Not Defined"
    )

    project_name = os.getenv(
        "PROJECT_NAME",
        "Not Defined"
    )

    version = os.getenv(
        "current_version",
        "Not Defined"
    )

    with open(
            RESULT_DIR / "environment.properties",
            "w",
            encoding="utf-8"
    ) as file:

        file.write(
            f"Project={project_name}\n"
            f"Base_URL={base_url}\n"
            f"Environment=Staging\n"
            f"Version={version}\n"
            f"Browser=Chrome\n"
            f"OS={platform.system()}\n"
            f"Python={sys.version.split()[0]}\n"
            f"Pytest={pytest.__version__}\n"
            f"Playwright={importlib.metadata.version('playwright')}\n"
            f"Allure_Pytest={importlib.metadata.version('allure-pytest')}\n"
            f"Framework=Pytest + Playwright\n"
        )

    # ==========================================
    # Allure Categories
    # ==========================================

    categories = [
        {
            "name": "Validation Failure",
            "matchedStatuses": ["failed"]
        },
        {
            "name": "Automation Error",
            "matchedStatuses": ["broken"]
        },
        {
            "name": "Skipped Test",
            "matchedStatuses": ["skipped"]
        }
    ]

    with open(
            RESULT_DIR / "categories.json",
            "w",
            encoding="utf-8"
    ) as file:

        json.dump(
            categories,
            file,
            indent=4
        )


# =====================================================
# Screenshot
# =====================================================

def get_full_page_screenshot(self, name):
    screenshot_path = str(SCREENSHOT_DIR / f"{name}.png")
    self.page.screenshot(path=str(screenshot_path), full_page=True)

    allure.attach.file(str(screenshot_path), name=name, attachment_type=allure.attachment_type.PNG)


# =====================================================
# PLAYWRIGHT
# =====================================================

@pytest.fixture(scope="session")
def playwright() -> Playwright:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(
        playwright: Playwright
):
    global global_browser

    if global_browser is None:
        global_browser = (
            playwright.chromium.launch(

                headless=HEADLESS,

                slow_mo=SLOW_MO,

                args=[

                    "--start-maximized",

                    "--window-position=0,0",

                    "--high-dpi-support=1",

                    "--force-device-scale-factor=1",

                    "--ignore-certificate-errors",

                ]

            )
        )

    yield global_browser

    if global_browser:
        global_browser.close()

        global_browser = None


@pytest.fixture(scope="session")
def context(
        browser: Browser
):
    global global_context

    if global_context is None:

        global_context = (
            browser.new_context(

                viewport={"width": screen_width, "height": screen_height},

                device_scale_factor=1,

                ignore_https_errors=True,

                record_video_dir=str(
                    VIDEO_DIR
                ),

                record_video_size={"width": screen_width, "height": screen_height}

            )
        )

        if HIGHLIGHT_ENABLED:
            install_auto_highlighter()

    yield global_context

    if global_context:
        global_context.close()

        global_context = None


# =====================================================
# PAGE
# Module Scope
# Same page reuse for:
# Login + Download + Validation tests
# =====================================================

# @pytest.fixture(scope="module")
# def page(
#         context: BrowserContext
# ):
#     pg = context.new_page()
#
#     pg.bring_to_front()
#
#     yield pg
#
#     pg.close()
# ------------------------------------------------------------------
# Open new Chrome window/page because of using scope="function"
# ------------------------------------------------------------------
# @pytest.fixture(scope="function")
# def page(context: BrowserContext):
#     pg = context.new_page()
#
#     pg.bring_to_front()
#
#     yield pg
#
#     try:
#         if not pg.is_closed():
#             pg.close()
#     except Exception:
#         pass
#
# ------------------------------
# new
# --------------------
@pytest.fixture(scope="module")
def page(context: BrowserContext):
    pg = context.new_page()
    pg.bring_to_front()

    yield pg

    try:
        if not pg.is_closed():
            pg.close()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def stop_if_browser_closed(request):
    if "page" not in request.fixturenames:
        yield
        return

    page = request.getfixturevalue("page")

    try:
        if page.is_closed():
            pytest.exit(
                "Browser was closed manually. "
                "Stopping remaining tests and generating Allure report.",
                returncode=1
            )
    except Exception:
        pytest.exit(
            "Browser/context was closed. "
            "Stopping remaining tests and generating Allure report.",
            returncode=1
        )

    yield


# @pytest.fixture
# def new_tab(page):
#     def _open_new_tab(action):
#         with page.context.expect_page() as page_info:
#             action(page)
#
#         new_page = page_info.value
#         new_page.wait_for_load_state("domcontentloaded")
#
#         return new_page
#
#     return _open_new_tab

@pytest.fixture
def new_tab(page):
    def _open_new_tab(action):
        with page.context.expect_page() as page_info:
            action(page)

        new_page = page_info.value

        new_page.wait_for_load_state(
            "domcontentloaded"
        )

        new_page.bring_to_front()

        return new_page

    return _open_new_tab


# =====================================================
# TRACE
# Per Test
# =====================================================

@pytest.fixture(autouse=True)
def trace_per_test(
        request,
        context
):
    test_name = request.node.name

    timestamp = (
        datetime.datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    trace_file = (

            TRACE_DIR /

            f"{timestamp}_{test_name}.zip"

    )
    tracing_started = False

    try:

        context.tracing.start(

            screenshots=True,

            snapshots=True,

            sources=True

        )

        tracing_started = True
    except Exception as error:

        print(
            f"Trace start skipped: {error}"
        )

    yield

    if tracing_started:

        try:

            # Keep the trace only for failed/broken tests,
            # otherwise the Allure report grows by ~50 MB per test
            test_failed = any(
                getattr(request.node, f"rep_{phase}", None) is not None
                and getattr(request.node, f"rep_{phase}").failed
                for phase in ("setup", "call")
            )

            if not test_failed:
                context.tracing.stop()
                return

            context.tracing.stop(
                path=str(trace_file)
            )

            if trace_file.exists():
                allure.attach.file(
                    str(trace_file),
                    name=f"Playwright Trace - {test_name}",
                    attachment_type="application/zip"
                )

        except Exception as error:
            print(
                f"Trace stop skipped: {error}"
            )

    # except Exception:
    #
    #     pass
    #
    # yield
    #
    # try:
    #
    #     context.tracing.stop(path=str(trace_file))
    #
    #     if trace_file.exists():
    #         allure.attach.file(
    #             str(trace_file),
    #             name="Playwright Trace",
    #             attachment_type="application/zip"
    #         )
    #
    #
    #
    # except Exception:
    #
    #     pass


# =====================================================
# TEST RESULT PER PHASE
# Stores item.rep_setup / rep_call / rep_teardown
# so fixtures (trace_per_test) can check the outcome
# =====================================================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield

    report = outcome.get_result()

    setattr(item, f"rep_{report.when}", report)


# =====================================================
# SCREENSHOT ON FAILURE
# =====================================================

# @pytest.hookimpl(
#     hookwrapper=True
# )
# def pytest_runtest_makereport(
#         item,
#         call
# ):
#     outcome = yield
#
#     report = outcome.get_result()
#
#     if (
#
#             report.when == "call"
#
#             and
#
#             report.failed
#
#     ):
#
#         page = None
#
#         for value in item.funcargs.values():
#
#             if isinstance(
#
#                     value,
#
#                     Page
#
#             ):
#                 page = value
#
#                 break
#
#         if page:
#             timestamp = (
#
#                 datetime.datetime.now()
#
#                 .strftime(
#                     "%Y%m%d_%H%M%S"
#                 )
#
#             )
#
#             screenshot = (
#
#                     SCREENSHOT_DIR /
#
#                     f"{item.name}_{timestamp}.png"
#
#             )
#
#             page.screenshot(
#
#                 path=str(
#                     screenshot
#                 ),
#
#                 full_page=True
#
#             )
#

# =====================================================
# AUTO HIGHLIGHT
# =====================================================

# Locator actions that mark the field while Playwright interacts with it
HIGHLIGHT_ACTIONS = ["click", "dblclick", "fill", "type", "press_sequentially",
                     "check", "uncheck", "select_option", "set_input_files"]

# Restore the original outline of every marked field
_CLEAR_HIGHLIGHT_JS = """() => document.querySelectorAll('[data-pw-highlight]').forEach(el => {
    el.style.outline = el.getAttribute('data-pw-highlight');
    el.removeAttribute('data-pw-highlight');
})"""


def clear_highlight(page):
    try:
        page.evaluate(_CLEAR_HIGHLIGHT_JS)
    except Exception:
        pass  # page navigated after a click


def highlight_locator(locator: Locator, action: str):
    color = ACTION_COLORS.get(action, "red")
    try:
        # Remove the mark of the previous field, then mark the current field
        locator.evaluate(
            """(el, color) => {
                (""" + _CLEAR_HIGHLIGHT_JS + """)();
                el.setAttribute('data-pw-highlight', el.style.outline || '');
                el.style.outline = `3px solid ${color}`;
            }""",
            color,
            timeout=2000
        )
    except Exception:
        pass


def install_auto_highlighter():
    if getattr(Locator, "_selp_highlight", False):
        return

    for action in HIGHLIGHT_ACTIONS:
        original = getattr(Locator, action)

        def wrapper(self, *args, _original=original, _action=action, **kwargs):
            highlight_locator(self, _action)
            try:
                return _original(self, *args, **kwargs)
            finally:
                # No mark stays on the page after the action
                clear_highlight(self.page)

        setattr(Locator, action, wrapper)

    Locator._selp_highlight = True


#     First
# ------------------
# def pytest_sessionfinish(session, exitstatus):
#
#     RESULT_DIR = Path("allure-results")
#     REPORT_DIR = Path("artifacts/reports")
#     REPORT_ZIP = Path(
#         "artifacts/DigitalMarketplace.zip"
#     )
#
#     allure_path = (
#         r"C:\Tools\allure-2.44.1\bin\allure.bat"
#     )
#
#     # Remove previous report
#     if REPORT_DIR.exists():
#         shutil.rmtree(
#             REPORT_DIR,
#             ignore_errors=True
#         )
#
#     if REPORT_ZIP.exists():
#         REPORT_ZIP.unlink()
#
#     REPORT_DIR.mkdir(
#         parents=True,
#         exist_ok=True
#     )
#
#     try:
#
#         # Generate normal Allure report
#         subprocess.run(
#             [
#                     "allure",
#                     "generate",
#                     "allure-results",
#                     "-o",
#                     "artifacts/reports",
#                     "--clean",
#                     "--single-file"
#                 # allure_path,
#                 # "generate",
#                 # str(RESULT_DIR),
#                 # "-o",
#                 # str(REPORT_DIR),
#                 # "--clean"
#             ],
#             check=True
#         )
#
#         # Create shareable ZIP
#         shutil.make_archive(
#             "artifacts/DigitalMarketplace",
#             "zip",
#             REPORT_DIR
#         )
#
#         print("\n======================================")
#         print("ALLURE REPORT GENERATED SUCCESSFULLY")
#         print("======================================")
#         print(f"Report: {REPORT_DIR.resolve()}")
#         print(f"ZIP   : {REPORT_ZIP.resolve()}")
#         print("======================================\n")
#
#         # Open report correctly
#         subprocess.Popen(
#             [
#                 "allure",
#                 "open",
#                 "artifacts/reports"
#                 # allure_path,
#                 # "open",
#                 # str(REPORT_DIR)
#             ]
#         )
#
#     except subprocess.CalledProcessError as error:
#
#         print(
#             f"Allure report generation failed: {error}"
#         )
#
#     except Exception as error:
#
#         print(
#             f"Allure report processing failed: {error}"
#         )

# ------------------
# def pytest_sessionfinish(session, exitstatus):
#
#     RESULT_DIR = Path("allure-results")
#     REPORT_DIR = Path("artifacts/reports")
#
#     SHAREABLE_REPORT = Path(
#         "artifacts/DigitalMarketplace_Allure_Report.html"
#     )
#
#     allure_path = (
#         r"C:\Tools\allure-2.44.1\bin\allure.bat"
#     )
#
#     # Remove previous report
#     if REPORT_DIR.exists():
#         shutil.rmtree(
#             REPORT_DIR,
#             ignore_errors=True
#         )
#
#     if SHAREABLE_REPORT.exists():
#         SHAREABLE_REPORT.unlink()
#
#     REPORT_DIR.mkdir(
#         parents=True,
#         exist_ok=True
#     )
#
#     try:
#
#         # Generate standalone single-file Allure report
#         subprocess.run(
#             [
#                 allure_path,
#                 "generate",
#                 str(RESULT_DIR),
#                 "-o",
#                 str(REPORT_DIR),
#                 "--clean",
#                 "--single-file"
#             ],
#             check=True
#         )
#
#         generated_html = REPORT_DIR / "index.html"
#
#         if not generated_html.exists():
#             print(
#                 "\n❌ Single-file Allure index.html "
#                 "was not generated."
#             )
#             return
#
#         # Create standalone shareable HTML
#         shutil.copy2(
#             generated_html,
#             SHAREABLE_REPORT
#         )
#
#         print("\n======================================")
#         print("ALLURE REPORT GENERATED SUCCESSFULLY")
#         print("======================================")
#         print(
#             f"Report : {SHAREABLE_REPORT.resolve()}"
#         )
#         print("======================================\n")
#
#         # Open the actual standalone HTML
#         os.startfile(
#             str(SHAREABLE_REPORT.resolve())
#         )
#
#     except subprocess.CalledProcessError as error:
#
#         print(
#             f"\n❌ Allure report generation failed: {error}"
#         )
#
#     except Exception as error:
#
#         print(
#             f"\n❌ Allure report processing failed: {error}"
#         )
# ----------
def pytest_sessionfinish(session, exitstatus):
    RESULT_DIR = get_allure_results_dir(session.config)
    REPORT_DIR = Path("artifacts/reports")
    REPORT_ZIP = Path("artifacts/DigitalMarketplace.zip")

    allure_path = (
        r"C:\Tools\allure-2.44.1\bin\allure.bat"
    )

    # Check Allure CLI
    if not Path(allure_path).exists():
        print(f"\n❌ Allure CLI not found: {allure_path}")
        return

    # Check Allure results
    if not RESULT_DIR.exists():
        print("\n❌ allure-results directory not found.")
        return

    # categories.json is written by sessionstart, so only count real test results
    if not list(RESULT_DIR.glob("*-result.json")):
        print("\n❌ No Allure result JSON files found.")
        return

    # Remove previous report
    if REPORT_DIR.exists():
        shutil.rmtree(
            REPORT_DIR,
            ignore_errors=True
        )

    if REPORT_ZIP.exists():
        REPORT_ZIP.unlink()

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        print("\n======================================")
        print("GENERATING ALLURE REPORT")
        print("======================================")

        # Generate Allure report
        subprocess.run(
            [
                allure_path,
                "generate",
                str(RESULT_DIR),
                "-o",
                str(REPORT_DIR),
                "--clean",
                # One self-contained index.html, so it opens with a double-click
                "--single-file"
            ],
            check=True
        )

        # Create shareable ZIP
        shutil.make_archive(
            "artifacts/DigitalMarketplace",
            "zip",
            REPORT_DIR
        )

        print("\n======================================")
        print("ALLURE REPORT GENERATED SUCCESSFULLY")
        print("======================================")
        print(f"Report : {REPORT_DIR.resolve()}")
        print(f"ZIP    : {REPORT_ZIP.resolve()}")
        print("======================================\n")

        # Open Allure report
        subprocess.Popen(
            [
                allure_path,
                "open",
                str(REPORT_DIR)
            ]
        )

    except subprocess.CalledProcessError as error:
        print(
            f"\n❌ Allure report generation failed: {error}"
        )

    except Exception as error:
        print(
            f"\n❌ Allure report processing failed: {error}"
        )
#     Second
# def pytest_sessionfinish(session, exitstatus):
#
#     RESULT_DIR = Path("allure-results")
#     REPORT_DIR = Path("artifacts/reports")
#
#     FINAL_REPORT = Path(
#         "artifacts/DigitalMarketplace_Allure_Report.html"
#     )
#
#     allure_path = (
#         r"C:\Tools\allure-2.44.1\bin\allure.bat"
#     )
#
#     # ==========================================
#     # Remove previous report
#     # ==========================================
#
#     if REPORT_DIR.exists():
#         shutil.rmtree(
#             REPORT_DIR,
#             ignore_errors=True
#         )
#
#     if FINAL_REPORT.exists():
#         FINAL_REPORT.unlink()
#
#     REPORT_DIR.mkdir(
#         parents=True,
#         exist_ok=True
#     )
#
#     try:
#
#         # ==========================================
#         # Generate standalone single-file report
#         # ==========================================
#
#         subprocess.run(
#             [
#                 allure_path,
#                 "generate",
#                 str(RESULT_DIR),
#                 "-o",
#                 str(REPORT_DIR),
#                 "--clean",
#                 "--single-file"
#             ],
#             check=True
#         )
#
#         generated_report = (
#             REPORT_DIR / "index.html"
#         )
#
#         # ==========================================
#         # Move standalone report to artifacts
#         # ==========================================
#
#         if generated_report.exists():
#
#             shutil.move(
#                 str(generated_report),
#                 str(FINAL_REPORT)
#             )
#
#             print("\n======================================")
#             print("ALLURE REPORT GENERATED")
#             print("======================================")
#             print(
#                 f"Report: {FINAL_REPORT.resolve()}"
#             )
#             print("======================================\n")
#
#             # Open exactly the same standalone file
#             webbrowser.open(
#                 FINAL_REPORT.resolve().as_uri()
#             )
#
#         else:
#
#             print(
#                 "Allure single-file report "
#                 "was not generated."
#             )
#
#     except subprocess.CalledProcessError as error:
#
#         print(
#             f"Allure report generation failed: {error}"
#         )
#
#     except Exception as error:
#
#         print(
#             f"Allure report processing failed: {error}"
#         )

# generated_index = (
#     REPORT_DIR /
#     "index.html"
# )
#
# # ======================================
# # Copy as meaningful standalone file
# # ======================================
#
# if generated_index.exists():
#
#     shutil.copy2(
#         generated_index,
#         SINGLE_REPORT
#     )
#
# # ======================================
# # Create shareable ZIP
# # ======================================
#
# shutil.make_archive(
#     str(
#         REPORT_ZIP.with_suffix("")
#     ),
#     "zip",
#     REPORT_DIR
# )
#
# print("\n==========================================")
# print("ALLURE REPORT GENERATED")
# print("==========================================")
#
# print(
#     f"HTML Report : "
#     f"{SINGLE_REPORT.resolve()}"
# )
#
# print(
#     f"ZIP Report  : "
#     f"{REPORT_ZIP.resolve()}"
# )
#
# print(
#     f"Report Folder: "
#     f"{REPORT_DIR.resolve()}"
# )
#
# print("==========================================\n")
#
# # ======================================
# # Automatically open standalone HTML
# # ======================================
#
# if SINGLE_REPORT.exists():
#
#     webbrowser.open(
#         SINGLE_REPORT.resolve().as_uri()
#     )
#
# except subprocess.CalledProcessError as error:
#
#     print(
#         f"Allure report generation failed: "
#         f"{error}"
#     )
#
# except Exception as error:
#
#     print(
#         f"Allure report processing failed: "
#         f"{error}"
#     )

# def pytest_sessionfinish(session, exitstatus):
#     RESULT_DIR = Path("allure-results")
#
#     REPORT_DIR = Path(
#         "artifacts/reports"
#     )
#
#     if REPORT_DIR.exists():
#         shutil.rmtree(
#             REPORT_DIR
#         )
#
#     REPORT_DIR.mkdir(
#         parents=True,
#         exist_ok=True
#     )
#
#     allure_path = (
#         r"C:\Tools\allure-2.44.1\bin\allure.bat"
#     )
#
#     # Generate Allure HTML report
#     subprocess.run(
#         [
#             allure_path,
#             "generate",
#             str(RESULT_DIR),
#             "-o",
#             str(REPORT_DIR),
#             "--clean"
#         ],
#         check=True
#     )
#
#     # Create shareable zip report
#     REPORT_ZIP = Path(
#         "artifacts/DigitalMarketplace.zip"
#     )
#
#     if REPORT_ZIP.exists():
#         REPORT_ZIP.unlink()
#
#     shutil.make_archive(
#         "artifacts/DigitalMarketplace",
#         "zip",
#         "artifacts/reports"
#     )
#
#     # Open report automatically
#     subprocess.Popen(
#         [
#             allure_path,
#             "open",
#             str(REPORT_DIR)
#         ]
#     )
