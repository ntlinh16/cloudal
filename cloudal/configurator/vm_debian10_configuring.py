import os
from tempfile import mkstemp
from xml.etree.ElementTree import Element, SubElement

from cloudal.utils import get_logger, get_remote_executor, execute_cmd

from execo import Process, Local, Host, sleep


logger = get_logger()


class vm_debian_configurator(object):
    """ This is a base class of host_configuring,
        and it can be used to config servers on different OS."""

    def __init__(self, hosts):
        self.hosts = hosts
        self.remote_executor = get_remote_executor()

    def _upgrade_hosts(self):
        """Dist upgrade performed on all hosts"""
        logger.info('Upgrading packages')
        cmd = "echo 'debconf debconf/frontend select noninteractive' | debconf-set-selections ; " + \
              "echo 'debconf debconf/priority select critical' | debconf-set-selections ;      " + \
              "export DEBIAN_MASTER=noninteractive ; apt-get update ; " + \
              "apt-get dist-upgrade -y --force-yes -o Dpkg::Options::='--force-confdef' " + \
              "-o Dpkg::Options::='--force-confold' "
        execute_cmd(cmd, self.hosts)

    def _config_dependencies(self):
        """Create the sources.list file """
        logger.info('Configuring APT')
        # Create sources.list file
        fd, tmpsource = mkstemp(dir='/tmp/', prefix='sources.list_')
        with os.fdopen(fd, 'w') as f:
            f.write('deb http://deb.debian.org/debian buster main contrib non-free\n' +
                    'deb-src http://deb.debian.org/debian buster main contrib non-free\n' +
                    'deb http://deb.debian.org/debian buster-updates main contrib non-free\n' +
                    'deb-src http://deb.debian.org/debian buster-updates main contrib non-free\n' +
                    'deb http://security.debian.org/debian-security/ buster/updates main contrib non-free\n' +
                    'deb-src http://security.debian.org/debian-security/ buster/updates main contrib non-free\n')

        # Create preferences file
        fd, tmppref = mkstemp(dir='/tmp/', prefix='preferences_')
        with os.fdopen(fd, 'w') as f:
            f.write('Package: * \nPin: release a=buster \nPin-Priority: 900\n\n' +
                    'Package: * \nPin: release a=buster-backports \nPin-Priority: 875\n\n')

        # Create apt.conf file
        fd, tmpaptconf = mkstemp(dir='/tmp/', prefix='apt.conf_')
        with os.fdopen(fd, 'w') as f:
            f.write('APT::Acquire::Retries=20;\n')

        self.remote_executor.get_fileput(self.hosts,
                                         [tmpsource, tmppref, tmpaptconf],
                                         remote_location='/etc/apt/').run()
        cmd = 'cd /etc/apt && ' + \
            'mv ' + tmpsource.split('/')[-1] + ' sources.list &&' + \
            'mv ' + tmppref.split('/')[-1] + ' preferences &&' + \
            'mv ' + tmpaptconf.split('/')[-1] + ' apt.conf'
        execute_cmd(cmd, self.hosts)
        Local('rm ' + tmpsource + ' ' + tmppref + ' ' + tmpaptconf).run()

        self._upgrade_hosts()

    def _install_packages(self, packages):
        cmd = 'export DEBIAN_MASTER=noninteractive ; apt-get update && apt-get ' + \
            'install -y --force-yes --no-install-recommends ' + packages
        # cmd = 'export DEBIAN_MASTER=noninteractive ; apt-get update && apt-get install -y --force-yes ' +\
        #     '-o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -t ' % self.packages
        execute_cmd(cmd, self.hosts)

    def _install_libvirt(self):
        """Installation of required packages on the hosts"""
        base_packages = 'uuid-runtime bash-completion taktuk locate htop init-system-helpers netcat-traditional'
        logger.info('Installing base packages: \n%s' % base_packages)
        self._install_packages(base_packages)

        libvirt_packages = 'libvirt-daemon-system libvirt-dev libvirt-clients virtinst python2.7 python-pycurl python-libxml2 qemu-kvm nmap libgmp10'
        logger.info('Installing libvirt packages \n%s' % libvirt_packages)
        self._install_packages(libvirt_packages)

    def _get_bridge(self, hosts):
        """ """
        logger.info('Retrieving bridge on hosts %s' %
                    ", ".join([host for host in hosts]))
        cmd = "brctl show |grep -v 'bridge name' | awk '{ print $1 }' |head -1"
        self.error_hosts, bridge_exists = execute_cmd(
            cmd, hosts, get_run_result=True)
        # bridge_exists.nolog_exit_code = True
        # bridge_exists.run()
        hosts_br = {}
        for p in bridge_exists.processes:
            stdout = p.stdout.strip()
            if len(stdout) == 0:
                hosts_br[p.host] = None
            else:
                hosts_br[p.host] = stdout
        return hosts_br

    def _enable_bridge(self, name='br0'):
        """We need a bridge to have automatic DHCP configuration for the VM."""
        logger.info('Configuring the bridge')
        hosts_br = self._get_bridge(self.hosts)
        nobr_hosts = []
        for host, br in hosts_br.iteritems():
            if br is None:
                logger.info('No bridge on host %s' % host)
                nobr_hosts.append(host)
            elif br != name:
                logger.info('Wrong bridge on host %s, destroying it' % host)
                self.error_hosts = execute_cmd(
                    'ip link set ' + br + ' down ; brctl delbr ' + br, host)
                nobr_hosts.append(host)
            else:
                logger.info('Bridge %s is present on host %s' % 'name'), host

        nobr_hosts = map(lambda x: x.address if isinstance(
            x, Host) else x, nobr_hosts)

        if len(nobr_hosts) > 0:
            logger.info('Creating bridge on %s' % nobr_hosts)
            # 'ifdown $br_if ; \n' + \
            # 'sed -i "s/$br_if inet dhcp/$br_if inet manual/g" /etc/network/interfaces ; \n' + \
            # 'sed -i "s/auto $br_if//g" /etc/network/interfaces ; \n' + \
            script = 'export br_if=`ip route |grep default |cut -f 5 -d " "`; \n' + \
                'export ip_df=`ip route |grep default |cut -f 3 -d " "`; \n' + \
                'export ip_net=`ip route | grep link | grep $br_if | grep -v ' + name + '| cut -f 1 -d " "`; \n' +\
                'echo " " >> /etc/network/interfaces ; \n' + \
                'echo "auto ' + name + '" >> /etc/network/interfaces ; \n' + \
                'echo "iface ' + name + ' inet dhcp" >> /etc/network/interfaces ; \n' + \
                'echo "  bridge_ports $br_if" >> /etc/network/interfaces ; \n' + \
                'echo "  bridge_stp off" >> /etc/network/interfaces ; \n' + \
                'echo "  bridge_maxwait 0" >> /etc/network/interfaces ; \n' + \
                'echo "  bridge_fd 0" >> /etc/network/interfaces ; \n' + \
                'ifup ' + name + ' ; \n' + \
                'ip route delete default ; \n' + \
                'ip route delete $ip_net dev $br_if ; \n' + \
                'ip route add default via $ip_df dev br0 ; \n' + \
                'sed -i "s/$br_if inet dhcp/$br_if inet manual/g" /etc/network/interfaces ; \n' + \
                'sed -i "s/auto $br_if//g" /etc/network/interfaces ; \n' + \
                'ifconfig $br_if 0.0.0.0'
            fd, br_script = mkstemp(dir='/tmp/', prefix='create_br_')
            with os.fdopen(fd, 'w') as f:
                f.write(script)

            self.remote_executor.get_fileput(nobr_hosts, [br_script]).run()
            self.error_hosts = execute_cmd(
                'nohup sh ' + br_script.split('/')[-1], nobr_hosts)

            logger.info('Waiting for network restart')
            if_up = False
            nmap_tries = 0
            while (not if_up) and nmap_tries < 20:
                sleep(20)
                nmap_tries += 1
                nmap = Process('nmap ' +
                               ' '.join([host for host in nobr_hosts]) +
                               ' -p 22').run()
                for line in nmap.stdout.split('\n'):
                    if 'Nmap done' in line:
                        if_up = line.split()[2] == line.split()[5].replace('(',
                                                                           '')
            logger.info('Network has been restarted')
        logger.info('All hosts have the bridge %s' % name)

    def _libvirt_check_service(self):
        """ """
        logger.detail('Checking libvirt service name')
        cmd = "if [ ! -e /etc/init.d/libvirtd ]; " + \
            "  then if [ -e /etc/init.d/libvirt-bin ]; " + \
            "       then ln -s /etc/init.d/libvirt-bin /etc/init.d/libvirtd; " + \
            "       else echo 1; " + \
            "        fi; " + \
            "else echo 0; fi"
        self.error_hosts = execute_cmd(cmd, self.hosts)

    def _libvirt_uniquify(self):
        logger.detail('Making libvirt host unique')
        cmd = 'uuid=`uuidgen` ' + \
            '&& sed -i "s/.*host_uuid.*/host_uuid=\\"${uuid}\\"/g" ' + \
            '/etc/libvirt/libvirtd.conf ' + \
            '&& service libvirtd restart'
        logger.debug(cmd)
        self.error_hosts = execute_cmd(cmd, self.hosts)

    def _libvirt_bridged_network(self, bridge):
        logger.detail('Configuring libvirt network')
        # Creating an XML file describing the network
        root = Element('network')
        name = SubElement(root, 'name')
        name.text = 'default'
        SubElement(root, 'forward', attrib={'mode': 'bridge'})
        SubElement(root, 'bridge', attrib={'name': bridge})
        fd, network_xml = mkstemp(dir='/tmp/', prefix='create_br_')
        with os.fdopen(fd, 'w') as f:
            # f.write(prettify(root))
            f.write(root)
        logger.debug('Destroying existing network')
        self.error_hosts = execute_cmd('virsh net-destroy default; ' +
                                       'virsh net-undefine default',
                                       self.hosts)
        put = self.remote_executor.get_fileput(
            self.hosts, [network_xml], remote_location='/root/')
        self.error_hosts = execute_cmd(
            'virsh net-define /root/' +
            network_xml.split('/')[-1] + ' ; ' +
            'virsh net-start default; virsh net-autostart default;',
            self.hosts)

    def _configure_libvirt(self, bridge='br0', libvirt_conf=None):
        """Enable a bridge if needed on the remote hosts, configure libvirt
        with a bridged network for the virtual machines, and restart service.
        """
        # Post configuration to load KVM
        self.error_hosts = execute_cmd('modprobe kvm; modprobe kvm-intel; modprobe kvm-amd ; ' +
                                       'chown root:kvm /dev/kvm ;', self.hosts)

        print 'Starting configuring libvirt'
        self._enable_bridge()
        self._libvirt_check_service()
        self._libvirt_uniquify()
        self._libvirt_bridged_network(bridge)
        logger.info('Restarting %s', 'libvirt')
        self.error_hosts = execute_cmd('service libvirtd restart', self.hosts)

    def config_hosts(self):
        logger.info('Configuring %s hosts' % len(self.hosts))
        self._config_dependencies()
        self._install_libvirt()
        self._configure_libvirt()
