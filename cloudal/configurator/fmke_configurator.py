import os
import re
import shutil

from time import sleep

from cloudal.utils import get_logger, execute_cmd, getput_file
from cloudal.configurator import k8s_resources_configurator, CancelException

import yaml
logger = get_logger()


class fmke_configurator(object): 

    def deploy_fmke_client(self, fmke_yaml_path, test_duration, concurrent_clients, n_total_fmke_clients, workload=None, kube_namespace='default'):
        """Deploy FMKe client on the given K8s cluster

        Parameters
        ----------
        fmke_yaml_path: str
            a path to the K8s yaml deployment files
        test_duration: int
            the duration to perform the workload
        concurrent_clients: int
            the number of concurrent clients 
        n_total_fmke_clients: int
            the total number of clients need to be deployed on the system
        workload: dict
            the workload ratio of FMKe benchmark
        kube_namespace: str
            the name of K8s namespace
        """
        logger.debug('Delete old k8s yaml files if exists')
        for filename in os.listdir(fmke_yaml_path):
            if filename.startswith('create_fmke_client_') or filename.startswith('fmke_client_'):
                if '.template' not in filename:
                    try:
                        os.remove(os.path.join(fmke_yaml_path, filename))
                    except OSError:
                        logger.debug('Error while deleting file')
        if workload:
            logger.debug('Create the new workload ratio')
            new_workload = ',\n'.join(['  {%s, %s}' % (key, val) for key, val in workload.items()])
            operations = '{operations,[\n%s\n]}.' % new_workload

        logger.debug('Init configurator: k8s_resources_configurator')
        configurator = k8s_resources_configurator()
        fmke_list = configurator.get_k8s_resources(resource='pod',
                                                   label_selectors='app=fmke',
                                                   kube_namespace=kube_namespace)

        fmke_client_files = list()
        config_file_path = os.path.join(fmke_yaml_path, 'fmke_client.config.template')
        create_file_path = os.path.join(fmke_yaml_path, 'create_fmke_client.yaml.template')
        for fmke in fmke_list.items:
            node = fmke.spec.node_name.split('.')[0]
            # Modify fmke_client config files with new values
            logger.debug('Create fmke_client config files to stress database for each AntidoteDB DC')
            with open(config_file_path) as f:
                doc = f.read()
                doc = doc.replace('127.0.0.1', '%s' % fmke.status.pod_ip)
                doc = doc.replace('{concurrent, 16}.', '{concurrent, %s}.' % concurrent_clients)
                doc = doc.replace('{duration, 3}.', '{duration, %s}.' % test_duration)
                doc = doc.replace("'", '"')
                if workload:
                    doc = re.sub(r'{operations.*', operations, doc, flags=re.S)
            file_path = os.path.join(fmke_yaml_path, 'fmke_client_%s.config' % node)
            with open(file_path, 'w') as f:
                f.write(doc)
            logger.debug('Create fmke_client folder on each fmke_client node')
            cmd = 'mkdir -p /tmp/fmke_client'
            execute_cmd(cmd, fmke.status.host_ip)
            logger.debug('Upload fmke_client config files to kube_master to be used by kubectl to run fmke_client pods')
            getput_file(hosts=fmke.status.host_ip, file_paths=[file_path], dest_location='/tmp/fmke_client/', action='put')


            logger.debug('Create create_fmke_client.yaml files to deploy one FMKe client')
            with open(create_file_path) as f:
                doc = yaml.safe_load(f)            
            doc['metadata']['name'] = 'fmke-client-%s' % node
            doc['spec']['template']['spec']['containers'][0]['lifecycle']['postStart']['exec']['command'] = [
                'cp', '/cluster_node/fmke_client_%s.config' % node, '/fmke_client/fmke_client.config']
            doc['spec']['template']['spec']['nodeSelector'] = {
                'service': 'fmke', 'kubernetes.io/hostname': '%s' % fmke.spec.node_name}
            file_path = os.path.join(fmke_yaml_path, 'create_fmke_client_%s.yaml' % node)
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)
            fmke_client_files.append(file_path)

        logger.info('Starting FMKe client instances on each AntidoteDB DC')
        configurator.deploy_k8s_resources(files=fmke_client_files, namespace=kube_namespace)
        sleep(20)
        logger.info('Checking if deploying enough the number of running FMKe_client or not')
        fmke_client_list = configurator.get_k8s_resources_name(resource='pod',
                                                            label_selectors='app=fmke-client',
                                                            kube_namespace=kube_namespace)
        if len(fmke_client_list) != n_total_fmke_clients:
            logger.info('n_fmke_client = %s, n_deployed_fmke_client = %s' %(n_total_fmke_clients, len(fmke_client_list)))
            raise CancelException('Cannot deploy enough FMKe_client')

        logger.info('Stressing database in %s minutes .....' % test_duration)
        deploy_ok = configurator.wait_k8s_resources(resource='job',
                                        label_selectors='app=fmke-client',
                                        timeout=(test_duration + 5)*60,
                                        kube_namespace=kube_namespace)
        if not deploy_ok:
            logger.error('Cannot wait until all FMKe client instances running completely')
            raise CancelException('Cannot wait until all FMKe client instances running completely')

        logger.info('Finish stressing AntidoteDB cluster')

    def deploy_fmke_app(self, fmke_yaml_path, clusters, n_fmke_app_per_dc, concurrent_clients, kube_namespace='default'):
        """Deploy FMKe application servers on the given K8s cluster

        Parameters
        ----------
        fmke_yaml_path: str
            a path to the K8s yaml deployment files
        clusters: list
            list of cluster name
        n_fmke_app_per_dc: int
            the number of FMKe application servers need to be deployed on one site
        concurrent_clients: int
            the number of concurrent clients 
        kube_namespace: str
            the name of K8s namespace
        """
        logger.debug('Delete old deployment files')
        for filename in os.listdir(fmke_yaml_path):
            if '.template' not in filename:
                try:
                    os.remove(os.path.join(fmke_yaml_path, filename))
                except OSError:
                    logger.debug('Error while deleting file')

        logger.debug('Create headless service file')
        file1 = os.path.join(fmke_yaml_path, 'headlessService.yaml.template')
        file2 = os.path.join(fmke_yaml_path, 'headlessService.yaml')
        shutil.copyfile(file1, file2)

        logger.debug('Create FMKe statefulSet files for each DC')
        file_path = os.path.join(fmke_yaml_path, 'statefulSet_fmke.yaml.template')
        with open(file_path) as f:
            doc = yaml.safe_load(f)

        for i in range(1,11):
            if 2 ** i > concurrent_clients:
                connection_pool_size = 2 ** i
                break
        logger.debug('Init configurator: k8s_resources_configurator')
        configurator = k8s_resources_configurator()
        service_list = configurator.get_k8s_resources(resource='service',
                                                      label_selectors='app=antidote,type=exposer-service',
                                                      kube_namespace=kube_namespace)

        for cluster in clusters:
            # Get IP of AntidoteDB DC exposer service for each cluster
            for service in service_list.items:
                if cluster.lower() in service.metadata.name:
                    ip = service.spec.cluster_ip
            doc['spec']['replicas'] = n_fmke_app_per_dc
            doc['metadata']['name'] = 'fmke-%s' % cluster.lower()
            doc['spec']['template']['spec']['containers'][0]['env'] = [
                {'name': 'DATABASE_ADDRESSES', 'value': ip},
                {'name': 'CONNECTION_POOL_SIZE', 'value': '%s' % connection_pool_size}]
            doc['spec']['template']['spec']['nodeSelector'] = {
                'service': 'fmke', 'cluster': '%s' % cluster.lower()}
            file_path = os.path.join(fmke_yaml_path, 'statefulSet_fmke_%s.yaml' % cluster.lower())
            with open(file_path, 'w') as f:
                yaml.safe_dump(doc, f)

        logger.info('Starting FMKe instances on each AntidoteDB DC')
        configurator.deploy_k8s_resources(path=fmke_yaml_path, namespace=kube_namespace)

        logger.info('Waiting until all fmke app instances are up')
        deploy_ok = configurator.wait_k8s_resources(resource='pod',
                                                    label_selectors='app=fmke',
                                                    timeout=600,
                                                    kube_namespace=kube_namespace)

        if not deploy_ok:
            raise CancelException('Cannot wait until all fmke app instances are up')
        logger.info('Checking if FMKe_app deployed correctly')
        fmke_app_list = configurator.get_k8s_resources_name(resource='pod',
                                                            label_selectors='app=fmke',
                                                            kube_namespace=kube_namespace)
        if len(fmke_app_list) != n_fmke_app_per_dc * len(clusters):
            logger.info('n_fmke_app = %s, n_deployed_fmke_app = %s' % (n_fmke_app_per_dc * len(clusters), len(fmke_app_list)))
            raise CancelException('Cannot deploy enough FMKe_app')

        logger.info('Finish deploying FMKe benchmark')

    def deploy_fmke_pop(self, fmke_yaml_path, dataset, n_fmke_pop_process, clusters, stabilizing_time, timeout=600,kube_namespace='default'):
        """Deploy FMKe populator on the given K8s cluster to generate the data in to an AntidoteDB cluster

        Parameters
        ----------
        fmke_yaml_path: str
            a path to the K8s yaml deployment files
        dataset: str
            name of the dataset of FMKe benchmark to generate into the database
        n_fmke_pop_process: int
            the number of FMKe populator processes running simultaneously
        clusters: list
            list of cluster name
        stabilizing_time: int
            the time to wait for synchronize and replication process between datacenters
        kube_namespace: str
            the name of K8s namespace
        """
        logger.debug('Modify the populate_data template file')
        configurator = k8s_resources_configurator()
        fmke_list = configurator.get_k8s_resources(resource='pod',
                                                   label_selectors='app=fmke',
                                                   kube_namespace=kube_namespace)
        fmke_IPs = list()
        for cluster in clusters:
            for fmke in fmke_list.items:
                if cluster.lower() in fmke.metadata.name:
                    fmke_IPs.append('fmke@%s' % fmke.status.pod_ip)
        with open(os.path.join(fmke_yaml_path, 'populate_data.yaml.template')) as f:
            doc = yaml.safe_load(f)
        doc['metadata']['name'] = 'populate-data-without-prescriptions'
        doc['spec']['template']['spec']['containers'][0]['args'] = ['-f -d %s --noprescriptions -p %s' %
                                                                    (dataset, n_fmke_pop_process)] + fmke_IPs
        with open(os.path.join(fmke_yaml_path, 'populate_data.yaml'), 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info('Populating the FMKe benchmark data without prescriptions')
        logger.debug('Init configurator: k8s_resources_configurator')
        configurator = k8s_resources_configurator()
        configurator.deploy_k8s_resources(files=[os.path.join(fmke_yaml_path, 'populate_data.yaml')],
                                          namespace=kube_namespace)

        logger.info('Waiting for populating data without prescriptions')
        deploy_ok = configurator.wait_k8s_resources(resource='job',
                                                    label_selectors='app=fmke_pop',
                                                    timeout=timeout,
                                                    kube_namespace=kube_namespace)
        if not deploy_ok:
            raise CancelException('Cannot wait until finishing populating data')

        logger.info('Checking if the populating process finished successfully or not')
        fmke_pop_pods = configurator.get_k8s_resources_name(resource='pod',
                                                            label_selectors='job-name=populate-data-without-prescriptions',
                                                            kube_namespace=kube_namespace)
        logger.debug('FMKe pod name: %s' % fmke_pop_pods[0])
        pop_result = dict()
        if len(fmke_pop_pods) > 0:
            log = configurator.get_k8s_pod_log(pod_name=fmke_pop_pods[0], kube_namespace=kube_namespace)
            last_line = log.strip().split('\n')[-1]
            logger.info('Last line of log: %s' % last_line)
            if 'Populated' in last_line and 'entities in' in last_line and 'avg' in last_line:
                result = log.strip().split('\n')[-1].split(' ')
                if len(result) == 8:
                    pop_result = result[4] + '\n' + result[6]
                if len(result) == 9:
                    pop_result = result[4] + '\n' + result[7]
                t = stabilizing_time
                logger.info('Waiting %s minutes for the replication and key distribution mechanisms between DCs' % t)
                sleep(t*60)
            else:
                raise CancelException('Populating process ERROR')
            logger.debug('FMKe populator result: \n%s' % pop_result)

        logger.debug('Modify the populate_data file to populate prescriptions')
        with open(os.path.join(fmke_yaml_path, 'populate_data.yaml.template')) as f:
            doc = yaml.safe_load(f)
        doc['metadata']['name'] = 'populate-data-with-onlyprescriptions'
        doc['spec']['template']['spec']['containers'][0]['args'] = [
            '-f --onlyprescriptions -p 1'] + fmke_IPs
        with open(os.path.join(fmke_yaml_path, 'populate_data.yaml'), 'w') as f:
            yaml.safe_dump(doc, f)

        logger.info('Populating the FMKe benchmark data with prescriptions')
        configurator.deploy_k8s_resources(files=[os.path.join(fmke_yaml_path, 'populate_data.yaml')],
                                          namespace=kube_namespace)

        logger.info('Waiting for populating data with prescriptions')
        configurator.wait_k8s_resources(resource='job',
                                        label_selectors='app=fmke_pop',
                                        timeout=timeout,
                                        kube_namespace=kube_namespace)
        logger.info('Checking if the populating process finished successfully or not')
        fmke_pop_pods = configurator.get_k8s_resources_name(resource='pod',
                                                            label_selectors='job-name=populate-data-with-onlyprescriptions',
                                                            kube_namespace=kube_namespace)
        logger.info('FMKe pod: %s' % fmke_pop_pods[0])
        if len(fmke_pop_pods) > 0:
            log = configurator.get_k8s_pod_log(
                pod_name=fmke_pop_pods[0], kube_namespace=kube_namespace)
            last_line = log.strip().split('\n')[-1]
            logger.info('Last line of log: %s' % last_line)
            if 'Populated' not in last_line:
                raise CancelException('Populating process ERROR')
            t = stabilizing_time
            logger.info('Waiting %s minutes for the replication and key distribution mechanisms between DCs' % t)
            sleep(t*60)
        logger.info('Finish populating data')

        return pop_result
        