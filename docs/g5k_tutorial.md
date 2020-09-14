# Working on Grid5000 

This tutorial shows you how to setup the connnection to [Grid5000](https://www.grid5000.fr/w/Grid5000:Home) system from your laptop and then provision machines, install applications and conduct experiments on the reserved machines.

If you do not have a Grid5000 account, check out the [Grid5000:Get an account](https://www.grid5000.fr/w/Grid5000:Get_an_account)

## Setup to access nodes from outside Grid5000
To interact with Grid5000 system from your laptop (not from a Grid5000 frontend node), you have to perform the following steps:

##### 1. Setup an alias for the access to any hosts inside Grid5000. 

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


##### 2. Setup `~/.execo.conf.py` configuration file 

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

## Example 1: Provision nodes
In this example, we provision some nodes on Grid5000 system.

First, edit the provision config file in `cloudal/examples/provision/provisioning_config_g5k.yaml` with your infrastructure requirements.

Then, run the following command to perform the provisioning process:
```
cd cloudal/examples/provision/
python provision_g5k.py --system_config_file provisioning_config_g5k.yaml -k
```

This `provision_g5k.py` script makes a reservation with the description in the provision config file: 3 nodes on cluster *ecotype*, 1 node on *dahu* and 2 nodes on *paravance* in 1 hour. These nodes are deployed with the `debian10-x64-big` environment. You can see all the supported OS enviroments from Grid5000 [here](https://www.grid5000.fr/w/Getting_Started#Deploying_nodes_with_Kadeploy). 

These provisioned nodes are kept alive after this script is terminated (with `-k` option) so that you can connect to them. Remember to delete the reservation to release the resoures after finishing your testing.


## Example 2: Configure Docker on running nodes
In this example, we provision some nodes on Grid5000 and then install Docker and configure the environment to ensure that Docker runs on these nodes.

First, you also have to edit the provisioning config file `provisioning_config_g5k.yaml` with your own requirements.

Then, run the configurator script to configure Docker container.

1. If you already run Example 1, and you still have your resevation, you can quickly install Docker container on these nodes (without making a provisioning process again):

```
cd cloudal/examples/configuration/
python config_docker_env_g5k.py --system_config_file provisioning_config_g5k.yaml -j econome:<your_oar_job_id>,dahu:<your_oar_job_id>,graphite:<your_oar_job_id> -k 
```

This `config_docker_env_g5k.py` will install Docker container on the provisioned nodes you give them.

2. If you do not have any running nodes on Grid5000, run the following command to provision and then configure nodes:
```
cd cloudal/examples/configuration/
python config_docker_env_g5k.py --system_config_file provisioning_config_g5k.yaml -k
```

In this case, the `config_docker_env_g5k.py` script makes a reservation for nodes then installs Docker container on them. You can modify the `config_host()` function in this script to install and configure your own necessary applications.

## Example 3: Configure AntidoteDB on running nodes

This example is similar to the Example 2, after provisioning some nodes on Grid5000, it configures to ensure that AntidoteDB runs on these nodes.

First, you still need to describe your infrastructure in `provisioning_config_g5k.yaml` file.

Then, run the following command:
```
cd cloudal/examples/configuration/
python config_antidotedb_env_g5k.py --system_config_file provisioning_config_g5k.yaml -k
```

This `config_antidotedb_env_g5k.py` script makes a reservation for required nodes, then installs Docker container on them, next pulls the AntidoteDB docker image, and finally runs the AntidoteDB container. You can modify the `config_host()` function in this script to install and configure your necessary applications.


## Example 4: Perform an experiment: measuring Docker boottime on configured Grid5000 nodes
In this example, we perform a workflow to measure a Docker container boottime.

First, edit the provision config file `provisioning_config_g5k.yaml` and the experimental setting file `exp_setting_docker_boottime.yaml` depends on your experiment setup.

Then, run the following command to perform experiment:
```
cd cloudal/examples/experiments/boottime/docker/
python docker_boottime_g5k.py --system_config_file provisioning_config_g5k.yaml --exp_setting_file exp_setting_docker_boottime.yaml -c /path/to/your/result/dir -k
```

The `docker_boottime_g5k.py` script (i) makes a reservation for nodes base on descreibe in `provisioning_config_g5k.yaml`; then (ii) installs Docker contianer on provisioned nodes and (iii) measures Docker boot time with different scenarios (base on parameters in `exp_setting_docker_boottime.yaml`) and saves all the results in the indicated result directory.

You can modify the `_perform_experiments()` function in the script to design your own experiment workflow scenarios.

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