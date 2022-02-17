import os
import re

from cloudal.utils import get_logger, getput_file

from execo_engine import utils, sweep, ParamSweeper

logger = get_logger()


def define_parameters(parameters):
    """Normalize a parameters dictionary from the user input

    Parameters
    ----------
    parameters: dict
        a dictionary contains the parameters space defined by user which is parsed from the config file
        key: str, the name of the experiment parameter
        value: list, str, int

    Returns
    -------
    dictionary
        a normalized dictionary contains the parameters space
        key: str, the name of the experiment parameter
        value: list, a list of possible values for a parameter of the experiment
    """
    if not isinstance(parameters, dict):
        raise TypeError('Parameters has to be a dictionary.')

    normalized_parameters = dict()
    pattern = re.compile(r"^\d+\.\.+\d+$")
    for param, values in parameters.items():
        if (values != 0.0 and not values) or isinstance(values, dict):
            continue
        elif not isinstance(values, list):
            normalized_parameters[param] = [values]
        elif len(values) > 1:
            normalized_parameters[param] = values
        elif isinstance(values[0], str) and len(pattern.findall(values[0])) > 0:
            start = int(values[0].split('.')[0])
            end = int(values[0].split('.')[-1])
            normalized_parameters[param] = range(start, end + 1)
        else:
            normalized_parameters[param] = values

    logger.info('Parameters:\n%s' % normalized_parameters)
    return normalized_parameters


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
    sweeper = ParamSweeper(os.path.join(result_dir, "sweeps"), sweeps)
    logger.info('-----> TOTAL COMBINATIONS: %s', len(sweeps))
    if len(sweeper.get_remaining()) < len(sweeps):
        logger.info('%s combinations remaining\n' % len(sweeper.get_remaining()))
    return sweeper


def create_combs_queue(result_dir, parameters):
    """Generate a combination queue that holds all the experimental combinations

    Parameters
    ----------
    result_dir: str
        the path to the directory to store the results on the local node

    parameters: dict
        a normalized dictionary contains the parameters space
        key: str, the name of the experiment parameter
        value: list, a list of possible values for a parameter of the experiment

    Returns
    -------
    ParamSweeper
        an instance of the `ParamSweeper` object.

    """
    if not os.path.exists(result_dir):
        os.mkdir(result_dir)
    normalized_parameters = define_parameters(parameters)
    sweeper = create_paramsweeper(normalized_parameters, result_dir)
    return sweeper


def create_combination_dir(comb, result_dir):
    """Create the directory to save result for a specific combination

    Parameters
    ----------
    comb: dict
        a dictionary that contains the set of parameters for a specific run
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
        logger.warning('%s already exists, removed existing files' % comb_dir)
        for f in os.listdir(comb_dir):
            try:
                os.remove(os.path.join(comb_dir, f))
            except Exception as e:
                logger.error(e, exc_info=True)
                continue
    return comb_dir


def get_results(comb, hosts, remote_result_files, local_result_dir):
    """Get all the results files from remote hosts to a local result directory

    Parameters
    ----------
    comb: dict
        a dictionary that contains the set of parameters for a specific run
        key: str, the name of the experiment parameter
        value: object, the value of the experiment parameter in this combination

    hosts: list
        a list of hosts to get the results from

    remote_result_files: list
        a list of results files on the remote nodes

    local_result_dir: str
        the path to the directory to store the results on the local node

    """
    logger.info('Create combination dir locally')
    comb_dir = create_combination_dir(comb, local_result_dir)
    logger.info('Download the result')
    getput_file(hosts=hosts,
                file_paths=remote_result_files,
                dest_location=comb_dir,
                action='get')
    return comb_dir