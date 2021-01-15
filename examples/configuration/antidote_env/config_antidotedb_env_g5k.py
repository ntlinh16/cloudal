from cloudal.utils import get_logger, execute_cmd
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import docker_configurator

from execo_g5k import oardel


logger = get_logger()


class config_antidotedb_env_g5k(performing_actions_g5k):
    """
    """

    def __init__(self):
        super(config_antidotedb_env_g5k, self).__init__()

    def config_host(self, hosts):
        logger.info("Starting configure AntidoteDB on nodes")
        # Install & config Docker
        logger.info("Init configurator: docker_configurator")
        configurator = docker_configurator(hosts)
        configurator.config_docker()

        # Install antidoteDB
        logger.info("Starting configure AntidoteDB")
        logger.info("Pull AntidoteDB docker image")
        cmd = 'docker pull antidotedb/antidote'
        execute_cmd(cmd, hosts)

        logger.info("Run AntidoteDB container")
        cmd = 'docker run -d --name antidote -p "8087:8087" antidotedb/antidote'
        execute_cmd(cmd, hosts)

        logger.info("Finish configuring AntidoteDB on all hosts")

    def run(self):
        logger.info("Starting provision nodes")
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
        self.oar_result = provisioner.oar_result

        self.config_host(hosts)


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_env_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
