import os
import traceback

from time import sleep

from cloudal.utils import get_logger, execute_cmd, parse_config_file, getput_file, install_packages_on_debian
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import kubernetes_configurator, docker_configurator, k8s_resources_configurator

from execo_g5k import oardel
from kubernetes import config
import yaml

logger = get_logger()


class elmerfs_exp(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(elmerfs_exp, self).__init__()
        self.args_parser.add_argument("--kube-master", dest="kube_master",
                                      help="name of kube master node",
                                      default=None,
                                      type=str)

    def deploy_elmerfs(self, kube_master, elmerfs_hosts):
        logger.info("Deploying elmerfs on hosts")
        install_packages_on_debian(['libfuse2'], elmerfs_hosts)

        elmerfs_file_path = self.configs['exp_env']['elmerfs_file_path']

        if elmerfs_file_path is None:
            logger.debug("Buiding elmerfs project on kube_master node and then downloading to local machine")

            logger.info("Downloading elmerfs project")
            cmd = " rm -rf /tmp/elmerfs_repo \
                    && git clone https://github.com/scality/elmerfs.git /tmp/elmerfs_repo \
                    && cd /tmp/elmerfs_repo \
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

            getput_file(hosts=[kube_master], file_paths=['/tmp/elmerfs'], dest_location='/tmp', action='get')
            elmerfs_file_path = '/tmp/elmerfs'

        logger.info("Uploading elmerfs binary file from local to elmerfs hosts")
        getput_file(hosts=elmerfs_hosts, file_paths=[elmerfs_file_path], dest_location='/tmp', action='put')
        cmd = "chmod +x /tmp/elmerfs \
               && mkdir -p /tmp/dc-$(hostname)"
        execute_cmd(cmd, elmerfs_hosts)

        cmd = "kubectl get services | grep antidote-exposer | awk '{print $3}'"
        _, p = execute_cmd(cmd, kube_master)
        antidote_ips = p.processes[0].stdout.strip().split('\r\n')
        antidote_options = ["--antidote=%s:8087" % ip for ip in antidote_ips]

        logger.info("Starting elmerfs on elmerfs hosts: %s" % elmerfs_hosts)
        cmd = "/tmp/elmerfs %s --mount=/tmp/dc-$(hostname) --no-locks &" % " ".join(antidote_options)
        for host in elmerfs_hosts:
            execute_cmd(cmd, [host], mode='start')
            sleep(5)

    def config_antidote(self, kube_master):
        logger.info('Deleting all k8s resource in namespace %s' % self.kube_namespace)
        cmd = '''kubectl config set-context --current --namespace=default &&
                kubectl delete namespaces %s &&
                kubectl create namespace %s  &&
                kubectl config set-context --current --namespace=%s ''' % (self.kube_namespace, self.kube_namespace, self.kube_namespace)
        execute_cmd(cmd, kube_master)

        logger.info('Starting deploying Antidote cluster')
        antidote_k8s_dir = self.configs['exp_env']['antidote_yaml_path']

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
            doc['spec']['template']['spec']['nodeSelector'] = {'service_g5k': 'antidote', 'cluster_g5k': '%s' % cluster}
            file_path = os.path.join(antidote_k8s_dir, 'statefulSet_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            statefulSet_files.append(file_path)

        logger.info("Starting AntidoteDB instances")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=statefulSet_files, namespace=self.kube_namespace)

        logger.info('Waiting until all Antidote instances are up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=antidote",
                                        kube_master=kube_master,
                                        kube_namespace=self.kube_namespace)

        logger.debug('Creating createDc.yaml file for each Antidote DC')
        dcs = dict()
        for cluster in self.configs['exp_env']['antidote_clusters']:
            dcs[cluster] = list()
        cmd = """kubectl get pods -l "app=antidote" | tail -n +2 | awk '{print $1}'"""
        _, r = execute_cmd(cmd, kube_master)
        antidotes_list = r.processes[0].stdout.strip().split('\r\n')
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
        configurator.deploy_k8s_resources(files=createdc_files, namespace=self.kube_namespace)

        logger.info('Waiting until all antidote DCs are created')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors="app=antidote",
                                        kube_master=kube_master,
                                        kube_namespace=self.kube_namespace)

        logger.debug('Creating connectDCs_antidote.yaml to connect all Antidote DCs')
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = ['--connectDcs'] + antidote_masters
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs_antidote.yaml')
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Connecting all Antidote DCs into a cluster")
        configurator.deploy_k8s_resources(files=[file_path], namespace=self.kube_namespace)

        logger.info('Waiting until connecting all Antidote DCs')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors="app=antidote",
                                        kube_master=kube_master,
                                        kube_namespace=self.kube_namespace)

        logger.info('Finish deploying the Antidote cluster')

    def _set_label(self, host, labels, kube_master):
        cmd = 'kubectl label node %s %s' % (host, ' '.join(labels))
        execute_cmd(cmd, kube_master)

    def _set_kube_workers_label(self, kube_master, antidote_hosts):
        kube_workers = [host for host in antidote_hosts if host != kube_master]
        for host in kube_workers:
            cluster = host.split('-')[0]
            self._set_label(host=host,
                            labels=['cluster_g5k=%s' % cluster, 'service_g5k=antidote'],
                            kube_master=kube_master)

    def _setup_g5k_kube_volumes(self, kube_master, antidote_hosts, n_pv=3):
        kube_workers = [host for host in antidote_hosts if host != kube_master]
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
                                        label_selectors="app.kubernetes.io/instance=local-volume-provisioner",
                                        kube_master=kube_master)

    def _get_credential(self, kube_master):
        home = os.path.expanduser('~')
        kube_dir = os.path.join(home, '.kube')
        if not os.path.exists(kube_dir):
            os.mkdir(kube_dir)
        getput_file(hosts=[kube_master], file_paths=['~/.kube/config'], dest_location=kube_dir, action='get')
        kube_config_file = os.path.join(kube_dir, 'config')
        config.load_kube_config(config_file=kube_config_file)
        logger.info('Kubernetes config file is stored at: %s' % kube_config_file)

    def config_kube(self, kube_master, antidote_hosts):
        logger.debug("Init configurator: docker_configurator")
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        logger.debug("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(hosts=self.hosts, kube_master=kube_master)
        configurator.deploy_kubernetes_cluster()

        logger.info('Create k8s namespace "%s" for this experiment' % self.kube_namespace)
        cmd = "kubectl create namespace %s && kubectl config set-context --current --namespace=%s" % (
            self.kube_namespace, self.kube_namespace)
        execute_cmd(cmd, kube_master)

        self._get_credential(kube_master)

        self._setup_g5k_kube_volumes(kube_master, antidote_hosts, n_pv=3)

        logger.info('Set labels for all kuber workers')
        self._set_kube_workers_label(kube_master, antidote_hosts)

        logger.info("Finish deploying the Kubernetes cluster")

    def config_host(self, kube_master_site):

        self.kube_namespace = 'elmerfs-exp'

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
            elmerfs_hosts = [host for host in self.hosts if host not in antidote_hosts]

            for host in antidote_hosts:
                if host.startswith(kube_master_site):
                    kube_master = host
                    break

            self.config_kube(kube_master, antidote_hosts)
            self.config_antidote(kube_master)
            self.deploy_elmerfs(kube_master, elmerfs_hosts)
        else:
            logger.info('Kubernetes master: %s' % kube_master)
            self._get_credential(kube_master)
            # self.config_antidote(kube_master)
            cmd = "kubectl get nodes --show-labels | grep antidote | awk '{print$1}'"
            _, p = execute_cmd(cmd, kube_master)
            antidote_hosts = p.processes[0].stdout.strip().split('\r\n')
            elmerfs_hosts = [host for host in self.hosts if host not in antidote_hosts]
            elmerfs_hosts.remove(kube_master)
            self.deploy_elmerfs(kube_master, elmerfs_hosts)

    def setup_env(self, kube_master_site):
        logger.info("STARTING SETTING THE EXPERIMENT ENVIRONMENT")
        logger.info("STARTING PROVISIONING NODES")
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
        oar_job_ids = provisioner.oar_result
        logger.info("FINISH PROVISIONING NODES\n")

        logger.info("STARTING CONFIGURING NODES")
        self.config_host(kube_master_site)
        logger.info("FINISH CONFIGURING NODES")

        logger.info("FINISH SETTING THE EXPERIMENT ENVIRONMENT\n")

    def create_configs(self):
        logger.debug('Get the k8s master node')
        kube_master_site = self.configs['exp_env']['kube_master_site']
        if kube_master_site is None or kube_master_site not in self.configs['exp_env']['antidote_clusters']:
            kube_master_site = self.configs['exp_env']['antidote_clusters'][0]

        # calculating the total number of hosts for each cluster
        clusters = dict()
        for cluster in self.configs['exp_env']['antidote_clusters']:
            if cluster == kube_master_site:
                clusters[cluster] = clusters.get(cluster, 0) + self.configs['exp_env']['n_antidotedb_per_dc'] + 1
            else:
                clusters[cluster] = clusters.get(cluster, 0) + self.configs['exp_env']['n_antidotedb_per_dc']

        for cluster in self.configs['exp_env']['elmerfs_site']:
            clusters[cluster] = clusters.get(cluster, 0) + self.configs['exp_env']['n_elmerfs_per_site']

        self.configs['clusters'] = [{'cluster': cluster, 'n_nodes': n_nodes} for cluster, n_nodes in clusters.items()]

        return kube_master_site

    def run(self):
        logger.debug('Parse and convert configs for G5K provisioner')
        self.configs = parse_config_file(self.args.config_file_path)
        kube_master_site = self.create_configs()

        logger.info('''Your topology:
                        Antidote DCs: %s
                        n_antidotedb_per_DC: %s
                        elmerfs sites: %s
                        n_elmerfs_per_site: %s ''' % (
            len(self.configs['exp_env']['antidote_clusters']),
            self.configs['exp_env']['n_antidotedb_per_dc'],
            len(self.configs['exp_env']['elmerfs_site']),
            self.configs['exp_env']['n_elmerfs_per_site'])
        )

        logger.info('Setting the enviroment')
        self.setup_env(kube_master_site)


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = elmerfs_exp()

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
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
