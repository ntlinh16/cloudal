import traceback

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioner import gcp_provisioner
from cloudal.configurator import docker_swarm_configurator

logger = get_logger()


class provision_docker_swarm_gcp(performing_actions):
    def __init__(self):
        super(provision_docker_swarm_gcp, self).__init__()

    def run(self):
        # make reservation from requested nodes in config file
        logger.info("Init provisioner: gcp_provisioner")
        provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
        provisioner.provisioning()
        hosts = provisioner.hosts

        # deploy docker swarm on all reserved hosts
        logger.info('Starting configuring hosts')
        logger.info("Init configurator: docker_swarm_configurator")
        configurator = docker_swarm_configurator(hosts)
        ds_manager, ds_workers = configurator.deploy_docker_swarm_cluster()
        logger.info('Docker Swarm workers: %s' % ds_workers)


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = provision_docker_swarm_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
