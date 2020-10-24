## Introduction
This experiment performs the FMKe benchmark to test the performance of an AntidoteDB cluster which is deployed on Grid5000 system by using Kubernetes.

### Workflow
The workflow of this experiment is as follow:
<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/exp_fmke_antidotedb.png" width="600"/>
    <br>
<p>
            
            Step 1: clean_k8s_resources()
            
            Step 2: config_antidote()
            
            Step 3: config_fmke()
            
            Step 4: config_fmke_pop()
            
            Step 5: perform_exp()
            
            Step 6: save_results()

## How to run the experiment

### 1. Preparing config files:
There are two types of config files to perform this experiment.


#### Provisioning and experimnenting config file
The first one is the config file to prepare the infrastructure, this file provides the following infomation:

* Infrastructure information: cluster and how many nodes for each cluster you want to provision, which OS you want to eploy on reserved nodes; when and how long you want to provision nodes; etc.

* Experiment environment information: the topology of an AntidoteDB cluster; the path to experimennt configuration files; etc.

You need to clarify all these information in `config_antidote_fmke.yaml` file

#### Experiment config files 

This experiment need to deploy an AntidoteDB cluster and FMKe as a benchmark, we are using k8s deployment files to deploy them. So you need to provide these config files.
We already provided the template files which work well with this experiment
If you do not need special things, you do not have to modify these files

### 2. Run the experiment
Run the following command:

```
python cloudal/examples/experiment/antidotedb/antidotedb_fmke_g5k.py --system_config_le cloudal/examples/experiment/antidotedb/config_antidote_fmke.yaml -k &> cloudal/examples/experiment/antidotedb/good_result_23Oct/test.log
```


### 3. Results of the experiments

A figure of the results of this experiment can be found at [here](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/antidotedb/results)

How to get the results
HOw to plot the results
Where is the results? (file store)

## Image used in the experiments

I use Docker images to pre-build the environment for FMKe services.

To deploy AntidoteDB cluster:

* **antidotedb/antidote:latest**
* **peterzel/antidote-connect**

To deploy FMKe service:

* **ntlinh/fmke**
* **ntlinh/fmke_pop**
* **ntlinh/fmke_client**