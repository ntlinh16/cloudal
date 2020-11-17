<p align="center">
    <a href="https://github.com/ntlinh16/cloudal">
        <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/cloudal_logo.png" width="300"/>
    </a>
    <br>
<p>

<h4 align="center"> cloudal is a module that helps to design and perform experiments on different cloud systems 🤗
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

--------------------------------------------------------------------------------

- [Introduction](#introduction)
  - [An experiment workflow with cloudal](#an-experiment-workflow-with-cloudal)
  - [Architecture](#architecture)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Tutorials](#tutorials)
  - [Provisioning](#provisioning)
  - [Configuring](#configuring)
  - [Experimenting](#experimenting)

# Introduction

## An experiment workflow with cloudal

To set up a cloud system for running rigorous experiments, we usually follow a typical workflow that consists of the following steps: (1) provisioning some machines; (2) configuring the environment; (3) performing the experiment workflow. The main goal of `cloudal` is to help you to perform a [full factorial experiment](https://en.wikipedia.org/wiki/Factorial_experiment) workflow and collect the results automatically on different cloud systems in a large-scale and reproducible manner. The following figure presents a general experiment flowchart on a specific cloud system when you use _cloudal_.

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/experiment_flowchart.png" width="650"/>
    <br>
<p>

First of all, _cloudal_ performs the `create_combinations_queue()` function to create a list of combinations. So what is a combinations list? Let say, when you perform an experiment, you want to examine various aspects of the system, so that you have to run the same experiment repeatedly with different setting of parameters. Each parameter contains a list of possible values of an aspect. For example, the disk type (SSD or HDD or remote storage) can be one of the parameters. _cloudal_ will combine all the given parameters to create a list of combinations. You just need to define all the parameters that you want to test for your experiment, then _cloudal_ will manage and ensure the run of all combinations automatically.

Next, _cloudal_ run the `setup_env()` function to prepare the environment on reserved machines with the clients' requirements. The `setup_env()` function (1) provisions the required infrastructure; and (2) installs and deploys all the necessary packages/services.

The `run_workflow()` function takes a combination from the queue as the input, and then run an user-defined experiment workflow with that combination info. This repeats until we have no combinations left. If a run of a combination fails, the combination is put back to the queue to be run later. The _run_workflow_ function needs to be implemented for different experiments. The progress of running one combination is checkpointed on the disk so that if a run is interrupted, the experiment can continue the current progress when you re-run.

If all combinations are performed, the experiment is done. While we are performing experiments, if the reserved nodes are dead (due to end of reservation time or unexpected problems), cloudal will execute `setup_env()` to prepare the infrastructure again.

## Architecture

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/architecture.png" width="800"/>
    <br>
<p>

The design of _cloudal_ is a _Performing Actions_ class that inherits the `execo_engine`. 
We use `execo` as an experiment toolkit which offers a Python API for asynchronous control of local or remote, standalone or parallel, unix processes. It is especially well suited for quick and easy scripting workflows of parallel/distributed operations on local or remote hosts: automate a scientific workflow, conduct computer science experiments, perform automated tests, etc.

_cloudal_ provides 3 main modules to helps user perform their actions (i.e., provisioning, configuring or experimenting action) easily and quickly"

- __provisioner__: Each provisioner is an instance of the `Cloud Provisioning` module, and implements steps to perform the provisioning process by calling the respective API of that cloud. For Grid5000, we use `execo-g5k` library while we utilize `libcloud` to interact with various public cloud systems. By leveraging _libcloud_, we do not have to work with each separated SDK cloud system and also provide the extensibility to other cloud providers.
- __configurator__: this module contains many ready-to-use configurators that we already implemented to set up the environment for a specific application (e.g, Docker, Kubernetes, QEMU-KVM, etc.) on the provisioned nodes.
- __experimenter__: this module contains some ready-to-use experimenter that used to manage the experiments, meaning that creating and controlling the combinations queue and handling the results.

By using the 3 provided modules as lego blocks, users can assemble them to write a `Performing Actions` script to describe sequential steps to perform their specific experimental scenarios. And they are free to choose which actions they want to incorporate in their script (i.e. users may just want to provision hosts for manually testing, or perform experiments automatically which require the whole workflow).

# Installation
This repo uses Python 2.7+ due to `execo`.

The following are steps to install cloudal. If you want to test it without affecting your system, you may want to run it in a virtual environment. If you're unfamiliar with Python virtual environments, check out the [user guide](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/).

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

Execo reads `~/.execo.conf.py` file to set up the connection. If this file is not exist, execo uses the default values that you can find more detail [here](http://execo.gforge.inria.fr/doc/latest-stable/execo.html#configuration)

To working on specific cloudal systems, you need more installation. Please find the detail instruction in the following links:
- [Working on Grid5000 (G5K)](https://github.com/ntlinh16/cloudal/blob/master/docs/g5k_tutorial.md)
- [Working with Kubernetes on Grid5000](https://github.com/ntlinh16/cloudal/blob/master/docs/g5k_k8s_tutorial.md)
- [Working on Google Cloud Platform (GCP)](https://github.com/ntlinh16/cloudal/blob/master/docs/gcp_tutorial.md)
- [Working with Google Kubernetes Engine (GKE)](https://github.com/ntlinh16/cloudal/blob/master/docs/gke_tutorial.md)

# Getting started

To write your custom _performing action_ script (a script to perform your experiment), you could use the provided template in `cloudal/template` directory. The detail explanation presents in [here](https://github.com/ntlinh16/cloudal/tree/master/templates)

# Tutorials
You can use _cloudal_ to perform a all cloudal experiment steps or only perform an simple action such as provisioning some resources on a specific cloud system or configuring some resources (i.e., provisioning some resources and then deploy services on them).
We provide here some quick tutorials on how to perform some actions with _cloudal_.

### Provisioning
- [Provisioning on G5K: reserving some hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-1-provisioning-some-hosts-on-g5k)
- [Provisioning on G5K: creating a Kubernetes cluster](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-2-creating-a-kubernetes-cluster-on-g5k)
- [Provisioning on GCP: reserving some hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-3-provisioning-some-hosts-on-gcp)
- [Provisioning on GKE: reserving Kubernetes clusters](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-4-provisioning-kubernetes-clusters-on-gke)

### Configuring
- [Configuring Docker on all reserved hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/configuration#example-1-configuring-docker-on-running-hosts-on-g5k)
- [Configuring AntidoteDB on all reserved hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/configuration#example-3-configuring-antidotedb-on-running-hosts-on-g5k)
- [Deploying an AntidoteDB cluster using Kubernetes](https://github.com/ntlinh16/cloudal/tree/master/examples/configuration#example-5-deploying-an-antidotedb-cluster-using-kubernetes-on-g5k)

### Experimenting
- [Running FMKe benchmark on AntidoteDB cluster using Kubernetes on G5K](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/antidotedb)
- [Running elmerfs with an AntidoteDB backend on G5K](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs)