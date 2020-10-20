import os
import shutil
import traceback
from execo_g5k import utils
import yaml

from kubernetes.config import kube_config

from cloudal.utils import get_logger, get_file, execute_cmd, get_remote_executor, parse_config_file, getput_file
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import kubernetes_configurator
from cloudal.configurator import docker_configurator
from cloudal.configurator import k8s_resources_configurator

from kubernetes import config

logger = get_logger()


class FMKe_antidotedb_g5k(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(FMKe_antidotedb_g5k, self).__init__()

    def get_results(self, kube_master):
        cmd = """kubectl get nodes --selector="service_g5k=fmke_client" | tail -n +2 | awk '{print $1}'"""
        _, r = execute_cmd(cmd, kube_master)
        results_nodes = r.processes[0].stdout.strip().split('\r\n')
        results_path = self.configs['exp_env']['results_dir']
        if not os.path.exists(results_path):
            os.mkdir(results_path)
        getput_file(hosts=results_nodes,
                    file_paths=['/tmp/results/'],
                    dest_location=results_path,
                    action='get')

    def perform_exp(self, kube_master):
        logger.info('==============================================================')
        logger.info('Starting deploying fmke client to stress the Antidote database')
        fmke_client_k8s_dir = self.configs['exp_env']['fmke_yaml_path']

        logger.debug('Delete old k8s yaml files if exists')
        for filename in os.listdir(fmke_client_k8s_dir):
            if filename.startswith('create_fmke_client_') or filename.startswith('fmke_client_'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(fmke_client_k8s_dir, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        logger.info('Create fmke_client folder on each Antidote DC')
        remote_executor = get_remote_executor()
        cmd = 'mkdir -p /tmp/fmke_client'
        execute_cmd(cmd, self.hosts)

        logger.info('Create fmke_client config files for each Antidote DC')
        file_path = os.path.join(fmke_client_k8s_dir, 'fmke_client.config.template')
        for cluster in self.configs['exp_env']['clusters']:
            fmke_IPs = list()
            for i in range(0, self.configs['exp_env']['n_fmke_app_per_dc']):
                cmd = "kubectl describe po fmke-%s-%s | grep IP: | awk '{print $2}'" % (cluster, i)
                _, r = execute_cmd(cmd, kube_master)
                fmke_IPs.append(r.processes[0].stdout.split('\n')[0].strip())
            fmke_ports = [9090 for i in range(0, len(fmke_IPs))]
            # Modify fmke_client config files with new values
            with open(file_path) as f:
                doc = f.read().replace('["127.0.0.1"]', '%s' % fmke_IPs)
                doc = doc.replace("[9090]", '%s' % fmke_ports)
                doc = doc.replace("'", '"')
            file_path2 = os.path.join(fmke_client_k8s_dir, 'fmke_client_%s.config' % cluster)
            with open(file_path2, 'w') as f:
                f.write(doc)
            logger.debug('Upload fmke_client config files to kube_master to be used by kubectl to run fmke_client pods')
            getput_file(hosts=self.hosts, file_paths=[file_path2], dest_location='/tmp/fmke_client/', action='put')

        logger.info('Create create_fmke_client files for each DC')
        file_path = os.path.join(fmke_client_k8s_dir, 'create_fmke_client.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        fmke_client_files = list()
        for cluster in self.configs['exp_env']['clusters']:
            doc['spec']['parallelism'] = self.configs['exp_env']['n_fmke_client_per_dc']
            doc['spec']['completions'] = self.configs['exp_env']['n_fmke_client_per_dc']
            doc['metadata']['name'] = 'fmke-client-%s' % cluster
            doc['spec']['template']['spec']['containers'][0]['lifecycle']['postStart']['exec']['command'] = [
                "cp", "/cluster_node/fmke_client_%s.config" % cluster, "/fmke_client/fmke_client.config"]
            doc['spec']['template']['spec']['nodeSelector'] = {
                'service_g5k': 'fmke_client', 'cluster_g5k': '%s' % cluster}
            file_path = os.path.join(fmke_client_k8s_dir, 'create_fmke_client_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            fmke_client_files.append(file_path)

        logger.info("Running fmke client instances on each DC")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=fmke_client_files)

        logger.info("Stressing database")
        with open(os.path.join(fmke_client_k8s_dir, 'fmke_client.config.template')) as search:
            for line in search:
                line = line.rstrip()  # remove '\n' at end of line
                if "{duration" in line:
                    timeout = line.split(',')[1].split('}')[0].strip()
        cmd = 'kubectl wait --for=condition=complete job -l "app=fmke-client" --timeout=%sm' % timeout
        execute_cmd(cmd, kube_master)
        logger.info("Finish stress database")

    def config_fmke(self, kube_master):
        logger.info('=================================')
        logger.info('Starting deploying FMKe benchmark')
        fmke_k8s_dir = self.configs['exp_env']['fmke_yaml_path']

        logger.debug('Delete old deployment files')
        for filename in os.listdir(fmke_k8s_dir):
            if '.template' not in filename:
                try:
                    os.remove(os.path.join(fmke_k8s_dir, filename))
                except OSError:
                    logger.debug("Error while deleting file")

        logger.info('Create headless service file')
        file1 = os.path.join(fmke_k8s_dir, 'headlessService.yaml.template')
        file2 = os.path.join(fmke_k8s_dir, 'headlessService.yaml')
        shutil.copyfile(file1, file2)

        logger.info('Create FMKe statefulSet files for each DC')
        file_path = os.path.join(fmke_k8s_dir, 'statefulSet_fmke.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        for cluster in self.configs['exp_env']['clusters']:
            # Get IP of antidote DC exposer service for each cluster
            cmd = "kubectl describe service antidote-exposer-%s | grep IP | awk '{print $2}'" % cluster
            _, r = execute_cmd(cmd, kube_master)
            ip = r.processes[0].stdout.strip()
            # Modify statefulSet file with new values
            doc['spec']['replicas'] = self.configs['exp_env']['n_fmke_app_per_dc']
            doc['metadata']['name'] = 'fmke-%s' % cluster
            doc['spec']['template']['spec']['containers'][0]['env'] = [
                {'name': 'DATABASE_ADDRESSES', 'value': ip}]
            doc['spec']['template']['spec']['nodeSelector'] = {'service_g5k': 'fmke', 'cluster_g5k': '%s' % cluster}
            file_path = os.path.join(fmke_k8s_dir, 'statefulSet_fmke_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)

        logger.info("Starting FMKe service instances on each DC")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(path=fmke_k8s_dir)

        logger.info('Waiting until all fmke app servers are up')
        cmd = 'kubectl wait --for=condition=Ready pod -l "app=fmke" --timeout=300s'
        execute_cmd(cmd, kube_master)

        logger.debug('Modify the populate_data file')
        fmke_IPs = list()
        for cluster in self.configs['exp_env']['clusters']:
            for i in range(0, self.configs['exp_env']['n_fmke_app_per_dc']):
                cmd = "kubectl logs fmke-%s-%s | grep NODE_NAME | awk '{print $2}'" % (cluster, i)
                _, r = execute_cmd(cmd, kube_master)
                fmke_IPs.append(r.processes[0].stdout.strip())
        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml.template')) as f:
            doc = yaml.safe_load(f)
        # TODO: give -d as a parameter
        doc['metadata']['name'] = 'populate-data-without-prescriptions'
        doc['spec']['template']['spec']['containers'][0]['args'] = ['-f --noprescriptions'] + fmke_IPs
        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml'), 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Populating the FMKe benchmark data ")
        configurator.deploy_k8s_resources(files=[os.path.join(fmke_k8s_dir, 'populate_data.yaml')])

        logger.info('Waiting until finishing populating data')
        cmd = 'kubectl wait --for=condition=complete job -l "app=fmke_pop" --timeout=600s'
        execute_cmd(cmd, kube_master)

        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml.template')) as f:
            doc = yaml.safe_load(f)
        # TODO: give -d as a parameter
        doc['metadata']['name'] = 'populate-data-with-onlyprescriptions'
        doc['spec']['template']['spec']['containers'][0]['args'] = ['-f --onlyprescriptions -p 1'] + fmke_IPs
        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml'), 'w') as f:
            yaml.safe_dump(doc, f)
        logger.info("Populating the FMKe benchmark data ")
        configurator.deploy_k8s_resources(files=[os.path.join(fmke_k8s_dir, 'populate_data.yaml')])

        logger.info('Waiting until finishing populating data')
        cmd = 'kubectl wait --for=condition=complete job -l "app=fmke_pop" --timeout=600s'
        execute_cmd(cmd, kube_master)

    def set_label_kube_node(self, host, label, kube_master):
        cmd = 'kubectl label node %s %s' % (host, label)
        execute_cmd(cmd, kube_master)

    def set_labels(self, kube_master):
        clusters = dict()
        kube_workers = [host for host in self.hosts if host != kube_master]
        for host in kube_workers:
            cluster = host.split('-')[0]
            clusters[cluster] = [host] + clusters.get(cluster, list())
            self.set_label_kube_node(host=host,
                                     label='cluster_g5k=%s' % cluster,
                                     kube_master=kube_master)

        n_fmke_app_per_dc = self.configs['exp_env']['n_fmke_app_per_dc']
        n_fmke_client_per_dc = self.configs['exp_env']['n_fmke_client_per_dc']
        n_antidotedb_per_dc = self.configs['exp_env']['n_antidotedb_per_dc']

        for cluster, list_of_hosts in clusters.items():
            for n, service_name in [(n_antidotedb_per_dc, 'antidote'),
                                    (n_fmke_app_per_dc, 'fmke'),
                                    (n_fmke_client_per_dc, 'fmke_client')]:
                for host in list_of_hosts[0: n]:
                    self.set_label_kube_node(host=host,
                                             label='service_g5k=%s' % service_name,
                                             kube_master=kube_master)
                list_of_hosts = list_of_hosts[n:]

    def config_antidote(self, kube_master):
        logger.info('====================================')
        logger.info('Starting deploying Antidote clusters')
        antidote_k8s_dir = self.configs['exp_env']['antidote_yaml_path']

        # temp run
        logger.info('Set labels for kuber workers')
        self.set_labels(kube_master)

        # TODO: delete all antidote service on kube cluster if existed

        logger.debug('Delete old createDC, connectDCs_antidote and exposer-service files if exists')
        for filename in os.listdir(antidote_k8s_dir):
            if filename.startswith('createDC_') or filename.startswith('statefulSet_') or filename.startswith('exposer-service_') or filename.startswith('connectDCs_antidote'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(antidote_k8s_dir, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        logger.info("Deploying local persistance volumes")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(path=antidote_k8s_dir)

        logger.info('Waiting for setting local persistance volumes')
        cmd = 'kubectl wait --for=condition=Ready pod -l "app.kubernetes.io/instance=local-volume-provisioner"'
        execute_cmd(cmd, kube_master)

        logger.debug('Modify the statefulSet file')
        file_path = os.path.join(antidote_k8s_dir, 'statefulSet.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        statefulSet_files = list()
        for cluster in self.configs['exp_env']['clusters']:
            doc['spec']['replicas'] = self.configs['exp_env']['n_antidotedb_per_dc']
            doc['metadata']['name'] = 'antidote-%s' % cluster
            doc['spec']['template']['spec']['nodeSelector'] = {'service_g5k': 'antidote', 'cluster_g5k': '%s' % cluster}
            file_path = os.path.join(antidote_k8s_dir, 'statefulSet_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            statefulSet_files.append(file_path)

        logger.info("Deploying AntidoteDB instance")
        configurator.deploy_k8s_resources(files=statefulSet_files)

        logger.info('Waiting until all antidote instances are up')
        cmd = 'kubectl wait --for=condition=Ready pod -l "app=antidote" --timeout=300s'
        execute_cmd(cmd, kube_master)

        logger.info('Creating createDc.yaml file for each Antidote DC')
        dcs = dict()
        for cluster in self.configs['exp_env']['clusters']:
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

        logger.info('Creating exposer-service files')
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

        logger.info("Creating Antidote DCs and expose service")
        configurator.deploy_k8s_resources(files=createdc_files)

        logger.info('Waiting until all antidote DCs are created')
        cmd = 'kubectl wait --for=condition=complete job -l "app=antidote" --timeout=300s'
        execute_cmd(cmd, kube_master)

        logger.info('Creating connectDCs_antidote.yaml to connect all Antidote DCs')
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = ['--connectDcs'] + antidote_masters
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs_antidote.yaml')
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Connecting Antidote cluster")
        configurator.deploy_k8s_resources(files=[file_path])
        logger.info('Waiting until connecting all Antidote DCs')
        cmd = 'kubectl wait --for=condition=complete job -l "app=antidote" --timeout=300s'
        execute_cmd(cmd, kube_master)

        logger.info('Finish deploying Antidote clusters')

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

    def _get_credential(self, kube_master):
        home = os.path.expanduser('~')
        kube_dir = os.path.join(home, '.kube')

        if not os.path.exists(kube_dir):
            os.mkdir(kube_dir)
        get_file(host=kube_master, remote_file_paths=['~/.kube/config'], local_dir=kube_dir)
        config.load_kube_config(config_file=os.path.join(kube_dir, 'config'))
        logger.info('Kubernetes config file is stored at: %s' % kube_dir)

    def config_kube(self, kube_master):
        logger.info("=====================================")
        logger.info("Starting deploying Kubernetes cluster")
        logger.debug("Init configurator: docker_configurator")
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        logger.debug("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(hosts=self.hosts,
                                               kube_master=kube_master)
        kube_master, kube_workers = configurator.deploy_kubernetes_cluster()
        logger.info('Kubernetes master: %s' % kube_master)

        self._get_credential(kube_master)

        self._setup_g5k_kube_volumes(kube_workers, n_pv=10)

        logger.info("Finish deploying Kubernetes cluster")

    def config_host(self, kube_master):
        # # temp re-run
        # self._get_credential(kube_master)

        self.config_kube(kube_master)
        self.config_antidote(kube_master)
        self.config_fmke(kube_master)

    def create_configs(self):
        n_nodes_per_cluster = (
            self.configs['exp_env']['n_fmke_client_per_dc'] +
            self.configs['exp_env']['n_fmke_app_per_dc'] +
            self.configs['exp_env']['n_antidotedb_per_dc'])

        clusters = list()
        for cluster in self.configs['exp_env']['clusters']:
            if cluster == self.configs['exp_env']['kube_master_site']:
                clusters.append({'cluster': cluster, 'n_nodes': n_nodes_per_cluster + 1})
            else:
                clusters.append({'cluster': cluster, 'n_nodes': n_nodes_per_cluster})
        self.configs['clusters'] = clusters

    def run(self):
        logger.info("STARTING PROVISIONING NODES")
        logger.debug('Parse and convert configs for G5K provisioner')
        self.configs = parse_config_file(self.args.config_file_path)
        self.create_configs()

        logger.info("Init provisioner: g5k_provisioner")
        provisioner = g5k_provisioner(configs=self.configs,
                                      keep_alive=self.args.keep_alive,
                                      out_of_chart=self.args.out_of_chart,
                                      oar_job_ids=self.args.oar_job_ids,
                                      no_deploy_os=self.args.no_deploy_os,
                                      is_reservation=self.args.is_reservation,
                                      job_name="cloudal_k8s")

        provisioner.provisioning()
        self.hosts = provisioner.hosts
        logger.info("FINISH PROVISIONING NODES\n")

        logger.info("STARTING CONFIGURING THE EXPERIMENT ENVIRONMENT")
        # temp run
        logger.debug('Get the kube master node')
        kube_master_site = self.configs['exp_env']['kube_master_site']
        if kube_master_site is None or kube_master_site not in self.configs['exp_env']['clusters']:
            kube_master_site = self.configs['exp_env']['clusters'][0]
        kube_master = None
        for host in self.hosts:
            if host.startswith(kube_master_site):
                kube_master = host
                break
        # # temp re-run
        # kube_master = 'econome-9.nantes.grid5000.fr'
        self.config_host(kube_master)
        logger.info("FINISH CONFIGURING THE EXPERIMENT ENVIRONMENT\n")

        logger.info("STARTING PERFORMING THE EXPERIMENTS")
        self.perform_exp(kube_master)
        logger.info("FINISH THE EXPERIMENTS\n")

        logger.info("GETTING THE RESULTS")
        self.get_results(kube_master)
        logger.info("FINISH GETTING THE RESULTS")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = FMKe_antidotedb_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
