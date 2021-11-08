import os
import traceback

from cloudal.utils import get_logger, getput_file
from cloudal.action import performing_actions
from cloudal.provisioner import ovh_provisioner
from cloudal.configurator import kubernetes_configurator, k8s_resources_configurator

from kubernetes import config

logger = get_logger()


class config_antidotedb_cluster_ovh(performing_actions):
    def __init__(self):
        super(config_antidotedb_cluster_ovh, self).__init__()

    def _set_kube_workers_label(self, kube_master):
        configurator = k8s_resources_configurator()
        clusters = dict()
        for node in self.nodes:
            if node['ipAddresses'][0]['ip'] == kube_master:
                pass
            else:
                cluster = node['region']
                clusters[cluster] = [node['name']] + clusters.get(cluster, list())
                configurator.set_labels_node(nodename=node['name'],
                                            labels='cluster_ovh=%s' % cluster)

    def _get_credential(self, kube_master):
        home = os.path.expanduser('~')
        kube_dir = os.path.join(home, '.kube')
        if not os.path.exists(kube_dir):
            os.mkdir(kube_dir)
        getput_file(hosts=[kube_master], file_paths=['~/.kube/config'],
                    dest_location=kube_dir, action='get')
        kube_config_file = os.path.join(kube_dir, 'config')
        config.load_kube_config(config_file=kube_config_file)
        logger.info('Kubernetes config file is stored at: %s' % kube_config_file)

    def deploy_k8s(self, kube_master):
        logger.debug("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(hosts=self.hosts, kube_master=kube_master)
        _, kube_workers = configurator.deploy_kubernetes_cluster()

        return kube_workers


    def setup_k8s(self, kube_namespace):
        logger.info("Starting configuring nodes")
        for node in self.nodes:
            if node['name'] == self.configs['clusters'][0]['node_name']:
                kube_master = node['ipAddresses'][0]['ip']
        logger.info('Kubernetes master: %s' % kube_master)

        kube_workers = self.deploy_k8s(kube_master)

        self._get_credential(kube_master)

        logger.info('Create k8s namespace "%s" for the experiments' % kube_namespace)
        configurator = k8s_resources_configurator()
        configurator.create_namespace(namespace=kube_namespace)

        logger.info('Set labels for all kubernetes workers')
        self._set_kube_workers_label(kube_workers)

        logger.info("Finish configuring Kubernetes environment")
        return kube_master

    def provisioning(self):
        logger.debug("Init provisioner: ovh_provisioner")
        provisioner = ovh_provisioner(config_file_path=self.args.config_file_path)
        provisioner.provisioning()

        self.nodes = provisioner.nodes
        self.hosts = provisioner.hosts
        self.configs = provisioner.configs

    def run(self):
        self.provisioning()

        kube_namespace = 'exp'
        self.setup_k8s(kube_namespace)



if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_cluster_ovh()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
