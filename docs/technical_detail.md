# An experiment workflow with cloudal

To set up a cloud system for running rigorous experiments, we usually follow a typical workflow that consists of three steps: (1) provisioning some hosts (physical machines or virtual machines); (2) configuring the environment (i.e., installing/deploying services or applications on hosts); (3) performing an experiment workflow. To achieve a completed setting environment, we have to overcome a massive amount of challenges and obstacles to build, deploy, and manage hosts and applications on one specific cloud system. `cloudal` helps you with these boring setting steps, therefore, you only need to focus on the experiments you are interested in.

_cloudal_ is designed to perform a [full factorial experiment](https://en.wikipedia.org/wiki/Factorial_experiment) workflow and collect the results automatically on different cloud systems in a large-scale and reproducible manner. You can use _cloudal_ to perform all cloudal experiment steps or only perform a simple action such as provisioning some resources on a specific cloud system or configuring some resources (i.e., provisioning some resources and then deploy applications/services on them).

The following figure presents a general experiment flowchart on a specific cloud system when you use _cloudal_.

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/experiment_flowchart.png" width="650"/>
    <br>
<p>

First of all, the `create_combinations_queue()` function is performed to create a list of combinations. So what is a combinations list? Let say, when you perform an experiment, you want to examine various aspects of the system, so that you have to run the same experiment repeatedly with different setting of parameters. Each parameter contains a list of possible values of an aspect. For example, the disk type (SSD or HDD or remote storage) can be one of the parameters. _cloudal_ will combine all the given parameters to create a list of combinations. You just need to define all the parameters that you want to test for your experiment, then _cloudal_ will manage and ensure the run of all combinations automatically.

Next, the `setup_env()` function prepares the environment on reserved hosts with the clients' requirements. The `setup_env()` function (1) provisions the required infrastructure; and (2) installs and deploys all the necessary packages/services.

The `run_exp_workflow()` function takes a combination from the queue as the input, and then run an user-defined experiment workflow with that combination info. This process repeats until we have no combinations left. If a run of a combination fails, the combination is put back to the queue to be run later. The _run_exp_workflow_ function needs to be implemented for different experiments. The progress of running one combination is checkpointed on the disk so that if a run is interrupted, the experiment can continue the current progress when you re-run.

If all combinations are performed, the experiment is done. While we are performing experiments, if the reserved nodes are dead (due to end of reservation time or unexpected problems), _cloudal_ will execute `setup_env()` to prepare the infrastructure again.

# cloudal architecture

<p align="center">
    <br>
    <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/architecture.png" width="800"/>
    <br>
<p>

The design of _cloudal_ is a _Performing Actions_ class that inherits the `execo_engine`. 
I use `execo` as an experiment toolkit which offers a Python API for asynchronous control of local or remote, standalone or parallel, unix processes. It is especially well suited for quick and easy scripting workflows of parallel/distributed operations on local or remote hosts: automate a scientific workflow, conduct computer science experiments, perform automated tests, etc.

_cloudal_ provides 3 main modules to helps user perform their actions (i.e., provisioning, configuring or experimenting action) easily and quickly"

- __provisioner__: Each provisioner is an instance of the `Cloud Provisioning` module, and implements steps to perform the provisioning process by calling the respective API of that cloud. For Grid5000, I use `execo-g5k` library while we utilize `libcloud` to interact with various public cloud systems. By leveraging _libcloud_, we do not have to work with each separated SDK cloud system and also provide the extensibility to other cloud providers.
- __configurator__: this module contains many ready-to-use configurators that I already implemented to set up the environment for a specific application (e.g, Docker, Docker Swarm, Kubernetes, QEMU-KVM, etc.) on the provisioned nodes.
- __experimenter__: this module contains some ready-to-use experimenter that used to manage the experiments, meaning that creating and controlling the combinations queue and handling the results.

By using the 3 provided modules as lego blocks, users can assemble them to write a `Performing Actions` script which describes steps to perform their specific experimental scenarios. And they are free to choose which actions they want to incorporate in their script (i.e. users may just want to provision hosts for manually testing, or perform an experiment automatically which requires the whole workflow).
