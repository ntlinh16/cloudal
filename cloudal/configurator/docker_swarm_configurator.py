from cloudal.utils import get_logger, execute_cmd
from cloudal.configurator import docker_configurator


logger = get_logger()


class docker_swarm_configurator(object):
    """
    """

    def __init__(self, hosts, ds_manager=None):
        self.hosts = hosts
        self.ds_maneger = ds_manager

    def deploy_docker_swarm_cluster(self):
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        if self.ds_maneger is None:
            self.ds_maneger = self.hosts[0]
            ds_workers = self.hosts[1:]
        else:
            ds_workers = [host for host in self.hosts if host != self.ds_maneger]

        logger.info('Getting IP of docker swarm maneger')
        cmd = "hostname -I"
        _, r = execute_cmd(cmd, [self.ds_maneger])
        ds_maneger_ip = r.processes[0].stdout.strip().split(' ')[0]

        logger.info('Creating a new swarm')
        cmd = 'docker swarm init --advertise-addr %s' % ds_maneger_ip
        execute_cmd(cmd, [self.ds_maneger])

        logger.info('Joining all docker swarm worker')
        cmd = 'docker swarm join-token worker | grep "docker swarm join"'
        _, r = execute_cmd(cmd, [self.ds_maneger])

        cmd = r.processes[0].stdout.strip()
        execute_cmd(cmd, ds_workers)

        logger.info('Finish deploying docker swarm cluster')
        logger.info('Docker swarm maneger: %s (%s)' % (self.ds_maneger, ds_maneger_ip))

        return self.ds_maneger, ds_workers
