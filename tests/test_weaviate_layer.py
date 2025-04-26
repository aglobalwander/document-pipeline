import pytest
import time
import uuid
from typing import Any, Dict, List

# Import modules from the weaviate_layer
from weaviate_layer.client import get_weaviate_client
from weaviate_layer.collections import ensure_collections_exist
from weaviate_layer.manage_collections import ingest_rows, list_all, get_config, drop
from weaviate.exceptions import WeaviateBaseError # Import the correct base exception

# Import the DocumentPipeline
from doc_processing.document_pipeline import DocumentPipeline

# Define collection names based on existing collections
KNOWLEDGE_ITEM_COLLECTION = "KnowledgeItem"
KNOWLEDGE_MAIN_COLLECTION = "KnowledgeMain"

# Pytest fixture for the Weaviate client
@pytest.fixture(scope="module")
@pytest.mark.integration
def weaviate_client():
    """Fixture to provide a Weaviate client instance for integration tests."""
    client = None
    try:
        # Use the get_weaviate_client from the weaviate_layer
        client = get_weaviate_client()
        # Optional: Add a check to ensure the client is connected before yielding
        # In v4, list_all() is a good lightweight check
        client.collections.list_all()
        print("\nWeaviate client fixture created and connected.")
        yield client
    except Exception as e:
        pytest.fail(f"Failed to connect to Weaviate: {e}")
    finally:
        if client:
            client.close()
            print("\nWeaviate client fixture closed.")

# Sample data for testing ingestion
SAMPLE_KNOWLEDGE_ITEM_DATA = [
    {
        "title": "Test Document 1",
        "body": "This is the body of test document 1. It contains some information about testing.",
        "chapter": "Introduction",
        "author": "Test Author",
        "year": 2023,
        "categories": ["testing", "development"],
        "type": "article",
        "source": "Test Source",
        "url": "http://example.com/doc1",
        "format": "text",
        "language": "en",
        "summary": "Summary of test document 1.",
        "created_at": int(time.time()),
        "chunk_index": 0, # Example value, might not be present on actual main docs
    },
    {
        "title": "Test Document 2",
        "body": "This is the body of test document 2. It discusses integration testing strategies.",
        "chapter": "Testing Strategies",
        "author": "Another Author",
        "year": 2024,
        "categories": ["testing", "strategies"],
        "type": "report",
        "source": "Another Source",
        "url": "http://example.com/doc2",
        "format": "pdf",
        "language": "en",
        "summary": "Summary of test document 2.",
        "created_at": int(time.time()),
        "chunk_index": 0, # Example value
    },
]

SAMPLE_KNOWLEDGE_MAIN_DATA = [
    {
        "text": "This is the first chunk of test document 1.",
        "filename": "test_doc_1.txt",
        "tags": ["chunk", "doc1"],
        "chunk_index": 0,
        "document_id": str(uuid.uuid4()), # Placeholder, should ideally link to a KnowledgeItem UUID
    },
    {
        "text": "This is the second chunk of test document 1.",
        "filename": "test_doc_1.txt",
        "tags": ["chunk", "doc1"],
        "chunk_index": 1,
        "document_id": str(uuid.uuid4()), # Placeholder
    },
    {
        "text": "This is the first chunk of test document 2.",
        "filename": "test_doc_2.pdf",
        "tags": ["chunk", "doc2"],
        "chunk_index": 0,
        "document_id": str(uuid.uuid4()), # Placeholder
    },
]


# Test Cases
@pytest.mark.integration
def test_client_connection(weaviate_client):
    """Test that the Weaviate client fixture provides a connected client."""
    assert weaviate_client is not None
    # A call was already made in the fixture to check connection,
    # but we can add another simple one here if needed.
    try:
        weaviate_client.collections.list_all()
    except Exception as e:
        pytest.fail(f"Client is not functional after connection: {e}")


@pytest.mark.integration
def test_ensure_collections_exist():
    """Test that ensure_collections_exist runs without error for existing collections."""
    try:
        ensure_collections_exist()
    except Exception as e:
        pytest.fail(f"ensure_collections_exist failed: {e}")

@pytest.mark.integration
def test_ingest_data_knowledge_item(weaviate_client):
    """Test data ingestion into the KnowledgeItem collection."""
    try:
        # Generate unique UUIDs for the test data
        data_with_uuids = []
        for item in SAMPLE_KNOWLEDGE_ITEM_DATA:
            item_with_uuid = item.copy()
            item_with_uuid['id'] = str(uuid.uuid4()) # Add a unique ID for each document
            data_with_uuids.append(item_with_uuid)

        ingest_rows(KNOWLEDGE_ITEM_COLLECTION, data_with_uuids, uuid_from='id')

        # Optional: Verify ingestion by counting objects (requires a query)
        # collection = weaviate_client.collections.get(KNOWLEDGE_ITEM_COLLECTION)
        # count_response = collection.aggregate.over_all(total_count=True)
        # assert count_response.total_count >= len(data_with_uuids) # Check if at least the number of ingested objects exist

    except WeaviateBaseError as e:
        pytest.fail(f"Data ingestion into {KNOWLEDGE_ITEM_COLLECTION} failed: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during ingestion: {e}")


@pytest.mark.integration
def test_ingest_data_knowledge_main(weaviate_client):
    """Test data ingestion into the KnowledgeMain collection."""
    try:
        # Generate unique UUIDs for the test data and link to dummy document_ids
        data_with_uuids = []
        for chunk in SAMPLE_KNOWLEDGE_MAIN_DATA:
            chunk_with_uuid = chunk.copy()
            chunk_with_uuid['uuid'] = str(uuid.uuid4()) # Add a unique ID for each chunk
            # Ensure document_id is a valid UUID string if the schema expects it
            if 'document_id' in chunk_with_uuid and not isinstance(chunk_with_uuid['document_id'], str):
                 chunk_with_uuid['document_id'] = str(chunk_with_uuid['document_id'])
            data_with_uuids.append(chunk_with_uuid)


        # Note: The ingest_rows function expects 'rows' to be an iterable of dicts
        # and uses generate_uuid5 if uuid_from is None. If uuid_from is provided,
        # it expects the UUID to be in the row dict under that key.
        # We are generating UUIDs manually above and passing uuid_from=None,
        # so generate_uuid5 will be used based on the row content.
        # If you need to use the generated 'uuid' key, you would pass uuid_from='uuid'.
        # Let's stick to generate_uuid5 for simplicity in this test.
        ingest_rows(KNOWLEDGE_MAIN_COLLECTION, SAMPLE_KNOWLEDGE_MAIN_DATA, uuid_from=None)


        # Optional: Verify ingestion by counting objects (requires a query)
        # collection = weaviate_client.collections.get(KNOWLEDGE_MAIN_COLLECTION)
        # count_response = collection.aggregate.over_all(total_count=True)
        # assert count_response.total_count >= len(SAMPLE_KNOWLEDGE_MAIN_DATA)

    except WeaviateBaseError as e:
        pytest.fail(f"Data ingestion into {KNOWLEDGE_MAIN_COLLECTION} failed: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during ingestion: {e}")


@pytest.mark.integration
def test_query_similar_documents(weaviate_client):
    """Test querying similar documents from KnowledgeItem."""
    # Note: This test requires data to be present in the collection.
    # Running test_ingest_data_knowledge_item before this test is recommended.
    pipeline = DocumentPipeline(weaviate_client=weaviate_client)
    query_text = "testing strategies"
    try:
        results = pipeline.query_similar_documents(query_text, limit=2)
        assert isinstance(results, list)
        # Assert that results are returned (if data was ingested)
        # assert len(results) > 0 # Uncomment if you ensure data is present before this test
        if results:
             # Assert that returned objects have expected properties
             first_result_properties = results[0].get('properties', {})
             assert 'title' in first_result_properties
             assert 'body' in first_result_properties
             assert 'source' in first_result_properties
             # Add more assertions for other expected properties

    except WeaviateBaseError as e:
        pytest.fail(f"Querying {KNOWLEDGE_ITEM_COLLECTION} failed: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during querying: {e}")


@pytest.mark.integration
def test_query_similar_chunks(weaviate_client):
    """Test querying similar chunks from KnowledgeMain."""
    # Note: This test requires data to be present in the collection.
    # Running test_ingest_data_knowledge_main before this test is recommended.
    pipeline = DocumentPipeline(weaviate_client=weaviate_client)
    query_text = "first chunk"
    try:
        results = pipeline.query_similar_chunks(query_text, limit=2)
        assert isinstance(results, list)
        # Assert that results are returned (if data was ingested)
        # assert len(results) > 0 # Uncomment if you ensure data is present before this test
        if results:
             # Assert that returned objects have expected properties
             first_result_properties = results[0].get('properties', {})
             assert 'text' in first_result_properties
             assert 'chunk_index' in first_result_properties
             # Add more assertions for other expected properties

    except WeaviateBaseError as e:
        pytest.fail(f"Querying {KNOWLEDGE_MAIN_COLLECTION} failed: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during querying: {e}")

@pytest.mark.integration
def test_get_document_context(weaviate_client):
    """Test retrieving document context from KnowledgeMain."""
    # Note: This test requires data to be present in the collection.
    # Running test_ingest_data_knowledge_main before this test is recommended.
    pipeline = DocumentPipeline(weaviate_client=weaviate_client)
    query_text = "second chunk"
    try:
        context = pipeline.get_document_context(query_text, context_chunks=1)
        assert isinstance(context, str)
        # Assert that the context is not empty (if data was ingested)
        # assert len(context) > 0 # Uncomment if you ensure data is present before this test
        # Optional: Add more specific assertions about the content of the context string

    except WeaviateBaseError as e:
        pytest.fail(f"Getting document context failed: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during getting document context: {e}")

# Note: To run these tests, ensure a Weaviate instance is running and accessible,
# and the necessary environment variables (WEAVIATE_URL, WEAVIATE_API_KEY, OPENAI_API_KEY) are set.
# Use 'pytest -m integration' to run only these integration tests.