from execo_engine import Engine
from cloudal.utils import get_remote_executor


class performing_actions(Engine):
    """This is a base class of cloudal engine, that is built from execo_engine
    and can be used to deploy servers a different cloud system."""

    def __init__(self):
        super(performing_actions, self).__init__()

        # initialize the remote_executor to execute a command on hosts
        self.remote_executor = get_remote_executor()

        self.args_parser.add_argument("--system_config_file",
                                      dest="config_file_path",
                                      help="the path to the provisioning configuration file.",
                                      type=str)
        self.args_parser.add_argument("--exp_setting_file",
                                      dest="exp_setting_file_path",
                                      help="the path to the experiment setting file.",
                                      type=str)

    def _provisioning(self):
        pass

    def _config_host(self):
        pass

    def _perform_experiments(self):
        pass


class performing_actions_g5k(performing_actions):
    def __init__(self):
        """ Add options and initialize the engine
        """
        super(performing_actions_g5k, self).__init__()

        self.args_parser.add_argument("-k", dest="keep_alive",
                                      help="keep the reservation alive after deploying.",
                                      action="store_true")

        self.args_parser.add_argument("-o", dest="out_of_chart",
                                      help="run the engine outside of grid5k charter",
                                      action="store_true")

        self.args_parser.add_argument("-j", dest="oar_job_ids",
                                      help="the reserved oar_job_ids on grid5k. The format is site1:oar_job_id1,site2:oar_job_id2,...",
                                      type=str)

        self.args_parser.add_argument("--no-deploy-os", dest="no_deploy_os",
                                      help="specify not to deploy OS on reserved nodes",
                                      action="store_true")
