import traceback
import os
import yaml
import base64
from tempfile import NamedTemporaryFile
from time import sleep

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioner import gke_provisioner
from cloudal.configurator import k8s_resources_configurator

from kubernetes import client

import google.auth
import google.auth.transport.requests


logger = get_logger()


class config_antidotedb_cluster_gke(performing_actions):
    def __init__(self, **kwargs):
        super(config_antidotedb_cluster_gke, self).__init__()
        self.args_parser.add_argument("--antidote_yaml_dir", dest="yaml_path",
                                      help="path to yaml file to deploy antidotedb cluster",
                                      default='',
                                      required=True,
                                      type=str)

    def config_antidote(self, kube_config, cluster, kube_namespace):
        logger.info('Starting deploying Antidote cluster')

        logger.info('Deleting old resources on namspace "%s"' % kube_namespace)
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.delete_namespace(namespace=kube_namespace, kube_config=kube_config)
        configurator.create_namespace(namespace=kube_namespace, kube_config=kube_config)

        antidote_k8s_dir = self.args.yaml_path

        logger.debug('Delete old deployment files if exists')
        for filename in os.listdir(antidote_k8s_dir):
            if filename.startswith('createDC_') or filename.startswith('statefulSet_') or filename.startswith('exposer-service_') or filename.startswith('connectDCs_antidote'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(antidote_k8s_dir, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        logger.debug('Modify the statefulSet file')
        with open(os.path.join(antidote_k8s_dir, 'statefulSet.yaml.template')) as f:
            doc = yaml.safe_load(f)

        doc['spec']['replicas'] = cluster.current_node_count
        doc['metadata']['name'] = 'antidote-%s' % cluster.name
        with open(os.path.join(antidote_k8s_dir, 'statefulSet_%s.yaml' % cluster.name), 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Starting AntidoteDB instances")
        configurator.deploy_k8s_resources(kube_config=kube_config, path=antidote_k8s_dir, namespace=kube_namespace)
        logger.info('Waiting until all Antidote instances are up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors='app=antidote',
                                        kube_config=kube_config,
                                        kube_namespace=kube_namespace)

        logger.debug('Creating createDc.yaml file for each Antidote DC')
        antidote_pods = configurator.get_k8s_resources_name(resource='pod',
                                                            kube_config=kube_config,
                                                            label_selectors='app=antidote',
                                                            kube_namespace=kube_namespace)
        deploy_files = list()
        file_path = os.path.join(antidote_k8s_dir, 'createDC.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = ['--createDc', '%s.antidote:8087' %
                                                                    antidote_pods[0]] + ['antidote@%s.antidote' % pod for pod in antidote_pods]
        doc['metadata']['name'] = 'createdc-%s' % cluster.name
        file_path = os.path.join(antidote_k8s_dir, 'createDC_%s.yaml' % cluster.name)
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)
        deploy_files.append(file_path)

        logger.debug('Creating exposer-service.yaml files')
        with open(os.path.join(antidote_k8s_dir, 'exposer-service.yaml.template')) as f:
            doc = yaml.safe_load(f)
        doc['spec']['selector']['statefulset.kubernetes.io/pod-name'] = antidote_pods[0]
        doc['metadata']['name'] = 'antidote-exposer-%s' % cluster.name
        file_path = os.path.join(antidote_k8s_dir, 'exposer-service_%s.yaml' % cluster.name)
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)
        deploy_files.append(file_path)

        logger.info("Starting connecting all Antidote instances and exposing service")
        configurator.deploy_k8s_resources(kube_config=kube_config, files=deploy_files, namespace=kube_namespace)
        logger.info('Waiting to create Antidote DC')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors='app=antidote',
                                        kube_config=kube_config,
                                        kube_namespace=kube_namespace)
        logger.info("Finish configuring an AntidoteDB DC on %s\n" % cluster.name)

    def connect_antidote_DCs(self, antidote_services_ips, kube_config, kube_namespace):
        antidote_k8s_dir = self.args.yaml_path
        logger.debug('Creating connectDCs_antidote.yaml to connect all Antidote DCs')
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = ['--connectDcs'] + antidote_services_ips
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs_antidote.yaml')
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Connecting all Antidote DCs into a cluster")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(kube_config=kube_config, files=[file_path], namespace=kube_namespace)

        logger.info('Waiting until connecting all Antidote DCs')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors='app=antidote',
                                        kube_config=kube_config,
                                        kube_namespace=kube_namespace)

    def _get_credential(self, cluster):
        logger.info('Getting credential for cluster %s' % cluster.name)
        creds, projects = google.auth.load_credentials_from_file(filename=self.configs['service_account_credentials_json_file_path'],
                                                                 scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        kube_config = client.Configuration()
        kube_config.host = 'https://%s' % cluster.endpoint
        with NamedTemporaryFile(delete=False) as ca_cert:
            ca_cert.write(base64.b64decode(cluster.master_auth.cluster_ca_certificate))
        kube_config.ssl_ca_cert = ca_cert.name
        kube_config.api_key_prefix['authorization'] = 'Bearer'
        kube_config.api_key['authorization'] = creds.token
        logger.debug('Getting credential for cluster : DONE')
        return kube_config

    def config_host(self, kube_namespace):
        logger.info("Starting configuring an AntidoteDB cluster")
        antidote_services_ips = list()
        for cluster in self.clusters:
            kube_config = self._get_credential(cluster)

            logger.info('Creating namespace "%s" to deploy Antidote DC' % kube_namespace)
            configurator = k8s_resources_configurator()
            configurator.create_namespace(namespace=kube_namespace, kube_config=kube_config)

            self.config_antidote(kube_config, cluster, kube_namespace)

            service_name = 'antidote-exposer-%s' % cluster.name
            antidote_services_ips.append('%s:8087' % configurator.get_k8s_endpoint_ip(service_name,
                                                                                      kube_config,
                                                                                      kube_namespace))

        logger.info("Starting connecting all AntidoteDB DCs")
        self.connect_antidote_DCs(antidote_services_ips, kube_config, kube_namespace)
        logger.info("Finish configuring an AntidoteDB cluster\n")

    def run(self):
        logger.debug("Init provisioner: gke_provisioner")
        provisioner = gke_provisioner(config_file_path=self.args.config_file_path)
        provisioner.make_reservation()
        self.clusters = provisioner.clusters
        self.configs = provisioner.configs

        kube_namespace = 'antidote'
        self.config_host(kube_namespace)


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_cluster_gke()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
