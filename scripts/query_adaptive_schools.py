#!/usr/bin/env python3
"""
Script to query the AdaptiveSchools collection in Weaviate.

This script demonstrates how to:
1. Perform semantic searches
2. Filter by document type, chapter number, or tags
3. Retrieve and display results
4. Group results by document
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
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

def semantic_search(query: str, limit: int = 5, collection_name: str = "AdaptiveSchools", group_by_document: bool = False) -> List[Dict[str, Any]]:
    """Perform a semantic search on the AdaptiveSchools collection."""
    client = get_weaviate_client()
    
    try:
        # Get the collection
        collection = client.collections.get(collection_name)
        
        # Perform the search
        response = collection.query.near_text(
            query=query,
            limit=limit if not group_by_document else 20,  # Get more results if grouping
            return_properties=["text", "chunk_index", "document_id", "title", "type", "chapterNumber", "tags", "source", "uniqueId"],
            return_metadata=["distance"]
        )
        
        # Format the results
        results = []
        for obj in response.objects:
            # Truncate content for display
            content = obj.properties.get("text", "")
            if content and len(content) > 300:
                content = content[:300] + "..."
            
            # Format the result
            # Get tags as a string and convert to list if needed
            tags_str = obj.properties.get("tags", "")
            tags_list = [tag.strip() for tag in tags_str.split(",")] if tags_str else []
            
            result = {
                "uuid": obj.uuid,
                "title": obj.properties.get("title", "Untitled"),
                "type": obj.properties.get("type", "unknown"),
                "chapterNumber": obj.properties.get("chapterNumber"),
                "tags": tags_list,
                "source": obj.properties.get("source", ""),
                "uniqueId": obj.properties.get("uniqueId", ""),
                "content": content,
                "distance": obj.metadata.distance,
                "document_id": obj.properties.get("document_id", ""),
                "chunk_index": obj.properties.get("chunk_index", 0)
            }
            results.append(result)
        
        # Group results by document if requested
        if group_by_document:
            grouped_results = group_results_by_document(results)
            return grouped_results[:limit]  # Return only the requested number of documents
        
        return results
    
    finally:
        client.close()

def filtered_search(
    query: str, 
    doc_type: Optional[str] = None, 
    chapter_number: Optional[int] = None,
    tag: Optional[str] = None,
    limit: int = 5, 
    collection_name: str = "AdaptiveSchools",
    group_by_document: bool = False
) -> List[Dict[str, Any]]:
    """Perform a filtered semantic search on the AdaptiveSchools collection."""
    client = get_weaviate_client()
    
    try:
        # Get the collection
        collection = client.collections.get(collection_name)
        
        # Build the filter
        filters = []
        
        if doc_type:
            filters.append({
                "path": ["type"],
                "operator": "Equal",
                "valueText": doc_type
            })
        
        if chapter_number is not None:
            filters.append({
                "path": ["chapterNumber"],
                "operator": "Equal",
                "valueInt": chapter_number
            })
        
        if tag:
            # For a string property, use Contains operator instead of ContainsAny
            filters.append({
                "path": ["tags"],
                "operator": "ContainsRegex",
                "valueText": f"(^|,\\s*){tag}(\\s*,|$)"  # Match tag as a whole word in the comma-separated list
            })
        
        # Combine filters if there are multiple
        if len(filters) > 1:
            combined_filter = {
                "operator": "And",
                "operands": filters
            }
        elif len(filters) == 1:
            combined_filter = filters[0]
        else:
            combined_filter = None
        
        # Perform the search
        response = collection.query.near_text(
            query=query,
            filters=combined_filter,
            limit=limit if not group_by_document else 20,  # Get more results if grouping
            return_properties=["text", "chunk_index", "document_id", "title", "type", "chapterNumber", "tags", "source", "uniqueId"],
            return_metadata=["distance"]
        )
        
        # Format the results
        results = []
        for obj in response.objects:
            # Truncate content for display
            content = obj.properties.get("text", "")
            if content and len(content) > 300:
                content = content[:300] + "..."
            
            # Format the result
            # Get tags as a string and convert to list if needed
            tags_str = obj.properties.get("tags", "")
            tags_list = [tag.strip() for tag in tags_str.split(",")] if tags_str else []
            
            result = {
                "uuid": obj.uuid,
                "title": obj.properties.get("title", "Untitled"),
                "type": obj.properties.get("type", "unknown"),
                "chapterNumber": obj.properties.get("chapterNumber"),
                "tags": tags_list,
                "source": obj.properties.get("source", ""),
                "uniqueId": obj.properties.get("uniqueId", ""),
                "content": content,
                "distance": obj.metadata.distance,
                "document_id": obj.properties.get("document_id", ""),
                "chunk_index": obj.properties.get("chunk_index", 0)
            }
            results.append(result)
        
        # Group results by document if requested
        if group_by_document:
            grouped_results = group_results_by_document(results)
            return grouped_results[:limit]  # Return only the requested number of documents
        
        return results
    
    finally:
        client.close()

def group_results_by_document(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group search results by document_id, keeping only the best chunk for each document."""
    # Group results by document_id
    grouped = defaultdict(list)
    for result in results:
        doc_id = result["document_id"]
        if doc_id:  # Only group if document_id is present
            grouped[doc_id].append(result)
    
    # For each document, keep only the best chunk (lowest distance)
    best_chunks = []
    for doc_id, chunks in grouped.items():
        # Sort chunks by distance (ascending)
        sorted_chunks = sorted(chunks, key=lambda x: x["distance"])
        # Take the best chunk
        best_chunk = sorted_chunks[0]
        # Add chunk count information
        best_chunk["total_chunks"] = len(chunks)
        best_chunks.append(best_chunk)
    
    # Sort the best chunks by distance
    best_chunks.sort(key=lambda x: x["distance"])
    
    return best_chunks

def list_tags(collection_name: str = "AdaptiveSchools") -> List[str]:
    """List all unique tags in the AdaptiveSchools collection."""
    client = get_weaviate_client()
    
    try:
        # Get the collection
        collection = client.collections.get(collection_name)
        
        # Query for all objects to get their tags
        response = collection.query.fetch_objects(
            limit=100,  # Adjust as needed
            return_properties=["tags"]
        )
        
        # Extract and deduplicate tags
        all_tags = set()
        for obj in response.objects:
            tags_str = obj.properties.get("tags", "")
            if tags_str:
                # Split the comma-separated string into individual tags
                tags_list = [tag.strip() for tag in tags_str.split(",")]
                all_tags.update(tags_list)
        
        return sorted(list(all_tags))
    
    finally:
        client.close()

def display_results(results: List[Dict[str, Any]], show_chunks: bool = False) -> None:
    """Display search results in a readable format."""
    if not results:
        print("No results found.")
        return
    
    print(f"\nFound {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Title: {result['title']}")
        print(f"  Type: {result['type']}")
        print(f"  Source: {result['source']}")
        print(f"  ID: {result['uniqueId']}")
        
        if result['chapterNumber'] is not None:
            print(f"  Chapter: {result['chapterNumber']}")
        
        print(f"  Tags: {', '.join(result['tags'])}")
        print(f"  Distance: {result['distance']:.4f}")
        
        # Show chunk information if available
        if "chunk_index" in result:
            print(f"  Chunk: {result['chunk_index']}")
        
        if "total_chunks" in result:
            print(f"  Total Chunks in Document: {result['total_chunks']}")
        
        print(f"  Content Preview: {result['content']}")
        print()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Query the AdaptiveSchools collection in Weaviate.'
    )
    
    parser.add_argument('--query', type=str, required=True,
                        help='The search query')
    
    parser.add_argument('--limit', type=int, default=5,
                        help='Maximum number of results to return')
    
    parser.add_argument('--type', type=str, choices=['chapter', 'appendix', 'references', 'index'],
                        help='Filter by document type')
    
    parser.add_argument('--chapter', type=int,
                        help='Filter by chapter number')
    
    parser.add_argument('--tag', type=str,
                        help='Filter by tag')
    
    parser.add_argument('--list-tags', action='store_true',
                        help='List all available tags')
    
    parser.add_argument('--group', action='store_true',
                        help='Group results by document (show only the best chunk for each document)')
    
    parser.add_argument('--show-chunks', action='store_true',
                        help='Show detailed chunk information in results')
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_arguments()
    
    try:
        # List tags if requested
        if args.list_tags:
            tags = list_tags()
            print("\nAvailable tags:")
            for tag in tags:
                print(f"  - {tag}")
            print()
            
            # If only listing tags, exit
            if not args.query:
                return
        
        # Perform the search
        if args.type or args.chapter is not None or args.tag:
            # Filtered search
            results = filtered_search(
                query=args.query,
                doc_type=args.type,
                chapter_number=args.chapter,
                tag=args.tag,
                limit=args.limit,
                group_by_document=args.group
            )
        else:
            # Simple semantic search
            results = semantic_search(
                query=args.query,
                limit=args.limit,
                group_by_document=args.group
            )
        
        # Display the results
        display_results(results, show_chunks=args.show_chunks)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
