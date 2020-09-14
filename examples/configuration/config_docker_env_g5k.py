import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioning.g5k_provisioner import g5k_provisioner
from cloudal.configuring.docker_configurator import docker_configurator

from execo_g5k import oardel


logger = get_logger()


class config_docker_env_g5k(performing_actions):
    """
    """

    def __init__(self):
        """ Add options for the number of measures, number of nodes
        walltime, env_file or env_name and clusters and initialize the engine
        """

        # Using super() function to access the parrent class
        # so that we do not care about the changing of parent class

        super(config_docker_env_g5k, self).__init__()

        self.args_parser.add_argument("-k", dest="keep_alive",
                                      help="keep the reservation alive after deploying.",
                                      action="store_true")

        self.args_parser.add_argument("-o", dest="out_of_chart",
                                      help="run the engine outside of grid5k charter",
                                      action="store_true")

        self.args_parser.add_argument("-j", dest="oar_job_ids",
                                      help="the reserved oar_job_ids on grid5k. The format is site1:oar_job_id1,site2:oar_job_id2,...",
                                      type=str)

        self.args_parser.add_argument("--no-deploy-os", dest="no_deploy_os",
                                      help="specify not to deploy OS on reserved nodes",
                                      action="store_true")

    def provisioning(self):
        """self.oar_result containts the list of tuples (oar_job_id, site_name)
        that identifies the reservation on each site,
        which can be retrieved from the command line arguments or from make_reservation()"""

        logger.info("Init provisioner: g5k_provisioner")
        self.provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                           keep_alive=self.args.keep_alive,
                                           out_of_chart=self.args.out_of_chart,
                                           oar_job_ids=self.args.oar_job_ids)

        self.provisioner.make_reservation()

        """Retrieve the hosts address list and (ip, mac) list from a list of oar_result and
        return the resources which is a dict needed by g5k_provisioner """
        self.provisioner.get_resources()
        self.hosts = self.provisioner.hosts

        if not self.args.no_deploy_os:
            self.provisioner.setup_hosts()

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
        # self.perform_experiments()


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
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
