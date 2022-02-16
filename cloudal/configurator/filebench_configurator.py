import random

from cloudal.utils import get_logger, execute_cmd
from cloudal.configurator import packages_configurator

logger = get_logger()


class filebench_configurator(object): 
    def install_filebench(self, hosts):
        configurator = packages_configurator()
        configurator.install_packages(['build-essential', 'bison', 'flex', 'libtool'], hosts)

        cmd = 'wget https://github.com/filebench/filebench/archive/refs/tags/1.5-alpha3.tar.gz -P /tmp/ -N'
        execute_cmd(cmd, hosts)
        cmd = 'tar -xf /tmp/1.5-alpha3.tar.gz --directory /tmp/'
        execute_cmd(cmd, hosts)
        cmd = '''cd /tmp/filebench-1.5-alpha3/ &&
                 libtoolize &&
                 aclocal &&
                 autoheader &&
                 automake --add-missing &&
                 autoconf &&
                 ./configure &&
                 make &&
                 make install'''
        execute_cmd(cmd, hosts)

    def run_mailserver(self, hosts, duration, n_client, n_threads):
        filebench_hosts = random.sample(hosts, n_client)

        logger.info('Dowloading Filebench configuration file')
        cmd = 'wget https://raw.githubusercontent.com/filebench/filebench/master/workloads/varmail.f -P /tmp/ -N'
        execute_cmd(cmd, filebench_hosts)

        logger.info('Editing the configuration file')
        cmd = 'sed -i "s/tmp/tmp\/dc-$(hostname)/g" /tmp/varmail.f'
        execute_cmd(cmd, filebench_hosts)
        cmd = 'sed -i "s/run 60/run %s/g" /tmp/varmail.f' % duration
        execute_cmd(cmd, filebench_hosts)
        cmd = 'sed -i "s/name=bigfileset/name=bigfileset-$(hostname)/g" /tmp/varmail.f'
        execute_cmd(cmd, filebench_hosts)
        cmd = 'sed -i "s/meandirwidth=1000000/meandirwidth=1000/g" /tmp/varmail.f'
        execute_cmd(cmd, filebench_hosts)
        cmd = 'sed -i "s/nthreads=16/nthreads=%s/g" /tmp/varmail.f' % n_threads
        execute_cmd(cmd, filebench_hosts)

        logger.info('Clearing cache ')
        cmd = 'rm -rf /tmp/dc-$(hostname)/bigfileset'
        execute_cmd(cmd, filebench_hosts)
        cmd = 'sync; echo 3 > /proc/sys/vm/drop_caches'
        execute_cmd(cmd, filebench_hosts)

        logger.info('filebench_hosts = %s' % filebench_hosts)
        logger.info('Running filebench in %s second' % duration)
        cmd = 'setarch $(arch) -R filebench -f /tmp/varmail.f > /tmp/results/filebench_$(hostname)'
        execute_cmd(cmd, filebench_hosts)
        return True, filebench_hosts
