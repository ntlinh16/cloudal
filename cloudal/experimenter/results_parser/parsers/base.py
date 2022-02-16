from datetime import datetime

from helpers import get_logger


class BaseParser:
    def __init__(self):
        self.logger = get_logger(__name__)

    def parse(self, combinations):
        pass

    def post_process(self, data):
        return data

    def _parse_datetime(self, datetime_str, format='%m/%d/%y %H:%M:%S.%f'):
        return datetime.strptime(datetime_str.strip()[:-3], format)
