import os

from cloudal.utils import get_logger
from cloudal.configurator import k8s_resources_configurator

import yaml
logger = get_logger()

class CancelException(Exception):
    pass

class antidotedb_configurator(object):

    def _calculate_ring_size(self, n_nodes):
        # calculate the ring size base on the number of nodes in a DC
        # this setting follows the recomandation of Riak KV here:
        # https://docs.riak.com/riak/kv/latest/setup/planning/cluster-capacity/index.html#ring-size-number-of-partitions 
        if n_nodes < 7:
            return 64
        elif n_nodes < 10:
            return 128
        elif n_nodes < 14:
            return 256
        elif n_nodes < 20:
            return 512
        elif n_nodes < 40:
            return 1024
        return 2048

    def deploy_antidotedb(self, n_nodes, antidote_yaml_path, clusters, k8s_namespace='default'):
        """Deploy AntidoteDB on the given K8s cluster

        Parameters
        ----------
        n_nodes: int
            the number of AntidoteDB nodes
        antidote_yaml_path: str
            a path to the K8s yaml deployment file 
        clusters: list
            a list of cluster that antidoted will be deployed on
        k8s_namespace: str
            the name of K8s naespace
        """

        logger.debug('Delete old createDC, connectDCs_antidote and exposer-service files if exists')
        for filename in os.listdir(antidote_yaml_path):
            if filename.startswith('createDC_') or filename.startswith('statefulSet_') or filename.startswith('exposer-service_') or filename.startswith('connectDCs_antidote'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(antidote_yaml_path, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        statefulSet_files = [os.path.join(antidote_yaml_path, 'headlessService.yaml')]
        
        logger.debug('Modify the statefulSet file')
        ring_size  = self._calculate_ring_size(n_nodes)
        file_path = os.path.join(antidote_yaml_path, 'statefulSet.yaml.template')    
        with open(file_path) as f:
            doc = yaml.safe_load(f)

        for cluster in clusters:
            doc['spec']['replicas'] = n_nodes
            doc['metadata']['name'] = 'antidote-%s' % cluster
            doc['spec']['template']['spec']['nodeSelector'] = {
                'service_g5k': 'antidote', 'cluster_g5k': '%s' % cluster}
            envs = doc['spec']['template']['spec']['containers'][0]['env']
            for env in envs:
                if env.get('name') == "RING_SIZE":
                    env['value'] = str(ring_size)
                    break
            file_path = os.path.join(antidote_yaml_path, 'statefulSet_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            statefulSet_files.append(file_path)

        logger.info("Starting AntidoteDB instances")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=statefulSet_files, namespace=k8s_namespace)

        logger.info('Waiting until all Antidote instances are up')
        deploy_ok = configurator.wait_k8s_resources(resource='pod',
                                                    label_selectors="app=antidote",
                                                    timeout=600,
                                                    kube_namespace=k8s_namespace)
        if not deploy_ok:
            raise CancelException("Cannot deploy enough Antidotedb instances")

        logger.debug('Creating createDc.yaml file for each Antidote DC')
        dcs = dict()
        for cluster in clusters:
            dcs[cluster] = list()
        antidote_list = configurator.get_k8s_resources_name(resource='pod',
                                                            label_selectors='app=antidote',
                                                            kube_namespace=k8s_namespace)
        logger.info("Checking if AntidoteDB are deployed correctly")
        if len(antidote_list) != n_nodes*len(clusters):
            logger.info("n_antidotedb = %s, n_deployed_fmke_app = %s" %
                        (n_nodes*len(clusters), len(antidote_list)))
            raise CancelException("Cannot deploy enough Antidotedb instances")

        for antidote in antidote_list:
            cluster = antidote.split('-')[1].strip()
            dcs[cluster].append(antidote)

        file_path = os.path.join(antidote_yaml_path, 'createDC.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)

        antidote_masters = list()
        createdc_files = list()
        for cluster, pods in dcs.items():
            doc['spec']['template']['spec']['containers'][0]['args'] = ['--createDc',
                                                                        '%s.antidote:8087' % pods[0]] + ['antidote@%s.antidote' % pod for pod in pods]
            doc['metadata']['name'] = 'createdc-%s' % cluster
            antidote_masters.append('%s.antidote:8087' % pods[0])
            file_path = os.path.join(antidote_yaml_path, 'createDC_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            createdc_files.append(file_path)

        logger.debug('Creating exposer-service.yaml files')
        file_path = os.path.join(antidote_yaml_path, 'exposer-service.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        for cluster, pods in dcs.items():
            doc['spec']['selector']['statefulset.kubernetes.io/pod-name'] = pods[0]
            doc['metadata']['name'] = 'antidote-exposer-%s' % cluster
            file_path = os.path.join(antidote_yaml_path, 'exposer-service_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            createdc_files.append(file_path)

        logger.info("Creating Antidote DCs and exposing services")
        configurator.deploy_k8s_resources(files=createdc_files, namespace=k8s_namespace)

        logger.info('Waiting until all antidote DCs are created')
        deploy_ok = configurator.wait_k8s_resources(resource='job',
                                                    label_selectors='app=antidote',
                                                    kube_namespace=k8s_namespace)

        if not deploy_ok:
            raise CancelException("Cannot connect Antidotedb instances to create DC")

        logger.debug('Creating connectDCs_antidote.yaml to connect all Antidote DCs')
        file_path = os.path.join(antidote_yaml_path, 'connectDCs.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = [
            '--connectDcs'] + antidote_masters
        file_path = os.path.join(antidote_yaml_path, 'connectDCs_antidote.yaml')
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Connecting all Antidote DCs into a cluster")
        configurator.deploy_k8s_resources(files=[file_path], namespace=k8s_namespace)

        logger.info('Waiting until connecting all Antidote DCs')
        deploy_ok = configurator.wait_k8s_resources(resource='job',
                                                    label_selectors='app=antidote',
                                                    kube_namespace=k8s_namespace)
        if not deploy_ok:
            raise CancelException("Cannot connect all Antidotedb DCs")

        logger.info('Finish deploying the Antidote cluster')