from tenacity import retry, stop_after_attempt, wait_fixed
import weaviate, logging
from weaviate.classes.init import Auth
from .config import settings

# Configure logging for tenacity
logging.basicConfig(level=logging.INFO)
logging.getLogger("tenacity").setLevel(logging.DEBUG)

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def get_weaviate_client(config=None):
    """
    Connects to Weaviate Cloud or local instance with retry logic.
    
    Args:
        config: Optional dictionary with configuration overrides
    """
    # Log Weaviate client version for debugging
    logging.info(f"Weaviate client version: {weaviate.__version__}")
    
    # Use config overrides if provided, otherwise use settings
    weav_url = config.get('weaviate_url') if config and 'weaviate_url' in config else settings.weav_url
    weav_api_key = config.get('weaviate_api_key') if config and 'weaviate_api_key' in config else settings.weav_api_key
    
    logging.info("Attempting to connect to Weaviate...")
    logging.info(f"Using Weaviate URL: {weav_url if weav_url else 'Not set (will use local)'}")
    logging.info(f"API Key provided: {bool(weav_api_key)}")
    
    try:
        if weav_url and weav_api_key:
            logging.info(f"Connecting to Weaviate Cloud at {weav_url}")
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weav_url,
                auth_credentials=Auth.api_key(weav_api_key),
                skip_init_checks=True, # Skip checks during retry attempts
            )
            logging.info("Successfully connected to Weaviate Cloud")
            return client
        else:
            logging.info("Connecting to local Weaviate instance")
            client = weaviate.connect_to_local(
                skip_init_checks=True, # Skip checks during retry attempts
            )
            logging.info("Successfully connected to local Weaviate instance")
            return client
    except Exception as e:
        logging.error(f"Error connecting to Weaviate: {e}", exc_info=True)
        raise

# Note: Client closing should be handled by the caller when the client object is no longer needed.
# For example, using a 'with' statement or explicitly calling client.close().