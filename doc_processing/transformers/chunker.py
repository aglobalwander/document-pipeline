"""Document chunking module for splitting text into manageable pieces."""
import re
from typing import Any, Dict, List, Optional, Union, Callable
import logging
import nltk
from nltk.tokenize import sent_tokenize

from doc_processing.embedding.base import BaseTransformer # Corrected import path

# Download necessary NLTK data if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class DocumentChunker(BaseTransformer):
    """Split documents into smaller chunks for processing and embedding."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize chunker.
        
        Args:
            config: Configuration options
        """
        super().__init__(config)
        
        # Chunking configuration
        self.chunk_size = self.config.get('chunk_size', 1000)
        self.chunk_overlap = self.config.get('chunk_overlap', 200)
        self.chunk_by = self.config.get('chunk_by', 'tokens')  # 'tokens', 'characters', 'sentences', 'paragraphs'
        self.preserve_paragraph_boundaries = self.config.get('preserve_paragraph_boundaries', True)
        self.respect_document_boundaries = self.config.get('respect_document_boundaries', True)
        
        # Sentence splitting for better chunking
        self.sentence_splitter = self._get_sentence_splitter()
    
    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Split document into chunks.
        
        Args:
            document: Document to chunk
            
        Returns:
            Document with added chunks
        """
        if not document.get('content'):
            self.logger.warning(f"Document has no content to chunk")
            document['chunks'] = []
            return document
        
        content = document.get('content', '')
        
        # Split document into chunks
        chunks = self._split_text(content)
        
        # Create chunk objects
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            chunk_object = {
                'content': chunk_text,
                'chunk_index': i,
                'document_id': document.get('id', None),
                'metadata': {
                    'start_position': self._get_chunk_start_position(content, chunk_text, i),
                    'length': len(chunk_text),
                    'chunk_method': self.chunk_by,
                    'page_numbers': self._get_page_numbers_for_chunk(document, chunk_text, i)
                }
            }
            chunk_objects.append(chunk_object)
        
        # Add chunks to document
        document['chunks'] = chunk_objects
        document['metadata']['num_chunks'] = len(chunk_objects)
        
        self.logger.info(f"Split document into {len(chunk_objects)} chunks")
        return document
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks based on configuration.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if self.chunk_by == 'tokens':
            return self._split_by_tokens(text)
        elif self.chunk_by == 'characters':
            return self._split_by_characters(text)
        elif self.chunk_by == 'sentences':
            return self._split_by_sentences(text)
        elif self.chunk_by == 'paragraphs':
            return self._split_by_paragraphs(text)
        else:
            self.logger.warning(f"Unknown chunk_by value: {self.chunk_by}. Using tokens.")
            return self._split_by_tokens(text)
    
    def _split_by_tokens(self, text: str) -> List[str]:
        """Split text by tokens.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Split text into sentences first for better chunking
        sentences = self.sentence_splitter(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            # Tokenize sentence (simple whitespace tokenization)
            tokens = sentence.split()
            sentence_len = len(tokens)
            
            # If sentence is too long for a single chunk, split it further
            if sentence_len > self.chunk_size:
                # First add the current_chunk if it's non-empty
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long sentence
                for i in range(0, sentence_len, self.chunk_size - self.chunk_overlap):
                    chunk = tokens[i:i + self.chunk_size]
                    chunks.append(' '.join(chunk))
            
            # Normal case: add sentence to current chunk if it fits
            elif current_length + sentence_len <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_len
            
            # If sentence doesn't fit, start a new chunk
            else:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_len
        
        # Add the last chunk if it's non-empty
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_by_characters(self, text: str) -> List[str]:
        """Split text by characters.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # If preserving paragraph boundaries, split by paragraphs first
        if self.preserve_paragraph_boundaries:
            paragraphs = text.split('\n\n')
            chunks = []
            current_chunk = ""
            
            for paragraph in paragraphs:
                # If paragraph itself is too long, split it
                if len(paragraph) > self.chunk_size:
                    # First add the current_chunk if it's non-empty
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = ""
                    
                    # Split long paragraph
                    for i in range(0, len(paragraph), self.chunk_size - self.chunk_overlap):
                        chunk = paragraph[i:i + self.chunk_size]
                        chunks.append(chunk)
                
                # Add paragraph to current chunk if it fits
                elif len(current_chunk) + len(paragraph) + 2 <= self.chunk_size:  # +2 for the paragraph separators
                    if current_chunk:
                        current_chunk += "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
                
                # If it doesn't fit, start a new chunk
                else:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
            
            # Add the last chunk if it's non-empty
            if current_chunk:
                chunks.append(current_chunk)
            
            return chunks
        
        # Simple character-based splitting if not preserving paragraphs
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Get all sentences
        sentences = self.sentence_splitter(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            # If sentence itself is too long for a chunk
            if sentence_len > self.chunk_size:
                # First add the current_chunk if it's non-empty
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split the long sentence by characters
                for i in range(0, sentence_len, self.chunk_size - self.chunk_overlap):
                    chunk = sentence[i:i + self.chunk_size]
                    chunks.append(chunk)
            
            # Add sentence to current chunk if it fits
            elif current_length + sentence_len <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_len
            
            # If it doesn't fit, start a new chunk
            else:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_len
        
        # Add the last chunk if it's non-empty
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Split text into paragraphs (empty line as separator)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            paragraph_len = len(paragraph)
            
            # If paragraph itself is too long for a chunk
            if paragraph_len > self.chunk_size:
                # First add the current_chunk if it's non-empty
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split the long paragraph by sentences
                paragraph_sentences = self.sentence_splitter(paragraph)
                paragraph_chunks = self._split_by_sentences('\n'.join(paragraph_sentences))
                
                # Add these chunks
                chunks.extend(paragraph_chunks)
            
            # Add paragraph to current chunk if it fits
            elif current_length + paragraph_len <= self.chunk_size:
                current_chunk.append(paragraph)
                current_length += paragraph_len
            
            # If it doesn't fit, start a new chunk
            else:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_length = paragraph_len
        
        # Add the last chunk if it's non-empty
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _get_sentence_splitter(self) -> Callable:
        """Get sentence splitting function.
        
        Returns:
            Function to split text into sentences
        """
        # Use NLTK's sent_tokenize for better sentence splitting
        return sent_tokenize
    
    def _get_chunk_start_position(self, 
                                 original_text: str, 
                                 chunk_text: str, 
                                 chunk_index: int) -> Optional[int]:
        """Find the start position of chunk in the original text.
        
        Args:
            original_text: Original document text
            chunk_text: Chunk text
            chunk_index: Index of chunk
            
        Returns:
            Character position of chunk start or None if not found
        """
        # If first chunk, start at 0
        if chunk_index == 0:
            return 0
        
        # Get first 100 chars of chunk (or fewer if chunk is shorter)
        prefix_len = min(100, len(chunk_text))
        prefix = chunk_text[:prefix_len]
        
        # Find this prefix in the original text
        try:
            pos = original_text.index(prefix)
            return pos
        except ValueError:
            self.logger.warning(f"Could not find chunk {chunk_index} start position")
            return None
    
    def _get_page_numbers_for_chunk(self, 
                                   document: Dict[str, Any], 
                                   chunk_text: str, 
                                   chunk_index: int) -> List[int]:
        """Get page numbers for a chunk.
        
        Args:
            document: Original document
            chunk_text: Chunk text
            chunk_index: Index of chunk
            
        Returns:
            List of page numbers
        """
        # If document has no page information, return empty list
        if 'pages' not in document:
            return []
        
        pages = document['pages']
        chunk_start = self._get_chunk_start_position(document['content'], chunk_text, chunk_index)
        
        if chunk_start is None:
            return []
        
        chunk_end = chunk_start + len(chunk_text)
        
        # Calculate cumulative position of each page
        cumulative_pos = 0
        page_positions = []
        
        for page in pages:
            page_content = page.get('text', '')
            page_len = len(page_content)
            page_positions.append((page.get('page_number', 0), cumulative_pos, cumulative_pos + page_len))
            cumulative_pos += page_len
        
        # Find pages that overlap with chunk
        chunk_pages = []
        for page_num, start_pos, end_pos in page_positions:
            if (start_pos <= chunk_start < end_pos) or (start_pos < chunk_end <= end_pos) or (chunk_start <= start_pos and chunk_end >= end_pos):
                chunk_pages.append(page_num)
        
        return chunk_pages