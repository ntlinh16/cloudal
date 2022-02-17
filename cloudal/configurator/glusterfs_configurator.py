from cloudal.utils import get_logger, execute_cmd
from cloudal.configurator import packages_configurator

logger = get_logger()


class glusterfs_configurator(object): 
    def install_glusterfs(self, hosts):
        logger.info('Installing GlusterFS')
        configurator = packages_configurator()
        configurator.install_packages(["glusterfs-server"], hosts)
        
        cmd = 'systemctl start glusterd'
        execute_cmd(cmd, hosts)

        gluster_configuration = list()
        for index, host in enumerate(hosts):
            cmd = "hostname -I | awk '{print $1}'"
            _, r = execute_cmd(cmd, host)
            host_ip = r.processes[0].stdout.strip()
            gluster_configuration.append("%s gluster-%s.%s.local gluster-%s " % (host_ip, index, host, index))
        gluster_configuration = "\n".join(gluster_configuration)
        cmd = "echo '%s' >> /etc/hosts" % gluster_configuration
        execute_cmd(cmd, hosts)

        for index, _ in enumerate(hosts):
            cmd = 'gluster peer probe gluster-%s' % index
            execute_cmd(cmd, hosts[0])

    def deploy_glusterfs(self, gluster_hosts, indices, gluster_mountpoint, gluster_volume_name):
        indices = sorted(indices)
        hosts = [host for index,host in enumerate(gluster_hosts) if index in indices]
        logger.info('Creating volumes on %s hosts: \n %s' % (len(hosts), hosts))
        volume_path = '/tmp/glusterd/volume'
        cmd = 'mkdir -p %s' % volume_path
        execute_cmd(cmd, hosts)

        volume_params = list()
        for index, host in zip(indices, hosts):
            volume_params.append("gluster-%s.%s.local:%s" % (index, host, volume_path))
        volume_params = " ".join(volume_params)

        cmd ='gluster --mode=script volume create %s replica 3 %s force' % (gluster_volume_name, volume_params)
        execute_cmd(cmd, hosts[0])
        
        logger.info('Starting volumes on hosts')
        cmd = 'gluster --mode=script volume start %s' % gluster_volume_name
        execute_cmd(cmd, hosts[0])

        cmd = ''' mkdir -p %s && 
                  mount -t glusterfs gluster-0:%s %s''' % (gluster_mountpoint, gluster_volume_name, gluster_mountpoint)
        execute_cmd(cmd, hosts)
        logger.info("Finish deploying glusterfs")
        return True, hosts