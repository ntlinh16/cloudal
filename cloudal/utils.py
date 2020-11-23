import os
import yaml
import logging
import tenacity
from tenacity import retry

from execo.action import ActionFactory
from execo.config import TAKTUK, SSH, SCP, default_connection_params


default_connection_params['taktuk_connector_options'] = ('-o', 'BatchMode=yes',
                                                         '-o', 'PasswordAuthentication=no',
                                                         '-o', 'StrictHostKeyChecking=no',
                                                         '-o', 'UserKnownHostsFile=~/.ssh/known_hosts',
                                                         '-o', 'ConnectTimeout=20')

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


logger = get_logger()


def parse_config_file(config_file_path):
    if config_file_path is None or config_file_path == "":
        raise IOError("Please enter the configuration file path.")
    elif not os.path.exists(config_file_path):
        raise IOError("Please enter an existing configuration file path.")
    else:
        with open(config_file_path, 'r') as f:
            content = yaml.full_load(f)
            try:
                return {key: str(value) if isinstance(value, str) else value for key, value in content.items()}
            except NameError:
                return content


executor_singleton = list()


def get_remote_executor(remote_tool=SSH, fileput_tool=SCP, fileget_tool=SCP):
    '''Instantiate remote process execution and file copies tool

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


def chunk_list(input_list, n):
    """Yield successive n-sized chunks from a list."""
    for i in range(0, len(input_list), n):
        yield input_list[i:i + n]


class ExecuteCommandException(Exception):
    def __init__(self, message, is_continue=False):
        self.message = message
        self.is_continue = is_continue
        super(ExecuteCommandException, self).__init__(message)


def custom_retry_return(state):
    logger.warning("Exception when running command: %s" % state.exception())
    if not hasattr(state.exception(), 'is_continue'):
        raise(state.exception())
    if state.exception().is_continue == True:
        logger.warning('Retrying maximum times, continue without raising exception (%s)' % state.exception().message)
        return None
    else:
        logger.warning('Retrying maximum times')
        raise(state.exception())


@retry(
    reraise=True,
    stop=tenacity.stop_after_attempt(10),
    wait=tenacity.wait_random(1, 10),
    retry_error_callback=custom_retry_return,
    retry=tenacity.retry_if_exception_type(ExecuteCommandException)
)
def execute_cmd(cmd, hosts, mode='run', batch_size=5, is_continue=False):
    """ Performing a command on remote hosts
    Parameters
    ----------
    cmd: str
        command to perform on remote hosts

    hosts: list of str
        list of host names or IPs 

    mode: str
        run: start a process and wait until it ends
        start: start a process

    batch_size: int
        chunk the hosts to smaller batches with batch size

    is_continue: bool

    Returns
    -------
    """
    if hosts is None:
        raise Exception("Hosts cannot be None")
    if isinstance(hosts, str):
        hosts = [hosts]
    remote_executor = get_remote_executor()
    # workaround to fix a bug of sending command to many hosts from personal machine outside of G5k:
    result = list()
    for chunk in chunk_list(hosts, batch_size):
        if mode == 'run':
            result.append(remote_executor.get_remote(cmd, chunk).run())
        elif mode == 'start':
            result.append(remote_executor.get_remote(cmd, chunk).start())

    host_errors = list()
    for chunk in result:
        for process in chunk.processes:
            if process.error_reason == 'taktuk connection failed':
                host_errors.append(process.host)
            if ('ssh_exchange_identification' in process.stderr or (process.ok == False and process.stdout.strip())):
                logger.info('---> Retrying: %s\n' % cmd)
                raise ExecuteCommandException(message=process.stderr.strip(), is_continue=is_continue)
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
    processes = list()
    for each in result:
        processes += each.processes
    if result:
        result[0].processes = processes
        result[0].hosts = hosts
        result = result[0]
    return host_errors, result


def get_file(remote_file_paths, host, local_dir, mode='run'):
    """
    2 modes:
        run: start a process and wait until it ends
        start: start a process
    """
    remote_executor = get_remote_executor()
    if mode == 'run':
        remote_executor.get_fileget(host, remote_file_paths, local_dir).run()
    elif mode == 'start':
        remote_executor.get_fileget(host, remote_file_paths, local_dir).start()


def getput_file(hosts, file_paths, dest_location, action, mode='run', batch_size=5):
    """Perform files copy between local and remote

    Parameters
    ----------
    hosts: list of str
        list of remote hosts to get/send files

    file_paths: list of str
        list of file paths to (1) the local files to send to remote hosts or (2) the remote files to get to local

    dest_location: str
        the path to the destination directory

    action: str
        a type of action to perform between local and remote, there are 2 actions:
        - get: get file from remote dest_location to local
        - put: send file from local to remote dest_location

    mode: str
        the mode of executing the file copy operation, there are 2 modes:
        - run: start a process and wait until it ends
        - start: start a process

    batch_size: int
        the list of hosts will be chunked into N chunks of size: batch_size before executing a command
        as a workaround to the limitation of Grid5k for the number of concurrent ssh connection from local

    """
    remote_executor = get_remote_executor()
    if isinstance(hosts, str):
        hosts = [hosts]
    result = list()
    for chunk in chunk_list(hosts, batch_size):
        act = None
        if action == 'get':
            act = remote_executor.get_fileget(chunk, file_paths, dest_location)
        elif action == 'put':
            act = remote_executor.get_fileput(chunk, file_paths, dest_location)
        if act:
            if mode == 'run':
                result.append(act.run())
            elif mode == 'start':
                result.append(act.start())
