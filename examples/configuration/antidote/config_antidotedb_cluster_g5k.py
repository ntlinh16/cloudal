import os
import traceback

from cloudal.utils import get_logger, get_file, execute_cmd
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import kubernetes_configurator
from cloudal.configurator import docker_configurator
from cloudal.configurator import antidotedb_configurator

from kubernetes import config

logger = get_logger()


class config_antidotedb_cluster_g5k(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(config_antidotedb_cluster_g5k, self).__init__()
        self.args_parser.add_argument("--antidote_yaml_dir", dest="yaml_path",
                                      help="path to yaml file to deploy antidotedb cluster",
                                      default='',
                                      required=True,
                                      type=str)

    def _get_credential(self, kube_master):
        home = os.path.expanduser('~')
        kube_dir = os.path.join(home, '.kube')

        if not os.path.exists(kube_dir):
            os.mkdir(kube_dir)
        get_file(host=kube_master, remote_file_paths=[
                 '~/.kube/config'], local_dir=kube_dir)
        config.load_kube_config(config_file=os.path.join(kube_dir, 'config'))
        logger.info('Kubernetes config file is stored at: %s' % kube_dir)

    def _setup_g5k_kube_volumes(self, kube_workers):
        logger.info("Setting volumes on %s kubernetes workers" %
                    len(kube_workers))
        N_PV = 10
        cmd = '''umount /dev/sda5;
                 mount -t ext4 /dev/sda5 /tmp'''
        execute_cmd(cmd, kube_workers)
        cmd = '''for i in $(seq 1 %s); do
                     mkdir -p /tmp/pv/vol${i}
                     mkdir -p /mnt/disks/vol${i}
                     mount --bind /tmp/pv/vol${i} /mnt/disks/vol${i}
                 done''' % N_PV
        execute_cmd(cmd, kube_workers)

    def config_host(self):
        logger.info("Init configurator: docker_configurator")
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        logger.info("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(self.hosts)
        kube_master, kube_workers = configurator.deploy_kubernetes_cluster()
        logger.info('Kubernetes master: %s' % kube_master)

        self._get_credential(kube_master=kube_master)

        self._setup_g5k_kube_volumes(kube_workers)

        logger.info("Init configurator: antidotedb_configurator")
        configurator = antidotedb_configurator(path=self.args.yaml_path)
        configurator.deploy_antidotedb_cluster()

    def run(self):
        logger.info("STARTING PROVISIONING NODES")
        logger.info("Init provisioner: g5k_provisioner")
        provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                      keep_alive=self.args.keep_alive,
                                      out_of_chart=self.args.out_of_chart,
                                      oar_job_ids=self.args.oar_job_ids,
                                      no_deploy_os=self.args.no_deploy_os,
                                      is_reservation=self.args.is_reservation,
                                      job_name="cloudal")
        provisioner.provisioning()
        self.hosts = provisioner.hosts
        logger.info("FINISH PROVISIONING NODES")

        logger.info("STARTING DEPLOY KUBERNETES CLUSTERS")
        self.config_host()
        logger.info("FINISH DEPLOY KUBERNETES CLUSTERS")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_cluster_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
