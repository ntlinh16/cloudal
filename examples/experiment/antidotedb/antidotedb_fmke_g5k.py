import os
import shutil
import traceback

from cloudal.utils import get_logger, execute_cmd, parse_config_file, getput_file, ExecuteCommandException
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import kubernetes_configurator, k8s_resources_configurator
from cloudal.experimenter import create_combs_queue, is_job_alive, get_results

from execo_g5k import oardel
from execo_engine import slugify
from kubernetes import config
import yaml

logger = get_logger()


class FMKe_antidotedb_g5k(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(FMKe_antidotedb_g5k, self).__init__()
        self.args_parser.add_argument("--kube-master", dest="kube_master",
                                      help="name of kube master node",
                                      default=None,
                                      type=str)

    def save_results(self, comb):
        logger.info("----------------------------------")
        logger.info("6. Starting dowloading the results")

        configurator = k8s_resources_configurator()
        results_nodes = configurator.get_k8s_resources_name(resource='node',
                                                            label_selectors='service_g5k=fmke_client')

        get_results(comb=comb,
                    hosts=results_nodes,
                    remote_result_files=['/tmp/results/'],
                    local_result_dir=self.configs['exp_env']['results_dir'])

        logger.info("Finish dowloading the results")

    def perform_combination(self, kube_namespace, concurrent_clients):
        logger.info('-----------------------------------------------------------------')
        logger.info('5. Starting deploying fmke client to stress the Antidote database')
        fmke_client_k8s_dir = self.configs['exp_env']['fmke_yaml_path']

        logger.debug('Delete old k8s yaml files if exists')
        for filename in os.listdir(fmke_client_k8s_dir):
            if filename.startswith('create_fmke_client_') or filename.startswith('fmke_client_'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(fmke_client_k8s_dir, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        logger.debug('Create fmke_client folder on each fmke_client node')
        configurator = k8s_resources_configurator()
        exp_nodes = configurator.get_k8s_resources_name(resource='node',
                                                        label_selectors='service_g5k=fmke_client')
        cmd = 'mkdir -p /tmp/fmke_client'
        execute_cmd(cmd, exp_nodes)

        logger.debug('Create fmke_client config files to stress database for each Antidote DC')
        file_path = os.path.join(fmke_client_k8s_dir, 'fmke_client.config.template')

        fmke_list = configurator.get_k8s_resources(resource='pod',
                                                   label_selectors='app=fmke',
                                                   kube_namespace=kube_namespace)
        for cluster in self.configs['exp_env']['clusters']:
            fmke_IPs = list()
            for fmke in fmke_list.items:
                if cluster in fmke.metadata.name:
                    fmke_IPs.append(fmke.status.pod_ip)
            fmke_ports = [9090 for i in range(0, len(fmke_IPs))]
            # Modify fmke_client config files with new values
            with open(file_path) as f:
                doc = f.read().replace('["127.0.0.1"]', '%s' % fmke_IPs)
                doc = doc.replace("[9090]", '%s' % fmke_ports)
                doc = doc.replace("{concurrent, 16}.", '{concurrent, %s}.' % concurrent_clients)
                doc = doc.replace("'", '"')
            file_path2 = os.path.join(fmke_client_k8s_dir, 'fmke_client_%s.config' % cluster)
            with open(file_path2, 'w') as f:
                f.write(doc)
            logger.debug('Upload fmke_client config files to kube_master to be used by kubectl to run fmke_client pods')
            getput_file(hosts=exp_nodes, file_paths=[file_path2], dest_location='/tmp/fmke_client/', action='put')

        logger.debug('Create create_fmke_client.yaml files to run job stress for each Antidote DC')
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
        configurator.deploy_k8s_resources(files=fmke_client_files, namespace=kube_namespace)

        t = '0'
        with open(os.path.join(fmke_client_k8s_dir, 'fmke_client.config.template')) as search:
            for line in search:
                line = line.rstrip()  # remove '\n' at end of line
                if "{duration" in line:
                    t = line.split(',')[1].split('}')[0].strip()
        timeout = (int(t) + 5)*60

        logger.info("Stressing database in %s minutes ....." % t)
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors="app=fmke-client",
                                        timeout=timeout,
                                        kube_namespace=kube_namespace)
        logger.info("Finish stressing Antidote database")

    def config_fmke(self, kube_master, kube_namespace):
        logger.info('------------------------------------')
        logger.info('3. Starting deploying FMKe benchmark')
        fmke_k8s_dir = self.configs['exp_env']['fmke_yaml_path']

        logger.debug('Delete old deployment files')
        for filename in os.listdir(fmke_k8s_dir):
            if '.template' not in filename:
                try:
                    os.remove(os.path.join(fmke_k8s_dir, filename))
                except OSError:
                    logger.debug("Error while deleting file")

        logger.debug('Create headless service file')
        file1 = os.path.join(fmke_k8s_dir, 'headlessService.yaml.template')
        file2 = os.path.join(fmke_k8s_dir, 'headlessService.yaml')
        shutil.copyfile(file1, file2)

        logger.debug('Create FMKe statefulSet files for each DC')
        file_path = os.path.join(fmke_k8s_dir, 'statefulSet_fmke.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)

        configurator = k8s_resources_configurator()
        service_list = configurator.get_k8s_resources(resource='service',
                                                      label_selectors='app=antidote,type=exposer-service',
                                                      kube_namespace=kube_namespace)

        for cluster in self.configs['exp_env']['clusters']:
            # Get IP of antidote DC exposer service for each cluster
            for service in service_list.items:
                if cluster in service.metadata.name:
                    ip = service.spec.cluster_ip
            doc['spec']['replicas'] = self.configs['exp_env']['n_fmke_app_per_dc']
            doc['metadata']['name'] = 'fmke-%s' % cluster
            doc['spec']['template']['spec']['containers'][0]['env'] = [
                {'name': 'DATABASE_ADDRESSES', 'value': ip}]
            doc['spec']['template']['spec']['nodeSelector'] = {'service_g5k': 'fmke', 'cluster_g5k': '%s' % cluster}
            file_path = os.path.join(fmke_k8s_dir, 'statefulSet_fmke_%s.yaml' % cluster)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)

        logger.info("Starting FMKe instances on each Antidote DC")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(path=fmke_k8s_dir, namespace=kube_namespace)

        logger.info('Waiting until all fmke app servers are up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=fmke",
                                        kube_namespace=kube_namespace)
        logger.info('Finish deploying FMKe benchmark')

    def config_fmke_pop(self, kube_namespace):
        logger.info('---------------------------')
        logger.info('4. Starting populating data')
        fmke_k8s_dir = self.configs['exp_env']['fmke_yaml_path']

        logger.debug('Modify the populate_data template file')
        configurator = k8s_resources_configurator()
        fmke_list = configurator.get_k8s_resources(resource='pod',
                                                   label_selectors='app=fmke',
                                                   kube_namespace=kube_namespace)
        logger.info('fmke_list: %s' % len(fmke_list.items))
        fmke_IPs = list()
        for cluster in self.configs['exp_env']['clusters']:
            for fmke in fmke_list.items:
                if cluster in fmke.metadata.name:
                    fmke_IPs.append('fmke@%s' % fmke.status.pod_ip)
        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml.template')) as f:
            doc = yaml.safe_load(f)
        doc['metadata']['name'] = 'populate-data-without-prescriptions'
        doc['spec']['template']['spec']['containers'][0]['args'] = ['-f -d small --noprescriptions'] + fmke_IPs
        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml'), 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Populating the FMKe benchmark data")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=[os.path.join(fmke_k8s_dir, 'populate_data.yaml')],
                                          namespace=kube_namespace)

        logger.info('Waiting for populating data')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors="app=fmke_pop",
                                        kube_namespace=kube_namespace)

        logger.debug('Modify the populate_data file to populate prescriptions')
        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml.template')) as f:
            doc = yaml.safe_load(f)
        doc['metadata']['name'] = 'populate-data-with-onlyprescriptions'
        doc['spec']['template']['spec']['containers'][0]['args'] = ['-f -d small --onlyprescriptions -p 1'] + fmke_IPs
        with open(os.path.join(fmke_k8s_dir, 'populate_data.yaml'), 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Populating the FMKe benchmark data with prescriptions")
        configurator.deploy_k8s_resources(files=[os.path.join(fmke_k8s_dir, 'populate_data.yaml')],
                                          namespace=kube_namespace)

        logger.info('Waiting for populating data')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors="app=fmke_pop",
                                        timeout=90,
                                        kube_namespace=kube_namespace)
        logger.info('Finish populating data')

    def config_antidote(self, kube_namespace):
        logger.info('--------------------------------------')
        logger.info('2. Starting deploying Antidote cluster')
        antidote_k8s_dir = self.configs['exp_env']['antidote_yaml_path']

        logger.debug('Delete old createDC, connectDCs_antidote and exposer-service files if exists')
        for filename in os.listdir(antidote_k8s_dir):
            if filename.startswith('createDC_') or filename.startswith('statefulSet_') or filename.startswith('exposer-service_') or filename.startswith('connectDCs_antidote'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(antidote_k8s_dir, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        statefulSet_files = [os.path.join(antidote_k8s_dir, 'headlessService.yaml')]
        logger.debug('Modify the statefulSet file')
        file_path = os.path.join(antidote_k8s_dir, 'statefulSet.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        for cluster in self.configs['exp_env']['clusters']:
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
        configurator.deploy_k8s_resources(files=statefulSet_files, namespace=kube_namespace)

        logger.info('Waiting until all Antidote instances are up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=antidote",
                                        kube_namespace=kube_namespace)

        logger.debug('Creating createDc.yaml file for each Antidote DC')
        dcs = dict()
        for cluster in self.configs['exp_env']['clusters']:
            dcs[cluster] = list()
        antidote_list = configurator.get_k8s_resources_name(resource='pod',
                                                            label_selectors='app=antidote',
                                                            kube_namespace=kube_namespace)
        for antidote in antidote_list:
            cluster = antidote.split('-')[1].strip()
            dcs[cluster].append(antidote)

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
                                        label_selectors='app=antidote',
                                        kube_namespace=kube_namespace)

        logger.debug('Creating connectDCs_antidote.yaml to connect all Antidote DCs')
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        doc['spec']['template']['spec']['containers'][0]['args'] = ['--connectDcs'] + antidote_masters
        file_path = os.path.join(antidote_k8s_dir, 'connectDCs_antidote.yaml')
        with open(file_path, 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info("Connecting all Antidote DCs into a cluster")
        configurator.deploy_k8s_resources(files=[file_path], namespace=kube_namespace)

        logger.info('Waiting until connecting all Antidote DCs')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors='app=antidote',
                                        kube_namespace=kube_namespace)

        logger.info('Finish deploying the Antidote cluster')

    def clean_k8s_resources(self, kube_namespace):
        logger.info('1. Deleting all k8s resource from the previous run in namespace "%s"' % kube_namespace)
        logger.debug('Delete namespace "%s" to delete all the resources, then create it again' % kube_namespace)
        configurator = k8s_resources_configurator()
        configurator.delete_namespace(kube_namespace)
        configurator.create_namespace(kube_namespace)

        logger.debug('Delete all files in /tmp/results folder on fmke_client nodes')
        results_nodes = configurator.get_k8s_resources_name(resource='node',
                                                            label_selectors='service_g5k=fmke_client',
                                                            kube_namespace=kube_namespace)
        cmd = 'rm -rf /tmp/results && mkdir -p /tmp/results'
        execute_cmd(cmd, results_nodes)

    def run_workflow(self, kube_namespace, comb, kube_master, sweeper):
        comb_ok = False
        try:
            logger.info('=======================================')
            logger.info('Performing combination: ' + slugify(comb))

            self.clean_k8s_resources(kube_namespace)
            self.config_antidote(kube_namespace)
            self.config_fmke(kube_master, kube_namespace)
            self.config_fmke_pop(kube_namespace)
            self.perform_combination(kube_namespace, comb['concurrent_clients'])
            self.save_results(comb)
            comb_ok = True
        except ExecuteCommandException as e:
            comb_ok = False
        finally:
            if comb_ok:
                sweeper.done(comb)
                logger.info('Finish combination: %s' % slugify(comb))
            else:
                sweeper.cancel(comb)
                logger.warning(slugify(comb) + ' is canceled')
            logger.info('%s combinations remaining\n' % len(sweeper.get_remaining()))
        return sweeper

    def _set_kube_workers_label(self, kube_workers):
        configurator = k8s_resources_configurator()
        clusters = dict()
        for host in kube_workers:
            cluster = host.split('-')[0]
            clusters[cluster] = [host] + clusters.get(cluster, list())
            configurator.set_labels_node(nodename=host,
                                         labels='cluster_g5k=%s' % cluster)

        n_fmke_app_per_dc = self.configs['exp_env']['n_fmke_app_per_dc']
        n_fmke_client_per_dc = self.configs['exp_env']['n_fmke_client_per_dc']
        n_antidotedb_per_dc = self.configs['exp_env']['n_antidotedb_per_dc']

        for cluster, list_of_hosts in clusters.items():
            for n, service_name in [(n_antidotedb_per_dc, 'antidote'),
                                    (n_fmke_app_per_dc, 'fmke'),
                                    (n_fmke_client_per_dc, 'fmke_client')]:
                for host in list_of_hosts[0: n]:
                    configurator.set_labels_node(nodename=host,
                                                 labels='service_g5k=%s' % service_name)
                list_of_hosts = list_of_hosts[n:]

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
        getput_file(hosts=[kube_master], file_paths=['~/.kube/config'], dest_location=kube_dir, action='get')
        kube_config_file = os.path.join(kube_dir, 'config')
        config.load_kube_config(config_file=kube_config_file)
        logger.info('Kubernetes config file is stored at: %s' % kube_config_file)

    def config_host(self, kube_master, kube_namespace):
        logger.debug("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(hosts=self.hosts, kube_master=kube_master)
        _, kube_workers = configurator.deploy_kubernetes_cluster()

        self._get_credential(kube_master)

        logger.info('Create k8s namespace "%s" for this experiment' % kube_namespace)
        configurator = k8s_resources_configurator()
        configurator.create_namespace(namespace=kube_namespace)

        self._setup_g5k_kube_volumes(kube_workers, n_pv=3)

        logger.info('Set labels for all kubernetes workers')
        self._set_kube_workers_label(kube_workers)

        logger.info("Finish deploying the Kubernetes cluster")

    def setup_env(self, kube_master_site, kube_namespace):
        logger.info("STARTING SETTING THE EXPERIMENT ENVIRONMENT")
        logger.info("Starting provisioning nodes on G5K")
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
        oar_job_ids = provisioner.oar_result

        logger.info("STARTING CONFIGURING NODES")
        kube_master = self.args.kube_master
        if kube_master is None:
            for host in self.hosts:
                if host.startswith(kube_master_site):
                    kube_master = host
                    break

        if self.args.kube_master is None:
            self.config_host(kube_master, kube_namespace)
        else:
            logger.info('Kubernetes master: %s' % kube_master)
            self._get_credential(kube_master)

        logger.info("FINISH CONFIGURING NODES")
        self.args.oar_job_ids = None
        logger.info("FINISH SETTING THE EXPERIMENT ENVIRONMENT\n")
        return kube_master, oar_job_ids

    def create_configs(self):
        logger.debug('Get the k8s master node')
        kube_master_site = self.configs['exp_env']['kube_master_site']
        if kube_master_site is None or kube_master_site not in self.configs['exp_env']['clusters']:
            kube_master_site = self.configs['exp_env']['clusters'][0]

        n_nodes_per_cluster = (
            self.configs['exp_env']['n_fmke_client_per_dc'] +
            self.configs['exp_env']['n_fmke_app_per_dc'] +
            self.configs['exp_env']['n_antidotedb_per_dc'])

        clusters = list()
        for cluster in self.configs['exp_env']['clusters']:
            if cluster == kube_master_site:
                clusters.append({'cluster': cluster, 'n_nodes': n_nodes_per_cluster + 1})
            else:
                clusters.append({'cluster': cluster, 'n_nodes': n_nodes_per_cluster})
        self.configs['clusters'] = clusters
        return kube_master_site

    def run(self):
        logger.debug('Parse and convert configs for G5K provisioner')
        self.configs = parse_config_file(self.args.config_file_path)
        kube_master_site = self.create_configs()

        logger.info('''Your topology:
                        Antidote DCs: %s
                        n_antidotedb_per_DC: %s
                        n_fmke_per_DC: %s
                        n_fmke_client_per_DC: %s ''' % (
            len(self.configs['exp_env']['clusters']),
            self.configs['exp_env']['n_antidotedb_per_dc'],
            self.configs['exp_env']['n_fmke_app_per_dc'],
            self.configs['exp_env']['n_fmke_client_per_dc'])
        )

        logger.debug('Creating the combination list')
        sweeper = create_combs_queue(result_dir=self.configs['exp_env']['results_dir'],
                                     parameters=self.configs['parameters'])

        kube_namespace = 'fmke-exp'
        oar_job_ids = None
        while len(sweeper.get_remaining()) > 0:
            if oar_job_ids is None:
                kube_master, oar_job_ids = self.setup_env(kube_master_site, kube_namespace)

            comb = sweeper.get_next()
            sweeper = self.run_workflow(kube_namespace=kube_namespace,
                                        kube_master=kube_master,
                                        comb=comb,
                                        sweeper=sweeper)

            if not is_job_alive(oar_job_ids):
                oardel(oar_job_ids)
                oar_job_ids = None
        logger.info('Finish the experiment!!!')


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = FMKe_antidotedb_g5k()

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
