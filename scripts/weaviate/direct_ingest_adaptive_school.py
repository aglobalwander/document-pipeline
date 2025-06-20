#!/usr/bin/env python3
"""
Script to directly ingest Adaptive School documents into Weaviate with hybrid tag generation.

This script:
1. Processes all markdown files in the adaptive_school_sourcebook directory
2. Generates tags using a hybrid approach (GPT-4.1 + keyword extraction)
3. Uses LangChain's text splitter to chunk documents
4. Directly uploads the chunks to Weaviate without using the document pipeline
"""

import os
import sys
import time
import uuid
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import spacy
from collections import Counter
from openai import OpenAI
import tiktoken
from langchain.text_splitter import TokenTextSplitter

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from weaviate_layer.client import get_weaviate_client
from weaviate_layer.collections import ensure_collections_exist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("direct_ingest_adaptive_school.log")
    ]
)
logger = logging.getLogger(__name__)

# Define domain-specific tags relevant to "The Adaptive School"
DOMAIN_TAGS = [
    "professional community", "collaboration", "leadership", 
    "facilitation", "group dynamics", "conflict resolution",
    "educational change", "school improvement", "coaching",
    "professional development", "systems thinking", "adaptive schools",
    "norms of collaboration", "dialogue", "discussion", "decision making",
    "consensus", "cognitive coaching", "seven norms", "facilitation strategies"
]

def get_openai_client():
    """Get configured OpenAI client."""
    # Ensure API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return OpenAI(api_key=api_key)

def generate_tags_with_gpt4(content: str, title: str) -> List[str]:
    """Generate tags using GPT-4.1."""
    client = get_openai_client()
    
    # Create a system prompt that explains the task
    system_prompt = """
    You are an expert in educational leadership and professional development.
    Your task is to analyze text from "The Adaptive School" book and generate relevant tags.
    Focus on key concepts, methodologies, frameworks, and themes in the text.
    """
    
    # Create a user prompt with the content
    user_prompt = f"""
    Based on the following content from "{title}", generate 5-10 relevant tags or keywords.
    These tags should represent key concepts, methodologies, or themes in the text.
    Return ONLY the tags as a comma-separated list, with no additional text or explanation.
    
    CONTENT:
    {content[:6000]}  # GPT-4.1 has a larger context window
    """
    
    # Make the API call
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",  # Use GPT-4.1 model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=150    # Limit response length
        )
        
        # Extract and clean the tags
        tags_text = response.choices[0].message.content.strip()
        tags = [tag.strip() for tag in tags_text.split(',')]
        
        logger.info(f"Generated {len(tags)} tags with GPT-4.1 for '{title}'")
        return tags
    except Exception as e:
        logger.error(f"Error generating tags with GPT-4.1: {e}")
        return []

def extract_keywords(content: str, max_keywords: int = 15) -> List[str]:
    """Extract keywords using NLP techniques."""
    try:
        # Load spaCy model
        nlp = spacy.load("en_core_web_sm")
        
        # Process the text (limit length for performance)
        doc = nlp(content[:20000])
        
        # Extract noun phrases and filter out stopwords
        keywords = []
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Limit to phrases with 3 or fewer words
                if not chunk.root.is_stop and not all(token.is_stop for token in chunk):
                    keywords.append(chunk.text.lower())
        
        # Count frequencies and get top keywords
        keyword_freq = Counter(keywords)
        top_keywords = [kw for kw, _ in keyword_freq.most_common(max_keywords)]
        
        logger.info(f"Extracted {len(top_keywords)} keywords with spaCy")
        return top_keywords
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        return []

def add_domain_tags(content: str, existing_tags: List[str]) -> List[str]:
    """Add domain-specific tags if they appear in the content."""
    additional_tags = []
    content_lower = content.lower()
    
    for tag in DOMAIN_TAGS:
        if tag.lower() in content_lower:
            additional_tags.append(tag)
    
    logger.info(f"Added {len(additional_tags)} domain-specific tags")
    return list(set(existing_tags + additional_tags))

def generate_hybrid_tags(content: str, title: str) -> List[str]:
    """Generate tags using hybrid approach with GPT-4.1."""
    # Get GPT-4.1 generated tags
    llm_tags = generate_tags_with_gpt4(content, title)
    
    # Get keyword-based tags
    keyword_tags = extract_keywords(content)
    
    # Add domain-specific tags
    combined_tags = llm_tags + keyword_tags
    final_tags = add_domain_tags(content, combined_tags)
    
    # Deduplicate and normalize
    normalized_tags = []
    seen_lowercase = set()
    
    for tag in final_tags:
        tag_lower = tag.lower()
        if tag_lower not in seen_lowercase:
            seen_lowercase.add(tag_lower)
            # Use the original case from the first occurrence
            normalized_tags.append(tag)
    
    # Limit to a reasonable number
    result = normalized_tags[:20]
    logger.info(f"Final tag count after hybrid generation: {len(result)}")
    return result

def process_adaptive_school_document(file_path: Path) -> Dict[str, Any]:
    """Process a single document from The Adaptive School."""
    # Read the document
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract metadata from filename
    filename = file_path.name
    file_stem = file_path.stem
    
    # Initialize chapter_num to None by default
    chapter_num = None
    
    # Determine document type and metadata
    if filename.startswith("chapter_"):
        doc_type = "chapter"
        parts = file_stem.split("_")
        if len(parts) > 1 and parts[1].isdigit():
            chapter_num = int(parts[1])
        title = " ".join(parts[2:]).replace("_", " ").title() if len(parts) > 2 else file_stem
    elif filename.startswith("appendix_"):
        doc_type = "appendix"
        parts = file_stem.split("_")
        appendix_letter = parts[1] if len(parts) > 1 else ""
        title = f"Appendix {appendix_letter}: " + " ".join(parts[2:]).replace("_", " ").title() if len(parts) > 2 else file_stem
    elif filename == "references.md":
        doc_type = "references"
        title = "References"
    elif filename == "index.md":
        doc_type = "index"
        title = "Index"
    else:
        doc_type = "other"
        title = file_stem.replace("_", " ").title()
    
    # Generate tags
    tags = generate_hybrid_tags(content, title)
    
    # Create document object
    document = {
        'title': title,
        'content': content,
        'type': doc_type,
        'chapterNumber': chapter_num,
        'tags': tags,
        'source': "The Adaptive School - Garmston & Wellman",
        'uniqueId': file_stem,
        'document_id': str(uuid.uuid4())  # Generate a unique ID for the document
    }
    
    return document

def chunk_document(document: Dict[str, Any], chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
    """Split a document into chunks using LangChain's text splitter."""
    # Create a text splitter
    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    # Split the content into chunks
    content = document['content']
    chunk_texts = text_splitter.split_text(content)
    
    # Create chunk objects
    chunks = []
    for i, chunk_text in enumerate(chunk_texts):
        # Convert tags list to a comma-separated string
        tags_string = ", ".join(document['tags']) if document['tags'] else ""
        
        # Create a chunk object with document metadata
        chunk = {
            'text': chunk_text,
            'chunk_index': i,
            'document_id': document['document_id'],
            'title': document['title'],
            'type': document['type'],
            'tags': tags_string,
            'source': document['source'],
            'uniqueId': document['uniqueId']
        }
        
        # Add chapterNumber if it exists and is not None
        if document.get('chapterNumber') is not None:
            chunk['chapterNumber'] = document['chapterNumber']
        
        chunks.append(chunk)
    
    logger.info(f"Split document '{document['title']}' into {len(chunks)} chunks")
    return chunks

def upload_chunks_to_weaviate(chunks: List[Dict[str, Any]], client, collection_name: str) -> int:
    """Upload chunks to Weaviate."""
    try:
        # Get the collection
        collection = client.collections.get(collection_name)
        
        # Upload chunks
        uploaded_count = 0
        with collection.batch.dynamic() as batch:
            for chunk in chunks:
                # Generate a UUID for the chunk
                chunk_uuid = str(uuid.uuid4())
                
                # Add the chunk to the batch
                batch.add_object(properties=chunk, uuid=chunk_uuid)
                uploaded_count += 1
        
        logger.info(f"Successfully uploaded {uploaded_count} chunks to Weaviate collection '{collection_name}'")
        return uploaded_count
    except Exception as e:
        logger.error(f"Error uploading chunks to Weaviate: {e}")
        return 0

def process_and_ingest_all_documents(args):
    """Process all Adaptive School documents and ingest into Weaviate."""
    # Verify Weaviate connection
    client = get_weaviate_client()
    if not client:
        logger.error("Failed to connect to Weaviate")
        return
    
    # Ensure the AdaptiveSchools collection exists
    ensure_collections_exist(collection_name="AdaptiveSchools")
    
    # Directory containing the split documents
    input_dir = Path(args.input_dir)
    
    # Statistics
    stats = {
        "processed_count": 0,
        "error_count": 0,
        "chapter_count": 0,
        "appendix_count": 0,
        "other_count": 0,
        "total_tags": 0,
        "total_chunks": 0,
        "doc_types": {}
    }
    
    # Process each file
    for file_path in input_dir.glob("*.md"):
        logger.info(f"Processing {file_path.name}...")
        
        try:
            # Process the document to extract metadata and tags
            document = process_adaptive_school_document(file_path)
            
            # Update statistics
            doc_type = document['type']
            stats["doc_types"][doc_type] = stats["doc_types"].get(doc_type, 0) + 1
            
            if doc_type == "chapter":
                stats["chapter_count"] += 1
            elif doc_type == "appendix":
                stats["appendix_count"] += 1
            else:
                stats["other_count"] += 1
            
            stats["total_tags"] += len(document['tags'])
            
            # Log the tags
            logger.info(f"Generated tags for {file_path.name}: {', '.join(document['tags'])}")
            
            # Split the document into chunks
            chunks = chunk_document(document, args.chunk_size, args.chunk_overlap)
            
            # Upload the chunks to Weaviate
            uploaded_count = upload_chunks_to_weaviate(chunks, client, "AdaptiveSchools")
            
            if uploaded_count > 0:
                stats["processed_count"] += 1
                stats["total_chunks"] += uploaded_count
                logger.info(f"Successfully processed {file_path.name}")
            else:
                stats["error_count"] += 1
                logger.error(f"Failed to upload chunks for {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            stats["error_count"] += 1
        
        # Add a small delay to avoid rate limiting with GPT-4.1
        if args.delay > 0:
            time.sleep(args.delay)
    
    # Print summary information
    print("\n" + "="*50)
    print("INGESTION SUMMARY")
    print("="*50)
    print(f"Total documents processed: {stats['processed_count']}")
    print(f"Documents with errors: {stats['error_count']}")
    print(f"Chapters: {stats['chapter_count']}")
    print(f"Appendices: {stats['appendix_count']}")
    print(f"Other documents: {stats['other_count']}")
    print(f"Total tags generated: {stats['total_tags']}")
    print(f"Average tags per document: {stats['total_tags'] / stats['processed_count'] if stats['processed_count'] > 0 else 0:.1f}")
    print(f"Total chunks created: {stats['total_chunks']}")
    print(f"Average chunks per document: {stats['total_chunks'] / stats['processed_count'] if stats['processed_count'] > 0 else 0:.1f}")
    print("\nDocument types:")
    for doc_type, count in stats["doc_types"].items():
        print(f"  - {doc_type}: {count}")
    print("="*50)
    
    logger.info(f"Completed processing {stats['processed_count']} documents")
    client.close()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Process and ingest Adaptive School documents into Weaviate with hybrid tag generation.'
    )
    
    parser.add_argument('--input_dir', type=str, 
                        default='data/output/markdown/adaptive_school_sourcebook',
                        help='Directory containing the split markdown files')
    
    parser.add_argument('--chunk_size', type=int, default=4000,
                        help='Chunk size for text splitting (default: 4000 tokens)')
    
    parser.add_argument('--chunk_overlap', type=int, default=200,
                        help='Chunk overlap for text splitting (default: 200 tokens)')
    
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between processing files in seconds')
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_arguments()
    
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    # Check if spaCy model is installed
    try:
        import spacy
        if not spacy.util.is_package("en_core_web_sm"):
            logger.error("spaCy model 'en_core_web_sm' not found. Please install it with: python -m spacy download en_core_web_sm")
            sys.exit(1)
    except ImportError:
        logger.error("spaCy not installed. Please install it with: pip install spacy")
        sys.exit(1)
    
    # Process and ingest documents
    process_and_ingest_all_documents(args)

if __name__ == "__main__":
    main()
