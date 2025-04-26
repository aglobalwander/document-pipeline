from .schema import KnowledgeItemSchema, KnowledgeMainSchema # Updated import
from .client import get_weaviate_client
import logging

logging.basicConfig(level=logging.INFO)

# List of all collection schemas defined in schema.py that should exist
COLLECTION_SCHEMAS = [KnowledgeItemSchema, KnowledgeMainSchema]

def ensure_collections_exist():
    """
    Ensures that all defined collections in COLLECTION_SCHEMAS exist in Weaviate.
    If a collection does not exist, it will be created using the schema definition.
    """
    client = None
    try:
        client = get_weaviate_client()
        for schema in COLLECTION_SCHEMAS:
            logging.info(f"Checking if collection '{schema.name}' exists...")
            if not client.collections.exists(schema.name):
                logging.warning(f"Collection '{schema.name}' does not exist. Creating with defined schema...")
                # Use the v4 create method with dataclass attributes
                client.collections.create(
                    name=schema.name,
                    description=schema.description,
                    properties=schema.properties,
                    vectorizer_config=schema.vectorizer_config,
                    inverted_index_config=schema.inverted_index_config,
                    multi_tenancy_config=schema.multi_tenancy_config,
                    replication_config=schema.replication_config,
                    sharding_config=schema.sharding_config,
                    # Add other relevant configs from the dataclass if necessary
                )
                logging.info(f"Collection '{schema.name}' created.")
            else:
                logging.info(f"Collection '{schema.name}' already exists.")
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