import os
import traceback
import base64
from tempfile import NamedTemporaryFile

from cloudal.utils import get_logger
from cloudal.action import performing_actions
from cloudal.provisioning.gke_provisioner import gke_provisioner

import json
from kubernetes import client, utils
from kubernetes.utils import FailToCreateError
from kubernetes.client.api_client import ApiClient

import google.auth
import google.auth.transport.requests


logger = get_logger()


class config_antidotedb_cluster_env_gke(performing_actions):
    def __init__(self, **kwargs):
        super(config_antidotedb_cluster_env_gke, self).__init__()
        self.args_parser.add_argument("--antidote_yaml_dir", dest="yaml_path",
                                      help="path to yaml file to deploy antidotedb cluster",
                                      default='',
                                      required=True,
                                      type=str)

    def provisioning(self):
        logger.info("Init provisioner: gke_provisioner")
        self.provisioner = gke_provisioner(config_file_path=self.args.config_file_path)
        logger.info("Making reservation")
        self.provisioner.make_reservation()
        self.clusters = self.provisioner.clusters
        self.configs = self.provisioner.configs

    def _deploy_antidote_cluster(self, kube_config):
        path = self.args.yaml_path
        api_client = ApiClient(kube_config)

        for file in os.listdir(path):
            if not file.endswith('.yaml'):
                continue
            logger.info('Deploying file %s' % file)
            try:
                utils.create_from_yaml(k8s_client=api_client, yaml_file=os.path.join(path, file))
                logger.debug('Deploy file %s successfully' % file)
            except FailToCreateError as e:
                for api_exception in e.api_exceptions:
                    body = json.loads(api_exception.body)
                    logger.error('Error: %s, because: %s' % (api_exception.reason, body['message']))

    def _get_credential(self, cluster):
        logger.info('Getting credetial for cluster %s' % cluster.name)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.configs['service_account_credentials_json_file_path']
        creds, projects = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        # creds, projects = google.auth.load_credentials_from_file(filename=self.configs['service_account_credentials_json_file_path'],
        #                                                         scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        kube_config = client.Configuration()
        kube_config.host = 'https://%s' % cluster.endpoint
        with NamedTemporaryFile(delete=False) as ca_cert:
            ca_cert.write(
                base64.b64decode(cluster.master_auth.cluster_ca_certificate))
        kube_config.ssl_ca_cert = ca_cert.name
        kube_config.api_key_prefix['authorization'] = 'Bearer'
        kube_config.api_key['authorization'] = creds.token
        logger.debug('Getting credetial for cluster : DONE')
        return kube_config

    def config_host(self):
        for cluster in self.clusters:
            logger.info('Deploying AntidoteDB on cluster %s' % cluster)
            kube_config = self._get_credential(cluster)
            self._deploy_antidote_cluster(kube_config)

    def run(self):
        logger.info("Starting create Kubernetes clusters")
        self.provisioning()
        logger.info("Finish create Kubernetes clusters")

        logger.info("Starting configure AntidoteDB on Kubernetes clusters")
        self.config_host()
        logger.info("Finish configure AntidoteDB on Kubernetes clusters")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_antidotedb_cluster_env_gke()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
