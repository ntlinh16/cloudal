import sys
import time
import datetime

from humanfriendly.terminal import message

from cloudal.provisioner.provisioning import cloud_provisioning
from cloudal.utils import get_remote_executor, get_logger, parse_config_file

from execo import format_date, Host
# from execo.config import default_connection_params
from execo.time_utils import timedelta_to_seconds, get_unixts
from execo_g5k import (
    oarsub, wait_oar_job_start, get_oar_job_nodes, get_oar_job_subnets, get_oar_job_kavlan,
    deploy, Deployment
)
from execo_g5k.planning import get_planning, compute_slots, get_jobs_specs
from execo_g5k.utils import hosts_list
from execo_g5k.api_utils import canonical_host_name
from execo_g5k.oar import get_oar_job_info, oardel


logger = get_logger()

# default_connection_params['user'] = 'root'

MAX_RETRY_DEPLOY = 10


class g5k_provisioner(cloud_provisioning):
    """docstring for grid5k"""

    def __init__(self, job_name="cloudal", **kwargs):
        self.keep_alive = kwargs.get('keep_alive')
        self.out_of_chart = kwargs.get('out_of_chart')
        self.oar_job_ids = kwargs.get('oar_job_ids')
        self.config_file_path = kwargs.get('config_file_path')
        self.configs = kwargs.get('configs')
        self.is_reservation = kwargs.get('is_reservation')
        self.no_deploy_os = kwargs.get('no_deploy_os')
        self.job_name = job_name

        self.max_deploy = MAX_RETRY_DEPLOY

        """self.oar_result containts the list of tuples (oar_job_id, site_name)
        that identifies the reservation on each site,
        which can be retrieved from the command line arguments or from make_reservation()
        """
        self.oar_result = list()
        """
        TODO:
            + write function to check all nodes in a job is alive
            + modify make_reservation function to accept error_hosts
              -> make replacement reservation or cancel program or ignore
        """
        if self.oar_job_ids is not None:
            logger.info('Checking the given oar_job_id is valid or not')
            for each in self.oar_job_ids.split(','):
                site_name, oar_job_id = each.split(':')
                oar_job_id = int(oar_job_id)
                # check validity of oar_job_id
                job_info = get_oar_job_info(oar_job_id=oar_job_id, frontend=site_name)
                if job_info is None or len(job_info) == 0:
                    logger.error("Job id: %s in %s is not a valid Grid5000 oar_job_id" % (oar_job_id, site_name))
                    logger.error("Please rerun the script with a correct oar_job_id")
                    exit()
                self.oar_result.append((int(oar_job_id), str(site_name)))
            if self.config_file_path and not self.configs:
                self.configs = parse_config_file(self.config_file_path)
            return
        elif self.configs and isinstance(self.configs, dict):
            logger.debug("Use configs instead of config file")
        elif self.config_file_path is None:
            logger.error(
                "Please provide at least a provisioning config file or oar_job_id.")
            exit()
        else:
            super(g5k_provisioner, self).__init__(config_file_path=self.config_file_path)
        # parse clusters into correct format to be used in g5k
        self.clusters = {each['cluster']: each['n_nodes']
                         for each in self.configs['clusters']}

    def _get_nodes(self, starttime, endtime):
        """ return the nearest slot (startdate) that has enough available nodes
        to perform the client's actions

        Parameters
        ----------
        starttime: str
            the time to start the reservation

        endtime: str
            the time to stop the reservation

        Returns
        -------
        str
        the start time of the reservation
        """

        planning = get_planning(elements=self.clusters.keys(),
                                starttime=starttime,
                                endtime=endtime,
                                out_of_chart=self.out_of_chart)
        slots = compute_slots(planning, self.configs['walltime'])
        startdate = None
        for slot in slots:
            is_enough_nodes = True
            for cluster_name, n_nodes in self.clusters.items():
                if slot[2][cluster_name] < n_nodes:
                    is_enough_nodes = False
                    break
            if is_enough_nodes:
                startdate = slot[0]
                break
        if startdate is not None:
            logger.info('A slot is found for your request at %s' % format_date(startdate))

        return startdate

    def make_reservation(self):
        """Perform a reservation of the required number of nodes.

        Parameters
        ----------

        Returns
        -------

        """
        if self.oar_result:
            message = "Validated OAR_JOB_ID:"
            for job_id, site in self.oar_result:
                message += "\n%s: %s" % (site, job_id)
            logger.info(message)
            message = "The list of hosts:"
            for job_id, site in self.oar_result:
                hosts = get_oar_job_nodes(oar_job_id=job_id, frontend=site)
                message += "\n--- %s: %s nodes ---" % (site, len(hosts))
                for host in hosts:
                    message += "\n%s" % (host.address)
            logger.info(message)
            return

        if self.configs['walltime'] <= 99*3600+99*60+99:
            walltime = time.strftime('%H:%M:%S', time.gmtime(self.configs['walltime']))
        else:
            walltime = '%s seconds' % self.configs['walltime']
        message = 'You are requesting %s nodes for %s:' % (sum(self.clusters.values()), walltime)

        for cluster, n_nodes in self.clusters.items():
            message += "\n%s: %s nodes" % (cluster, n_nodes)
        logger.info(message)

        logger.info('Performing reservation .......')
        if 'starttime' not in self.configs or self.configs['starttime'] is None:
            self.configs['starttime'] = int(time.time() + timedelta_to_seconds(datetime.timedelta(minutes=1)))

        starttime = int(get_unixts(self.configs['starttime']))
        endtime = int(
            starttime + timedelta_to_seconds(datetime.timedelta(days=3, minutes=1)))
        startdate = self._get_nodes(starttime, endtime)

        while startdate is None:
            logger.info('No enough nodes found between %s and %s, ' +
                        '\nIncreasing the window time....', format_date(starttime), format_date(endtime))
            starttime = endtime
            endtime = int(
                starttime + timedelta_to_seconds(datetime.timedelta(days=3, minutes=1)))

            startdate = self._get_nodes(starttime, endtime)
            if starttime > int(self.configs['starttime'] + timedelta_to_seconds(datetime.timedelta(weeks=6))):
                logger.error(
                    'What a pity! There is no slot which satisfies your request until %s :(' % format_date(endtime))
                exit()

        jobs_specs = get_jobs_specs(self.clusters, name=self.job_name)
        for job_spec, site_name in jobs_specs:
            tmp = str(job_spec.resources).replace('\\', '')
            job_spec.resources = 'slash_22=4+' + tmp.replace('"', '')
            job_spec.walltime = self.configs['walltime']
            # -t deploy to reserve node without deploying OS
            job_spec.additional_options = '-t deploy'
            job_spec.reservation_date = startdate + 10

        self.oar_result = oarsub(jobs_specs)

        for oar_job_id, _ in self.oar_result:
            if oar_job_id is None:
                logger.info('Performing reservation FAILED')
                exit()

        message = "Reserved nodes successfully!!! \nOAR JOB ID:"
        for each in self.oar_result:
            message += "\n%s: %s" % (each[1], each[0])
        logger.info(message)

    def get_resources(self):
        """Retrieve the hosts address list and (ip, mac) list from a list of oar_result and
        return the resources which is a dict needed by g5k_provisioner
        """
        logger.info("Getting resources specs")
        self.resources = dict()
        self.hosts = list()

        for oar_job_id, site in self.oar_result:
            logger.info('Waiting for the reserved nodes on %s to be up' % site)
            if not wait_oar_job_start(oar_job_id, site):
                logger.error('The reserved resources cannot be used.\nThe program is terminated.')
                exit()

        for oar_job_id, site in self.oar_result:
            logger.info('Retrieving resource information on %s' % site)
            logger.debug('Retrieving hosts')
            hosts = [host.address for host in get_oar_job_nodes(
                oar_job_id, site)]

            logger.debug('Retrieving subnet')
            ip_mac, _ = get_oar_job_subnets(oar_job_id, site)
            kavlan = None
            if len(ip_mac) == 0:
                logger.debug('Retrieving kavlan')
                kavlan = get_oar_job_kavlan(oar_job_id, site)
                if kavlan:
                    ip_mac = self.get_kavlan_ip_mac(kavlan, site)
            self.resources[site] = {'hosts': hosts,
                                    'ip_mac': ip_mac,
                                    'kavlan': kavlan}

        for site, resource in self.resources.items():
            self.hosts += resource['hosts']

    def _launch_kadeploy(self, max_tries=10, check_deploy=True):
        """Create an execo_g5k.Deployment object, launch the deployment and
        return a tuple (deployed_hosts, undeployed_hosts)
        """

        # if the provisioner has oar_job_ids and no config_file_path
        # then the configs variable is not created
        if not hasattr(self, 'configs'):
            logger.info('The list of %s hosts: \n%s', len(
                self.hosts), hosts_list(self.hosts, separator='\n'))
            return

        logger.info('Deploying %s hosts \n%s', len(self.hosts),
                    hosts_list(self.hosts, separator='\n'))
        try:
            deployment = Deployment(hosts=[Host(canonical_host_name(host))
                                           for host in self.hosts],
                                    env_file=self.configs['custom_image'],
                                    env_name=self.configs['cloud_provider_image'])
        except ValueError:
            logger.error(
                "Please put in the config file either custom_image or cloud_provider_image.")
            exit()
        # user=self.env_user,
        # vlan=self.kavlan)

        # Activate kadeploy output log if log level is debug
        if logger.getEffectiveLevel() <= 10:
            stdout = [sys.stdout]
            stderr = [sys.stderr]
        else:
            stdout = None
            stderr = None

        # deploy() function will iterate through each frontend to run kadeploy
        # so that the deployment hosts will be performed sequentially site after site
        deployed_hosts, undeployed_hosts = deploy(deployment,
                                                  stdout_handlers=stdout,
                                                  stderr_handlers=stderr,
                                                  num_tries=max_tries,
                                                  check_deployed_command=check_deploy)
        deployed_hosts = list(deployed_hosts)
        undeployed_hosts = list(undeployed_hosts)
        # # Renaming hosts if a kavlan is used
        # if self.kavlan:
        #     for i, host in enumerate(deployed_hosts):
        #         deployed_hosts[i] = get_kavlan_host_name(host, self.kavlan)
        #     for i, host in enumerate(undeployed_hosts):
        #         undeployed_hosts[i] = get_kavlan_host_name(host, self.kavlan)
        logger.info('Deployed %s hosts successfully', len(deployed_hosts))
        cr = '\n' if len(undeployed_hosts) > 0 else ''
        logger.info('Failed %s hosts %s%s', len(undeployed_hosts), cr, hosts_list(undeployed_hosts))

        return deployed_hosts, undeployed_hosts

    def _configure_ssh(self):
        self.remote_executor = get_remote_executor()
        if self.remote_executor.remote_tool == 2:
            # Configuring SSH with precopy of id_rsa and id_rsa.pub keys on all
            # host to allow TakTuk connection
            taktuk_conf = ('-s', '-S',
                           '$HOME/.ssh/id_rsa:$HOME/.ssh/id_rsa,' +
                           '$HOME/.ssh/id_rsa.pub:$HOME/.ssh')
        else:
            taktuk_conf = ('-s', )
        conf_ssh = self.remote_executor.get_remote('echo "Host *" >> /root/.ssh/config ;' +
                                                   'echo " StrictHostKeyChecking no" >> /root/.ssh/config; ',
                                                   self.hosts,
                                                   connection_params={'taktuk_options': taktuk_conf}).run()

    def provisioning(self):
        """Provision nodes on Grid5000 based on client's requirements
        """
        self.make_reservation()

        # skip waiting for resources to be up in case of making reservations for the future
        if not self.is_reservation:
            self.get_resources()
        else:
            exit()

        if not self.no_deploy_os:
            n_nodes = sum([len(resource['hosts']) for site, resource in self.resources.items()])
            logger.info('Starting setup on %s hosts' % n_nodes)
            deployed_hosts, undeployed_hosts = self._launch_kadeploy()
            # self._configure_ssh()

            # Retry provisioning again if all reserved hosts are not deployed successfully
            if len(undeployed_hosts) > 0:
                if self.max_deploy > 0:
                    self.max_deploy -= 1
                    if self.oar_job_ids is None:
                        logger.info('Deleting the current reservation')
                        oardel(self.oar_result)
                        time.sleep(60)
                        self.oar_result = list()
                    logger.info('---> Retrying provisioning nodes: attempt #%s' % (MAX_RETRY_DEPLOY - self.max_deploy))
                    self.provisioning()
                else:
                    raise Exception('Failed to deploy all reserved nodes. Terminate the program.')
        logger.info("Finish provisioning nodes\n")
