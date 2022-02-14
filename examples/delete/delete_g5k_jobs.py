from argparse import ArgumentParser
import sys

from execo_g5k.oar import get_current_oar_jobs, oardel
from execo_g5k.api_utils import get_g5k_sites


def parse_job_ids(job_id_str):
    job_ids = list()
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
        
        job_ids.append((job_id, site))
    
    return job_ids


def main(options):
    parser = ArgumentParser(prog='delete_jobs_G5k')

    parser.add_argument('-j', '--job_ids', 
                        dest='job_ids',
                        type=str,
                        help='Grid5000 job IDs')

    args = parser.parse_args()
    if args.job_ids:
        job_ids = parse_job_ids(args.job_ids)
        print('Jobs will be deleted:')
    else:
        sites = get_g5k_sites()
        job_ids =  get_current_oar_jobs(frontends=sites)
        print('All your running jobs:')

    print(''.join(['%s: %s\n' % (site, job_id)for job_id, site in job_ids]))

    decision = input('Do you want to delete those jobs [y/n]? ')
    if decision.lower().strip() == 'y':
        oardel(job_ids)
        print('Delete jobs successfully!')
    else:
        print('Bye bye!')

if __name__ == "__main__":
    main(sys.argv[1:])
    


