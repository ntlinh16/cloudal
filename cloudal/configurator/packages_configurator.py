from time import sleep

from cloudal.utils import get_logger, execute_cmd

logger = get_logger()

OS_NAMES = {
    "ubuntu": "Ubuntu",
    "debian": "Debian",
    "rhel": "RedHat Enterprise Linux",
    "centos": "CentOS",
    "fedora": "Fedora",
    "sles": "SUSE Linux Enterprise Server",
    "opensuse": "openSUSE",
    "amazon": "Amazon Linux",
    "arch": "Arch Linux",
    "cloudlinux": "CloudLinux OS",
    "exherbo": "Exherbo Linux",
    "gentoo": "GenToo Linux",
    "ibm_powerkvm": "IBM PowerKVM",
    "kvmibm": "KVM for IBM z Systems",
    "linuxmint": "Linux Mint",
    "mageia": "Mageia",
    "mandriva": "Mandriva Linux",
    "parallels": "Parallels",
    "pidora": "Pidora",
    "raspbian": "Raspbian",
    "oracle": "Oracle Linux (and Oracle Enterprise Linux)",
    "scientific": "Scientific Linux",
    "slackware": "Slackware",
    "xenserver": "XenServer",
    "openbsd": "OpenBSD",
    "netbsd": "NetBSD",
    "freebsd": "FreeBSD",
    "midnightbsd": "MidnightBSD",
}

MAX_RETRIES = 10


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
        logger.debug("Installing packages: %s on %s hosts" % (', '.join(packages), len(hosts)))
        cmd = ("export DEBIAN_FRONTEND=noninteractive && "
               "apt-get update && "
               "apt-get install -q -y --allow-change-held-packages %s") % ' '.join(packages)
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
        logger.debug("Installing packages: %s on %s hosts" % (', '.join(packages), len(hosts)))
        cmd = ("yum update -y -q && "
               "yum install -y -q %s") % ' '.join(packages)
        try:
            execute_cmd(cmd, hosts)
        except Exception as e:
            logger.error("---> Bug [%s] with command: %s" % (e, cmd), exc_info=True)

    def install_packages_with_dnf(self, packages, hosts):
        '''Install a list of given packages

        Parameters
        ----------
        packages: list of string
            the list of package names to be installed

        hosts: list of string
            the list of hostnames

        '''
        logger.debug("Installing packages: %s on %s hosts" % (', '.join(packages), len(hosts)))
        cmd = ("dnf update -y -q && "
               "dnf install -y -q %s") % ' '.join(packages)
        try:
            execute_cmd(cmd, hosts)
        except Exception as e:
            logger.error("---> Bug [%s] with command: %s" % (e, cmd), exc_info=True)

    def _get_os_name(self, host):
        os_name = None
        for attempt in range(MAX_RETRIES):
            cmd = 'hostnamectl | grep "Operating System"'
            _, r = execute_cmd(cmd, host)
            os_info = r.processes[0].stdout.strip().lower()
            if os_info:
                for os_name, os_full_name in OS_NAMES.items():
                    if os_name in os_info:
                        logger.debug('OS of %s: %s' % (host, os_full_name))
                        return os_name, os_full_name
                return None, None
            logger.info('---> Retrying: "%s" on host %s ' % (cmd, host))
            sleep(10)
        return None, None

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
        logger.info("Installing packages: %s" % ', '.join(packages))

        for host in hosts:
            os_name, os_full_name = self._get_os_name(host)
            if os_name:
                list_os_hosts[os_name] = list_os_hosts.get(os_name, list()) + [host]
            else:
                logger.error('Cannot install %s on %s due to no OS name found' % (packages, host))

        for os_name, list_hosts in list_os_hosts.items():
            if os_name in ['debian', 'ubuntu']:
                self.install_packages_with_apt(packages, list_hosts)
            elif os_name in ['centos']:
                self.install_packages_with_yum(packages, list_hosts)
            elif os_name in ['fedora']:
                self.install_packages_with_dnf(packages, list_hosts)
            else:
                logger.info('Not support to install packages on OS %s yet' % os_name)
