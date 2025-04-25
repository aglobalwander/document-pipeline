"""Pydantic models for document processing."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Document metadata."""
    filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    title: Optional[str] = None
    author: Optional[str] = None
    num_pages: Optional[int] = None
    num_processed_pages: Optional[int] = None


class PageContent(BaseModel):
    """Content of a single page."""
    page_number: int
    text: str = Field(description="Extracted text content of the page")
    

class TableCell(BaseModel):
    """Single cell in a table."""
    text: str
    row_index: int
    col_index: int
    

class Table(BaseModel):
    """Structured table data."""
    table_index: int
    page_number: Optional[int] = None
    rows: List[List[str]] = Field(description="Table data as a list of rows, where each row is a list of cell text values")
    

class DocumentChunk(BaseModel):
    """Chunk of document content."""
    content: str = Field(description="Text content of the chunk")
    chunk_index: int
    document_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Processed document."""
    id: Optional[str] = None
    source_path: str
    content: str = Field(description="Full text content of the document")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    pages: List[PageContent] = Field(default_factory=list)
    tables: Optional[List[Table]] = None
    chunks: Optional[List[DocumentChunk]] = None
    error: Optional[str] = None
    
    @field_validator('content')
    def validate_content_not_empty(cls, v):
        """Validate that content is not empty."""
        if not v:
            raise ValueError("Document content cannot be empty")
        return v