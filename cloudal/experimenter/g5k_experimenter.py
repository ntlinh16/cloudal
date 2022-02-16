from time import sleep

from cloudal.utils import get_logger

from execo_g5k import get_host_attributes, get_oar_job_info


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


def is_job_alive(oar_job_ids):
    """Check if the given OAR_JOB_IDs are still alive on Grid5000 system or not

    Parameters
    ----------
    oar_job_ids: dict
        a dictionary that contains the reserved information 
        key: str, the name of the site on Grid5000 system
        value: int, the number of the reservation on that site

    Returns
    ------
    bool
        True: if the given oar_job_ids is still alive
        False: if  the given oar_job_ids is dead

    """
    for oar_job_id, site in oar_job_ids:
        job_info = get_oar_job_info(oar_job_id, site)
        while 'state' not in job_info:
            job_info = get_oar_job_info(oar_job_id, site)
            sleep(5)
        if job_info['state'] == 'Error':
            return False
    return True

def parse_job_ids(job_id_str):
    """Parse a given string of oar_job_ids to a  a dictionary that contains the information 
        key: int, the number of the reservation on Grid5000 site
        value: str, the name of the site on Grid5000 system
        

    Parameters
    ----------
    job_id_str: str

    Returns
    ------
    oar_job_ids: dict
        a dictionary that contains the reserved information 
        key: str, the name of the site on Grid5000 system
        value: int, the number of the reservation on that site

    """

    oar_job_ids = list()
    if ':' not in job_id_str:
        raise ValueError('Please give the right format of job IDs <site:id>,<site:id>....')
    for each in job_id_str.split(','):
        if len(each.strip()) == 0:
            continue
        try:
            site, job_id = each.split(':')
            job_id = int(job_id)
        except ValueError:
            raise ValueError('Please give the right format of job IDs <site:id>,<site:id>....')
        
        oar_job_ids.append((job_id, site))
    
    return oar_job_ids

