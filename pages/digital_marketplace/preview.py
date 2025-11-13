import re

from utils.basic_actionsdm import BasicActionsDM


class Preview(BasicActionsDM):

    def __init__(self, page):
        super().__init__(page)

        self.page = page
        self.icon = page.locator("cr-icon")
