import traceback
import os
import yaml
import base64
from tempfile import NamedTemporaryFile
from time import sleep

from cloudal.utils import get_logger, execute_cmd, getput_file, parse_config_file
from cloudal.action import performing_actions
from cloudal.provisioner import gke_provisioner, gcp_provisioner
from cloudal.configurator import k8s_resources_configurator, docker_configurator, packages_configurator

from kubernetes import client

import google.auth
import google.auth.transport.requests


logger = get_logger()


class elmerfs_gke(performing_actions):
    def __init__(self, **kwargs):
        super(elmerfs_gke, self).__init__()
        self.args_parser.add_argument("--antidote_yaml_dir", dest="yaml_path",
                                      help="path to yaml file to deploy antidotedb cluster",
                                      default='',
                                      required=True,
                                      type=str)

    def config_elmerfs(self, hosts_gcp, antidote_services_ips, configs_gcp):
        logger.info("Starting deploying elmerfs on hosts")
        configurator = packages_configurator()
        configurator.install_packages(['libfuse2'], hosts_gcp)

        elmerfs_file_path = configs_gcp['exp_env']['elmerfs_file_path']

        logger.info('Killing elmerfs process if it is running')
        for host in hosts_gcp:
            cmd = "ps aux | grep elmerfs | awk '{print$2}'"
            _, r = execute_cmd(cmd, host)
            pids = r.processes[0].stdout.strip().split('\r\n')
            if len(pids) >= 3:
                cmd = "kill %s && umount /tmp/dc-$(hostname)" % pids[0]
                execute_cmd(cmd, host)

        if elmerfs_file_path is None:
            logger.debug("Building elmerfs project on kube_master node and then downloading to local machine")

            configurator.install_packages(['libfuse2'], hosts_gcp[0])

            configurator = docker_configurator(hosts=[hosts_gcp[0]])
            configurator.config_docker()

            logger.info("Downloading elmerfs project")
            cmd = " rm -rf /tmp/elmerfs_repo \
                    && git clone https://github.com/scality/elmerfs.git /tmp/elmerfs_repo \
                    && cd /tmp/elmerfs_repo \
                    && git submodule update --init --recursive"
            execute_cmd(cmd, hosts_gcp[0])

            cmd = '''cat <<EOF | sudo tee /tmp/elmerfs_repo/Dockerfile
            FROM rust:1.47
            RUN mkdir  /elmerfs
            WORKDIR /elmerfs
            COPY . .
            RUN apt-get update \
                && apt-get -y install libfuse-dev
            RUN cargo build --release
            CMD ["/bin/bash"]
            '''
            execute_cmd(cmd, hosts_gcp[0])

            logger.info("Building elmerfs")
            cmd = " cd /tmp/elmerfs_repo/ \
                    && docker build -t elmerfs ."
            execute_cmd(cmd, hosts_gcp[0])

            cmd = "docker run --name elmerfs elmerfs \
                    && docker cp -L elmerfs:/elmerfs/target/release/main /tmp/elmerfs \
                    && docker rm elmerfs"
            execute_cmd(cmd, hosts_gcp[0])

            logger.debug('Downloading elmerfs binary file to local directory: /tmp/')
            getput_file(hosts=[hosts_gcp[0]], file_paths=['/tmp/elmerfs'], dest_location='/tmp', action='get')
            elmerfs_file_path = '/tmp/elmerfs'

        logger.info("Uploading elmerfs binary file from local to elmerfs hosts")
        getput_file(hosts=hosts_gcp, file_paths=[elmerfs_file_path], dest_location='/tmp', action='put')
        cmd = "chmod +x /tmp/elmerfs \
               && mkdir -p /tmp/dc-$(hostname)"
        execute_cmd(cmd, hosts_gcp)

        logger.debug('Creating antidote options for elmerfs command')
        antidote_options = ["--antidote=%s" % ip for ip in antidote_services_ips]

        logger.info("Starting elmerfs on hosts: %s" % hosts_gcp)
        cmd = "RUST_BACKTRACE=1 RUST_LOG=debug nohup /tmp/elmerfs %s --mount=/tmp/dc-$(hostname) --no-locks > /tmp/elmer.log" % " ".join(
            antidote_options)
        for host in hosts_gcp:
            execute_cmd(cmd, host, mode='start')
            sleep(20)
        logger.info('Finish deploying elmerfs\n')

    def deploy_antidote(self, kube_config, cluster, kube_namespace):
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

    def _get_credential(self, cluster, configs_gke):
        logger.info('Getting credential for cluster %s' % cluster.name)
        creds, projects = google.auth.load_credentials_from_file(filename=configs_gke['service_account_credentials_json_file_path'],
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

    def config_antidote(self, kube_namespace, clusters_gke, configs_gke):
        logger.info("Starting configuring an AntidoteDB cluster")
        antidote_services_ips = list()
        kube_config = None
        for cluster in clusters_gke:
            kube_config = self._get_credential(cluster, configs_gke)

            logger.info('Creating namespace "%s" to deploy Antidote DC' % kube_namespace)
            configurator = k8s_resources_configurator()
            configurator.create_namespace(namespace=kube_namespace, kube_config=kube_config)

            self.deploy_antidote(kube_config, cluster, kube_namespace)

            service_name = 'antidote-exposer-%s' % cluster.name
            antidote_services_ips.append('%s:8087' % configurator.get_k8s_endpoint_ip(service_name,
                                                                                      kube_config,
                                                                                      kube_namespace))

        logger.info("Starting connecting all AntidoteDB DCs")
        self.connect_antidote_DCs(antidote_services_ips, kube_config, kube_namespace)
        logger.info("Finish configuring an AntidoteDB cluster\n")
        return antidote_services_ips

    def create_configs(self):
        configs = parse_config_file(self.args.config_file_path)
        configs_gke = configs.copy()
        configs_gke['clusters'] = configs_gke.pop('antidote_clusters')
        configs_gcp = configs.copy()
        configs_gcp['clusters'] = configs_gcp.pop('elmerfs_clusters')
        return configs_gke, configs_gcp

    def setup_env(self):
        configs_gke, configs_gcp = self.create_configs()
        logger.info('Starting provisioning K8s clusters on GKE to deploy an antidoteDB cluster')
        logger.debug("Init provisioner: gke_provisioner")
        provisioner = gke_provisioner(configs=configs_gke)
        provisioner.make_reservation()
        clusters_gke = provisioner.clusters

        logger.info('Starting provisioning nodes on GCP to deploy elmerfs nodes')
        logger.debug("Init provisioner: gke_provisioner")
        provisioner = gcp_provisioner(configs=configs_gcp)
        provisioner.make_reservation()
        provisioner.get_resources()
        hosts_gcp = provisioner.hosts

        kube_namespace = 'antidote'
        antidote_services_ips = self.config_antidote(kube_namespace, clusters_gke, configs_gke)
        self.config_elmerfs(hosts_gcp, antidote_services_ips, configs_gcp)

    def run(self):
        self.setup_env()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = elmerfs_gke()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
