Here are some examples to perform the provisioning process on different cloud system.

## Example 1: Provisioning some hosts on Grid5000 (G5k)
In this example, we provision some nodes on Grid5000 system.

First, edit the provision config file in `cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command to perform the provisioning process on G5K:
```
cd cloudal/examples/provision/
python provision_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```

This `provision_g5k.py` script makes a reservation with the description in the provision config file: 3 nodes on cluster *ecotype*, 1 node on *dahu* and 2 nodes on *paravance* in 1 hour. These nodes are deployed with the `debian10-x64-big` environment. You can see all the supported OS environments from Grid5000 [here](https://www.grid5000.fr/w/Advanced_Kadeploy#Search_and_deploy_an_existing_environment). 

These reserved nodes are kept alive after this script is terminated with `-k` option. You can connect to these nodes and install or set up your applications manually or you just need to give these nodes to _cloudal_ and it will configure them as your wish (see [examples in the Configuration](https://github.com/ntlinh16/cloudal/tree/master/examples/configuration)).

Remember to delete the reservation to release the resources after finishing your testing.

## Example 2: Provisioning a Kubernetes cluster on Grid5000 (G5K)

You cannot provision a Kubernetes cluster directly from Grid5000. In this example, we help you to do that. We first provision some nodes on Grid5000 system and then create a Kubernetes cluster from these nodes using kubeadm.

First, you should edit the provisioning config file at `cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command:
```
cd cloudal/examples/provision/
python provision_g5k_k8s.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```

The `provision_g5k_k8s.py` script makes a reservation with the clusters described in _provisioning_config_g5k.yaml_ file: 3 nodes on cluster *ecotype*, 1 node on *dahu* and 2 nodes on *paravance* in 1 hour. These nodes are deployed with the `debian10-x64-big` environment. You can see all the supported OS environments from Grid5000 [here](https://www.grid5000.fr/w/Getting_Started#Deploying_nodes_with_Kadeploy). After that, we install kubelet, kubeadm, kubectl and then perform some setups on these nodes to create a Kubernetes cluster.

This cluster are kept alive after this script is terminated with `-k` option. Remember to delete the reservation to release the resources after finishing your testing.
## Example 3: Provisioning Docker Swarm cluster on Grid5000 (G5K)

You cannot provision a Docker Swarm cluster directly from Grid5000. In this example, we help you do that. We first provision some nodes on Grid5000 system and then create a Docker Swarm cluster from these nodes.

First, you should edit the provisioning config file at `cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command:
```
cd cloudal/examples/provision/
python provision_docker_swarm_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```
## Example 4: Provisioning some hosts on Google Cloud Platform (GCP)
In this example, we provision some hosts on GCP.

First, edit the parameters in the provisioning config file `cloudal/examples/provisioning_config_files/provisioning_config_gcp.yaml` with your authentication information and your infrastructure requirements.

Then, run the following command to perform the provisioning process on GCP:
```
cd cloudal/examples/provision/
python provision_gcp.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gcp.yaml
```

The `provision_gcp.py` script makes a reservation with the description in `provisioning_config_gcp.yaml` file : 1 host on data center _us-central1-a_ with the type of host is _e2-standard-2_, and 2 _f1-micro_ hosts on _europe-west3-a_. These hosts are deployed with the given `cloud_provider_image`. You can see all the supported images from GCP [here](https://cloud.google.com/compute/docs/images). 

With GCP, all the provisioned hosts are kept alive until you deleted it, so that remember to delete your hosts to release the resources (and not losing money) after finishing your testing.

If you do not have a free trial account (with $300 credit), you can always create hosts with `f1-micro` type and it is free, check out the information in [Always Free usage limits](https://cloud.google.com/free/docs/gcp-free-tier#always-free-usage-limits)

## Example 5: Provisioning Docker Swarm cluster on Google Cloud Platform (GCP)

You cannot provision a Docker Swarm cluster directly on GCP. In this example, we help you do that. We first provision some nodes on Grid5000 system and then create a Docker Swarm cluster from these nodes.

First, you should edit the provisioning config file at `cloudal/examples/provisioning_config_files/provisioning_config_gcp.yaml` with your infrastructure requirements.

Then, run the following command:
```
cd cloudal/examples/provision/
python provision_docker_swarm_gcp.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gcp.yaml
```

## Example 6: Provisioning Kubernetes clusters on Google Cloud Engine (GKE)
In this example, we create some Kubernetes clusters on Google Cloud by using GKE.

First, edit the parameters in the provisioning config file `cloudal/examples/provisioning_config_files/provisioning_config_gke.yaml` with your authentication information and your infrastructure requirements.

Then, run the following command to perform the provisioning process on GKE:
```
cd cloudal/examples/provision/
python provision_gke.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gke.yaml
```

The `provision_gke.py` script checks if the required clusters existed or not. If not, it creates clusters that is described in `provisioning_config_gke.yaml` file: cluster _test-1_ with 4 nodes in data center _europe-west3-a_, and cluster _test-2_ with 3 nodes in _us-central1-a_.

With GKE, all the provisioned clusters are kept alive until you deleted it, so that remember to delete your provision to release the resources (and not losing money) after finishing your testing.

## Example 7: Provisioning some hosts on Microsoft Azure
In this example, we provision some hosts on Azure.

First, edit the parameters in the provisioning config file `cloudal/examples/provisioning_config_files/provisioning_config_azure.yaml` with your authentication information and your infrastructure requirements.

Then, run the following command to perform the provisioning process on Azure:
```
cd cloudal/examples/provision/
python provision_azure.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_azure.yaml
```

The `provision_azure.py` script makes a reservation with the description in `provisioning_config_azure.yaml` file : 1 host on region _eastus_ with the type of host is Standard_A4_v2;1 Standard_F2s_v2 host and 1 Standard_A4_v2 hosts on _westeurope_.

With azure, all the provisioned hosts are kept alive until you deleted it, so that remember to delete your hosts to release the resources (and not losing money) after finishing your testing.

## Example 8: Provisioning some hosts on OVHCloud
In this example, we provision some nodes on Grid5000 system.

First, edit the provision config file in `cloudal/examples/provisioning_config_files/provisioning_config_ovh.yaml` with your authentication and infrastructure requirements.

Then, run the following command to perform the provisioning process on OVHCloud:
```
cd cloudal/examples/provision/
python provision_ovh.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_ovh.yaml
```

Remember to delete the reservation to release the resources after finishing your testing.

## Example 9: Provisioning a Kubernetes cluster on OVHCloud

You can provision a Kubernetes cluster directly on OVHCloud. But the Kubernetes cluster has all nodes located on one region. In this example, we help you to provision a multiple site Kubernetes cluster on OVHCloud. We first provision some nodes on OVHCloud and then create a Kubernetes cluster from these nodes using kubeadm.

First, you should edit the provisioning config file at `cloudal/examples/provisioning_config_files/provisioning_config_ovh.yaml` with your authentication and infrastructure requirements.

Then, run the following command:
```
cd cloudal/examples/provision/
python provision_ovh_k8s.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml
```

The `provision_ovh_k8s.py` script makes a reservation with the clusters described in _provisioning_config_ovh.yaml_ file. After that, we install Docker, kubelet, kubeadm, kubectl and then perform some setups on these nodes to create a Kubernetes cluster.

Remember to delete the reservation to release the resources after finishing your testing.
## Options
You might want to use `--help` to see more supported options:

For example: `python provision_g5k.py --help`

```
usage: <program> [options] <arguments>

engine: provision_g5k

optional arguments:
  -h, --help            show this help message and exit
  -l LOG_LEVEL          log level (int or string). Default = inherit execo
                        logger level
  -L                    copy stdout / stderr to log files in the experiment
                        result directory. Default = False
  -R                    redirect stdout / stderr to log files in the
                        experiment result directory. Default = False
  -M                    when copying or redirecting outputs, merge stdout /
                        stderr in a single file. Default = False
  -c DIR                use experiment directory DIR
  --system_config_file CONFIG_FILE_PATH
                        the path to the provisioning configuration file.
  --exp_setting_file EXP_SETTING_FILE_PATH
                        the path to the experiment setting file.
  -k                    keep the reservation alive after deploying.
  -o                    run the engine outside of grid5k charter
  -j OAR_JOB_IDS        the reserved oar_job_ids on grid5k. The format is
                        site1:oar_job_id1,site2:oar_job_id2,...
  --no-deploy-os        specify not to deploy OS on reserved nodes
  -r                    only make a reservation, no deploy hosts
```