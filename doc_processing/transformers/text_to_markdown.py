"""Transform text documents to Markdown format."""
import datetime
import re
from typing import Any, Dict, List, Optional, Union
import logging
from pathlib import Path
import jinja2

from doc_processing.embedding.base import BaseTransformer # Corrected import path
from doc_processing.templates.prompt_manager import PromptTemplateManager
from doc_processing.config import get_settings

class TextToMarkdown(BaseTransformer):
    """Transform plain text to Markdown format."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize transformer.
        
        Args:
            config: Configuration options
        """
        super().__init__(config)
        self.settings = get_settings()
        
        # Get template manager
        template_dir = self.config.get('template_dir', self.settings.OUTPUT_TEMPLATE_DIR)
        self.template_manager = PromptTemplateManager(template_dir)
        
        # Template configuration
        self.markdown_template = self.config.get('markdown_template', 'markdown_template.j2')
        self.generate_toc = self.config.get('generate_toc', True)
        self.detect_headings = self.config.get('detect_headings', True)
        self.extract_metadata = self.config.get('extract_metadata', True)
        
    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform text document to Markdown.
        
        Args:
            document: Document to transform
            
        Returns:
            Document with added markdown content
        """
        if not document.get('content'):
            self.logger.warning(f"Document has no content to transform")
            document['markdown'] = ""
            return document
        
        try:
            content = document.get('content', '')
            title = self._extract_title(document)
            
            # Process content
            processed_content = self._process_content(content)
            
            # Extract sections and headings
            sections, headings = self._extract_sections(processed_content)
            
            # Generate table of contents if needed
            toc = self._generate_toc(headings) if self.generate_toc else ""
            
            # Create markdown using template
            context = {
                'title': title,
                'toc': toc,
                'content': processed_content,
                'sections': sections,
                'metadata': document.get('metadata', {}),
                'document': document,
                'now': datetime.datetime.now() # Add current timestamp
            }
            
            try:
                # Use template if available
                markdown = self.template_manager.render_output(self.markdown_template, context)
            except jinja2.exceptions.TemplateNotFound:
                # Fallback if template not found
                self.logger.warning(f"Markdown template not found: {self.markdown_template}")
                markdown = self._generate_default_markdown(context)
            
            # Add markdown to document
            document['markdown'] = markdown
            
            # Save to file if output_path is provided
            output_path = self.config.get('output_path')
            if output_path:
                self._save_markdown(markdown, output_path, document)
            
            return document
            
        except Exception as e:
            self.logger.error(f"Error transforming document to markdown: {str(e)}")
            document['error'] = f"Markdown transformation error: {str(e)}"
            document['markdown'] = ""
            return document
    
    def _extract_title(self, document: Dict[str, Any]) -> str:
        """Extract title from document.
        
        Args:
            document: Document to extract title from
            
        Returns:
            Document title
        """
        # Try to get title from metadata
        if 'metadata' in document:
            metadata = document['metadata']
            if 'title' in metadata and metadata['title']:
                return metadata['title']
            if 'filename' in metadata and metadata['filename']:
                # Convert filename to title (remove extension, replace underscores)
                filename = metadata['filename']
                title = Path(filename).stem
                title = title.replace('_', ' ').replace('-', ' ')
                return title.title()  # Capitalize words
        
        # Try to extract from content
        content = document.get('content', '')
        if content:
            # Try to find a title pattern in the first 20 lines
            lines = content.split('\n')[:20]
            
            # Check for centered lines that might be titles
            for line in lines:
                line = line.strip()
                if line and line.isupper() and len(line) > 3:
                    return line
                    
            # Use first non-empty line as title
            for line in lines:
                line = line.strip()
                if line:
                    # Limit length
                    if len(line) > 80:
                        line = line[:77] + '...'
                    return line
        
        # Default title if nothing found
        return "Untitled Document"
    
    def _process_content(self, content: str) -> str:
        """Process content for markdown conversion.
        
        Args:
            content: Text content
            
        Returns:
            Processed content
        """
        # Remove excessive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        if self.detect_headings:
            # Detect and convert likely headings
            lines = content.split('\n')
            processed_lines = []
            prev_line_empty = True
            
            for i, line in enumerate(lines):
                # Check if this line might be a heading
                stripped = line.strip()
                
                if stripped and prev_line_empty:
                    # Check for heading patterns
                    is_heading = False
                    
                    # All uppercase with no punctuation at end
                    if stripped.isupper() and not stripped[-1] in '.,:;!?':
                        is_heading = True
                        processed_lines.append(f"## {stripped}")
                    
                    # Numbered headings like "1. Section Title"
                    elif re.match(r'^\d+\.\s+\w+', stripped) and len(stripped) < 100:
                        is_heading = True
                        processed_lines.append(f"## {stripped}")
                        
                    # Short line followed by an empty line (potential heading)
                    elif i < len(lines) - 1 and not lines[i+1].strip() and len(stripped) < 80:
                        # Check if next non-empty line has indent (suggests this is a heading)
                        next_non_empty = None
                        for j in range(i+2, min(i+10, len(lines))):
                            if lines[j].strip():
                                next_non_empty = lines[j]
                                break
                                
                        if next_non_empty and (next_non_empty.startswith('  ') or next_non_empty.startswith('\t')):
                            is_heading = True
                            processed_lines.append(f"## {stripped}")
                    
                    if not is_heading:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
                
                prev_line_empty = not stripped
            
            content = '\n'.join(processed_lines)
        
        return content
    
    def _extract_sections(self, content: str) -> tuple:
        """Extract sections and headings from content.
        
        Args:
            content: Text content
            
        Returns:
            Tuple of (sections list, headings list)
        """
        lines = content.split('\n')
        sections = []
        headings = []
        
        current_heading = None
        current_section = []
        
        for line in lines:
            # Check if line is a markdown heading
            heading_match = re.match(r'^(#{1,6})\s+(.*?)$', line)
            
            if heading_match:
                # Save previous section if it exists
                if current_section:
                    sections.append({
                        'heading': current_heading,
                        'content': '\n'.join(current_section)
                    })
                
                heading_level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                
                current_heading = {
                    'level': heading_level,
                    'text': heading_text
                }
                headings.append(current_heading)
                
                current_section = []
            else:
                current_section.append(line)
        
        # Add the last section
        if current_section:
            sections.append({
                'heading': current_heading,
                'content': '\n'.join(current_section)
            })
        
        return sections, headings
    
    def _generate_toc(self, headings: List[Dict[str, Any]]) -> str:
        """Generate table of contents from headings.
        
        Args:
            headings: List of heading objects
            
        Returns:
            Markdown table of contents
        """
        if not headings:
            return ""
        
        toc_lines = ["## Table of Contents\n"]
        
        for heading in headings:
            if not heading:
                continue
                
            level = heading.get('level', 2)
            text = heading.get('text', '')
            
            # Create TOC link
            anchor = text.lower().replace(' ', '-').replace('.', '').replace(',', '')
            anchor = re.sub(r'[^\w\-]', '', anchor)
            
            # Calculate indentation based on heading level
            indent = '  ' * (level - 1)
            
            toc_lines.append(f"{indent}- [{text}](#{anchor})")
        
        return '\n'.join(toc_lines)
    
    def _generate_default_markdown(self, context: Dict[str, Any]) -> str:
        """Generate default markdown without template.
        
        Args:
            context: Template context
            
        Returns:
            Generated markdown
        """
        title = context.get('title', 'Untitled Document')
        toc = context.get('toc', '')
        content = context.get('content', '')
        
        parts = [
            f"# {title}\n",
        ]
        
        # Add metadata if available
        metadata = context.get('metadata', {})
        if metadata and self.extract_metadata:
            parts.append("## Metadata\n")
            for key, value in metadata.items():
                if key not in ['content', 'chunks'] and value is not None:
                    parts.append(f"- **{key}**: {value}")
            parts.append("\n")
        
        # Add TOC if available
        if toc:
            parts.append(f"{toc}\n")
        
        # Add content
        parts.append(content)
        
        return '\n'.join(parts)
    
    def _save_markdown(self, markdown: str, output_path: Union[str, Path], document: Dict[str, Any]) -> None:
        """Save markdown to file.
        
        Args:
            markdown: Markdown content
            output_path: Path to save file
            document: Document data
            
        Raises:
            Exception: If error saving file
        """
        try:
            # If output_path is a directory, create a filename
            path = Path(output_path)
            
            if path.is_dir():
                # Generate filename from document metadata
                if 'metadata' in document and 'filename' in document['metadata']:
                    filename = Path(document['metadata']['filename']).stem + '.md'
                else:
                    filename = f"document_{document.get('id', 'untitled')}.md"
                path = path / filename
            
            # Make sure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(markdown)
                
            self.logger.info(f"Saved markdown to {path}")
            
        except Exception as e:
            self.logger.error(f"Error saving markdown file: {str(e)}")
            raise