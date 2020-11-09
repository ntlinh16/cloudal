

## Example 1: Configure Docker on running nodes on G5k
In this example, we provision some nodes on Grid5000 and then install Docker and configure the environment to ensure that Docker runs on these nodes.

First, you also have to edit the provisioning config file `provisioning_config_g5k.yaml` with your own requirements.

Then, run the configurator script to configure Docker container.

1. If you already run Example 1, and you still have your resevation, you can quickly install Docker container on these nodes (without making a provisioning process again):

```
cd cloudal/examples/configuration/docker/
python config_docker_env_g5k.py -j nantes:<your_oar_job_id_on_nantes>,rennes:<your_oar_job_id_on_rennes>,grenoble:<your_oar_job_id_on_grenoble> --no-deploy-os -k 
```

This `config_docker_env_g5k.py` will install Docker on the provisioned nodes you give them.

2. If you do not have any running nodes on Grid5000, run the following command to provision and then configure nodes:
```
cd cloudal/examples/configuration/docker/
python config_docker_env_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```

In this case, the `config_docker_env_g5k.py` script makes a reservation for nodes then installs Docker container on them. You can modify the `config_host()` function in this script to install and configure your own necessary applications.

## Example 2: Configure AntidoteDB on running nodes on G5K

This example is similar to the Example 2, after provisioning some nodes on Grid5000, it configures to ensure that AntidoteDB runs on these nodes.

First, you still need to describe your infrastructure in `provisioning_config_g5k.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/antidote/
python config_antidotedb_env_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```

This `config_antidotedb_env_g5k.py` script makes a reservation for required nodes, then installs Docker container on them, next pulls the AntidoteDB docker image, and finally runs the AntidoteDB container. You can modify the `config_host()` function in this script to install and configure your necessary applications.


## Example 3: Configure an AntidoteDB cluster on G5K

In this example, we deploy an AntidoteDB cluster on top of a Kubernetes cluster in Grid5000 system.

First, edit the provision config file in `cloudal/examples/provision/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command to create a Kubernetes:
```
cd cloudal/examples/configuration/antidote/
python config_antidotedb_cluster_g5k.py --system_config_file cloudal/examples/provisionign_config_files/provisioning_config_g5k.yaml --antidote_yaml_dir antidotedb_yaml_g5k/ -k
```

This cluster are kept alive after this script is terminated with `-k` option. Remember to delete the reservation to release the resoures after finishing your testing.


## Example 4: Configure AntidoteDB on GCP

In this example, after provisioning some nodes on GCP, we install Docker and configure to ensure that AntidoteDB runs on these nodes.

First, you still need to describe your infrastructure in  `provisioning_config_gcp.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/antidote/
python config_antidotedb_env_gcp.py --system_config_file cloudal/examples/provisionign_config_files/provisioning_config_gcp.yaml -k
```

This `config_antidotedb_env_gcp.py` script makes a reservation for required nodes, then installs Docker on them, next pulls the AntidoteDB docker image, and finally runs the AntidoteDB container. You can modify the `config_host()` function in this script to install and configure your necessary applications.

Now on your GCP, you have the number of your required nodes running the AntidoteDB, you can connect to them and perform your testing.



## Example 5 : Deploy an AntidoteDB cluster on GKE
In this example, after creating GKE clusters, we use Kubernetes to deploy an AntidoteDB cluster on each GKE cluster. This AntidoteDB cluster consists of 2 data centers that span in a Kubernetes cluster. We follow the instruction [here](https://github.com/AntidoteDB/AntidoteDB-documentation/blob/master/deployment/kubernetes/deployment.md) to deploy an AntidoteDB cluster by using Kubernetes.

First, you still have to describe your GKE authentication information and your clusters requirements in `provisioning_config_gke.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/antidote/
python config_antidotedb_cluster_env_gke.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gke.yaml --antidote_yaml_dir antidotedb_yaml_gke/
```

This `config_antidotedb_env_gke.py` script creates all required clusters, then performs the necessary setup and deploy the AntidoteDB from given yaml files. These antidote deployment yaml files are stored in the `antidotedb_yaml` directory. You can also modify the `config_host()` function in this script to install and configure your custom applications.

Now on your GKE you have running AntidoteDB clusters, you can connect to them and peform your testing.
