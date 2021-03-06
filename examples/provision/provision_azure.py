import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioner import azure_provisioner

logger = get_logger()


class provision_azure(performing_actions):
    def __init__(self):
        super(provision_azure, self).__init__()

    def run(self):
        logger.debug("Init provisioner: azure_provisioner")
        provisioner = azure_provisioner(config_file_path=self.args.config_file_path)
        provisioner.provisioning()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_azure()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
