from cloudal.utils import parse_config_file


class cloud_provisioning(object):
    """This is a base class of cloudal engine,
        and it can be used to deploy servers on different cloud systems."""

    def __init__(self, config_file_path):
        self.configs = parse_config_file(config_file_path)

    def make_reservation(self):
        """Performing a reservation of the required infrastructure.
        """
        pass

    def get_resources(self):
        """Retriving the needed information of the list of provisioned resources
        """
        pass

    def provisioning(self):
        """Performing reservation and retrieving the provisioned resources
        """
        pass
