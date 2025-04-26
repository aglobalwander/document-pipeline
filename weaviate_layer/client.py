from tenacity import retry, stop_after_attempt, wait_fixed
import weaviate, logging
from weaviate.classes.init import Auth
from .config import settings

# Configure logging for tenacity
logging.basicConfig(level=logging.INFO)
logging.getLogger("tenacity").setLevel(logging.DEBUG)

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def get_weaviate_client():
    """
    Connects to Weaviate Cloud or local instance with retry logic.
    """
    logging.info("Attempting to connect to Weaviate...")
    if settings.weav_url and settings.weav_api_key:
        logging.info(f"Connecting to Weaviate Cloud at {settings.weav_url}")
        return weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.weav_url,
            auth_credentials=Auth.api_key(settings.weav_api_key),
            skip_init_checks=True, # Skip checks during retry attempts
        )
    else:
        logging.info("Connecting to local Weaviate instance")
        return weaviate.connect_to_local(
             skip_init_checks=True, # Skip checks during retry attempts
        )

# Note: Client closing should be handled by the caller when the client object is no longer needed.
# For example, using a 'with' statement or explicitly calling client.close().