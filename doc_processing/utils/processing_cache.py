"""Processing Cache Utility for Document Pipeline."""
import os
import json
import time
from pathlib import Path

class ProcessingCache:
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, document_id):
        """Generate a unique cache file path based on document ID"""
        return self.cache_dir / f"{document_id}.json"
    
    def save_checkpoint(self, document_id, processed_pages, metadata):
        """Save current processing state to cache"""
        cache_path = self.get_cache_path(document_id)
        checkpoint_data = {
            "document_id": document_id,
            "processed_pages": processed_pages,
            "metadata": metadata,
            "timestamp": time.time()
        }
        with open(cache_path, "w") as f:
            json.dump(checkpoint_data, f)
    
    def load_checkpoint(self, document_id):
        """Load processing state from cache if exists"""
        cache_path = self.get_cache_path(document_id)
        if cache_path.exists():
            with open(cache_path, "r") as f:
                return json.load(f)
        return None
    
    def clear_checkpoint(self, document_id):
        """Remove checkpoint after successful processing"""
        cache_path = self.get_cache_path(document_id)
        if cache_path.exists():
            cache_path.unlink()
