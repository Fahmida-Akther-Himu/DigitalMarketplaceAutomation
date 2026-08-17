import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import (
    Request,
    build_opener,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPBasicAuthHandler,
)

from dotenv import load_dotenv

# File location:
# project_root/pages/erp_procurement/reset_hub_page.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# Must be called before os.getenv()
load_dotenv(dotenv_path=ENV_FILE)


class ResetHubPage:

    def __init__(self, page=None):
        self.page = page

        self.resethub_username = os.getenv("test_resethub_username")
        self.resethub_password = os.getenv("test_resethub_password")

        if not self.resethub_username:
            raise RuntimeError(
                f"test_resethub_username was not found in {ENV_FILE}"
            )

        if not self.resethub_password:
            raise RuntimeError(
                f"test_resethub_password was not found in {ENV_FILE}"
            )

    def generate_reset_link(self, env: str, username: str) -> str:
        reset_url = (
            "https://resethub.bracits.com/api/public/link"
            f"?env={env}&username={username}"
        )

        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(
            None,
            reset_url,
            self.resethub_username,
            self.resethub_password,
        )

        auth_handler = HTTPBasicAuthHandler(password_mgr)
        opener = build_opener(auth_handler)

        request = Request(
            reset_url,
            headers={
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with opener.open(request, timeout=30) as response:
                response_data = response.read().decode("utf-8")

        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")

            raise RuntimeError(
                f"ResetHub API request failed: "
                f"{exc.code} {exc.reason}. "
                f"Response: {error_body}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"ResetHub API connection failed: {exc.reason}"
            ) from exc

        try:
            data = json.loads(response_data)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "ResetHub API returned invalid JSON."
            ) from exc

        generated_link = data.get("link")

        if not generated_link:
            raise RuntimeError(
                f"ResetHub response does not contain 'link': {data}"
            )

        print("Reset link generated successfully.")

        return generated_link

    def open_generated_link(self, link: str) -> None:
        if self.page is None:
            raise RuntimeError(
                "A Playwright page is required to open the generated link."
            )

        self.page.goto(
            link,
            wait_until="domcontentloaded",
        )

        self.page.wait_for_timeout(5000)
        self.page.reload(wait_until="domcontentloaded")

# import json
# from urllib.request import Request, build_opener, HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler
# from urllib.error import URLError, HTTPError
#
#
# class ResetHubPage:
#
#     def __init__(self, page):
#         self.page = page
#
#     def generate_reset_link(self, env: str, username: str):
#
#         reset_url = (
#             f"https://resethub.bracits.com/api/public/link?"
#             f"env={env}&username={username}"
#         )
#
#         password_mgr = HTTPPasswordMgrWithDefaultRealm()
#         password_mgr.add_password(None, reset_url, "linkbot", "7rnJYedY816TA9DjosPPFpyc363Ymk")
#         auth_handler = HTTPBasicAuthHandler(password_mgr)
#         opener = build_opener(auth_handler)
#
#         request = Request(
#             reset_url,
#             headers={
#                 "Accept": "application/json"
#             },
#             method="GET"
#         )
#
#         try:
#             with opener.open(request) as response:
#                 response_data = response.read().decode("utf-8")
#         except HTTPError as exc:
#             raise RuntimeError(f"ResetHub API request failed: {exc.code} {exc.reason}")
#         except URLError as exc:
#             raise RuntimeError(f"ResetHub API request failed: {exc.reason}")
#
#         data = json.loads(response_data)
#         generated_link = data["link"]
#
#         print("Generated Link:")
#         print(generated_link)
#
#         return generated_link
#
#     def open_generated_link(self, link):
#
#         self.page.goto(link)
#
#         self.page.wait_for_load_state("domcontentloaded")
#         # popup = self.page.locator("#modals")
#         # try:
#         #     popup.wait_for(state="visible", timeout=60000)
#         #     print("Popup appeared.")
#         # except TimeoutError:
#         #      print("Popup did not appear within 6 seconds.")
#
#         print("Refreshing page...")
#         self.page.wait_for_timeout(5000)  # Wait for 2 seconds before refreshing
#         self.page.reload(wait_until="domcontentloaded")
