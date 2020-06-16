import os
import yaml
import logging

from execo.action import ActionFactory
from execo.config import TAKTUK, default_connection_params


default_connection_params['taktuk_connector_options'] = ('-o', 'BatchMode=yes',
                                                         '-o', 'PasswordAuthentication=no',
                                                         '-o', 'StrictHostKeyChecking=no',
                                                         '-o', 'UserKnownHostsFile=~/.ssh/known_hosts',
                                                         '-o', 'ConnectTimeout=20')


def parse_config_file(config_file_path):
    if config_file_path is None or config_file_path == "":
        raise IOError("Please enter the configuration file path.")
    elif not os.path.exists(config_file_path):
        raise IOError("Please enter an existing configuration file path.")
    else:
        with open(config_file_path, 'r') as f:
            content = yaml.full_load(f)
            try:
                return {key: str(value) if isinstance(value, basestring) else value for key, value in content.items()}
            except NameError:
                return content


logger_singleton = list()


def get_logger(log_level=logging.INFO):
    '''Create a custom logger

    Parameters
    ----------
    log_level: int
        the level of log from `logging` module

    Returns
    -------
    Logger
        a custom Logger object with custom format and logging level
    '''
    global logger_singleton
    if len(logger_singleton) > 0:
        logger = logger_singleton[0]
    else:
        logger = logging.getLogger(__name__)
        log_format = "%(asctime)s [%(threadName)s] %(levelname)s: %(message)s"
        handler = logging.StreamHandler()
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)
        logger_singleton.append(logger)

        try:
            import coloredlogs
            coloredlogs.install(logger=logger, fmt=log_format)
        except Exception as e:
            logger.error('Exception: %s' % e, exc_info=True)
    return logger


executor_singleton = list()


def get_remote_executor(remote_tool=TAKTUK, fileput_tool=TAKTUK, fileget_tool=TAKTUK):
    '''Instanciate remote process execution and file copies tool

    Parameters
    ----------
    remote_tool: str
        can be `execo.config.SSH` or `execo.config.TAKTUK`
    fileput_tool: str
        can be `execo.config.SCP`, `execo.config.TAKTUK` or `execo.config.CHAINPUT`
    fileget_tool: str
        can be `execo.config.SCP` or `execo.config.TAKTUK`

    Returns
    -------
    ActionFactory
        an object contains multiple remote process execution and file copies tools
        For more detail, see this: http://execo.gforge.inria.fr/doc/latest-stable/execo.html#actionfactory
    '''
    global executor_singleton
    if len(executor_singleton) > 0:
        return executor_singleton[0]
    else:
        executor = ActionFactory(remote_tool=remote_tool,
                                 fileput_tool=fileput_tool,
                                 fileget_tool=fileget_tool)
        executor_singleton.append(executor)
        return executor


def execute_cmd(cmd, hosts, mode='run'):
    """
    """
    remote_executor = get_remote_executor()
    result = None
    if mode == 'run':
        result = remote_executor.get_remote(cmd, hosts).run()
    elif mode == 'start':
        result = remote_executor.get_remote(cmd, hosts).start()
    logger = get_logger()

    host_errors = list()
    for process in result.processes:
        if process.error_reason == 'taktuk connection failed':
            host_errors.append(process.host)

    # config host -> check for alive hosts at the end of the configuration
    # workflow -> detect by wrap the execute_cmd by another command and check
    #             for return host_errors --> remove host from all hosts/available host
    #             then cancel the combination, remember to check the finally statement of
    #             the workflow
    if len(host_errors) == len(hosts):
        logger.error("Connection error to all hosts.\nProgram is terminated")
        exit()
    elif len(host_errors) > 0:
        logger.error("Connection error to %s hosts:\n%s" % (len(host_errors), '\n'.join(host_errors)))
        hosts = [host for host in hosts if host not in host_errors]
    return host_errors, result
