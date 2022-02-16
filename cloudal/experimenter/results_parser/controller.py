import os
import hashlib
from functools import reduce

import pandas as pd

from helpers import get_logger, IGNORE_DIRS
from parsers import PARSERS

logger = get_logger(__name__)


ID = '_id'


class ParsingController:

    DEFAULT_OUTPUT_FILENAME = 'output'

    def __init__(self, input_path, output_path, parsers):
        self.input_path, self.output_path = self._ensure_path(input_path, output_path)

        self.combinations = [
            self._path_2_comb(self.input_path, directory)
            for directory in os.listdir(self.input_path)
            if directory not in IGNORE_DIRS and os.path.isdir(os.path.join(self.input_path, directory))
        ]
        # TODO: using Object Factory pattern
        self.parsers = [PARSERS[parser]() for parser in parsers]

    def parse(self):
        data_list = list()
        common_columns = set.intersection(*[set(comb) for _, comb in self.combinations])
        df_template = pd.DataFrame([comb for _, comb in self.combinations])
        common_columns.remove(ID)

        for parser in self.parsers:
            data = parser.parse(self.combinations)
            data = parser.post_process(data)
            columns = list(set(data.columns).difference(common_columns))
            data_list.append(data[columns])

        df = reduce(lambda x, y: pd.merge(x, y, on=ID, how='outer'), data_list)
        result = pd.merge(df_template, df, on=ID, how='outer')
        del result[ID]
        return result

    def write_result(self, data, output_format):
        logger.info("Write data to file %s" % self.output_path)
        df = pd.DataFrame(data)
        logger.info("Write %s rows as a %s file" % (len(df), output_format))
        if output_format not in self.output_path:
            self.output_path += '.' + output_format
        if output_format == 'csv':
            df.to_csv(self.output_path, index=False, encoding='utf-8')
        elif output_format == 'xlsx':
            df.to_excel(self.output_path, index=False, encoding='utf-8')

    def _ensure_path(self, input_path, output_path):
        if not os.path.isdir(input_path):
            raise IOError("%s directory not found" % input_path)

        if os.path.isdir(output_path):
            logger.info("%s is a directory, a default output file name is used" % output_path)
            if not os.path.exists(os.path.join(output_path, self.DEFAULT_OUTPUT_FILENAME)):
                output_path = os.path.join(output_path, self.DEFAULT_OUTPUT_FILENAME)

        i = 0
        cur_path = output_path
        while os.path.exists(cur_path):
            path, extension = os.path.splitext(output_path)
            cur_path = os.path.join(path + str(i) + extension)
            i += 1
        output_path = cur_path

        return input_path, output_path

    def _path_2_comb(self, path, comb_dir_name):
        comb_path = os.path.join(path, comb_dir_name)
        comb = comb_dir_name.replace('/', ' ').strip()
        i = iter(comb.split('-'))
        comb = dict(zip(i, i))
        comb[ID] = hashlib.sha256(comb.__repr__().encode('utf-8')).hexdigest()
        return comb_path, comb
