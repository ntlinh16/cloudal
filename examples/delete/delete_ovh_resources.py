import ovh

from cloudal.utils import get_logger
from cloudal.experimenter import delete_ovh_nodes
from argparse import ArgumentParser

logger = get_logger()

endpoint='ovh-eu'
application_key='abc'
application_secret='xyz'
consumer_key='qwe'
project_id='123'

logger.info("Creating a Driver to connect to OVHCloud")
driver = ovh.Client(
    endpoint=endpoint,
    application_key=application_key,
    application_secret=application_secret,
    consumer_key=consumer_key,
)
parser = ArgumentParser(prog='delete_nodes')
parser.add_argument("--node_ids_file", dest="node_ids_file",
                    help="the path to the file contents list of node IDs",
                    default=None,
                    required=True,
                    type=str)
parser.add_argument("--volumes_region", dest="volumes_region",
                    help="the list of regions where you want to delete all the volumes",
                    default=None,
                    type=str)
args = parser.parse_args()
if args.node_ids_file:
    with open(args.node_ids_file, 'r') as f:
        node_ids = [line.strip() for line in f]

logger.info('We found %s instances: \n' % len(node_ids))
for node in node_ids:
    print(node)

decision = input('Do you want to delete all instances [y/n]? ')
if decision.lower().strip() == 'y':
    delete_ovh_nodes(node_ids, project_id, driver)
else:
    logger.info('Bye bye!')
