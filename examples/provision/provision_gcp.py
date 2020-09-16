import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioning.gcp_provisioner import gcp_provisioner

logger = get_logger()


class provision_gcp(performing_actions):
    def __init__(self):
        super(provision_gcp, self).__init__()

    def provisioning(self):
        logger.info("Init provisioner: gcp_provisioner")
        self.provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
        logger.info("Making reservation")
        self.provisioner.make_reservation()
        logger.info("Getting resources")
        self.provisioner.get_resources()

    def run(self):
        logger.info("Starting provision hosts")
        self.provisioning()
        logger.info("Finish provisioning hosts")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
