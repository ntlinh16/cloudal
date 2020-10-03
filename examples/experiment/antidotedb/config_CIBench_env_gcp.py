# import os
import traceback

from cloudal.utils import get_logger, execute_cmd
from cloudal.action import performing_actions
from cloudal.provisioner import gcp_provisioner
from cloudal.configurator import docker_configurator

logger = get_logger()


class config_CIbench_env_gcp(performing_actions):
    def __init__(self):
        super(config_CIbench_env_gcp, self).__init__()

    def provisioning(self):
        logger.info("Init provisioner: gcp_provisioner")
        self.provisioner = gcp_provisioner(
            config_file_path=self.args.config_file_path)
        logger.info("Making reservation")
        self.provisioner.make_reservation()
        logger.info("Getting resources")
        self.provisioner.get_resources()
        self.hosts = self.provisioner.hosts

    def config_host(self):
        logger.info("Start configuring docker on hosts")
        logger.info("Init Docker configurator")
        configurator = docker_configurator(self.hosts)
        configurator.config_hosts()

        logger.info("Install essential packages")
        cmd = 'apt-get install --yes --allow-change-held-packages --no-install-recommends git make htop sysstat'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Pull AntidoteDB docker image")
        cmd = 'docker pull antidotedb/antidote'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'docker pull google/cadvisor'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Install docker-compose")
        cmd = 'apt-get update && apt-get install --yes --allow-change-held-packages --no-install-recommends docker-compose'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Install CI-Bench")
        cmd = 'cd ~/ && git clone https://github.com/AntidoteDB/antidote.git'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'cd ~/antidote && make docker-build'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'cd ~/ && git clone https://github.com/AntidoteDB/CI-bench.git'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'cd ~/CI-bench && docker build --no-cache -t antidote-benchmark .'
        self.error_hosts = execute_cmd(cmd, self.hosts)

    def run(self):
        logger.info("Starting provision nodes")
        self.provisioning()
        logger.info("Provisioning nodes: DONE")

        logger.info("Starting configure CI-Bench on nodes")
        self.config_host()
        logger.info("Configuring CI-Bench on nodes: DONE")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_CIbench_env_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
