import pytest
from dotenv import load_dotenv
import os
import re
import random
import string
from conftest import new_tab
# from conftest_1 import new_tab
from datetime import datetime, timedelta

load_dotenv()

# Project URLs
proj_url = os.getenv("test_url")
requisition_list_url = proj_url + "/procurementDashboard/myDashboard#!/requisition/list"

# Procurement information
proj_user = os.getenv("test_user_name")
proj_pass = os.getenv("test_user_pass")
marketplace_password = os.getenv("test_marketplace_password")
marketplace_admin = os.getenv("test_order_admin")

agreement_officer = os.getenv("test_agreement_officer")
agreement_number = os.getenv("test_agreement_number")

agreement = os.getenv("test_white_listed_agreement")
proc_admin = os.getenv("test_proc_admin")
amended_agreement_recommender = os.getenv("test_amended_agreement_recommender")
amended_agreement_approver = os.getenv("test_amended_agreement_approver")
moq_value = os.getenv("test_moq_value")

marketplace_url_qa = os.getenv("test_marketplace_url_qa")

# order_reference_number = os.getenv("test_order_reference_number")

# Page models for procurement
from pages.digital_marketplace.procurement_login_page import ProcurementLoginPage
from pages.digital_marketplace.dashboard_page import DashboardPage
from pages.digital_marketplace.procurement_home_page import ProcurementHomePage
from pages.digital_marketplace.main_navigation_bar import MainNavigationBar
from pages.digital_marketplace.framework_information import FrameworkInformation
from pages.digital_marketplace.framework_order_list import FrameworkOrderListPage
from pages.digital_marketplace.framework_list import FrameworkList
from pages.digital_marketplace.framework_agreement_information import FrameworkAgreementInformation

# Page models for marketplace
from pages.digital_marketplace.login_page import LoginPage
from pages.digital_marketplace.home_page import HomePage
from pages.digital_marketplace.main_navigation_menu import MainNavigationMenu

# For validation
from playwright.sync_api import expect

# Import for beautiful reporting
from rich.traceback import install

install()
# Procurement global variable
allowed_chars = string.ascii_letters + string.digits + ' '
amendment_remarks = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
edit_remarks = ''.join(random.choices(string.ascii_letters + string.digits + string.ascii_letters, k=15))
agreement_remarks = ''.join(random.choices(allowed_chars, k=20))
approval_remarks = ''.join(random.choices(allowed_chars, k=20))

# Procurement global variable
agreement_approver = ''
agreement_reviewer = ''
agreement_recommender = ''


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
       Test Case 1: Search Whitelisted Framework Agreement in Procurement System.

       Objective:
           To verify that a framework/agreement officer can successfully log in to the ERP Procurement system,
           navigate to the Framework Agreement List, and accurately search for a whitelisted framework agreement
           using a valid agreement number.

       """)
def test_1_search_whitelisted_framework_agreement_in_procurement(page, new_tab, logger):
    """
       Test Case 1: Search Whitelisted Framework Agreement in Procurement System.

       Objective:
           To verify that a framework/agreement officer can successfully log in to the ERP Procurement system,
           navigate to the Framework Agreement List, and accurately search for a whitelisted framework agreement
           using a valid agreement number.

       Steps:
           1. Log in to the ERP Procurement system using framework agreement officer credentials.
           2. Navigate to the Procurement module from the dashboard.
           3. Go to the Framework Agreement List page.
           4. Search for a framework agreement using the provided agreement number.
           5. Capture screenshots at each critical step for verification.
       """
    print("Test 1: Framework agreement searches for amendment")
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=agreement_officer,
        pass_word=proj_pass,
        timeout=60000
    )
    logger.step(f" Logging in as user: {agreement_officer}")
    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()
    proc_dashboard_page.get_full_page_screenshot('1. Framework officer enters procurement module')

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.goto_framework_agreement_list()

    framework_list = FrameworkList(page)
    framework_list.get_full_page_screenshot('2. Framework officer go to the framework agreement list')
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.get_full_page_screenshot('3. Framework officer searches the framework agreement number')


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
       Test Case 2: View Whitelisted Framework Agreement Details in Procurement System.

       Objective:
           To verify that the framework agreement officer can successfully open and view the
           detailed information of a whitelisted framework agreement from the Framework
           Agreement List in the ERP Procurement system.
       """)
def test_2_view_whitelisted_agreement_details_in_procurement(page, new_tab):
    """
       Test Case 2: View Whitelisted Framework Agreement Details in Procurement System.

       Objective:
           To verify that the framework agreement officer can successfully open and view the
           detailed information of a whitelisted framework agreement from the Framework
           Agreement List in the ERP Procurement system.

       Steps:
           1. Click on the framework agreement number (FA link) from the framework list.
           2. Open the framework agreement details in a new browser tab.
           3. Capture a full-page screenshot for verification.
           4. Retrieve and display the vendor information.
           5. Print and verify the agreement date, price review date, start date, and end date.
           6. Print and verify the framework item details.
           7. Navigate back to the framework agreement list.
           8. Close the newly opened framework details tab.
       """
    print("Test 2: Framework agreement views for before amendment")
    framework_list = FrameworkList(page)
    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_list.get_full_page_screenshot('4. Framework officer views the framework agreement details')

    framework_info = FrameworkInformation(new_page)
    framework_info.get_vendor_info()
    framework_info.print_agreement_date()
    framework_info.print_price_review_date()
    framework_info.print_from_date()
    framework_info.print_to_date()
    framework_info.print_framework_item_details()
    # framework_info.print_item_details_2()
    framework_info.go_to_framework_list()
    new_page.close()


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
       Test Case 3: Confirm Framework Agreement Amendment and Capture Reviewer Information.

       Objective:
           To validate that a framework agreement amendment can be successfully confirmed
           and that the assigned reviewer ID is correctly captured from the agreement status.

       """)
def test_3_confirm_agreement_amendment_and_capture_reviewer(page, new_tab, logger):
    """
       Test Case 3: Confirm Framework Agreement Amendment and Capture Reviewer Information.

       Objective:
           To validate that a framework agreement amendment can be successfully confirmed
           and that the assigned reviewer ID is correctly captured from the agreement status.

       Steps:
           1. Search for the framework agreement using the agreement number.
           2. Open the framework agreement details in a new browser tab.
           3. Enter amendment remarks in the comment section.
           4. Confirm the agreement amendment.
           5. Close the framework agreement details tab.
           6. Re-search the framework agreement from the list.
           7. Capture and store the assigned agreement reviewer ID.
           8. Log the reviewer ID for reporting and traceability.
       """
    print("Test 3: Framework agreement amendment confirmation")
    framework_list = FrameworkList(page, logger)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    new_page = new_tab(lambda p: framework_list.fa_no_link.click())

    framework_info = FrameworkInformation(new_page)
    framework_info.enter_agreement_comments(comments=amendment_remarks)
    framework_info.get_full_page_screenshot('5. Framework agreement details after entering agreement comments')
    framework_info.confirm_agreement_amendment()
    new_page.close()

    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.get_full_page_screenshot(
        '6. Search framework agreement details after confirming agreement amendment')
    global agreement_reviewer
    agreement_reviewer = str(int(framework_list.get_status_info()))
    print("Agreement Reviewer ID:", agreement_reviewer)
    logger.step(f" 📥 Agreement Reviewer ID: {agreement_reviewer}")


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
    Test Case 4: Reviewer Modifies and Submits a Framework Agreement.

    Objective:
        Verify that a framework agreement reviewer can modify agreement details,
        update document attachments, adjust item information including unit price and MOQ,
        and submit the amended agreement for approval in the ERP Procurement system.
    """)
def test_4_reviewer_modifies_and_submits_framework_agreement(page, new_tab):
    """
        Test Case 4: Reviewer Modifies and Submits a Framework Agreement.

        Objective:
            Verify that a framework agreement reviewer can modify agreement details,
            update document attachments, adjust item information including unit price and MOQ,
            and submit the amended agreement for approval in the ERP Procurement system.

        Steps:
            1. Open the framework agreement details from the framework list in a new tab.
            2. Enter comments regarding the amendment.
            3. Click the edit button to enable modification.
            4. Update key dates: start date, end date, and price review date.
            5. Upload required framework documents.
            6. Mark the agreement as applicable for both parties.
            7. Enter remarks for the agreement.
            8. Review item details and print them for verification.
            9. Modify item-specific information, such as unit price and minimum order quantity (MOQ).
            10. Update the agreement with the modified information.
            11. Select the recommender and approver for the amended agreement.
            12. Submit the amended framework agreement.
            13. Close the framework agreement tab.

        """
    print("Test 4: Framework agreement modification and submission by reviewer")
    framework_list = FrameworkList(page)
    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_info = FrameworkInformation(new_page)
    framework_info.enter_agreement_comments(comments=edit_remarks)
    framework_info.get_full_page_screenshot(
        '7. Framework agreement details after entering agreement modification comments')
    framework_info.edit_button.click()
    framework_info.wait_for_timeout(2000)

    framework_agreement_information = FrameworkAgreementInformation(new_page)
    framework_agreement_information.select_start_date()
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.select_end_date()
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.select_price_review_date()
    framework_agreement_information.wait_for_timeout(2000)

    current_dir = os.getcwd()
    document_location = os.path.join(current_dir, 'utils', 'upload_file.pdf')
    framework_agreement_information.upload_framework_document(document_location)
    framework_agreement_information.applicable_for_both.click()
    framework_agreement_information.enter_remarks(remarks=agreement_remarks)
    framework_agreement_information.print_item_details()
    # framework_agreement_information.print_table_data()
    # framework_agreement_information.print_table_data(only_status=True)
    # framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.modify_item_unit_price(unit_price="50")
    framework_agreement_information.modify_agreement_moq(value=moq_value)
    framework_agreement_information.get_full_page_screenshot(
        '8. Framework agreement details view after modification agreement')
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.update_agreement()
    framework_agreement_information.get_full_page_screenshot(
        '9. Framework agreement details view before update output document')
    framework_agreement_information.recommender_checkbox_selection()
    framework_agreement_information.wait_for_timeout(2000)
    framework_agreement_information.recommender_selection(agreement_recommender=amended_agreement_recommender)
    framework_agreement_information.approver_selection(agreement_approver=amended_agreement_approver)
    framework_agreement_information.get_full_page_screenshot(
        '10. Framework agreement details view after update output document')
    framework_agreement_information.amended_agreement_submission()

    # framework_agreement_information.wait_for_timeout(2000)
    new_page.close()


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
    Test Case 5: Identify Framework Agreement Recommender and Logout.

    Objective:
        To verify that the system correctly displays the assigned recommender for an
        amended framework agreement and to ensure the user can successfully log out
        of the ERP Procurement system.
    """)
def test_5_identify_framework_agreement_recommender_and_logout(page):
    """
        Test Case 5: Identify Framework Agreement Recommender and Logout.

        Objective:
            To verify that the system correctly displays the assigned recommender for an
            amended framework agreement and to ensure the user can successfully log out
            of the ERP Procurement system.

        Steps:
            1. Search for the framework agreement using the agreement number.
            2. View and print the current status of the agreement.
            3. Capture the assigned recommender ID from the agreement status.
            4. Store the recommender ID for use in subsequent test cases.
            5. Exit the current module and log out from the system.

        """
    print("Test 5: Framework agreement recommender identification and logout")
    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.agreement_status_print()
    framework_list.get_full_page_screenshot('11. Framework agreement list view after submission agreement')

    global agreement_recommender
    agreement_recommender = str(int(framework_list.get_status_info()))
    print("Recommender ID:", agreement_recommender)

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.wait_for_timeout(2000)


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
    Test Case 6: Framework Agreement Recommender Approval.

    Objective:
        To verify that the assigned recommender can successfully log in,
        review the amended framework agreement, provide approval remarks,
        and approve the framework agreement in the ERP Procurement system.
    """)
def test_6_recommender_approves_framework_agreement(page, new_tab):
    """
       Test Case 6: Framework Agreement Recommender Approval.

       Objective:
           To verify that the assigned recommender can successfully log in,
           review the amended framework agreement, provide approval remarks,
           and approve the framework agreement in the ERP Procurement system.

       Steps:
           1. Log in to the ERP Procurement system as the framework agreement recommender.
           2. Navigate to the Procurement module.
           3. Open the Framework Agreement List.
           4. Search for the framework agreement using the agreement number.
           5. Open the framework agreement details in a new tab.
           6. Enter approval remarks.
           7. Confirm and submit the framework agreement approval.
           8. Close the framework agreement details tab.
       """
    print("Test 6: Framework agreement approves by recommender")
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=agreement_recommender,
        pass_word=proj_pass,
        timeout=60000
    )

    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()
    proc_dashboard_page.get_full_page_screenshot('12. Framework recommender enters procurement module')

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.goto_framework_agreement_list()
    print("Framework agreement search")

    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_list.get_full_page_screenshot('13. Framework recommender views the framework agreement details')

    framework_info = FrameworkInformation(new_page)
    framework_info.enter_agreement_comments(comments=approval_remarks)
    framework_info.get_full_page_screenshot(
        '14. Framework agreement recommender views after entering agreement approval comments')
    framework_info.confirm_agreement_approval()
    new_page.close()


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
        Test Case 7: Identify Framework Agreement Approver and Logout.

        Objective:
            To verify that the system correctly displays the assigned approver for the
            framework agreement after recommender approval and to ensure the user can
            successfully log out of the ERP Procurement system.
        """)
def test_7_identify_framework_agreement_approver_and_logout(page):
    """
        Test Case 7: Identify Framework Agreement Approver and Logout.

        Objective:
            To verify that the system correctly displays the assigned approver for the
            framework agreement after recommender approval and to ensure the user can
            successfully log out of the ERP Procurement system.

        Steps:
            1. Search for the framework agreement using the agreement number.
            2. Retrieve and capture the currently assigned approver ID from the agreement status.
            3. Store the approver ID for use in the next approval test case.
            4. Exit the current module.
            5. Log out from the ERP Procurement system.
        """
    print("Test 7: Framework agreement approver identified and logged out")
    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.get_full_page_screenshot(
        '15. Framework agreement recommender views the framework agreement approver information')
    global agreement_approver
    agreement_approver = str(int(framework_list.get_status_info()))
    print("Approver ID:", agreement_approver)

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.wait_for_timeout(2000)


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
        Test Case 8: Framework Agreement Final Approval by Approver.

        Objective:
            To verify that the assigned approver can successfully log in, review the
            framework agreement after recommender approval, add approval comments,
            and provide the final approval in the ERP Procurement system.
        """)
def test_8_approver_approves_framework_agreement(page, new_tab):
    """
        Test Case 8: Framework Agreement Final Approval by Approver.

        Objective:
            To verify that the assigned approver can successfully log in, review the
            framework agreement after recommender approval, add approval comments,
            and provide the final approval in the ERP Procurement system.

        Steps:
            1. Log in to the ERP Procurement system as the framework agreement approver.
            2. Navigate to the Procurement module.
            3. Open the Framework Agreement List.
            4. Search for the framework agreement using the agreement number.
            5. Open the framework agreement details in a new browser tab.
            6. Enter approval remarks.
            7. Confirm and submit the framework agreement approval.
            8. Close the framework agreement details tab.
        """
    print("Test 8: Framework agreement approves by approver")
    proc_login_page = ProcurementLoginPage(page)
    proc_login_page.perform_login(
        given_url=proj_url,
        user_name=agreement_approver,
        pass_word=proj_pass,
        timeout=60000
    )

    proc_dashboard_page = DashboardPage(page)
    proc_dashboard_page.goto_procurement()

    proc_home_page = ProcurementHomePage(page)
    proc_home_page.goto_framework_agreement_list()
    print("Test 1: Framework agreement search")

    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.get_full_page_screenshot('16. Framework agreement approver searches the framework agreement')

    new_page = new_tab(lambda p: framework_list.fa_no_link.click())
    framework_info = FrameworkInformation(new_page)
    framework_info.enter_agreement_comments(comments=approval_remarks)
    framework_info.get_full_page_screenshot(
        '17. Framework agreement approver views after entering agreement approval comments')
    framework_info.confirm_agreement_approval()
    new_page.close()


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
        Test Case 9: Verify Final Framework Agreement Status.

        Objective:
            To verify that the framework agreement has been successfully approved by
            all required authorities and that its final status is correctly updated
            and visible in the ERP Procurement system.
        """)
def test_9_verify_final_framework_agreement_status(page):
    """
        Test Case 9: Verify Final Framework Agreement Status.

        Objective:
            To verify that the framework agreement has been successfully approved by
            all required authorities and that its final status is correctly updated
            and visible in the ERP Procurement system.

        Steps:
            1. Search for the framework agreement using the agreement number.
            2. Retrieve and verify the final status of the framework agreement.
            3. Exit the framework agreement module.
            4. Log out from the ERP Procurement system.
        """
    print("Test 9: Framework agreement final status identified")
    framework_list = FrameworkList(page)
    framework_list.search_agreement(search_framework_agreement=agreement_number)
    framework_list.get_full_page_screenshot(
        '18. Framework agreement approver searches the framework agreement after approval of agreement')
    framework_list.get_status_info()

    m_page = MainNavigationBar(page)
    m_page.exit()
    m_page.logout()
    m_page.wait_for_timeout(2000)


@pytest.mark.reporting(
    functional_specification="test_1",
    test_description="""
        Test Case 10: Verify DM Login
        
        Objective:
        To verify that a marketplace login

        """)
def test_10_marketplace_login(page):
    """
    Test Case 10: Marketplace Login.

    Objective:
        To verify that a marketplace login

    """
    print("Test 10: Marketplace Login...")
    login_page = LoginPage(page)
    login_page.navigate_to_url(marketplace_url_qa)
    login_page.perform_login_for_sso_login(
        user_name=proj_user,
        pass_word=marketplace_password
    )

    home_page = HomePage(page)
    home_page.verify_welcome_message()
    home_page.get_full_page_screenshot('19. Welcome to marketplace homepage or landing page')
    home_page.wait_for_timeout(2000)

    dm_logout = MainNavigationMenu(page)
    dm_logout.perform_logout()
    dm_logout.get_full_page_screenshot('20. Logout from the marketplace homepage')
