# Working on Google Cloud Platform

This tutorial helps you to setup the authentication to connect to [Google Cloud Platform (GCP)](https://cloud.google.com) and then shows some examples to provision machines and then perform some actions on the reserved machines on .

If you do not have a GCP account, you can create one [free trial account](https://cloud.google.com/gcp/?utm_source=google&utm_medium=cpc&utm_campaign=emea-fr-all-en-dr-bkws-all-all-trial-e-gcp-1009139&utm_content=text-ad-none-any-DEV_c-CRE_167380635539-ADGP_Hybrid+%7C+AW+SEM+%7C+BKWS+~+EXA_M:1_FR_EN_General_Cloud_google+cloud+free+trial-KWID_43700053280219975-kwd-112926782887-userloc_1006410&utm_term=KW_google%20cloud%20free%20trial-NET_g-PLAC_&ds_rl=1242853&ds_rl=1245734&ds_rl=1242853&ds_rl=1245734&gclid=EAIaIQobChMI6JjWkffb6wIVeRkGAB3ajQbQEAAYASAAEgISbvD_BwE) to work with.


## Setup to access nodes on GCP from your laptop

Google supports two ways to authenticate from outside: using Service Accounts and User Accounts (or OAuth 2.0 client IDs). `cloudal` implements to support both authentication methods. You have to determine the correct authentication for your application.

#### 1. Service Account

Service Accounts are generally better suited for automated systems, cron jobs, etc. They should be used when access to the application/script is limited and needs to be able to run with limited intervention.

Follow the instructions at [Createing a service account](https://cloud.google.com/docs/authentication/production#create_service_account) to create and download the private key.

To set up a Service Account authentication, you have to provide:

1. The path to your private key file in the new JSON (preferred) format.

2. Your Service Account’s “Email Address”.

3. Your “Project ID” (a string, not a numerical value).


#### 2. User Account

User account authentication is often the better choice when creating an application that may be used by third-parties interactively. For example, a desktop application for managing VMs that would be used by many different people with different Google accounts.

Follow the instruction at [Creating your client credentials](https://cloud.google.com/docs/authentication/end-user#creating_your_client_credentials) to create and download your client secret.

For authentication, you will need the “Client ID”, the “Client Secret” and the “Project ID” (a string, not a numerical value).


## Example 1: Provision nodes 
In this example, we provision some nodes on GCP.

First, edit the parameters in the provisioning config file `provisioning_config_gcp.yaml` with your authentication information and your infrastructure requirements.

Then, run the following command to perform the provisioning process on GCP:
```
cd cloudal/examples/provision/
python provision_gcp.py --system_config_file provisioning_config_gcp.yaml
```

The `provision_gcp.py` script makes a reservation with the description in `provisioning_config_gcp.yaml` file : 1 node on datacenter _us-central1-a_ with the type of node is _e2-standard-2_, and 2 _f1-micro_ nodes on _europe-west3-a_. These nodes are deployed with the `debian-10-buster-v20200618` image. You can see all the supported images from GCP [here](https://cloud.google.com/compute/docs/images). 

With GCP, all the provisioned nodes are kept alive until you deleted it, so that remember to delete your nodes to release the resources (and not losing money) after finishing your testing.

If you do not have a free trial account (with $300 credit), you always create nodes with `f1-micro` type and it is free, check out the information in [Always Free usage limits](https://cloud.google.com/free/docs/gcp-free-tier#always-free-usage-limits)



