"""Utilities for detecting and reconstructing multi-column text in PDFs."""
import logging
from typing import Any, Dict, List, Tuple, Optional
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

def detect_columns(blocks: List[Dict[str, Any]], page_width: float, threshold: float = 0.3) -> List[List[Dict[str, Any]]]:
    """
    Detect columns in a page based on text block positions.
    
    Args:
        blocks: List of text blocks with position information (x0, x1, y0, y1)
        page_width: Width of the page
        threshold: Threshold for column separation (as a fraction of page width)
        
    Returns:
        List of columns, where each column is a list of blocks
    """
    if not blocks:
        return []
    
    # Extract x-coordinates of blocks
    x_centers = [((block['x0'] + block['x1']) / 2) / page_width for block in blocks if 'x0' in block and 'x1' in block]
    
    if not x_centers:
        return [blocks]  # No position information, assume single column
    
    # Use histogram to detect column centers
    hist, bin_edges = np.histogram(x_centers, bins=10)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Find peaks in histogram (column centers)
    peaks = []
    for i in range(1, len(hist) - 1):
        if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > len(blocks) * threshold:
            peaks.append(bin_centers[i])
    
    if not peaks:
        return [blocks]  # No clear columns detected
    
    # Sort peaks from left to right
    peaks.sort()
    
    # Assign blocks to columns
    columns = [[] for _ in range(len(peaks))]
    for block in blocks:
        if 'x0' not in block or 'x1' not in block:
            # Skip blocks without position information
            continue
            
        x_center = ((block['x0'] + block['x1']) / 2) / page_width
        
        # Find closest peak
        distances = [abs(x_center - peak) for peak in peaks]
        closest_peak_idx = distances.index(min(distances))
        
        columns[closest_peak_idx].append(block)
    
    # Sort blocks within each column by y-coordinate (top to bottom)
    for i in range(len(columns)):
        columns[i].sort(key=lambda block: block.get('y0', 0))
    
    # Check if any blocks were not assigned (no position info)
    unassigned = [block for block in blocks if 'x0' not in block or 'x1' not in block]
    if unassigned:
        logger.warning(f"Found {len(unassigned)} blocks without position information")
        # Add unassigned blocks to the first column
        if columns:
            columns[0].extend(unassigned)
        else:
            columns.append(unassigned)
    
    return columns

def reconstruct_text_flow(columns: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Reconstruct text flow from detected columns.
    
    Args:
        columns: List of columns, where each column is a list of blocks
        
    Returns:
        List of blocks in reading order
    """
    if not columns:
        return []
    
    # If only one column, return it as is
    if len(columns) == 1:
        return columns[0]
    
    # Determine if the document has a header or footer
    # This is a simplified approach - in a real implementation, we would need
    # more sophisticated detection of headers and footers
    all_blocks = [block for column in columns for block in column]
    y_positions = [block.get('y0', 0) for block in all_blocks if 'y0' in block]
    
    if not y_positions:
        # No position information, return blocks as is
        return all_blocks
    
    min_y = min(y_positions)
    max_y = max(y_positions)
    page_height = max_y - min_y
    
    # Assume header is in top 10% of page
    header_threshold = min_y + page_height * 0.1
    # Assume footer is in bottom 10% of page
    footer_threshold = max_y - page_height * 0.1
    
    # Extract header, footer, and main content
    header_blocks = []
    footer_blocks = []
    main_content_columns = []
    
    for column in columns:
        column_header = []
        column_footer = []
        column_main = []
        
        for block in column:
            y0 = block.get('y0', 0)
            if y0 < header_threshold:
                column_header.append(block)
            elif y0 > footer_threshold:
                column_footer.append(block)
            else:
                column_main.append(block)
        
        header_blocks.extend(column_header)
        footer_blocks.extend(column_footer)
        main_content_columns.append(column_main)
    
    # Sort header and footer blocks by x-coordinate (left to right)
    header_blocks.sort(key=lambda block: block.get('x0', 0))
    footer_blocks.sort(key=lambda block: block.get('x0', 0))
    
    # Reconstruct main content in reading order (left to right, top to bottom)
    main_content_blocks = []
    for column in main_content_columns:
        main_content_blocks.extend(column)
    
    # Combine header, main content, and footer
    result = header_blocks + main_content_blocks + footer_blocks
    
    return result

def extract_text_from_blocks(blocks: List[Dict[str, Any]]) -> str:
    """
    Extract text from blocks in the given order.
    
    Args:
        blocks: List of text blocks
        
    Returns:
        Extracted text
    """
    text_parts = []
    for block in blocks:
        if 'text' in block and block['text']:
            text_parts.append(block['text'])
    
    return '\n'.join(text_parts)

def process_page_with_column_detection(page: Any) -> str:
    """
    Process a page with column detection and text flow reconstruction.
    
    Args:
        page: Page object with blocks attribute
        
    Returns:
        Processed text
    """
    if not hasattr(page, 'blocks'):
        logger.warning("Page does not have 'blocks' attribute")
        return ""
    
    # Extract blocks with position information
    blocks = []
    page_width = getattr(page, 'width', 1.0)  # Default to 1.0 if width not available
    
    for block in page.blocks:
        block_dict = {
            'text': block.text if hasattr(block, 'text') else "",
        }
        
        # Extract position information if available
        if hasattr(block, 'bbox'):
            x0, y0, x1, y1 = block.bbox
            block_dict.update({
                'x0': x0,
                'y0': y0,
                'x1': x1,
                'y1': y1,
            })
        
        blocks.append(block_dict)
    
    # Detect columns
    columns = detect_columns(blocks, page_width)
    
    # Reconstruct text flow
    ordered_blocks = reconstruct_text_flow(columns)
    
    # Extract text
    text = extract_text_from_blocks(ordered_blocks)
    
    return text

def process_docling_doc_with_column_detection(doc: Any) -> str:
    """
    Process a Docling document with column detection and text flow reconstruction.
    
    Args:
        doc: Docling document object
        
    Returns:
        Processed text
    """
    if not hasattr(doc, 'pages'):
        logger.warning("Document does not have 'pages' attribute")
        return ""
    
    page_texts = []
    for page in doc.pages:
        page_text = process_page_with_column_detection(page)
        page_texts.append(page_text)
    
    return '\n\n'.join(page_texts)

def analyze_column_structure(doc: Any) -> Dict[int, int]:
    """
    Analyze the column structure of a document.
    
    Args:
        doc: Docling document object
        
    Returns:
        Dictionary mapping page numbers to number of columns
    """
    if not hasattr(doc, 'pages'):
        logger.warning("Document does not have 'pages' attribute")
        return {}
    
    page_columns = {}
    for i, page in enumerate(doc.pages):
        if not hasattr(page, 'blocks'):
            continue
            
        # Extract blocks with position information
        blocks = []
        page_width = getattr(page, 'width', 1.0)
        
        for block in page.blocks:
            block_dict = {'text': getattr(block, 'text', "")}
            
            # Extract position information if available
            if hasattr(block, 'bbox'):
                x0, y0, x1, y1 = block.bbox
                block_dict.update({
                    'x0': x0,
                    'y0': y0,
                    'x1': x1,
                    'y1': y1,
                })
            
            blocks.append(block_dict)
        
        # Detect columns
        columns = detect_columns(blocks, page_width)
        
        # Store number of columns
        page_columns[i + 1] = len(columns)
    
    return page_columns
