#!/usr/bin/env python
"""
Script to check Weaviate API functionality with SampleCollection.
"""

import logging
import sys
import yaml
from pathlib import Path
import traceback

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
    from weaviate.classes.config import Property, Configure, DataType
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

def check_sample_collection():
    """Test creating the SampleCollection."""
    collection_name = "SampleCollection"
    
    # Load the schema from YAML
    schema_file_path = Path("weaviate_layer/schemas") / f"{collection_name}.yaml"
    logger.info(f"Loading schema from {schema_file_path}")
    
    try:
        with open(schema_file_path, 'r') as f:
            schema_definition = yaml.safe_load(f)
        logger.info(f"Successfully loaded schema: {schema_definition}")
    except Exception as e:
        logger.error(f"Error loading schema file: {e}")
        return False
    
    # Connect to Weaviate
    try:
        client = get_weaviate_client()
        logger.info("Successfully connected to Weaviate")
    except Exception as e:
        logger.error(f"Failed to connect to Weaviate: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Check if collection exists
        exists = client.collections.exists(collection_name)
        logger.info(f"Collection '{collection_name}' exists: {exists}")
        
        if exists:
            # Get collection info
            collection = client.collections.get(collection_name)
            logger.info(f"Collection properties: {[p.name for p in collection.properties]}")
            logger.info(f"Collection vectorizer: {collection.vectorizer_config}")
        else:
            # Try to create the collection manually
            logger.info(f"Attempting to create collection '{collection_name}'")
            
            # Parse properties from YAML
            properties = []
            for prop in schema_definition.get('properties', []):
                logger.info(f"Creating property: {prop['name']}")
                properties.append(
                    Property(
                        name=prop['name'],
                        data_type=prop['dataType'][0]  # Assuming first dataType is the primary one
                    )
                )
            
            # Parse vectorizer config
            vectorizer_config = None
            if 'vectorizerConfig' in schema_definition:
                logger.info(f"Vectorizer config in YAML: {schema_definition['vectorizerConfig']}")
                
                # Check if OpenAI API key is set
                if 'text2vec-openai' in schema_definition['vectorizerConfig']:
                    if not settings.openai_api_key:
                        logger.error("OpenAI API key is required for text2vec-openai vectorizer but is not set")
                    else:
                        logger.info("OpenAI API key is set")
                
                # Create vectorizer config
                try:
                    vectorizer_name = list(schema_definition['vectorizerConfig'].keys())[0]
                    vectorizer_params = schema_definition['vectorizerConfig'][vectorizer_name]
                    
                    logger.info(f"Creating vectorizer config for {vectorizer_name} with params {vectorizer_params}")
                    
                    if vectorizer_name == 'text2vec-openai':
                        vectorizer_config = Configure.Vectorizer.text2vec_openai(**vectorizer_params)
                    # Add other vectorizers as needed
                    
                    logger.info(f"Vectorizer config created: {vectorizer_config}")
                except Exception as e:
                    logger.error(f"Error creating vectorizer config: {e}")
                    traceback.print_exc()
            
            # Create the collection
            try:
                collection = client.collections.create(
                    name=schema_definition['name'],
                    description=schema_definition.get('description', ''),
                    properties=properties,
                    vectorizer_config=vectorizer_config
                )
                logger.info(f"Successfully created collection '{collection_name}'")
            except Exception as e:
                logger.error(f"Error creating collection: {e}")
                traceback.print_exc()
                return False
        
        # Close the client
        client.close()
        logger.info("Connection closed")
        
    except Exception as e:
        logger.error(f"Error during collection operations: {e}")
        traceback.print_exc()
        if client:
            client.close()
        return False
    
    return True

if __name__ == "__main__":
    success = check_sample_collection()
    sys.exit(0 if success else 1)