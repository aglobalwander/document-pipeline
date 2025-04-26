# Weaviate Layer Documentation

This document provides an overview and usage guide for the modular Weaviate v4 integration layer within the document processing pipeline.

## Overview

The `weaviate_layer` is designed to provide a clean, modular interface for interacting with Weaviate. It encapsulates Weaviate-specific logic, making the main document pipeline independent of the Weaviate client implementation details.

The key modules are:

*   `config.py`: Handles loading configuration settings for Weaviate and OpenAI.
*   `client.py`: Provides a helper function to connect to Weaviate with retry logic.
*   `schema.py`: Defines the declarative schema for Weaviate collections using Pydantic dataclasses.
*   `collections.py`: Contains utilities for ensuring collections exist based on the defined schema.
*   `manage_collections.py`: Provides high-level functions for common collection operations (create, list, get, drop, ingest).

## Configuration

Weaviate and OpenAI settings are loaded using the "golden path" logic implemented in `weaviate_layer/config.py`. The priority for loading settings is:

1.  Real environment variables.
2.  Settings from a YAML file specified by the `PIPELINE_CONFIG` environment variable (only fills in keys not already set by environment variables).
3.  Settings from the `.env` file.
4.  Default values defined in the `Settings` class.

This approach allows for flexible configuration, prioritizing environment variables for deployment while providing options for local development and scenario-specific overrides via YAML.

## Client Connection

The `weaviate_layer.client.get_weaviate_client()` function is the primary way to obtain a connected Weaviate client instance. It automatically attempts to connect to a cloud instance if `WEAVIATE_URL` and `WEAVIATE_API_KEY` are set in the environment or configuration, falling back to a local connection if cloud connection fails or is not configured. The function includes retry logic using Tenacity to handle transient connection issues.

```python
from weaviate_layer.client import get_weaviate_client

# Get a connected Weaviate client
client = get_weaviate_client()

# Use the client
try:
    # Perform Weaviate operations
    pass
finally:
    # Ensure the client is closed when done
    if client:
        client.close()
```

## Collection Management CLI

The `weaviate_layer` functionality is exposed through the Typer CLI application, accessible via `python -m cli.weav_cli weav ...`.

### `pipeline weav create <name>`

Creates a new Weaviate collection.

*   `name`: The name of the collection to create.
*   `--openai`: (Optional flag) Use the `text2vec-openai` vectorizer with the `text-embedding-3-large` model for the collection.

Example:
```bash
python -m cli.weav_cli weav create MyCollection
python -m cli.weav_cli weav create LiteratureTest --openai
```

### `pipeline weav list`

Lists all collections in the connected Weaviate instance.

*   `--simple`: (Optional flag, default: True) Return only collection names if set to True, otherwise return full configuration details.

Example:
```bash
python -m cli.weav_cli weav list
python -m cli.weav_cli weav list --simple False
```

### `pipeline weav show <name>`

Shows the full configuration for a single collection.

*   `name`: The name of the collection to show.

Example:
```bash
python -m cli.weav_cli weav show LiteratureTest
```

### `pipeline weav drop <name>`

Deletes one or more collections and all data within them. **Use with caution!**

*   `name`: The name(s) of the collection(s) to delete (can be a single name or a comma-separated list).
*   `--yes`, `-y`: (Required flag) Confirm the destructive drop operation.

Example:
```bash
python -m cli.weav_cli weav drop MyCollection --yes
python -m cli.weav_cli weav drop Collection1,Collection2 -y
```

### `pipeline weav ingest <name> <jsonl_path>`

Bulk-ingests objects from a JSON-Lines file into an existing collection.

*   `name`: The name of the collection to ingest data into.
*   `jsonl_path`: Path to the JSON-Lines file containing the data. Each line in the file should be a JSON object representing a data item.

Example:
```bash
python -m cli.weav_cli weav ingest LiteratureTest ./data/sample_literature.jsonl
```

## Data Ingestion

The `weaviate_layer.manage_collections.ingest_rows` function is used for efficient bulk data ingestion. It utilizes Weaviate's gRPC-backed batch import mechanism with automatic flushing. Data should be provided as an iterable of dictionaries, where each dictionary represents an object to be added to the collection.

## Schema Definition

Collection schemas are defined declaratively using Pydantic dataclasses in `weaviate_layer/schema.py`. This approach keeps schema definitions separate from the code that interacts with Weaviate, making them easier to manage and understand.

## Testing (Planned)

Integration tests for the `weaviate_layer` are planned to ensure the core functionality (client connection, collection management, data ingestion) works correctly against a live Weaviate instance. These tests will likely involve spinning up a local Weaviate container using Docker Compose.

## CI Setup (Planned)

A GitHub Actions workflow is planned to automate the testing of the Weaviate layer. This workflow will include steps to set up a Weaviate service, install dependencies, and run the integration tests.

## Key Concepts and Best Practices

*   **Weaviate v4 Collection API:** The layer utilizes the stable v4 Python client's `client.collections` API for managing collections.
*   **Declarative Schema:** Defining schemas using Python dataclasses provides a clear and versionable way to manage your Weaviate schema.
*   **Batch Import:** Using the batch API for data ingestion is crucial for performance.
*   **Vectorizer Configuration:** Vectorizer settings, such as the OpenAI model, are configured declaratively within the schema definition.
*   **Error Handling:** Weaviate-specific errors are caught and potentially re-raised to provide informative feedback.
*   **Dependency Management:** Poetry is used for managing Python dependencies, including pinning the `weaviate-client` version.

This documentation provides a solid foundation for understanding and using the Weaviate layer.