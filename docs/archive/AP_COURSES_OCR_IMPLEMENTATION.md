# AP Courses OCR Enhancement Implementation Plan

## Executive Summary

Your AP courses pipeline can significantly benefit from the pipeline-documents OCR capabilities, particularly for:
1. **Missing Units Problem**: 19 courses with missing unit information
2. **Cost Optimization**: Reduce GPT-4V API costs using fallback strategies
3. **Accuracy Improvement**: Multi-modal OCR for complex formatting
4. **Robustness**: Fallback chain for failed extractions

## Current vs Enhanced Pipeline Comparison

### Current AP Courses Pipeline
```
PDFs → PyMuPDF (5x zoom) → PNG Images → GPT-4V OCR → JSON Parsing
```
**Limitations:**
- Single OCR attempt (no fallbacks)
- Expensive (GPT-4V for all pages)
- Missing units in 19 courses
- No table/column detection

### Enhanced Pipeline with Pipeline-Documents
```
PDFs → Multi-Strategy Processing → Structured Output → JSON Parsing
         ├── Docling (primary, fast, cheap)
         ├── Enhanced Docling (tables/columns)
         ├── Gemini Vision (fallback)
         └── GPT-4V (final fallback)
```

## Implementation Strategy

### Phase 1: Hybrid Integration (Recommended)

Keep your existing pipeline but enhance it with pipeline-documents components for problem cases.

#### Step 1: Install Pipeline-Documents Components

```python
# Option A: Direct import (if in same environment)
from doc_processing.processors import (
    EnhancedDoclingPDFProcessor,
    GeminiVisionPDFProcessor,
    PDFProcessor
)
from doc_processing.config import Settings

# Option B: Copy specific processors to AP courses
# Copy these files:
# - doc_processing/processors/enhanced_docling_processor.py
# - doc_processing/processors/pdf_processor.py
# - doc_processing/utils/column_detection.py
```

#### Step 2: Create Fallback OCR Function

```python
# /Volumes/PortableSSD/ap-courses/notebooks/ocr_fallback_pipeline.py

import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

class APCoursesOCRPipeline:
    """Enhanced OCR pipeline with fallback strategies for AP courses."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.processors = self._initialize_processors()
        
    def _initialize_processors(self):
        """Initialize OCR processors in order of preference."""
        processors = []
        
        # 1. Docling - Fast and cheap for standard PDFs
        if self.config.get('use_docling', True):
            from doc_processing.processors import EnhancedDoclingPDFProcessor
            processors.append({
                'name': 'docling',
                'processor': EnhancedDoclingPDFProcessor(),
                'cost_per_page': 0.0,  # Free/local processing
                'accuracy': 0.85
            })
        
        # 2. Gemini Vision - Good balance of cost/quality
        if self.config.get('use_gemini', True):
            from doc_processing.processors import GeminiVisionPDFProcessor
            processors.append({
                'name': 'gemini',
                'processor': GeminiVisionPDFProcessor(
                    api_key=os.getenv('GOOGLE_API_KEY')
                ),
                'cost_per_page': 0.0002,  # Much cheaper than GPT-4V
                'accuracy': 0.90
            })
        
        # 3. GPT-4V - Highest quality but expensive
        if self.config.get('use_gpt4v', True):
            processors.append({
                'name': 'gpt4v',
                'processor': self._create_gpt4v_processor(),
                'cost_per_page': 0.01,
                'accuracy': 0.95
            })
        
        return processors
    
    def process_with_fallback(self, pdf_path: Path, target_pages: List[int] = None) -> Dict:
        """
        Process PDF with fallback strategy.
        Perfect for the 19 courses with missing units.
        """
        results = {}
        
        for page_num in target_pages or range(1, self._get_page_count(pdf_path) + 1):
            page_result = None
            
            for processor_info in self.processors:
                try:
                    processor = processor_info['processor']
                    logging.info(f"Trying {processor_info['name']} for page {page_num}")
                    
                    # Process single page
                    page_result = processor.process_page(pdf_path, page_num)
                    
                    # Validate result has expected content
                    if self._validate_extraction(page_result, page_num):
                        results[page_num] = {
                            'text': page_result,
                            'processor': processor_info['name'],
                            'cost': processor_info['cost_per_page']
                        }
                        break
                    else:
                        logging.warning(f"{processor_info['name']} failed validation for page {page_num}")
                        
                except Exception as e:
                    logging.error(f"Error with {processor_info['name']}: {str(e)}")
                    continue
            
            if not page_result:
                logging.error(f"All processors failed for page {page_num}")
                results[page_num] = {'text': '', 'processor': 'failed', 'cost': 0}
        
        return results
    
    def _validate_extraction(self, text: str, page_num: int) -> bool:
        """Validate extraction quality for AP course content."""
        if not text or len(text) < 100:
            return False
        
        # Check for key AP course elements
        validation_keywords = [
            'unit', 'topic', 'big idea', 'enduring understanding',
            'learning objective', 'essential knowledge', 'skill'
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for kw in validation_keywords if kw in text_lower)
        
        # Require at least 2 keywords for valid extraction
        return keyword_count >= 2
```

#### Step 3: Enhance Missing Units Extraction

```python
# /Volumes/PortableSSD/ap-courses/notebooks/extract_missing_units.py

def extract_missing_units(course_pdfs_with_missing_units: List[Path]):
    """
    Use enhanced OCR pipeline specifically for courses with missing units.
    """
    pipeline = APCoursesOCRPipeline({
        'use_docling': True,
        'use_gemini': True,
        'use_gpt4v': True,
        'validate_output': True
    })
    
    results = {}
    
    for pdf_path in course_pdfs_with_missing_units:
        course_name = pdf_path.stem
        logging.info(f"Processing {course_name} with enhanced OCR")
        
        # Target pages likely to contain unit information
        # Based on AP course structure: usually pages 10-30
        target_pages = list(range(10, 31))
        
        extraction_results = pipeline.process_with_fallback(
            pdf_path, 
            target_pages=target_pages
        )
        
        # Post-process to extract units
        units = extract_units_from_text(extraction_results)
        
        if units:
            results[course_name] = units
            logging.info(f"Successfully extracted {len(units)} units from {course_name}")
        else:
            logging.warning(f"No units found in {course_name}")
    
    return results
```

### Phase 2: Cost Optimization Strategy

#### Implement Intelligent Page Classification

```python
def classify_page_complexity(image_path: Path) -> str:
    """
    Classify page to determine optimal OCR strategy.
    """
    # Use simple heuristics or a lightweight model
    # Returns: 'simple', 'table', 'complex'
    
    from PIL import Image
    import numpy as np
    
    img = Image.open(image_path)
    img_array = np.array(img.convert('L'))  # Convert to grayscale
    
    # Check for tables (lots of straight lines)
    edges = detect_edges(img_array)
    horizontal_lines = count_horizontal_lines(edges)
    vertical_lines = count_vertical_lines(edges)
    
    if horizontal_lines > 5 and vertical_lines > 3:
        return 'table'
    
    # Check text density
    text_density = calculate_text_density(img_array)
    if text_density > 0.7:
        return 'complex'
    
    return 'simple'

def select_optimal_processor(page_type: str, importance: str = 'normal') -> str:
    """
    Select processor based on page type and importance.
    """
    strategy_map = {
        'simple': 'docling',      # Fast and free
        'table': 'enhanced_docling',  # Better table extraction
        'complex': 'gemini',      # Good balance
        'critical': 'gpt4v'       # When accuracy is paramount
    }
    
    # Override for critical pages (e.g., units overview)
    if importance == 'critical':
        return 'gpt4v'
    
    return strategy_map.get(page_type, 'docling')
```

### Phase 3: Integration with Existing Pipeline

#### Modify Your Current OCR Notebook

```python
# Enhanced version of notebooks/01_gpt_ocr.ipynb

import sys
sys.path.append('/Users/scottwilliams/Documents/Develop Projects/master_projects/pipeline-documents')

from doc_processing.processors import EnhancedDoclingPDFProcessor
from ocr_fallback_pipeline import APCoursesOCRPipeline

def process_course_with_enhanced_ocr(pdf_path: Path, output_dir: Path):
    """
    Process AP course PDF with intelligent OCR selection.
    """
    # Initialize pipeline
    pipeline = APCoursesOCRPipeline({
        'use_docling': True,
        'use_gemini': True,
        'use_gpt4v': True
    })
    
    # First pass: Try Docling for all pages (fast and free)
    docling_results = try_docling_first(pdf_path)
    
    # Identify pages that need better OCR
    pages_needing_reprocessing = []
    for page_num, result in docling_results.items():
        if not validate_ap_content(result['text']):
            pages_needing_reprocessing.append(page_num)
    
    # Second pass: Use better OCR for failed pages
    if pages_needing_reprocessing:
        enhanced_results = pipeline.process_with_fallback(
            pdf_path,
            target_pages=pages_needing_reprocessing
        )
        
        # Merge results
        for page_num, result in enhanced_results.items():
            docling_results[page_num] = result
    
    # Save results
    save_ocr_results(docling_results, output_dir)
    
    # Report cost savings
    total_cost = sum(r.get('cost', 0) for r in docling_results.values())
    gpt4v_cost = len(docling_results) * 0.01  # If all pages used GPT-4V
    savings = gpt4v_cost - total_cost
    
    print(f"Processed {pdf_path.name}:")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"  Savings vs GPT-4V only: ${savings:.4f} ({savings/gpt4v_cost*100:.1f}%)")
    
    return docling_results
```

## Expected Benefits

### 1. Cost Reduction
- **Current**: ~$0.01 per page (GPT-4V only)
- **Enhanced**: ~$0.002 per page (80% reduction)
- **Annual Savings**: For 38 courses × 300 pages = $91.20 vs $11.40

### 2. Improved Extraction
- **Missing Units**: Fallback chain increases success rate
- **Tables**: Enhanced Docling handles complex tables better
- **Columns**: Proper multi-column detection

### 3. Performance
- **Docling**: 10-50x faster than GPT-4V for simple pages
- **Parallel Processing**: Can process multiple pages simultaneously
- **Caching**: Resume interrupted processing

### 4. Robustness
- **No Single Point of Failure**: Multiple OCR engines
- **Validation**: Automatic quality checks
- **Detailed Logging**: Track which processor succeeded

## Implementation Timeline

### Week 1: Setup and Testing
- [ ] Install pipeline-documents dependencies
- [ ] Create test notebook with sample courses
- [ ] Validate Docling works with AP PDFs
- [ ] Test fallback chain on problematic pages

### Week 2: Integration
- [ ] Modify existing OCR notebooks
- [ ] Add cost tracking
- [ ] Process courses with missing units
- [ ] Compare results with current approach

### Week 3: Optimization
- [ ] Implement page classification
- [ ] Fine-tune processor selection
- [ ] Add caching for processed pages
- [ ] Create performance benchmarks

### Week 4: Production
- [ ] Process all 38 courses
- [ ] Generate cost/quality report
- [ ] Document new workflow
- [ ] Update CLAUDE.md with new pipeline

## Specific Solutions for AP Courses Challenges

### 1. Missing Units (19 courses)
```python
# Target extraction for unit information
unit_extraction_config = {
    'target_keywords': ['Unit', 'UNIT', 'unit overview', 'exam weighting'],
    'page_range': (10, 40),  # Units typically in this range
    'use_enhanced_extraction': True,
    'require_validation': True
}
```

### 2. Skills/Practices in Parentheses
```python
# Enhanced regex patterns for Docling post-processing
skill_patterns = {
    'topic_with_skill': r'(\d+\.\d+)\s+(.+?)\s*\(([A-Z]+\-\d+\.\w+)\)',
    'skill_reference': r'\(([A-Z]{2,4}\-\d+\.\w+)\)',
    'practice_code': r'Practice\s+(\d+\.\w+)'
}
```

### 3. Hierarchical Structure Preservation
```python
# Structured extraction with hierarchy validation
hierarchy_validator = {
    'course': {'required': ['title', 'exam_percentage']},
    'unit': {'required': ['number', 'title', 'periods', 'exam_weight']},
    'topic': {'required': ['number', 'title', 'skill_mapping']}
}
```

## Next Steps

1. **Immediate Action**: Test Docling on one problematic course
2. **Quick Win**: Process the 19 courses with missing units
3. **Full Integration**: Gradually migrate all courses to new pipeline
4. **Monitor**: Track cost savings and quality improvements

This implementation plan provides a practical path to enhance your AP courses OCR pipeline while maintaining your existing structure and addressing specific pain points.