# Unified OCR Optimization Plan: Pipeline-Documents + AP Courses

## Executive Summary

Combining optimization opportunities from both repositories can create a best-in-class OCR pipeline that is:
- **Cost-effective**: 80-90% reduction in API costs
- **Accurate**: Multi-stage validation and fallback strategies
- **Fast**: Parallel processing and intelligent caching
- **Robust**: Multiple OCR engines with automatic fallback

## Optimization Strategy Matrix

| Optimization | Current State | Enhanced State | Impact |
|--------------|--------------|----------------|---------|
| **Image Preprocessing** | Basic conversion | Binarization, deskewing, noise removal | +15-20% accuracy for Tesseract |
| **Resolution Scaling** | Fixed 2x (pipeline), 5x (AP) | Dynamic based on DPI/content | +10-30% accuracy |
| **Parallel Processing** | Sequential | Concurrent with ThreadPoolExecutor | 3-5x faster |
| **Caching** | Docling only | All processors with unified cache | 100% faster for re-runs |
| **Fallback Chain** | GPT-4V only (AP) | Tesseract → Docling → Gemini → GPT-4V | 80% cost reduction |
| **Prompt Optimization** | Static, verbose | Dynamic, minimal tokens | 20-30% faster API calls |
| **Post-processing** | None | OCR error correction, validation | +5-10% accuracy |

## Unified Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Document (PDF/Image)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Image Preprocessing Layer                   │
│  • Dynamic resolution scaling (DPI-aware)                    │
│  • Binarization, deskewing, noise removal                   │
│  • Page classification (simple/table/complex)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Parallel OCR Pipeline                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Tesseract  │  │   Docling   │  │   Gemini    │        │
│  │   (Local)   │  │   (Local)   │  │  (API-$)    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘               │
│                           │                                  │
│                           ▼                                  │
│                    Validation Layer                          │
│                  (Confidence scoring)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Fallback to GPT-4V                        │
│                  (Only for failed pages)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Post-Processing Layer                      │
│  • OCR error correction (l→1, O→0)                         │
│  • Structure validation (AP courses)                        │
│  • Content extraction (units, topics, skills)              │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Unified Image Preprocessing Module

```python
# /pipeline-documents/doc_processing/utils/image_preprocessing.py

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import pytesseract

class ImagePreprocessor:
    """Advanced image preprocessing for optimal OCR."""
    
    @staticmethod
    def auto_scale_resolution(image: Image.Image, target_dpi: int = 300) -> Tuple[Image.Image, float]:
        """
        Dynamically scale image based on detected DPI.
        AP courses benefit from 5x, simple docs need only 2x.
        """
        # Detect current DPI
        current_dpi = image.info.get('dpi', (72, 72))[0]
        
        # Calculate optimal scale
        if current_dpi < 150:  # Low quality scan
            scale = target_dpi / current_dpi
        else:
            scale = min(target_dpi / current_dpi, 3.0)  # Cap at 3x
        
        # Apply scaling
        new_size = (int(image.width * scale), int(image.height * scale))
        scaled = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return scaled, scale
    
    @staticmethod
    def preprocess_for_ocr(image: Image.Image, target_engine: str = 'tesseract') -> Image.Image:
        """
        Apply preprocessing based on target OCR engine.
        """
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply different preprocessing based on engine
        if target_engine == 'tesseract':
            # Aggressive preprocessing for Tesseract
            # 1. Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # 2. Binarization (Otsu's method)
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 3. Deskew
            coords = np.column_stack(np.where(binary > 0))
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if angle != 0:
                (h, w) = binary.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                binary = cv2.warpAffine(binary, M, (w, h), 
                                      flags=cv2.INTER_CUBIC, 
                                      borderMode=cv2.BORDER_REPLICATE)
            
            # 4. Remove borders
            binary = ImagePreprocessor._remove_borders(binary)
            
            processed = binary
            
        elif target_engine in ['docling', 'gemini', 'gpt4v']:
            # Lighter preprocessing for AI models
            # 1. Enhance contrast
            enhanced = cv2.equalizeHist(gray)
            
            # 2. Mild denoising
            processed = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        else:
            processed = gray
        
        # Convert back to PIL
        return Image.fromarray(processed)
    
    @staticmethod
    def classify_page_complexity(image: Image.Image) -> dict:
        """
        Classify page to determine optimal OCR strategy.
        Critical for AP courses with mixed content.
        """
        img_array = np.array(image.convert('L'))
        
        # Detect features
        features = {
            'has_tables': ImagePreprocessor._detect_tables(img_array),
            'has_columns': ImagePreprocessor._detect_columns(img_array),
            'text_density': ImagePreprocessor._calculate_text_density(img_array),
            'has_formulas': ImagePreprocessor._detect_formulas(img_array),
            'has_diagrams': ImagePreprocessor._detect_diagrams(img_array)
        }
        
        # Classify complexity
        if features['has_tables'] or features['has_formulas']:
            complexity = 'complex'
        elif features['has_columns'] or features['text_density'] > 0.7:
            complexity = 'medium'
        else:
            complexity = 'simple'
        
        return {
            'complexity': complexity,
            'features': features,
            'recommended_engine': ImagePreprocessor._recommend_engine(features)
        }
    
    @staticmethod
    def _recommend_engine(features: dict) -> str:
        """Recommend OCR engine based on page features."""
        if features['has_tables']:
            return 'enhanced_docling'  # Best for tables
        elif features['has_formulas'] or features['has_diagrams']:
            return 'gemini'  # Good balance for complex content
        elif features['text_density'] < 0.3:
            return 'gpt4v'  # Best for sparse/handwritten text
        else:
            return 'tesseract'  # Fast and free for simple text
```

#### 1.2 Parallel Processing Framework

```python
# /pipeline-documents/doc_processing/utils/parallel_processor.py

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Callable, Any
import logging
from tqdm import tqdm

class ParallelOCRProcessor:
    """Parallel processing for OCR operations."""
    
    def __init__(self, max_workers: int = None, use_processes: bool = False):
        self.max_workers = max_workers or (4 if use_processes else 8)
        self.use_processes = use_processes
        self.executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    
    def process_pages_parallel(self, 
                             pages: List[Any], 
                             process_func: Callable,
                             desc: str = "Processing pages") -> Dict[int, Any]:
        """
        Process pages in parallel with progress bar.
        """
        results = {}
        
        with self.executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_page = {
                executor.submit(process_func, page, idx): (idx, page)
                for idx, page in enumerate(pages)
            }
            
            # Process completed tasks
            with tqdm(total=len(pages), desc=desc) as pbar:
                for future in as_completed(future_to_page):
                    idx, page = future_to_page[future]
                    try:
                        result = future.result()
                        results[idx] = result
                        pbar.update(1)
                    except Exception as e:
                        logging.error(f"Error processing page {idx}: {str(e)}")
                        results[idx] = {'error': str(e)}
                        pbar.update(1)
        
        # Sort results by page index
        return dict(sorted(results.items()))
    
    def process_with_fallback_parallel(self, 
                                     items: List[Any],
                                     processors: List[Dict],
                                     validation_func: Callable = None) -> Dict:
        """
        Process items with multiple processors in parallel,
        using fallback for failed items.
        """
        results = {}
        remaining_items = list(enumerate(items))
        
        for processor_info in processors:
            if not remaining_items:
                break
            
            processor = processor_info['processor']
            processor_name = processor_info['name']
            
            logging.info(f"Processing {len(remaining_items)} items with {processor_name}")
            
            # Process remaining items in parallel
            batch_results = self.process_pages_parallel(
                [item for _, item in remaining_items],
                processor.process,
                desc=f"OCR with {processor_name}"
            )
            
            # Validate results and identify failures
            newly_completed = []
            still_remaining = []
            
            for (original_idx, item), result in zip(remaining_items, batch_results.values()):
                if validation_func and not validation_func(result):
                    still_remaining.append((original_idx, item))
                else:
                    results[original_idx] = {
                        'result': result,
                        'processor': processor_name,
                        'cost': processor_info.get('cost_per_page', 0)
                    }
                    newly_completed.append(original_idx)
            
            remaining_items = still_remaining
            
            logging.info(f"Completed {len(newly_completed)} items with {processor_name}")
        
        return results
```

#### 1.3 Unified Caching System

```python
# /pipeline-documents/doc_processing/utils/unified_cache.py

import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Dict
import pickle
from datetime import datetime, timedelta

class UnifiedOCRCache:
    """Unified caching for all OCR processors."""
    
    def __init__(self, cache_dir: Path = None, ttl_days: int = 30):
        self.cache_dir = cache_dir or Path("data/cache/ocr")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)
    
    def _get_cache_key(self, 
                      file_path: Path, 
                      page_num: int, 
                      processor: str,
                      settings: Dict = None) -> str:
        """Generate unique cache key."""
        key_parts = [
            str(file_path),
            str(page_num),
            processor,
            json.dumps(settings or {}, sort_keys=True)
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, 
            file_path: Path, 
            page_num: int, 
            processor: str,
            settings: Dict = None) -> Optional[Dict]:
        """Retrieve cached OCR result."""
        cache_key = self._get_cache_key(file_path, page_num, processor, settings)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                
                # Check TTL
                if datetime.now() - cached_data['timestamp'] < self.ttl:
                    return cached_data['result']
                else:
                    cache_file.unlink()  # Remove expired cache
            except Exception as e:
                logging.warning(f"Cache read error: {e}")
        
        return None
    
    def set(self, 
            file_path: Path, 
            page_num: int, 
            processor: str,
            result: Dict,
            settings: Dict = None):
        """Cache OCR result."""
        cache_key = self._get_cache_key(file_path, page_num, processor, settings)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        cached_data = {
            'result': result,
            'timestamp': datetime.now(),
            'metadata': {
                'file': str(file_path),
                'page': page_num,
                'processor': processor,
                'settings': settings
            }
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cached_data, f)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)  # MB
        
        processor_counts = {}
        for cache_file in cache_files:
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    processor = data['metadata']['processor']
                    processor_counts[processor] = processor_counts.get(processor, 0) + 1
            except:
                pass
        
        return {
            'total_cached': len(cache_files),
            'cache_size_mb': round(total_size, 2),
            'by_processor': processor_counts
        }
```

### Phase 2: Smart OCR Router (Week 2)

#### 2.1 Intelligent OCR Router

```python
# /pipeline-documents/doc_processing/processors/smart_ocr_router.py

from typing import List, Dict, Optional
import logging
from pathlib import Path

class SmartOCRRouter:
    """
    Intelligent routing of pages to optimal OCR engines.
    Specifically optimized for AP course materials.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.preprocessor = ImagePreprocessor()
        self.cache = UnifiedOCRCache()
        self.parallel_processor = ParallelOCRProcessor()
        
        # Initialize processors
        self.processors = self._init_processors()
        
        # AP-specific patterns
        self.ap_patterns = {
            'unit_pages': r'Unit \d+|UNIT \d+|Exam Weighting',
            'skill_pages': r'Skill|Practice|CED\.[\d\w]+',
            'table_pages': r'Course at a Glance|Overview',
            'formula_pages': r'Equation|Formula|∑|∫|√'
        }
    
    def process_document(self, pdf_path: Path) -> Dict:
        """
        Process entire document with intelligent routing.
        """
        logging.info(f"Processing {pdf_path.name} with Smart OCR Router")
        
        # Load PDF and get page images
        pages = self._load_pdf_pages(pdf_path)
        
        # Classify all pages
        page_classifications = self.parallel_processor.process_pages_parallel(
            pages,
            self._classify_page,
            desc="Classifying pages"
        )
        
        # Group pages by recommended processor
        processor_groups = self._group_by_processor(page_classifications)
        
        # Process each group with appropriate processor
        all_results = {}
        
        for processor_name, page_indices in processor_groups.items():
            processor = self.processors[processor_name]
            
            # Check cache first
            cached_results = {}
            uncached_indices = []
            
            for idx in page_indices:
                cached = self.cache.get(pdf_path, idx, processor_name)
                if cached:
                    cached_results[idx] = cached
                else:
                    uncached_indices.append(idx)
            
            # Process uncached pages
            if uncached_indices:
                pages_to_process = [pages[idx] for idx in uncached_indices]
                
                results = self.parallel_processor.process_pages_parallel(
                    pages_to_process,
                    lambda page, idx: processor.process_page(page),
                    desc=f"OCR with {processor_name}"
                )
                
                # Cache results
                for idx, result in zip(uncached_indices, results.values()):
                    self.cache.set(pdf_path, idx, processor_name, result)
                    all_results[idx] = result
            
            # Add cached results
            all_results.update(cached_results)
        
        # Post-process for AP course structure
        structured_result = self._structure_ap_content(all_results)
        
        return structured_result
    
    def _classify_page(self, page_image) -> Dict:
        """
        Classify page and determine optimal processor.
        """
        # Preprocess for classification
        preprocessed = self.preprocessor.preprocess_for_ocr(
            page_image, 
            target_engine='classification'
        )
        
        # Get page features
        classification = self.preprocessor.classify_page_complexity(preprocessed)
        
        # Check for AP-specific content
        is_critical = self._is_critical_ap_page(preprocessed)
        
        # Determine processor
        if is_critical:
            recommended_processor = 'gpt4v'  # Highest accuracy for critical pages
        else:
            recommended_processor = classification['recommended_engine']
        
        return {
            'complexity': classification['complexity'],
            'features': classification['features'],
            'processor': recommended_processor,
            'is_critical': is_critical
        }
    
    def _is_critical_ap_page(self, page_image) -> bool:
        """
        Detect if page contains critical AP course information.
        """
        # Quick OCR with Tesseract to check content
        try:
            text = pytesseract.image_to_string(page_image)
            
            # Check for critical patterns
            for pattern_name, pattern in self.ap_patterns.items():
                if pattern_name in ['unit_pages', 'skill_pages']:
                    if re.search(pattern, text, re.IGNORECASE):
                        return True
        except:
            pass
        
        return False
```

### Phase 3: AP Courses Integration (Week 3)

#### 3.1 Enhanced AP Courses Pipeline

```python
# /Volumes/PortableSSD/ap-courses/notebooks/enhanced_ocr_pipeline.py

import sys
sys.path.append('/path/to/pipeline-documents')

from doc_processing.processors.smart_ocr_router import SmartOCRRouter
from doc_processing.utils.unified_cache import UnifiedOCRCache
import pandas as pd
from pathlib import Path
import json

class APCoursesEnhancedPipeline:
    """
    Enhanced OCR pipeline specifically for AP course materials.
    """
    
    def __init__(self, config_path: Path = None):
        self.config = self._load_config(config_path)
        self.router = SmartOCRRouter(self.config)
        self.cache = UnifiedOCRCache()
        
        # Cost tracking
        self.cost_tracker = {
            'tesseract': 0.0,
            'docling': 0.0,
            'gemini': 0.0002,
            'gpt4v': 0.01
        }
    
    def process_all_courses(self, reprocess_missing_only: bool = True):
        """
        Process all AP courses with enhanced pipeline.
        """
        course_pdfs = list(Path("data/input/course_pdfs").glob("**/*.pdf"))
        
        if reprocess_missing_only:
            # Load existing results
            existing_results = self._load_existing_results()
            
            # Identify courses with missing units
            courses_to_process = []
            for pdf in course_pdfs:
                course_name = pdf.stem
                if course_name in existing_results:
                    if not existing_results[course_name].get('units'):
                        courses_to_process.append(pdf)
                else:
                    courses_to_process.append(pdf)
        else:
            courses_to_process = course_pdfs
        
        logging.info(f"Processing {len(courses_to_process)} courses")
        
        results = {}
        total_cost = 0.0
        
        for pdf_path in tqdm(courses_to_process, desc="Processing courses"):
            try:
                # Process with smart router
                course_result = self.router.process_document(pdf_path)
                
                # Extract structured data
                structured_data = self._extract_ap_structure(course_result)
                
                # Validate extraction
                validation = self._validate_extraction(structured_data)
                
                # Calculate cost
                cost = self._calculate_cost(course_result)
                total_cost += cost
                
                results[pdf_path.stem] = {
                    'data': structured_data,
                    'validation': validation,
                    'cost': cost,
                    'processors_used': course_result.get('processors_used', {})
                }
                
                # Save intermediate results
                self._save_result(pdf_path.stem, structured_data)
                
            except Exception as e:
                logging.error(f"Error processing {pdf_path.name}: {str(e)}")
                results[pdf_path.stem] = {'error': str(e)}
        
        # Generate report
        self._generate_report(results, total_cost)
        
        return results
    
    def _extract_ap_structure(self, ocr_result: Dict) -> Dict:
        """
        Extract AP course structure from OCR results.
        """
        extracted = {
            'course_title': '',
            'units': [],
            'big_ideas': [],
            'skills': [],
            'course_at_glance': {}
        }
        
        # Combine all page texts
        full_text = '\n'.join([
            page_data.get('text', '') 
            for page_data in ocr_result.values()
        ])
        
        # Extract units with improved regex
        unit_pattern = r'Unit\s+(\d+)[:\s]+([^\n]+?)(?:\s*~?(\d+[-–]\d+)\s*Class\s*Periods?)?\s*(?:(\d+[-–]\d+)%\s*AP\s*Exam\s*Weighting)?'
        
        units = re.findall(unit_pattern, full_text, re.IGNORECASE | re.MULTILINE)
        
        for unit_match in units:
            unit_num, title, periods, weight = unit_match
            extracted['units'].append({
                'number': int(unit_num),
                'title': title.strip(),
                'class_periods': periods,
                'exam_weight': weight
            })
        
        # Extract topics with skills
        topic_pattern = r'(\d+\.\d+)\s+([^(\n]+?)(?:\s*\(([^)]+)\))?'
        topics = re.findall(topic_pattern, full_text)
        
        # Group topics by unit
        for unit in extracted['units']:
            unit['topics'] = []
            unit_prefix = f"{unit['number']}."
            
            for topic_num, topic_title, skills in topics:
                if topic_num.startswith(unit_prefix):
                    unit['topics'].append({
                        'number': topic_num,
                        'title': topic_title.strip(),
                        'skills': skills.split(',') if skills else []
                    })
        
        return extracted
    
    def _generate_report(self, results: Dict, total_cost: float):
        """
        Generate comprehensive processing report.
        """
        report = {
            'summary': {
                'total_courses': len(results),
                'successful': sum(1 for r in results.values() if 'error' not in r),
                'failed': sum(1 for r in results.values() if 'error' in r),
                'total_cost': total_cost,
                'avg_cost_per_course': total_cost / len(results) if results else 0
            },
            'missing_units_fixed': [],
            'processor_usage': {},
            'cost_breakdown': {}
        }
        
        # Analyze results
        for course_name, result in results.items():
            if 'error' not in result:
                # Check if previously missing units were found
                if result['data']['units']:
                    report['missing_units_fixed'].append(course_name)
                
                # Track processor usage
                for processor, pages in result.get('processors_used', {}).items():
                    if processor not in report['processor_usage']:
                        report['processor_usage'][processor] = 0
                    report['processor_usage'][processor] += len(pages)
        
        # Cost analysis
        baseline_cost = len(results) * 300 * 0.01  # If all pages used GPT-4V
        report['cost_breakdown'] = {
            'actual_cost': total_cost,
            'baseline_cost': baseline_cost,
            'savings': baseline_cost - total_cost,
            'savings_percentage': ((baseline_cost - total_cost) / baseline_cost * 100) if baseline_cost > 0 else 0
        }
        
        # Save report
        report_path = Path("data/output/processing_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logging.info(f"Processing complete. Report saved to {report_path}")
        logging.info(f"Total cost: ${total_cost:.2f} (saved ${report['cost_breakdown']['savings']:.2f})")
```

### Phase 4: Production Deployment (Week 4)

#### 4.1 Production Configuration

```yaml
# /pipeline-documents/config/ocr_production.yaml

ocr_pipeline:
  # Processor priorities (order matters)
  processors:
    - name: tesseract
      enabled: true
      priority: 1
      cost_per_page: 0.0
      settings:
        preprocess: true
        languages: ["eng", "fra", "spa"]
        psm: 3  # Page segmentation mode
        
    - name: docling
      enabled: true
      priority: 2
      cost_per_page: 0.0
      settings:
        extract_tables: true
        extract_figures: true
        
    - name: gemini
      enabled: true
      priority: 3
      cost_per_page: 0.0002
      settings:
        model: "gemini-1.5-pro"
        temperature: 0.1
        
    - name: gpt4v
      enabled: true
      priority: 4
      cost_per_page: 0.01
      settings:
        model: "gpt-4-vision-preview"
        max_tokens: 4000
        temperature: 0.1

  # Performance settings
  performance:
    max_workers: 8
    use_processes: false  # Use threads
    batch_size: 10
    cache_ttl_days: 30
    
  # Image preprocessing
  preprocessing:
    auto_scale: true
    target_dpi: 300
    denoise: true
    deskew: true
    
  # Validation rules
  validation:
    min_text_length: 100
    required_keywords:
      ap_courses: ["unit", "topic", "skill", "big idea"]
      general: ["chapter", "section", "page"]
    confidence_threshold: 0.8
    
  # Cost controls
  cost_limits:
    max_cost_per_document: 5.0
    daily_budget: 100.0
    require_approval_above: 10.0
```

#### 4.2 Monitoring and Analytics

```python
# /pipeline-documents/doc_processing/utils/ocr_analytics.py

from datetime import datetime
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

class OCRAnalytics:
    """Analytics and monitoring for OCR pipeline."""
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path("data/logs/ocr")
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_processing(self, document: str, results: Dict):
        """Log processing results for analytics."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'document': document,
            'total_pages': len(results),
            'processors_used': {},
            'total_cost': 0.0,
            'processing_time': 0.0,
            'errors': []
        }
        
        # Aggregate results
        for page_num, page_result in results.items():
            processor = page_result.get('processor', 'unknown')
            if processor not in log_entry['processors_used']:
                log_entry['processors_used'][processor] = 0
            log_entry['processors_used'][processor] += 1
            log_entry['total_cost'] += page_result.get('cost', 0.0)
        
        # Save to daily log
        log_file = self.log_dir / f"ocr_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def generate_dashboard(self, days: int = 30) -> Path:
        """Generate analytics dashboard."""
        # Load logs
        logs = self._load_logs(days)
        df = pd.DataFrame(logs)
        
        # Create visualizations
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Cost over time
        daily_costs = df.groupby(df['timestamp'].dt.date)['total_cost'].sum()
        axes[0, 0].plot(daily_costs.index, daily_costs.values)
        axes[0, 0].set_title('Daily OCR Costs')
        axes[0, 0].set_ylabel('Cost ($)')
        
        # 2. Processor usage
        processor_usage = {}
        for _, row in df.iterrows():
            for proc, count in row['processors_used'].items():
                processor_usage[proc] = processor_usage.get(proc, 0) + count
        
        axes[0, 1].bar(processor_usage.keys(), processor_usage.values())
        axes[0, 1].set_title('OCR Engine Usage')
        axes[0, 1].set_ylabel('Pages Processed')
        
        # 3. Success rate
        success_rate = (df['errors'].str.len() == 0).mean() * 100
        axes[1, 0].text(0.5, 0.5, f'{success_rate:.1f}%', 
                       fontsize=48, ha='center', va='center')
        axes[1, 0].set_title('Success Rate')
        axes[1, 0].axis('off')
        
        # 4. Cost savings
        baseline_cost = df['total_pages'].sum() * 0.01  # If all GPT-4V
        actual_cost = df['total_cost'].sum()
        savings_pct = (baseline_cost - actual_cost) / baseline_cost * 100
        
        axes[1, 1].text(0.5, 0.5, f'{savings_pct:.1f}%', 
                       fontsize=48, ha='center', va='center')
        axes[1, 1].set_title('Cost Savings vs GPT-4V Only')
        axes[1, 1].axis('off')
        
        # Save dashboard
        dashboard_path = self.log_dir / f"dashboard_{datetime.now().strftime('%Y%m%d')}.png"
        plt.tight_layout()
        plt.savefig(dashboard_path)
        
        return dashboard_path
```

## Expected Outcomes

### 1. Cost Reduction
- **Current**: $0.01/page (GPT-4V only) = ~$114 for 38 courses
- **Optimized**: ~$0.002/page average = ~$23 for 38 courses
- **Annual Savings**: ~$91 (80% reduction)

### 2. Performance Improvement
- **Sequential → Parallel**: 3-5x faster processing
- **Caching**: 100% faster for re-runs
- **Smart Routing**: Process simple pages in <1 second

### 3. Accuracy Enhancement
- **Missing Units**: Fallback chain should recover 90%+ of missing data
- **Tables/Columns**: Proper structure preservation
- **Validation**: Automatic quality checks

### 4. Operational Benefits
- **Monitoring**: Real-time cost and performance tracking
- **Flexibility**: Easy to add new OCR engines
- **Reliability**: No single point of failure

## Implementation Checklist

### Week 1
- [ ] Set up unified preprocessing module
- [ ] Implement parallel processing framework
- [ ] Create unified caching system
- [ ] Test with sample AP course PDFs

### Week 2
- [ ] Build smart OCR router
- [ ] Implement page classification
- [ ] Create fallback chain logic
- [ ] Benchmark performance

### Week 3
- [ ] Integrate with AP courses pipeline
- [ ] Process courses with missing units
- [ ] Validate extraction quality
- [ ] Generate cost comparison

### Week 4
- [ ] Deploy to production
- [ ] Set up monitoring
- [ ] Create documentation
- [ ] Train team on new pipeline

This unified approach combines the best of both repositories to create a production-ready, cost-effective OCR pipeline optimized for your AP courses use case.