import os
import threading
from datetime import datetime
from time import sleep
from threading import Lock, Thread

import cloudal.experimenting.exp_g5k_utils as g5k_utils
from cloudal.action import performing_actions
from cloudal.utils import parse_config_file, get_logger, execute_cmd
from cloudal.provisioning.grid5k_provisioner import grid5k_provisioner
from cloudal.configuring.docker_debian10_configuring import docker_debian_configuring

from execo_engine import slugify
from execo_g5k import oardel
from execo_g5k.oar import get_oar_job_info


logger = get_logger()


class DockerBootTime_Measurement(performing_actions):

    def __init__(self):
        """ Add options for the number of measures, number of nodes
        walltime, env_file or env_name and clusters and initialize the engine
        """

        # Using super() function to access the parrent class
        # so that we do not care about the changing of parent class

        super(DockerBootTime_Measurement, self).__init__()

        self.args_parser.add_argument("-k", dest="keep_alive",
                                      help="keep the reservation alive after deploying.",
                                      action="store_true")

        self.args_parser.add_argument("-o", dest="out_of_chart",
                                      help="run the engine outside of grid5k charter",
                                      action="store_true")

        self.args_parser.add_argument("-j", dest="oar_job_ids",
                                      help="the reserved oar_job_ids on grid5k. The format is site1:oar_job_id1,site2:oar_job_id2,...",
                                      type=str)

        self.args_parser.add_argument("--no-deploy-os", dest="no_deploy_os",
                                      help="specify not to deploy OS on reserved nodes",
                                      action="store_true")

        # Lock sharing data between threads while updating
        self.lock = Lock()

    def define_parameters(self):
        """Define the parameters space you want to explore

        Returns
        -------
        dict
            key: str, the name of the experiment parameter
            value: list, a list of possible values for a parameter of the experiment
        """
        self.parameters = {
            'n_dockers': range(1, self.settings['parameters']['n_dockers'] + 1),
            'n_co_dockers': range(1, self.settings['parameters']['n_co_dockers'] + 1),
            'n_mem': range(1, self.settings['parameters']['n_mem'] + 1),
            'n_cpu': range(1, self.settings['parameters']['n_cpu'] + 1),
            'cpu_sharing': [self.settings['parameters']['cpu_sharing']],
            'cpu_policy': [self.settings['parameters']['cpu_policy']],
            'boot_policy': [self.settings['parameters']['boot_policy']],
            'co_workload': [self.settings['parameters']['co_workload']],
            'iteration': range(1, self.settings['parameters']['iteration'] + 1)
        }
        if self.settings['exp_env']['bandwidth']:
            self.parameters['bandwidths'] = range(1, self.settings['exp_env']['bandwidth'] + 1, 1)

        return self.parameters

    def _provisioning(self):
        """self.oar_result containts the list of tuples (oar_job_id, site_name)
        that identifies the reservation on each site,
        which can be retrieved from the command line arguments or from make_reservation()"""

        self.provisioner = grid5k_provisioner(config_file_path=self.args.config_file_path,
                                               keep_alive=self.args.keep_alive,
                                               out_of_chart=self.args.out_of_chart)

        """
        TODO:
            + write function to check all nodes in a job is alive
            + modify make_reservation function to accept error_hosts
              -> make replacement reservation or cancel program or ignore
            + after checking for case args.oar_job_ids is not None, change it to None
              so that it won't be called in the 2nd time on
            
+        """
        if self.args.oar_job_ids is not None:
            self.provisioner.oar_result = list()
            logger.info('Checking oar_job_id is valid or not')
            for each in self.args.oar_job_ids.split(','):
                site_name, oar_job_id = each.split(':')
                oar_job_id = int(oar_job_id)
                # check validity of oar_job_id
                job_info = get_oar_job_info(oar_job_id=oar_job_id, frontend=site_name)
                if job_info is None or len(job_info) == 0:
                    logger.error("Job id: %s in %s is not a valid Grid5000 oar job id" %
                                 (oar_job_id, site_name))
                    logger.error("Please rerun the script with a correct job id")
                    exit()
                self.provisioner.oar_result.append((int(oar_job_id), str(site_name)))
        else:
            logger.info("START PROVISIONING PROCESS")
            self.provisioner.make_reservation(job_name=self.__class__.__name__)

        """Retrieve the hosts address list and (ip, mac) list from a list of oar_result and
        return the resources which is a dict needed by grid5k_provisioner """
        logger.info('Getting resources infomation')
        self.provisioner.get_resources()
        self.hosts = self.provisioner.hosts
        self.oar_result = self.provisioner.oar_result
        # logger.info('Reserved hosts: %s' % self.hosts)
        # logger.info('oar_result: %s' % self.oar_result)

        if not self.args.no_deploy_os:
            self.provisioner.setup_hosts()

        logger.info('-----> PROVISIONING PROCESS FINISHED')

    def _setup_ssd(self):
        """Installation of packages"""
        logger.info('SETUP SSD DISK FOR RESERVED NODES')
        cmd = 'umount /tmp; mount -t ext4 /dev/sdf1 /tmp;'
        self.error_hosts = execute_cmd(cmd, self.hosts)

    def _setup_ceph(self):
        logger.info('SETTING CEPH ON RESERVED NODES')
        cmd = '''export DEBIAN_FRONTEND=noninteractive && ''' + \
              '''apt-get update -y --force-yes && ''' + \
              '''apt-get install -y --force-yes ceph'''
        self.error_hosts = execute_cmd(cmd, self.hosts)
        logger.info('Install ceph + packages ... DONE')

        logger.info('Setting from ceph master')
        for host in self.hosts:
            cmd = '''ceph-deploy install %s''' % (host)
            error_hosts = execute_cmd(cmd, [self.settings['exp_env']['ceph_master']])
            cmd = '''ceph-deploy admin %s''' % (host)
            error_hosts = execute_cmd(cmd, [self.settings['exp_env']['ceph_master']])
        logger.info('Setting from ceph master ... DONE')

        logger.info('Create volume for docker root file on ceph master')
        cmd = 'rbd create docker_root --size 102400 --pool rbd'
        error_hosts = execute_cmd(cmd, [self.args['ceph_master']])
        logger.info('Create volume in ceph master ... DONE')

        logger.info('Setup ceph')
        cmd = 'modprobe rbd'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info('Mounting volume docker_root')
        cmd = 'rbd --pool rbd map docker_root'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'mkfs.ext4 -F /dev/rbd0'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'mount /dev/rbd0 /tmp/docker_root'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info('Clear cache and Sleep 2 minutes after setup to ceph ....')
        cmd = '''sync && echo 3 > /proc/sys/vm/drop_caches'''
        self.error_hosts = execute_cmd(cmd, self.hosts)
        sleep(120)

        logger.info('SETTING CEPH FINISHED')

    def _setup_iperf3_host(self):
        logger.info('Setup iperf3 on all the hosts')
        # logger.info('Installing iperf3')
        cmd = '''echo "deb http://ftp.debian.org/debian sid main" >> /etc/apt/sources.list && ''' + \
            '''apt-get update -y --force-yes && apt-get install -y --force-yes -t sid libc6 libc6-dev libc6-dbg && ''' + \
            '''apt-get install -y --force-yes iperf3 && ''' + \
            '''sed -i "s/deb http:\/\/ftp.debian.org\/debian sid main/#deb http:\/\/ftp.debian.org\/debian sid main/g" /etc/apt/sources.list'''
        self.error_hosts = execute_cmd(cmd, self.hosts)

    # TODO: fix this function
    def get_disk_speed(self, vms, out_file_path='/tmp/data/'):
        """ """
        disk_speeds = {vm['ip']: [] for vm in vms}
        for index in range(5):
            logger.info('Run disk speed test #%s' % index)
            # cmd = 'dd if=/dev/urandom of=%smyfile bs=1M count=2048' % out_file_path
            cmd = 'dd if=/dev/zero of=%szero conv=fdatasync bs=120k count=30k' % out_file_path
            # retry Taktuk for k-times
            retries = self.options.number_of_retries
            while retries > 0:
                is_error = False
                error_vms, get_boottime = execute_cmd(cmd, [vm['ip'] for vm in vms], get_run_result=True)
                for p in get_boottime.processes:
                    if p.error or 'copied' not in p.stderr:
                        is_error = True
                        continue
                    speed, unit = p.stderr.strip().split(' s, ')[1].split(' ')
                    unit = unit.replace('\n', '')
                    if speed:
                        disk_speeds[p.host.address].append({'speed': speed, 'unit': unit})
                if is_error:
                    logger.info('Retrying [#%s] because there is error in Taktuk on disk speed test\n' %
                                (self.options.number_of_retries - retries + 1))
                    retries -= 1
                    sleep(10)
                else:
                    break
        return disk_speeds

    # TODO: fix this function
    def _get_hosts_disk_speed(self, hosts):
        # Sleep to make sure there are nothing running on the machines
        logger.info('Measuring disk speed on hosts: %s' % self.hosts)
        sleep(30)
        result = {}
        if self.settings['exp_env']['disk_type'] == 'ceph':
            out_file_path = '/tmp/docker_root'
        else:
            out_file_path = '/tmp/'
        hosts_speeds = self.get_disk_speed([{'ip': host} for host in hosts], out_file_path=out_file_path)
        if not hosts_speeds:
            return {}
        for host, host_disk_speeds in hosts_speeds.iteritems():
            # host_disk_speeds = self.get_disk_speed([{'ip': host}]).get(host, list())
            host_speed = None
            host_unit = None
            host_speeds = []
            host_units = []
            for index, each in enumerate(host_disk_speeds):
                logger.info('Speed #%s: %s (%s)' % (host, index, each['speed'], each['unit']))
                host_speeds.append(float(each['speed']))
                host_units.append(each['unit'].strip().lower())
            if len(host_speeds) > 0:
                host_speed = max(host_speeds)
                host_unit = set(host_units).pop()
                logger.info('Average speed: %s (%s); max-min speed: %s -> %s (%s)' %
                            (host, sum(host_speeds) * 1.0 / len(host_speeds), host_unit,
                                max(host_speeds), min(host_speeds), host_unit))
                result[host] = host_speed
            sleep(5)
        self.hosts_speed = result
        print self.hosts_speed
        return result

    def _setup_dockers(self):
        """Prepare docker images for e_docker and co_docker"""
        logger.info('Start docker engine')
        cmd = '''service docker start && gpasswd -a $USER docker && service docker restart'''
        self.error_hosts = execute_cmd(cmd, self.hosts)

        # Remove all existed dockers on host
        self.error_hosts = execute_cmd('''docker container rm $(docker ps -a -q)''', self.hosts)

        e_docker_image_name = self.settings['exp_env']['e_docker_image'].strip().split('/')[-1]
        co_docker_image_name = self.settings['exp_env']['co_docker_image'].strip().split('/')[-1]

        logger.info('Upload e_docker_image: %s' % e_docker_image_name)
        self.remote_executor.get_fileput(self.hosts, [self.settings['exp_env']['e_docker_image']], remote_location='/tmp/').run()

        logger.info('Upload co_docker_image: %s' % co_docker_image_name)
        self.remote_executor.get_fileput(self.hosts, [self.settings['exp_env']['co_docker_image']], remote_location='/tmp/').run()

        logger.info('Load e_docker_image: %s' % e_docker_image_name)
        self.error_hosts = execute_cmd('docker load -i /tmp/%s' % e_docker_image_name, self.hosts)

        logger.info('Load co_docker_image: %s' % co_docker_image_name)
        self.error_hosts = execute_cmd('docker load -i /tmp/%s' % co_docker_image_name, self.hosts)

        logger.info('Load images finished')

    def _setup_exp_env(self):
        """ """
        packages = 'iftop sysstat time build-essential parallel gawk nload git'
        logger.info('Installing system monitoring packages:\n%s' % packages)
        cmd = 'export DEBIAN_MASTER=noninteractive ; apt-get update && apt-get ' + \
            'install -y --force-yes --no-install-recommends ' + packages
        self.error_hosts = execute_cmd(cmd, self.hosts)

        if self.settings['exp_env']['disk_type'] == 'ssd':
            self._setup_ssd(self)

        # Creating folders to store docker root files
        cmd = 'mkdir -p /tmp/docker_root'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        if self.settings['exp_env']['disk_type'] == 'ceph':
            self._setup_ceph(self)

        # Create config file for docker to move docker root to /tmp/docker_root
        cmd = """printf '{\n    "graph": "/tmp/docker_root"\n}\n' > /etc/docker/daemon.json"""
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info('Restart dockerd to use new config file')
        cmd = """systemctl restart docker"""
        self.error_hosts = execute_cmd(cmd, self.hosts)
        sleep(5)

        if self.settings['exp_env']['network_iperf']:
            self._setup_iperf3_host(self.settings['exp_env']['network_iperf'])

        self._setup_dockers()

        if self.settings['exp_env']['get_host_diskspeed']:
            self._get_hosts_disk_speed(self.hosts)
        else:
            self.hosts_speed = {host: 0.0 for host in self.hosts}

    def _config_host(self):
        logger.info('Start configuring the following hosts:\n%s' % self.hosts)
        configurator = docker_debian_configuring(self.hosts)
        configurator.config_hosts()
        self.error_hosts = configurator.error_hosts

        self._setup_exp_env()
        logger.info("-----> FINISHED CONFIGURING HOSTS")

    # TODO: fix this function on lxc
    def setup_pgbench(self, containers, host):
        logger.info('Sleeping 30 s for starting postgres')
        sleep(30)
        for container in containers:
            logger.info('Init pgbench for container: %s' % container['id'])
            cmd = """lxc-attach -n %s -- su - postgres -c 'createdb benchdb'""" % container['id']
            execute_cmd(cmd, host)
            sleep(7)
            cmd = """lxc-attach -n %s -- su - postgres -c 'pgbench -i -s 30 benchdb'""" % container['id']
            execute_cmd(cmd, host)
            sleep(15)

    def stress_pgbench(self, co_containers, host):
        logger.info('Stress pgbench on %s' % co_containers)
        pgbench_cmd = """su - postgres -c 'pgbench benchdb -c 90 -j 2 -T 3600'"""
        cmd = '''truncate -s 0 stress.sh && ''' + \
            '''echo "%s" > stress.sh && nohup bash stress.sh &>/dev/null &''' % \
            ';'.join(['''(lxc-attach -n %s -- %s &)''' % (container['id'], pgbench_cmd)
                      for container in co_containers])
        # logger.info('Run command:\n%s' % cmd)
        execute_cmd(cmd, host, mode='start')
        logger.info('Sleep to wait for stress to reach its maximum')
        sleep(25)

    def stress_cpu(self, co_containers, host):
        """ """
        logger.info('Stress CPU on %s' % co_containers)
        cmd = ';'.join(['''
            (docker run --cpuset-cpus="0" --name %s stress_img /root/kflops &)
        ''' % container['id'] for container in co_containers])

        logger.info('Run command:\n%s' % cmd)
        execute_cmd(cmd, host, mode='start')
        logger.info('Sleep to wait for stress to reach its maximum')
        sleep(15)

    def stress_io(self, co_containers, host):
        """ """
        logger.info('Stress IO on %s' % co_containers)
        cmd = ';'.join(['''
            (docker run --cpuset-cpus="%s" -v /tmp/data_%s:/tmp --name %s stress_img /bin/bash -c "cd /tmp/ && sleep 12 && stress --hdd 6" &)
        ''' % (index + 1, index + 1, c['id']) for index, c in enumerate(co_containers)])

        logger.info('Run command:\n%s' % cmd)
        execute_cmd(cmd, host, mode='start')
        logger.info('Sleep to wait for stress to reach its maximum')
        sleep(15)

    def stress_mem(self, co_containers, host):
        """ """
        logger.info('Stress mem on %s' % co_containers)
        cmd = ';'.join(['''
            (docker run --cpuset-cpus="%s" --name %s stress_img /llcbench/cachebench/cachebench -m 1024 -e 1000 -x 2 -d 1 -b &)
        ''' % (index + 1, c['id']) for index, c in enumerate(co_containers)])

        logger.info('Run command:\n%s' % cmd)
        execute_cmd(cmd, host, mode='start')
        logger.info('Sleep to wait for stress to reach its maximum')
        sleep(15)

    def stress_network(self, co_containers, host):
        """ """
        self.network_ports = ['%s' % i for i in range(5000, 5000 + len(co_containers))]
        logger.info('Stress Network containers on %s' % co_containers)
        cmd = ';'.join(['''(docker run --cpuset-cpus="%s" --name %s stress_img iperf3 -c %s -t 3600 -P 1 -b 1G -R -p %s &)''' %
                        (index + 1, container['id'], self.options.ip, self.network_ports[index])
                        for index, container in enumerate(co_containers)])
        logger.info('Run command:\n%s' % cmd)
        execute_cmd(cmd, host, mode='start')
        logger.info('Sleep to wait for stress to reach its maximum')
        sleep(15)

    def limit_network_host(self, host, bandwidth):
        """Prepare a benchmark command with stress tool"""
        logger.info('Running Network Stress with bandwidth %s on the following host: %s' % (bandwidth, host))
        execute_cmd('''iperf3 -c %s -t 3600 -P 1 -b %sG -R''' % (self.options.ip, bandwidth), host, mode='start')

    # TODO: add retry
    def save_results(self, **kwargs):
        host = kwargs.get('host')
        comb = kwargs.get('comb')
        result = kwargs.get('result')
        host_speed = kwargs.get('host_speed')
        e_containers_index = kwargs.get('e_containers_index')

        logger.info('SAVING THE RESULTS')
        comb_dir = g5k_utils.create_combination_dir(comb, self.result_dir)
        logger.info('Saving the boot time result')
        with open(os.path.join(comb_dir, "boot_time.txt"), "w") as f:
            for c, duration in result.items():
                f.write('%s,%s\n' % (e_containers_index[c], duration))

        if self.settings['exp_env']['monitor']:
            logger.info('Saving the monitor results')
            self.remote_executor.get_fileget(host, ['/root/vmstat.txt'], comb_dir).run()
            self.remote_executor.get_fileget(host, ['/root/iostat.txt'], comb_dir).run()

        if self.settings['exp_env']['get_host_diskspeed']:
            logger.info('Saving host disk speed result')
            with open(comb_dir + "host_disk_speed.txt", "w") as f:
                f.write('%s' % host_speed)
        logger.info('Save all results successfully')
        return True

    def _wait_for_boot(self, container, host):
        count = 10
        while count > 0:
            logger.info('Checking container %s is started or not' % container)
            cmd = 'docker container ls | grep %s' % container
            _, run = execute_cmd(cmd, host, get_run_result=True)

            for p in run.processes:
                # logger.info('Check container %s is started, stdout: %s' % (container, p.stdout.strip().split('\n')))
                for line in p.stdout.strip().split('\n'):
                    # logger.info('Check container %s is started, line: %s' % (container, line.strip()))
                    if container in line.strip():
                        logger.info('All containers are booted')
                        return True
            count -= 1
            sleep(3)
        logger.info('Cannot boot containers ')
        return False

    def get_container_boottime(self, e_containers, host):
        """ Get container boot time of simultaneously boot """
        boot_duration = {container['id']: 0 for container in e_containers}

        # logger.info('remove commands.txt and cur_time.txt file')
        cmd = '''rm -rf /root/commands.txt /root/cur_time.txt'''
        execute_cmd(cmd, host)

        # logger.info('create commands.txt file')
        cmd = ';'.join(["echo 'docker run --cpuset-cpus=\"%s\" --name %s docker_img /usr/sbin/sshd -D & ' >> /root/commands.txt" %
                        (i, c['id']) for i, c in enumerate(e_containers)])
        execute_cmd(cmd, host)

        cmd = '''
            cat /proc/uptime | awk '{print $1}' > /root/cur_time.txt;
            parallel -k < /root/commands.txt;
        '''
        logger.info('Booting containers')
        # logger.info('Run boot command: %s' % cmd)
        error_host, run = execute_cmd(cmd, host, get_run_result=True)
        # sleep to wait for container boot, not check right away
        sleep(3)

        for c in e_containers:
            self._wait_for_boot(c['id'], host)

        createstr = ['{{.Created}}']
        startstr = ['{{.State.StartedAt}}']

        logger.info('Getting containers boot time')
        for c in e_containers:
            cmd = """docker inspect --format="{{ createstr }}" %s; docker inspect --format="{{ startstr }}" %s;""" % (
                c['id'], c['id'])
            # logger.info('Run get boot_time command: %s' % cmd)
            error_host, run = execute_cmd(cmd, host, get_run_result=True)

            sleep(2)
            for p in run.processes:
                # logger.info('RUN RESULT of %s - stdout: %s' % (c['id'], p.stdout.strip()))
                start, end = p.stdout.strip().split('\n')
                start = datetime.strptime(start.strip()[:-4], '%Y-%m-%dT%H:%M:%S.%f')
                end = datetime.strptime(end.strip()[:-4], '%Y-%m-%dT%H:%M:%S.%f')
                boot_duration[c['id']] = (end - start).total_seconds()
                break
        logger.info('Boot result: %s' % boot_duration)
        return boot_duration

    def _destroy_containers(self, comb, host):
        if comb['co_workload'] == 'io':
            logger.info('Kill IO stress processes')
            execute_cmd('''pkill -9 -f stress''', host)

        logger.info('Destroying all containers')
        execute_cmd('''docker stop $(docker ps -q)''', host)

        # TODO: fix 21- count
        count = 20
        while count > 0:
            logger.info('Destroying all containers ... try attempt #%s' % (21 - count))
            execute_cmd('''docker rm $(docker ps -a -q)''', host)
            error_host, run = execute_cmd('''docker ps -a -q | wc -l''', host, get_run_result=True)
            for p in run.processes:
                for line in p.stdout.strip():
                    try:
                        num = int(line)
                        if num <= 1:
                            count = 0
                            break
                    except Exception:
                        continue
            count -= 1
        logger.info('Destroy all containers .... DONE')
        # Sleep to ensure there is no IO operation on disk
        sleep(5)

        logger.info('Restart docker service')
        execute_cmd('''service docker restart''', host)
        logger.info('Restart docker service.... DONE')

    def cleanup_exp(self, **kwargs):
        logger.info('CLEANING EXPERIMENT ENVIRONMENT')
        host = kwargs.get('host')
        comb = kwargs.get('comb')

        if self.settings['exp_env']['monitor']:
            logger.info('Stop resource monitor')
            # logger.info('stop vmstat monitor: %s' % stat_cmd)
            stat_cmd = '''pkill -f vmstat'''
            execute_cmd(stat_cmd, host, mode='start')
            # logger.info('stop iostat monitor: %s' % stat_cmd)
            stat_cmd = '''pkill -f iostat'''
            execute_cmd(stat_cmd, host, mode='start')

        self._destroy_containers(comb, host)

    def workflow(self, comb, host):
        logger.info('Running combination: %s on %s' % (comb, host))

        # Check the number of containers against the number of cores of this host
        if comb['cpu_policy'] == 'one_by_core':
            if not comb['cpu_sharing']:
                if comb['n_dockers'] + comb['n_co_dockers'] > self.n_cores_hosts[host]:
                    logger.info("This combination has too many containers: "
                                "%s containers vs %s cores/node" % (
                                    comb['n_dockers'] + comb['n_co_dockers'],
                                    self.n_cores_hosts[host]
                                ))
                    self.sweeper.skip(comb)
                    logger.info('Combination: %s is marked as skipped' % comb)
                    # update list of available hosts
                    self.lock.acquire()
                    self.available_hosts.append(host)
                    self.lock.release()
                    return False
                    # TODO: add this combination in to a list and announce to clients

        try:
            # containers variable has ids of all e-docker and co-docker containers
            e_containers = [{'id': 'e-c-%s' % _} for _ in range(comb['n_dockers'])]
            co_containers = [{'id': 'co-c-%s' % _} for _ in range(comb['n_co_dockers'])]
            # get container index for outputing ordered result
            e_containers_index = {container['id']: str(index) for index, container in enumerate(e_containers)}

            # run co-workloads
            if len(co_containers) > 0:
                if comb['co_workload'] == 'cpu':
                    self.stress_cpu(co_containers, host)
                elif comb['co_workload'] == 'io':
                    self.stress_io(co_containers, host)
                elif comb['co_workload'] == 'mem':
                    self.stress_mem(co_containers, host)
                elif comb['co_workload'] == 'network':
                    self.stress_network(co_containers, host)
                elif comb['co_workload'] == 'pgbench':
                    self.setup_pgbench(co_containers, host)
                    self.stress_pgbench(co_containers, host)

            if comb.get('network_iperf', None):
                logger.info('[%s] Trigger network injector on %s with bandwidth %s' %
                            (slugify(comb), host, comb['bandwidths']))
                logger.info('Run network stress on HOST up to %sG bandwidths' % self.settings['exp_env']['bandwidth'])
                self.limit_network_host(host, self.settings['exp_env']['bandwidth'])
                logger.info('Sleep 15 seconds to wait for stress network to reach its maximum')
                sleep(15)

            # Clear cache on host
            if comb['co_workload'] != 'io':
                logger.info('clear cache on host %s before booting containers' % host)
                cmd = '''free && sync && echo 3 > /proc/sys/vm/drop_caches && free'''
                execute_cmd(cmd, host)

            # Start monitoring: vmstat & iostat
            if self.settings['exp_env']['monitor']:
                logger.info('Run Resource Monitor')
                stat_cmd = '''vmstat 1 | perl -e \'$| = 1; while (<>) { print localtime() . ": $_"; }\' > vmstat.txt &'''
                # logger.info('Run vmstat monitor: %s' % stat_cmd)
                execute_cmd(stat_cmd, host, mode='start')

                if self.settings['exp_env']['disk_type'] == 'hdd':
                    stat_cmd = '''iostat -xdt sda5 1 > iostat.txt &'''
                elif self.settings['exp_env']['disk_type'] == 'ssd':
                    stat_cmd = '''iostat -xdt sdf1 1 > iostat.txt &'''
                else:
                    stat_cmd = '''iostat 1 > iostat.txt &'''
                execute_cmd(stat_cmd, host, mode='start')
                sleep(2)

            boot_duration = self.get_container_boottime(e_containers, host)

            # Cleanup
            self.cleanup_exp(host=host, comb=comb)

            # TODO: add retry
            # if not self.save_results(host=host, comb=comb, dockers=e_containers,
            #                          dockers_index=e_containers_index, boot_duration=boot_duration,
            #                          dd=speed, host_speed=self.hosts_speed.get(host)):
            if not self.save_results(host=host, comb=comb, result=boot_duration,
                                     e_containers_index=e_containers_index):
                raise Exception('Cannot save result for this run.')

            # update the state of this combination
            self.sweeper.done(comb)
            logger.info('%s  has been done' % slugify(comb))
            logger.info('-----> %s combinations remaining', len(self.sweeper.get_remaining()))
        except Exception as e:
            logger.error('Exception: %s' % e, exc_info=True)
            self.sweeper.cancel(comb)
            logger.warning(slugify(comb) + ' has been canceled')
        finally:
            # update list of available hosts
            self.lock.acquire()
            self.available_hosts.append(host)
            self.lock.release()

    def _get_available_host(self):
        logger.info('Getting one available host to run a combination')
        while True:
            if len(self.available_hosts) > 0:
                self.lock.acquire()
                host = self.available_hosts.pop()
                self.lock.release()
                return host
            # logger.info('All host are busy. Waiting one thread to finish to get host from it')
            sleep(5)

    def is_job_alive(self):
        """Check whether a list of job_id is still valid or alive on Grid5000

        The function checks for the existing of the reservation job_ids, and whether
        the machines in these job_ids are up and running.

        It examines the validity of each job_id in the `oar_result`.
        `oar_result` is a list of tuple which has the following structure:
            [(oar_job_id1, site_name1), (oar_job_id2, site_name2), ...]

        Returns
        -------
        bool
            True if the job_ids are existed and at least one job_id is valid
            (this is because of this specific experiment scenario);
            False otherwise

        """
        # TODO: use retry library to retry if fail to get the state
        # this to ensure in case the provisioning step is never called
        logger.info("Checking reserved nodes alive")
        if not hasattr(self, 'oar_result'):
            logger.info("There is no oar_result information.")
            return False

        logger.info('checking validity of job_ids: %s' % self.oar_result)
        # check validity of job_ids
        for oar_job_id, site_name in self.oar_result:
            oar_job_info = dict()
            while 'state' not in oar_job_info:
                # TODO: retrying
                oar_job_info = get_oar_job_info(oar_job_id, site_name)
            if oar_job_info['state'] != 'Error':
                logger.info("At least one job_id is alive")
                return True
        logger.info("All nodes are dead")
        return False

    def _perform_experiments(self):
        logger.info('START RUNNING A COMBINATION:')
        host = self._get_available_host()
        host_name = host.split('.')[0]
        comb = self.sweeper.get_next()
        t = Thread(target=self.workflow, args=(comb, host), name='thread-%s' % host_name)
        t.daemon = True
        t.start()

    def run(self):
        # parse the parameters from the experiment setting file
        self.settings = parse_config_file(self.args.exp_setting_file_path)
        # create all combinations for the experiment from the parameters
        self.define_parameters()
        self.sweeper = g5k_utils.create_paramsweeper(self.parameters, self.result_dir)
        self.available_hosts = list()
        self.n_cores_hosts = dict()
        while len(self.sweeper.get_remaining()) > 0:
            # check if the reserved nodes are still running
            if not self.is_job_alive():
                self._provisioning()

                self.lock.acquire()
                self.available_hosts = self.hosts
                self.lock.release()

                self.n_cores_hosts = g5k_utils.get_cores_hosts(self.hosts)
                logger.info('available hosts: %s' % self.available_hosts)
                self._config_host()
            self._perform_experiments()

        # waiting for all threads to finish
        for thread in threading.enumerate():
            # do not join Main Thread
            if 'thread-' in thread.name:
                thread.join()
        logger.info("EXPERIMENT FINISHED")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = DockerBootTime_Measurement()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
    except KeyboardInterrupt:
        logger.error('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
