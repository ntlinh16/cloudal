import base64
import hashlib
import time
import os
from pathlib import Path
from time import sleep

import ovh

from cloudal.provisioner.provisioning import cloud_provisioning
from cloudal.utils import get_logger

logger = get_logger()


class ovh_provisioner(cloud_provisioning):
    def __init__(self, **kwargs):
        self.config_file_path = kwargs.get('config_file_path')
        self.configs = kwargs.get('configs')
        self.node_ids_file = kwargs.get('node_ids_file')
        self.nodes = list()
        self.hosts = list()

        if self.configs and isinstance(self.configs, dict):
            logger.debug("Use configs instead of config file")
        elif self.config_file_path is None:
            logger.error("Please provide at least a provisioning config file or a custom configs.")
            exit()
        else:
            super(ovh_provisioner, self).__init__(config_file_path=self.config_file_path)

        if self.node_ids_file:
            if not Path(self.node_ids_file).is_file():
                logger.info(
                    'The path to the node IDs file is not valid. Please provide the correct file path')
                exit()
            else:
                with open(self.node_ids_file, 'r') as f:
                    self.nodes = [line.strip() for line in f]
                n_nodes = 0
                for cluster in self.configs['clusters']:
                    n_nodes += cluster['n_nodes']
                if len(self.nodes) != n_nodes:
                    logger.error("The topology required %s nodes, but the file contents %s nodes. Please provide the correct node IDs" % (
                        n_nodes, len(self.nodes)))
                    exit()
                logger.debug('nodes = %s' % self.nodes)

    def detach_volume_from_node(self, driver, volume_id, node_id):
        """Detach node which is attaching to given volumes

        Parameters
        ----------
        volumes: list
            list of volume IDs on OVHCloud
        """
        driver.post('/cloud/project/%s/volume/%s/detach' % (self.configs['project_id'], volume_id),
                    instanceId=node_id)

    def attach_volume_to_node(self, driver, volume_id, node_id):
        """Attach an external volumes to a node

        Parameters
        ----------
        node_id: string
            ID of the node
        volume_id: string
            ID of the volume
        """
        driver.post('/cloud/project/%s/volume/%s/attach' % (self.configs['project_id'], volume_id),
                    instanceId=node_id)

    def attach_volume(self, nodes):
        """Attach external volumes in the same region to given nodes

        Parameters
        ----------
        nodes: list of node
            list of nodes information

        """
        driver = self._get_ovh_driver()
        list_volumes = driver.get('/cloud/project/%s/volume' % self.configs['project_id'])
        volumes = dict()
        for volume in list_volumes:
            volumes[volume['region']] = volumes.get(volume['region'], list()) + [volume['id']]
        attached_volumes = dict()
        for node in nodes:
            if not volumes.get(node['region']):
                if len(attached_volumes) > 0:
                    for volume_id, node_id in attached_volumes.items():
                        self.detach_volume_from_node(driver, volume_id, node_id)
                logger.error('Not enough volumes to attach to node on region %s' % node['region'])
                logger.warning('No nodes are attached')
                exit()
            else:
                volume_id = volumes[node['region']].pop()
                self.attach_volume_to_node(driver, volume_id, node['id'])
                attached_volumes[volume_id] = node['id']

    def _get_existing_nodes(self, driver):
        list_regions = list()
        for cluster in self.configs['clusters']:
            list_regions.append(cluster['region'])
        existing_nodes = dict()
        for region in list_regions:
            existing_nodes[region] = list()

        for region in list_regions:
            nodes = driver.get('/cloud/project/%s/instance' % self.configs['project_id'],
                               region=region)
            for node in nodes:
                existing_nodes[region].append(node['name'])
        return existing_nodes

    def _get_flavor_id(self, driver, region, instance_type):
        flavors = driver.get('/cloud/project/%s/flavor' %
                             self.configs['project_id'], region='%s' % region)
        for flavor in flavors:
            if flavor['name'] == instance_type:
                return flavor['id']
        return None

    def _get_image_id(self, driver, region, image_name):
        images = driver.get('/cloud/project/%s/image' %
                            self.configs['project_id'], region='%s' % region)
        for image in images:
            if image['name'] == '%s' % image_name:
                return image['id']
        return None

    def _get_ovh_driver(self):
        logger.info("Creating a Driver to connect to OVHCloud")
        driver = ovh.Client(
            endpoint=self.configs['endpoint'],
            application_key=self.configs['application_key'],
            application_secret=self.configs['application_secret'],
            consumer_key=self.configs['consumer_key'],
        )
        return driver

    def make_reservation(self, driver):
        project_id = self.configs['project_id']

        existing_nodes = self._get_existing_nodes(driver)

        logger.info("Checking existing nodes")
        error_nodes = set()
        for cluster in self.configs['clusters']:
            if cluster.get('node_name'):
                new_nodes = [cluster['node_name']+'-%s' % i for i in range(1, cluster['n_nodes']+1)]
                logger.info('new_nodes = %s' % new_nodes)
                r = set(existing_nodes['region']).intersection(set(new_nodes))
                logger.info('r = %s' % r)
                error_nodes = error_nodes.union(r)
        if error_nodes:
            logger.error('Can not provision nodes on OVHCloud')
            logger.error('Nodes: %s are already existing' % error_nodes)
            exit()

        logger.info("Starting provisioning nodes on ovh")
        for cluster in self.configs['clusters']:
            n_nodes = cluster['n_nodes']
            logger.debug('n_nodes = %s' % n_nodes)

            region = cluster['region']
            logger.debug('region = %s' % region)

            if cluster.get('node_name') is None:
                # using kebabcase in node name to follow name in Kubernetes
                _hash = base64.urlsafe_b64encode(hashlib.md5(
                    str(time.time()).encode()).digest()).decode('ascii')[:8].lower()
                _hash = _hash.replace('_', '-')
                cluster['node_name'] = 'node-%s-%s' % (region.lower(), _hash)

            if cluster['flexible_instance'] is True:
                instance_type = '%s-flex' % cluster['instance_type']
            else:
                instance_type = cluster['instance_type']
            logger.debug('instance_type = %s' % instance_type)

            flavor_id = self._get_flavor_id(driver, region, instance_type)
            logger.debug('flavor_id = %s' % flavor_id)

            image_id = self._get_image_id(driver, region, cluster['image'])
            logger.debug('image_id = %s' % image_id)

            sshKey_id = driver.get('/cloud/project/%s/sshkey' %
                                   project_id, region='%s' % region)[0]['id']
            logger.debug('sshKey_id = %s' % sshKey_id)

            # post_installation script on nodes: edit ssh setting to enable login as root user
            post_install_script = '''#!/bin/bash

                                    sudo sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/g' /etc/ssh/sshd_config &&
                                    sudo service ssh restart && 
                                    sudo sed -i 's/^.*ssh-rsa/ssh-rsa/' /root/.ssh/authorized_keys '''

            logger.info("Deploying %s nodes on %s" % (n_nodes, region))
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
        logger.debug('Waiting for all hosts are up')
        sleep(60)
        logger.info('nodes = %s' % self.nodes)

    def _wait_hosts_up(self, driver):
        logger.info('Checking whether all hosts are up')
        nodes_up = list()
        for node in self.nodes:
            node = driver.get('/cloud/project/%s/instance/%s' % (self.configs['project_id'], node))
            if node['status'] == 'ACTIVE':
                nodes_up.append(node)
        if len(nodes_up) == len(self.nodes):
            logger.info('All reserved hosts are up')
            self.nodes = nodes_up
        else:
            hosts_ko = [node['name'] for node in self.nodes if node not in nodes_up]
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
        driver = self._get_ovh_driver()
        if self.node_ids_file is None:
            self.make_reservation(driver)

            home = os.path.expanduser('~')
            self.node_ids_file = os.path.join(home, 'node_ids_file')
            if os.path.exists(self.node_ids_file):
                os.remove(self.node_ids_file)
            with open(self.node_ids_file, 'w') as f:
                for id in self.nodes:
                    f.write(id + "\n")
        logger.info('List of node IDs is stored at: %s' % self.node_ids_file)

        self._wait_hosts_up(driver)
        self.get_resources()
