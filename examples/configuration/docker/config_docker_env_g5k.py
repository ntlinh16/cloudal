import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import docker_configurator

from execo_g5k import oardel


logger = get_logger()


class config_docker_env_g5k(performing_actions_g5k):
    """
    """

    def __init__(self):
        super(config_docker_env_g5k, self).__init__()

    def config_host(self, hosts):
        logger.info("Init configurator: docker_configurator")
        configurator = docker_configurator(hosts)
        configurator.config_docker()

    def run(self):
        logger.info("Starting provision nodes")
        logger.info("Init provisioner: g5k_provisioner")
        provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                      keep_alive=self.args.keep_alive,
                                      out_of_chart=self.args.out_of_chart,
                                      oar_job_ids=self.args.oar_job_ids,
                                      no_deploy_os=self.args.no_deploy_os,
                                      is_reservation=self.args.is_reservation,
                                      job_name="cloudal_docker")
        provisioner.provisioning()
        hosts = provisioner.hosts
        self.oar_result = provisioner.oar_result
        logger.info("Provisioning nodes: DONE")

        logger.info("Starting configure Docker on nodes")
        self.config_host(hosts)
        logger.info("Configuring Docker on nodes: DONE")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_docker_env_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.info('Program is terminated by the following exception:')
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
