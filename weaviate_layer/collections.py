from typing import Optional, List # Import Optional and List
import yaml # Import yaml
from pathlib import Path # Import Path
from .schema import ( # Updated import to include media schemas
    KnowledgeItemSchema,
    KnowledgeMainSchema,
    AudioItemSchema,
    AudioChunkSchema,
    ImageItemSchema,
    VideoItemSchema,
    VideoChunkSchema,
)
from .client import get_weaviate_client
import logging

logging.basicConfig(level=logging.INFO)

# List of all collection schemas defined in schema.py that should exist
COLLECTION_SCHEMAS = [
    KnowledgeItemSchema,
    KnowledgeMainSchema,
    AudioItemSchema,
    AudioChunkSchema,
    ImageItemSchema,
    VideoItemSchema,
    VideoChunkSchema,
]

def ensure_collections_exist(collection_name: Optional[str] = None):
    """
    Ensures that a specified collection (using a YAML schema file) or all defined
    collections (using internal schemas) exist in Weaviate.

    Args:
        collection_name: Optional name of a specific collection to ensure.
                         If provided, loads schema from weaviate_layer/schemas/{collection_name}.yaml.
                         If None, processes all schemas in COLLECTION_SCHEMAS.
    """
    client = None
    try:
        logging.info("Starting ensure_collections_exist function")
        try:
            client = get_weaviate_client()
            logging.info("Successfully obtained Weaviate client")
        except Exception as e:
            logging.error(f"Error getting Weaviate client: {e}", exc_info=True)
            raise

        if collection_name:
            schema_file_path = Path(__file__).parent / "schemas" / f"{collection_name}.yaml"
            logging.info(f"Attempting to load schema from {schema_file_path}")
            if not schema_file_path.exists():
                logging.error(f"Schema file not found for collection '{collection_name}': {schema_file_path}")
                raise FileNotFoundError(f"Schema file not found for collection '{collection_name}'")

            try:
                with open(schema_file_path, 'r') as f:
                    schema_definition = yaml.safe_load(f)
                logging.info(f"Loaded schema for collection '{collection_name}' from YAML.")

                # Use the loaded schema definition to create the collection
                logging.info(f"Checking if collection '{collection_name}' exists...")
                try:
                    exists = client.collections.exists(collection_name)
                    logging.info(f"Collection existence check result: {exists}")
                except Exception as e:
                    logging.error(f"Error checking if collection exists: {e}", exc_info=True)
                    raise
                
                if not exists:
                    logging.warning(f"Collection '{collection_name}' does not exist. Creating with defined schema...")
                    # Log the schema definition for debugging
                    logging.info(f"Schema definition: {schema_definition}")
                    
                    # Import necessary classes here to ensure they're available
                    from weaviate.classes.config import Property, Configure, DataType
                    
                    # Parse YAML data into Weaviate client configuration objects
                    logging.info("Creating properties configuration")
                    try:
                        # Convert YAML dataType array to DataType enum
                        properties_config = []
                        for p in schema_definition.get('properties', []):
                            # Get the first dataType from the array and convert to enum
                            data_type_str = p['dataType'][0] if isinstance(p['dataType'], list) else p['dataType']
                            logging.info(f"Converting dataType '{data_type_str}' to DataType enum")
                            
                            # Map string to DataType enum
                            if data_type_str == 'TEXT':
                                data_type_enum = DataType.TEXT
                            elif data_type_str == 'INT':
                                data_type_enum = DataType.INT
                            elif data_type_str == 'NUMBER':
                                data_type_enum = DataType.NUMBER
                            elif data_type_str == 'BOOLEAN':
                                data_type_enum = DataType.BOOLEAN
                            elif data_type_str == 'DATE':
                                data_type_enum = DataType.DATE
                            elif data_type_str == 'TEXT_ARRAY':
                                data_type_enum = DataType.TEXT_ARRAY
                            else:
                                logging.warning(f"Unknown dataType: {data_type_str}, defaulting to TEXT")
                                data_type_enum = DataType.TEXT
                                
                            properties_config.append(Property(name=p['name'], data_type=data_type_enum))
                        
                        logging.info("Properties configuration created successfully")
                        
                        logging.info("Creating vectorizer configuration")
                        vectorizer_config = None
                        if schema_definition.get('vectorizerConfig'):
                            logging.info(f"Vectorizer config from YAML: {schema_definition.get('vectorizerConfig')}")
                            
                            # Handle different vectorizer types
                            vectorizer_config_dict = schema_definition.get('vectorizerConfig', {})
                            if 'text2vec-openai' in vectorizer_config_dict:
                                logging.info("Creating text2vec-openai vectorizer configuration")
                                openai_config = vectorizer_config_dict['text2vec-openai']
                                vectorizer_config = Configure.Vectorizer.text2vec_openai(
                                    model=openai_config.get('model', 'text-embedding-3-large')
                                )
                            else:
                                # Fall back to generic approach if not a known type
                                logging.info("Using generic vectorizer configuration approach")
                                try:
                                    vectorizer_config = Configure.Vectorizer(**vectorizer_config_dict)
                                except Exception as e:
                                    logging.error(f"Error creating vectorizer config with generic approach: {e}")
                                    # Create a minimal default config if all else fails
                                    vectorizer_config = None
                            
                            logging.info("Vectorizer configuration created successfully")
                    except Exception as e:
                        logging.error(f"Error creating configuration objects: {e}", exc_info=True)
                        raise
                    
                    # Add parsing for other configs as needed (e.g., inverted_index_config, multi_tenancy_config, etc.)
                    
                    logging.info("Attempting to create collection")
                    try:
                        client.collections.create(
                        name=schema_definition['name'],
                        description=schema_definition.get('description'),
                        properties=properties_config,
                        vectorizer_config=vectorizer_config,
                        # Pass other parsed configs here
                        inverted_index_config=schema_definition.get('inverted_index_config'),
                        multi_tenancy_config=schema_definition.get('multi_tenancy_config'),
                        replication_config=schema_definition.get('replication_config'),
                        sharding_config=schema_definition.get('sharding_config'),
                        )
                        logging.info(f"Collection '{collection_name}' created successfully")
                    except Exception as e:
                        logging.error(f"Error creating collection: {e}", exc_info=True)
                        raise
                    logging.info(f"Collection '{collection_name}' created.")
                else:
                    logging.info(f"Collection '{collection_name}' already exists.")

            except yaml.YAMLError as e:
                logging.error(f"Error parsing YAML schema file {schema_file_path}: {e}")
                raise ValueError(f"Invalid YAML schema file: {schema_file_path}") from e
            except KeyError as e:
                 logging.error(f"Missing required key in YAML schema file {schema_file_path}: {e}")
                 raise ValueError(f"Missing required key in YAML schema file: {schema_file_path}") from e
            except Exception as e:
                 logging.error(f"Unexpected error processing YAML schema {schema_file_path}: {e}")
                 raise # Re-raise unexpected errors

        else:
            # Existing logic to process all predefined schemas
            schemas_to_process = COLLECTION_SCHEMAS
            # The original filtering logic by schema_names list is removed as the function now takes a single collection_name or processes all predefined
            # If filtering by a list of names is still needed, this section would require adjustment.
            # For this plan, we assume either a single name is provided or all predefined are processed.

            for schema_class in schemas_to_process:
                # Instantiate the schema class to access its attributes
                schema_instance = schema_class()
                logging.info(f"Checking if collection '{schema_instance.name}' exists...")
                if not client.collections.exists(schema_instance.name):
                    logging.warning(f"Collection '{schema_instance.name}' does not exist. Creating with defined schema...")
                    # Use the v4 create method with attributes from the schema instance
                    client.collections.create(
                        name=schema_instance.name,
                        description=schema_instance.description,
                        properties=schema_instance.properties,
                        vectorizer_config=schema_instance.vectorizer_config,
                        inverted_index_config=schema_instance.inverted_index_config,
                        multi_tenancy_config=schema_instance.multi_tenancy_config,
                        replication_config=schema_instance.replication_config,
                        sharding_config=schema_instance.sharding_config,
                        # Add other relevant configs from the dataclass if necessary
                    )
                    logging.info(f"Collection '{schema_instance.name}' created.")
                else:
                    logging.info(f"Collection '{schema_instance.name}' already exists.")

    except Exception as e:
        logging.error(f"An error occurred during collection check/creation: {e}")
        # Depending on desired behavior, you might want to re-raise or handle differently
        # For now, re-raise to indicate a failure in ensuring collections exist
        raise
    finally:
        if client:
            client.close()
            logging.info("Weaviate client closed.")

# Example usage (can be called from CLI or other scripts)
if __name__ == "__main__":
    # Example of ensuring a specific collection from YAML
    # ensure_collections_exist(collection_name="SampleCollection")

    # Example of ensuring all predefined collections
    ensure_collections_exist()