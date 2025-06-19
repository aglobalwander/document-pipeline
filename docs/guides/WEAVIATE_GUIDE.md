# Weaviate Integration Guide

This guide covers how to use Weaviate vector database with the pipeline-documents system for semantic search and document retrieval.

## Overview

Weaviate integration enables:
- **Vector search**: Find semantically similar documents
- **Hybrid search**: Combine keyword and vector search
- **Document chunking**: Automatic text splitting for better retrieval
- **Metadata filtering**: Search by document properties
- **Scalable storage**: Handle millions of documents

## Quick Start

### Basic Document Ingestion

```bash
# Ingest a single PDF to Weaviate
python scripts/run_pipeline.py --input_path document.pdf --pipeline_type weaviate

# Ingest entire directory
python scripts/run_pipeline.py --input_path data/pdfs --pipeline_type weaviate --recursive

# Specify collection name
python scripts/run_pipeline.py --input_path doc.pdf --pipeline_type weaviate --collection ResearchDocs
```

### Configuration

Set environment variables:
```bash
export WEAVIATE_URL="http://localhost:8080"  # or your Weaviate instance
export WEAVIATE_API_KEY="your-api-key"       # if using Weaviate Cloud
export OPENAI_API_KEY="your-openai-key"     # for embeddings
```

Or configure in code:
```python
config = {
    'weaviate_url': 'http://localhost:8080',
    'weaviate_api_key': 'your-key',
    'collection': 'Documents',
    'embedding_model': 'text-embedding-3-small'
}
```

## Collection Management

### Create Collections

```bash
# Create from predefined schemas
python -m cli.weav_cli weav create --media

# Create from YAML schema
python -m cli.weav_cli weav create CustomDocs --schema-file schemas/custom.yaml
```

### List and Inspect

```bash
# List all collections
python -m cli.weav_cli weav list

# Show collection details
python -m cli.weav_cli weav show Documents

# Drop collection
python -m cli.weav_cli weav drop Documents -y
```

## Schema Design

### Basic Document Schema

```yaml
# schemas/Documents.yaml
class_name: Documents
description: General document storage
properties:
  - name: title
    dataType: [text]
    description: Document title
  - name: content
    dataType: [text]
    description: Document content
  - name: source_path
    dataType: [text]
    description: Original file path
  - name: doc_type
    dataType: [text]
    description: Document type (pdf, docx, etc)
  - name: metadata
    dataType: [object]
    description: Additional metadata
```

### Creating Custom Schemas

```python
from weaviate_layer.schemas import create_schema

schema = {
    'class_name': 'ResearchPapers',
    'properties': [
        {'name': 'title', 'dataType': ['text']},
        {'name': 'abstract', 'dataType': ['text']},
        {'name': 'authors', 'dataType': ['text[]']},
        {'name': 'publication_date', 'dataType': ['date']},
        {'name': 'content', 'dataType': ['text']},
        {'name': 'citations', 'dataType': ['int']}
    ]
}

create_schema(schema)
```

## Document Processing Pipeline

### Standard Weaviate Pipeline

```python
from doc_processing.document_pipeline import DocumentPipeline

# Configure pipeline for Weaviate
config = {
    'chunking_strategy': 'semantic',
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'extract_metadata': True,
    'collection': 'Documents'
}

pipeline = DocumentPipeline(config)
pipeline.configure_weaviate_pipeline()

# Process document
result = pipeline.process_document('research_paper.pdf')
```

### Advanced Chunking Strategies

```python
# Semantic chunking (recommended)
config = {
    'chunking_strategy': 'semantic',
    'min_chunk_size': 500,
    'max_chunk_size': 1500,
    'similarity_threshold': 0.7
}

# Fixed-size chunking
config = {
    'chunking_strategy': 'fixed',
    'chunk_size': 1000,
    'chunk_overlap': 200
}

# Sentence-based chunking
config = {
    'chunking_strategy': 'sentence',
    'sentences_per_chunk': 5,
    'min_chunk_size': 100
}
```

## Querying Documents

### Basic Search

```python
from weaviate_layer import get_client

client = get_client()

# Vector search
results = client.query.get(
    'Documents',
    ['title', 'content', '_additional { distance }']
).with_near_text({
    'concepts': ['machine learning algorithms']
}).with_limit(10).do()

# Hybrid search (keyword + vector)
results = client.query.get(
    'Documents', 
    ['title', 'content']
).with_hybrid(
    query='neural networks',
    alpha=0.75  # 0=keyword only, 1=vector only
).do()
```

### Filtered Search

```python
# Search with metadata filters
results = client.query.get(
    'Documents',
    ['title', 'content']
).with_near_text({
    'concepts': ['data analysis']
}).with_where({
    'path': ['doc_type'],
    'operator': 'Equal',
    'valueText': 'pdf'
}).with_limit(5).do()
```

### Advanced Queries

```python
# Semantic search with multiple concepts
results = client.query.get(
    'Documents',
    ['title', 'content', '_additional { score distance }']
).with_near_text({
    'concepts': ['machine learning', 'deep learning'],
    'certainty': 0.7
}).with_limit(20).do()

# Get similar documents
results = client.query.get(
    'Documents',
    ['title', 'content']
).with_near_object({
    'id': 'document-uuid-here'
}).with_limit(5).do()
```

## Best Practices

### 1. Chunking Strategy
- Use semantic chunking for better context preservation
- Adjust chunk size based on your use case (smaller for Q&A, larger for summaries)
- Include overlap to maintain context across chunks

### 2. Metadata Design
- Store useful metadata for filtering (date, type, source, author)
- Use consistent naming conventions
- Index frequently queried fields

### 3. Collection Organization
- Separate collections by document type or use case
- Use meaningful collection names
- Document your schema design

### 4. Performance Optimization
```python
# Batch import for better performance
with client.batch as batch:
    batch.batch_size = 100
    
    for doc in documents:
        batch.add_data_object(
            data_object=doc,
            class_name='Documents'
        )
```

### 5. Error Handling
```python
try:
    result = pipeline.process_document(file_path)
except WeaviateException as e:
    logger.error(f"Weaviate error: {e}")
    # Handle connection issues, schema conflicts, etc.
```

## Monitoring and Maintenance

### Check Collection Health
```python
# Get collection statistics
info = client.query.aggregate('Documents').with_meta_count().do()
print(f"Total documents: {info['data']['Aggregate']['Documents'][0]['meta']['count']}")

# Check vector index status
schema = client.schema.get('Documents')
print(f"Vector index type: {schema['vectorIndexType']}")
```

### Backup and Recovery
```bash
# Export collection data
python -m cli.weav_cli export Documents --output backup.json

# Import from backup
python -m cli.weav_cli import Documents --input backup.json
```

## Common Issues

### Connection Errors
```python
# Test connection
from weaviate_layer import check_connection

if not check_connection():
    print("Cannot connect to Weaviate. Check URL and credentials.")
```

### Schema Conflicts
- Always check if collection exists before creating
- Use versioned collection names for schema changes
- Migrate data when updating schemas

### Performance Issues
- Enable vector caching for repeated queries
- Use batch operations for bulk imports
- Consider sharding for very large collections

## Integration Examples

### With FastAPI
```python
from fastapi import FastAPI
from weaviate_layer import get_client

app = FastAPI()
weaviate_client = get_client()

@app.post("/search")
async def search_documents(query: str, limit: int = 10):
    results = weaviate_client.query.get(
        'Documents',
        ['title', 'content', '_additional { distance }']
    ).with_near_text({
        'concepts': [query]
    }).with_limit(limit).do()
    
    return results['data']['Get']['Documents']
```

### With Streamlit
```python
import streamlit as st
from weaviate_layer import search_documents

st.title("Document Search")

query = st.text_input("Search query:")

if query:
    results = search_documents(query, collection='Documents')
    
    for result in results:
        st.write(f"**{result['title']}**")
        st.write(result['content'][:200] + "...")
        st.write("---")
```