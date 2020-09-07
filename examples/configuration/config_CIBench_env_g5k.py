from cloudal.utils import get_logger, execute_cmd
from cloudal.action import performing_actions
from cloudal.provisioning.g5k_provisioner import g5k_provisioner
from cloudal.configuring.docker_configurator import docker_configurator

from execo_g5k import oardel


logger = get_logger()


class config_CIbench_env_g5k(performing_actions):
    """
    """

    def __init__(self):
        """ Add options for the number of measures, number of nodes
        walltime, env_file or env_name and clusters and initialize the engine
        """

        # Using super() function to access the parrent class
        # so that we do not care about the changing of parent class

        super(config_CIbench_env_g5k, self).__init__()

        self.args_parser.add_argument("-k", dest="keep_alive",
                                      help="keep the reservation alive after deploying.",
                                      action="store_true")

        self.args_parser.add_argument("-o", dest="out_of_chart",
                                      help="run the engine outside of grid5k charter",
                                      action="store_true")

        self.args_parser.add_argument("-j", dest="oar_job_ids",
                                      help="the reserved oar_job_ids on grid5k. The format is site1:oar_job_id1,site2:oar_job_id2,...",
                                      type=str)

        self.args_parser.add_argument("--no-deploy-os", dest="no_deploy_os",
                                      help="specify not to deploy OS on reserved nodes",
                                      action="store_true")

    def provisioning(self):
        """self.oar_result containts the list of tuples (oar_job_id, site_name)
        that identifies the reservation on each site,
        which can be retrieved from the command line arguments or from make_reservation()"""

        logger.info("Init provisioner: g5k_provisioner")
        self.provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                           keep_alive=self.args.keep_alive,
                                           out_of_chart=self.args.out_of_chart)
        self.provisioner.oar_result = list()

        if self.args.oar_job_ids is not None:
            for each in self.args.oar_job_ids.split(','):
                site_name, oar_job_id = each.split(':')
                self.provisioner.oar_result.append((int(oar_job_id), str(site_name)))
        else:
            self.provisioner.make_reservation()

        """Retrieve the hosts address list and (ip, mac) list from a list of oar_result and
        return the resources which is a dict needed by g5k_provisioner """
        self.provisioner.get_resources()
        self.hosts = self.provisioner.hosts

        if not self.args.no_deploy_os:
            self.provisioner.setup_hosts()

    def config_host(self):
        logger.info("Init Docker configurator")
        configurator = docker_configurator(self.hosts)
        # Install & config Docker
        logger.info("Start configuring Docker on hosts")
        configurator.config_hosts()

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
        # cmd = 'mv ~/go /usr/local'
        # self.error_hosts = execute_cmd(cmd, self.hosts)
        # cmd = 'echo "export PATH=$PATH:/usr/local/go/bin" >> ~/.profile'
        # self.error_hosts = execute_cmd(cmd, self.hosts)
        # cmd = 'source ~/.profile'
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

        logger.info("Finish configuring hosts")

    def run(self):
        self.provisioning()
        self.config_host()
        # self.perform_experiments()


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_CIbench_env_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
