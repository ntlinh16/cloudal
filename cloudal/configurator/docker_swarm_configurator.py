from cloudal.utils import get_logger, execute_cmd
from cloudal.configurator import docker_configurator


logger = get_logger()


class docker_swarm_configurator(object):
    """
    """

    def __init__(self, hosts, ds_manager=None):
        self.hosts = hosts
        self.ds_manager = ds_manager

    def deploy_docker_swarm_cluster(self):
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        if self.ds_manager is None:
            self.ds_manager = self.hosts[0]
            ds_workers = self.hosts[1:]
        else:
            ds_workers = [host for host in self.hosts if host != self.ds_manager]

        logger.info('Getting IP of docker swarm manager')
        cmd = "hostname -I"
        _, r = execute_cmd(cmd, [self.ds_manager])
        ds_manager_ip = r.processes[0].stdout.strip().split(' ')[0]

        logger.info('Creating a new swarm')
        cmd = 'docker swarm init --advertise-addr %s' % ds_manager_ip
        execute_cmd(cmd, [self.ds_manager])

        logger.info('Joining all docker swarm worker')
        cmd = 'docker swarm join-token worker | grep "docker swarm join"'
        _, r = execute_cmd(cmd, [self.ds_manager])

        cmd = r.processes[0].stdout.strip()
        execute_cmd(cmd, ds_workers)

        logger.info('Finish deploying docker swarm cluster')
        logger.info('Docker swarm manager: %s (%s)' % (self.ds_manager, ds_manager_ip))

        return self.ds_manager, ds_workers
