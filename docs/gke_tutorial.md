# Working with Google Kubernetes Engine

This tutorial helps you to setup the authentication to connect to [Google Kubernetes Engine (GKE)](https://cloud.google.com/kubernetes-engine) and then shows some examples to create clusters and then perform some actions on these clusters.

If you do not have a GCP account, you can create one [free trial account](https://cloud.google.com/gcp/?utm_source=google&utm_medium=cpc&utm_campaign=emea-fr-all-en-dr-bkws-all-all-trial-e-gcp-1009139&utm_content=text-ad-none-any-DEV_c-CRE_167380635539-ADGP_Hybrid+%7C+AW+SEM+%7C+BKWS+~+EXA_M:1_FR_EN_General_Cloud_google+cloud+free+trial-KWID_43700053280219975-kwd-112926782887-userloc_1006410&utm_term=KW_google%20cloud%20free%20trial-NET_g-PLAC_&ds_rl=1242853&ds_rl=1245734&ds_rl=1242853&ds_rl=1245734&gclid=EAIaIQobChMI6JjWkffb6wIVeRkGAB3ajQbQEAAYASAAEgISbvD_BwE) to work with.

## Installation

Note: we use Python 3

To work with GKE, you need to install _GKE_ and _Kubernetes_ packages:

```
pip install google-cloud-container
pip install kubernetes
```

## Setup to authenticate with GCP from your laptop

Follow the instructions at [Createing a service account](https://cloud.google.com/docs/authentication/production#create_service_account) to create and download the private key.

To set up a Service Account authentication, you have to provide:

1. The path to your private key file in the new JSON (preferred) format.

2. Your “Project ID” (a string, not a numerical value).


## Example 1: Create Kubernetes clusters
In this example, we create Kubernetes clusters on GCP by using GKE.

First, edit the parameters in the provisioning config file `provisioning_config_gke.yaml` with your authentication information and your infrastructure requirements.

Then, run the following command to perform the provisioning process on GKE:
```
cd cloudal/examples/provision/
python provision_gke.py --system_config_file cloudal/examples/provisionign_config_files/provisioning_config_gke.yaml
```

The `provision_gke.py` script checks if the required clusters existed or not. If not, it creates clusters that is described in `provisioning_config_gke.yaml` file: cluter _test-1_ with 4 nodes in data center _europe-west3-a_, and cluter _test-2_ with 3 nodes in _us-central1-a_.

With GKE, all the provisioned clusters are kept alive until you deleted it, so that remember to delete your provision to release the resources (and not losing money) after finishing your testing.

## Example 2: Deploy an AntidoteDB cluster
In this example, after creating GKE clusters, we use Kubernetes to deploy an AntidoteDB cluster on each GKE cluster. This AntidoteDB cluster consists of 2 data centers that span in a Kubernetes cluster. We follow the instruction [here](https://github.com/AntidoteDB/AntidoteDB-documentation/blob/master/deployment/kubernetes/deployment.md) to deploy an AntidoteDB cluster by using Kubernetes.

First, you still have to describe your GKE authentication information and your clusters requirements in `provisioning_config_gke.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/antidote/
python config_antidotedb_cluster_env_gke.py --system_config_file cloudal/examples/provisionign_config_files/provisioning_config_gke.yaml --antidote_yaml_dir antidotedb_yaml_gce/ 
```

This `config_antidotedb_env_gke.py` script creates all required clusters, then performs the necessary setup and deploy the AntidoteDB from given yaml files. These antidote deployment yaml files are stored in the `antidotedb_yaml` directory. You can also modify the `config_host()` function in this script to install and configure your custom applications.

Now on your GKE you have running AntidoteDB clusters, you can connect to them and peform your testing.

## Options
You might want to use `--help` to see all available options:
```
usage: <program> [options] <arguments>

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