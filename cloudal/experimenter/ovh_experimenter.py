from ovh import ResourceNotFoundError, BadParametersError
from cloudal.utils import get_logger


logger = get_logger()


def is_node_active(node_ids, project_id, driver):
    """Check if the given node IDs are still running on OVHCloud system or not

    Parameters
    ----------
    node_ids: list of str

    Returns
    ------
    bool, node_id
        True: if the given node IDs is still alive and list of node ids 
        False: if some of the given node IDs is dead and list of node ids that are not running
    

    """
    
    
    nodes_ko = list()
    nodes_ok = list()
    for node in node_ids:
        try:
            node = driver.get('/cloud/project/%s/instance/%s' % (project_id, node))
        except (ResourceNotFoundError, BadParametersError):
            logger.info('Some of nodes are deleted')
            return False, nodes_ko
        if node['status'] != 'ACTIVE':
            nodes_ko.append(node)
        else:
            nodes_ok.append(node)

    if len(nodes_ok) == len(node_ids):
        logger.info('All nodes are running')
        return True, nodes_ok
    else:
        logger.info('The following hosts are not up: %s' % [node['id'] for node in nodes_ko])
        return False, nodes_ko

def delete_ovh_nodes(node_ids, project_id, driver):
    for node in node_ids:
        try:
            driver.delete('/cloud/project/%s/instance/%s' % (project_id, node))
        except (ResourceNotFoundError, BadParametersError):
            continue
    logger.info('Delete nodes successfully!')