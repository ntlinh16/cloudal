import os

from cloudal.utils import get_logger, execute_cmd, is_ip
from cloudal.configurator import k8s_resources_configurator, CancelException, packages_configurator

import yaml
logger = get_logger()


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

    def deploy_antidotedb(self, n_nodes, antidotedb_yaml_path, clusters, kube_namespace='default'):
        """Deploy AntidoteDB on the given Kubernetes cluster

        Parameters
        ----------
        n_nodes: int
            the number of AntidoteDB nodes
        antidotedb_yaml_path: str
            a path to the K8s yaml deployment files
        clusters: list
            a list of cluster that antidoted will be deployed on
        kube_namespace: str
            the name of K8s namespace
        """

        logger.debug('Delete old createDC, connectDCs and exposer-service files if exists')
        for filename in os.listdir(antidotedb_yaml_path):
            if filename.startswith('createDC_') or filename.startswith('statefulSet_') or filename.startswith('exposer-service_') or filename.startswith('connectDCs_antidote'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(antidotedb_yaml_path, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        statefulSet_files = [os.path.join(antidotedb_yaml_path, 'headlessService.yaml')]
        
        logger.debug('Modify the statefulSet file')
        ring_size  = self._calculate_ring_size(n_nodes)
        file_path = os.path.join(antidotedb_yaml_path, 'statefulSet.yaml.template')    
        with open(file_path) as f:
            doc = yaml.safe_load(f)

        for cluster in clusters:
            doc['spec']['replicas'] = n_nodes
            doc['metadata']['name'] = 'antidote-%s' % cluster.lower()
            doc['spec']['template']['spec']['nodeSelector'] = {
                'service': 'antidote', 'cluster': '%s' % cluster.lower()}
            envs = doc['spec']['template']['spec']['containers'][0]['env']
            for env in envs:
                if env.get('name') == "RING_SIZE":
                    env['value'] = str(ring_size)
                    break
            file_path = os.path.join(antidotedb_yaml_path, 'statefulSet_%s.yaml' % cluster.lower())
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            statefulSet_files.append(file_path)

        logger.info("Starting AntidoteDB instances")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=statefulSet_files, namespace=kube_namespace)

        logger.info('Waiting until all AntidoteDB instances are up')
        deploy_ok = configurator.wait_k8s_resources(resource='pod',
                                                    label_selectors="app=antidote",
                                                    timeout=600,
                                                    kube_namespace=kube_namespace)
        if not deploy_ok:
            raise CancelException("Cannot deploy enough Antidotedb instances")

        logger.debug('Creating createDc.yaml file for each AntidoteDB DC')
        dcs = dict()
        for cluster in clusters:
            dcs[cluster.lower()] = list()
        antidote_list = configurator.get_k8s_resources_name(resource='pod',
                                                            label_selectors='app=antidote',
                                                            kube_namespace=kube_namespace)
        logger.info("Checking if AntidoteDB are deployed correctly")
        if len(antidote_list) != n_nodes*len(clusters):
            logger.info("n_antidotedb = %s, n_deployed_fmke_app = %s" % (n_nodes*len(clusters), len(antidote_list)))
            raise CancelException("Cannot deploy enough Antidotedb instances")

        for antidote in antidote_list:
            cluster = antidote.split('-')[1].strip()
            dcs[cluster].append(antidote)

        file_path = os.path.join(antidotedb_yaml_path, 'createDC.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)

        antidote_masters = list()
        createdc_files = list()
        for cluster, pods in dcs.items():
            doc['spec']['template']['spec']['containers'][0]['args'] = ['--createDc',
                                                                        '%s.antidote:8087' % pods[0]] + ['antidote@%s.antidote' % pod for pod in pods]
            doc['metadata']['name'] = 'createdc-%s' % cluster
            antidote_masters.append('%s.antidote:8087' % pods[0])
            file_path = os.path.join(antidotedb_yaml_path, 'createDC_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            createdc_files.append(file_path)

        logger.debug('Creating exposer-service.yaml files')
        file_path = os.path.join(antidotedb_yaml_path, 'exposer-service.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        for cluster, pods in dcs.items():
            doc['spec']['selector']['statefulset.kubernetes.io/pod-name'] = pods[0]
            doc['metadata']['name'] = 'antidote-exposer-%s' % cluster
            file_path = os.path.join(antidotedb_yaml_path, 'exposer-service_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            createdc_files.append(file_path)

        logger.info("Creating AntidoteDB DCs and exposing services")
        configurator.deploy_k8s_resources(files=createdc_files, namespace=kube_namespace)

        logger.info('Waiting until all AntidoteDB DCs are created')
        deploy_ok = configurator.wait_k8s_resources(resource='job',
                                                    label_selectors='app=antidote',
                                                    kube_namespace=kube_namespace)

        if not deploy_ok:
            raise CancelException("Cannot connect AntidoteDB instances to create DC")

        logger.debug('Creating connectDCs_antidote.yaml to connect all AntidoteDB DCs')
        file_path = os.path.join(antidotedb_yaml_path, 'connectDCs.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = [
            '--connectDcs'] + antidote_masters
        file_path = os.path.join(antidotedb_yaml_path, 'connectDCs_antidote.yaml')
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Connecting all AntidoteDB DCs into a cluster")
        configurator.deploy_k8s_resources(files=[file_path], namespace=kube_namespace)

        logger.info('Waiting until connecting all AntidoteDB DCs')
        deploy_ok = configurator.wait_k8s_resources(resource='job',
                                                    label_selectors='app=antidote',
                                                    kube_namespace=kube_namespace)
        if not deploy_ok:
            raise CancelException("Cannot connect all AntidoteDB DCs")

        logger.info('Finish deploying the AntidoteDB cluster')

    def deploy_monitoring(self, node, monitoring_yaml_path, kube_namespace='default'):
        """Deploy monitoring system for AntidoteDB cluster on the given K8s cluster

        Parameters
        ----------
        node: str
            the IP or hostname used to connect to the node to deploy monitoring system on
        monitoring_yaml_path: str
            a path to the K8s yaml deployment files
        kube_namespace: str
            the name of K8s namespace
        """
        logger.info("Deleting old deployment")
        cmd = "rm -rf /root/antidote_stats"
        execute_cmd(cmd, node)

        configurator = packages_configurator()
        configurator.install_packages(['git'], [node])

        cmd = "git clone https://github.com/AntidoteDB/antidote_stats.git"
        execute_cmd(cmd, node)
        logger.info("Setting to allow pods created on kube mater node")
        cmd = "kubectl taint nodes --all node-role.kubernetes.io/master-"
        execute_cmd(cmd, node, is_continue=True)

        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        pods = configurator.get_k8s_resources_name(resource='pod',
                                                   label_selectors='app=antidote',
                                                   kube_namespace=kube_namespace)
        antidote_info = ["%s.antidote:3001" % pod for pod in pods]

        logger.debug('Modify the prometheus.yml file with AntidoteDB instances info')
        file_path = os.path.join(monitoring_yaml_path, 'prometheus.yml.template')
        with open(file_path) as f:
            doc = f.read().replace('antidotedc_info', '%s' % antidote_info)
        prometheus_configmap_file = os.path.join(monitoring_yaml_path, 'prometheus.yml')
        with open(prometheus_configmap_file, 'w') as f:
            f.write(doc)
        configurator.create_configmap(file=prometheus_configmap_file,
                                      namespace=kube_namespace,
                                      configmap_name='prometheus-configmap')
        logger.debug('Modify the deploy_prometheus.yaml file with node info')
        
        if not is_ip(node):
            node_info = configurator.get_k8s_resources(resource='node',
                                                            label_selectors='kubernetes.io/hostname=%s' % node)
            for item in node_info.items[0].status.addresses:
                if item.type == 'InternalIP':
                    node_ip = item.address
            node_hostname = node
        else:
            node_ip = node
            cmd = 'hostname'
            _, r = execute_cmd(cmd, node)
            node_hostname = r.processes[0].stdout.strip().lower()

        file_path = os.path.join(monitoring_yaml_path, 'deploy_prometheus.yaml.template')
        with open(file_path) as f:
            doc = f.read().replace('node_ip', '%s' % node_ip)
            doc = doc.replace("node_hostname", '%s' % node_hostname)
        prometheus_deploy_file = os.path.join(monitoring_yaml_path, 'deploy_prometheus.yaml')
        with open(prometheus_deploy_file, 'w') as f:
            f.write(doc)

        logger.info("Starting Prometheus service")
        configurator.deploy_k8s_resources(files=[prometheus_deploy_file], namespace=kube_namespace)
        logger.info('Waiting until Prometheus instance is up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=prometheus",
                                        kube_namespace=kube_namespace)

        logger.debug('Modify the deploy_grafana.yaml file with node info')
        file_path = os.path.join(monitoring_yaml_path, 'deploy_grafana.yaml.template')
        with open(file_path) as f:
            doc = f.read().replace('node_ip', '%s' % node_ip)
            doc = doc.replace("node_hostname", '%s' % node_hostname)
        grafana_deploy_file = os.path.join(monitoring_yaml_path, 'deploy_grafana.yaml')
        with open(grafana_deploy_file, 'w') as f:
            f.write(doc)

        file = '/root/antidote_stats/monitoring/grafana-config/provisioning/datasources/all.yml'
        cmd = """ sed -i "s/localhost/%s/" %s """ % (node_ip, file)
        execute_cmd(cmd, node)

        logger.info("Starting Grafana service")
        configurator.deploy_k8s_resources(files=[grafana_deploy_file], namespace=kube_namespace)
        logger.info('Waiting until Grafana instance is up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=grafana",
                                        kube_namespace=kube_namespace)

        logger.info("Finish deploying monitoring system\n")
        prometheus_url = "http://%s:9090" % node_ip
        grafana_url = "http://%s:3000" % node_ip
        logger.info("Connect to Grafana at: %s" % grafana_url)
        logger.info("Connect to Prometheus at: %s" % prometheus_url)

        return prometheus_url, grafana_url