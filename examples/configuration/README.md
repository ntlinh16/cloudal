Here are some examples to configuring some applications/services on reserved hosts.

## Example 1: Configuring Docker on running hosts on Grid5000 (G5K)
In this example, we provision some nodes on G5K and then install Docker and configure the environment to ensure that Docker runs on these nodes.

First, you also have to edit the provisioning config file `provisioning_config_g5k.yaml` with your own requirements.

Then, run the configurator script to configure Docker container.

1. If you already had your reservation, you can quickly install Docker container on these nodes (without making a provisioning process again) by giving the OAR_JOB_IDs:

```
cd cloudal/examples/configuration/docker/
python config_docker_env_g5k.py -j nantes:<your_oar_job_id_on_nantes>,rennes:<your_oar_job_id_on_rennes>,grenoble:<your_oar_job_id_on_grenoble> --no-deploy-os -k 
```

This `config_docker_env_g5k.py` will install Docker on the provisioned nodes you give them.

2. If you do not have any running nodes on G5K, run the following command to provision and then configure nodes:
```
cd cloudal/examples/configuration/docker/
python config_docker_env_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```

In this case, the `config_docker_env_g5k.py` script makes a reservation for nodes then installs Docker container on them. You can modify the `config_host()` function in this script to install and configure your own necessary applications.

## Example 2: Configuring Docker on running hosts on Google Cloud Platform (GCP)
In this example, we provision some hosts on GCP and then install Docker and configure the environment to ensure that Docker runs on these hosts.

First, you also have to edit the provisioning config file `provisioning_config_gcp.yaml` with your own requirements.

Then, run the following command to provision and then configure hosts:

```
cd cloudal/examples/configuration/docker/
python config_docker_env_gcp.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gcp.yaml
```

the `config_docker_env_gcp.py` script makes a reservation for nodes then installs Docker container on them. You can modify the `config_host()` function in this script to install and configure your own necessary applications.

## Example 3: Configuring AntidoteDB on running hosts on G5K

In this example, after provisioning some nodes on G5K, we configure to ensure that AntidoteDB runs on these nodes.

First, you need to describe your infrastructure in `cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/antidote_env/
python config_antidotedb_env_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```

This `config_antidotedb_env_g5k.py` script makes a reservation for required nodes, then installs Docker container on them, next pulls the AntidoteDB docker image, and finally runs the AntidoteDB container. You can modify the `config_host()` function in this script to install and configure different applications.

## Example 4: Configuring AntidoteDB on running hosts on Google Cloud Platform (GCP)

In this example, after provisioning some hosts on GCP, we install Docker and configure to ensure that AntidoteDB runs on these hosts.

First, you still need to describe your infrastructure in  `cloudal/examples/provisioning_config_files/provisioning_config_gcp.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/antidote_env/
python config_antidotedb_env_gcp.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gcp.yaml -k
```

This `config_antidotedb_env_gcp.py` script makes a reservation for required hosts, then installs Docker on them, next pulls the AntidoteDB docker image, and finally runs the AntidoteDB container. You can modify the `config_host()` function in this script to install and configure your necessary applications.

Now on your GCP, you have the number of your required nodes running the AntidoteDB, you can connect to them and perform your testing.

## Example 5: Deploying an AntidoteDB cluster using Kubernetes on G5K

We follow the instruction [here](https://github.com/AntidoteDB/AntidoteDB-documentation/blob/master/deployment/kubernetes/deployment.md) to deploy an AntidoteDB cluster by using Kubernetes. 
In this example, we (1) provision some hosts on Grid5000 system; next (2) deploy a Kubernetes cluster on these nodes; and then (3) deploy an AntidoteDB cluster on top of the Kubernetes cluster.

To run this example from your laptop, remember to run VPN to access the Grid5000 system as shown in the instruction at [Working with Kubernetes on Grid5000](https://github.com/ntlinh16/cloudal/blob/master/docs/g5k_k8s_tutorial.md)

First, you should edit the provision config file at `cloudal/examples/provision/provisioning_config_g5k.yaml` with your infrastructure requirements. The _clusters_ information is the AntidoteDB cluster, each data center will be deployed on a cluster you provide. For example, in this experiment, we will create an AntidoteDB cluster includes 3 data centers (_econome_ - 3 instances of antidote, _dahu_ - 1 instance of antidote, _paravance_ - 2 instances of antidote)

Then, run the following command:
```
cd cloudal/examples/configuration/antidote_cluster/
python config_antidotedb_cluster_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml --antidote_yaml_dir antidotedb_yaml_g5k/ -k
```
The `config_antidotedb_cluster_g5k.py` script deploys a Kubernetes cluster with all the nodes. Then, using the Kubernetes deployment files in _antidotedb_yaml_g5k_ to deploy an AntidoteDB cluster.

With `-k` option, this cluster are kept alive after this script is terminated so that you can login to it for testing. Remember to delete the reservation to release the resources after finishing your testing.

While you are running the scrip, if there is an unexpected problem, and the Kubernetes cluster is already deployed successfully but antidoteDB cluster. You can re-run the script without making provisioning and deploying Kubernetes cluster again as follow:
```
cd cloudal/examples/configuration/antidote_cluster/
python config_antidotedb_cluster_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml --antidote_yaml_dir antidotedb_yaml_g5k/ -k -j <oar_job_ids> --no-deploy-os --kube-master <kube_master_host_name>
```


## Example 6: Deploying an AntidoteDB cluster on Google Kubernetes Engine (GKE)
In this example, after creating GKE clusters, we use Kubernetes to deploy an AntidoteDB cluster on each GKE cluster. This AntidoteDB cluster consists of 2 data centers that span in a Kubernetes cluster. We follow the instruction [here](https://github.com/AntidoteDB/AntidoteDB-documentation/blob/master/deployment/kubernetes/deployment.md) to deploy an AntidoteDB cluster by using Kubernetes.

First, you still have to describe your GKE authentication information and your clusters requirements in `cloudal/examples/provisioning_config_files/provisioning_config_gke.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/antidote_cluster/
python config_antidotedb_cluster_env_gke.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gke.yaml --antidote_yaml_dir antidotedb_yaml_gke/
```

This `config_antidotedb_env_gke.py` script creates all required clusters, then performs the necessary setup and deploy the AntidoteDB from given yaml files. These antidote deployment yaml files are stored in the `antidotedb_yaml` directory. You can also modify the `config_host()` function in this script to install and configure your custom applications.

Now on your GKE you have running AntidoteDB clusters, you can connect to them and perform your testing.
