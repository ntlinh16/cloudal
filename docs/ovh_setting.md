# Working on OVH Cloud
This tutorial helps you to setup the authentication to connect to OVH cloud from your laptop so that you can use `cloudal` to provision machines and perform the experiments.

If you do not have an OVH account yet, you should create an OVH account.

# How to authenticate with OVH?
Visit https://api.ovh.com/createToken to create your credentials.
Depending on your script, you can add the rights (`GET`, `PUT`, `POST` or `DELETE`) and the path (e.g. `/me` or `/*` ...)


# Install the OVH python library

```
pip install ovh
```