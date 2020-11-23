# import os
import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioner import gke_provisioner

logger = get_logger()


class provision_gke(performing_actions):
    def __init__(self):
        super(provision_gke, self).__init__()

    def provisioning(self):
        logger.debug("Init provisioner: gke_provisioner")
        provisioner = gke_provisioner(config_file_path=self.args.config_file_path)
        provisioner.make_reservation()
        clusters = provisioner.clusters

        clusters_name = list()
        for cluster in clusters:
            clusters_name.append(cluster.name)
        logger.info('List of clusters: %s' % clusters_name)

    def run(self):
        self.provisioning()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_gke()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
