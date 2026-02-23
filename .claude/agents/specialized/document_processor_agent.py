"""Document processor agent for handling various document formats."""
import asyncio
from typing import Any, Dict, Optional
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from ..core.base_agent import (
    BaseAgent, AgentRole, AgentStatus, AgentMessage, AgentCapability
)
from doc_processing.processors.enhanced_docling_processor import EnhancedDoclingPDFProcessor
from doc_processing.processors.pymupdf_processor import PyMuPDFProcessor
from doc_processing.processors.docx_processor import MammothDOCXProcessor
from doc_processing.processors.pptx_processor import MarkItDownPPTXProcessor


class DocumentProcessorAgent(BaseAgent):
    """Agent specialized in processing documents."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize document processor agent.
        
        Args:
            config: Agent configuration
        """
        super().__init__(
            name="document_processor",
            role=AgentRole.PROCESSOR,
            config=config
        )
        
        self.processors = {}
        self._setup_capabilities()
        
    def _setup_capabilities(self):
        """Setup processor capabilities."""
        # PDF processing capabilities
        self.add_capability(AgentCapability(
            name="process_pdf_docling",
            description="Process PDF using Enhanced Docling",
            input_types=["pdf", "file_path"],
            output_types=["text", "markdown", "json"],
            parameters={
                "ocr_mode": "hybrid",
                "extract_tables": True,
                "detect_columns": True
            }
        ))
        
        self.add_capability(AgentCapability(
            name="process_pdf_pymupdf",
            description="Process PDF using PyMuPDF",
            input_types=["pdf", "file_path"],
            output_types=["text", "markdown"],
            parameters={
                "extract_images": False,
                "preserve_layout": True
            }
        ))
        
        # DOCX processing
        self.add_capability(AgentCapability(
            name="process_docx",
            description="Process DOCX documents",
            input_types=["docx", "file_path"],
            output_types=["markdown", "html"],
            parameters={
                "extract_styles": True,
                "extract_comments": True
            }
        ))
        
        # PPTX processing
        self.add_capability(AgentCapability(
            name="process_pptx",
            description="Process PowerPoint presentations",
            input_types=["pptx", "file_path"],
            output_types=["markdown", "text"],
            parameters={
                "extract_notes": True,
                "extract_media": False
            }
        ))
        
        # Analysis capabilities
        self.add_capability(AgentCapability(
            name="analyze_document",
            description="Analyze document structure and content",
            input_types=["any"],
            output_types=["analysis_report"]
        ))
        
    async def initialize(self) -> bool:
        """Initialize processor resources."""
        try:
            self.logger.info("Initializing document processor agent...")
            
            # Initialize processors
            self.processors = {
                "docling": EnhancedDoclingPDFProcessor(config=self.config.get("docling", {})),
                "pymupdf": PyMuPDFProcessor(config=self.config.get("pymupdf", {})),
                "docx": MammothDOCXProcessor(config=self.config.get("docx", {})),
                "pptx": MarkItDownPPTXProcessor(config=self.config.get("pptx", {}))
            }
            
            self.update_status(AgentStatus.READY)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
    
    async def shutdown(self) -> bool:
        """Clean up processor resources."""
        try:
            self.logger.info("Shutting down document processor agent...")
            # Clean up any open resources
            self.processors.clear()
            self.update_status(AgentStatus.IDLE)
            return True
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            return False
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process document processing requests.
        
        Args:
            message: Processing request
            
        Returns:
            Processing result
        """
        self.update_status(AgentStatus.PROCESSING)
        
        try:
            action = message.action
            payload = message.payload
            
            if action == "process_pdf_docling":
                result = await self._process_pdf_docling(payload)
                
            elif action == "process_pdf_pymupdf":
                result = await self._process_pdf_pymupdf(payload)
                
            elif action == "process_docx":
                result = await self._process_docx(payload)
                
            elif action == "process_pptx":
                result = await self._process_pptx(payload)
                
            elif action == "analyze_document":
                result = await self._analyze_document(payload)
                
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
            self.logger.error(f"Processing error: {e}")
            self.update_status(AgentStatus.ERROR)
            
            return self.create_response(
                recipient=message.sender,
                action="error",
                payload={"error": str(e)},
                correlation_id=message.correlation_id
            )
    
    async def _process_pdf_docling(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF using Enhanced Docling.
        
        Args:
            payload: Processing parameters
            
        Returns:
            Processing results
        """
        file_path = payload.get("file_path")
        ocr_mode = payload.get("ocr_mode", "hybrid")
        extract_tables = payload.get("extract_tables", True)
        
        processor = self.processors["docling"]
        
        # Process document
        result = await asyncio.to_thread(
            processor.process,
            file_path,
            ocr_mode=ocr_mode,
            extract_tables=extract_tables
        )
        
        return {
            "success": True,
            "text": result.get("text"),
            "markdown": result.get("markdown"),
            "json": result.get("json"),
            "metadata": result.get("metadata", {})
        }
    
    async def _process_pdf_pymupdf(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF using PyMuPDF.
        
        Args:
            payload: Processing parameters
            
        Returns:
            Processing results
        """
        file_path = payload.get("file_path")
        extract_images = payload.get("extract_images", False)
        
        processor = self.processors["pymupdf"]
        
        # Process document
        result = await asyncio.to_thread(
            processor.process,
            file_path,
            extract_images=extract_images
        )
        
        return {
            "success": True,
            "text": result.get("text"),
            "markdown": result.get("markdown"),
            "metadata": result.get("metadata", {})
        }
    
    async def _process_docx(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process DOCX document.
        
        Args:
            payload: Processing parameters
            
        Returns:
            Processing results
        """
        file_path = payload.get("file_path")
        extract_styles = payload.get("extract_styles", True)
        
        processor = self.processors["docx"]
        
        # Process document
        result = await asyncio.to_thread(
            processor.process,
            file_path,
            extract_styles=extract_styles
        )
        
        return {
            "success": True,
            "markdown": result.get("markdown"),
            "html": result.get("html"),
            "metadata": result.get("metadata", {})
        }
    
    async def _process_pptx(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process PowerPoint presentation.
        
        Args:
            payload: Processing parameters
            
        Returns:
            Processing results
        """
        file_path = payload.get("file_path")
        extract_notes = payload.get("extract_notes", True)
        
        processor = self.processors["pptx"]
        
        # Process document
        result = await asyncio.to_thread(
            processor.process,
            file_path,
            extract_notes=extract_notes
        )
        
        return {
            "success": True,
            "markdown": result.get("markdown"),
            "text": result.get("text"),
            "slides": result.get("slides", []),
            "metadata": result.get("metadata", {})
        }
    
    async def _analyze_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document structure and content.
        
        Args:
            payload: Analysis parameters
            
        Returns:
            Analysis report
        """
        file_path = payload.get("file_path")
        document_content = payload.get("content")
        
        # Perform analysis
        analysis = {
            "file_info": {
                "path": file_path,
                "size": Path(file_path).stat().st_size if file_path else None,
                "type": Path(file_path).suffix if file_path else "unknown"
            },
            "content_analysis": {
                "word_count": len(document_content.split()) if document_content else 0,
                "character_count": len(document_content) if document_content else 0,
                "has_tables": False,  # Would need actual detection
                "has_images": False,  # Would need actual detection
                "language": "en"  # Would need language detection
            },
            "recommendations": []
        }
        
        # Add recommendations based on analysis
        if analysis["content_analysis"]["word_count"] > 10000:
            analysis["recommendations"].append("Consider chunking for better processing")
        
        if file_path and Path(file_path).suffix == ".pdf":
            analysis["recommendations"].append("Use Enhanced Docling for best results")
        
        return {
            "success": True,
            "analysis": analysis
        }