import os
from time import sleep

from google.cloud.container_v1.services.cluster_manager import ClusterManagerClient
from google.cloud.container_v1.types import Cluster

from cloudal.provisioning.provisioning import cloud_provisioning
from cloudal.utils import get_logger

logger = get_logger()


class gke_provisioner(cloud_provisioning):
    # def __init__(self, config_file_path):
    def __init__(self, **kwargs):
        self.config_file_path = kwargs.get('config_file_path')
        self.clusters = list()

        super(gke_provisioner, self).__init__(config_file_path=self.config_file_path)

    def _get_gke_client(self):
        service_account_credentials_json_file_path = os.path.expanduser(self.configs['service_account_credentials_json_file_path'])
        cluster_manager_client = ClusterManagerClient.from_service_account_json(service_account_credentials_json_file_path)
        return cluster_manager_client

    def _check_clusters(self, project_id, list_zones):
        clusters_ok = dict()
        clusters_ko = dict()

        cluster_manager_client = self._get_gke_client()
        for zone in list_zones:
            list_clusters = cluster_manager_client.list_clusters(project_id=project_id, zone=zone)

            for cluster in list_clusters.clusters:
                key = '%s:%s' % (zone, cluster.name)
                if cluster.status == 2:
                    clusters_ok[key] = cluster
                else:
                    clusters_ko[key] = cluster

        return clusters_ok, clusters_ko

    def make_reservation(self):
        cluster_manager_client = self._get_gke_client()
        project_id = self.configs['project_id']
        list_zones = list()
        for cluster in self.configs['clusters']:
            list_zones.append(cluster['data_center'])

        logger.info("Validating Kubernetes clusters on GCP")
        clusters_ok, clusters_ko = self._check_clusters(project_id, list_zones)

        for cluster in self.configs['clusters']:
            key = '%s:%s' % (cluster['data_center'], cluster['cluster_name'])
            if key in clusters_ok:
                logger.info('Cluster %s on data center %s already existed and is running' % (cluster['cluster_name'], cluster['data_center']))
                self.clusters.append(clusters_ok[key])
            elif key in clusters_ko:
                logger.info('Cluster %s on data center %s already existed but not running' % (cluster['cluster_name'], cluster['data_center']))
            else:
                logger.info("Deploying cluster %s: %s nodes on data center %s" %
                            (cluster['cluster_name'], cluster['n_nodes'], cluster['data_center']))
                cluster_specs = Cluster(mapping={'name': cluster['cluster_name'],
                                                 'locations': [cluster['data_center']],
                                                 'initial_node_count': cluster['n_nodes']})
                cluster_manager_client.create_cluster(cluster=cluster_specs,
                                                      parent='projects/%s/locations/%s' % (project_id, cluster['data_center']))

                i = 0
                while i < 15:
                    c = cluster_manager_client.get_cluster(project_id=project_id,
                                                           zone=cluster['data_center'],
                                                           cluster_id=cluster['cluster_name'])
                    if c.status == 2:
                        self.clusters.append(c)
                        break
                    i += 1
                    sleep(15)

        logger.info("Deploying Kubernetes clusters on GCP: DONE")
