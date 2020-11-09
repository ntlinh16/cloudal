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
