from cloudal.provisioner.provisioning import cloud_provisioning
from cloudal.utils import get_logger

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from libcloud.compute.base import NodeAuthSSHKey

logger = get_logger()


class azure_provisioner(cloud_provisioning):

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
            super(azure_provisioner, self).__init__(config_file_path=self.config_file_path)

    def _get_azure_driver(self):
        logger.info("Creating a Driver to connect to Azure")

        tenant_id = self.configs['tenant_ID']
        subscription_id = self.configs['subscription_ID']
        application_id = self.configs['application_ID']
        secret = self.configs['client_secret_key']

        cls = get_driver(Provider.AZURE_ARM)
        driver = cls(tenant_id=tenant_id,
                     subscription_id=subscription_id,
                     key=application_id,
                     secret=secret)
        return driver

    def make_reservation(self):
        logger.info("Starting provisioning nodes on Azure")
        driver = self._get_azure_driver()

        with open(self.configs['public_ssh_key_path'], 'r') as fp:
            auth = NodeAuthSSHKey(fp.read().strip())

        for cluster in self.configs['clusters']:
            logger.info("Starting provisioning %s nodes on %s" % (n_nodes, location_str))

            n_nodes = cluster['n_nodes']

            # Get location
            location_str = cluster['location']
            locations = driver.list_locations()
            location = [location for location in locations if location.id == location_str]
            if len(location) > 0:
                location = location[0]
            else:
                raise Exception('Wrong location provided')

            # Get instance_type
            if cluster['instance_type'] is not None:
                instance_type = cluster['instance_type']
            else:
                instance_type = self.configs['instance_type']
            sizes = driver.list_sizes(location=location)
            instance_type = [size for size in sizes if size.id == instance_type]
            if len(instance_type) > 0:
                instance_type = instance_type[0]
            else:
                raise Exception('Wrong instance_type provided')

            # Get image
            if cluster['image'] is not None:
                image_id = cluster['image']
            else:
                image_id = self.configs['cloud_provider_image']
            image = driver.get_image(image_id, location=location)

            # Get resource information
            for resource in self.configs['region_resources']:
                if resource['location'] == cluster['location']:
                    resource_group = resource['resource_group']
                    network = resource['network']
                    storage_account = resource['storage_account']

            if cluster.get('node_name') is None:
                cluster['node_name'] = 'node'

            for index in range(n_nodes):
                node_name = '%s-%s' % (cluster['node_name'], index)

                node = driver.create_node(name=node_name,
                                          auth=auth,
                                          size=instance_type,
                                          image=image,
                                          location=location,
                                          ex_resource_group=resource_group,
                                          ex_network=network,
                                          ex_storage_account=storage_account,
                                          ex_use_managed_disks=True)
                self.nodes.append(node)
                index += 1
        logger.info("Finish provisioning nodes on Azure\n")

    def provisioning(self):
        self.make_reservation()
