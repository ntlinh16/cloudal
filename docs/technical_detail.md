# An experiment workflow with cloudal

To set up a cloud system for running rigorous experiments, we usually follow a typical workflow that consists of three steps: (1) provisioning some hosts (physical machines or virtual machines); (2) configuring the environment (i.e., installing/deploying services or applications on hosts); (3) performing an experiment workflow. To achieve a complete configured environment, we have to overcome a massive amount of challenges and obstacles to deploy and manage hosts as well as build and install applications/services on one specific cloud system. Additionally, we have to ensure the reproducibility of the experiments and the control of the parameter space. `cloudal` helps us with these boring setting steps as well as manage the experimenter more productively, therefore, we only need to focus on the experiments we are interested in and find out more insights.

To address all the challenges when performing cloud experiments, I design a flowchart of a general cloud experiment on a specific cloud system. The following figure presents a general experiment flowchart on a specific cloud system when using _cloudal_.


<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/experiment_flowchart.png" width="650"/>
    <br>
<p>

First of all, the `create_combinations_queue()` function is performed to create a list of combinations. So what is a combinations list and why we need this list? When you perform an cloud experiment, you want to examine various aspects of the system, so that you have to run the same experiment scenarios repeatedly with different setting of parameters. Each parameter contains a list of possible values of an aspect. All the given parameters are combined to create a list of combinations. For example, with two parameters: storage types (SSD, HDD, remote storage) and workloads (read, write, mixed), we have a list of 9 combinations. You just need to define all the parameters that you want to test for your experiment, then _cloudal_ will manage and ensure the run of all combinations automatically.

Next, the `setup_env()` function prepares the environment on reserved hosts with the clients' requirements. The `setup_env()` function (1) provisions the required infrastructure; and (2) installs and deploys all the necessary packages/services.

The `run_exp_workflow()` is an user-defined workflow to perform an experiment scenario. This function gets a combination from the queue as the input, and then run the user-defined workflow with that combination information. This process repeats until there is no combination left. If a run of a combination fails, this combination is put back to the queue to be run later. The progress of running one combination is check-pointed on the disk so that if a run is interrupted, the experiment can continue the current progress when you re-run it. If all combinations are performed, the experiment is done. While we are performing experiments, if the provisioned nodes are dead (due to end of provisioning time or unexpected problems), `setup_env()` is executed to prepare the environment again.

# cloudal architecture

_cloudal_ is designed to perform a [full factorial experiment](https://en.wikipedia.org/wiki/Factorial_experiment) workflow and collect the results automatically on different cloud systems in a large-scale and reproducible manner. I choose a pluggable design to develop _cloudal_ so that users can use and extend _cloudal_ to perform all cloud experiment steps or only perform a single step. Users can use cloudal to perform all cloudal experiment steps or only perform a simple action such as provisioning some resources on a specific cloud system or configuring some resources (i.e., provisioning some resources and then deploy applications/services on them).

The components of _cloudal_ are revolving around an experiment script. The script contains a main experiment engine class that inherits the `execo_engine`. `execo_engine` defines an argument parser for the CLI of the script, as well as sets up necessary directories to persist the current working states of an experiment. This engine class uses appropriated modules provided by _cloudal_ for each specific experiment. 

As shown in the following Figure _cloudal_ provides 3 main modules to helps users perform their actions (i.e., provisioning, configuring or performing experiments) "more easily and quickly"

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/architecture.png" width="800"/>
    <br>
<p>

- __provisioner__: each provisioner is an instance of the `Cloud Provisioning` module, and implements steps to perform the provisioning process by calling the respective API of that cloud. I utilize [Apache Libcloud](https://libcloud.apache.org/) to interact with various public cloud systems. `libcloud` is a Python library which provides a unified API for interacting with many of the popular cloud service providers. By leveraging `libcloud`, I do not have to work with each separated SDK of each cloud system and also provide the extensibility to other cloud providers effectively. For cloud systems that are not supported by _libcloud_ such as Grid'5000 and Google Kubernetes Engine (GKE), I work directly with their SDK. A provisioner takes a list of users' infrastructure requirements as input and returns a list of provisioned hosts information, particularly, their IPs.

- __configurator__: this module contains many ready-to-use configurators that are already implemented to set up the environment for a specific application (e.g, Docker, Docker Swarm, Kubernetes, QEMU-KVM, etc.) on the provisioned nodes. Users can choose their wanted required application from the list of configurators or they can extend it by writing their custom configurators to be used in their projects. A configurator takes a list of hosts as input and then installs and configures the applications on those hosts. A configurator can be used independently of the hosts' OSes.

- __experimenter__: this module contains some ready-to-use experimenters to manage the experiments, meaning that creating and controlling the combinations queue and handling the results.

By using the 3 provided modules as lego blocks, users can assemble them to write a `Experiment Actions` script which describes steps to perform their specific experimental scenarios. And they are free to choose which actions they want to incorporate in their script (i.e. users may just want to provision hosts for manually testing, or perform an experiment automatically which requires the whole workflow).