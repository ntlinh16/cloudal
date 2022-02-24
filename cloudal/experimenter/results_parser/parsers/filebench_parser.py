from asyncio.log import logger
import os
from pathlib import Path
import re

import pandas as pd

from parsers.base import BaseParser


class FileBenchParser(BaseParser):

    def parse_filebench_format(self, path):
        metadata = dict()
        operations = list()
        is_valid = False
        with open(path, 'r') as f:
            for line in f:
                if 'Filebench Version' in line:
                    metadata['filebench_version'] = line.split('Filebench Version')[1].strip()
                elif 'shared memory' in line:
                    metadata['shared_mem'] = line.split('of shared memory')[0].split('Allocated')[1].strip()
                elif 'successfully loaded' in line:
                    metadata['workload'] = line.split('personality successfully loaded')[0].split(':')[1].strip()
                elif 'populated' in line:
                    metadata['dir_name'] = re.findall(': ?([\w|\.|\-]+) populated', line)[0]
                    metadata['populated_files'] = int(re.findall(' ?populated: ?(\d+) file', line)[0])
                    metadata['avg_dir_width'] = float(re.findall(' ?width ?= ?(\d+)', line)[0])
                    metadata['avg_dir_depth'] = float(re.findall(' ?depth ?= ?(\d*\.?\d*)', line)[0])
                    metadata['leafdirs'] = int(re.findall('(\d*\.?\d*) leafdirs', line)[0])
                    metadata['total_size'] = re.findall('(\d*\.?\d*\w+) total size', line)[0]
                elif 'Run took' in line:
                    metadata['run_duration'] = int(re.findall(' ?Run took ?(\d+) second', line)[0])
                else:
                    tokens = [tok.strip() for tok in line.split(" ") if tok.strip()]
                    if 'ops' in line and 'ms' in line:
                        if 'Summary' not in line:
                            operations.append({
                                'name': tokens[0],
                                'ops': int(tokens[1].split('ops')[0].strip()),
                                'ops_per_sec': float(tokens[2].split('ops')[0].strip()),
                                'mb_per_sec': float(tokens[3].split('mb')[0].strip()),
                                'latency': float(tokens[4].split('ms')[0].strip()),
                                'range_lower': float(re.findall('(\d*\.?\d*)ms', tokens[5])[0]),
                                'range_upper': float(re.findall('(\d*\.?\d*)ms', tokens[7])[0])
                            })
                        else:
                            is_valid = True
                            operations.append({
                                'name': 'summary',
                                'ops': int(tokens[3].strip()),
                                'ops_per_sec': float(tokens[5].strip()),
                                'mb_per_sec': float(tokens[9].split('mb')[0].strip()),
                                'latency': float(tokens[10].split('ms')[0].strip()),
                            })
        if is_valid:
            return metadata, pd.DataFrame(operations)
        return None, None

    def parse(self, combinations):
        self.logger.info("Parsing using %s" % self.__class__.__name__)
        data = list()
        try:
            dfs = list()
            for comb_dir_path, comb in combinations:
                comb_dir_path = Path(comb_dir_path)
                is_valid = True
                for filepath in comb_dir_path.rglob('filebench*'):
                    metadata, df_operations = self.parse_filebench_format(filepath)
                    if metadata is None and df_operations is None:
                        is_valid = False
                        break
                    df_operations['_id'] = comb['_id']
                    dfs.append(df_operations)
                if not is_valid:
                    logger.error('Combination: %s is not valid' % comb_dir_path)
                    continue
            df_operations = pd.concat(dfs)
            for (_id, op_name), group in df_operations.groupby(['_id', 'name']):
                operation = {
                    'op_name': op_name,
                    'ops': group['ops'].sum(),
                    'ops_per_sec': group['ops_per_sec'].mean(),
                    'mb_per_sec': group['mb_per_sec'].mean(),
                    'latency': group['latency'].mean(),
                    '_id': _id,
                }
                if op_name != 'summary':
                    operation['range_lower'] = group['range_lower'].min()
                    operation['range_upper'] = group['range_upper'].max()
                data.append(operation)
        except IOError as e:
            self.logger.error(str(e))
        return pd.DataFrame(data)
