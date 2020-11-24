import os
import traceback

from cloudal.utils import get_logger, get_file
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import kubernetes_configurator
from cloudal.configurator import docker_configurator

from execo_g5k import oardel

from kubernetes import config

logger = get_logger()


class provision_g5k_k8s(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(provision_g5k_k8s, self).__init__()

    def _get_credential(self, kube_master):
        home = os.path.expanduser('~')
        kube_dir = os.path.join(home, '.kube')

        if not os.path.exists(kube_dir):
            os.mkdir(kube_dir)
        get_file(host=kube_master, remote_file_paths=['~/.kube/config'], local_dir=kube_dir)
        config.load_kube_config(config_file=os.path.join(kube_dir, 'config'))
        logger.info('Kubernetes config file is stored at: %s' % kube_dir)

    def config_host(self, hosts):
        logger.info("Starting configuring Kubernetes cluster")
        logger.info("Init configurator: docker_configurator")
        configurator = docker_configurator(hosts)
        configurator.config_docker()

        logger.info("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(hosts)
        kube_master, kube_workers = configurator.deploy_kubernetes_cluster()
        logger.info('Kubernetes workers: %s' % kube_workers)

        self._get_credential(kube_master=kube_master)

        logger.info("Finish configuring Kubernetes cluster")

    def run(self):
        logger.info("Init provisioner: g5k_provisioner")
        provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                      keep_alive=self.args.keep_alive,
                                      out_of_chart=self.args.out_of_chart,
                                      oar_job_ids=self.args.oar_job_ids,
                                      no_deploy_os=self.args.no_deploy_os,
                                      is_reservation=self.args.is_reservation,
                                      job_name="cloudal")
        provisioner.provisioning()
        hosts = provisioner.hosts

        self.config_host(hosts)


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_g5k_k8s()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
