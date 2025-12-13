import re

from utils.basic_actionsdm import BasicActionsDM


class Preview(BasicActionsDM):

    def __init__(self, page, logger=None):
        super().__init__(page)

        self.page = page
        self.logger = logger
        self.icon = page.locator("cr-icon")

    ##################### small helper so we can log easily #####################
    def _log(self, message: str):
        if self.logger:
            self.logger.step(message)
