import os
import traceback

from execo_g5k.oar import oardel
from execo_engine import slugify

from cloudal.utils import (ExecuteCommandException,
                           get_logger,
                           install_packages_on_debian,
                           execute_cmd,
                           parse_config_file)
from cloudal.action import performing_actions_g5k
from cloudal.provisioner import g5k_provisioner
from cloudal.configurator import docker_configurator
from cloudal.experimenter import create_combs_queue, is_job_alive, get_results


logger = get_logger()


class performing_action_template(performing_actions_g5k):
    def __init__(self, **kwargs):
        super(performing_action_template, self).__init__()

    def run_workflow(self, comb, sweeper):
        """Run user-defined steps of an experiment scenario and save the result.
        The input of this run is one combination of parameters from the combination queue.
        """

        comb_ok = False
        try:
            logger.info('Performing combination: ' + slugify(comb))
            # write your code here to perform a run of your experiment
            # you can get the current combination of parameters
            # (specified in the config file exp_setting.yaml)
            # and use them in this run of your experiment
            # For example, you can get the parameters out of the combination
            # and then use them.
            message = "parameter_1: %s, parameter_2: %s, parameter_3: %s, parameter_4: %s, parameter_5: %s" % (
                comb['parameter_1'], comb['parameter_2'], comb['parameter_3'], comb['parameter_4'], comb['parameter_5'])
            cmd = "echo %s > /tmp/result_$(hostname).txt" % message
            execute_cmd(cmd, self.hosts)

            # then download the remote_result_files on the remote hosts and save it to local_result_dir
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

    def setup_env(self):
        """Setting the experiment environment base on the user's requirements

        This funtion normally contains two steps:
            1. Provisioning hosts on G5k if needed
               (if you provided the OAR_JOB_ID of the already reserved hosts,
               the provisioner will not make a reservation again)
            2. Configuring all your necessary pakages/services on those hosts.
        """
        provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                      keep_alive=self.args.keep_alive,
                                      out_of_chart=self.args.out_of_chart,
                                      oar_job_ids=self.args.oar_job_ids,
                                      no_deploy_os=self.args.no_deploy_os,
                                      is_reservation=self.args.is_reservation,
                                      job_name="cloudal")
        provisioner.provisioning()
        self.hosts = provisioner.hosts
        oar_job_ids = provisioner.oar_result

        ##################################################
        #  Configuring hosts with your applications here #
        ##################################################

        # For example: install some dependencies
        install_packages_on_debian(['sysstat', 'htop'], self.hosts)

        # or perform some commands on all of hosts
        logger.info("Downloading cloudal")
        cmd = "cd /tmp/ && git clone https://github.com/ntlinh16/cloudal.git"
        execute_cmd(cmd, self.hosts)

        # or call the provided configurator (by cloudal) to deploy some well-known services
        configurator = docker_configurator(self.hosts)
        configurator.config_docker()

        return oar_job_ids

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
                logger.info('Setting the experiment enviroment')
                oar_job_ids = self.setup_env()

            comb = sweeper.get_next()
            sweeper = self.run_workflow(comb=comb, sweeper=sweeper)

            if not is_job_alive(oar_job_ids):
                oardel(oar_job_ids)
                oar_job_ids = None

        logger.info('Finish the experiment!!!')


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

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
