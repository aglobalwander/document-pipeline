#!/usr/bin/env python3
"""
Script to generate a summary report of the AdaptiveSchools collection in Weaviate.

This script:
1. Connects to Weaviate
2. Retrieves information about the AdaptiveSchools collection
3. Generates a summary report of the documents, chunks, and tags
"""

import sys
import logging
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Set

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

def get_collection_stats(collection_name: str = "AdaptiveSchools") -> Dict[str, Any]:
    """Get statistics about the AdaptiveSchools collection."""
    client = get_weaviate_client()
    
    try:
        # Check if collection exists
        if not client.collections.exists(collection_name):
            logger.error(f"Collection '{collection_name}' does not exist")
            return {}
        
        # Get the collection
        collection = client.collections.get(collection_name)
        
        # Get all objects
        response = collection.query.fetch_objects(
            limit=1000,  # Adjust as needed
            return_properties=["text", "chunk_index", "document_id", "title", "type", "chapterNumber", "tags", "source", "uniqueId"]
        )
        
        # Get total count
        total_count = 0
        if hasattr(response, 'total_count'):
            total_count = response.total_count
        elif hasattr(response, 'total_results'):
            total_count = response.total_results
        else:
            # Count the objects manually
            total_count = len(response.objects)
        
        # Initialize statistics
        stats = {
            "total_objects": total_count,
            "doc_types": Counter(),
            "tags": Counter(),
            "chapters": 0,
            "appendices": 0,
            "other": 0,
            "avg_content_length": 0,
            "unique_tags": set(),
            "document_count": 0,
            "chunks_per_document": [],
            "document_ids": set(),
        }
        
        # Group objects by document_id
        documents = defaultdict(list)
        
        # Calculate statistics
        total_content_length = 0
        
        for obj in response.objects:
            # Count document types
            doc_type = obj.properties.get("type", "unknown")
            stats["doc_types"][doc_type] += 1
            
            # Count document categories
            if doc_type == "chapter":
                stats["chapters"] += 1
            elif doc_type == "appendix":
                stats["appendices"] += 1
            else:
                stats["other"] += 1
            
            # Count tags
            tags_str = obj.properties.get("tags", "")
            if tags_str:
                # Split the comma-separated string into individual tags
                tags_list = [tag.strip() for tag in tags_str.split(",")]
                for tag in tags_list:
                    if tag:  # Skip empty tags
                        stats["tags"][tag] += 1
                        stats["unique_tags"].add(tag)
            
            # Calculate content length
            content = obj.properties.get("text", "")
            total_content_length += len(content)
            
            # Group by document_id
            doc_id = obj.properties.get("document_id", "")
            if doc_id:
                documents[doc_id].append(obj)
                stats["document_ids"].add(doc_id)
        
        # Calculate document statistics
        stats["document_count"] = len(documents)
        
        for doc_id, chunks in documents.items():
            stats["chunks_per_document"].append(len(chunks))
        
        # Calculate average content length
        if stats["total_objects"] > 0:
            stats["avg_content_length"] = total_content_length / stats["total_objects"]
        
        # Calculate average chunks per document
        if stats["document_count"] > 0:
            stats["avg_chunks_per_document"] = sum(stats["chunks_per_document"]) / stats["document_count"]
        else:
            stats["avg_chunks_per_document"] = 0
        
        return stats
    
    finally:
        client.close()

def print_summary_report(stats: Dict[str, Any]) -> None:
    """Print a summary report of the AdaptiveSchools collection."""
    if not stats:
        print("No statistics available. Make sure the AdaptiveSchools collection exists.")
        return
    
    print("\n" + "="*50)
    print("ADAPTIVE SCHOOLS COLLECTION SUMMARY")
    print("="*50)
    print(f"Total chunks: {stats['total_objects']}")
    print(f"Total documents: {stats['document_count']}")
    print(f"Average chunks per document: {stats.get('avg_chunks_per_document', 0):.1f}")
    print(f"Chapters: {stats['chapters']}")
    print(f"Appendices: {stats['appendices']}")
    print(f"Other documents: {stats['other']}")
    print(f"Average chunk length: {stats['avg_content_length']:.0f} characters")
    print(f"Unique tags: {len(stats['unique_tags'])}")
    
    print("\nDocument types:")
    for doc_type, count in stats["doc_types"].most_common():
        print(f"  - {doc_type}: {count}")
    
    print("\nTop 20 tags:")
    for tag, count in stats["tags"].most_common(20):
        print(f"  - {tag}: {count}")
    
    print("="*50)

def main():
    """Main function."""
    try:
        # Get collection statistics
        stats = get_collection_stats()
        
        # Print summary report
        print_summary_report(stats)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
