# import os
import traceback

from cloudal.utils import get_logger, execute_cmd
from cloudal.action import performing_actions
from cloudal.provisioning.gcp_provisioner import gcp_provisioner
from cloudal.configuring.docker_configurator import docker_configurator

logger = get_logger()


class config_CIbench_env_gcp(performing_actions):
    """ This is a base class of cloudal engine, that is built from execo_engine
        and can be used to deploy servers a different cloud system."""

    def __init__(self):
        """ Add options for the number of measures, number of nodes
        walltime, env_file or env_name and clusters and initialize the engine
        """

        # Using super() function to access the parrent class
        # so that we do not care about the changing of parent class

        super(config_CIbench_env_gcp, self).__init__()

    def provisioning(self):
        """self.oar_result containts the list of tuples (oar_job_id, site_name)
        that identifies the reservation on each site,
        which can be retrieved from the command line arguments or from make_reservation()"""

        logger.info("Init provisioner: gcp_provisioner")
        self.provisioner = gcp_provisioner(config_file_path=self.args.config_file_path)
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

        logger.info("Pull cadvisor docker image")
        cmd = 'docker pull google/cadvisor'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Install docker-compose")
        cmd = 'apt-get update && apt-get install --yes --allow-change-held-packages --no-install-recommends docker-compose'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        # logger.info("Install golang")
        # cmd = 'cd ~/ && wget https://dl.google.com/go/go1.14.3.linux-amd64.tar.gz'
        # self.error_hosts = execute_cmd(cmd, self.hosts)
        # cmd = 'cd ~/ && tar xzf go1.14.3.linux-amd64.tar.gz'
        # self.error_hosts = execute_cmd(cmd, self.hosts)
        # cmd = 'chown -R root:root ~/go'
        # self.error_hosts = execute_cmd(cmd, self.hosts)
        # cmdRemise appliquée automatiquementRemise appliquée automatiquementRemise appliquée automatiquementRemise appliquée automatiquement = 'mv ~/go /usr/local'
        # self.error_hosts = execute_cmd(cmd, self.hosts)
        # cmd = 'echo "export PATH=$PATH:/usr/local/go/bin" >> ~/.profile'
        # self.error_hosts = execute_cmd(cmd, self.hosts)
        # cmd = 'bash ~/.profile'
        # self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Install CI-Bench")
        cmd = 'cd ~/ && git clone https://github.com/AntidoteDB/antidote.git'
        self.error_hosts = execute_cmd(cmd, self.hosts)
        logger.info("Install CI-Bench 2")
        cmd = 'cd ~/antidote && make docker-build'
        self.error_hosts = execute_cmd(cmd, self.hosts)
        logger.info("Install CI-Bench 3")
        cmd = 'cd ~/ && git clone https://github.com/AntidoteDB/CI-bench.git'
        self.error_hosts = execute_cmd(cmd, self.hosts)
        logger.info("Install CI-Bench 4")
        cmd = 'cd ~/CI-bench && docker build --no-cache -t antidote-benchmark .'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Finish configuring CI-bench")

    def run(self):
        logger.info("Start provisioning hosts")
        self.provisioning()
        logger.info("Finish provisioning hosts")

        logger.info("Start configuring CI-bench on hosts")
        self.config_host()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_CIbench_env_gcp()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
