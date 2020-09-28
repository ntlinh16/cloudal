# Working with Kubernetes on Grid5000

This tutorial helps you to setup the authentication to connect to Grid5000 to deploy Kubernetes and then shows some examples to create Kubernetes clusters and then perform some actions on these clusters.

## Installation

Install _Kubernetes_ packages:

```
pip install kubernetes
```

## Set up to access nodes from outside Grid5000
To interact with Grid5000 system from your laptop (not from a Grid5000 frontend node), you have to perform the following steps:

##### 1. Set up an alias for the access to any hosts inside Grid5000. 

In `~/.ssh/config`, put these lines:
```
Host g5k
  User <your_g5k_username>
  Hostname access.grid5000.fr
  ForwardAgent no

Host *.g5k
  User <your_g5k_username>
  ProxyCommand ssh g5k -W "$(basename %h .g5k):%p"
  ForwardAgent no
```


##### 2. Set up `~/.execo.conf.py` configuration file 

```
import re
  
default_connection_params = {
    'user': '<username_to_connect_to_node_inside_g5k>',
    'keyfile': '<your_private_ssh_key_path>',
    'host_rewrite_func': lambda host: re.sub("\.grid5000\.fr$", ".g5k", host),
    'taktuk_gateway': 'g5k'
    }


default_frontend_connection_params = {
    'user': '<your_g5k_username>',
    'host_rewrite_func': lambda host: host + ".g5k"
    }

g5k_configuration = {
    'api_username': '<your_g5k_username>',
    }

```

These above configurations follow the instruction of: 

- [Running from outside Grid5000](http://execo.gforge.inria.fr/doc/latest-stable/execo_g5k.html#running-from-outside-grid5000)

- [Using SSH ProxyCommand to access hosts inside Grid5000](https://www.grid5000.fr/w/SSH#Using_SSH_ProxyCommand_feature_to_ease_the_access_to_hosts_inside_Grid.275000)


##### 3. Set up Grid5000 API authentification 

When you use cloudal for the first time with Grid5000, it asks your Grid5000 account password in your terminal:
```
Grid5000 API authentication password for user <your_Grid5000_username>
```

If you don't want to type your password everytime, you need to install `keyring` package to securely store your password on your working machine. Now you only need to type in your password once, and it is saved automatically for next times.
```
pip install keyring
```
And then have to you install the corresponding storage backend depends on your system, please follow this [link](https://pypi.org/project/keyring/) for more information on how to install them. 
In case it is not important to store your password securely for you, you can choose to install this simple backend, and your password will be stored as plain text:
```
pip install keyrings.alt
```
##### 4. Set up a VPN to connect to the Grid5000 network

Following the instruction [here](https://www.grid5000.fr/w/VPN?fbclid=IwAR1t_5TBkUhJ5LkMSO2BRkjp-CAksRfEKf4-HrBBxGkOa_yDXIRT40SWvRE) to create and download your Grid5000 VPN certificate.

If you create a Grid5000 certificate with passphrase, and you want to run your `openvpn` as a daemon, you shoule following these steps:
1. create a `auth` file with your VPN password:
```
touch auth | echo "<your VPN password>" > auth
```

2. add this line to `Grid5000_VPN.ovpn`:
```
askpass /path/to/your/auth/file
```
3. run openvpn as a daemon:
```
sudo openvpn --config Grid5000_VPN.ovpn --daemon
```


## Example 1: Create a Kubernetes clusters
In this example, we provision some nodes on Grid5000 system and then create a Kubernetes cluster from that nodes.

First, edit the provision config file in `cloudal/examples/provision/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command to create a Kubernetes:
```
cd cloudal/examples/provision/
python provision_g5k_k8s.py --system_config_file provisioning_config_g5k.yaml -k
```

This `provision_g5k.py` script makes a reservation with the description in the provision config file: 3 nodes on cluster *ecotype*, 1 node on *dahu* and 2 nodes on *paravance* in 1 hour. These nodes are deployed with the `debian10-x64-big` environment. You can see all the supported OS enviroments from Grid5000 [here](https://www.grid5000.fr/w/Getting_Started#Deploying_nodes_with_Kadeploy). After that, we install and setup kubernetes on these nodes to create a Kubernetes cluster

This cluster are kept alive after this script is terminated with `-k` option. Remember to delete the reservation to release the resoures after finishing your testing.


## Example 2: Deploy an AntidoteDB cluster

In this example, we deploy an AntidoteDB cluster on top of a Kubernetes cluster in Grid5000 system.

First, edit the provision config file in `cloudal/examples/provision/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command to create a Kubernetes:
```
cd cloudal/examples/configuration/
python config_antidotedb_cluster_g5k.py --system_config_file provisioning_config_g5k.yaml -k --antidote_yaml_dir antidotedb_yaml_g5k/ 
```

This cluster are kept alive after this script is terminated with `-k` option. Remember to delete the reservation to release the resoures after finishing your testing.

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
  -k                    keep the reservation alive after deploying.
  -o                    run the engine outside of grid5k charter
  -j OAR_JOB_IDS        the reserved oar_job_ids on grid5k. The format is
                        site1:oar_job_id1,site2:oar_job_id2,...
  --no-deploy-os        specify not to deploy OS on reserved nodes
```