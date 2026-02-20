"""Configuration settings for document processing pipeline."""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from centralized API key store
MASTER_ENV_PATH = Path.home() / '.config' / 'api-keys' / '.env.master'
if MASTER_ENV_PATH.exists():
    load_dotenv(dotenv_path=MASTER_ENV_PATH, override=False)

# Calculate base paths beforehand
_base_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_data_dir_path = os.path.join(_base_dir_path, 'data')
_input_dir_path = os.path.join(_data_dir_path, 'input')
_output_dir_path = os.path.join(_data_dir_path, 'output')
_temp_dir_path = os.path.join(_data_dir_path, 'temp')

class Settings(BaseSettings):
    """Application settings."""
    
    # Base directories
    BASE_DIR: str = Field(default=_base_dir_path)
    DATA_DIR: str = Field(default=_data_dir_path)
    INPUT_DIR: str = Field(default=_input_dir_path)
    OUTPUT_DIR: str = Field(default=_output_dir_path)
    TEMP_DIR: str = Field(default=_temp_dir_path)
    
    # Input subdirectories by file type
    PDF_INPUT_DIR: str = Field(default=os.path.join(_input_dir_path, 'pdfs'))
    TEXT_INPUT_DIR: str = Field(default=os.path.join(_input_dir_path, 'text'))
    MARKDOWN_INPUT_DIR: str = Field(default=os.path.join(_input_dir_path, 'markdown'))
    IMAGE_INPUT_DIR: str = Field(default=os.path.join(_input_dir_path, 'images'))
    AUDIO_INPUT_DIR: str = Field(default=os.path.join(_input_dir_path, 'audio'))
    VIDEO_INPUT_DIR: str = Field(default=os.path.join(_input_dir_path, 'video'))
    JSON_INPUT_DIR: str = Field(default=os.path.join(_input_dir_path, 'json'))
    
    # Output subdirectories by file type
    TEXT_OUTPUT_DIR: str = Field(default=os.path.join(_output_dir_path, 'text'))
    MARKDOWN_OUTPUT_DIR: str = Field(default=os.path.join(_output_dir_path, 'markdown'))
    JSON_OUTPUT_DIR: str = Field(default=os.path.join(_output_dir_path, 'json'))
    
    # Template directories
    TEMPLATE_DIR: str = Field(default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'prompts'))
    OUTPUT_TEMPLATE_DIR: str = Field(default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'outputs'))
    
    # API Keys
    OPENAI_API_KEY: str = Field(default=os.getenv('OPENAI_API_KEY', ''))
# Add potentially missing API keys from .env
    OPENAI_APIKEY: Optional[str] = Field(default=os.getenv('OPENAI_APIKEY', '')) # Note: Potential typo in .env? OPENAI_API_KEY exists.
    ANTHROPIC_API_KEY: Optional[str] = Field(default=os.getenv('ANTHROPIC_API_KEY', ''))
    GEMINI_API_KEY: Optional[str] = Field(default=os.getenv('GEMINI_API_KEY', ''))
    DEEPSEEK_API_KEY: Optional[str] = Field(default=os.getenv('DEEPSEEK_API_KEY', ''))
    ELEVEN_LABS_API_KEY: Optional[str] = Field(default=os.getenv('ELEVEN_LABS_API_KEY', ''))
    BSA_API_KEY: Optional[str] = Field(default=os.getenv('BSA_API_KEY', ''))
    SUPABASE_API_KEY: Optional[str] = Field(default=os.getenv('SUPABASE_API_KEY', ''))
    WOLFRAM_API_KEY: Optional[str] = Field(default=os.getenv('WOLFRAM_API_KEY', ''))
    OPENROUTER_API_KEY: Optional[str] = Field(default=os.getenv('OPENROUTER_API_KEY', ''))
    GROQ_API_KEY: Optional[str] = Field(default=os.getenv('GROQ_API_KEY', ''))
    PERPLEXITY_API_KEY: Optional[str] = Field(default=os.getenv('PERPLEXITY_API_KEY', ''))
    GOOGLE_API_KEY: Optional[str] = Field(default=os.getenv('GOOGLE_API_KEY', ''))
    DEEPGRAM_API_KEY: Optional[str] = Field(default=os.getenv('DEEPGRAM_API_KEY', ''))
    REPLICATE_API_KEY: Optional[str] = Field(default=os.getenv('REPLICATE_API_KEY', ''))
    FRIENDLI_TOKEN: Optional[str] = Field(default=os.getenv('FRIENDLI_TOKEN', ''))
    HF_TOKEN: Optional[str] = Field(default=os.getenv('HF_TOKEN', ''))
    SMITHERY_API_TOKEN: Optional[str] = Field(default=os.getenv('SMITHERY_API_TOKEN', ''))
    GIT_HUB_TOKEN: Optional[str] = Field(default=os.getenv('GIT_HUB_TOKEN', ''))
    # Processing configuration
    MAX_RETRIES: int = Field(default=3)
    CONCURRENT_TASKS: int = Field(default=4)
    
    # Models configuration
    # OpenAI
    DEFAULT_OPENAI_EMBEDDING_MODEL: str = Field(default='text-embedding-ada-002', alias='DEFAULT_EMBEDDING_MODEL') # Keep alias for backward compat?
    DEFAULT_OPENAI_VISION_MODEL: str = Field(default='gpt-4.1', alias='DEFAULT_VISION_MODEL') # Assuming gpt-4.1 handles vision, adjust if needed
    DEFAULT_OPENAI_CHAT_MODEL: str = Field(default='gpt-4.1', alias='DEFAULT_CHAT_MODEL')
    # Anthropic
    DEFAULT_ANTHROPIC_MODEL: str = Field(default='claude-3-opus-20240229')
    # Google Gemini
    DEFAULT_GEMINI_MODEL: str = Field(default='gemini-1.5-pro-latest') # Or 'gemini-pro-vision' for vision
    # DeepSeek
    DEFAULT_DEEPSEEK_MODEL: str = Field(default='deepseek-chat') # Or 'deepseek-coder'
    
    # Other settings
    LOG_LEVEL: str = Field(default='INFO')
    PROGRESS_FILE: str = Field(default='processing_progress.txt')
    
    # Remove env_file loading for this specific Settings class
    model_config = SettingsConfigDict(
        # env_file='.env', # Removed
        case_sensitive=True,
        extra='ignore' # Explicitly keep ignore, though it should be default
    )

    # PDF Processor Configuration
    PDF_PROCESSOR_STRATEGY: str = Field(
        default="exclusive",
        description="Processing strategy: 'exclusive' (choose one) or 'fallback_chain'"
    )
    ACTIVE_PDF_PROCESSORS: list[str] = Field(
        default=["docling", "enhanced_docling", "gemini", "gpt", "pymupdf", "claude"],
        description="Ordered list of enabled processors: docling (FREE), enhanced_docling, gemini (cheap), gpt, pymupdf, claude (opt-in with API key)"
    )
    DEFAULT_PDF_PROCESSOR: str = Field(
        default="enhanced_docling",
        description="Default processor for 'exclusive' strategy (enhanced_docling is FREE and excellent)"
    )
    PDF_FALLBACK_ORDER: list[str] = Field(
        default=["enhanced_docling", "docling", "gemini"],
        description="Fallback order (FREE first, then cheap options). Claude removed to avoid API costs - use explicitly if needed"
    )

    @validator('PDF_PROCESSOR_STRATEGY')
    def validate_strategy(cls, v):
        if v not in ['exclusive', 'fallback_chain']:
            raise ValueError("Invalid strategy. Choose 'exclusive' or 'fallback_chain'")
        return v

    @validator('ACTIVE_PDF_PROCESSORS')
    def validate_active_processors(cls, v):
        valid = {'claude', 'pymupdf', 'docling', 'enhanced_docling', 'gpt', 'gemini'}
        if not set(v).issubset(valid):
            raise ValueError(f"Invalid processors. Valid options: {valid}")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()


def get_file_type_config(file_type: str) -> Dict[str, Any]:
    """Get configuration for specific file type.

    Args:
        file_type: File type (pdf, text, markdown, etc.)

    Returns:
        Dictionary with file type configuration
    """
    settings = get_settings()

    # Common configuration
    config = {
        'max_retries': settings.MAX_RETRIES,
        'concurrent_tasks': settings.CONCURRENT_TASKS,
    }

    # File type specific configuration
    if file_type == 'pdf':
        config.update({
            'input_dir': settings.PDF_INPUT_DIR,
            'output_dir': settings.TEXT_OUTPUT_DIR,
            # Remove vision_model and prompt_template from here,
            # as they are now handled by the specific PDF processors
            # 'vision_model': settings.DEFAULT_VISION_MODEL,
            # 'prompt_template': 'pdf_extraction.j2',
            # Add new PDF processor specific settings
            'pdf_processor_strategy': settings.PDF_PROCESSOR_STRATEGY,
            'active_pdf_processors': settings.ACTIVE_PDF_PROCESSORS,
            'default_pdf_processor': settings.DEFAULT_PDF_PROCESSOR,
            'pdf_fallback_order': settings.PDF_FALLBACK_ORDER,
        })
    elif file_type == 'text':
        config.update({
            'input_dir': settings.TEXT_INPUT_DIR,
            'output_dir': settings.TEXT_OUTPUT_DIR,
        })
    elif file_type == 'markdown':
        config.update({
            'input_dir': settings.MARKDOWN_INPUT_DIR,
            'output_dir': settings.MARKDOWN_OUTPUT_DIR,
        })
    elif file_type == 'image':
        config.update({
            'input_dir': settings.IMAGE_INPUT_DIR,
            'output_dir': settings.TEXT_OUTPUT_DIR,
            'vision_model': settings.DEFAULT_VISION_MODEL,
            'prompt_template': 'image_extraction.j2',
        })
    elif file_type == 'audio':
        config.update({
            'input_dir': settings.AUDIO_INPUT_DIR,
            'output_dir': settings.TEXT_OUTPUT_DIR,
        })
    elif file_type == 'video':
        config.update({
            'input_dir': settings.VIDEO_INPUT_DIR,
            'output_dir': settings.TEXT_OUTPUT_DIR,
        })
    elif file_type == 'json':
        config.update({
            'input_dir': settings.JSON_INPUT_DIR,
            'output_dir': settings.JSON_OUTPUT_DIR,
        })

    return config


def ensure_directories_exist() -> None:
    """Create all necessary directories if they don't exist."""
    settings = get_settings()

    # Create base directories
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.INPUT_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)

    # Create input subdirectories
    os.makedirs(settings.PDF_INPUT_DIR, exist_ok=True)
    os.makedirs(settings.TEXT_INPUT_DIR, exist_ok=True)
    os.makedirs(settings.MARKDOWN_INPUT_DIR, exist_ok=True)
    os.makedirs(settings.IMAGE_INPUT_DIR, exist_ok=True)
    os.makedirs(settings.AUDIO_INPUT_DIR, exist_ok=True)
    os.makedirs(settings.VIDEO_INPUT_DIR, exist_ok=True)
    os.makedirs(settings.JSON_INPUT_DIR, exist_ok=True)

    # Create output subdirectories
    os.makedirs(settings.TEXT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(settings.MARKDOWN_OUTPUT_DIR, exist_ok=True)
    os.makedirs(settings.JSON_OUTPUT_DIR, exist_ok=True)
    # Add these new settings to your existing config

DOCLING_ENABLED: bool = Field(default=True)
DOCLING_USE_EASYOCR: bool = Field(default=True)
DOCLING_EXTRACT_TABLES: bool = Field(default=True)
DOCLING_EXTRACT_FIGURES: bool = Field(default=True)
