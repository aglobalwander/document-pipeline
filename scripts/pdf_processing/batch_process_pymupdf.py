#!/usr/bin/env python3
"""
Batch process standards PDFs with PyMuPDF, saving progress as we go.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List
import fitz  # PyMuPDF

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from doc_processing.document_pipeline import DocumentPipeline


def process_pdf(pdf_path: Path, output_dir: Path) -> Dict:
    """Process a single PDF and return result."""
    try:
        # First test with PyMuPDF directly
        doc = fitz.open(str(pdf_path))
        total_text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            total_text += text
        
        doc.close()
        
        # Check if meaningful text was extracted
        if len(total_text.strip()) < 100:
            return {
                'status': 'failed',
                'error': 'Insufficient text extracted',
                'text_length': len(total_text)
            }
        
        # Use pipeline to save the output
        config = {
            'pipeline_type': 'text',
            'pdf_processor_strategy': 'exclusive',
            'pdf_processor': 'pymupdf',
            'default_pdf_processor': 'pymupdf',
            'output_dir': str(output_dir)
        }
        
        pipeline = DocumentPipeline(config)
        result = pipeline.process_document(str(pdf_path))
        
        if result and 'error' not in result:
            # Save the output
            output_filename = f"{pdf_path.stem}_output.txt"
            output_path = output_dir / output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.get('content', ''))
            
            return {
                'status': 'success',
                'text_length': len(total_text),
                'output_file': str(output_path)
            }
        else:
            return {
                'status': 'failed',
                'error': result.get('error', 'Unknown error'),
                'text_length': len(total_text)
            }
            
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e),
            'text_length': 0
        }


def main():
    """Process all PDFs in batches."""
    input_base = Path("data/input/pdfs/standards")
    output_base = Path("data/output/text/standards_pymupdf")
    progress_file = Path("data/output/pymupdf_processing_progress.json")
    
    # Load previous progress if exists
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        print(f"Resuming from previous progress: {progress['processed']} files already processed")
    else:
        progress = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'processed_files': set(),
            'failed_pdfs': []
        }
    
    # Convert processed_files to set if loading from JSON
    if isinstance(progress['processed_files'], list):
        progress['processed_files'] = set(progress['processed_files'])
    
    # Get all PDFs
    all_pdfs = list(input_base.rglob("*.pdf"))
    print(f"Found {len(all_pdfs)} PDFs total")
    
    # Filter out already processed
    pdfs_to_process = [p for p in all_pdfs if str(p) not in progress['processed_files']]
    print(f"{len(pdfs_to_process)} PDFs remaining to process")
    
    if not pdfs_to_process:
        print("All PDFs already processed!")
        return
    
    # Process in batches
    batch_size = 10
    for i in range(0, len(pdfs_to_process), batch_size):
        batch = pdfs_to_process[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} files)...")
        
        for pdf_path in batch:
            # Get framework name from parent directory
            framework_name = pdf_path.parent.name
            framework_output = output_base / framework_name
            framework_output.mkdir(parents=True, exist_ok=True)
            
            print(f"  Processing: {pdf_path.name}...", end=' ')
            
            result = process_pdf(pdf_path, framework_output)
            
            progress['processed'] += 1
            progress['processed_files'].add(str(pdf_path))
            
            if result['status'] == 'success':
                progress['successful'] += 1
                print(f"✅ ({result['text_length']} chars)")
            else:
                progress['failed'] += 1
                progress['failed_pdfs'].append({
                    'framework': framework_name,
                    'filename': pdf_path.name,
                    'path': str(pdf_path),
                    'error': result['error'],
                    'text_length': result['text_length']
                })
                print(f"❌ ({result['error']})")
        
        # Save progress after each batch
        save_data = progress.copy()
        save_data['processed_files'] = list(progress['processed_files'])
        with open(progress_file, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        print(f"Progress saved. Total processed: {progress['processed']}/{len(all_pdfs)}")
        
        # Small delay between batches
        if i + batch_size < len(pdfs_to_process):
            time.sleep(1)
    
    # Print final summary
    print("\n" + "="*70)
    print("PROCESSING COMPLETE")
    print("="*70)
    print(f"Total PDFs processed: {progress['processed']}")
    print(f"Successful: {progress['successful']} ({progress['successful']/progress['processed']*100:.1f}%)")
    print(f"Failed: {progress['failed']} ({progress['failed']/progress['processed']*100:.1f}%)")
    
    # Save final results
    results_file = output_base / 'pymupdf_batch_results.json'
    save_data = progress.copy()
    save_data['processed_files'] = list(progress['processed_files'])
    with open(results_file, 'w') as f:
        json.dump(save_data, f, indent=2)
    
    # Create failed PDFs list
    if progress['failed_pdfs']:
        failed_list_path = output_base / 'failed_pdfs_list.txt'
        with open(failed_list_path, 'w') as f:
            f.write("PDFs that PyMuPDF could not process\n")
            f.write("="*70 + "\n")
            f.write(f"Total: {progress['failed']} out of {progress['processed']} PDFs\n\n")
            
            # Group by framework
            by_framework = {}
            for pdf in progress['failed_pdfs']:
                fw = pdf['framework']
                if fw not in by_framework:
                    by_framework[fw] = []
                by_framework[fw].append(pdf)
            
            for framework, pdfs in sorted(by_framework.items()):
                f.write(f"\n{framework.upper()} ({len(pdfs)} files)\n")
                f.write("-"*len(framework) + "\n")
                for pdf in pdfs:
                    f.write(f"  • {pdf['filename']}\n")
                    f.write(f"    Error: {pdf['error']}\n\n")
        
        print(f"\nFailed PDFs list saved to: {failed_list_path}")


if __name__ == "__main__":
    main()