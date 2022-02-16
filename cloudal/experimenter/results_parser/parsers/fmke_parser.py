from datetime import datetime
import os
import re

import pandas as pd

from helpers import IGNORE_DIRS
from parsers.base import BaseParser


class FMKePopulateParser(BaseParser):

    def parse(self, combinations):
        self.logger.info("Parsing using %s" % self.__class__.__name__)
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
            self.logger.error(str(e))
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
        columns += ['_id']
        return data[columns]


class FMKeClientParser(BaseParser):

    def parse(self, combinations):
        self.logger.info("Parsing using %s" % self.__class__.__name__)
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
            self.logger.error(str(e))
        return pd.DataFrame(data)

    def post_process(self, data):
        data['total_concurrent_clients'] = data['n_fmke_client_per_dc'].astype(
            int) * data['concurrent_clients'].astype(int)
        data1 = data.groupby('_id')[['total_concurrent_clients']].mean()
        data2 = data.groupby('_id')[['update_ops', 'create_ops']].sum()
        data = data1.merge(data2, on='_id')
        data = data.reset_index()
        return data
