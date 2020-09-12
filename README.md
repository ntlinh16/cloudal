<p align="center">
    <a href="https://github.com/ntlinh16/cloudal">
        <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/cloudal_logo.png" width="300"/>
    </a>
    <br>
<p>

<h4 align="center"> cloudal is a module helps to design and perform experiments on different cloud systems 🤗
</h4>

<p align="center">
<b><i>Currently support:</i></b>
    <a target="_blank" href="https://www.grid5000.fr">
        <img align="middle" src="https://www.grid5000.fr/mediawiki/resources/assets/logo.png" width="70"/>
    </a>
    <a target="_blank" href="https://cloud.google.com">
        <img align="middle" src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/google_logo.png" width="140"/>
    </a>
</p>



# Introduction

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/architecture.png" width="600"/>
    <br>
<p>

The main goal of `cloudal` is to perform large-scale reproducible experiments and collecting results automatically on different cloud systems. cloudal is composed of:  
- a performing actions script that conducts user defined experiment workflow
- a cloud provisioning module that reserves nodes from cloud systems

In order to setup a cloud system for running rigorous experiments, we usually follow a typical experiment workflow which is (1) provisioning machines; (2) configuring the enviroment; (3) writing the experiment workflow scripts. 
cloudal implements this workflow and provide templates so that users can customize to their needs. 

Users modify the `Performing Actions` script to perform one or multiple actionsm they are free to choose which actions they want to incorporate in their script (i.e. users may just want to provision hosts, or perform experiments which require all the actions). There are three main components in this script:

- __provisioner__: Each provisioner is an instance of `Cloud Provisioning` module, and implements steps to perform the provisioning process by calling the respective API of that cloud. For Grid5000, we use `execo-g5k` library while we utilize `libcloud` to interact with various public cloud systems. By leveraging libcloud, we do not have to work with each separated SDK cloud system and also provide the extensibility to other cloud providers.
- __configurator__: this module contains some ready-to-use configurators that we already implemented to set up the environment for a specific application (e.g, Docker, Kubernetes, QEMU-KVM, etc.) on the provisioned machines.
- __experimenter__: users have to wirte their own experimenter to describe sequential steps to perform their specific experimental scenarios. Users can execute this workflow with different input parameters and repeat it the number of times on the same environment in order to obtain a statistically significant result. In this way, users can perform reproducible and repetitive experiments automatically. We use `execo` as an experiment toolkits which offers a Python API for asynchronous control of local or remote, standalone or parallel, unix processes. It is especially well suited for quick and easy scripting workflows of parallel/distributed operations on local or remote hosts: automate a scientific workflow, conduct computer science experiments, perform automated tests, etc.


# Installation
This repo uses Python 2.7+ due to `execo`.

The following are steps to install cloudal. If you want to test it without affecting your system, you may want to run it in a virtual enviroment. If you're unfamiliar with Python virtual environments, check out the [user guide](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/).

1. Clone the repository.
```
git clone https://github.com/ntlinh16/cloudal.git
```
2. Activate your virtualenv (optional), and then install the requirements.
```
cd cloudal
pip install -U -r requirements.txt
```

3. In other to run `execo`, we need to install `taktuk`
```
apt-get install taktuk
```

4. Set the `PYTHONPATH` to the directory of `cloudal`.
```
export PYTHONPATH=$PYTHONPATH:/path/to/your/cloudal
```
You can add the above line to your `.bashrc` to have the env variable set on new shell session.

5. Set up the SSH configuration for execo:

If you want to specify the SSH key to use with cloudal, you have to modify the execo configuration file. 

In `~/.execo.conf.py`, put these lines:

```
default_connection_params = {
    'user': '<username_to_connect_to_nodes_inside_cloud_system>',
    'keyfile': '<your_private_ssh_key_path>',
    }
```
for example:
```
default_connection_params = {
    'user': 'root',
    'keyfile': '~/.ssh/cloudal_key/id_rsa',
    }
```

Execo reads `~/.execo.conf.py` file to setup the connection. If this file is not exist, execo uses the default values that you can find more detail [here](http://execo.gforge.inria.fr/doc/latest-stable/execo.html#configuration)

# Tutorials

We provide some quick tutorials to get you started with `cloudal`:
- [Working on Grid5000](https://github.com/ntlinh16/cloudal/blob/master/docs/g5k_tutorial.md)
- [Working on Google Cloud Platform](https://github.com/ntlinh16/cloudal/blob/master/docs/gcp_tutorial.md)


