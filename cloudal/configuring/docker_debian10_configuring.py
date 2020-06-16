from cloudal.utils import get_logger, execute_cmd


logger = get_logger()


class docker_debian_configuring(object):
    """ This is a base class of host_configuring,
        and it can be used to config servers on different OS."""

    def __init__(self, hosts):
        self.hosts = hosts

    def _upgrade_hosts(self):
        """Dist upgrade performed on all hosts"""
        logger.info('Upgrading packages')
        cmd = "echo 'debconf debconf/frontend select noninteractive' | debconf-set-selections ; " + \
              "echo 'debconf debconf/priority select critical' | debconf-set-selections ;      " + \
              "export DEBIAN_MASTER=noninteractive ; apt-get update ; " + \
              "apt-get dist-upgrade -y --force-yes -o Dpkg::Options::='--force-confdef' " + \
              "-o Dpkg::Options::='--force-confold' "
        self.error_hosts = execute_cmd(cmd, self.hosts)

    def _config_dependencies(self):
        """Uninstall old versions of docker """
        logger.info('Uninstall old Docker instance')
        cmd = 'apt-get remove docker docker-engine docker.io containerd runc'

        self.error_hosts = execute_cmd(cmd, self.hosts)

        # self.remote_executor.get_remote(cmd, self.hosts).run()

        """Installation of required packages on the hosts"""
        depend_packages = 'apt-transport-https ca-certificates curl gnupg2 software-properties-common'
        logger.info('Installing following dependencies for Docker: \n%s' % depend_packages)
        self._install_packages(depend_packages)

        cmd = 'curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"'
        self.error_hosts = execute_cmd(cmd, self.hosts)
        cmd = "sed -i 's/\\\\//g' /etc/apt/sources.list"
        self.error_hosts = execute_cmd(cmd, self.hosts)

        # self._upgrade_hosts()

    def _install_packages(self, packages):
        try:
            # cmd = 'export DEBIAN_MASTER=noninteractive ; apt-get update && apt-get ' + \
            #     'install --yes --force-yes --no-install-recommends ' + packages

            # to force no prompt and say yes when install in Debian 10
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
        docker_packages = 'docker-ce docker-ce-cli containerd.io'
        logger.info('Installing Docker packages: \n%s' % docker_packages)
        self._install_packages(docker_packages)

    def _configure_docker(self, bridge='br0', docker_conf=None):
        pass

    def config_hosts(self):
        logger.info('Configuring %s hosts with Docker' % len(self.hosts))
        self._config_dependencies()
        self._install_docker()
        # self._configure_docker()
        logger.info('Configuring %s hosts with Docker' % len(self.hosts))
