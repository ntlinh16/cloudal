import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from execo_g5k import oardel

logger = get_logger()


class provision_g5k(performing_actions_g5k):
    def __init__(self):
        super(provision_g5k, self).__init__()

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
        logger.info("FINISH PROVISIONING NODES")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
