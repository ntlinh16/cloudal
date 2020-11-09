## Example 1: Provision nodes on G5k
In this example, we provision some nodes on Grid5000 system.

First, edit the provision config file in `cloudal/examples/provision/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command to perform the provisioning process:
```
cd cloudal/examples/provision/
python provision_g5k.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_g5k.yaml -k
```

This `provision_g5k.py` script makes a reservation with the description in the provision config file: 3 nodes on cluster *ecotype*, 1 node on *dahu* and 2 nodes on *paravance* in 1 hour. These nodes are deployed with the `debian10-x64-big` environment. You can see all the supported OS enviroments from Grid5000 [here](https://www.grid5000.fr/w/Getting_Started#Deploying_nodes_with_Kadeploy). 

These provisioned nodes are kept alive after this script is terminated with `-k` option. You can connect to these nodes and install or set up your applications manually or you just need to give these nodes to _cloudal_ and it will configure them as your wish (see Example 2).

Remember to delete the reservation to release the resoures after finishing your testing.

## Example 2: Provision a Kubernetes cluster on G5K

In this example, we provision some nodes on Grid5000 system and then create a Kubernetes cluster from that nodes.

First, edit the provision config file in `cloudal/examples/provision/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command to create a Kubernetes:
```
cd cloudal/examples/provision/
python provision_g5k_k8s.py --system_config_file cloudal/examples/provisionign_config_files/provisioning_config_g5k.yaml -k
```

This `provision_g5k.py` script makes a reservation with the description in the provision config file: 3 nodes on cluster *ecotype*, 1 node on *dahu* and 2 nodes on *paravance* in 1 hour. These nodes are deployed with the `debian10-x64-big` environment. You can see all the supported OS enviroments from Grid5000 [here](https://www.grid5000.fr/w/Getting_Started#Deploying_nodes_with_Kadeploy). After that, we install and setup kubernetes on these nodes to create a Kubernetes cluster

This cluster are kept alive after this script is terminated with `-k` option. Remember to delete the reservation to release the resoures after finishing your testing.


## Example 3: Provision nodes on GCP
In this example, we provision some nodes on GCP.

First, edit the parameters in the provisioning config file `provisioning_config_gcp.yaml` with your authentication information and your infrastructure requirements.

Then, run the following command to perform the provisioning process on GCP:
```
cd cloudal/examples/provision/
python provision_gcp.py --system_config_file cloudal/examples/provisionign_config_files/provisioning_config_gcp.yaml
```

The `provision_gcp.py` script makes a reservation with the description in `provisioning_config_gcp.yaml` file : 1 node on datacenter _us-central1-a_ with the type of node is _e2-standard-2_, and 2 _f1-micro_ nodes on _europe-west3-a_. These nodes are deployed with the given `cloud_provider_image`. You can see all the supported images from GCP [here](https://cloud.google.com/compute/docs/images). 

With GCP, all the provisioned nodes are kept alive until you deleted it, so that remember to delete your nodes to release the resources (and not losing money) after finishing your testing.

If you do not have a free trial account (with $300 credit), you always create nodes with `f1-micro` type and it is free, check out the information in [Always Free usage limits](https://cloud.google.com/free/docs/gcp-free-tier#always-free-usage-limits)


## Example 4: Provision Kubernetes clusters on GKE
In this example, we create Kubernetes clusters on GCP by using GKE.

First, edit the parameters in the provisioning config file `provisioning_config_gke.yaml` with your authentication information and your infrastructure requirements.

Then, run the following command to perform the provisioning process on GKE:
```
cd cloudal/examples/provision/
python provision_gke.py --system_config_file cloudal/examples/provisioning_config_files/provisioning_config_gke.yaml
```

The `provision_gke.py` script checks if the required clusters existed or not. If not, it creates clusters that is described in `provisioning_config_gke.yaml` file: cluter _test-1_ with 4 nodes in data center _europe-west3-a_, and cluter _test-2_ with 3 nodes in _us-central1-a_.

With GKE, all the provisioned clusters are kept alive until you deleted it, so that remember to delete your provision to release the resources (and not losing money) after finishing your testing.


## Options
You might want to use `--help` to see all available options:
```
usage: <program> [options] <arguments>

engine: provision_g5k_k8s

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