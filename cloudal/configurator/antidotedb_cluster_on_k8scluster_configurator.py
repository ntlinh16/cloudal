import os
import json

from cloudal.utils import get_logger

from kubernetes import utils
from kubernetes.utils import FailToCreateError
from kubernetes.client.api_client import ApiClient


logger = get_logger()


class antidotedb_configurator(object):
    """
    """

    def __init__(self, path, kube_config=None):
        self.kube_config = kube_config
        self.path = path

    def deploy_antidotedb_cluster(self):
        if not self.kube_config:
            api_client = ApiClient(self.kube_config)
        else:
            api_client = ApiClient()

        for file in os.listdir(self.path):
            if not file.endswith('.yaml'):
                continue
            logger.info('Deploying file %s' % file)
            try:
                utils.create_from_yaml(k8s_client=api_client, yaml_file=os.path.join(self.path, file))
                logger.debug('Deploy file %s successfully' % file)
            except FailToCreateError as e:
                for api_exception in e.api_exceptions:
                    body = json.loads(api_exception.body)
                    logger.error('Error: %s, because: %s' % (api_exception.reason, body['message']))
