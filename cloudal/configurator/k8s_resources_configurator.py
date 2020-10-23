import os
import json

from cloudal.utils import get_logger, execute_cmd

from kubernetes import utils
from kubernetes.utils import FailToCreateError
from kubernetes.client.api_client import ApiClient

logger = get_logger()


class k8s_resources_configurator(object):
    """
    """

    def deploy_k8s_resources(self, path=None, files=None, kube_config=None, namespace="default"):
        if not kube_config:
            api_client = ApiClient(kube_config)
        else:
            api_client = ApiClient()

        if path is not None:
            files = list()
            for file in os.listdir(path):
                if file.endswith('.yaml'):
                    files.append(file)
        for file in files:
            logger.info('--> Deploying file %s' % file.split('/')[-1])
            try:
                utils.create_from_yaml(k8s_client=api_client, yaml_file=os.path.join(path, file), namespace=namespace)
                logger.debug('Deploy file %s successfully' % file)
            except FailToCreateError as e:
                for api_exception in e.api_exceptions:
                    body = json.loads(api_exception.body)
                    logger.error('Error: %s, because: %s' % (api_exception.reason, body['message']))

    def wait_k8s_resources(self, resource, label_selectors,
                           kube_master, kube_namespace='default', timeout='60s', is_continue=False):
        '''Wait until specified k8s resources are completed or ready

        Parameters
        ----------
        resource: string
            the name of the resource (job, pod, etc.)

        label_selectors: string
            the k8s labels used to filter to resource, the format is: key1=value1,key2=value2,...

        kube_master: string
            the hostname of the kube master node

        kube_namespace: string
            the k8s namespace to perform the wait of k8s resources operation on,
            the default namespace is 'default'

        timeout: string
            the length of time to wait before giving up, the format looks like: 60s, 1m, etc.

        is_continue: bool
            when set to True no exception raises even if the wait operation fails,
            raise exception otherwise
        '''
        wait_condition = 'complete' if resource == 'job' else 'Ready'
        cmd = 'kubectl wait --for=condition={condition} {resource} -l "{labels}" --timeout={timeout} -n {namespace}'.format(
            condition=wait_condition,
            resource=resource,
            labels=label_selectors,
            timeout=timeout,
            namespace=kube_namespace
        )
        execute_cmd(cmd, kube_master, is_continue=is_continue)
