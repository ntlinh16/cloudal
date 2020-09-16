from cloudal.utils import get_logger, execute_cmd


logger = get_logger()


class docker_configurator(object):
    """ This is a base class of host_configuring,
        and it can be used to config servers on different OS."""

    def __init__(self, hosts):
        self.hosts = hosts

    def _install_packages(self, packages):
        try:
            cmd = (
                "export DEBIAN_FRONTEND=noninteractive; "
                "apt-get update && apt-get "
                "install --yes --allow-change-held-packages --no-install-recommends %s"
            ) % packages

            # cmd = 'export DEBIAN_MASTER=noninteractive ; apt-get update && apt-get install -y --force-yes ' +\
            #     '-o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -t ' % self.packages
            self.error_hosts = execute_cmd(cmd, self.hosts)
            # return result
        except Exception as e:
            logger.error("---> Bug [%s] with command: %s" % (e, cmd), exc_info=True)

    def _install_docker(self):
        logger.info('Installing wget package')
        self._install_packages('wget')
        logger.info('Downloading the official get_docker script')
        cmd = 'wget https://get.docker.com -O get-docker.sh'
        self.error_hosts = execute_cmd(cmd, self.hosts)
        logger.info('Installing Docker by using get_docker script')
        cmd = 'sh get-docker.sh'
        self.error_hosts = execute_cmd(cmd, self.hosts)

    def config_hosts(self):
        logger.info('Starting install Docker on %s hosts' % len(self.hosts))
        self._install_docker()
        logger.info('Installing Docker on %s hosts: DONE' % len(self.hosts))
