from dataclasses import dataclass, field
from typing import List, Any, Dict
from weaviate.classes.config import Property, DataType, Configure, StopwordsPreset, Tokenization, VectorDistances, VectorFilterStrategy
from weaviate.classes.config import Reconfigure # Although not used in schema definition, good to have for potential updates

# Dataclass representing the schema for the 'KnowledgeItem' collection
@dataclass(frozen=True)
class KnowledgeItemSchema:
    name: str = "KnowledgeItem"
    description: str = "A unit of content in the knowledge base from literature, media, or notes"
    properties: List[Property] = field(default_factory=lambda: [
        Property(name="title", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="body", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="chapter", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="author", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="year", data_type=DataType.INT, index_filterable=True, index_searchable=False),
        Property(name="categories", data_type=DataType.TEXT_ARRAY, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="type", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="source", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="url", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="format", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="language", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="summary", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="embedding", data_type=DataType.BLOB, index_filterable=True, index_searchable=False), # Assuming this is for storing raw embedding if needed
        Property(name="created_at", data_type=DataType.DATE, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="chunk_index", data_type=DataType.NUMBER, index_filterable=True, index_range_filters=False, index_searchable=False), # Based on schema inspection
    ])
    # Define named vector for 'body' property
    vectorizer_config: List[Configure.NamedVectors] = field(default_factory=lambda: [
        Configure.NamedVectors.text2vec_openai(
            name="body_vector",
            source_properties=["body"],
            model={"model": "text-embedding-3-large", "vectorizeClassName": True}, # Match inspected config
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other collection-level configs based on inspection
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25=Configure.inverted_index.BM25(b=0.75, k1=1.2),
        stopwords=Configure.inverted_index.Stopwords(preset=StopwordsPreset.EN),
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128,
        key='_id',
        strategy='hash',
        function='murmur3'
    ))


# Dataclass representing the schema for the 'KnowledgeMain' collection (chunks)
@dataclass(frozen=True)
class KnowledgeMainSchema:
    name: str = "KnowledgeMain"
    description: str = "Main knowledge collection for chunked text data."
    properties: List[Property] = field(default_factory=lambda: [
        Property(name="text", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="filename", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="tags", data_type=DataType.TEXT_ARRAY, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="chunk_index", data_type=DataType.INT, index_filterable=True, index_range_filters=False, index_searchable=False),
    ])
    # Define named vector for 'text' property
    vectorizer_config: List[Configure.NamedVectors] = field(default_factory=lambda: [
        Configure.NamedVectors.text2vec_openai(
            name="text_vector",
            source_properties=["text"],
            model={"model": "text-embedding-3-large", "vectorizeClassName": True}, # Match inspected config
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other collection-level configs based on inspection
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25=Configure.inverted_index.BM25(b=0.75, k1=1.2),
        stopwords=Configure.inverted_index.Stopwords(preset=StopwordsPreset.EN),
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128,
        key='_id',
        strategy='hash',
        function='murmur3'
    ))

# List of all collection schemas defined in this file
COLLECTION_SCHEMAS = [KnowledgeItemSchema, KnowledgeMainSchema]

# Optional: Keep the LiteratureTestSchema commented out for reference if needed
# @dataclass(frozen=True)
# class LiteratureTestSchema:
#     name: str = "LiteratureTest"
#     properties = [
#         Property(name="title", data_type=DataType.TEXT),
#         Property(name="body", data_type=DataType.TEXT),
#         Property(name="tag", data_type=DataType.TEXT_ARRAY),
#     ]
#     vectorizer_config = Configure.Vectorizer.text2vec_openai(
#         model="text-embedding-3-large"
#     )