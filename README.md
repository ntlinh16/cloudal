<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/cloudal_logo.png" width="300"/>
    <br>
<p>

<h3 align="center">
<p> cloudal is a module to help design and perform experiments on different cloud systems
</h3>

# Installation
1. Clone the repository from www.github.com, and change directory into the project.
```
git clone https://github.com/ntlinh16/cloudal.git
cd cloudal
```
2. Activate your virtualenv (optional), and install the requirements.
```
pip install -U -r requirements.txt
```

3. Set the `PYTHONPATH` to the directory of `cloudal`.
```
export PYTHONPATH=/path/to/your/cloudal
```
You can add the above line to your `.bashrc` to have the env variable set on new shell session.



# Usages
## 1. Provision nodes on Grid5000
In this example, we provision some nodes on Grid5000 system.

First, edit the provision config file `provisioning_config_g5k.yaml` with your desired infrastructure description.

Then run the following command to make the provision:
```
cd cloudal/examples/provision/
python provision_g5k.py --system_config_file provisioning_config_g5k.yaml -k
```

The `provision_g5k.py` script makes a reservation with the description on the provision config file `provisioning_config_g5k.yaml`. We will have 10 nodes on *econome*, 3 nodes on *dahu* and 7 nodes on *graphite* clusters in 3 hours. These nodes are deployed with `debian10-x64-big` environment. 
The nodes are kept alive after the script is terminated (with `-k` option) so that you can connect to them.

## 2. Configure softwares on running Grid5000 nodes
In this example, we provision some nodes on Grid5000 and then install Docker on these nodes.

First, we also need to edit the provision config file `provisioning_config_g5k.yaml` with your desired infrastructure description.

Then run the following command to provision and configure nodes:
```
cd cloudal/examples/configuration/
python config_docker_env_g5k.py --system_config_file provisioning_config_g5k.yaml -k
```

This `config_docker_env_g5k.py` script makes a reservation for nodes then install Docker on them.

You can modify the `config_host()` function in the script to install your necessary applications.


## 3. Perform experiment: measuring Docker boottime on configured Grid5000 nodes
In this example, we provision some nodes on Grid5000 and then install Docker on these nodes.

First, edit the provision config file `provisioning_config_g5k.yaml` and the experimental setting file `exp_setting_docker_boottime.yaml` depends on your experiment setup.

Then run the following command to perform experiment:
```
cd cloudal/examples/experiments/boottime/docker/
python docker_boottime_g5k.py --system_config_file provisioning_config_g5k.yaml --exp_setting_file exp_setting_docker_boottime.yaml -c /path/to/your/result/dir -k
```

The `docker_boottime_g5k.py` script (i) makes a reservation for nodes; then (ii) installs Docker on them and (iii) measures Docker boot time with different scenarios and save all the result in a result directory.

You can modify the `_perform_experiments()` function in the script to design your own experiment scenarios.