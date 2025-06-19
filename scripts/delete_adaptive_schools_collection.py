#!/usr/bin/env python3
"""
Script to delete the AdaptiveSchools collection from Weaviate.
This is useful when you need to recreate the collection with a new schema.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from weaviate_layer.client import get_weaviate_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Delete the AdaptiveSchools collection from Weaviate."""
    try:
        # Connect to Weaviate
        logger.info("Connecting to Weaviate...")
        client = get_weaviate_client()
        logger.info("Successfully connected to Weaviate")
        
        # Check if AdaptiveSchools collection exists
        logger.info("Checking if AdaptiveSchools collection exists...")
        exists = client.collections.exists("AdaptiveSchools")
        
        if exists:
            logger.info("AdaptiveSchools collection exists. Deleting...")
            client.collections.delete("AdaptiveSchools")
            logger.info("AdaptiveSchools collection deleted successfully")
        else:
            logger.info("AdaptiveSchools collection does not exist. Nothing to delete.")
        
        # Close the client
        client.close()
        logger.info("Weaviate client closed")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
