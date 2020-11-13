import os
import traceback
import yaml

from cloudal.utils import get_logger, get_file, execute_cmd, parse_config_file
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import kubernetes_configurator
from cloudal.configurator import docker_configurator
from cloudal.configurator import k8s_resources_configurator

from execo_g5k import oardel

from kubernetes import config

logger = get_logger()


class config_antidotedb_cluster_g5k(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(config_antidotedb_cluster_g5k, self).__init__()
        self.args_parser.add_argument("--antidote_yaml_dir", dest="yaml_path",
                                      help="path to yaml file to deploy antidotedb cluster",
                                      default='',
                                      required=True,
                                      type=str)
        self.args_parser.add_argument("--kube-master", dest="kube_master",
                                      help="name of kube master node",
                                      default=None,
                                      type=str)

    def config_antidote(self, kube_master):
        logger.info('Starting deploying Antidote cluster')
        antidote_k8s_dir = self.args.yaml_path

        logger.debug('Delete old createDC, connectDCs_antidote and exposer-service files if exists')
        for filename in os.listdir(antidote_k8s_dir):
            if filename.startswith('createDC_') or filename.startswith('statefulSet_') or filename.startswith('exposer-service_') or filename.startswith('connectDCs_antidote'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(antidote_k8s_dir, filename))
                    except OSError:
                        logger.debug("Error while deleting file")

        deploy_files = [os.path.join(antidote_k8s_dir, 'headlessService.yaml')]
        logger.debug('Modify the statefulSet file')
        file_path = os.path.join(antidote_k8s_dir, 'statefulSet.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)
        for cluster in self.configs['clusters']:
            doc['spec']['replicas'] = cluster['n_nodes']
            doc['metadata']['name'] = 'antidote-%s' % cluster['cluster']
            doc['spec']['template']['spec']['nodeSelector'] = {
                'service_g5k': 'antidote', 'cluster_g5k': '%s' % cluster['cluster']}
            file_path = os.path.join(antidote_k8s_dir, 'statefulSet_%s.yaml' % cluster['cluster'])
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            deploy_files.append(file_path)

        logger.info("Starting AntidoteDB instances")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=deploy_files, namespace=self.kube_namespace)

        logger.info('Waiting until all Antidote instances are up')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app=antidote",
                                        kube_master=kube_master,
                                        kube_namespace=self.kube_namespace)

        logger.debug('Creating createDc.yaml file for each Antidote DC')
        dcs = dict()
        for cluster in self.configs['clusters']:
            dcs[cluster['cluster']] = list()
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

        logger.info('Finish deploying an Antidote cluster')

    def _set_kube_workers_label(self, kube_master, kube_workers):
        for host in kube_workers:
            cluster = host.split('-')[0]
            labels = ['cluster_g5k=%s' % cluster, 'service_g5k=antidote']
            cmd = 'kubectl label node %s %s' % (host, " ".join(labels))
            execute_cmd(cmd, kube_master)

    def _get_credential(self, kube_master):
        home = os.path.expanduser('~')
        kube_dir = os.path.join(home, '.kube')

        if not os.path.exists(kube_dir):
            os.mkdir(kube_dir)
        get_file(host=kube_master, remote_file_paths=[
                 '~/.kube/config'], local_dir=kube_dir)
        config.load_kube_config(config_file=os.path.join(kube_dir, 'config'))
        logger.info('Kubernetes config file is stored at: %s' % kube_dir)

    def _setup_g5k_kube_volumes(self, kube_master, kube_workers):
        logger.info("Setting volumes on %s kubernetes workers" %
                    len(kube_workers))
        N_PV = 3
        cmd = '''umount /dev/sda5;
                 mount -t ext4 /dev/sda5 /tmp'''
        execute_cmd(cmd, kube_workers)
        cmd = '''for i in $(seq 1 %s); do
                     mkdir -p /tmp/pv/vol${i}
                     mkdir -p /mnt/disks/vol${i}
                     mount --bind /tmp/pv/vol${i} /mnt/disks/vol${i}
                 done''' % N_PV
        execute_cmd(cmd, kube_workers)

        logger.info("Creating local persistance volumes on Kubernetes workers")
        logger.debug("Init configurator: k8s_resources_configurator")
        configurator = k8s_resources_configurator()
        antidote_k8s_dir = self.args.yaml_path
        deploy_files = [os.path.join(antidote_k8s_dir, 'local_persistentvolume.yaml'),
                        os.path.join(antidote_k8s_dir, 'storageClass.yaml')]
        configurator.deploy_k8s_resources(files=deploy_files)

        logger.info('Waiting for setting local persistance volumes')
        configurator.wait_k8s_resources(resource='pod',
                                        label_selectors="app.kubernetes.io/instance=local-volume-provisioner",
                                        kube_master=kube_master)

    def config_kube(self):
        logger.info("sTARTING deploying Kubernetes cluster")
        logger.info("Init configurator: docker_configurator")
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        logger.info("Init configurator: kubernetes_configurator")
        configurator = kubernetes_configurator(hosts=self.hosts)
        kube_master, kube_workers = configurator.deploy_kubernetes_cluster()

        logger.info('Create Kubernetes namespace "%s" for this experiment' % self.kube_namespace)
        cmd = "kubectl create namespace %s && kubectl config set-context --current --namespace=%s" % (
            self.kube_namespace, self.kube_namespace)
        execute_cmd(cmd, kube_master)

        self._get_credential(kube_master=kube_master)

        self._setup_g5k_kube_volumes(kube_master, kube_workers)

        logger.info('Set labels for all kubernetes workers')
        self._set_kube_workers_label(kube_master, kube_workers)

        logger.info("Finish deploying the Kubernetes cluster")
        return kube_master

    def config_host(self):
        self.kube_namespace = "antidote"
        kube_master = self.args.kube_master
        if self.args.kube_master is None:
            kube_master = self.config_kube()
        else:
            logger.info('Kubernetes master: %s' % kube_master)
            self._get_credential(kube_master)
        self.config_antidote(kube_master)

    def run(self):
        logger.info("STARTING PROVISIONING NODES")
        logger.info("Init provisioner: g5k_provisioner")
        provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                      keep_alive=self.args.keep_alive,
                                      out_of_chart=self.args.out_of_chart,
                                      oar_job_ids=self.args.oar_job_ids,
                                      no_deploy_os=self.args.no_deploy_os,
                                      is_reservation=self.args.is_reservation,
                                      job_name="cloudal_k8s")
        provisioner.provisioning()
        self.hosts = provisioner.hosts
        self.configs = provisioner.configs
        logger.info("FINISH PROVISIONING NODES")

        logger.info("STARTING CONFIGURING HOSTS")
        self.config_host()
        logger.info("FINISH CONFIGURING HOSTS")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_cluster_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error(
            'Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
