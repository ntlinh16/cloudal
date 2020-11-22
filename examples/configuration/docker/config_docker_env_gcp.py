import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioner import gcp_provisioner
from cloudal.configurator import docker_configurator


logger = get_logger()


class config_docker_env_gcp(performing_actions):
    def __init__(self):
        super(config_docker_env_gcp, self).__init__()

    def config_host(self):
        logger.debug("Init configurator")
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

    def provisioning(self):
        logger.debug("Init provisioner: gcp_provisioner")
        provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
        provisioner.make_reservation()
        provisioner.get_resources()
        self.hosts = provisioner.hosts

    def run(self):
        self.provisioning()
        self.config_host()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_docker_env_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
