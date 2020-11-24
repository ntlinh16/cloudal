import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioner import gcp_provisioner

logger = get_logger()


class provision_gcp(performing_actions):
    def __init__(self):
        super(provision_gcp, self).__init__()

    def provisioning(self):
        logger.debug("Init provisioner: gcp_provisioner")
        provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
        provisioner.provisioning()

        nodes = provisioner.nodes
        hosts = dict()
        for node in nodes:
            hosts[node.name] = node.public_ips[0]
        logger.info('List of hosts: %s' % hosts)

    def run(self):
        self.provisioning()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
