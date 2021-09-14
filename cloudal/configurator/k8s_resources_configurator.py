import os
import json
from functools import partial
from time import sleep

from cloudal.utils import get_logger

from kubernetes import utils, client
from kubernetes.stream import stream
from kubernetes.utils import FailToCreateError
from kubernetes.client.api_client import ApiClient

logger = get_logger()


class k8s_resources_configurator(object):
    """
    """

    def deploy_k8s_resources(self, path=None, files=None, kube_config=None, namespace="default"):
        """Deploy k8s resources on a k8s cluster from deployment yaml files

        Parameters
        ----------
        path: string
            the path to the directory which stores all the deployment yaml files

        files: list
            a list of yaml files to use for deployment

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        namespace: string
            a namespace for k8s working with

        """
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        if path is not None:
            files = list()
            for file in os.listdir(path):
                if file.endswith('.yaml'):
                    files.append(os.path.join(path, file))
        for file in files:
            logger.info('--> Deploying file %s' % file.split('/')[-1])
            try:
                utils.create_from_yaml(k8s_client=api_client, yaml_file=file, namespace=namespace)
                logger.debug('Deploy file %s successfully' % file)
            except FailToCreateError as e:
                for api_exception in e.api_exceptions:
                    body = json.loads(api_exception.body)
                    logger.error('Error: %s, because: %s' % (api_exception.reason, body['message']))

    def wait_k8s_resources(self, resource, label_selectors, kube_config=None, kube_namespace='default', timeout=300):
        '''Wait until specified k8s resources are completed or ready in a namespace

        Parameters
        ----------
        resource: string
            the name of the resource (job, pod, etc.)

        label_selectors: string
            the k8s labels used to filter to resource, the format is: key1=value1,key2=value2,...

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        kube_namespace: string
            the k8s namespace to perform the wait of k8s resources operation on,
            the default namespace is 'default'

        timeout: int
            the number of seconds to wait before giving up

        Returns
        -------
        bool
            True: wait successfully
            False: wait unsuccessfully

        '''
        MAX_ATTEMPT = 10
        SLEEP_TIME = int(1.0 + timeout / MAX_ATTEMPT)
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        if resource == 'job':
            wait_condition = 'complete'
            v1 = client.BatchV1Api(api_client)
            list_resources = v1.list_namespaced_job
        elif resource == 'pod':
            wait_condition = 'ready'
            v1 = client.CoreV1Api(api_client)
            list_resources = v1.list_namespaced_pod
        else:
            logger.info('Not support this type of resource: %s' % resource)
            return False

        for attempt in range(MAX_ATTEMPT):
            count = 0
            resources = list_resources(label_selector=label_selectors, namespace=kube_namespace)
            if not resources:
                logger.info('Cannot find %s with labels %s in namespace %s' %
                            (resource, label_selectors, kube_namespace))
                sleep(SLEEP_TIME)
                continue
            for r in resources.items:
                count += 1
                if r.status.conditions is None:
                    logger.debug('%s %s status is None' % (resource, r.metadata.name))
                    break

                for condition in r.status.conditions:
                    if condition.status == 'True' and condition.type.lower() == wait_condition:
                        logger.debug('Status of %s %s: %s' %
                                     (resource, r.metadata.name, condition.type))
                        count -= 1
            if count == 0:
                logger.debug('All %s are up' % resource)
                return True
            sleep(SLEEP_TIME)
            logger.debug('Attempt #%s' % (attempt + 1))
        logger.info('Timeout! Cannot wait until all %s are up' % resource)
        return False

    def get_k8s_pod_log(self, pod_name, kube_config=None, kube_namespace='default'):
        '''Get the log of a given pod

        Parameters
        ----------
        pod_name: string
            the name of the pod to get log

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        kube_namespace: string
            the k8s namespace to perform the k8s resources operation on,
            the default namespace is 'default'

        Returns
        -------
        string
        the content of the log
        '''

        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        v1 = client.CoreV1Api(api_client)
        log = v1.read_namespaced_pod_log(name=pod_name, namespace=kube_namespace)

        return log

    def get_k8s_resources(self, resource, label_selectors='', kube_config=None, kube_namespace='default'):
        '''List all k8s resources in a namespace

        Parameters
        ----------
        resource: string
            the name of the resource (job, pod, etc.)

        label_selectors: string
            the k8s labels used to filter to resource, the format is: key1=value1,key2=value2,...

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        kube_namespace: string
            the k8s namespace to perform the k8s resources operation on,
            the default namespace is 'default'

        Returns
        -------
        kubernetes resource type: V1JobList, V1PodList, etc.
        (ref: https://github.com/kubernetes-client/python/blob/master/kubernetes/README.md#documentation-for-models)

        '''
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        if resource == 'job':
            v1 = client.BatchV1Api(api_client)
            list_resources = partial(v1.list_namespaced_job, namespace=kube_namespace)
        elif resource == 'pod':
            v1 = client.CoreV1Api(api_client)
            list_resources = partial(v1.list_namespaced_pod, namespace=kube_namespace)
        elif resource == 'namespace':
            v1 = client.CoreV1Api(api_client)
            list_resources = v1.list_namespace
        elif resource == 'node':
            v1 = client.CoreV1Api(api_client)
            list_resources = v1.list_node
        elif resource == 'service':
            v1 = client.CoreV1Api(api_client)
            list_resources = v1.list_service_for_all_namespaces
        else:
            logger.info('Not support this type of resource: %s' % resource)
            return False

        resources = list_resources(label_selector=label_selectors)
        return resources

    def get_k8s_resources_name(self, resource, label_selectors='', kube_config=None, kube_namespace='default'):
        '''List all k8s resources' names in a namespace

        Parameters
        ----------
        resource: string
            the name of the resource (job, pod, etc.)

        label_selectors: string
            the k8s labels used to filter to resource, the format is: key1=value1,key2=value2,...

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        kube_namespace: string
            the k8s namespace to perform the k8s resources operation on,
            the default namespace is 'default'

        Return
        ------
        list of strings
            list of resources' names
        '''
        resources = self.get_k8s_resources(resource=resource,
                                           label_selectors=label_selectors,
                                           kube_config=kube_config,
                                           kube_namespace=kube_namespace)
        return [r.metadata.name for r in resources.items]

    def get_k8s_endpoint_ip(self, service_name, kube_config=None, kube_namespace='default'):
        '''Get the endpoint ip of a k8s service

        Parameters
        ----------
        service_name: string
            the name of the service

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        kube_namespace: string
            the k8s namespace to perform the k8s resources operation on,
            the default namespace is 'default'

        Returns
        -------
        string
            the ip of a k8s endpoint
        '''
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        v1 = client.CoreV1Api(api_client)
        endpoints = v1.read_namespaced_endpoints(name=service_name, namespace=kube_namespace)
        if endpoints and endpoints.subsets:
            if endpoints.subsets[0].addresses:
                return endpoints.subsets[0].addresses[0].ip
        return None

    def create_namespace(self, namespace=None, kube_config=None):
        """Create a namespace in a k8s cluster

        Parameters
        ----------
        namespace: string
            a namespace for k8s working with

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        Returns
        -------
        V1Namespace (https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Namespace.md)
        """
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        v1 = client.CoreV1Api(api_client)
        logger.debug('Creating namespace % s' % namespace)
        for ns in v1.list_namespace().items:
            if ns.metadata.name == namespace:
                logger.warning('Namespace %s already exists' % namespace)
                return None

        body = client.V1Namespace()
        body.metadata = client.V1ObjectMeta(name=namespace)
        return v1.create_namespace(body)

    def delete_namespace(self, namespace=None, kube_config=None):
        """Delete a namespace from a k8s cluster

        Parameters
        ----------
        namespace: string
            a namespace for k8s working with

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        Returns
        -------
        bool
            True: delete successfully
            False: delete unsuccessfully
        """
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        v1 = client.CoreV1Api(api_client)
        logger.debug('Deleting namespace %s' % namespace)
        for ns in v1.list_namespace().items:
            if ns.metadata.name == namespace:
                v1.delete_namespace(name=namespace)
                logger.debug('Waiting for namespace %s to be deleted' % namespace)
                for i in range(100):
                    for ns in v1.list_namespace().items:
                        if ns.metadata.name == namespace:
                            sleep(5)
                            break
                    else:
                        return True

        else:
            logger.warning('Namespace %s does not exist' % namespace)
            return False

    def set_labels_node(self, nodename, labels, kube_config=None):
        """Create a namespace in a k8s cluster

        Parameters
        ----------
        namespace: str
            a namespace for k8s working with

        labels: string
            the new k8s labels used to label this node, the format is: key1=value1,key2=value2,...

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        Returns
        -------
        V1Node (https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Node.md)
            if label node successfully
        None
            if label node unsuccessfully
        """
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        v1 = client.CoreV1Api(api_client)
        logger.debug('Label node %s with %s' % (nodename, labels))
        for node in v1.list_node().items:
            if node.metadata.name == nodename:
                break
        else:
            logger.warning('Node %s does not exist' % nodename)
            return None

        body = {
            'metadata': {
                'labels': dict()
            }
        }
        for label in labels.strip().split(','):
            key, val = label.strip().split('=')
            body['metadata']['labels'][key] = val

        return v1.patch_node(name=nodename, body=body)

    def execute_command(self, pod_name, command, kube_config=None, kube_namespace='default'):
        """Execute a command on a pod

        Parameters
        ----------
        pod_name: string
            the name of the pod to run the command

        command: string
            the command to run on the pod

        kube_config: kubernetes.client.configuration.Configuration
            the configuration to the kubernetes cluster

        kube_namespace: string
            the k8s namespace to perform the k8s resources operation on,
            the default namespace is 'default'

        Returns
        -------
        string
            the std output when run the command in the pod
        """
        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        v1 = client.CoreV1Api(api_client)
        logger.debug('Run command %s on pod %s' % (command, pod_name))

        if ' ' in command:
            command = command.split()
        logger.debug('command = %s' % command)

        return stream(v1.connect_get_namespaced_pod_exec,
                      pod_name,
                      namespace=kube_namespace,
                      command=command,
                      stderr=True,
                      stdin=False,
                      stdout=True,
                      tty=False,
                      _preload_content=True)

    def create_configmap(self, kube_config=None, configmap=None, file=None, namespace="default", configmap_name="Configmap_name"):
        if configmap is None and file is None:
            raise Exception(
                "Please provide either a configmap or a file to create a Kubernetes configmap")

        if kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        # Configureate ConfigMap metadata
        metadata = client.V1ObjectMeta(name=configmap_name, namespace=namespace)

        v1 = client.CoreV1Api(api_client)
        if file is not None:
            file_name = file.split('/')[-1]
            logger.info('Creating configmap object from file %s' % file_name)
            # Get File Content
            with open(file, 'r') as f:
                file_content = f.read()
            data = {file_name: file_content}
            # Instantiate the configmap object
            configmap = client.V1ConfigMap(api_version="v1",
                                           kind="ConfigMap",
                                           data=data,
                                           metadata=metadata)
        try:
            logger.info('Deploying configmap')
            v1.create_namespaced_config_map(namespace=namespace,
                                            body=configmap,)
            logger.debug('Deploy configmap successfully')
        except FailToCreateError as e:
            for api_exception in e.api_exceptions:
                body = json.loads(api_exception.body)
                logger.error('Error: %s, because: %s' % (api_exception.reason, body['message']))
