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
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other collection-level configs based on inspection
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25_b=0.75,                 # Pass 'b' parameter directly
        bm25_k1=1.2,                 # Pass 'k1' parameter directly
        stopwords_preset=StopwordsPreset.EN, # Pass preset directly
        # stopwords_additions=None,  # Optional: Add if needed
        # stopwords_removals=None,   # Optional: Add if needed
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128
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
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other collection-level configs based on inspection
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25_b=0.75,                 # Pass 'b' parameter directly
        bm25_k1=1.2,                 # Pass 'k1' parameter directly
        stopwords_preset=StopwordsPreset.EN, # Pass preset directly
        # stopwords_additions=None,  # Optional: Add if needed
        # stopwords_removals=None,   # Optional: Add if needed
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128
    ))

# Dataclass representing the schema for the 'AudioItem' collection
@dataclass(frozen=True)
class AudioItemSchema:
    name: str = "AudioItem"
    description: str = "Metadata and transcript for an audio file."
    properties: List[Property] = field(default_factory=lambda: [
        Property(name="transcript", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="duration_sec", data_type=DataType.NUMBER, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="language", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="filename", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        # Reference to the parent KnowledgeItem
        Property(name="ofKnowledgeItem", data_type=DataType.OBJECT, nested_properties=[
            Property(name="uuid", data_type=DataType.UUID)
        ]),
    ])
    # Configure vectorizer (e.g., text2vec-openai on transcript)
    vectorizer_config: List[Configure.NamedVectors] = field(default_factory=lambda: [
        Configure.NamedVectors.text2vec_openai(
            name="transcript_vector",
            source_properties=["transcript"],
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other relevant collection-level configs
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25_b=0.75,
        bm25_k1=1.2,
        stopwords_preset=StopwordsPreset.EN,
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128
    ))

# Dataclass representing the schema for the 'AudioChunk' collection
@dataclass(frozen=True)
class AudioChunkSchema:
    name: str = "AudioChunk"
    description: str = "Chunks of audio transcripts."
    properties: List[Property] = field(default_factory=lambda: [
        Property(name="text", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="time_start", data_type=DataType.NUMBER, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="time_end", data_type=DataType.NUMBER, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="chunk_index", data_type=DataType.INT, index_filterable=True, index_range_filters=False, index_searchable=False),
        # Reference to the parent AudioItem
        Property(name="ofAudioItem", data_type=DataType.OBJECT, nested_properties=[
            Property(name="uuid", data_type=DataType.UUID)
        ]),
    ])
    # Configure vectorizer (e.g., text2vec-openai on text)
    vectorizer_config: List[Configure.NamedVectors] = field(default_factory=lambda: [
        Configure.NamedVectors.text2vec_openai(
            name="text_vector",
            source_properties=["text"],
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other relevant collection-level configs
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25_b=0.75,
        bm25_k1=1.2,
        stopwords_preset=StopwordsPreset.EN,
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128
    ))

# Dataclass representing the schema for the 'ImageItem' collection
@dataclass(frozen=True)
class ImageItemSchema:
    name: str = "ImageItem"
    description: str = "Metadata, captions, and OCR text for an image file."
    properties: List[Property] = field(default_factory=lambda: [
        Property(name="caption", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="ocr_text", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="width", data_type=DataType.INT, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="height", data_type=DataType.INT, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="backend", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD), # e.g., "openai", "gemini"
        Property(name="filename", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        # Reference to the parent KnowledgeItem
        Property(name="ofKnowledgeItem", data_type=DataType.OBJECT, nested_properties=[
            Property(name="uuid", data_type=DataType.UUID)
        ]),
    ])
    # Configure vectorizer (e.g., text2vec-openai on caption and ocr_text)
    vectorizer_config: List[Configure.NamedVectors] = field(default_factory=lambda: [
        Configure.NamedVectors.text2vec_openai(
            name="caption_vector",
            source_properties=["caption"],
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        ),
         Configure.NamedVectors.text2vec_openai(
            name="ocr_vector",
            source_properties=["ocr_text"],
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other relevant collection-level configs
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25_b=0.75,
        bm25_k1=1.2,
        stopwords_preset=StopwordsPreset.EN,
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128
    ))

# Dataclass representing the schema for the 'VideoItem' collection
@dataclass(frozen=True)
class VideoItemSchema:
    name: str = "VideoItem"
    description: str = "Metadata and transcript for a video file."
    properties: List[Property] = field(default_factory=lambda: [
        Property(name="transcript", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="duration_sec", data_type=DataType.NUMBER, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="language", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="filename", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        # Reference to the parent KnowledgeItem
        Property(name="ofKnowledgeItem", data_type=DataType.OBJECT, nested_properties=[
            Property(name="uuid", data_type=DataType.UUID)
        ]),
    ])
    # Configure vectorizer (e.g., text2vec-openai on transcript)
    vectorizer_config: List[Configure.NamedVectors] = field(default_factory=lambda: [
        Configure.NamedVectors.text2vec_openai(
            name="transcript_vector",
            source_properties=["transcript"],
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other relevant collection-level configs
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25_b=0.75,
        bm25_k1=1.2,
        stopwords_preset=StopwordsPreset.EN,
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128
    ))

# Dataclass representing the schema for the 'VideoChunk' collection
@dataclass(frozen=True)
class VideoChunkSchema:
    name: str = "VideoChunk"
    description: str = "Chunks of video transcripts."
    properties: List[Property] = field(default_factory=lambda: [
        Property(name="text", data_type=DataType.TEXT, index_filterable=True, index_searchable=True, tokenization=Tokenization.WORD),
        Property(name="time_start", data_type=DataType.NUMBER, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="time_end", data_type=DataType.NUMBER, index_filterable=True, index_range_filters=False, index_searchable=False),
        Property(name="chunk_index", data_type=DataType.INT, index_filterable=True, index_range_filters=False, index_searchable=False),
        # Reference to the parent VideoItem
        Property(name="ofVideoItem", data_type=DataType.OBJECT, nested_properties=[
            Property(name="uuid", data_type=DataType.UUID)
        ]),
    ])
    # Configure vectorizer (e.g., text2vec-openai on text)
    vectorizer_config: List[Configure.NamedVectors] = field(default_factory=lambda: [
        Configure.NamedVectors.text2vec_openai(
            name="text_vector",
            source_properties=["text"],
            model="text-embedding-3-large", # Pass model name as string
            vectorize_collection_name=True, # Explicitly set vectorizeClassName
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=VectorDistances.COSINE)
        )
    ])
    # Include other relevant collection-level configs
    inverted_index_config: Configure.inverted_index = field(default_factory=lambda: Configure.inverted_index(
        bm25_b=0.75,
        bm25_k1=1.2,
        stopwords_preset=StopwordsPreset.EN,
        index_null_state=False,
        index_property_length=False,
        index_timestamps=False
    ))
    multi_tenancy_config: Configure.multi_tenancy = field(default_factory=lambda: Configure.multi_tenancy(enabled=False))
    replication_config: Configure.replication = field(default_factory=lambda: Configure.replication(factor=1))
    sharding_config: Configure.sharding = field(default_factory=lambda: Configure.sharding(
        virtual_per_physical=128,
        desired_count=1,
        desired_virtual_count=128
    ))


# List of all collection schemas defined in this file
COLLECTION_SCHEMAS = [
    KnowledgeItemSchema,
    KnowledgeMainSchema,
    AudioItemSchema,
    AudioChunkSchema,
    ImageItemSchema,
    VideoItemSchema,
    VideoChunkSchema,
]

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