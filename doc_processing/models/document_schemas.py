"""Pydantic models for document processing."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class Author(BaseModel):
    """Document author information."""
    name: str = Field(description="Full name of the author")
    affiliation: Optional[str] = Field(None, description="Organization or institution the author is affiliated with")
    email: Optional[str] = Field(None, description="Author's email address if available")


class Section(BaseModel):
    """Document section information."""
    title: str = Field(description="Title or heading of the section")
    content: str = Field(description="Text content of the section")
    level: int = Field(1, description="Heading level (1 for main heading, 2 for subheading, etc.)")


class TableData(BaseModel):
    """Structured table data."""
    title: Optional[str] = Field(None, description="Title or caption of the table")
    headers: List[str] = Field(description="Column headers of the table")
    rows: List[List[str]] = Field(description="Data rows of the table")
    page_number: Optional[int] = Field(None, description="Page number where the table appears")


class DocumentStructure(BaseModel):
    """Structured document information."""
    title: str = Field(description="Title of the document")
    authors: List[Author] = Field(default_factory=list, description="Authors of the document")
    abstract: Optional[str] = Field(None, description="Document abstract or summary")
    keywords: List[str] = Field(default_factory=list, description="Keywords or tags related to the document")
    publication_date: Optional[str] = Field(None, description="Publication date of the document")
    sections: List[Section] = Field(default_factory=list, description="Document sections")
    tables: List[TableData] = Field(default_factory=list, description="Tables in the document")
    references: List[str] = Field(default_factory=list, description="References or citations")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Machine Learning Approaches for Natural Language Processing",
                    "authors": [
                        {"name": "Jane Smith", "affiliation": "University of AI", "email": "jane@example.com"}
                    ],
                    "abstract": "This paper explores recent advances in machine learning for NLP.",
                    "keywords": ["machine learning", "natural language processing", "deep learning"],
                    "publication_date": "2023-05-15",
                    "sections": [
                        {"title": "Introduction", "content": "This paper introduces...", "level": 1}
                    ],
                    "tables": [
                        {
                            "title": "Model Comparison",
                            "headers": ["Model", "Accuracy", "F1-Score"],
                            "rows": [["BERT", "95%", "0.92"], ["GPT", "93%", "0.90"]],
                            "page_number": 3
                        }
                    ],
                    "references": ["Smith et al. (2022). Deep Learning for NLP."]
                }
            ]
        }
    )