# import os
import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioning.g5k_provisioner import g5k_provisioner

# from execo import default_connection_params
from execo_g5k import oardel
# from execo_g5k.config import default_frontend_connection_params


logger = get_logger()


# current_user = os.getlogin()
# default_connection_params['user'] = 'root'
# default_frontend_connection_params['user'] = current_user


class provision_g5k(performing_actions):
    """ This is a base class of cloudal engine, that is built from execo_engine
        and can be used to deploy servers a different cloud system."""

    def __init__(self):
        """ Add options for the number of measures, number of nodes
        walltime, env_file or env_name and clusters and initialize the engine
        """

        # Using super() function to access the parrent class
        # so that we do not care about the changing of parent class

        super(provision_g5k, self).__init__()

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

    def run(self):
        logger.info("Start provisioning hosts")
        self.provisioning()
        logger.info("Finish provisioning hosts")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
