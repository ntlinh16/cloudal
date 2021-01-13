from .g5k_provisioner import g5k_provisioner
from .azure_provisioner import azure_provisioner
from cloudal.utils import get_logger

logger = get_logger()


try:
    from .gcp_provisioner import gcp_provisioner
except ImportError:
    logger.warning('Missing dependencies to use GCP provisioner')

try:
    from .gke_provisioner import gke_provisioner
except ImportError:
    logger.warning('Missing dependencies to use GKE provisioner')
