# Adaptive School Ingestion

This README explains how to ingest "The Adaptive School" documents into Weaviate using the hybrid tag generation approach.

## Prerequisites

Before running the ingestion script, ensure you have the following:

1. **Python Dependencies**:
   ```bash
   pip install openai spacy tiktoken weaviate-client
   python -m spacy download en_core_web_sm
   ```

2. **OpenAI API Key**:
   Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

3. **Weaviate Instance**:
   Ensure your Weaviate instance is running and properly configured in your environment variables or `.env` file.

4. **Split Documents**:
   The script expects the split markdown files to be in `data/output/markdown/adaptive_school_sourcebook/`.

## Running the Ingestion Script

To run the ingestion script with default settings:

```bash
python scripts/ingest_adaptive_school.py
```

### Command Line Options

The script supports the following command line options:

- `--input_dir`: Directory containing the split markdown files (default: `data/output/markdown/adaptive_school_sourcebook`)
- `--chunk_size`: Chunk size for text splitting (default: 800)
- `--chunk_overlap`: Chunk overlap for text splitting (default: 100)
- `--delay`: Delay between processing files in seconds (default: 1.0)

Example with custom settings:

```bash
python scripts/ingest_adaptive_school.py --chunk_size 1000 --chunk_overlap 200 --delay 2.0
```

## Verifying and Querying the Collection

After ingestion, you can use the following scripts to verify and query the collection:

### Verify Collection

To check if the AdaptiveSchools collection exists and view its properties:

```bash
python scripts/verify_adaptive_schools_collection.py
```

### Query Collection

To search for content in the collection:

```bash
python scripts/query_adaptive_schools.py --query "professional community" --limit 5
```

You can also filter by document type, chapter number, or tag:

```bash
python scripts/query_adaptive_schools.py --query "facilitation" --type chapter --chapter 8
```

To list all available tags:

```bash
python scripts/query_adaptive_schools.py --query "any" --list-tags
```

### Summarize Collection

To generate a summary report of the collection:

```bash
python scripts/summarize_adaptive_schools.py
```

This will display:
- Total number of documents
- Breakdown by document type
- Average content length
- Unique tags
- Top 20 most common tags

## Available Ingestion Scripts

### 1. Standard Pipeline Approach (`ingest_adaptive_school.py`)

The standard ingestion script attempts to use the document pipeline:

```bash
python scripts/ingest_adaptive_school.py --chunk_size 4000 --chunk_overlap 200
```

### 2. Direct Ingestion Approach (`direct_ingest_adaptive_school.py`) - RECOMMENDED

The direct ingestion script bypasses the document pipeline for more reliable results:

```bash
python scripts/direct_ingest_adaptive_school.py --chunk_size 4000 --chunk_overlap 200
```

This script performs the following steps:

1. **Processes each markdown file** in the specified directory
2. **Generates tags** using a hybrid approach:
   - GPT-4.1 for contextual understanding
   - spaCy for keyword extraction
   - Domain-specific tag matching
3. **Converts tags** from a list to a comma-separated string to match the Weaviate schema
4. **Chunks the documents** using LangChain's text splitter
5. **Directly uploads the chunks** to Weaviate with proper document metadata

## Monitoring Progress

The script logs its progress to both the console and a log file (`ingest_adaptive_school.log`). You can monitor the ingestion process by watching the log output.

## Collection Management

Before ingesting documents, you may need to delete the existing collection to apply schema changes:

```bash
python scripts/delete_adaptive_schools_collection.py
```

## Chunking Strategy

Both scripts use LangChain's text splitter to divide documents into smaller chunks:

1. **Chunk Size**: Default is 4000 tokens (configurable via `--chunk_size`), which is well below the 8192 token limit of the OpenAI embedding model
2. **Chunk Overlap**: Default is 200 tokens (configurable via `--chunk_overlap`), which helps maintain context between chunks
3. **Document Linking**: Each chunk maintains a reference to its parent document via the `document_id` field
4. **Chunk Indexing**: Each chunk has a `chunk_index` field indicating its position in the original document

This chunking approach allows for:
- Processing documents of any size
- More precise semantic search results
- Ability to reconstruct full documents when needed
- Better handling of token limits in embedding models

## Ingestion Results

The direct ingestion script successfully processed all 28 documents:
- 15 chapters
- 11 appendices
- 1 references section
- 1 index section

These were split into 110 chunks with an average of 3.9 chunks per document.

## Querying Chunked Documents

The `query_adaptive_schools.py` script has been updated to work with the chunked data model:

```bash
# Basic search
python scripts/query_adaptive_schools.py --query "professional community"

# Group results by document (show only the best chunk per document)
python scripts/query_adaptive_schools.py --query "facilitation" --group

# Show detailed chunk information
python scripts/query_adaptive_schools.py --query "conflict" --show-chunks
```

## Troubleshooting

If you encounter issues:

1. **Check the log file** for detailed error messages
2. **Verify your OpenAI API key** is correctly set
3. **Ensure Weaviate is running** and properly configured
4. **Check that spaCy and its model** are correctly installed
5. **Verify the schema** in `weaviate_layer/schemas/AdaptiveSchools.yaml` matches the data format
6. **Check chunk sizes** if you encounter token limit errors

### Common Errors

- **"invalid text property 'tags' on class 'AdaptiveSchools': not a string, but []interface {}"**: This error occurs if the schema expects a string for tags but receives an array. The current implementation converts the tags array to a comma-separated string to avoid this issue.
- **"This model's maximum context length is 8192 tokens"**: This error occurs if a document chunk exceeds the token limit of the embedding model. Reduce the `--chunk_size` parameter if you encounter this error.

## Cost Considerations

Using GPT-4.1 for tag generation will incur API costs. With approximately 27 documents (14 chapters, 11 appendices, references, and index), and assuming an average of 10,000 tokens per document for the input, the cost would be roughly:

- 27 documents × 10,000 tokens × $0.01/1K tokens = ~$2.70
