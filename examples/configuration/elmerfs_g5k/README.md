# Deploying elmerfs with an AntidoteDB backend on Grid5000
This example deploys [elmerfs](https://github.com/scality/elmerfs) which is a file system using an [AntidoteDB](https://www.antidoteDB.eu/) cluster as backend on Gri5000 system.


## Introduction

This example implements a provisioning process based on the required infrastructure, it deploys a Kubernetes cluster, and then deploys AntidoteDB clusters using Kubernetes. After that, `elmerfs` is installed on hosts that run AntidoteDB instances. The infrastructure is shown in the following Figure:

## How to run the experiment

### 1. Prepare the system config file

There are two types of config files to perform this experiment.

#### AntidoteDB Kubernetes deployment files 

I use Kubernetes deployment files to deploy an AntidoteDB cluster for this experiment. These files are provided in folder [antidotedb_yaml](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs/antidotedb_yaml) and they work well for this experiment scenario. Check and modify these template files if you need any special configurations for AntidoteDB.
#### Experiment environment config file
You need to clarify three following information in the `exp_setting_elmerfs_eval_g5k.yaml` file.

* Infrastructure requirements: includes the number of clusters, name of cluster and the number of nodes for each cluster you want to provision on Grid5k system; which OS you want to deploy on reserved nodes; when and how long you want to provision nodes; etc.

* Parameters: is a list of experiment parameters that represent different aspects of the system that you want to examine. Each parameter contains a list of possible values of that aspect. For example, I want to achieve a statistically significant results so that each experiment will be repeated 5 times  with parameter `iteration: [1..5]`. In this example, we only deploy the elmerfs without performing any scenario, so that we can ignore this filed.

* Experiment environment settings: the path to Kubernetes deployment files for Antidote; the elmerfs version information that you want to deploy; the topology of an AntidoteDB cluster; etc.


### 2. Run the experiment
If you are running this experiment on your local machine, remember to run the VPN to [connect to Grid5000 system from outside](https://github.com/ntlinh16/cloudal/blob/master/docs/g5k_k8s_setting.md).

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
