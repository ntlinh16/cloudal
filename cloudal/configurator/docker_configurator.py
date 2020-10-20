from cloudal.utils import get_logger, execute_cmd, install_packages_on_debian


logger = get_logger()


class docker_configurator(object):
    """
    """

    def __init__(self, hosts):
        self.hosts = hosts

    def config_docker(self):
        logger.info('Starting installing Docker on %s hosts' % len(self.hosts))
        logger.info('Installing wget package')
        install_packages_on_debian(['wget'], self.hosts)
        logger.info('Downloading the official get_docker script')
        cmd = 'wget https://get.docker.com -O get-docker.sh'
        self.error_hosts = execute_cmd(cmd, self.hosts)
        logger.info('Installing Docker by using get_docker script')
        cmd = 'sh get-docker.sh'
        self.error_hosts = execute_cmd(cmd, self.hosts)
        logger.info('Finish installing Docker on %s hosts' % len(self.hosts))
