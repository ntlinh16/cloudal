import os
import re
from datetime import datetime

import pandas as pd

from helpers import get_logger, IGNORE_DIRS


logger = get_logger(__name__)


class BaseParser:

    def parse(self, combinations):
        pass

    def post_process(self, data):
        return data

    def _parse_datetime(self, datetime_str, format='%m/%d/%y %H:%M:%S.%f'):
        return datetime.strptime(datetime_str.strip()[:-3], format)


class FMKePopulateParser(BaseParser):

    def parse(self, combinations):
        logger.info("Parsing using %s" % self.__class__.__name__)
        data = list()
        try:
            for comb_dir_path, comb in combinations:
                cur_row = comb.copy()
                for file_name in os.listdir(comb_dir_path):
                    if 'pop_time' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            line = f.readline().strip().lower()
                            line = line.replace('"', '').replace('\\n', '\n')
                            if 'm' in line:
                                duration = re.findall('(.+)m(.+)s', line)
                                if duration:
                                    minutes, seconds = duration[0]
                                    cur_row['duration'] = int(minutes) * 60 + int(seconds)
                            else:
                                cur_row['duration'] = int(line)
                            cur_row['ops'] = float(f.readline().strip())
                data.append(cur_row)
        except IOError as e:
            logger.error(str(e))
        return pd.DataFrame(data)


class ElmerfsBenchParser(BaseParser):

    TIME_RE = re.compile(r'(\d+)m(\d*\.?\d+)s')

    def parse(self, combinations):
        logger.info("Parsing using %s" % self.__class__.__name__)
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
            logger.error(str(e))
        return pd.DataFrame(data)

    def _parse_runtime(self, time_str):
        r = self.TIME_RE.findall(time_str)[0]
        if len(r) == 2:
            minute, second = float(r[0]), float(r[1])
            return minute * 60 + second
        return None


class ElmerfsCopyTimeParser(BaseParser):

    def parse(self, combinations):
        logger.info("Parsing using %s" % self.__class__.__name__)
        data = list()
        try:
            for comb_dir_path, comb in combinations:
                cur_row = comb.copy()
                for file_name in os.listdir(comb_dir_path):
                    if '_start' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_row['time_cp_start'] = self.parse_datetime(f.readline())
                            cur_row['time_cp_end'] = self.parse_datetime(f.readline())
                            cur_row['src_host'] = file_name.split('_')[1]
                            src_site = cur_row['src_host'].split('-')[0]
                    elif 'checksum_copy_' in file_name:
                        with open(os.path.join(comb_dir_path, file_name), "r") as f:
                            cur_row['copy_ok'] = f.readline().strip()
                data.append(cur_row)
        except IOError as e:
            logger.error(str(e))
        return pd.DataFrame(data)

    def post_process(self, data):
        data['copy_time'] = data['time_cp_end'] - data['time_cp_start']
        data['copy_time'] = data['copy_time'].dt.total_seconds()
        return data


class ElmerfsConvergenceParser(BaseParser):

    def parse(self, combinations):
        logger.info("Parsing using %s" % self.__class__.__name__)
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
            logger.error(str(e))
        return pd.DataFrame(data)

    def post_process(self, data):
        data['copy_time'] = data['time_cp_end'] - data['time_cp_start']
        data['convergence_time'] = data['end_time'] - data['time_cp_start']
        data['copy_time'] = data['copy_time'].dt.total_seconds()
        data['convergence_time'] = data['convergence_time'].dt.total_seconds()
        data['latency'] = data['latency'].astype(int)
        data['iteration'] = data['iteration'].astype(int)
        sort_by = ['benchmarks', 'latency', 'iteration', 'src_host']
        columns = ['benchmarks', 'latency', 'iteration', 'src_host']
        if 'host_inner' in data:
            sort_by.append('host_inner')
            columns.append('host_inner')
        if 'host_outer' in data:
            sort_by.append('host_outer')
            columns.append('host_outer')
        if 'node' in data:
            sort_by.append('node')
            columns.append('node')
        sort_by.append('end_time')
        columns += ['time_cp_start', 'time_cp_end', 'end_time', 'copy_time', 'convergence_time']
        data.sort_values(by=sort_by, inplace=True)
        if "copy_ok" in data:
            columns.append("copy_ok")
        if "elmerfs_ok" in data:
            columns.append("elmerfs_ok")

        return data[columns]


class FMKeClientParser(BaseParser):

    def parse(self, combinations):
        logger.info("Parsing using %s" % self.__class__.__name__)
        data = list()
        try:
            for comb_dir_path, comb in combinations:
                cur_row = comb.copy()
                # change to results directory
                cur_dir_path = os.path.join(comb_dir_path, 'results')
                if not os.path.isdir(cur_dir_path):
                    continue
                for client_dir in os.listdir(cur_dir_path):
                    if client_dir in IGNORE_DIRS:
                        continue
                    cur_row = comb.copy()
                    cur_row['client'] = client_dir
                    for file_name in os.listdir(os.path.join(cur_dir_path, client_dir)):
                        if ('create-prescription_latencies' in file_name or
                                'update-prescription-medication_latencies' in file_name):
                            df = pd.read_csv(os.path.join(cur_dir_path, client_dir, file_name))
                            df.columns = [col.strip() for col in df.columns]
                            col_name = file_name.split('-')[0] + '_ops'
                            cur_row[col_name] = sum(df[df['window'] >= 8]['mean']) / 180
                    data.append(cur_row)
        except IOError as e:
            logger.error(str(e))
        return pd.DataFrame(data)

    def post_process(self, data):
        data['total_concurrent_clients'] = data['n_fmke_client_per_dc'].astype(
            int) * data['concurrent_clients'].astype(int)
        data1 = data.groupby('_id')[['total_concurrent_clients']].mean()
        data2 = data.groupby('_id')[['update_ops', 'create_ops']].sum()
        data = data1.merge(data2, on='_id')
        data = data.reset_index()
        return data


PARSERS = {
    'fmke_pop': FMKePopulateParser,
    'elmerfs_bench': ElmerfsBenchParser,
    'elmerfs_copy': ElmerfsCopyTimeParser,
    'elmerfs_convergence': ElmerfsConvergenceParser,
    'fmke_client': FMKeClientParser,
}
