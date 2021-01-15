In this example, we perform a simple experiment which follows a full experiment workflow on a cloud infrastructure (as illustrated in [An experiment workflow with cloudal](https://github.com/ntlinh16/cloudal/blob/master/docs/technical_detail.md#an-experiment-workflow-with-cloudal)).

This experiment is performed on Grid5000. First, we set up an experiment environment by provisioning and configuring steps: we provision 3 nodes on cluster `econome`, 1 node on cluster `paravance` in 2 hours, all nodes are install with _debian 10_; after all nodes are up, we install and deploy on all hosts the following software and services: sysstat, htop, Docker container, and download _cloudal_ from the github repository. Then, we perform a simple experiment workflow: write a message into a file on each nodes and then download that file to local result directory.

# Prepare the system config file
You can describe all your requirements for an experiment in the `exp_setting_template_g5k.yaml` file. This system config file provides the following information:

* _Infrastructures_: includes the number of clusters, name and the number of nodes for each cluster you want to provision on Grid5k system; which OS you want to deploy on these reserved nodes; when and how long you want to provision nodes; etc.

* _Experiment Parameters_: is a list of experiment parameters that represent different aspects of the system that you want to examine. Each parameter contains a list of possible values of that aspect.

* _Experiment Environment Settings_: the settings related to this experiment, like the path to experiment result files; etc.

# Script your experiment

## The bare bones 
Let say we want to write a script to perform an experiment on Grid5000 with _cloudal_, we should begin as follow:

```python
import traceback

from execo_g5k.oar import oardel

from cloudal.action import performing_actions_g5k
from cloudal.utils import ExecuteCommandException, get_logger

logger = get_logger()


class performing_action_template(performing_actions_g5k):
    
    def __init__(self, **kwargs):
        super(performing_action_template, self).__init__()

    def run(self):
        # contains the real experiment workflow
        pass 


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = performing_action_template()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
        traceback.print_exc()
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')
```

The `performing_action_template` class is the subclass of the execo Engine that has supports for initializing and preparing an experiment, including: automatic experiment directory creation, support for continuing a previously stopped experiment, and other facilities (read [here](http://execo.gforge.inria.fr/doc/latest-stable/execo_engine.html#execo_engine.engine.Engine) for more detail). When running the engine by calling `engine.start()`, the engine parses all command line arguments, perform some initializations, calls all `init()` of all subclasses, and then performs the experiment workflow in the `run()` function.

## Implement of the experiment workflow in detail

Following the [experiment workflow with cloudal](https://github.com/ntlinh16/cloudal/blob/master/docs/technical_detail.md#an-experiment-workflow-with-cloudal), we implement those steps in the `run()` function of the experiment engine class.

```python
    def run(self):
        logger.debug('Parse and convert configs for G5K provisioner')
        self.configs = parse_config_file(self.args.config_file_path)

        logger.debug('Creating the combination list')
        sweeper = create_combs_queue(result_dir=self.configs['exp_env']['results_dir'],
                                     parameters=self.configs['parameters'])

        oar_job_ids = None
        logger.info('Running the experiment workflow')
        while len(sweeper.get_remaining()) > 0:
            if oar_job_ids is None:
                logger.info('Setting the experiment environment')
                oar_job_ids = self.setup_env()

            comb = sweeper.get_next()
            sweeper = self.run_workflow(comb=comb, sweeper=sweeper)

            if not is_job_alive(oar_job_ids):
                oardel(oar_job_ids)
                oar_job_ids = None

        logger.info('Finish the experiment!!!')
```

We begin by parsing the user requirements (described [above](#Prepare-the-system-config-file)) and creating the combination queue. We have a `sweeper` instance of the [ParamSweeper](http://execo.gforge.inria.fr/doc/latest-stable/execo_engine.html#paramsweeper) class which is an iterable container that iterate over all possible combinations of experiment parameters.

Afterwards, we iterate with this `sweeper` until there is no combination left (by using `sweeper.get_remaining()` and `sweeper.get_next()`). With each combination `comb`, we perform an actual experiment run with [`run_workflow(comb)` function](#Perform-an-experiment-run). Each time we check for the readiness of the experiment environment and setup the environment `setup_env()` for the experiment if needed.

## Perform an experiment run

```python
    def run_workflow(self, comb, sweeper):
        comb_ok = False
        try:
            logger.info('Performing combination: ' + slugify(comb))
            message = """
                parameter_1: %s,
                parameter_2: %s,
                parameter_3: %s,
                parameter_4: %s,
                parameter_5: %s""" % (
                comb['parameter_1'],
                comb['parameter_2'],
                comb['parameter_3'],
                comb['parameter_4'],
                comb['parameter_5'])
            cmd = "echo %s > /tmp/result_$(hostname).txt" % message
            execute_cmd(cmd, self.hosts)

            get_results(comb=comb,
                        hosts=self.hosts,
                        remote_result_files=['/tmp/result_*.txt'],
                        local_result_dir=self.configs['exp_env']['results_dir'])
            comb_ok = True

        except ExecuteCommandException as e:
            comb_ok = False
        finally:
            if comb_ok:
                sweeper.done(comb)
                logger.info('Finish combination: %s' % slugify(comb))
            else:
                sweeper.cancel(comb)
                logger.warning(slugify(comb) + ' is canceled')
            logger.info('%s combinations remaining\n' % len(sweeper.get_remaining()))
        return sweeper
```

A `comb` instance contains one combination of parameters and we can retrieve each parameter to be used in this experiment scenario. We can save result of each run into files on the remote host and we can download the result to our local directory with `get_results()`. If this combination runs successfully, we mark it with `sweeper.done(comb)`, otherwise, we mark it as `sweeper.cancel(comb)` so that it can be sent back to the queue and rerun in the future. 

# Run the experiment

We assume that you already followed the setting steps in [Installation](https://github.com/ntlinh16/cloudal#installation) to set up all necessary for running _cloudal_.

You only need to run the command:

```
python performing_exp_template_g5k.py --system_config_file exp_setting_template_g5k.yaml -k
```

