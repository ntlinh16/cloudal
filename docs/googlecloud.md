# Working with Google Cloud Platform



This tutorial helps you to setup the authentication to connect to [Google Cloud Platform (GCP)](https://cloud.google.com) and then shows some examples to provision machines and then perform some actions on the reserved machines on .

If you do not have a GCP account, you can create one [free trial account](https://cloud.google.com/gcp/?utm_source=google&utm_medium=cpc&utm_campaign=emea-fr-all-en-dr-bkws-all-all-trial-e-gcp-1009139&utm_content=text-ad-none-any-DEV_c-CRE_167380635539-ADGP_Hybrid+%7C+AW+SEM+%7C+BKWS+~+EXA_M:1_FR_EN_General_Cloud_google+cloud+free+trial-KWID_43700053280219975-kwd-112926782887-userloc_1006410&utm_term=KW_google%20cloud%20free%20trial-NET_g-PLAC_&ds_rl=1242853&ds_rl=1245734&ds_rl=1242853&ds_rl=1245734&gclid=EAIaIQobChMI6JjWkffb6wIVeRkGAB3ajQbQEAAYASAAEgISbvD_BwE) to work with.


## Setup to access nodes on GCP from your laptop

Google supports two ways to authenticate from outside: using Service Accounts and User Accounts (or OAuth 2.0 client IDs). `cloudal` implements to support both authentication methods. You have to determine the correct authentication flow for your application.

#### 1. Service Account 

Service Accounts are generally better suited for automated systems, cron jobs, etc. They should be used when access to the application/script is limited and needs to be able to run with limited intervention.

To set up Service Account authentication, you will need to download the corresponding private key file in either the new JSON (preferred) format, or the legacy P12 format.

1. Follow the instructions at https://cloud.google.com/docs/authentication/production#create_service_account to create and download the private key.

2. You will need the Service Account’s “Email Address” and the path to the key file for authentication.

3. You will also need your “Project ID” (a string, not a numerical value) that can be found by clicking on the “Overview” link on the left sidebar.


#### 2. User Account

Installed Application authentication is often the better choice when creating an application that may be used by third-parties interactively. For example, a desktop application for managing VMs that would be used by many different people with different Google accounts.

To set up Installed Account authentication:

1. Go to the Google Developers Console
2. Select your project
3. In the left sidebar, go to “APIs & auth”
4. Click on “Credentials” then “Create New Client ID”
5. Select “Installed application” and “Other” then click “Create Client ID”
6. For authentication, you will need the “Client ID” and the “Client Secret”
7. You will also need your “Project ID” (a string, not a numerical value) that can be found by clicking on the “Overview” link on the left sidebar.



## Example 1: Provision nodes 
In this example, we provision some nodes on GCP.


## Example 2: Configure Docker on running nodes
In this example, we provision some nodes on GCP and then install Docker and configure to ensure that Docker runs on these nodes.


## Example 3: Configure AntidoteDB on running nodes