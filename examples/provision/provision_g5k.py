import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions_g5k
from cloudal.provisioning.g5k_provisioner import g5k_provisioner
from execo_g5k import oardel

logger = get_logger()

# from execo import default_connection_params
# from execo_g5k.config import default_frontend_connection_params


# current_user = os.getlogin()
# default_connection_params['user'] = 'root'
# default_frontend_connection_params['user'] = current_user


class provision_g5k(performing_actions_g5k):
    def __init__(self):
        super(provision_g5k, self).__init__()

    def provisioning(self):
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
        logger.info("Starting provisioning hosts")
        self.provisioning()
        logger.info("Provisioning hosts: DONE")


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
