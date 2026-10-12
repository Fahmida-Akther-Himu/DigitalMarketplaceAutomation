# Attachment rules used by all marketplace test files (shopping cart, delivery schedule, confirm order,
# order details, framework agreement documents):
# - an attachment is correct when it is downloaded (not empty) with the same file type (extension) as the
#   uploaded attachment
# - the file content is not compared: the staging server can change the file content (e.g. an XLS file is
#   shown as text)
from pathlib import Path


def same_file_type(downloaded_file, attachment_name):
    # Downloaded file (path) has the file type of the uploaded attachment and is not empty
    downloaded_file = Path(downloaded_file)
    return (downloaded_file.suffix.lower() == Path(attachment_name).suffix.lower()
            and downloaded_file.is_file() and downloaded_file.stat().st_size > 0)


def same_file_type_content(file_name, content, attachment_name):
    # File opened in the browser (name and content, not saved) has the file type of the uploaded attachment
    # and is not empty
    return Path(file_name).suffix.lower() == Path(attachment_name).suffix.lower() and len(content or b"") > 0
