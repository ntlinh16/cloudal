import os
import re

import pandas as pd

from parsers.base import BaseParser


class ElmerfsBenchParser(BaseParser):

    TIME_RE = re.compile(r'(\d+)m(\d*\.?\d+)s')

    def parse(self, combinations):
        self.logger.info("Parsing using %s" % self.__class__.__name__)
        data = list()
        try:
            for comb_dir_path, comb in combinations:
                for file_name in os.listdir(comb_dir_path):
                    cur_row = comb.copy()
                    if '_bench' in file_name:
                        cur_row['hostname'] = file_name.split('_bench')[0].strip()

                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            lines = [self._parse_runtime(line.strip().split('\t')[-1])
                                     for line in f if line.strip() and 'real' in line]
                            if len(lines) == 1:
                                cur_row['time_bench'] = lines[0]
                        data.append(cur_row)
        except IOError as e:
            self.logger.error(str(e))
        return pd.DataFrame(data)

    def _parse_runtime(self, time_str):
        r = self.TIME_RE.findall(time_str)[0]
        if len(r) == 2:
            minute, second = float(r[0]), float(r[1])
            return minute * 60 + second
        return None


class ElmerfsCopyTimeParser(BaseParser):

    def parse(self, combinations):
        self.logger.info("Parsing using %s" % self.__class__.__name__)
        data = list()
        try:
            for comb_dir_path, comb in combinations:
                cur_row = comb.copy()
                for file_name in os.listdir(comb_dir_path):
                    if '_start' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_row['time_cp_start'] = self._parse_datetime(f.readline())
                            cur_row['time_cp_end'] = self._parse_datetime(f.readline())
                            cur_row['src_host'] = file_name.split('_')[1]
                            src_site = cur_row['src_host'].split('-')[0]
                    elif 'checksum_copy_' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_row['copy_ok'] = f.readline().strip()
                data.append(cur_row)
        except IOError as e:
            self.logger.error(str(e))
        return pd.DataFrame(data)

    def post_process(self, data):
        data['copy_time'] = data['time_cp_end'] - data['time_cp_start']
        data['copy_time'] = data['copy_time'].dt.total_seconds()
        return data


class ElmerfsConvergenceParser(BaseParser):

    def parse(self, combinations):
        self.logger.info("Parsing using %s" % self.__class__.__name__)
        data = list()
        try:
            for comb_dir_path, comb in combinations:
                src_site = ""
                cur_row = comb.copy()
                for file_name in os.listdir(comb_dir_path):
                    if '_start' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_row['time_cp_start'] = self._parse_datetime(f.readline())
                            cur_row['time_cp_end'] = self._parse_datetime(f.readline())
                            cur_row['src_host'] = file_name.split('_')[1]
                            src_site = cur_row['src_host'].split('-')[0]
                    elif 'checksum_copy_' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_row['copy_ok'] = f.readline().strip()
                    elif 'checkelmerfs_' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_row['elmerfs_ok'] = 0
                            if "rpfs on" in f.readline().strip():
                                if "rpfs on" in f.readline().strip():
                                    cur_row['elmerfs_ok'] = 1
                for file_name in os.listdir(comb_dir_path):
                    if '_end' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_end_row = cur_row.copy()
                            cur_end_row['end_time'] = self._parse_datetime(f.readline())
                            host_name = file_name.split('_')[1]
                            if src_site in host_name:
                                cur_end_row['host_inner'] = host_name
                            else:
                                cur_end_row['host_outer'] = host_name
                        data.append(cur_end_row)

        except IOError as e:
            self.logger.error(str(e))
        return pd.DataFrame(data)
