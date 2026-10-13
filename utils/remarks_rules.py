# Remarks rules used by all test files (requisition, shopping cart and order remarks):
# - remarks are 0 (blank) to 500 characters, all special characters allowed
# - blank remarks are shown as "N/A" (or "n/a") in the Digital Marketplace and in ERP after the integration
#   (e.g. blank requisition remarks show N/A in the marketplace; blank cart remarks show N/A in ERP after the
#   vendor acknowledgement)

MAX_REMARKS_LENGTH = 500
BLANK_REMARKS_DISPLAY = "N/A"


def check_remarks_length(env_name, remarks):
    # Remarks from .env: blank (0) to 500 characters
    remarks = remarks or ""
    assert len(remarks) <= MAX_REMARKS_LENGTH, \
        f"{env_name} must be max {MAX_REMARKS_LENGTH} characters, found {len(remarks)}"
    return remarks


def expected_remarks_display(remarks):
    # How the system shows the remarks: "N/A" when blank, otherwise the text on one line
    remarks_text = " ".join((remarks or "").split())
    return remarks_text if remarks_text else BLANK_REMARKS_DISPLAY


def same_remarks(expected_remarks, shown_remarks):
    # The shown remarks are the expected remarks ("N/A" and "n/a" are the same)
    expected = expected_remarks_display(expected_remarks)
    shown = " ".join((shown_remarks or "").split())
    if expected == BLANK_REMARKS_DISPLAY:
        return shown.upper() == BLANK_REMARKS_DISPLAY
    return shown == expected
