# PDF/Vision/OCR Stack Enhancement Plan

**Date**: 2025-11-15
**Goal**: Evolve the PDF/vision/OCR stack with Milvus-first ETL approach
**Scope**: Add Kimi/Qwen multimodal support, provider-agnostic processing, intelligent routing

---

## Overview

Enhance the document processing pipeline to support multiple multimodal LLM providers (Kimi, Qwen, OpenAI, Gemini) with intelligent routing, language detection, and cost optimization while maintaining pure ETL focus (no vector database dependencies).

### Core Principles

1. **Pure ETL**: Pipeline produces clean outputs (text, markdown, JSON) for downstream systems
2. **Provider Agnostic**: Easy to swap/add new multimodal providers
3. **Cost Optimization**: Route only hard pages to expensive models
4. **Language Aware**: Auto-detect and route to best model per language
5. **Resumable**: Cache support for all processors
6. **CLI First**: All options exposed through command-line flags

---

## Enhancement Roadmap

### Phase 1: LLM Client Abstraction

**Goal**: Create unified interface for multimodal LLM providers

#### 1.1 Add New LLM Clients

**File**: `doc_processing/llm/clients.py`

**Clients to Add**:
- `KimiClient`: Moonshot AI's Kimi multimodal models
- `QwenClient`: Alibaba's Qwen-VL multimodal models

**Structure** (mirror existing `OpenAIClient`, `GeminiClient`):

```python
class BaseMultimodalClient(ABC):
    """Base class for multimodal LLM clients."""

    @abstractmethod
    def process_image(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        """Process single image with prompt."""
        pass

    @abstractmethod
    def process_pdf_page(self, page_image: bytes, page_num: int, **kwargs) -> str:
        """Process single PDF page as image."""
        pass

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """Check if client has strong support for given language."""
        pass

class KimiClient(BaseMultimodalClient):
    """Moonshot AI Kimi multimodal client."""

    def __init__(self, api_key: str = None, model: str = "moonshot-v1-vision"):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        self.model = model
        self.base_url = "https://api.moonshot.cn/v1"

    def process_image(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        # Implementation using Kimi API
        pass

    def supports_language(self, language: str) -> bool:
        # Kimi has strong Chinese support
        return language in ['zh', 'zh-CN', 'zh-TW', 'en']

class QwenClient(BaseMultimodalClient):
    """Alibaba Qwen-VL multimodal client."""

    def __init__(self, api_key: str = None, model: str = "qwen-vl-max"):
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"

    def process_image(self, image_bytes: bytes, prompt: str, **kwargs) -> str:
        # Implementation using Qwen API
        pass

    def supports_language(self, language: str) -> bool:
        # Qwen excels at Chinese
        return language in ['zh', 'zh-CN', 'zh-TW', 'en', 'ja', 'ko']
```

**Configuration** (`doc_processing/config.py`):

```python
# Add to Settings class
KIMI_API_KEY: Optional[str] = Field(None, env='KIMI_API_KEY')
KIMI_MODEL: str = Field('moonshot-v1-vision', env='KIMI_MODEL')

QWEN_API_KEY: Optional[str] = Field(None, env='QWEN_API_KEY')
QWEN_MODEL: str = Field('qwen-vl-max', env='QWEN_MODEL')

# Provider preferences
VISION_PROVIDER: str = Field('openai', env='VISION_PROVIDER')  # openai, kimi, qwen, gemini
VISION_FALLBACK_ORDER: List[str] = ['enhanced_docling', 'kimi', 'qwen', 'openai']
```

---

### Phase 2: Provider-Agnostic PDF Processors

**Goal**: Make PDF processors work with any multimodal provider

#### 2.1 Refactor GPTPVisionProcessor

**Current**: Hardcoded to OpenAI
**Target**: Parameterized to use any multimodal client

**File**: `doc_processing/processors/gpt_vision_processor.py`

**Rename**: `GPTPVisionProcessor` → `MultimodalVisionProcessor`

```python
class MultimodalVisionProcessor(BaseProcessor):
    """Provider-agnostic vision-based PDF processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Get provider from config
        provider = self.config.get('vision_provider', 'openai')

        # Initialize appropriate client
        self.client = self._initialize_client(provider)
        self.provider_name = provider

    def _initialize_client(self, provider: str) -> BaseMultimodalClient:
        """Initialize multimodal client based on provider."""
        clients = {
            'openai': OpenAIClient,
            'kimi': KimiClient,
            'qwen': QwenClient,
            'gemini': GeminiClient
        }

        if provider not in clients:
            raise ValueError(f"Unknown provider: {provider}")

        return clients[provider]()

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF using configured multimodal provider."""
        # Existing logic but using self.client instead of hardcoded OpenAI
        pass
```

#### 2.2 Create Provider-Specific Processors

**Files**:
- `doc_processing/processors/kimi_pdf_processor.py`
- `doc_processing/processors/qwen_pdf_processor.py`

```python
class KimiPDFProcessor(MultimodalVisionProcessor):
    """Kimi-specific PDF processor with optimizations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        config['vision_provider'] = 'kimi'
        super().__init__(config)

class QwenPDFProcessor(MultimodalVisionProcessor):
    """Qwen-specific PDF processor with optimizations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        config['vision_provider'] = 'qwen'
        super().__init__(config)
```

#### 2.3 Register Processors in PDFProcessor

**File**: `doc_processing/processors/pdf_processor.py`

```python
def _initialize_processors(self):
    """Initialize all available PDF processors."""
    processors = {
        'enhanced_docling': EnhancedDoclingPDFProcessor,
        'docling': DoclingPDFProcessor,
        'pymupdf': PyMuPDFProcessor,
        'claude': ClaudePDFProcessor,
        'kimi': KimiPDFProcessor,      # NEW
        'qwen': QwenPDFProcessor,      # NEW
        'openai': MultimodalVisionProcessor,  # Renamed from GPTPVisionProcessor
        'gemini': GeminiPDFProcessor,
    }

    # ... rest of initialization
```

---

### Phase 3: Intelligent Page-Level Routing

**Goal**: Only send hard pages to expensive OCR models

#### 3.1 Page Difficulty Detection

**File**: `doc_processing/utils/page_analyzer.py` (NEW)

```python
class PageDifficultyAnalyzer:
    """Analyze PDF pages to determine OCR difficulty."""

    @staticmethod
    def analyze_page(page_image: bytes, ocr_confidence: float = None) -> Dict[str, Any]:
        """
        Analyze a page to determine if it needs expensive OCR.

        Returns:
            {
                'needs_vision_ocr': bool,
                'difficulty_score': float,  # 0.0-1.0
                'reasons': List[str],
                'recommended_processor': str
            }
        """
        needs_vision = False
        reasons = []
        difficulty = 0.0

        # Heuristics:
        # 1. Low OCR confidence from PyMuPDF/Docling
        if ocr_confidence and ocr_confidence < 0.7:
            needs_vision = True
            difficulty += 0.4
            reasons.append("Low OCR confidence")

        # 2. Detect if page is primarily image-based
        # (could use image analysis here)

        # 3. Detect complex layouts, tables, charts
        # (could use layout analysis)

        # 4. Detect non-Latin scripts without embedded text
        # (could use script detection)

        # Determine recommended processor
        if difficulty > 0.7:
            recommended = 'kimi' if is_chinese(page_image) else 'openai'
        elif difficulty > 0.4:
            recommended = 'qwen'
        else:
            recommended = 'enhanced_docling'

        return {
            'needs_vision_ocr': needs_vision,
            'difficulty_score': difficulty,
            'reasons': reasons,
            'recommended_processor': recommended
        }
```

#### 3.2 Hybrid Processing Strategy

**File**: `doc_processing/processors/hybrid_pdf_processor.py` (NEW)

```python
class HybridPDFProcessor(BaseProcessor):
    """
    Intelligent hybrid PDF processor.

    1. Try fast/free processor (Docling/PyMuPDF) first
    2. Analyze page quality
    3. Route hard pages to appropriate vision model
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Initialize processors
        self.fast_processor = EnhancedDoclingPDFProcessor(config)
        self.vision_processors = {
            'kimi': KimiPDFProcessor(config),
            'qwen': QwenPDFProcessor(config),
            'openai': MultimodalVisionProcessor(config)
        }

        self.analyzer = PageDifficultyAnalyzer()
        self.cache = ProcessingCache() if config.get('use_cache') else None

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process with intelligent routing."""

        # Step 1: Fast processing with Docling
        result = self.fast_processor.process(document)

        # Step 2: Analyze each page
        pages_to_reprocess = []

        for page in result.get('pages', []):
            analysis = self.analyzer.analyze_page(
                page.get('image_bytes'),
                page.get('ocr_confidence')
            )

            if analysis['needs_vision_ocr']:
                pages_to_reprocess.append({
                    'page_num': page['page_number'],
                    'recommended_processor': analysis['recommended_processor'],
                    'reasons': analysis['reasons']
                })

        # Step 3: Reprocess hard pages with vision models
        if pages_to_reprocess:
            logger.info(f"Reprocessing {len(pages_to_reprocess)} pages with vision models")

            for page_info in pages_to_reprocess:
                processor_name = page_info['recommended_processor']
                processor = self.vision_processors.get(processor_name)

                if processor:
                    # Reprocess just this page
                    page_result = processor.process_page(
                        document['source_path'],
                        page_info['page_num']
                    )

                    # Update result with better OCR
                    self._update_page_in_result(result, page_info['page_num'], page_result)

        return result
```

---

### Phase 4: Language Detection & Auto-Routing

**Goal**: Automatically select best model based on document language

#### 4.1 Language Detector

**File**: `doc_processing/utils/language_detector.py` (NEW)

```python
import langdetect
from typing import Dict, List

class LanguageDetector:
    """Detect language of documents and recommend best processor."""

    # Language -> Best processor mapping
    PROCESSOR_STRENGTHS = {
        'zh': ['qwen', 'kimi', 'openai'],    # Chinese
        'ja': ['qwen', 'openai'],             # Japanese
        'ko': ['qwen', 'openai'],             # Korean
        'ar': ['openai', 'gemini'],           # Arabic
        'en': ['openai', 'gemini', 'kimi'],  # English
        # ... more languages
    }

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect language from text sample."""
        try:
            return langdetect.detect(text)
        except:
            return 'en'  # Default to English

    @classmethod
    def recommend_processor(cls, language: str, available_providers: List[str]) -> str:
        """Recommend best processor for detected language."""

        # Get processors good at this language
        preferred = cls.PROCESSOR_STRENGTHS.get(language, ['openai'])

        # Return first available from preferred list
        for processor in preferred:
            if processor in available_providers:
                return processor

        # Fallback to first available
        return available_providers[0] if available_providers else 'enhanced_docling'
```

#### 4.2 Auto-Routing in PDFProcessor

**File**: `doc_processing/processors/pdf_processor.py`

```python
def _select_processor(self, document: Dict[str, Any]) -> BaseProcessor:
    """Select processor based on language detection."""

    # If user specified a processor, use that
    if self.config.get('force_processor'):
        return self.processors[self.config['force_processor']]

    # Try to detect language from first page
    if 'pages' in document and document['pages']:
        first_page_text = document['pages'][0].get('text', '')[:500]
        detected_lang = LanguageDetector.detect_language(first_page_text)

        logger.info(f"Detected language: {detected_lang}")

        # Get available providers with API keys
        available = self._get_available_providers()

        # Get recommended processor for this language
        recommended = LanguageDetector.recommend_processor(detected_lang, available)

        logger.info(f"Recommended processor for {detected_lang}: {recommended}")

        return self.processors[recommended]

    # Fallback to default strategy
    return self._get_default_processor()
```

---

### Phase 5: ProcessingCache Integration

**Goal**: Wire caching into all new processors

#### 5.1 Update Cache to Support Multiple Processors

**File**: `doc_processing/utils/processing_cache.py`

```python
class ProcessingCache:
    """Enhanced cache supporting multiple processors."""

    def _generate_cache_key(self, doc_id: str, processor_name: str) -> str:
        """Generate cache key including processor name."""
        return f"{doc_id}_{processor_name}"

    def save_checkpoint(
        self,
        doc_id: str,
        processed_pages: List[Dict],
        metadata: Dict,
        processor_name: str = 'unknown'  # NEW
    ):
        """Save processing checkpoint with processor info."""
        cache_key = self._generate_cache_key(doc_id, processor_name)
        # ... save logic

    def load_checkpoint(self, doc_id: str, processor_name: str = 'unknown') -> Optional[Dict]:
        """Load checkpoint for specific processor."""
        cache_key = self._generate_cache_key(doc_id, processor_name)
        # ... load logic
```

#### 5.2 Add Caching to New Processors

All new processors (`KimiPDFProcessor`, `QwenPDFProcessor`, `MultimodalVisionProcessor`) should support caching:

```python
class KimiPDFProcessor(MultimodalVisionProcessor):
    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        doc_id = self._generate_document_id(document['source_path'])

        # Try to load from cache
        if self.cache:
            cached = self.cache.load_checkpoint(doc_id, 'kimi')
            if cached:
                return cached

        # Process document
        result = super().process(document)

        # Save to cache
        if self.cache:
            self.cache.save_checkpoint(
                doc_id,
                result['pages'],
                result['metadata'],
                'kimi'
            )

        return result
```

---

### Phase 6: CLI & Configuration

**Goal**: Expose all options through CLI flags and env vars

#### 6.1 CLI Options

**File**: `scripts/document_processing/master_docling.py` (update)
**File**: `scripts/document_processing/run_pipeline.py` (update)

```bash
# New CLI options to add:

--vision-provider <provider>     # kimi, qwen, openai, gemini
--auto-detect-language           # Enable language-based routing
--hybrid-mode                    # Use hybrid processor with intelligent routing
--page-analysis-threshold <0-1>  # OCR confidence threshold for reprocessing
--force-processor <processor>    # Override auto-routing
```

**Example commands**:

```bash
# Use Kimi for Chinese PDFs
poetry run python scripts/document_processing/master_docling.py \
  --input_path chinese_doc.pdf \
  --vision-provider kimi

# Auto-detect language and route to best processor
poetry run python scripts/document_processing/master_docling.py \
  --input_path multilingual_doc.pdf \
  --auto-detect-language

# Hybrid mode: fast processing + selective vision OCR
poetry run python scripts/document_processing/master_docling.py \
  --input_path complex_doc.pdf \
  --hybrid-mode \
  --page-analysis-threshold 0.7
```

#### 6.2 Environment Variables

Update `.env.example`:

```bash
# Multimodal Provider API Keys
KIMI_API_KEY=your-kimi-api-key
QWEN_API_KEY=your-qwen-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key  # existing
OPENAI_API_KEY=your-openai-api-key        # existing
GEMINI_API_KEY=your-gemini-api-key        # existing

# Provider Preferences
VISION_PROVIDER=openai                     # Default provider
VISION_FALLBACK_ORDER=enhanced_docling,kimi,qwen,openai

# Processing Options
AUTO_DETECT_LANGUAGE=false
HYBRID_MODE=false
PAGE_ANALYSIS_THRESHOLD=0.7
```

---

### Phase 7: Unified Media Processing

**Goal**: Apply multimodal capabilities to images, audio, video

#### 7.1 Refactor ImageProcessor

**File**: `doc_processing/processors/image_processor.py`

```python
class ImageProcessor(BaseProcessor):
    """Provider-agnostic image processor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Use same multimodal client abstraction as PDF processing
        provider = self.config.get('vision_provider', 'openai')
        self.client = self._initialize_client(provider)

    def process(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process image with configured provider."""

        # Load image
        image_bytes = self._load_image(document['source_path'])

        # Process with multimodal client
        prompt = self.config.get('prompt', 'Describe this image in detail.')
        result_text = self.client.process_image(image_bytes, prompt)

        document['content'] = result_text
        document['processing_method'] = f'image_{self.client.provider_name}'

        return document
```

#### 7.2 Update CLI for Media

**File**: `scripts/document_processing/run_pipeline.py`

Add support for:
- `--vision-provider` for images
- Audio/video processing through multimodal APIs
- Unified interface across all media types

---

## Implementation Priority

### High Priority (Implement First)
1. ✅ **Phase 1.1**: Add KimiClient and QwenClient
2. ✅ **Phase 2.1**: Refactor GPTPVisionProcessor → MultimodalVisionProcessor
3. ✅ **Phase 2.3**: Register new processors in PDFProcessor
4. ✅ **Phase 6.1**: Add CLI options for provider selection

### Medium Priority (Implement Second)
5. ✅ **Phase 4**: Language detection and auto-routing
6. ✅ **Phase 5**: ProcessingCache integration for new processors
7. ✅ **Phase 6.2**: Environment variable configuration

### Lower Priority (Nice to Have)
8. ⚠️ **Phase 3**: Intelligent page-level routing (complex heuristics)
9. ⚠️ **Phase 7**: Unified media processing

---

## Success Criteria

### Functional Requirements
- ✅ Can process PDFs with Kimi, Qwen, OpenAI, or Gemini
- ✅ Auto-detects document language and routes to best processor
- ✅ Caching works for all processors
- ✅ CLI flags control all behavior
- ✅ Zero changes to existing functionality (backward compatible)

### Non-Functional Requirements
- ✅ Pure ETL output (no vector DB dependencies)
- ✅ Cost-optimized (hybrid mode reduces API costs)
- ✅ Resumable processing (cache integration)
- ✅ Easy to add new providers (follows abstraction pattern)

---

## Testing Strategy

### Unit Tests
- `tests/test_kimi_client.py`: Test Kimi API integration
- `tests/test_qwen_client.py`: Test Qwen API integration
- `tests/test_multimodal_vision_processor.py`: Test provider-agnostic processor
- `tests/test_language_detector.py`: Test language detection logic

### Integration Tests
- `tests/test_hybrid_processing.py`: Test intelligent routing
- `tests/test_provider_fallback.py`: Test fallback when provider fails
- `tests/test_cache_multiprocessor.py`: Test cache with multiple processors

### End-to-End Tests
- Process sample Chinese PDF with Kimi
- Process sample English PDF with auto-detection
- Process complex PDF with hybrid mode

---

## Migration Guide

### For Existing Users

No breaking changes! Existing code continues to work:

```bash
# Still works exactly as before
poetry run python scripts/document_processing/master_docling.py \
  --input_path document.pdf
```

### To Use New Features

```bash
# Option 1: Specify provider
poetry run python scripts/document_processing/master_docling.py \
  --input_path document.pdf \
  --vision-provider kimi

# Option 2: Auto-detect language
poetry run python scripts/document_processing/master_docling.py \
  --input_path document.pdf \
  --auto-detect-language

# Option 3: Hybrid mode (recommended for complex docs)
poetry run python scripts/document_processing/master_docling.py \
  --input_path document.pdf \
  --hybrid-mode
```

---

## Cost Analysis

### Current State
- Free: Enhanced Docling (default)
- Paid: OpenAI GPT-4 Vision (~$2.50-10/1M tokens)

### After Enhancements
- **Free**: Enhanced Docling (default, unchanged)
- **Cheap**: Kimi (~$0.50/1M tokens), Qwen (~$0.30/1M tokens)
- **Premium**: OpenAI (~$2.50-10/1M tokens)
- **Hybrid**: Mix of free + selective paid (optimized costs)

**Example Cost Savings (100-page complex PDF)**:
- Before: 100 pages × $0.10/page (GPT-4V) = $10
- After (Hybrid): 90 pages × $0 (Docling) + 10 pages × $0.05/page (Kimi) = $0.50
- **Savings**: 95%

---

## Future Enhancements

### Beyond This Plan
- **Recursive page refinement**: Retry failed pages with different providers
- **Quality scoring**: Rate OCR quality and auto-select best result
- **Batch optimization**: Process multiple pages in parallel
- **Model fine-tuning**: Train custom models for specific document types
- **Active learning**: Learn which processor works best for which doc types

---

## Dependencies

### New Python Packages
```bash
poetry add langdetect              # Language detection
poetry add pillow                  # Image analysis (if not already installed)
# Kimi/Qwen SDKs (if they provide official Python clients)
```

### API Access
- Kimi API Key (Moonshot AI)
- Qwen API Key (Alibaba Cloud)

---

## References

- Moonshot AI Kimi API: https://platform.moonshot.cn/docs
- Alibaba Qwen-VL: https://help.aliyun.com/zh/dashscope/
- Current Architecture: `docs/plans/2025-11-15-theory-of-change-pdf-processing-design.md`
