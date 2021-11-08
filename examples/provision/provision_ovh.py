import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioner import ovh_provisioner

logger = get_logger()


class provision_ovh(performing_actions):
    def __init__(self):
        super(provision_ovh, self).__init__()

    def provisioning(self):
        logger.debug("Init provisioner: ovh_provisioner")
        provisioner = ovh_provisioner(config_file_path=self.args.config_file_path)
        provisioner.provisioning()

        hosts = provisioner.hosts
        logger.info('List of hosts: %s' % hosts)

    def run(self):
        self.provisioning()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_ovh()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
