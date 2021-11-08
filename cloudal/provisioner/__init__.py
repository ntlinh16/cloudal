from cloudal.utils import get_logger

logger = get_logger()

try:
    from .g5k_provisioner import g5k_provisioner
except ImportError:
    logger.warning('Missing dependencies to use GCP provisioner')

try:
    from .gcp_provisioner import gcp_provisioner
except ImportError:
    logger.warning('Missing dependencies to use GCP provisioner')

try:
    from .gke_provisioner import gke_provisioner
except ImportError:
    logger.warning('Missing dependencies to use GKE provisioner')

try:
    from .azure_provisioner import azure_provisioner
except ImportError:
    logger.warning('Missing dependencies to use Azure provisioner')

try:
    from .ovh_provisioner import ovh_provisioner
except ImportError:
    logger.warning('Missing dependencies to use OVH provisioner')