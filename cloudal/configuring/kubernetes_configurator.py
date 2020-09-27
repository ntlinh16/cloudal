
from cloudal.utils import get_logger, execute_cmd, install_packages_on_debian


logger = get_logger()


class kubernetes_configurator(object):
    """
    """

    def __init__(self, hosts):
        self.hosts = hosts

    def _install_kubeadm(self):
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

        logger.debug('Installing kubeadm')
        install_packages_on_debian(['apt-transport-https', 'curl'], self.hosts)

        cmd = 'curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -'
        execute_cmd(cmd, self.hosts)

        cmd = '''cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
                deb https://apt.kubernetes.io/ kubernetes-xenial main'''
        execute_cmd(cmd, self.hosts)

        install_packages_on_debian(['kubelet', 'kubeadm', 'kubectl'], self.hosts)

    def deploy_kubernetes_cluster(self):
        self._install_kubeadm()

        kube_master = self.hosts[0]
        kube_workers = self.hosts[1:]

        logger.debug('Configuring kubeadm on master')
        cmd = 'kubeadm init'
        execute_cmd(cmd, [kube_master])

        cmd = '''mkdir -p $HOME/.kube
                 cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
                 chown $(id -u):$(id -g) $HOME/.kube/config'''
        execute_cmd(cmd, [kube_master])

        cmd = 'kubeadm token create --print-join-command'
        _, result = execute_cmd(cmd, [kube_master])

        logger.debug('Adding %s kube workers' % len(kube_workers))
        cmd = 'kubeadm join' + result.processes[0].stdout.split('kubeadm join')[-1]
        execute_cmd(cmd.strip(), kube_workers)

        return kube_master, kube_workers
