# Benchmarking the AntidoteDB cluster using FMKe on Grid5000 system
This experiment performs the [FMKe benchmark](https://github.com/ntlinh16/FMKe) to test the performance of an [AntidoteDB](https://www.antidotedb.eu/) cluster which is deployed on Grid5000 system by using Kubernetes.

## Introduction

The flow of the experiment follows the flowchart [here](https://github.com/ntlinh16/cloudal#an-experiment-flow-with-cloudal).

The `create_combs_queue()` function creates a list of combinations from the given parameters in the _exp_setting_fmke_antidotedb_ file which is described more in detail later.

The `setup_env()` function (1) makes a reservation for the required infrastructure; and then (2) deploys a Kubernetes cluster to managed all services of this experiment (which are deployed by using containers).

The `run_workflow()` function performs 6 steps of a run of this experiment scenario which described detail in the following figure. With a successful run, a directory of result will be created.

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/exp_fmke_antidotedb_workflow.png" width="600"/>
    <br>
<p>
                

## How to run the experiment

### 1. Prepare config files:
There are two types of config files to perform this experiment.

#### Setup environment config file
This system config file provides three following information:

* Infrastructure requirements: includes the number of clusters, name of cluster and the number of nodes for each cluster you want to provision on Grid5k system; which OS you want to deploy on reserved nodes; when and how long you want to provision nodes; etc.

* Experiment environment information: the topology of an AntidoteDB cluster; the path to experiment configuration files; etc.

* Parameters: is a list of experiment parameters that represent different aspects of the system that you want to examine. Each parameter contains a list of possible values of that aspect. For example, I want to examine the effect of the number of concurrent clients that connect to an AntidoteDB database, so I define a parameter such as `concurrent_clients: [16, 32]`

You need to clarify all these information in `exp_setting_fmke_antidotedb.yaml` file

#### Experiment config files 

This experiment need to deploy an AntidoteDB cluster and FMKe as a benchmark, I am using k8s deployment files to deploy them. So you need to provide these config files.
I already provided the template files which work well with this experiment in folder [exp_config_files](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/antidotedb/exp_config_files). If you do not require special configurations, you do not have to modify these files.

### 2. Run the experiment
If you are running this experiment on your local machine, remember to run the VPN to connect to Grid5000 system from outside before run the following command:

```
cd cloudal/examples/experiment/antidotedb/
python antidotedb_fmke_g5k.py --system_config_file exp_setting_fmke_antidotedb.yaml -k &>  result/test.log
```
Then, you can watch the log by:

```
tail -f cloudal/examples/experiment/antidotedb/result/test.log
```

### 3. Re-run the experiment
If the script is interrupted by unexpected reasons. You can re-run the experiment and it will continue with the list of combinations left in the queue. You have to provide the same result directory of the previous one. There are two possible cases:

1. If your reserved hosts are dead, you just run the same above command:
```
cd cloudal/examples/experiment/antidotedb/
python antidotedb_fmke_g5k.py --system_config_file exp_setting_fmke_antidotedb.yaml -k &>  result/test2.log
```

2. If your reserved hosts are still alive, you can give it to the script:
```
cd cloudal/examples/experiment/antidotedb/
python antidotedb_fmke_g5k.py --system_config_file exp_setting_fmke_antidotedb.yaml -k -j < site1:oar_job_id1,site2:oar_job_id2,...> --no-deploy-os --kube-master <the host name of the kubernetes master> &> result/test2.log
```

### 4. Results of the experiments

A figure of the results of this experiment can be found [here](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/antidotedb/results)


## Image used in the experiments

I use Docker images to pre-build the environment for FMKe services. All images are on Docker repository.

To deploy AntidoteDB cluster:

* **antidotedb/antidote:latest**
* **peterzel/antidote-connect**

To deploy FMKe benchmark:

* **ntlinh/fmke**
* **ntlinh/fmke_pop**
* **ntlinh/fmke_client**