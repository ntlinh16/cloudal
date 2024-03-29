import os
import traceback

from time import sleep

from cloudal.utils import get_logger, execute_cmd, parse_config_file, getput_file
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import kubernetes_configurator, k8s_resources_configurator, packages_configurator

from execo_g5k import oardel
from kubernetes import config
import yaml

logger = get_logger()


class elmerfs_g5k(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(elmerfs_g5k, self).__init__()
        self.args_parser.add_argument("--kube-master", dest="kube_master",
                                      help="name of kube master node",
                                      default=None,
                                      type=str)
        self.args_parser.add_argument("--monitoring", dest="monitoring",
                                      help="deploy Grafana and Prometheus for monitoring",
                                      action="store_true")

    def deploy_monitoring(self, kube_master, kube_namespace):
        logger.info("Deploying monitoring system")
        monitoring_k8s_dir = self.configs['exp_env']['monitoring_yaml_path']

        logger.info("Deleting old deployment")
        cmd = "rm -rf /root/antidote_stats"
        execute_cmd(cmd, kube_master)

        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()

        cmd = "git clone https://github.com/AntidoteDB/antidote_stats.git"
        execute_cmd(cmd, kube_master)
        logger.info("Setting to allow pods created on kube_master")
        cmd = "kubectl taint nodes --all node-role.kubernetes.io/master-"
        execute_cmd(cmd, kube_master, is_continue=True)

        pods = configurator.get_k8s_resources_name(resource='pod',
                                                   label_selectors='app=antidote',
                                                   kube_namespace=kube_namespace)
        antidote_info = ["%s.antidote:3001" % pod for pod in pods]

        logger.debug('Modify the prometheus.yml file with antidote instances info')
        file_path = os.path.join(monitoring_k8s_dir, 'prometheus.yml.template')
        with open(file_path) as f:
            doc = f.read().replace('antidotedc_info', '%s' % antidote_info)
        prometheus_configmap_file = os.path.join(monitoring_k8s_dir, 'prometheus.yml')
        with open(prometheus_configmap_file, 'w') as f:
            f.write(doc)
        configurator.create_configmap(file=prometheus_configmap_file,
                                      namespace=kube_namespace,
                                      configmap_name='prometheus-configmap')
        logger.debug('Modify the deploy_prometheus.yaml file with kube_master info')
        kube_master_info = configurator.get_k8s_resources(resource='node',
                                                          label_selectors='kubernetes.io/hostname=%s' % kube_master)
        for item in kube_master_info.items[0].status.addresses:
            if item.type == 'InternalIP':
                kube_master_ip = item.address
        file_path = os.path.join(monitoring_k8s_dir, 'deploy_prometheus.yaml.template')
        with open(file_path) as f:
            doc = f.read().replace('kube_master_ip', '%s' % kube_master_ip)
            doc = doc.replace("kube_master_hostname", '%s' % kube_master)
        prometheus_deploy_file = os.path.join(monitoring_k8s_dir, 'deploy_prometheus.yaml')
        with open(prometheus_deploy_file, 'w') as f:
            f.write(doc)

        logger.info("Starting Prometheus service")
        configurator.deploy_k8s_resources(files=[prometheus_deploy_file], namespace=kube_namespace)
        logger.info('Waiting until Prometheus instance is up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=prometheus",
                                        kube_namespace=kube_namespace)

        logger.debug('Modify the deploy_grafana.yaml file with kube_master info')
        file_path = os.path.join(monitoring_k8s_dir, 'deploy_grafana.yaml.template')
        with open(file_path) as f:
            doc = f.read().replace('kube_master_ip', '%s' % kube_master_ip)
            doc = doc.replace("kube_master_hostname", '%s' % kube_master)
        grafana_deploy_file = os.path.join(monitoring_k8s_dir, 'deploy_grafana.yaml')
        with open(grafana_deploy_file, 'w') as f:
            f.write(doc)

        file = '/root/antidote_stats/monitoring/grafana-config/provisioning/datasources/all.yml'
        cmd = """ sed -i "s/localhost/%s/" %s """ % (kube_master_ip, file)
        execute_cmd(cmd, kube_master)

        logger.info("Starting Grafana service")
        configurator.deploy_k8s_resources(files=[grafana_deploy_file], namespace=kube_namespace)
        logger.info('Waiting until Grafana instance is up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=grafana",
                                        kube_namespace=kube_namespace)
        logger.info("Finish deploying monitoring system")
        logger.info("Connect to Grafana at: http://%s:3000" % kube_master_ip)
        logger.info("Connect to Prometheus at: http://%s:9090" % kube_master_ip)

    def deploy_elmerfs(self, kube_master, kube_namespace, elmerfs_hosts):
        logger.info("Starting deploying elmerfs on hosts")

        configurator = packages_configurator()
        configurator.install_packages(['libfuse2', 'wget', 'jq'], elmerfs_hosts)

        elmerfs_repo = self.configs['exp_env']['elmerfs_repo']
        elmerfs_version = self.configs['exp_env']['elmerfs_version']
        if elmerfs_repo is None:
            elmerfs_repo = 'https://github.com/scality/elmerfs'
        if elmerfs_version is None:
            elmerfs_version = 'latest'

        logger.info('Killing elmerfs process if it is running')
        for host in elmerfs_hosts:
            cmd = "ps aux | grep elmerfs | awk '{print$2}'"
            _, r = execute_cmd(cmd, host)
            pids = r.processes[0].stdout.strip().split('\r\n')
            if len(pids) >= 3:
                cmd = "kill %s && umount /tmp/dc-$(hostname)" % pids[0]
                execute_cmd(cmd, host)

        logger.info("Downloading elmerfs project from the repo")
        cmd = '''curl \
                -H "Accept: application/vnd.github.v3+json" \
                https://api.github.com/repos/scality/elmerfs/releases/%s | jq ".tag_name" \
                | xargs -I tag_name git clone https://github.com/scality/elmerfs.git --branch tag_name --single-branch /tmp/elmerfs_repo ''' % elmerfs_version
        execute_cmd(cmd, kube_master)

        cmd = "cd /tmp/elmerfs_repo \
               && git submodule update --init --recursive"
        execute_cmd(cmd, kube_master)

        cmd = '''cat <<EOF | sudo tee /tmp/elmerfs_repo/Dockerfile
        FROM rust:1.47
        RUN mkdir  /elmerfs
        WORKDIR /elmerfs
        COPY . .
        RUN apt-get update \
            && apt-get -y install libfuse-dev
        RUN cargo build --release
        CMD ["/bin/bash"]
        '''
        execute_cmd(cmd, kube_master)

        logger.info("Building elmerfs")
        cmd = " cd /tmp/elmerfs_repo/ \
                && docker build -t elmerfs ."
        execute_cmd(cmd, kube_master)

        cmd = "docker run --name elmerfs elmerfs \
                && docker cp -L elmerfs:/elmerfs/target/release/main /tmp/elmerfs \
                && docker rm elmerfs"
        execute_cmd(cmd, kube_master)

        getput_file(hosts=[kube_master], file_paths=['/tmp/elmerfs'],
                    dest_location='/tmp', action='get')
        elmerfs_file_path = '/tmp/elmerfs'

        logger.info("Uploading elmerfs binary file from local to %s elmerfs hosts" %
                    len(elmerfs_hosts))
        getput_file(hosts=elmerfs_hosts, file_paths=[
                    elmerfs_file_path], dest_location='/tmp', action='put')
        cmd = "chmod +x /tmp/elmerfs \
               && mkdir -p /tmp/dc-$(hostname)"
        execute_cmd(cmd, elmerfs_hosts)

        logger.debug('Getting IP of antidoteDB instances on nodes')
        antidote_ips = dict()
        configurator = k8s_resources_configurator()
        pod_list = configurator.get_k8s_resources(resource='pod',
                                                  label_selectors='app=antidote',
                                                  kube_namespace=kube_namespace)
        for pod in pod_list.items:
            node = pod.spec.node_name
            if node not in antidote_ips:
                antidote_ips[node] = list()
            antidote_ips[node].append(pod.status.pod_ip)

        for host in elmerfs_hosts:
            antidote_options = ["--antidote=%s:8087" % ip for ip in antidote_ips[host]]

            cmd = "RUST_BACKTRACE=1 RUST_LOG=debug nohup /tmp/elmerfs %s --mount=/tmp/dc-$(hostname) --no-locks > /tmp/elmer.log 2>&1" % " ".join(
                antidote_options)
            logger.info("Starting elmerfs on %s with cmd: %s" % (host, cmd))
            execute_cmd(cmd, host, mode='start')
            sleep(5)
        logger.info('Finish deploying elmerfs\n')

    def deploy_antidote(self, kube_namespace):
        logger.info('Starting deploying Antidote cluster')
        antidote_k8s_dir = self.configs['exp_env']['antidote_yaml_path']

        logger.info('Deleting all k8s resource in namespace %s' % kube_namespace)
        configurator = k8s_resources_configurator()
        configurator.delete_namespace(kube_namespace)
        configurator.create_namespace(kube_namespace)

        logger.debug('Delete old createDC, connectDCs_antidote and exposer-service files if exists')
        for filename in os.listdir(antidote_k8s_dir):
            if filename.startswith('createDC_') or filename.startswith('statefulSet_') or filename.startswith('exposer-service_') or filename.startswith('connectDCs_antidote'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(antidote_k8s_dir, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        logger.debug('Modify the statefulSet file')
        file_path = os.path.join(antidote_k8s_dir, 'statefulSet.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        statefulSet_files = [os.path.join(antidote_k8s_dir, 'headlessService.yaml')]
        for cluster in self.configs['exp_env']['antidote_clusters']:
            doc['spec']['replicas'] = self.configs['exp_env']['n_antidotedb_per_dc']
            doc['metadata']['name'] = 'antidote-%s' % cluster
            doc['spec']['template']['spec']['nodeSelector'] = {
                'service_g5k': 'antidote', 'cluster_g5k': '%s' % cluster}
            file_path = os.path.join(antidote_k8s_dir, 'statefulSet_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            statefulSet_files.append(file_path)

        logger.info("Starting AntidoteDB instances")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=statefulSet_files, namespace=kube_namespace)

        logger.info('Waiting until all Antidote instances are up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=antidote",
                                        kube_namespace=kube_namespace)

        logger.debug('Creating createDc.yaml file for each Antidote DC')
        dcs = dict()
        for cluster in self.configs['exp_env']['antidote_clusters']:
            dcs[cluster] = list()
        antidotes_list = configurator.get_k8s_resources_name(resource='pod',
                                                             label_selectors='app=antidote',
                                                             kube_namespace=kube_namespace)
        for antidote in antidotes_list:
            cluster = antidote.split('-')[1].strip()
            dcs[cluster].append(antidote.strip())

        file_path = os.path.join(antidote_k8s_dir, 'createDC.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)

        antidote_masters = list()
        createdc_files = list()
        for cluster, pods in dcs.items():
            doc['spec']['template']['spec']['containers'][0]['args'] = ['--createDc',
                                                                        '%s.antidote:8087' % pods[0]] + ['antidote@%s.antidote' % pod for pod in pods]
            doc['metadata']['name'] = 'createdc-%s' % cluster
            antidote_masters.append('%s.antidote:8087' % pods[0])
            file_path = os.path.join(antidote_k8s_dir, 'createDC_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            createdc_files.append(file_path)

        logger.debug('Creating exposer-service.yaml files')
        file_path = os.path.join(antidote_k8s_dir, 'exposer-service.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        for cluster, pods in dcs.items():
            doc['spec']['selector']['statefulset.kubernetes.io/pod-name'] = pods[0]
            doc['metadata']['name'] = 'antidote-exposer-%s' % cluster
            file_path = os.path.join(antidote_k8s_dir, 'exposer-service_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
                createdc_files.append(file_path)

        logger.info("Creating Antidote DCs and exposing services")
        configurator.deploy_k8s_resources(files=createdc_files, namespace=kube_namespace)

        logger.info('Waiting until all antidote DCs are created')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors="app=antidote",
                                        kube_namespace=kube_namespace)

        logger.debug('Creating connectDCs_antidote.yaml to connect all Antidote DCs')
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = [
            '--connectDcs'] + antidote_masters
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs_antidote.yaml')
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Connecting all Antidote DCs into a cluster")
        configurator.deploy_k8s_resources(files=[file_path], namespace=kube_namespace)

        logger.info('Waiting until connecting all Antidote DCs')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors="app=antidote",
                                        kube_namespace=kube_namespace)

        logger.info('Finish deploying the Antidote cluster\n')

    def _set_kube_workers_label(self, kube_workers):
        logger.info('Set labels for all kubernetes workers')
        configurator = k8s_resources_configurator()
        for host in kube_workers:
            cluster = host.split('-')[0]
            labels = 'cluster_g5k=%s,service_g5k=antidote' % cluster
            configurator.set_labels_node(host, labels)

    def _setup_g5k_kube_volumes(self, kube_workers, n_pv=3):

        logger.info("Setting volumes on %s kubernetes workers" % len(kube_workers))
        cmd = '''umount /dev/sda5;
                 mount -t ext4 /dev/sda5 /tmp'''
        execute_cmd(cmd, kube_workers)
        logger.debug('Create n_pv partitions on the physical disk to make a PV can be shared')
        cmd = '''for i in $(seq 1 %s); do
                     mkdir -p /tmp/pv/vol${i}
                     mkdir -p /mnt/disks/vol${i}
                     mount --bind /tmp/pv/vol${i} /mnt/disks/vol${i}
                 done''' % n_pv
        execute_cmd(cmd, kube_workers)

        logger.info("Creating local persistance volumes on Kubernetes cluster")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        antidote_k8s_dir = self.configs['exp_env']['antidote_yaml_path']
        deploy_files = [os.path.join(antidote_k8s_dir, 'local_persistentvolume.yaml'),
                        os.path.join(antidote_k8s_dir, 'storageClass.yaml')]
        configurator.deploy_k8s_resources(files=deploy_files)

        logger.info('Waiting for setting local persistance volumes')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app.kubernetes.io/instance=local-volume-provisioner")

    def _get_credential(self, kube_master):
        home = os.path.expanduser('~')
        kube_dir = os.path.join(home, '.kube')
        if not os.path.exists(kube_dir):
            os.mkdir(kube_dir)
        getput_file(hosts=[kube_master], file_paths=['~/.kube/config'],
                    dest_location=kube_dir, action='get')
        kube_config_file = os.path.join(kube_dir, 'config')
        config.load_kube_config(config_file=kube_config_file)
        logger.info('Kubernetes config file is stored at: %s' % kube_config_file)

    def config_kube(self, kube_master, antidote_hosts, kube_namespace):
        logger.info('Starting configuring a Kubernetes cluster')
        logger.debug("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(hosts=self.hosts, kube_master=kube_master)
        configurator.deploy_kubernetes_cluster()

        self._get_credential(kube_master)

        logger.info('Create k8s namespace "%s" for this experiment' % kube_namespace)
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.create_namespace(kube_namespace)

        kube_workers = [host for host in antidote_hosts if host != kube_master]

        self._setup_g5k_kube_volumes(kube_workers, n_pv=3)

        self._set_kube_workers_label(kube_workers)

        logger.info("Finish configuring the Kubernetes cluster\n")

    def config_host(self, kube_master_site, kube_namespace):
        kube_master = self.args.kube_master

        if self.args.kube_master is None:
            antidote_hosts = list()
            for cluster in self.configs['exp_env']['antidote_clusters']:
                if cluster == self.configs['exp_env']['kube_master_site']:
                    antidote_hosts += [host
                                       for host in self.hosts if host.startswith(cluster)][0:self.configs['exp_env']['n_antidotedb_per_dc']+1]
                else:
                    antidote_hosts += [host
                                       for host in self.hosts if host.startswith(cluster)][0:self.configs['exp_env']['n_antidotedb_per_dc']]

            for host in antidote_hosts:
                if host.startswith(kube_master_site):
                    kube_master = host
                    break
            elmerfs_hosts = antidote_hosts
            elmerfs_hosts.remove(kube_master)

            self.config_kube(kube_master, antidote_hosts, kube_namespace)

        else:
            logger.info('Kubernetes master: %s' % kube_master)
            self._get_credential(kube_master)

            configurator = k8s_resources_configurator()
            antidote_hosts = configurator.get_k8s_resources_name(resource='node',
                                                                 label_selectors='service_g5k=antidote')
            elmerfs_hosts = antidote_hosts

        self.deploy_antidote(kube_namespace)
        self.deploy_elmerfs(kube_master, kube_namespace, elmerfs_hosts)

        if self.args.monitoring is not None:
            self.deploy_monitoring(kube_master, kube_namespace)

    def setup_env(self, kube_master_site, kube_namespace):
        logger.info("Starting configuring the experiment environment")
        logger.debug("Init provisioner: g5k_provisioner")
        provisioner = g5k_provisioner(configs=self.configs,
                                      keep_alive=self.args.keep_alive,
                                      out_of_chart=self.args.out_of_chart,
                                      oar_job_ids=self.args.oar_job_ids,
                                      no_deploy_os=self.args.no_deploy_os,
                                      is_reservation=self.args.is_reservation,
                                      job_name="cloudal")

        provisioner.provisioning()
        self.hosts = provisioner.hosts
        self.oar_result = provisioner.oar_result

        logger.info("Starting configuring nodes")
        self.config_host(kube_master_site, kube_namespace)

        logger.info("Finish configuring nodes\n")

    def create_configs(self):
        logger.debug('Get the k8s master node')
        kube_master_site = self.configs['exp_env']['kube_master_site']
        if kube_master_site is None or kube_master_site not in self.configs['exp_env']['antidote_clusters']:
            kube_master_site = self.configs['exp_env']['antidote_clusters'][0]

        # calculating the total number of hosts for each cluster
        clusters = dict()
        for cluster in self.configs['exp_env']['antidote_clusters']:
            if cluster == kube_master_site:
                clusters[cluster] = clusters.get(
                    cluster, 0) + self.configs['exp_env']['n_antidotedb_per_dc'] + 1
            else:
                clusters[cluster] = clusters.get(
                    cluster, 0) + self.configs['exp_env']['n_antidotedb_per_dc']

        self.configs['clusters'] = [{'cluster': cluster, 'n_nodes': n_nodes}
                                    for cluster, n_nodes in clusters.items()]

        return kube_master_site

    def run(self):
        logger.debug('Parse and convert configs for G5K provisioner')
        self.configs = parse_config_file(self.args.config_file_path)
        kube_master_site = self.create_configs()

        logger.info('''Your topology:
                        Antidote DCs: %s
                        n_antidotedb_per_DC: %s ''' % (
            len(self.configs['exp_env']['antidote_clusters']),
            self.configs['exp_env']['n_antidotedb_per_dc'])
        )

        kube_namespace = 'elmerfs-exp'
        self.setup_env(kube_master_site, kube_namespace)


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = elmerfs_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
