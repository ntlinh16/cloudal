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

The main goal of `cloudal` is to perform large-scale reproducible experiments and collecting results automatically on different cloud systems. `cloudal` is composed of: 
- a performing actions script that conducts user defined experiment workflow
- a cloud provisioning module that reserves nodes from cloud systems

In order to setup a cloud system for running rigorous experiments, we usually follow a typical experiment workflow which is (1) provisioning machines; (2) configuring the enviroment; (3) writing the experiment workflow scripts. 
`cloudal` implements this workflow and provide templates so that users can customize to their needs. 

Users modify the `Performing Actions` script to perform one or multiple actions. Users are free to choose which actions they want to incorporate in their script (i.e. users may just want to provision hosts, or perform experiments which require all the actions). There are three main components:

- __provisioner__: Each provisioner is an instance of `Cloud Provisioning`, implements steps to perform the reservation and OS installation (if needed) phase by calling the respective API of that cloud. For Grid5000, we use `execo-g5k` library while we utilizes `libcloud` to interact with various public cloud systems. By leveraging libcloud, we do not have to work with each separated SDK cloud system and also provide the extensibility to other cloud providers.
- __configurator__: this module contains some ready-to-use configurators that help setting up the environment for a specific application (e.g, Docker, Kubernetes, QEMU-KVM, etc.) on the provisioned machines.
- __experimenter__: is a workflow for user's specific experimental scenario. 


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



# Tutorials

We provide some quick tutorials to get you started with `cloudal`:
- [Working with Grid5000](https://github.com/ntlinh16/cloudal/blob/master/docs/grid5000.md)
- [Working with Google Cloud Platform](https://github.com/ntlinh16/cloudal/blob/master/docs/googlecloud.md)


# Options
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