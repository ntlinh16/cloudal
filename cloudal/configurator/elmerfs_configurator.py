from time import sleep

from cloudal.utils import get_logger, execute_cmd, getput_file
from cloudal.configurator import packages_configurator, k8s_resources_configurator

logger = get_logger()
class elmerfs_configurator(object):

    def install_elmerfs(self, kube_master, elmerfs_hosts, elmerfs_mountpoint, elmerfs_repo, elmerfs_version, elmerfs_path):

        # Create folder to build the elmerfs from the repo
        # cmd = 'rm -rf /tmp/elmerfs_repo && mkdir -p /tmp/elmerfs_repo'
        # execute_cmd(cmd, elmerfs_hosts)

        if elmerfs_repo is None:
            elmerfs_repo = 'https://github.com/scality/elmerfs'
        if elmerfs_version is None:
            elmerfs_version = 'latest'

        if elmerfs_path is None:
            logger.info('Installing elmerfs')
            configurator = packages_configurator()
            configurator.install_packages(['libfuse2', 'wget', 'jq'], elmerfs_hosts)
            logger.info('Create folder to build the elmerfs from the repo')
            # Create folder to build the elmerfs from the repo
            cmd = 'rm -rf /tmp/elmerfs_repo && mkdir -p /tmp/elmerfs_repo'
            execute_cmd(cmd, kube_master)

            logger.info('Downloading elmerfs project from the repo')
            cmd = '''curl \
                    -H 'Accept: application/vnd.github.v3+json' \
                    https://api.github.com/repos/scality/elmerfs/releases/%s | jq '.tag_name' \
                    | xargs -I tag_name git clone https://github.com/scality/elmerfs.git --branch tag_name --single-branch /tmp/elmerfs_repo ''' % elmerfs_version
            execute_cmd(cmd, kube_master)

            logger.info('update the repo')
            cmd = 'cd /tmp/elmerfs_repo \
                   && git submodule update --init --recursive'
            execute_cmd(cmd, kube_master)

            logger.info('Creating the Docker file')
            cmd = '''cat <<EOF | sudo tee /tmp/elmerfs_repo/Dockerfile
                     FROM rust:1.47
                     RUN mkdir  /elmerfs
                     WORKDIR /elmerfs
                     COPY . .
                     RUN apt-get update \
                         && apt-get -y install libfuse-dev
                     RUN cargo build --release
                     CMD ['/bin/bash']
                   '''
            execute_cmd(cmd, kube_master)

            logger.info('Building elmerfs Docker image')
            cmd = 'cd /tmp/elmerfs_repo/ \
                   && docker build -t elmerfs .'
            execute_cmd(cmd, kube_master)

            logger.info('Building elmerfs')
            cmd = 'docker run --name elmerfs elmerfs \
                   && docker cp -L elmerfs:/elmerfs/target/release/main /tmp/elmerfs \
                   && docker rm elmerfs'
            execute_cmd(cmd, kube_master)

            getput_file(hosts=[kube_master],
                        file_paths=['/tmp/elmerfs'],
                        dest_location='/tmp',
                        action='get',)
            elmerfs_path = '/tmp/elmerfs'

        logger.info('Uploading elmerfs binary file from local to %s elmerfs hosts' % len(elmerfs_hosts))
        getput_file(hosts=elmerfs_hosts,
                    file_paths=[elmerfs_path],
                    dest_location='/tmp',
                    action='put')
        cmd = 'chmod +x /tmp/elmerfs'
        execute_cmd(cmd, elmerfs_hosts)
        logger.info('Create mountpoint and result folder')
        cmd = 'rm -rf /tmp/results && mkdir -p /tmp/results && \
               rm -rf %s && mkdir -p %s' % (elmerfs_mountpoint, elmerfs_mountpoint)
        execute_cmd(cmd, elmerfs_hosts)

    def deploy_elmerfs(self, clusters, kube_namespace, elmerfs_hosts, elmerfs_mountpoint, antidote_ips):
        logger.info('Killing elmerfs process if it is running')
        logger.debug('elmerfs_hosts: %s' % elmerfs_hosts)
        for host in elmerfs_hosts:
            cmd = 'pidof elmerfs'
            _, r = execute_cmd(cmd, host)
            pids = r.processes[0].stdout.strip().split(' ')

            if len(pids) >= 1 and pids[0] != '':
                for pid in pids:
                    cmd = 'kill %s' % pid.strip()
                    execute_cmd(cmd, host)
                sleep(5)

            cmd = 'mount | grep %s' % elmerfs_mountpoint
            _, r = execute_cmd(cmd, host)
            is_mount = r.processes[0].stdout.strip()

            if is_mount:
                cmd = 'umount %s ' % elmerfs_mountpoint
                execute_cmd(cmd, host)

        logger.info('Delete all files on elmerfs nodes from the previous run')
        cmd = 'rm -rf /tmp/results && mkdir -p /tmp/results'
        execute_cmd(cmd, elmerfs_hosts)
        cmd = 'rm -rf %s && mkdir -p %s' % (elmerfs_mountpoint, elmerfs_mountpoint)
        execute_cmd(cmd, elmerfs_hosts)

        logger.info('Downloading the elmerfs configuration file on %s hosts' % len(elmerfs_hosts))
        cmd = 'wget https://raw.githubusercontent.com/scality/elmerfs/master/Elmerfs.template.toml -P /tmp/ -N'
        execute_cmd(cmd, elmerfs_hosts)

        elmerfs_cluster_id = set(range(0, len(clusters)))
        elmerfs_node_id = set(range(0, len(elmerfs_hosts)))
        elmerfs_uid = set(range(len(elmerfs_hosts), len(elmerfs_hosts)*2))

        logger.info('Editing the elmerfs configuration file on %s hosts' % len(elmerfs_hosts))
        for cluster in clusters:
            configurator = k8s_resources_configurator()
            host_info = configurator.get_k8s_resources(resource='node',
                                                    label_selectors='cluster=%s' % cluster.lower(),
                                                    kube_namespace=kube_namespace)
            hosts = [host.metadata.annotations['flannel.alpha.coreos.com/public-ip'] for host in host_info.items]
            cluster_id = elmerfs_cluster_id.pop()
            for host in hosts:
                if host in antidote_ips:
                    logger.debug('Editing the configuration file on host %s' % host)
                    logger.debug('elmerfs_node_id = %s, elmerfs_cluster_id = %s' %
                                (elmerfs_node_id, elmerfs_cluster_id))
                    ips = ' '.join([ip for ip in antidote_ips[host]])
                    cmd = '''sed -i 's/127.0.0.1:8101/%s:8087/g' /tmp/Elmerfs.template.toml ;
                            sed -i 's/node_id = 0/node_id = %s/g' /tmp/Elmerfs.template.toml ;
                            sed -i 's/cluster_id = 0/cluster_id = %s/g' /tmp/Elmerfs.template.toml
                        ''' % (ips, elmerfs_node_id.pop(), cluster_id)
                    execute_cmd(cmd, host)

        logger.info('Running bootstrap command on host %s' % elmerfs_hosts[0])
        cmd = '/tmp/elmerfs --config /tmp/Elmerfs.template.toml --bootstrap --mount %s' % elmerfs_mountpoint
        execute_cmd(cmd, elmerfs_hosts[0])
        # waiting for the bootstrap common to propagate on all DCs
        sleep(30)

        logger.info('Starting elmerfs on %s hosts' % len(elmerfs_hosts))
        for host in elmerfs_hosts:
            elmerfs_cmd = 'RUST_BACKTRACE=1 RUST_LOG=debug nohup /tmp/elmerfs --config /tmp/Elmerfs.template.toml --mount=%s --force-view=%s > /tmp/elmer.log 2>&1' % (elmerfs_mountpoint, elmerfs_uid.pop())
            logger.debug('Starting elmerfs on %s with cmd: %s' % (host, elmerfs_cmd))
            execute_cmd(elmerfs_cmd, host, mode='start')
            
            logger.info('Checking if elmerfs is running on host %s' % host)
            sleep(5)
            for i in range(10):
                cmd = 'pidof elmerfs'
                _, r = execute_cmd(cmd, host)
                pid = r.processes[0].stdout.strip().split(' ')

                if len(pid) >= 1 and pid[0].strip():
                    logger.info('elmerfs starts successfully')
                    break
                else:
                    logger.info('---> Retrying: starting elmerfs again')
                    execute_cmd(elmerfs_cmd, host, mode='start')
                    sleep(5)
            else:
                logger.info('Cannot deploy elmerfs on host %s' % host)
                return False

        logger.info('Finish deploying elmerfs')
        return True