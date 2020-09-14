from execo_engine import Engine
from cloudal.utils import get_remote_executor


class performing_actions(Engine):
    """This is a base class of cloudal engine, that is built from execo_engine
    and can be used to deploy servers a different cloud system."""

    def __init__(self):
        """Add options for the number of measures, number of nodes
        walltime, env_file or env_name and clusters and initialize the engine
        """

        # Using super() function to access the parrent class
        # so that we do not care about the changing of parent class

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
