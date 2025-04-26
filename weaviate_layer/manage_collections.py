"""High-level helpers for common collection operations."""
from __future__ import annotations
from typing import Iterable, Mapping, Any
from .client import get_weaviate_client
from weaviate.classes.config import Property, DataType, Configure
from weaviate.exceptions import WeaviateBaseError # Corrected import
from weaviate.util import generate_uuid5

# ---------- CREATE ----------
def create_basic(name: str) -> None:
    """
    Create an empty collection with default settings.
    Mirrors the one-liner in the docs. ⚠️ Capitalise names per GraphQL rules.
    """
    client = get_weaviate_client()
    try:
        client.collections.create(name)     # v4 shortcut
    finally:
        client.close()

def create_text2vec_openai(
    name: str,
    properties: list[str] = ("title", "body"),
    model: str = "text-embedding-3-large",
) -> None:
    """
    Create a text collection with OpenAI 3-series embeddings.
    """
    client = get_weaviate_client()
    try:
        client.collections.create(
            name,
            vectorizer_config=Configure.Vectorizer.text2vec_openai(model=model),
            properties=[Property(p, DataType.TEXT) for p in properties],
        )
    finally:
        client.close()

# ---------- LIST / GET ----------
def list_all(simple: bool = False) -> dict[str, Any]:
    """Return every collection definition."""
    client = get_weaviate_client()
    try:
        return client.collections.list_all(simple=simple)
    finally:
        client.close()

def get_config(name: str) -> dict[str, Any]:
    """Return the config of a single collection."""
    client = get_weaviate_client()
    try:
        coll = client.collections.get(name)
        return coll.config.get()
    finally:
        client.close()

# ---------- DELETE ----------
def drop(names: str | list[str], *, yes_i_know: bool = False) -> None:
    """
    Delete one or many collections (and all data inside).
    Pass yes_i_know=True to make it explicit in your code that you understand the risk.
    """
    if not yes_i_know:
        raise ValueError("Set yes_i_know=True to confirm destructive drop.")
    client = get_weaviate_client()
    try:
        client.collections.delete(names)
    finally:
        client.close()

# ---------- INGEST ----------
def ingest_rows(
    collection_name: str,
    rows: Iterable[Mapping[str, Any]],
    uuid_from: str | None = None,
    max_errors: int = 10,
) -> None:
    """
    Batch-insert iterable rows (list of dicts) into an existing collection.
    Uses gRPC batch import by default (v1.23+). Raises if too many errors.
    """
    client = get_weaviate_client()
    try:
        collection = client.collections.get(collection_name)
        with collection.batch.dynamic() as batch:           # gRPC batch pattern
            for row in rows:
                uid = generate_uuid5(row) if uuid_from is None else row[uuid_from]
                batch.add_object(properties=row, uuid=uid)
                if batch.number_errors > max_errors:
                    raise WeaviateBaseError( # Corrected exception class
                        f"Aborting import – {batch.number_errors} errors so far"
                    )
    finally:
        client.close()