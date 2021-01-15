from logging import info
import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

from cloudal.provisioner.provisioning import cloud_provisioning
from cloudal.utils import get_logger

logger = get_logger()


class gcp_provisioner(cloud_provisioning):
    def __init__(self, **kwargs):
        self.config_file_path = kwargs.get('config_file_path')
        self.configs = kwargs.get('configs')
        self.nodes = list()
        self.hosts = list()

        if self.configs and isinstance(self.configs, dict):
            logger.debug("Use configs instead of config file")
        elif self.config_file_path is None:
            logger.error("Please provide at least a provisioning config file or a custom configs.")
            exit()
        else:
            super(gcp_provisioner, self).__init__(config_file_path=self.config_file_path)

    def _get_gce_driver(self):
        logger.info("Creating a Driver to connect to GCP")

        # GCE authentication related info
        SERVICE_ACCOUNT_USERNAME = self.configs['service_account_username']
        SERVICE_ACCOUNT_CREDENTIALS_JSON_FILE_PATH = os.path.expanduser(
            self.configs['service_account_credentials_json_file_path'])
        PROJECT_ID = self.configs['project_id']

        Driver = get_driver(Provider.GCE)
        driver = Driver(SERVICE_ACCOUNT_USERNAME,
                        SERVICE_ACCOUNT_CREDENTIALS_JSON_FILE_PATH,
                        project=PROJECT_ID)
        return driver

    def _get_existed_nodes(self, driver, list_zones):
        existed_nodes = dict()
        for zone in list_zones:
            existed_nodes[zone] = dict()

        for zone in list_zones:
            nodes = driver.list_nodes(ex_zone=zone)
            for node in nodes:
                existed_nodes[zone][node.name] = node
        return existed_nodes

    def _wait_hosts_up(self, driver):
        logger.info('Waiting for all hosts are up')
        nodes_up = list()
        r = driver.wait_until_running(self.nodes)
        for each in r:
            nodes_up.append(each[0])
        if len(nodes_up) == len(self.nodes):
            logger.info('All reserved hosts are up')
            self.nodes = nodes_up
        else:
            hosts_ko = [node.name for node in self.nodes if node not in nodes_up]
            logger.info('The following hosts are not up: %s' % hosts_ko)

    def make_reservation(self):
        driver = self._get_gce_driver()

        list_zones = list()
        for cluster in self.configs['clusters']:
            list_zones.append(cluster['zone'])
        existed_nodes = self._get_existed_nodes(driver, list_zones)

        images = driver.list_images()
        sizes = driver.list_sizes()
        if self.configs['cloud_provider_image'] is not None:
            image = [i for i in images if i.name == self.configs['cloud_provider_image']][0]
        if self.configs['instance_type'] is not None:
            instance_type = [s for s in sizes if s.name == self.configs['instance_type']][0]

        PUBLIC_SSH_KEY_PATH = os.path.expanduser(self.configs['public_ssh_key_path'])

        with open(PUBLIC_SSH_KEY_PATH, 'r') as fp:
            PUBLIC_SSH_KEY_CONTENT = fp.read().strip()

        metadata = {
            'items': [
                {
                    'key': 'ssh-keys',
                    'value': 'root: %s' % (PUBLIC_SSH_KEY_CONTENT)
                }
            ]
        }

        logger.info("Starting provisioning nodes on GCP")
        index = 0
        for cluster in self.configs['clusters']:
            if cluster.get('node_name') is None:
                cluster['node_name'] = 'node'
            n_nodes = cluster['n_nodes']
            instance_type = cluster['instance_type']
            zone = cluster['zone']

            if cluster['image'] is not None:
                current_image = cluster['image']
            else:
                current_image = image

            if cluster['instance_type'] is not None:
                current_instance_type = cluster['instance_type']
            else:
                current_instance_type = instance_type

            logger.info("Deploying on %s" % zone)

            for index in range(n_nodes):
                node_name = '%s-%s' % (cluster['node_name'], index)
                if node_name in existed_nodes[zone]:
                    self.nodes.append(existed_nodes[zone][node_name])
                    if existed_nodes[zone][node_name].state == 'running':
                        logger.info('%s on zone %s already existed and is running' % (node_name, zone))
                        continue
                    else:
                        logger.info('%s on zone %s already existed and is not running' % (node_name, zone))
                        continue

                logger.info('Deploying %s with %s instance type, using %s image' %
                            (node_name, current_instance_type, current_image.name))

                node = driver.create_node(name=node_name,
                                          image=current_image,
                                          size=current_instance_type,
                                          ex_metadata=metadata,
                                          location=zone)
                self.nodes.append(node)
                index += 1
        logger.info("Finish provisioning nodes on GCP\n")

        return driver

    def get_resources(self):
        """Retriving the public IPs of the list of provisioned hosts
        """
        logger.info("Retriving the public IPs of all nodes on GCP")
        for node in self.nodes:
            if len(node.public_ips) > 0:
                self.hosts.append(node.public_ips[0])
        logger.info("Finish retriving the public IPs\n")

    def provisioning(self):
        driver = self.make_reservation()
        self._wait_hosts_up(driver)
        self.get_resources()
