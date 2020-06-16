from cloudal.utils import parse_config_file


class cloud_provisioning(object):
    """This is a base class of cloudal engine,
        and it can be used to deploy servers on different cloud systems."""

    def __init__(self, config_file_path):
        """Add options for the number of measures, number of nodes
        walltime, env_file or env_name and clusters and initialize the engine
        """
        self.configs = parse_config_file(config_file_path)

    def _get_nodes(self, starttime, endtime):
        """return the nearest slot (startdate) that has enough available nodes
        to perform the client's actions"""
        pass

    def make_reservation(self):
        """Performing a reservation of the required number of nodes.
        """
        pass

    def get_resources(self):
        """Retriving the needed information of  the list of reserved hosts
        """
        pass

    def setup_hosts(self):
        """Installing OS and performing initial configuration on the host
        """
        pass
