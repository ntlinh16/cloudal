import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

from cloudal.provisioning.provisioning import cloud_provisioning
from cloudal.utils import parse_config_file, get_logger

logger = get_logger()


class gcp_provisioner(cloud_provisioning):
    """This is a base class of cloudal engine,
        and it can be used to deploy servers on different cloud systems."""

    def __init__(self, config_file_path):
        """Add options for the number of measures, number of nodes,
        env_file or env_name and clusters and initialize the engine
        """
        self.configs = parse_config_file(config_file_path)
        self.nodes = list()

    def _get_gce_driver(self):
        logger.info("Creating a Driver to connect to GCP")

        # GCE authentication related info
        SERVICE_ACCOUNT_USERNAME = self.configs['service_account_username']
        SERVICE_ACCOUNT_CREDENTIALS_JSON_FILE_PATH = os.path.expanduser(self.configs['service_account_credentials_json_file_path'])
        PROJECT_ID = self.configs['project_id']

        Driver = get_driver(Provider.GCE)
        driver = Driver(SERVICE_ACCOUNT_USERNAME,
                        SERVICE_ACCOUNT_CREDENTIALS_JSON_FILE_PATH,
                        project=PROJECT_ID)
        return driver

    def make_reservation(self):
        driver = self._get_gce_driver()

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

        logger.info("Deploying the nodes on GCP")
        index = 0
        for cluster in self.configs['clusters']:
            n_nodes = cluster['n_nodes']
            for i in range(n_nodes):
                machine_name = 'node-%s' % index
                instance_type = cluster['instance_type']
                datacenter = cluster['cluster']
                if cluster['image'] is not None:
                    current_image = cluster['image']
                else:
                    current_image = image

                if cluster['instance_type'] is not None:
                    current_instance_type = cluster['instance_type']
                else:
                    current_instance_type = instance_type

                logger.info("Deploying %s on %s ....." % (machine_name, datacenter))
                logger.info('Using image: %s' % (current_image.name))
                logger.info('Using instance type: %s' % (current_instance_type))

                node = driver.create_node(name=machine_name,
                                          image=current_image,
                                          size=current_instance_type,
                                          ex_metadata=metadata,
                                          location=datacenter)
                self.nodes.append(node)
                index += 1
        logger.info("Deploying the nodes on GCP: DONE")

    def get_resources(self):
        """Retriving the information of  the list of reserved hosts
        """
        self.hosts = list()
        for node in self.nodes:
            if len(node.public_ips) > 0:
                self.hosts.append(node.public_ips[0])
        logger.info(self.hosts)
