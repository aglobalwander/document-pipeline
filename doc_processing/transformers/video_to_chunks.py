"""Transformer for splitting video transcripts into chunks."""
import logging
from typing import Any, Dict, List

from doc_processing.embedding.base import PipelineComponent

logger = logging.getLogger(__name__)

class VideoToChunks(PipelineComponent):
    """
    Splits a video transcript into chunks based on utterance or silence markers.
    """
    def __init__(self, cfg: Dict[str, Any] = None):
        """
        Initializes the VideoToChunks transformer.

        Args:
            cfg: Configuration dictionary (optional).
                 Expected keys:
                 - "split_strategy": "utterance" or "silence" (default: "utterance")
                 - "silence_threshold_sec": Silence duration in seconds to split on (for "silence" strategy)
        """
        self.cfg = cfg or {}
        self.split_strategy = self.cfg.get("split_strategy", "utterance")
        self.silence_threshold_sec = self.cfg.get("silence_threshold_sec", 1.0) # Default 1 second silence
        logger.info(f"VideoToChunks initialized with strategy: {self.split_strategy}")

    def run(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Splits the transcript data into chunks.

        Args:
            transcript_data: A dictionary containing the transcript and metadata,
                             expected to include "content" (full transcript text)
                             and "metadata" which may contain "words" with timestamps
                             or information about silence markers from the processor.

        Returns:
            A dictionary containing the original content and a list of chunks.
        """
        full_transcript = transcript_data.get("content", "")
        metadata = transcript_data.get("metadata", {})
        words = metadata.get("words", []) # Expected from Deepgram output with timestamps

        chunks: List[Dict[str, Any]] = []
        current_chunk_text = ""
        current_chunk_start_time = None
        chunk_index = 0

        if self.split_strategy == "utterance" and words:
            # Split based on utterances (assuming words list has utterance boundaries or can be inferred)
            # This is a simplified approach; a more robust implementation might need
            # explicit utterance markers from the transcription service.
            # For now, let's assume each word is a potential chunk or group words into sentences/utterances.
            # A more practical approach might be to group words by speaker or sentence structure.
            # Given the blueprint mentions splitting on Deepgram's utterances,
            # a more direct integration with Deepgram's output structure might be needed.
            # For this scaffold, let's create chunks based on a simple word count or sentence split if possible.
            # A basic implementation: treat each sentence as a chunk.
            import re
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', full_transcript)
            
            for i, sentence in enumerate(sentences):
                 if sentence.strip():
                      chunks.append({
                          "text": sentence.strip(),
                          "chunk_index": i,
                          "time_start": None, # Need to map sentence to time if possible
                          "time_end": None, # Need to map sentence to time if possible
                          "metadata": {}, # Add chunk-specific metadata if available
                      })
            logger.info(f"Split transcript into {len(chunks)} chunks using sentence splitting.")


        elif self.split_strategy == "silence" and words:
             # Splitting by silence requires processing the word timestamps and identifying gaps.
             # This is more complex and depends heavily on the format of 'words' and silence info.
             # Placeholder for silence-based splitting logic
             logger.warning("Silence-based splitting not fully implemented in scaffold.")
             # Fallback to a simple chunking if silence splitting is requested but not implemented
             if not chunks:
                  # Simple chunking by character count as a fallback
                  chunk_size = 500 # Example chunk size
                  for i in range(0, len(full_transcript), chunk_size):
                       chunks.append({
                           "text": full_transcript[i:i+chunk_size],
                           "chunk_index": len(chunks),
                           "time_start": None,
                           "time_end": None,
                           "metadata": {},
                       })
                  logger.info(f"Split transcript into {len(chunks)} chunks using character count fallback.")


        else:
            # Default to a simple chunking if no specific strategy is applicable or data is missing
            chunk_size = 500 # Example chunk size
            for i in range(0, len(full_transcript), chunk_size):
                 chunks.append({
                     "text": full_transcript[i:i+chunk_size],
                     "chunk_index": len(chunks),
                     "time_start": None,
                     "time_end": None,
                     "metadata": {},
                 })
            logger.info(f"Split transcript into {len(chunks)} chunks using default character count.")


        # Add a reference to the parent item ID if available in the input metadata
        parent_item_id = metadata.get("item_id")
        for chunk in chunks:
             chunk["metadata"]["item_id"] = parent_item_id


        return {"content": full_transcript, "chunks": chunks, "metadata": metadata}

# Note: This transformer expects transcript data with a "content" key for the full transcript
# and potentially a "metadata" key containing a "words" list with timestamp information
# from a previous component like DeepgramProcessor.