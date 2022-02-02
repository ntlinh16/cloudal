from execo_g5k.oar import get_current_oar_jobs, oardel
from execo_g5k.api_utils import get_g5k_sites

from cloudal.utils import get_logger

logger = get_logger()


sites = get_g5k_sites()
cur_jobs = get_current_oar_jobs(frontends=sites)

logger.info('We found these jobs:')
logger.info(''.join(['\n%s: %s' % (site, job_id)for job_id, site in cur_jobs]))

decision = input('Do you want to delete those jobs [y/n]? ')
if decision.lower().strip() == 'y':
    oardel(cur_jobs)
    logger.info('Delete jobs successfully!')
else:
    logger.info('Bye bye!')
