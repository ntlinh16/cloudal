import traceback

from cloudal.utils import get_logger, execute_cmd
from cloudal.action import performing_actions
from cloudal.provisioning.gcp_provisioner import gcp_provisioner
from cloudal.configuring.docker_configurator import docker_configurator


logger = get_logger()


class config_antidotedb_env_gcp(performing_actions):
    def __init__(self):
        super(config_antidotedb_env_gcp, self).__init__()

    def provisioning(self):
        logger.info("Init provisioner: gcp_provisioner")
        provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
        logger.info("Making reservation")
        provisioner.make_reservation()
        logger.info("Getting resources of nodes:")
        provisioner.get_resources()
        self.hosts = provisioner.hosts

    def config_host(self):
        # Install & config Docker
        logger.info("Init configurator: docker_configurator")
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        # Install antidoteDB
        logger.info("Starting configure AntidoteDB on nodes")
        logger.info("Pull AntidoteDB docker image")
        cmd = 'docker pull antidotedb/antidote'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Run AntidoteDB container")
        cmd = 'docker run -d --name antidote -p "8087:8087" antidotedb/antidote'
        self.error_hosts = execute_cmd(cmd, self.hosts)

    def run(self):
        logger.info("Starting provision nodes")
        self.provisioning()
        logger.info("Provisioning nodes: DONE")

        logger.info("Starting configure AntidoteDB on nodes")
        self.config_host()
        logger.info("Configuring AntidoteDB on nodes: DONE")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_env_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
