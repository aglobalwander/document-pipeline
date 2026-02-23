"""Transformer agent for converting between document formats."""
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
from doc_processing.transformers.text_to_markdown import TextToMarkdown
from doc_processing.transformers.text_to_json import TextToJSON
from doc_processing.transformers.chunker import LangChainChunker
from doc_processing.transformers.json_to_csv import JsonToCSV
from doc_processing.transformers.json_to_excel import JsonToExcel


class TransformerAgent(BaseAgent):
    """Agent specialized in document transformation and conversion."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize transformer agent.
        
        Args:
            config: Agent configuration
        """
        super().__init__(
            name="transformer",
            role=AgentRole.TRANSFORMER,
            config=config
        )
        
        self.transformers = {}
        self._setup_capabilities()
        
    def _setup_capabilities(self):
        """Setup transformer capabilities."""
        # Format conversion capabilities
        self.add_capability(AgentCapability(
            name="text_to_markdown",
            description="Convert text to markdown format",
            input_types=["text", "document"],
            output_types=["markdown"],
            parameters={
                "preserve_formatting": True,
                "add_headers": True
            }
        ))
        
        self.add_capability(AgentCapability(
            name="text_to_json",
            description="Convert text to structured JSON",
            input_types=["text", "document"],
            output_types=["json"],
            parameters={
                "schema": None,
                "extract_entities": True
            }
        ))
        
        self.add_capability(AgentCapability(
            name="json_to_csv",
            description="Convert JSON to CSV format",
            input_types=["json"],
            output_types=["csv"],
            parameters={
                "flatten": True,
                "delimiter": ","
            }
        ))
        
        self.add_capability(AgentCapability(
            name="json_to_excel",
            description="Convert JSON to Excel format",
            input_types=["json"],
            output_types=["xlsx"],
            parameters={
                "template": None,
                "sheet_name": "Data"
            }
        ))
        
        # Chunking capabilities
        self.add_capability(AgentCapability(
            name="chunk_text",
            description="Split text into chunks",
            input_types=["text", "document"],
            output_types=["chunks"],
            parameters={
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "strategy": "recursive"
            }
        ))
        
        self.add_capability(AgentCapability(
            name="chunk_by_section",
            description="Split document by sections",
            input_types=["document", "markdown"],
            output_types=["sections"],
            parameters={
                "min_section_size": 100,
                "preserve_hierarchy": True
            }
        ))
        
        # Enhancement capabilities
        self.add_capability(AgentCapability(
            name="enrich_metadata",
            description="Add metadata to document",
            input_types=["document"],
            output_types=["document"],
            parameters={
                "extract_keywords": True,
                "extract_entities": True,
                "generate_summary": False
            }
        ))
        
        self.add_capability(AgentCapability(
            name="clean_text",
            description="Clean and normalize text",
            input_types=["text"],
            output_types=["text"],
            parameters={
                "remove_extra_whitespace": True,
                "fix_encoding": True,
                "normalize_unicode": True
            }
        ))
        
    async def initialize(self) -> bool:
        """Initialize transformer resources."""
        try:
            self.logger.info("Initializing transformer agent...")
            
            # Initialize transformers
            self.transformers = {
                "text_to_markdown": TextToMarkdown(config=self.config.get("markdown", {})),
                "text_to_json": TextToJSON(config=self.config.get("json", {})),
                "chunker": LangChainChunker(config=self.config.get("chunker", {})),
                "json_to_csv": JsonToCSV(config=self.config.get("csv", {})),
                "json_to_excel": JsonToExcel(config=self.config.get("excel", {}))
            }
            
            self.update_status(AgentStatus.READY)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize transformer: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
    
    async def shutdown(self) -> bool:
        """Clean up transformer resources."""
        try:
            self.logger.info("Shutting down transformer agent...")
            self.transformers.clear()
            self.update_status(AgentStatus.IDLE)
            return True
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            return False
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process transformation requests.
        
        Args:
            message: Transformation request
            
        Returns:
            Transformation result
        """
        self.update_status(AgentStatus.PROCESSING)
        
        try:
            action = message.action
            payload = message.payload
            
            if action == "text_to_markdown":
                result = await self._text_to_markdown(payload)
                
            elif action == "text_to_json":
                result = await self._text_to_json(payload)
                
            elif action == "json_to_csv":
                result = await self._json_to_csv(payload)
                
            elif action == "json_to_excel":
                result = await self._json_to_excel(payload)
                
            elif action == "chunk_text":
                result = await self._chunk_text(payload)
                
            elif action == "chunk_by_section":
                result = await self._chunk_by_section(payload)
                
            elif action == "enrich_metadata":
                result = await self._enrich_metadata(payload)
                
            elif action == "clean_text":
                result = await self._clean_text(payload)
                
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
            self.logger.error(f"Transformation error: {e}")
            self.update_status(AgentStatus.ERROR)
            
            return self.create_response(
                recipient=message.sender,
                action="error",
                payload={"error": str(e)},
                correlation_id=message.correlation_id
            )
    
    async def _text_to_markdown(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert text to markdown.
        
        Args:
            payload: Conversion parameters
            
        Returns:
            Markdown content
        """
        text = payload.get("text", "")
        document = payload.get("document", {})
        
        transformer = self.transformers["text_to_markdown"]
        
        # Transform to markdown
        result = await asyncio.to_thread(
            transformer.transform,
            text or document.get("content", "")
        )
        
        return {
            "success": True,
            "markdown": result,
            "format": "markdown"
        }
    
    async def _text_to_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert text to JSON.
        
        Args:
            payload: Conversion parameters
            
        Returns:
            JSON content
        """
        text = payload.get("text", "")
        document = payload.get("document", {})
        schema = payload.get("schema")
        
        transformer = self.transformers["text_to_json"]
        
        # Transform to JSON
        result = await asyncio.to_thread(
            transformer.transform,
            text or document.get("content", ""),
            schema=schema
        )
        
        return {
            "success": True,
            "json": result,
            "format": "json"
        }
    
    async def _json_to_csv(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON to CSV.
        
        Args:
            payload: Conversion parameters
            
        Returns:
            CSV content
        """
        json_data = payload.get("json", {})
        
        transformer = self.transformers["json_to_csv"]
        
        # Transform to CSV
        result = await asyncio.to_thread(
            transformer.transform,
            json_data
        )
        
        return {
            "success": True,
            "csv": result,
            "format": "csv"
        }
    
    async def _json_to_excel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON to Excel.
        
        Args:
            payload: Conversion parameters
            
        Returns:
            Excel file path
        """
        json_data = payload.get("json", {})
        template = payload.get("template")
        
        transformer = self.transformers["json_to_excel"]
        
        # Transform to Excel
        result = await asyncio.to_thread(
            transformer.transform,
            json_data,
            template=template
        )
        
        return {
            "success": True,
            "excel_path": result,
            "format": "xlsx"
        }
    
    async def _chunk_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Chunk text into smaller pieces.
        
        Args:
            payload: Chunking parameters
            
        Returns:
            Text chunks
        """
        text = payload.get("text", "")
        document = payload.get("document", {})
        chunk_size = payload.get("chunk_size", 1000)
        chunk_overlap = payload.get("chunk_overlap", 200)
        
        chunker = self.transformers["chunker"]
        
        # Chunk text
        chunks = await asyncio.to_thread(
            chunker.chunk,
            text or document.get("content", ""),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return {
            "success": True,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "avg_chunk_size": sum(len(c) for c in chunks) // len(chunks) if chunks else 0
        }
    
    async def _chunk_by_section(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Chunk document by sections.
        
        Args:
            payload: Chunking parameters
            
        Returns:
            Document sections
        """
        document = payload.get("document", {})
        markdown = payload.get("markdown", "")
        min_section_size = payload.get("min_section_size", 100)
        
        # Simple section detection
        content = markdown or document.get("content", "")
        sections = []
        
        if "# " in content or "## " in content:
            # Split by headers
            import re
            pattern = r'^#+\s+(.+)$'
            lines = content.split('\n')
            current_section = {"title": "Introduction", "content": []}
            
            for line in lines:
                match = re.match(pattern, line)
                if match:
                    # Save current section if it has content
                    if current_section["content"]:
                        sections.append({
                            "title": current_section["title"],
                            "content": '\n'.join(current_section["content"])
                        })
                    # Start new section
                    current_section = {"title": match.group(1), "content": []}
                else:
                    current_section["content"].append(line)
            
            # Add last section
            if current_section["content"]:
                sections.append({
                    "title": current_section["title"],
                    "content": '\n'.join(current_section["content"])
                })
        else:
            # No headers, treat as single section
            sections = [{"title": "Main", "content": content}]
        
        # Filter by minimum size
        sections = [s for s in sections if len(s["content"]) >= min_section_size]
        
        return {
            "success": True,
            "sections": sections,
            "section_count": len(sections)
        }
    
    async def _enrich_metadata(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich document with metadata.
        
        Args:
            payload: Enrichment parameters
            
        Returns:
            Enriched document
        """
        document = payload.get("document", {})
        extract_keywords = payload.get("extract_keywords", True)
        extract_entities = payload.get("extract_entities", True)
        
        # Add metadata
        metadata = document.get("metadata", {})
        
        if extract_keywords:
            # Simple keyword extraction
            content = document.get("content", "")
            words = content.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Simple filter
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            metadata["keywords"] = [k[0] for k in keywords]
        
        if extract_entities:
            # Would use NER here
            metadata["entities"] = []
        
        document["metadata"] = metadata
        
        return {
            "success": True,
            "document": document,
            "metadata": metadata
        }
    
    async def _clean_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize text.
        
        Args:
            payload: Cleaning parameters
            
        Returns:
            Cleaned text
        """
        text = payload.get("text", "")
        remove_extra_whitespace = payload.get("remove_extra_whitespace", True)
        
        cleaned = text
        
        if remove_extra_whitespace:
            import re
            # Remove extra whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
            cleaned = cleaned.strip()
        
        return {
            "success": True,
            "text": cleaned,
            "original_length": len(text),
            "cleaned_length": len(cleaned)
        }