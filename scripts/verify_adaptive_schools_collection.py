#!/usr/bin/env python3
"""
Script to verify the Weaviate connection and check if the AdaptiveSchools collection exists.
"""

import sys
import logging
from pathlib import Path
from collections import defaultdict

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
    """Verify Weaviate connection and check if AdaptiveSchools collection exists."""
    try:
        # Connect to Weaviate
        logger.info("Connecting to Weaviate...")
        client = get_weaviate_client()
        logger.info("Successfully connected to Weaviate")
        
        # Check if AdaptiveSchools collection exists
        logger.info("Checking if AdaptiveSchools collection exists...")
        exists = client.collections.exists("AdaptiveSchools")
        
        if exists:
            logger.info("AdaptiveSchools collection exists")
            
            # Get collection info
            collection = client.collections.get("AdaptiveSchools")
            properties = collection.config.get().properties
            
            logger.info(f"Collection properties:")
            for prop in properties:
                logger.info(f"  - {prop.name} ({prop.data_type})")
            
            # Count objects in collection
            try:
                # Try the newer API first
                result = collection.query.fetch_objects(
                    limit=1000,  # Get a large number of objects to analyze
                    return_properties=["document_id", "chunk_index", "title", "type"]
                )
                
                # Count total objects
                total_objects = len(result.objects)
                logger.info(f"Total objects in collection: {total_objects}")
                
                # Count unique documents
                document_ids = set()
                document_chunks = defaultdict(list)
                
                for obj in result.objects:
                    doc_id = obj.properties.get("document_id")
                    if doc_id:
                        document_ids.add(doc_id)
                        document_chunks[doc_id].append(obj)
                
                logger.info(f"Total unique documents: {len(document_ids)}")
                
                # Calculate average chunks per document
                if document_ids:
                    chunks_per_doc = [len(chunks) for chunks in document_chunks.values()]
                    avg_chunks = sum(chunks_per_doc) / len(chunks_per_doc)
                    logger.info(f"Average chunks per document: {avg_chunks:.1f}")
                
                # Count document types
                doc_types = defaultdict(int)
                for obj in result.objects:
                    doc_type = obj.properties.get("type")
                    if doc_type:
                        doc_types[doc_type] += 1
                
                logger.info("Document types:")
                for doc_type, count in doc_types.items():
                    logger.info(f"  - {doc_type}: {count}")
                
            except Exception as count_error:
                logger.error(f"Error counting objects: {count_error}")
                logger.info("Unable to determine the total count of objects in the collection.")
            
        else:
            logger.warning("AdaptiveSchools collection does not exist")
            logger.info("You can create it by running: python -c 'from weaviate_layer.collections import ensure_collections_exist; ensure_collections_exist(\"AdaptiveSchools\")'")
        
        # Close the client
        client.close()
        logger.info("Weaviate client closed")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
