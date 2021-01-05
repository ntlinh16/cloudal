<p align="center">
    <a href="https://github.com/ntlinh16/cloudal">
        <img src="https://raw.githubusercontent.com/ntlinh16/cloudal/master/images/cloudal_logo.png" width="300"/>
    </a>
    <br>
<p>

<h4 align="center"> Design and perform experiments on different cloud systems 🤗
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

`cloudal` is one of the contributions of the [RainbowFS](https://rainbowfs.lip6.fr/) project. 

It is a module that helps to design and perform experiments on different cloud systems. 

You can use `cloudal` to provision your infrastructure on a specific cloud system by simply describing your requirements in a yaml file. Other than that, by calling our ready-to-use modules you can easily install and configure some software or services on all hosts.

Read the [doc](https://github.com/ntlinh16/cloudal/blob/master/docs/technical_detail.md) for more technical detail.

--------------------------------------------------------------------------------

- [Getting Started](#getting-started)
- [Installation](#installation)
- [Tutorials](#tutorials)
  - [Provisioning](#provisioning)
  - [Configuring](#configuring)
  - [Experimenting](#experimenting)

# Getting started

`cloudal` should be painless to work with. Just pick the appropriate module with the right arguments and move along 😉

```python
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import docker_configurator, packages_configurator


provisioner = g5k_provisioner(config_file_path="/path/to/configuring/file.yaml")
provisioner.provisioning() # provisioning hosts on Grid5000 base on requirement in a configuring file.
hosts = provisioner.hosts

configurator = packages_configurator()
configurator.install_packages(['sysstat', 'htop'], hosts) # install sysstat and htop on all hosts

configurator = docker_configurator(hosts)
configurator.config_docker() # install and start Docker engine on all hosts
```

To write your own script to perform your custom actions such as provisioning, configuring or experimenting, you could use the provided templates and follow the detail explanation in [templates](https://github.com/ntlinh16/cloudal/tree/master/templates).

You can also try some examples in the [tutorials](#tutorials) section.

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

5. Set up the SSH configuration for `execo`:

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

# Tutorials

I provide here some quick tutorials on how to perform an action with _cloudal_.
### Provisioning
- [Provisioning on G5K: reserving some hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-1-provisioning-some-hosts-on-grid5000-g5k)
- [Provisioning on G5K: creating a Kubernetes cluster](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-2-provisioning-a-kubernetes-cluster-on-grid5000-g5k)
- [Provisioning on G5K: creating a Docker Swarm cluster](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-3-provisioning-docker-swarm-cluster-on-grid5000-g5k)
- [Provisioning on GCP: reserving some hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-4-provisioning-some-hosts-on-google-cloud-platform-gcp)
- [Provisioning on GCP: creating a Docker Swarm cluster](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-5-provisioning-docker-swarm-cluster-on-google-cloud-platform-gcp)
- [Provisioning on GKE: reserving Kubernetes clusters](https://github.com/ntlinh16/cloudal/tree/master/examples/provision#example-6-provisioning-kubernetes-clusters-on-google-cloud-engine-gke)

### Configuring
- [Configuring Docker on all reserved hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/configuration#example-1-configuring-docker-on-running-hosts-on-grid5000-g5k)
- [Configuring AntidoteDB on all reserved hosts](https://github.com/ntlinh16/cloudal/tree/master/examples/configuration#example-3-configuring-antidotedb-on-running-hosts-on-g5k)
- [Deploying an AntidoteDB cluster using Kubernetes](https://github.com/ntlinh16/cloudal/tree/master/examples/configuration#example-5-deploying-an-antidotedb-cluster-using-kubernetes-on-g5k)

### Experimenting
- [Running FMKe benchmark on AntidoteDB cluster using Kubernetes on G5K](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/antidotedb_g5k)
- [Running elmerfs with an AntidoteDB backend on G5K](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs_g5k)
- [Running elmerfs with an AntidoteDB backend on Google Cloud (using both GCP and GKE)](https://github.com/ntlinh16/cloudal/tree/master/examples/experiment/elmerfs_gke)