# Running elmerfs with an AntidoteDB backend on Grid5000
This experiment performs some tests (which not designed yet) of [elmerfs](https://github.com/scality/elmerfs) which is a file system using an [AntidoteDB](https://www.antidoteDB.eu/) cluster as backend.


## Introduction

The steps of this experiment follows the general experiment flowchart of cloudal [here](https://github.com/ntlinh16/cloudal/blob/master/docs/technical_detail.md#an-experiment-workflow-with-cloudal).

The `create_combs_queue()` function is not called because the parameters are not designed yet.

The `setup_env()` function (1) makes a reservation for the required infrastructure; and then (2) configuring these hosts by: deploys a Kubernetes cluster to manage a AntidoteDB cluster and installs elmerfs is deploy on hosts which connect to AntidoteDB cluster.

The `run_workflow()` is not designed yet.

## How to run the experiment

### 1. Prepare the system config file

There are two types of config files to perform this experiment.

#### Setup environment config file
The system config file provides three following information:

* Infrastructure requirements: includes the number of clusters, name of cluster and the number of nodes for each cluster you want to provision on Grid5k system; which OS you want to deploy on reserved nodes; when and how long you want to provision nodes; etc.

* Experiment environment information: the topology of an AntidoteDB cluster; the path to experiment configuration files; etc.

* Parameters: is a list of experiment parameters that represent different aspects of the system that you want to examine. Each parameter contains a list of possible values of that aspect. For example, I want to examine the effect of the number of concurrent clients that connect to an AntidoteDB database, so I define a parameter such as `concurrent_clients: [16, 32]`

You need to clarify all these information in `exp_setting_elmerfs.yaml` file

#### Experiment config files 

This experiment needs to deploy an AntidoteDB cluster, and I am using Kubernetes deployment files to deploy them. I already provided the template files which work well for this experiment in folder [antidotedb_yaml](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs/antidotedb_yaml). If you do not require special configurations for AntidoteDB, you do not have to modify these files.

### 2. Run the experiment
If you are running this experiment on your local machine, first, remember to run the VPN to connect to Grid5000 system from outside (see instruction [here](https://github.com/ntlinh16/cloudal/blob/master/docs/g5k_k8s_setting.md)).

Then, run the following command:

```
cd cloudal/examples/experiment/elmerfs/
python elmerfs_g5k.py --system_config_file exp_setting_elmerfs_g5k.yaml -k
```

### 3. Re-run the experiment
If the script is interrupted by unexpected reasons. You can re-run the experiment and it will continue with the list of combinations left in the queue. You have to provide the same result directory of the previous one. There are two possible cases:

1. If your reserved hosts are dead, you just run the same above command:
```
cd cloudal/examples/experiment/elmerfs/
python elmerfs_g5k.py --system_config_file exp_setting_elmerfs.yaml -k
```

2. If your reserved hosts are still alive, you can give it to the script (to ignore the provisioning process):

```
cd cloudal/examples/experiment/elmerfs/
python elmerfs_g5k.py --system_config_file exp_setting_elmerfs_g5k.yaml -k -j <site1:oar_job_id1,site2:oar_job_id2,...> --no-deploy-os --kube-master <the host name of the kubernetes master>
```
