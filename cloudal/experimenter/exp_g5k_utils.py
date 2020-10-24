import os

from cloudal.utils import get_logger, getput_file

from execo_engine import utils, sweep, ParamSweeper
from execo_g5k import get_host_attributes


logger = get_logger()


# TODO: retry
def get_cores_hosts(hosts):
    """Get the number of cores of a list of given hosts

    Parameters
    ----------
    hosts: list
        a list of hosts

    Returns
    -------
    dict
        key: str, name of host (e.g. econome-8.nantes.grid5000.fr)
        value: int, the number of cores

    """

    n_cores_hosts = dict()
    for host in hosts:
        host_name = host.split('.')[0]
        try:
            n_cores_hosts[host] = get_host_attributes(host_name)['architecture']['nb_cores']
            logger.info('Number of cores of [%s] = %s' % (host_name, n_cores_hosts[host]))
        except Exception as e:
            logger.error('Cannot get number of cores from host [%s]' % host_name)
            logger.error('Exception: %s' % e, exc_info=True)
    return n_cores_hosts


def create_paramsweeper(parameters, result_dir):
    """Generate an iterator over combination parameters

    This function initializes a `ParamSweeper` as an iterator over the possible
    parameters space (The dictionary of parameters space is created from the
    `define_parameters` function.). The detail information about the `ParamSweeper`
    can be found here: http://execo.gforge.inria.fr/doc/latest-stable/execo_engine.html#paramsweeper

    Parameters
    ----------
    parameters: dict
        a dictionary contains the parameters space
        key: str, the name of the experiment parameter
        value: list, a list of possible values for a parameter of the experiment

    result_dir: str
        the path to the result directory on the disk for `ParamSweeper` to persist
        the state of combinations

    Returns
    -------
    ParamSweeper
        an instance of the `ParamSweeper` object.
    """

    logger.debug('Parameters:\n%s' % parameters)
    sweeps = sweep(parameters)
    logger.info('-----> TOTAL COMBINATIONS: %s', len(sweeps))
    return ParamSweeper(os.path.join(result_dir, "sweeps"), sweeps)


def create_combination_dir(comb, result_dir):
    """Create the directory to save result for a combination

    Parameters
    ----------
    comb: dict
        a dictionay that contains the set of parameters for a specific run
        key: str, the name of the experiment parameter
        value: object, the value of the experiment parameter in this combination

    result_dir: str
        the path to the directory to store the result on the local node

    Returns
    -------
    str
        the directory path to store the result of this combination
    """

    # Create a folder (with the folder name is the combination) to save the result
    comb_dir = os.path.join(result_dir, utils.slugify(comb))
    if not os.path.exists(comb_dir):
        os.mkdir(comb_dir)
    else:
        logger.warning('%s already exists, removing existing files' % comb_dir)
        for f in os.listdir(comb_dir):
            try:
                os.remove(os.path.join(comb_dir, f))
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
    return comb_dir


def get_results(self, comb, hosts, remote_result_files, local_result_dir):
    """Get all the results files from remote hosts to a local result directory

    Parameters
    ----------
    comb: dict
        a dictionay that contains the set of parameters for a specific run
        key: str, the name of the experiment parameter
        value: object, the value of the experiment parameter in this combination

    hosts: list
        a list of hosts to get the results from

    remote_result_files: list
        a list of results files on the remote nodes

    local_result_dir: str
        the path to the directory to store the results on the local node

    """
    comb_dir = create_combination_dir(comb, local_result_dir)
    getput_file(hosts=hosts,
                file_paths=remote_result_files,
                dest_location=comb_dir,
                action='get')
