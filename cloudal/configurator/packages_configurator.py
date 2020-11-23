from cloudal.utils import get_logger, execute_cmd


logger = get_logger()


class packages_configurator(object):

    def install_packages_with_apt(self, packages, hosts):
        '''Install a list of given packages

        Parameters
        ----------
        packages: list of string
            the list of package names to be installed

        hosts: list of string
            the list of hostnames

        '''
        logger.debug("Installing packages: %s on %s hosts" % (', '.join(packages)), len(hosts))
        cmd = (
            "export DEBIAN_FRONTEND=noninteractive; "
            "apt-get update && apt-get "
            "install --yes --allow-change-held-packages --no-install-recommends %s"
        ) % ' '.join(packages)
        try:
            execute_cmd(cmd, hosts)
        except Exception as e:
            logger.error("---> Bug [%s] with command: %s" % (e, cmd), exc_info=True)

    def install_packages_with_yum(self, packages, hosts):
        '''Install a list of given packages

        Parameters
        ----------
        packages: list of string
            the list of package names to be installed

        hosts: list of string
            the list of hostnames

        '''
        logger.debug("Installing packages: %s on %s hosts" % (', '.join(packages)), len(hosts))
        cmd = (
            "export DEBIAN_FRONTEND=noninteractive; "
            "yum update && apt-get "
            "install --yes --allow-change-held-packages --no-install-recommends %s"
        ) % ' '.join(packages)
        try:
            execute_cmd(cmd, hosts)
        except Exception as e:
            logger.error("---> Bug [%s] with command: %s" % (e, cmd), exc_info=True)

    def install_packages(self, packages, hosts):
        '''Install a list of given packages

        Parameters
        ----------
        packages: list of string
            the list of package names to be installed

        hosts: list of string
            the list of hostnames

        '''
        list_os_hosts = dict()
        for host in hosts:
            cmd = "uname -a | awk '{print$6}'"
            _, r = execute_cmd(cmd, host)
            os_name = r.processes[0].stdout.strip().lower()
            list_os_hosts[os_name] = list_os_hosts.get(os_name, list()) + [host]

        logger.info('list_os_hosts: %s' % list_os_hosts)
        logger.info("Installing packages: %s" % ', '.join(packages))
        for os_name, list_hosts in list_os_hosts.items():
            if os_name in ['debian', 'ubuntu']:
                self.install_packages_with_apt(packages, list_hosts)
            elif os_name in ['centos']:
                self.install_packages_with_yum(packages, list_hosts)
            elif os_name in ['fedora']:
                self.install_packages_with_dnf(packages, list_hosts)
