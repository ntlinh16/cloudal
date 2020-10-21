import os
import json

from cloudal.utils import get_logger

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
