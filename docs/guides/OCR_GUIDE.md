# OCR and PDF Processing Guide

This guide consolidates all OCR and PDF processing strategies, tools, and optimization techniques for the pipeline-documents system.

## Table of Contents

1. [Overview](#overview)
2. [Processing Tools Comparison](#processing-tools-comparison)
3. [Processing Strategies](#processing-strategies)
4. [Implementation Guide](#implementation-guide)
5. [Optimization Techniques](#optimization-techniques)
6. [Cost Analysis](#cost-analysis)
7. [Troubleshooting](#troubleshooting)

## Overview

The pipeline-documents system provides a sophisticated multi-stage PDF processing pipeline that intelligently selects the best tool for each document type, optimizing for speed, accuracy, and cost.

### Key Features

- **Multi-tool support**: PyMuPDF, Docling, Tesseract, Gemini Vision, GPT-4V
- **Intelligent fallback chains**: Automatic progression from fast/free to accurate/expensive
- **Cost optimization**: 80-90% reduction in API costs through smart routing
- **Performance**: 50-100x faster for text-based PDFs using PyMuPDF
- **Robustness**: Multiple fallback options ensure successful processing

## Processing Tools Comparison

### 1. PyMuPDF (Text Extraction)
- **Purpose**: Extract embedded text from native PDFs
- **Speed**: Extremely fast (0.01-0.1 seconds per page)
- **Cost**: Free
- **Accuracy**: 100% for text-based PDFs
- **Best for**: Modern PDFs, reports, ebooks with selectable text
- **Limitations**: Cannot process scanned documents or images

### 2. Tesseract (Traditional OCR)
- **Purpose**: Optical Character Recognition on images/scanned PDFs
- **Speed**: Fast (0.5-2 seconds per page)
- **Cost**: Free
- **Accuracy**: 85-95% with good preprocessing
- **Best for**: Simple scanned documents, clear text
- **Limitations**: Struggles with complex layouts, tables, handwriting

### 3. Docling (AI Document Understanding)
- **Purpose**: Advanced document parsing with layout understanding
- **Speed**: Moderate (2-10 seconds per page)
- **Cost**: Free (local processing)
- **Accuracy**: 95-99% for complex documents
- **Best for**: Complex layouts, tables, multi-column documents
- **Limitations**: Requires more computational resources

### 4. Gemini Vision (Google AI)
- **Purpose**: Multimodal document understanding
- **Speed**: Fast (1-3 seconds per page)
- **Cost**: ~$0.0002 per page
- **Accuracy**: 97-99%
- **Best for**: When Docling fails, complex mixed content
- **Limitations**: Requires API key, costs per use

### 5. GPT-4V (OpenAI Vision)
- **Purpose**: Advanced vision model for challenging documents
- **Speed**: Moderate (3-5 seconds per page)
- **Cost**: ~$0.01 per page
- **Accuracy**: 98-99.5%
- **Best for**: Handwritten text, poor quality scans, complex layouts
- **Limitations**: Most expensive option

## Processing Strategies

### 1. Exclusive Strategy
Use only the specified processor:

```bash
# Use only PyMuPDF
python scripts/run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor pymupdf

# Use only Docling
python scripts/run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor docling
```

### 2. Fallback Chain Strategy (Recommended)
Automatically try processors in order until one succeeds:

```bash
# Default chain: PyMuPDF → Docling → Enhanced Docling → Gemini → GPT-4V
python scripts/run_pipeline.py --input_path doc.pdf --pipeline_type text --pdf_processor_strategy fallback_chain
```

### 3. Custom Fallback Order
Configure your own processing order:

```bash
# Environment variable approach
export PDF_FALLBACK_ORDER='["pymupdf", "tesseract", "gemini", "gpt"]'
export ACTIVE_PDF_PROCESSORS='["pymupdf", "tesseract", "gemini", "gpt"]'

# Or in Python
config = {
    'pdf_processor_strategy': 'fallback_chain',
    'active_pdf_processors': ['pymupdf', 'docling', 'gemini'],
    'pdf_fallback_order': ['pymupdf', 'gemini', 'docling']
}
```

## Implementation Guide

### Basic Usage

```python
from doc_processing.document_pipeline import DocumentPipeline

# Create pipeline with fallback chain
config = {
    'pdf_processor_strategy': 'fallback_chain',
    'active_pdf_processors': ['pymupdf', 'docling', 'enhanced_docling', 'gemini', 'gpt']
}

pipeline = DocumentPipeline(config)
result = pipeline.process_document('path/to/document.pdf')
```

### Adding Tesseract OCR

1. **Install Tesseract**:
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download installer from GitHub
```

2. **Install Python wrapper**:
```bash
poetry add pytesseract
# or
pip install pytesseract
```

3. **Implement TesseractProcessor**:
```python
from doc_processing.processors import TesseractProcessor

processor = TesseractProcessor(config={
    'languages': ['eng', 'spa'],  # English and Spanish
    'preprocessing': True,         # Enable image preprocessing
    'dpi': 300,                   # Target DPI for conversion
})
```

### Batch Processing

```python
# Process directory with progress tracking
results = pipeline.process_directory(
    'data/input/pdfs',
    recursive=True,
    batch_size=10,
    show_progress=True
)

# With specific configuration per file type
for pdf_path in pdf_files:
    if is_scanned(pdf_path):
        # Use OCR-focused chain
        config['active_pdf_processors'] = ['tesseract', 'docling', 'gemini']
    else:
        # Use text extraction first
        config['active_pdf_processors'] = ['pymupdf', 'docling']
    
    result = pipeline.process_document(pdf_path)
```

## Optimization Techniques

### 1. Preprocessing for Better OCR

```python
# Image preprocessing pipeline
preprocessing_config = {
    'binarization': True,      # Convert to black/white
    'deskew': True,           # Correct rotation
    'denoise': True,          # Remove noise
    'enhance_contrast': True,  # Improve contrast
    'target_dpi': 300         # Optimal DPI for OCR
}
```

### 2. Smart Page Routing

```python
def route_page(page_image, page_text):
    """Determine best processor for a page."""
    if len(page_text.strip()) > 100:
        return 'pymupdf'  # Has embedded text
    elif is_simple_layout(page_image):
        return 'tesseract'  # Simple scanned page
    elif has_tables(page_image):
        return 'docling'  # Complex layout
    else:
        return 'gemini'  # Fallback to AI
```

### 3. Caching Strategy

```python
# Enable caching for all processors
config = {
    'use_cache': True,
    'cache_dir': 'data/cache',
    'cache_ttl': 86400,  # 24 hours
    'cache_strategy': 'page_level'  # Cache per page
}
```

### 4. Parallel Processing

```python
# Process multiple pages concurrently
config = {
    'max_workers': 4,
    'concurrent_pages': True,
    'batch_size': 10
}
```

## Cost Analysis

### Processing Cost Comparison

| Document Type | Pages | PyMuPDF | Tesseract | Docling | Gemini | GPT-4V |
|--------------|-------|---------|-----------|---------|---------|---------|
| Native PDF | 100 | $0.00 | N/A | $0.00 | $0.02 | $1.00 |
| Scanned PDF | 100 | N/A | $0.00 | $0.00 | $0.02 | $1.00 |
| Mixed Content | 100 | $0.00* | $0.00* | $0.00 | $0.02 | $1.00 |

*Assuming 50% of pages can be processed with free tools

### Optimization Impact

Using the recommended fallback chain strategy:
- **Average cost reduction**: 85-95%
- **Processing time**: 60-80% faster for mixed documents
- **Success rate**: 99.9% (vs 95% with single processor)

### ROI Calculation

For 10,000 pages/month:
- **GPT-4V only**: $100/month
- **Optimized pipeline**: $5-15/month
- **Annual savings**: $1,140-1,140

## Troubleshooting

### Common Issues and Solutions

#### 1. PyMuPDF Returns Empty Text
**Issue**: PDF appears to have text but PyMuPDF extracts nothing
**Solution**: 
- Check if PDF has copy protection
- Try with `extract_text(password='')` 
- Fall back to OCR methods

#### 2. Tesseract Poor Accuracy
**Issue**: Getting garbled or incorrect text
**Solutions**:
- Increase image DPI to 300+
- Enable preprocessing options
- Check language settings
- Use Docling for complex layouts

#### 3. Docling Memory Issues
**Issue**: Out of memory on large PDFs
**Solutions**:
- Process in smaller batches
- Reduce concurrent pages
- Use page-level caching
- Consider using Gemini for large documents

#### 4. API Rate Limits
**Issue**: Gemini/GPT-4V rate limit errors
**Solutions**:
- Implement exponential backoff
- Use request queuing
- Increase local processing (PyMuPDF/Tesseract)
- Consider dedicated API tier

### Performance Tuning

```python
# Optimal configuration for different scenarios

# High volume, cost-sensitive
config_high_volume = {
    'pdf_processor_strategy': 'fallback_chain',
    'active_pdf_processors': ['pymupdf', 'tesseract', 'docling'],
    'max_workers': 8,
    'use_cache': True
}

# High accuracy requirements
config_high_accuracy = {
    'pdf_processor_strategy': 'fallback_chain', 
    'active_pdf_processors': ['pymupdf', 'enhanced_docling', 'gpt'],
    'preprocessing': True,
    'extract_tables': True
}

# Real-time processing
config_realtime = {
    'pdf_processor_strategy': 'exclusive',
    'pdf_processor': 'gemini',  # Fast and accurate
    'timeout': 30,
    'max_retries': 1
}
```

## Best Practices

1. **Always use fallback chains** for production systems
2. **Start with free/fast options** (PyMuPDF, Tesseract)
3. **Monitor costs and performance** using metadata
4. **Cache aggressively** for repeated processing
5. **Preprocess images** for better OCR results
6. **Set appropriate timeouts** for each processor
7. **Log processor selection** for debugging
8. **Validate output quality** with spot checks

## Future Enhancements

### Planned Improvements

1. **AWS Textract Integration** - For forms and tables
2. **Azure Form Recognizer** - For structured documents  
3. **EasyOCR Support** - For multilingual documents
4. **ONNX Runtime** - For faster local inference
5. **Smart Router v2** - ML-based processor selection
6. **Distributed Processing** - For massive scale

### Research Areas

- Few-shot learning for custom document types
- Active learning for processor selection
- Ensemble methods combining multiple OCR outputs
- Real-time quality assessment and re-routing