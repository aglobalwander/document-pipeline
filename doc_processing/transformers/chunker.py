"""Document chunking module using LangChain text splitters."""
from typing import Any, Dict, List, Optional, Union, Callable
import logging
import tiktoken

from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
)

from doc_processing.embedding.base import BaseTransformer # Assuming BaseTransformer is still needed

class LangChainChunker(BaseTransformer): # Inheriting from BaseTransformer as in the original file
    """Split documents into smaller chunks using LangChain text splitters."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize chunker.
        
        Args:
            config: Configuration options
        """
        super().__init__(config)
        
        chunk_size = self.config.get("chunk_size", 800)
        chunk_overlap = self.config.get("chunk_overlap", 100)
        
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.token_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Split document into chunks using LangChain.
        
        Args:
            document: Document to chunk (expected to have 'content' key)
            
        Returns:
            Document with added 'chunks' key
        """
        if not document.get('content'):
            self.logger.warning(f"Document has no content to chunk")
            document['chunks'] = []
            return document
        
        content = document.get('content', '')
        
        # Use only token-based splitting for uniform chunking
        chunks = self.token_splitter.split_text(content)
            
        # Debug: log token counts and previews for each chunk
        encoding = tiktoken.get_encoding("cl100k_base")
        for idx, ch_text in enumerate(chunks):
            token_count = len(encoding.encode(ch_text))
            self.logger.debug(f"Chunk {idx}: {token_count} tokens, preview: {repr(ch_text[:50])}")

        # Debug: log overlap validation between consecutive chunks
        for idx in range(1, len(chunks)):
            prev_text = chunks[idx - 1]
            curr_text = chunks[idx]
            overlap_prefix_len = min(50, len(curr_text))
            overlap_search_len = min(150, len(prev_text))
            prefix_to_find = curr_text[:overlap_prefix_len]
            search_area = prev_text[-overlap_search_len:]
            found = prefix_to_find in search_area
            self.logger.debug(f"Overlap between chunk {idx-1} and {idx}: {found}")

        # Create chunk objects with content and index
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
             chunk_objects.append({"content": chunk_text, "chunk_index": i})
        
        document['chunks'] = chunk_objects
        self.logger.info(f"Split document into {len(chunk_objects)} chunks using LangChain")
        
        return document

    # Removed NLTK-specific helper methods: _split_text, _split_by_tokens, _split_by_characters, _split_by_sentences, _split_by_paragraphs, _get_sentence_splitter, _get_chunk_start_position, _get_page_numbers_for_chunk
    # Note: Metadata like start_position and page_numbers will need to be handled differently if required, as LangChain splitters don't provide this directly.
    # The development plan only specified adding the chunk content and index.