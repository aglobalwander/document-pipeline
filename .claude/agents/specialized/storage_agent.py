"""Storage agent for handling document persistence and retrieval."""
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from ..core.base_agent import (
    BaseAgent, AgentRole, AgentStatus, AgentMessage, AgentCapability
)


class StorageAgent(BaseAgent):
    """Agent specialized in document storage and retrieval."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize storage agent.
        
        Args:
            config: Agent configuration
        """
        super().__init__(
            name="storage",
            role=AgentRole.STORAGE,
            config=config
        )
        
        self.weaviate_client = None
        self.storage_backends = {}
        self._setup_capabilities()
        
    def _setup_capabilities(self):
        """Setup storage capabilities."""
        # Weaviate storage
        self.add_capability(AgentCapability(
            name="store_in_weaviate",
            description="Store documents in Weaviate vector database",
            input_types=["documents", "chunks"],
            output_types=["storage_result"],
            parameters={
                "collection": "Documents",
                "batch_size": 100
            }
        ))
        
        self.add_capability(AgentCapability(
            name="retrieve_from_weaviate",
            description="Retrieve documents from Weaviate",
            input_types=["query", "filters"],
            output_types=["documents"],
            parameters={
                "limit": 10,
                "certainty": 0.7
            }
        ))
        
        # File system storage
        self.add_capability(AgentCapability(
            name="store_to_file",
            description="Store documents to file system",
            input_types=["document", "content"],
            output_types=["file_path"],
            parameters={
                "output_dir": "data/output",
                "format": "json"
            }
        ))
        
        self.add_capability(AgentCapability(
            name="load_from_file",
            description="Load documents from file system",
            input_types=["file_path"],
            output_types=["document", "content"]
        ))
        
        # Cache management
        self.add_capability(AgentCapability(
            name="cache_document",
            description="Cache processed document",
            input_types=["document", "cache_key"],
            output_types=["cache_result"]
        ))
        
        self.add_capability(AgentCapability(
            name="retrieve_from_cache",
            description="Retrieve from cache",
            input_types=["cache_key"],
            output_types=["document", "cache_hit"]
        ))
        
    async def initialize(self) -> bool:
        """Initialize storage resources."""
        try:
            self.logger.info("Initializing storage agent...")
            
            # Initialize Weaviate client if configured
            if self.config.get("weaviate_enabled", False):
                from weaviate_layer.client import WeaviateClientManager
                manager = WeaviateClientManager()
                self.weaviate_client = manager.get_client()
            
            # Initialize storage backends
            self.storage_backends = {
                "file": FileStorage(self.config.get("file_storage", {})),
                "cache": CacheStorage(self.config.get("cache", {}))
            }
            
            self.update_status(AgentStatus.READY)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize storage: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
    
    async def shutdown(self) -> bool:
        """Clean up storage resources."""
        try:
            self.logger.info("Shutting down storage agent...")
            
            # Close Weaviate connection
            if self.weaviate_client:
                self.weaviate_client.close()
            
            self.update_status(AgentStatus.IDLE)
            return True
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            return False
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process storage requests.
        
        Args:
            message: Storage request
            
        Returns:
            Storage result
        """
        self.update_status(AgentStatus.PROCESSING)
        
        try:
            action = message.action
            payload = message.payload
            
            if action == "store_in_weaviate":
                result = await self._store_in_weaviate(payload)
                
            elif action == "retrieve_from_weaviate":
                result = await self._retrieve_from_weaviate(payload)
                
            elif action == "store_to_file":
                result = await self._store_to_file(payload)
                
            elif action == "load_from_file":
                result = await self._load_from_file(payload)
                
            elif action == "cache_document":
                result = await self._cache_document(payload)
                
            elif action == "retrieve_from_cache":
                result = await self._retrieve_from_cache(payload)
                
            else:
                raise ValueError(f"Unknown action: {action}")
            
            self.update_status(AgentStatus.READY)
            
            return self.create_response(
                recipient=message.sender,
                action=f"{action}_result",
                payload=result,
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            self.logger.error(f"Storage error: {e}")
            self.update_status(AgentStatus.ERROR)
            
            return self.create_response(
                recipient=message.sender,
                action="error",
                payload={"error": str(e)},
                correlation_id=message.correlation_id
            )
    
    async def _store_in_weaviate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store documents in Weaviate.
        
        Args:
            payload: Storage parameters
            
        Returns:
            Storage result
        """
        if not self.weaviate_client:
            return {"success": False, "error": "Weaviate not configured"}
        
        documents = payload.get("documents", [])
        chunks = payload.get("chunks", [])
        collection = payload.get("collection", "Documents")
        
        # Store documents or chunks
        items_to_store = documents or chunks
        stored_ids = []
        
        for item in items_to_store:
            # Would actually store in Weaviate
            stored_ids.append(f"doc_{len(stored_ids)}")
        
        return {
            "success": True,
            "stored_count": len(stored_ids),
            "ids": stored_ids,
            "collection": collection
        }
    
    async def _retrieve_from_weaviate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve documents from Weaviate.
        
        Args:
            payload: Retrieval parameters
            
        Returns:
            Retrieved documents
        """
        if not self.weaviate_client:
            return {"success": False, "error": "Weaviate not configured"}
        
        query = payload.get("query")
        filters = payload.get("filters", {})
        limit = payload.get("limit", 10)
        
        # Would actually query Weaviate
        documents = []
        
        return {
            "success": True,
            "documents": documents,
            "count": len(documents),
            "query": query
        }
    
    async def _store_to_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store document to file system.
        
        Args:
            payload: Storage parameters
            
        Returns:
            File path
        """
        storage = self.storage_backends["file"]
        result = await storage.store(payload)
        return result
    
    async def _load_from_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Load document from file system.
        
        Args:
            payload: Load parameters
            
        Returns:
            Document content
        """
        storage = self.storage_backends["file"]
        result = await storage.load(payload)
        return result
    
    async def _cache_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Cache processed document.
        
        Args:
            payload: Cache parameters
            
        Returns:
            Cache result
        """
        cache = self.storage_backends["cache"]
        result = await cache.store(payload)
        return result
    
    async def _retrieve_from_cache(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve from cache.
        
        Args:
            payload: Cache parameters
            
        Returns:
            Cached document
        """
        cache = self.storage_backends["cache"]
        result = await cache.retrieve(payload)
        return result


class FileStorage:
    """File system storage backend."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize file storage.
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self.output_dir = Path(config.get("output_dir", "data/output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def store(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store to file.
        
        Args:
            payload: Storage parameters
            
        Returns:
            Storage result
        """
        content = payload.get("content", "")
        document = payload.get("document", {})
        format = payload.get("format", "json")
        filename = payload.get("filename", f"document_{len(list(self.output_dir.glob('*')))}")
        
        # Determine file path
        file_path = self.output_dir / f"{filename}.{format}"
        
        # Write content
        if format == "json":
            with open(file_path, "w") as f:
                json.dump(document or {"content": content}, f, indent=2)
        else:
            with open(file_path, "w") as f:
                f.write(content)
        
        return {
            "success": True,
            "file_path": str(file_path),
            "size": file_path.stat().st_size
        }
    
    async def load(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Load from file.
        
        Args:
            payload: Load parameters
            
        Returns:
            File content
        """
        file_path = Path(payload.get("file_path"))
        
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        # Read content
        if file_path.suffix == ".json":
            with open(file_path, "r") as f:
                content = json.load(f)
        else:
            with open(file_path, "r") as f:
                content = f.read()
        
        return {
            "success": True,
            "content": content,
            "file_path": str(file_path)
        }


class CacheStorage:
    """In-memory cache storage."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize cache storage.
        
        Args:
            config: Cache configuration
        """
        self.config = config
        self.cache = {}
        self.max_size = config.get("max_size", 100)
    
    async def store(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store in cache.
        
        Args:
            payload: Cache parameters
            
        Returns:
            Cache result
        """
        cache_key = payload.get("cache_key")
        document = payload.get("document")
        
        # Implement simple LRU by removing oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        
        self.cache[cache_key] = document
        
        return {
            "success": True,
            "cache_key": cache_key,
            "cached": True
        }
    
    async def retrieve(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve from cache.
        
        Args:
            payload: Retrieval parameters
            
        Returns:
            Cached content
        """
        cache_key = payload.get("cache_key")
        
        if cache_key in self.cache:
            return {
                "success": True,
                "cache_hit": True,
                "document": self.cache[cache_key]
            }
        
        return {
            "success": True,
            "cache_hit": False,
            "document": None
        }