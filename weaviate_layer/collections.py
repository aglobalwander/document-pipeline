from typing import Optional, List # Import Optional and List
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

def ensure_collections_exist(schema_names: Optional[List[str]] = None):
    """
    Ensures that specified collections (or all defined) exist in Weaviate.
    If a collection does not exist, it will be created using the schema definition.

    Args:
        schema_names: Optional list of schema names to ensure. If None, all schemas in COLLECTION_SCHEMAS are processed.
    """
    client = None
    try:
        client = get_weaviate_client()

        schemas_to_process = COLLECTION_SCHEMAS
        if schema_names is not None:
            # Filter COLLECTION_SCHEMAS to include only the specified names
            schemas_to_process = [
                schema for schema in COLLECTION_SCHEMAS if schema.name in schema_names
            ]
            if len(schemas_to_process) != len(schema_names):
                missing_schemas = set(schema_names) - set(schema.name for schema in schemas_to_process)
                logging.warning(f"Could not find schema definitions for: {missing_schemas}. Skipping these.")


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
    ensure_collections_exist()