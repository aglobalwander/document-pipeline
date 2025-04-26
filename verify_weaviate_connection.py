#!/usr/bin/env python
"""
Script to verify Weaviate connection and diagnose issues.
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add project root to sys.path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

try:
    import weaviate
    logger.info(f"Weaviate client version: {weaviate.__version__}")
except ImportError:
    logger.error("Failed to import weaviate. Is it installed? Try: pip install weaviate-client")
    sys.exit(1)

# Import our client getter
try:
    from weaviate_layer.client import get_weaviate_client
    from weaviate_layer.config import settings
    logger.info("Successfully imported project modules")
except ImportError as e:
    logger.error(f"Failed to import project modules: {e}")
    sys.exit(1)

def main():
    """Test Weaviate connection and print diagnostic information."""
    # Print environment settings
    logger.info("=== Environment Settings ===")
    logger.info(f"Weaviate URL: {settings.weav_url if settings.weav_url else 'Not set (will use local)'}")
    logger.info(f"Weaviate API Key provided: {bool(settings.weav_api_key)}")
    logger.info(f"OpenAI API Key provided: {bool(settings.openai_api_key)}")
    
    # Try to connect
    logger.info("=== Connection Test ===")
    try:
        client = get_weaviate_client()
        logger.info("Successfully connected to Weaviate!")
        
        # Check if we can get the schema
        logger.info("=== Schema Test ===")
        try:
            schema = client.schema.get()
            logger.info(f"Successfully retrieved schema with {len(schema['classes'] if 'classes' in schema else [])} classes")
            
            # List collections (v4 client)
            try:
                collections = client.collections.list_all()
                logger.info(f"Collections: {[c.name for c in collections]}")
            except Exception as e:
                logger.error(f"Error listing collections: {e}")
                
        except Exception as e:
            logger.error(f"Error retrieving schema: {e}")
        
        # Close the client
        client.close()
        logger.info("Connection closed")
        
    except Exception as e:
        logger.error(f"Failed to connect to Weaviate: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)