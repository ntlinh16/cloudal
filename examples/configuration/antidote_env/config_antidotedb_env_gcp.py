import traceback

from cloudal.utils import get_logger, execute_cmd
from cloudal.action import performing_actions
from cloudal.provisioner import gcp_provisioner
from cloudal.configurator import docker_configurator


logger = get_logger()


class config_antidotedb_env_gcp(performing_actions):
    def __init__(self):
        super(config_antidotedb_env_gcp, self).__init__()

    def config_host(self, hosts):
        logger.info("Starting configure AntidoteDB on nodes")
        logger.debug("Init configurator: docker_configurator")
        configurator = docker_configurator(hosts)
        configurator.config_docker()

        logger.info("Pull AntidoteDB docker image")
        cmd = 'docker pull antidotedb/antidote'
        execute_cmd(cmd, hosts)

        logger.info("Run AntidoteDB container")
        cmd = 'docker run -d --name antidote -p "8087:8087" antidotedb/antidote'
        execute_cmd(cmd, hosts)
        logger.info("Finish configuring AntidoteDB on all hosts")

    def provisioning(self):
        logger.debug("Init provisioner: gcp_provisioner")
        provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
        provisioner.make_reservation()
        provisioner.get_resources()
        hosts_ips = provisioner.hosts
        return hosts_ips

    def run(self):
        hosts_ips = self.provisioning()
        self.config_host(hosts_ips)


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_env_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
