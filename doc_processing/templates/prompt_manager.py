"""Jinja2 template manager for prompts and output formatting."""
import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import jinja2
import logging

from doc_processing.config import get_settings

class PromptTemplateManager:
    """Manage Jinja2 templates for prompts and output formatting."""
    
    def __init__(self, template_dir: Optional[Union[str, Path]] = None):
        """Initialize template manager.
        
        Args:
            template_dir: Directory containing template files (optional)
        """
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Set up template directory
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(self.settings.TEMPLATE_DIR)
            
        # Set up output template directory
        self.output_template_dir = Path(self.settings.OUTPUT_TEMPLATE_DIR)
        
        # Initialize Jinja environments
        self.prompt_env = self._create_jinja_env(self.template_dir)
        self.output_env = self._create_jinja_env(self.output_template_dir)
    
    def _create_jinja_env(self, template_dir: Path) -> jinja2.Environment:
        """Create Jinja2 environment.
        
        Args:
            template_dir: Directory containing template files
            
        Returns:
            Configured Jinja2 environment
        """
        if not template_dir.exists():
            self.logger.warning(f"Template directory does not exist: {template_dir}")
            os.makedirs(template_dir, exist_ok=True)
            
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render_prompt(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render prompt template with context.
        
        Args:
            template_name: Name of template file
            context: Dictionary of context variables for template
            
        Returns:
            Rendered prompt text
            
        Raises:
            jinja2.exceptions.TemplateNotFound: If template file not found
            jinja2.exceptions.TemplateError: If error rendering template
        """
        try:
            template = self.prompt_env.get_template(template_name)
            return template.render(**context)
        except jinja2.exceptions.TemplateNotFound:
            self.logger.error(f"Prompt template not found: {template_name}")
            raise
        except Exception as e:
            self.logger.error(f"Error rendering prompt template {template_name}: {str(e)}")
            raise
    
    def render_output(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render output template with context.
        
        Args:
            template_name: Name of template file
            context: Dictionary of context variables for template
            
        Returns:
            Rendered output text
            
        Raises:
            jinja2.exceptions.TemplateNotFound: If template file not found
            jinja2.exceptions.TemplateError: If error rendering template
        """
        try:
            template = self.output_env.get_template(template_name)
            return template.render(**context)
        except jinja2.exceptions.TemplateNotFound:
            self.logger.error(f"Output template not found: {template_name}")
            raise
        except Exception as e:
            self.logger.error(f"Error rendering output template {template_name}: {str(e)}")
            raise
    
    def list_prompt_templates(self) -> List[str]:
        """List available prompt templates.
        
        Returns:
            List of template file names
        """
        return self.prompt_env.list_templates()
    
    def list_output_templates(self) -> List[str]:
        """List available output templates.
        
        Returns:
            List of template file names
        """
        return self.output_env.list_templates()
    
    def create_prompt_template(self, template_name: str, content: str) -> None:
        """Create a new prompt template.
        
        Args:
            template_name: Name of template file
            content: Template content
            
        Raises:
            FileExistsError: If template file already exists
        """
        template_path = self.template_dir / template_name
        if template_path.exists():
            raise FileExistsError(f"Template already exists: {template_name}")
            
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Created prompt template: {template_name}")
    
    def create_output_template(self, template_name: str, content: str) -> None:
        """Create a new output template.
        
        Args:
            template_name: Name of template file
            content: Template content
            
        Raises:
            FileExistsError: If template file already exists
        """
        template_path = self.output_template_dir / template_name
        if template_path.exists():
            raise FileExistsError(f"Template already exists: {template_name}")
            
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Created output template: {template_name}")
    
    def update_prompt_template(self, template_name: str, content: str) -> None:
        """Update an existing prompt template.
        
        Args:
            template_name: Name of template file
            content: Template content
            
        Raises:
            FileNotFoundError: If template file not found
        """
        template_path = self.template_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
            
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Updated prompt template: {template_name}")
    
    def update_output_template(self, template_name: str, content: str) -> None:
        """Update an existing output template.
        
        Args:
            template_name: Name of template file
            content: Template content
            
        Raises:
            FileNotFoundError: If template file not found
        """
        template_path = self.output_template_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
            
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Updated output template: {template_name}")