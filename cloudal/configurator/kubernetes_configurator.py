from cloudal.utils import get_logger, execute_cmd
from cloudal.configurator import docker_configurator, packages_configurator


logger = get_logger()


class kubernetes_configurator(object):
    """
    """

    def __init__(self, hosts, kube_master=None):
        self.hosts = hosts
        self.kube_master = kube_master

    def _install_kubeadm(self):
        logger.info('Starting installing kubeadm on %s nodes' % len(self.hosts))

        logger.debug('Turning off Firewall on hosts')
        cmd = '''cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
                 net.bridge.bridge-nf-call-ip6tables = 1
                 net.bridge.bridge-nf-call-iptables = 1'''
        execute_cmd(cmd, self.hosts)
        cmd = 'sudo sysctl --system'
        execute_cmd(cmd, self.hosts)

        logger.debug('Turning off swap on hosts')
        cmd = 'swapoff -a'
        execute_cmd(cmd, self.hosts)

        logger.debug('Installing kubeadm kubelet kubectl')
        configurator = packages_configurator()
        configurator.install_packages(['apt-transport-https', 'curl'], self.hosts)

        cmd = 'curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -'
        execute_cmd(cmd, self.hosts)

        cmd = '''cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
                deb https://apt.kubernetes.io/ kubernetes-xenial main'''
        execute_cmd(cmd, self.hosts)

        configurator.install_packages(['kubelet', 'kubeadm', 'kubectl'], self.hosts)

    def deploy_kubernetes_cluster(self):
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        self._install_kubeadm()
        if self.kube_master is None:
            self.kube_master = self.hosts[0]
            kube_workers = self.hosts[1:]
        else:
            kube_workers = [host for host in self.hosts if host != self.kube_master]

        logger.info('Initializing kubeadm on master')
        cmd = 'kubeadm init --pod-network-cidr=10.244.0.0/16'
        execute_cmd(cmd, [self.kube_master])

        cmd = '''mkdir -p $HOME/.kube
                 cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
                 chown $(id -u):$(id -g) $HOME/.kube/config'''
        execute_cmd(cmd, [self.kube_master])

        cmd = 'kubectl apply -f https://github.com/coreos/flannel/raw/master/Documentation/kube-flannel.yml'
        execute_cmd(cmd, [self.kube_master])

        cmd = 'kubeadm token create --print-join-command'
        _, result = execute_cmd(cmd, [self.kube_master])

        logger.debug('Adding %s kube workers' % len(kube_workers))
        cmd = 'kubeadm join' + \
            result.processes[0].stdout.split('kubeadm join')[-1]
        execute_cmd(cmd.strip(), kube_workers)

        logger.info('Deploying Kubernetes cluster successfully')
        logger.info('Kubernetes master: %s' % self.kube_master)

        return self.kube_master, kube_workers
