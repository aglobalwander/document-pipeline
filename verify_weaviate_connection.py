import os
import weaviate
# Import the new get_weaviate_client function
from weaviate_layer.client import get_weaviate_client
from weaviate.classes.init import Auth
from tenacity import retry, stop_after_attempt, wait_fixed # Added import for tenacity
import logging

# Configure logging for the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# The get_weaviate_client function is now in weaviate_layer.client, so we call that.
# The retry logic is already inside get_weaviate_client, so no need for the decorator here.
def verify_connection():
    """
    Verifies connection to Weaviate using the get_weaviate_client function.
    """
    client = None
    try:
        logger.info("Attempting to get Weaviate client via weaviate_layer.client...")
        client = get_weaviate_client()

        # v4 does not have is_ready(); use a lightweight call to check
        try:
            collections = client.collections.list_all()
            logger.info("Weaviate client is ready!")
            logger.info(f"Collections: {list(collections.keys())}")
            return True
        except Exception as check_e:
            logger.error(f"Weaviate client is not ready or accessible: {check_e}")
            return False
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False
    finally:
        if client:
            client.close()
            logger.info("Weaviate client connection closed.")

if __name__ == "__main__":
    if verify_connection():
        logger.info("Weaviate connection verification successful.")
    else:
        logger.error("Weaviate connection verification failed.")