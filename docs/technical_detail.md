# A cloud experiment workflow

To set up a cloud environment for running rigorous experiments, we usually follow a typical workflow that consists of three steps: (1) provisioning some nodes (physical machines or virtual machines); (2) configuring the environment (i.e., installing/deploying services or applications on provisioned nodes); (3) performing an user-defined experiment scenario. To achieve a complete configured environment, we have to overcome a massive amount of challenges and obstacles of low-level technical details such as system deployment, failures management on one specific cloud system. Additionally, we have to ensure the reproducibility of the experiments and the control of the parameter space. `cloudal` helps us with these boring setting steps as well as manage the experimenter productively, therefore, we only need to focus on the interesting experiments and find out more insights.

To address all the challenges when performing a cloud experiment, I design a general workflow of a cloud experiment. The following flowchart presents three main functions of the workflow: create a combination queue, setup the environment, and run a user-defined experiment scenario.


<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/experiment_flowchart.png" width="650"/>
    <br>
<p>

First of all, the `create_combinations_queue()` function is performed to create a list of combinations. So what is a combinations list and why we need this list? When you perform a cloud experiment, you want to examine various aspects of the system, so that you have to run the same experiment scenarios repeatedly with different setting of parameters. Each parameter set contains a list of possible values of an aspect. All the given parameters are combined to create a list of combinations. For example, with two parameters: storage types (SSD, HDD, remote storage) and workloads (read, write, mixed), we can produce a list of 9 combinations. You just need to define all the parameters that you want to test for your experiment, then _cloudal_ will manage and ensure the run of all combinations automatically.

Next, the `setup_env()` function prepares the environment on nodes with the clients' requirements. The `setup_env()` function (1) provisions the required infrastructure; and (2) installs and deploys all the necessary packages/services.

The `run_exp_workflow()` function consists of user-defined steps to perform an experiment scenario. This function gets one combination from the queue as the input, and then run the user-defined steps with that combination information. This process repeats until there is no combination left. If a run of a combination fails, this combination is put back to the queue to be run later. The progress of running one combination is check-pointed on the disk so that if a run is interrupted, the experiment can continue when you re-run it. When all combinations are performed, the whole experiment completes. While we are performing experiments, if the provisioned nodes are dead (due to end of reservation time or unexpected problems), `setup_env()` is executed to prepare the environment again.

# _cloudal_ implementation

_cloudal_ is designed to perform a [full factorial experiment](https://en.wikipedia.org/wiki/Factorial_experiment) workflow and collect the results automatically on different cloud systems in a large-scale and reproducible manner. I choose a pluggable design to develop _cloudal_ so that users can use and extend _cloudal_ to perform all cloud experiment steps or only perform a single step. Users can use cloudal to perform all cloudal experiment steps or only perform a simple action such as provisioning some resources on a specific cloud system or configuring some resources (i.e., provisioning some resources and then deploy applications/services on them).



As shown in the following Figure, _cloudal_ provides 3 main modules to help users perform their actions (i.e., provisioning, configuring or performing a whole experiments) easily and quickly.

These components of _cloudal_ are revolving around an `Experiment script`. The script contains a main experiment engine class that inherits the `execo_engine`. `execo_engine` defines an argument parser for the CLI of the script, as well as sets up necessary directories to persist the current working states of an experiment. This engine class uses appropriated modules provided by _cloudal_ for each specific experiment. 

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/architecture.png" width="800"/>
    <br>
<p>

- __provisioner__: each provisioner is an instance of the `Cloud Provisioning` module, and implements steps to perform the provisioning process by calling the respective API of that cloud. I utilize [Apache Libcloud](https://libcloud.apache.org/) to interact with various public cloud systems. `libcloud` is a Python library which provides a unified API for interacting with many of the popular cloud service providers. By leveraging `libcloud`, I do not have to work with each separated SDK of each cloud system and also provide the extensibility to other cloud providers effectively. For cloud systems that are not supported by _libcloud_ such as Grid'5000 and Google Kubernetes Engine (GKE), I work directly with their SDK. A provisioner takes a list of users' infrastructure requirements as input and returns a list of provisioned nodes information, particularly, their IPs.

- __configurator__: this module contains many ready-to-use configurators that are useful to get the machines configured. A configurator can be used independently of the nodes' OSes. Users can choose their applications to configure from the supported list of configurators or they can extend it by writing their custom configurators to be used in their projects. Currently supported configurators are: one basic configurator to install packages on different OSes (by using the right package management tool of the respective OS of a node); and various configurators for deploying services such as Docker, Docker Swarm, or Kubernetes on the provisioned nodes. A configurator takes a list of nodes as input and then installs and configures the required applications on those nodes.

- __experimenter__: this module contains some ready-to-use experimenters to manage the experiments, meaning that creating and controlling the combinations queue and handling the results.

By using the 3 provided modules as Lego blocks, users can assemble them to write an `Experiment script` which describes steps to perform their specific experimental scenarios. And they are free to choose which actions they want to incorporate in their script (i.e. users may just want to provision nodes for manually testing, or perform an experiment automatically which requires the whole workflow).

We do not leverage any popular infrastructure-as-code (IaC) tools such as [Terraform](https://www.terraform.io/), [Ansible](https://www.ansible.com/), [Pulumi](https://www.pulumi.com/), or [SaltStack](https://saltproject.io/) for the `provisioner` or `configurator` module. Even though they can deal with the provisioning and configuring stages, they are not designed to perform and manage a whole experiments workflow. Plus, users also have to learn how to use additional IaC tools beside `cloudal`.

More information can be found in the [cloudal report](https://drive.google.com/file/d/1rCVob6QfjCi5fVHNxE0g7yQxoR2jJhhK/view?usp=sharing).