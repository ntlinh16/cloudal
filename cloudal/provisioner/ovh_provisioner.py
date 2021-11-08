from time import sleep
import ovh

from cloudal.provisioner.provisioning import cloud_provisioning
from cloudal.utils import get_logger

logger = get_logger()


class ovh_provisioner(cloud_provisioning):
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
            super(ovh_provisioner, self).__init__(config_file_path=self.config_file_path)

    def _get_ovh_driver(self):
        logger.info("Creating a Driver to connect to OVH")
        driver = ovh.Client(
                endpoint=self.configs['endpoint'],
                application_key=self.configs['application_key'],
                application_secret=self.configs['application_secret'],
                consumer_key=self.configs['consumer_key'],
            )
        return driver

    def _get_existed_nodes(self, driver):
        list_regions = list()
        for cluster in self.configs['clusters']:
            list_regions.append(cluster['region'])
        existed_nodes = dict()
        for region in list_regions:
            existed_nodes[region] = list()
        
        for region in list_regions:
            nodes = driver.get('/cloud/project/%s/instance' % self.configs['project_id'], region='%s' % region)
            for node in nodes:
                existed_nodes[region].append(node['name'])
        return existed_nodes


    def _get_flavor_id(self, driver, region, instance_type):
        flavors = driver.get('/cloud/project/%s/flavor' % self.configs['project_id'], region='%s' % region)
        for flavor in flavors:
            if flavor['name'] == instance_type:
                return flavor['id']
        return None


    def _get_image_id(self, driver, region, image_name):
        images = driver.get('/cloud/project/%s/image' % self.configs['project_id'], region='%s' % region)
        for image in images:
            if image['name'] == '%s' % image_name:
                return image['id']
        return None

    def make_reservation(self):
        driver = self._get_ovh_driver()
        
        existed_nodes = self._get_existed_nodes(driver)
        project_id = self.configs['project_id']

        logger.info("Starting provisioning nodes on ovh")
        for cluster in self.configs['clusters']:
            if cluster.get('node_name') is None:
                cluster['node_name'] = 'node'
            
            n_nodes = cluster['n_nodes']
            logger.debug('n_nodes = %s' % n_nodes)

            region = cluster['region']
            logger.debug('region = %s' % region)

            if cluster['flexible_instance'] is True:
                instance_type = '%s-flex' % cluster['instance_type']
            else:
                instance_type = cluster['instance_type']
            logger.debug('instance_type = %s' % instance_type)

            flavor_id = self._get_flavor_id(driver, region, instance_type)
            logger.debug('flavor_id = %s' % flavor_id)

            image_id = self._get_image_id(driver, region, cluster['image'])
            logger.debug('image_id = %s' % image_id)

            sshKey_id = driver.get('/cloud/project/%s/sshkey' % project_id, region='%s' % region)[0]['id']
            logger.debug('sshKey_id = %s' % sshKey_id)

            #post_installation script on nodes: edit ssh setting to enable login as root user
            post_install_script = '''#!/bin/bash

                                    sudo sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/g' /etc/ssh/sshd_config &&
                                    sudo service ssh restart && 
                                    sudo sed -i 's/^.*ssh-rsa/ssh-rsa/' /root/.ssh/authorized_keys '''

            logger.info("Deploying %s nodes on %s" % (n_nodes,region))
            if n_nodes > 1:
                uri = '/cloud/project/%s/instance/bulk' % project_id
            else:
                uri = '/cloud/project/%s/instance' % project_id
            try:
                nodes = driver.post('%s' % uri, 
                            flavorId=flavor_id, 
                            imageId=image_id, 
                            sshKeyId=sshKey_id,
                            monthlyBilling=False, 
                            name=cluster['node_name'], 
                            region=region,
                            number=n_nodes,
                            userData=post_install_script
                        )
                logger.debug('uri = %s' % uri)
                
                if not isinstance(nodes, list):
                    nodes = [nodes]
                logger.debug('nodes = %s' % nodes)
                for each in nodes:
                    self.nodes.append(each['id'])
            except ovh.APIError as e:
                print('ERROR: ')
                print(e)
        logger.info('nodes = %s' % self.nodes)
        return driver

    def _wait_hosts_up(self, driver):
        logger.info('Waiting for all hosts are up')
        nodes_up = list()
        sleep(60)
        for node in self.nodes:
            node = driver.get('/cloud/project/%s/instance/%s' % (self.configs['project_id'], node))
            if node['status'] == 'ACTIVE':
                nodes_up.append(node)
        if len(nodes_up) == len(self.nodes):
            logger.info('All reserved hosts are up')
            self.nodes = nodes_up
        else:
            hosts_ko = [node.name for node in self.nodes if node not in nodes_up]
            logger.info('The following hosts are not up: %s' % hosts_ko)
    
    def get_resources(self):
        """Retriving the public IPs of the list of provisioned hosts
        """
        logger.info("Retriving the public IPs of all nodes on ovh")
        for node in self.nodes:
            self.hosts.append(node['ipAddresses'][0]['ip'])
        logger.info('hosts = %s' % self.hosts)
        logger.info("Finish retriving the public IPs\n")
    
    def provisioning(self):
        driver = self.make_reservation()
        self._wait_hosts_up(driver)
        self.get_resources()
