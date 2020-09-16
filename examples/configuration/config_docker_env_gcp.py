import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioning.gcp_provisioner import gcp_provisioner
from cloudal.configuring.docker_configurator import docker_configurator


logger = get_logger()


class config_docker_env_gcp(performing_actions):
    def __init__(self):
        super(config_docker_env_gcp, self).__init__()

    def provisioning(self):
        logger.info("Init provisioner: gcp_provisioner")
        self.provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
        logger.info("Making reservation")
        self.provisioner.make_reservation()
        logger.info("Getting resources")
        self.provisioner.get_resources()
        self.hosts = self.provisioner.hosts

    def config_host(self):
        logger.info("Init configurator")
        configurator = docker_configurator(self.hosts)
        logger.info("Starting install Docker")
        configurator.config_hosts()

    def run(self):
        logger.info("Starting provision nodes")
        self.provisioning()
        logger.info("Provisioning nodes: DONE")

        logger.info("Starting configure Docker on nodes")
        self.config_host()
        logger.info("Configuring Docker on nodes: DONE")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_docker_env_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
