# Working on Grid5000 

This tutorial shows you how to set up the connection to [Grid5000](https://www.grid5000.fr/w/Grid5000:Home) system from your laptop, then provision machines, install applications and conduct experiments on the reserved machines.

If you do not have a Grid5000 account, check out the [Grid5000:Get an account](https://www.grid5000.fr/w/Grid5000:Get_an_account)

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
    'user': '<username_to_connect_to_node_inside_g5k>', # usually `root`
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


##### 3. Set up Grid5000 API authentication 

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
