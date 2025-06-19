# PDF OCR Enhancement Plan for Pipeline-Documents

## Current State Analysis

### What We Have
- ✅ Docling (basic & enhanced) for modern PDFs
- ✅ GPT-4 Vision & Gemini for complex/scanned PDFs
- ✅ Fallback chain strategy (but limited to expensive options)
- ✅ Caching system for resumable processing
- ✅ Column detection utility (not integrated)

### What's Missing
- ❌ Tesseract for traditional OCR
- ❌ PyMuPDF text extraction (fast, free)
- ❌ Cost-effective fallback options
- ❌ Smart page-level routing
- ❌ Preprocessing for scanned PDFs

## Enhancement Roadmap

### Phase 1: Add Traditional OCR Methods (Immediate)

#### 1.1 Implement PyMuPDF Text Extractor

```python
# doc_processing/processors/pymupdf_processor.py
import fitz  # PyMuPDF
from typing import Dict, Optional
from doc_processing.base import BaseProcessor
import logging

class PyMuPDFProcessor(BaseProcessor):
    """Fast, free text extraction using PyMuPDF."""
    
    def __init__(self):
        super().__init__()
        self.name = "pymupdf"
        self.cost_per_page = 0.0
        
    def process(self, document: Dict) -> Dict:
        """Extract text using PyMuPDF's built-in extraction."""
        try:
            pdf_path = document.get('source_path')
            if not pdf_path:
                raise ValueError("No source path provided")
            
            doc = fitz.open(pdf_path)
            extracted_text = []
            metadata = {
                'page_count': len(doc),
                'metadata': doc.metadata,
                'is_encrypted': doc.is_encrypted,
                'is_scanned': False  # Will detect later
            }
            
            for page_num, page in enumerate(doc):
                # Extract text
                text = page.get_text()
                
                # Check if page is scanned (no text extracted)
                if len(text.strip()) < 10:
                    metadata['is_scanned'] = True
                    metadata[f'page_{page_num}_scanned'] = True
                else:
                    extracted_text.append(f"Page {page_num + 1}:\n{text}")
                
                # Also extract tables if present
                tables = page.find_tables()
                if tables:
                    metadata[f'page_{page_num}_tables'] = len(tables)
                    for table in tables:
                        extracted_text.append(f"\nTable on page {page_num + 1}:\n")
                        extracted_text.append(self._format_table(table))
            
            doc.close()
            
            document['content'] = '\n\n'.join(extracted_text)
            document['metadata'].update(metadata)
            document['processor'] = self.name
            
            # If mostly scanned, indicate need for OCR
            if metadata['is_scanned']:
                document['requires_ocr'] = True
                
            return document
            
        except Exception as e:
            logging.error(f"PyMuPDF extraction failed: {str(e)}")
            raise
    
    def _format_table(self, table) -> str:
        """Format table data as text."""
        rows = []
        for row in table.extract():
            rows.append(' | '.join(str(cell) if cell else '' for cell in row))
        return '\n'.join(rows)
```

#### 1.2 Implement Tesseract Processor

```python
# doc_processing/processors/tesseract_processor.py
import pytesseract
from PIL import Image
import numpy as np
import cv2
from pdf2image import convert_from_path
from typing import Dict, List, Optional
import logging
from tqdm import tqdm

class TesseractPDFProcessor(BaseProcessor):
    """OCR using Tesseract for scanned PDFs."""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__()
        self.name = "tesseract"
        self.cost_per_page = 0.0
        self.config = config or {}
        
        # Tesseract configuration
        self.tesseract_config = self.config.get('tesseract_config', {
            'lang': 'eng',
            'oem': 3,  # Default OCR Engine Mode
            'psm': 3,  # Page segmentation mode
        })
        
        # Preprocessing settings
        self.preprocess = self.config.get('preprocess', True)
        self.dpi = self.config.get('dpi', 300)
        
    def process(self, document: Dict) -> Dict:
        """Process PDF using Tesseract OCR."""
        try:
            pdf_path = document.get('source_path')
            if not pdf_path:
                raise ValueError("No source path provided")
            
            # Convert PDF to images
            logging.info(f"Converting PDF to images at {self.dpi} DPI...")
            images = convert_from_path(pdf_path, dpi=self.dpi)
            
            extracted_text = []
            ocr_metadata = {
                'page_count': len(images),
                'dpi': self.dpi,
                'preprocessing': self.preprocess,
                'confidence_scores': []
            }
            
            # Process each page
            for page_num, image in enumerate(tqdm(images, desc="OCR processing")):
                # Preprocess if enabled
                if self.preprocess:
                    image = self._preprocess_image(image)
                
                # Perform OCR with confidence scores
                data = pytesseract.image_to_data(
                    image, 
                    lang=self.tesseract_config['lang'],
                    config=self._build_tesseract_config(),
                    output_type=pytesseract.Output.DICT
                )
                
                # Extract text and calculate confidence
                page_text = []
                confidences = []
                
                for i, text in enumerate(data['text']):
                    if text.strip():
                        page_text.append(text)
                        conf = data['conf'][i]
                        if conf > 0:  # -1 means no confidence
                            confidences.append(conf)
                
                # Calculate average confidence for page
                avg_confidence = np.mean(confidences) if confidences else 0
                ocr_metadata['confidence_scores'].append({
                    'page': page_num + 1,
                    'confidence': avg_confidence
                })
                
                # Add page text
                extracted_text.append(f"Page {page_num + 1}:\n{' '.join(page_text)}")
                
                # Low confidence warning
                if avg_confidence < 70:
                    logging.warning(f"Low OCR confidence on page {page_num + 1}: {avg_confidence:.1f}%")
            
            # Combine results
            document['content'] = '\n\n'.join(extracted_text)
            document['metadata'].update(ocr_metadata)
            document['processor'] = self.name
            
            # Calculate overall confidence
            overall_confidence = np.mean([p['confidence'] for p in ocr_metadata['confidence_scores']])
            document['ocr_confidence'] = overall_confidence
            
            # Suggest fallback if confidence is low
            if overall_confidence < 60:
                document['requires_better_ocr'] = True
                
            return document
            
        except Exception as e:
            logging.error(f"Tesseract OCR failed: {str(e)}")
            raise
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy."""
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply preprocessing steps
        # 1. Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 2. Threshold (binarization)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 3. Deskew
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 0.5:  # Only deskew if angle is significant
                (h, w) = binary.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                binary = cv2.warpAffine(binary, M, (w, h), 
                                      flags=cv2.INTER_CUBIC, 
                                      borderMode=cv2.BORDER_REPLICATE)
        
        # 4. Remove noise and smooth
        kernel = np.ones((1, 1), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL
        return Image.fromarray(binary)
    
    def _build_tesseract_config(self) -> str:
        """Build Tesseract configuration string."""
        config_parts = [
            f"--oem {self.tesseract_config['oem']}",
            f"--psm {self.tesseract_config['psm']}"
        ]
        return ' '.join(config_parts)
```

### Phase 2: Enhanced Fallback Chain (Week 1)

#### 2.1 Update PDF Processor with Smart Fallback

```python
# Enhanced doc_processing/processors/pdf_processor.py

class PDFProcessor(BaseProcessor):
    """Enhanced PDF processor with intelligent fallback chain."""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__()
        self.config = config or {}
        self.settings = get_settings()
        
        # Enhanced processor chain with cost-effective options first
        self.processor_chain = [
            ('pymupdf', PyMuPDFProcessor, 0.0),
            ('tesseract', TesseractPDFProcessor, 0.0),
            ('docling', DoclingPDFProcessor, 0.0),
            ('enhanced_docling', EnhancedDoclingPDFProcessor, 0.0),
            ('gemini', GeminiPDFProcessor, 0.0002),
            ('gpt', GPTPDFProcessor, 0.01),
        ]
        
        # Smart routing configuration
        self.smart_routing = self.config.get('smart_routing', True)
        self.page_level_fallback = self.config.get('page_level_fallback', True)
        
    def process(self, document: Dict) -> Dict:
        """Process with intelligent fallback strategy."""
        strategy = self.config.get('strategy', self.settings.PDF_PROCESSOR_STRATEGY)
        
        if strategy == 'smart':
            return self._process_smart(document)
        elif strategy == 'fallback_chain':
            return self._process_fallback_enhanced(document)
        else:
            return self._process_exclusive(document)
    
    def _process_smart(self, document: Dict) -> Dict:
        """Smart processing with document analysis."""
        pdf_path = Path(document['source_path'])
        
        # Analyze PDF characteristics
        pdf_info = self._analyze_pdf(pdf_path)
        
        # Determine optimal processor based on analysis
        if pdf_info['is_text_pdf'] and not pdf_info['has_complex_layout']:
            # Use PyMuPDF for simple text PDFs
            processor = PyMuPDFProcessor()
        elif pdf_info['is_scanned']:
            # Use Tesseract for scanned PDFs
            processor = TesseractPDFProcessor({'preprocess': True})
        elif pdf_info['has_tables'] or pdf_info['has_columns']:
            # Use Enhanced Docling for complex layouts
            processor = EnhancedDoclingPDFProcessor()
        else:
            # Default to regular Docling
            processor = DoclingPDFProcessor()
        
        try:
            result = processor.process(document)
            
            # Check if result needs improvement
            if self._needs_better_extraction(result):
                logging.info(f"Initial extraction inadequate, trying fallback...")
                return self._process_fallback_enhanced(document)
            
            return result
            
        except Exception as e:
            logging.error(f"Smart processing failed: {str(e)}")
            return self._process_fallback_enhanced(document)
    
    def _analyze_pdf(self, pdf_path: Path) -> Dict:
        """Analyze PDF characteristics for smart routing."""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            
            analysis = {
                'page_count': len(doc),
                'is_encrypted': doc.is_encrypted,
                'is_text_pdf': False,
                'is_scanned': True,
                'has_tables': False,
                'has_columns': False,
                'has_complex_layout': False,
                'avg_text_length': 0
            }
            
            text_lengths = []
            
            for page in doc[:5]:  # Analyze first 5 pages
                text = page.get_text()
                text_length = len(text.strip())
                text_lengths.append(text_length)
                
                if text_length > 100:
                    analysis['is_text_pdf'] = True
                    analysis['is_scanned'] = False
                
                # Check for tables
                tables = page.find_tables()
                if tables:
                    analysis['has_tables'] = True
                
                # Simple column detection
                blocks = page.get_text_blocks()
                if len(blocks) > 20:  # Many text blocks might indicate columns
                    analysis['has_columns'] = True
            
            analysis['avg_text_length'] = np.mean(text_lengths)
            
            # Determine complexity
            if analysis['has_tables'] or analysis['has_columns']:
                analysis['has_complex_layout'] = True
            
            doc.close()
            return analysis
            
        except Exception as e:
            logging.error(f"PDF analysis failed: {str(e)}")
            return {'is_text_pdf': False, 'is_scanned': True}
    
    def _needs_better_extraction(self, result: Dict) -> bool:
        """Check if extraction result needs improvement."""
        content = result.get('content', '')
        metadata = result.get('metadata', {})
        
        # Check various quality indicators
        if len(content) < 100:
            return True
        
        if metadata.get('ocr_confidence', 100) < 70:
            return True
        
        if result.get('requires_ocr') or result.get('requires_better_ocr'):
            return True
        
        # Check for common OCR errors
        error_patterns = [
            r'[^\s]{50,}',  # Very long words (likely OCR errors)
            r'[^a-zA-Z0-9\s]{10,}',  # Many special characters
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def _process_fallback_enhanced(self, document: Dict) -> Dict:
        """Enhanced fallback with cost tracking."""
        results = []
        total_cost = 0.0
        
        for proc_name, proc_class, cost_per_page in self.processor_chain:
            if proc_name not in self.settings.ACTIVE_PDF_PROCESSORS:
                continue
            
            try:
                logging.info(f"Trying {proc_name} processor...")
                processor = proc_class()
                result = processor.process(document.copy())
                
                # Track cost
                page_count = result.get('metadata', {}).get('page_count', 1)
                processor_cost = cost_per_page * page_count
                total_cost += processor_cost
                
                # Check quality
                if not self._needs_better_extraction(result):
                    result['extraction_cost'] = total_cost
                    result['processors_tried'] = [r['processor'] for r in results] + [proc_name]
                    logging.info(f"Success with {proc_name}. Total cost: ${total_cost:.4f}")
                    return result
                else:
                    results.append({
                        'processor': proc_name,
                        'cost': processor_cost,
                        'confidence': result.get('ocr_confidence', 0)
                    })
                    
            except Exception as e:
                logging.warning(f"{proc_name} failed: {str(e)}")
                continue
        
        # If all failed, return best result
        if results:
            best_result = max(results, key=lambda x: x.get('confidence', 0))
            logging.warning(f"All processors inadequate. Using {best_result['processor']} result.")
            
        document['extraction_failed'] = True
        document['extraction_cost'] = total_cost
        return document
```

### Phase 3: Page-Level Processing (Week 2)

#### 3.1 Implement Page-Level Fallback

```python
# doc_processing/processors/page_level_processor.py

class PageLevelPDFProcessor(BaseProcessor):
    """Process PDF with different processors for different pages."""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__()
        self.config = config or {}
        self.cache = ProcessingCache()
        
    def process(self, document: Dict) -> Dict:
        """Process each page with optimal processor."""
        pdf_path = Path(document['source_path'])
        
        # Initialize processors
        processors = {
            'pymupdf': PyMuPDFProcessor(),
            'tesseract': TesseractPDFProcessor(),
            'docling': DoclingPDFProcessor(),
            'gemini': GeminiPDFProcessor(),
        }
        
        # Get page count
        import fitz
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        
        # Process each page
        page_results = {}
        total_cost = 0.0
        
        for page_num in range(page_count):
            # Check cache first
            cached = self.cache.get_page(pdf_path, page_num)
            if cached:
                page_results[page_num] = cached
                continue
            
            # Extract page as image for analysis
            page_image = self._extract_page_image(pdf_path, page_num)
            
            # Classify page
            page_type = self._classify_page(page_image)
            
            # Select processor based on page type
            if page_type == 'simple_text':
                processor = processors['pymupdf']
                cost = 0.0
            elif page_type == 'scanned':
                processor = processors['tesseract']
                cost = 0.0
            elif page_type == 'complex':
                processor = processors['docling']
                cost = 0.0
            else:  # 'very_complex'
                processor = processors['gemini']
                cost = 0.0002
            
            # Process page
            try:
                page_result = self._process_single_page(
                    processor, pdf_path, page_num
                )
                page_results[page_num] = page_result
                total_cost += cost
                
                # Cache result
                self.cache.save_page(pdf_path, page_num, page_result)
                
            except Exception as e:
                logging.error(f"Failed to process page {page_num}: {str(e)}")
                # Try fallback
                page_results[page_num] = self._fallback_page_processing(
                    pdf_path, page_num, processors
                )
        
        # Combine page results
        document['content'] = self._combine_page_results(page_results)
        document['metadata']['page_processors'] = {
            page: result.get('processor', 'unknown') 
            for page, result in page_results.items()
        }
        document['extraction_cost'] = total_cost
        
        return document
```

### Phase 4: Integration & Testing (Week 3)

#### 4.1 Update Configuration

```python
# doc_processing/config.py updates

# Add new processor settings
TESSERACT_ENABLED: bool = Field(default=True)
TESSERACT_LANG: str = Field(default='eng')
TESSERACT_DPI: int = Field(default=300)
TESSERACT_PREPROCESS: bool = Field(default=True)

PYMUPDF_ENABLED: bool = Field(default=True)
PYMUPDF_EXTRACT_TABLES: bool = Field(default=True)

# Smart routing settings
PDF_SMART_ROUTING: bool = Field(default=True)
PDF_PAGE_LEVEL_PROCESSING: bool = Field(default=False)
PDF_QUALITY_THRESHOLD: float = Field(default=0.7)

# Enhanced fallback chain
PDF_PROCESSOR_CHAIN: list[str] = Field(
    default=["pymupdf", "tesseract", "docling", "enhanced_docling", "gemini", "gpt"],
    description="Processor order for fallback chain (cheapest to most expensive)"
)
```

#### 4.2 Create Test Suite

```python
# tests/test_enhanced_pdf_ocr.py

import pytest
from pathlib import Path
from doc_processing.processors import (
    PyMuPDFProcessor, TesseractPDFProcessor, 
    PDFProcessor, PageLevelPDFProcessor
)

class TestEnhancedPDFOCR:
    """Test suite for enhanced PDF OCR capabilities."""
    
    @pytest.fixture
    def sample_pdfs(self):
        """Get sample PDFs of different types."""
        return {
            'text_pdf': Path('tests/data/simple_text.pdf'),
            'scanned_pdf': Path('tests/data/scanned_document.pdf'),
            'complex_pdf': Path('tests/data/complex_layout.pdf'),
            'mixed_pdf': Path('tests/data/mixed_content.pdf'),
        }
    
    def test_pymupdf_extraction(self, sample_pdfs):
        """Test PyMuPDF extraction on text PDF."""
        processor = PyMuPDFProcessor()
        document = {'source_path': sample_pdfs['text_pdf']}
        
        result = processor.process(document)
        
        assert 'content' in result
        assert len(result['content']) > 100
        assert not result.get('requires_ocr', False)
    
    def test_tesseract_ocr(self, sample_pdfs):
        """Test Tesseract OCR on scanned PDF."""
        processor = TesseractPDFProcessor({'preprocess': True})
        document = {'source_path': sample_pdfs['scanned_pdf']}
        
        result = processor.process(document)
        
        assert 'content' in result
        assert 'ocr_confidence' in result
        assert result['processor'] == 'tesseract'
    
    def test_smart_routing(self, sample_pdfs):
        """Test smart routing selects appropriate processor."""
        processor = PDFProcessor({'strategy': 'smart'})
        
        # Test with text PDF
        result = processor.process({'source_path': sample_pdfs['text_pdf']})
        assert result['processor'] == 'pymupdf'
        
        # Test with scanned PDF
        result = processor.process({'source_path': sample_pdfs['scanned_pdf']})
        assert result['processor'] == 'tesseract'
    
    def test_fallback_chain(self, sample_pdfs):
        """Test fallback chain with cost tracking."""
        processor = PDFProcessor({
            'strategy': 'fallback_chain',
            'force_fallback_test': True  # Force multiple attempts
        })
        
        result = processor.process({'source_path': sample_pdfs['complex_pdf']})
        
        assert 'extraction_cost' in result
        assert 'processors_tried' in result
        assert len(result['processors_tried']) > 1
    
    def test_page_level_processing(self, sample_pdfs):
        """Test page-level processor selection."""
        processor = PageLevelPDFProcessor()
        document = {'source_path': sample_pdfs['mixed_pdf']}
        
        result = processor.process(document)
        
        assert 'page_processors' in result['metadata']
        # Should use different processors for different pages
        processors_used = set(result['metadata']['page_processors'].values())
        assert len(processors_used) > 1
```

## Implementation Benefits

### 1. **Cost Optimization**
- PyMuPDF: Free for text PDFs (handles ~40% of documents)
- Tesseract: Free for scanned PDFs (handles ~30% of documents)  
- Docling: Free for complex layouts (handles ~20% of documents)
- LLMs: Only for remaining ~10% of difficult cases
- **Expected cost reduction: 85-90%**

### 2. **Performance Improvement**
- PyMuPDF: 100x faster than OCR for text PDFs
- Tesseract: 10x faster than LLM-based OCR
- Smart routing: Skip unnecessary processing
- Page-level: Optimize per-page processing

### 3. **Quality Enhancement**
- Preprocessing: Better accuracy for scanned documents
- Multiple attempts: Higher success rate
- Confidence tracking: Know when to fallback
- Smart routing: Use best tool for each document type

### 4. **Robustness**
- No single point of failure
- Graceful degradation
- Cache recovery
- Detailed error tracking

## Quick Implementation Steps

### Step 1: Add PyMuPDF Processor (1 hour)
```bash
# Install dependency
poetry add PyMuPDF

# Create processor file
# Copy the PyMuPDFProcessor code above
```

### Step 2: Add Tesseract Processor (2 hours)
```bash
# Install dependencies
poetry add pytesseract pdf2image opencv-python-headless
# Install Tesseract binary (OS-specific)

# Create processor file
# Copy the TesseractPDFProcessor code above
```

### Step 3: Update Fallback Chain (1 hour)
- Modify pdf_processor.py with enhanced fallback logic
- Add smart routing capability

### Step 4: Test & Validate (2 hours)
- Create test PDFs of different types
- Run comparison tests
- Measure cost and performance improvements

This enhancement plan focuses specifically on improving PDF OCR in the pipeline-documents repository, adding cost-effective options before falling back to expensive LLM-based OCR.