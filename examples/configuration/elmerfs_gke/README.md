# Running elmerfs with an AntidoteDB backend on Google Cloud
This experiment performs some tests (which not designed yet) of [elmerfs](https://github.com/scality/elmerfs) which is a file system using an [AntidoteDB](https://www.antidoteDB.eu/) cluster as backend.


## Introduction

The steps of this experiment follow [the general experiment flowchart of cloudal](https://github.com/ntlinh16/cloudal/blob/master/docs/technical_detail.md#an-experiment-workflow-with-cloudal).

The `create_combs_queue()` function is not called because the parameters are not designed yet.

The `setup_env()` function (1) makes a reservation for the required infrastructure; and then (2) configuring these hosts by: deploys a Kubernetes cluster to manage a AntidoteDB cluster; elmerfs is deploy on hosts which run AntidoteDB instances.

The `run_workflow()` is not designed yet.

## How to run the experiment

### 1. Prepare the system config file

There are two types of config files to perform this experiment.

#### Setup environment config file
The system config file provides three following information:

* Infrastructure requirements: includes the number of clusters, name of cluster and the number of nodes for each cluster you want to provision on Google Cloud System; which OS you want to deploy on reserved nodes;  etc.

* Parameters: is a list of experiment parameters that represent different aspects of the system that you want to examine. Each parameter contains a list of possible values of that aspect. For example, I want to achieve a statistically significant results so that each experiment will be repeated 5 times  with parameter `iteration: [1..5]`.

* Experiment environment settings: the path to Kubernetes deployment files for Antidote; the elmerfs version information that you want to deploy; the topology of an AntidoteDB cluster; etc.

You need to clarify all these information in `exp_setting_elmerfs_gke.yaml` file

#### Experiment config files 

I use Kubernetes deployment files to deploy an AntidoteDB cluster for this experiment. These files are provided in folder [antidotedb_yaml](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs/antidotedb_yaml) and they work well for this experiment. Check and modify these template files if you need any special configurations for AntidoteDB.

### 2. Run the experiment
Remember to follow setting instruction to [run cloudal on GKE] (https://github.com/ntlinh16/cloudal/blob/master/docs/gke_setting.md).

Then, run the following command:

```
cd cloudal/examples/experiment/elmerfs/
python elmerfs_gke.py --system_config_file exp_setting_elmerfs_gke.yaml
```

### 3. Re-run the experiment
If the script is interrupted by unexpected reasons. You can re-run the experiment and it will continue with the list of combinations left in the queue. You have to provide the same result directory of the previous one. If your reserved hosts/clusters still valid, you just run the same above command:

```
cd cloudal/examples/experiment/elmerfs/
python elmerfs_gke.py --system_config_file exp_setting_elmerfs.yaml
```
