# Deploying elmerfs with an AntidoteDB backend on Grid5000
This example deploys [elmerfs](https://github.com/scality/elmerfs) which is a file system using an [AntidoteDB](https://www.antidoteDB.eu/) cluster as backend on Gri5000 system.


## Introduction

This example implements a provisioning process based on the required infrastructure, it deploys a Kubernetes cluster, and then deploys AntidoteDB clusters using Kubernetes. After that, `elmerfs` is installed on hosts that run AntidoteDB instances.

## How to run the deployment script

### 1. Prepare the deployment and config files

There are three types of files to perform this deployment.

#### AntidoteDB Kubernetes deployment files 

I use Kubernetes deployment files to deploy an AntidoteDB cluster. These files are provided in folder [antidotedb_yaml](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs/antidotedb_yaml) and they work well for this experiment scenario. Check and modify these template files if you need any special configurations for AntidoteDB.

#### Monitoring Kubernetes deployment files 

[antidote_stats](https://github.com/AntidoteDB/antidote_stats) provides the configuration files for Grafana and Prometheus deployment. I use Kubernetes deployment files that make use of those configuration files to deploy Grafana and Prometheus services. These template files are provided in folder [monitoring_yaml](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs/monitoring_yaml).
#### Experiment environment config file
You need to clarify the following information in the `exp_setting_elmerfs_eval_g5k.yaml` file.

* Infrastructure requirements: includes the number of clusters, name of cluster and the number of nodes for each cluster you want to provision on Grid5k system; which OS you want to deploy on reserved nodes; when and how long you want to provision nodes; etc.

* Experiment environment settings: the path to Kubernetes deployment files for AntidoteDB and monitoring services; the elmerfs version information that you want to deploy; the topology of an AntidoteDB cluster; etc.


### 2. Run the deployment
If you are running this experiment on your local machine, remember to run the VPN to [connect to Grid5000 system from outside](https://github.com/ntlinh16/cloudal/blob/master/docs/g5k_k8s_setting.md).

Then, run the following command:

```
cd cloudal/examples/experiment/elmerfs/
python elmerfs_g5k.py --system_config_file exp_setting_elmerfs_g5k.yaml -k --monitoring
```
Arguments:

* `-k`: after finishing all the runs of the experiment, all provisioned nodes on Gris5000 will be kept alive so that you can connect to them, or if the experiment is interrupted in the middle, you can use these provisioned nodes to continue the experiments. This mechanism saves time since you don't have to reserve and deploy nodes again. If you do not use `-k`, when the script is finished or interrupted, all your reserved nodes will be deleted.
* `--monitoring`: the script will deploy [Grafana](https://grafana.com/) and [Prometheus](https://prometheus.io/) as an AntidoteDB monitoring system. If you use this option, please make sure that you provide the corresponding Kubernetes deployment files. You can connect to the url provided in the log to access the monitoring UI (i.e., `http://<kube_master_ip>:3000`). The default account credential is `admin/admin`. When login successfully, you can search for `Antidote` to access the pre-defined AntidoteDB dashboard.
<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/grafana_example_screenshot.png" width="650"/>
    <br>
<p>

### 3. Re-run the deployment
When the script is interrupted by unexpected reasons, you can re-run the deployment. 

If your reserved nodes are dead (due to timeout or running without `-k` option), you have to perform again the same above command. 

If your reserved nodes are still alive, you can give it to the script (to ignore the provisioning process):

```
cd cloudal/examples/experiment/elmerfs/
python elmerfs_g5k.py --system_config_file exp_setting_elmerfs_g5k.yaml -k --monitoring -j <site1:oar_job_id1,site2:oar_job_id2,...> --no-deploy-os --kube-master <the host name of the kubernetes master>
```
By this way, the script re-deploys the AntidoteDB clusters, elmerfs instances and monitoring system on the pre-deployed infrastructure which are the provisioned nodes and the deployed Kubernetes cluster.
