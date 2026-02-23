#!/usr/bin/env python
"""
Generate quality metrics from PDF processing logs and outputs.

This script analyzes processing logs and output files to generate
quality metrics that help track improvements between runs.

Usage:
    python scripts/generate_quality_metrics.py --log_file data/output/processing_log_*.txt
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate quality metrics from PDF processing logs'
    )

    parser.add_argument('--log_file', type=str, required=True,
                        help='Path to the processing log file')

    parser.add_argument('--output_dir', type=str, default='data/output/markdown',
                        help='Directory containing markdown output files')

    parser.add_argument('--output_file', type=str, default=None,
                        help='Output file for metrics (default: processing_summary_<timestamp>.json)')

    parser.add_argument('--min_output_size', type=int, default=1000,
                        help='Minimum expected output size in characters (default: 1000)')

    parser.add_argument('--slow_threshold', type=int, default=60,
                        help='Processing time threshold in seconds to flag as slow (default: 60)')

    return parser.parse_args()


def parse_log_file(log_file: str) -> Dict[str, Any]:
    """Parse the processing log file to extract processing information."""

    if not os.path.exists(log_file):
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)

    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    # Extract timestamp from log file name
    timestamp_match = re.search(r'processing_log_(\d{8}_\d{6})', log_file)
    run_id = timestamp_match.group(1) if timestamp_match else datetime.now().strftime("%Y%m%d_%H%M%S")

    # Parse processing results (handle ANSI color codes)
    success_pattern = r'✓ SUCCESS.*?:\s*(.+?)\.pdf\s*\((\d+)s\)'
    failed_pattern = r'✗ FAILED.*?:\s*(.+?)\.pdf\s*\((\d+)s\)'

    successful_files = []
    failed_files = []

    for match in re.finditer(success_pattern, log_content):
        filename = match.group(1) + '.pdf'
        duration = int(match.group(2))
        successful_files.append({
            'filename': filename,
            'status': 'success',
            'processing_time': duration
        })

    for match in re.finditer(failed_pattern, log_content):
        filename = match.group(1) + '.pdf'
        duration = int(match.group(2))
        failed_files.append({
            'filename': filename,
            'status': 'failed',
            'processing_time': duration
        })

    return {
        'run_id': run_id,
        'successful_files': successful_files,
        'failed_files': failed_files
    }


def analyze_output_files(output_dir: str, processed_files: List[Dict], min_size: int) -> Dict[str, Any]:
    """Analyze output files to detect quality issues."""

    quality_flags = {
        'short_outputs': [],
        'missing_outputs': [],
        'large_outputs': []
    }

    file_details = []

    for file_info in processed_files:
        if file_info['status'] != 'success':
            continue

        # Construct expected output filename
        base_name = file_info['filename'].replace('.pdf', '')
        markdown_file = os.path.join(output_dir, f"{base_name}_docling.md")

        if not os.path.exists(markdown_file):
            quality_flags['missing_outputs'].append(file_info['filename'])
            continue

        # Analyze file size
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
            size = len(content)

        # Flag if output is suspiciously short
        if size < min_size:
            quality_flags['short_outputs'].append(file_info['filename'])

        # Track very large outputs (might indicate processing issues)
        if size > 500000:  # 500KB
            quality_flags['large_outputs'].append(file_info['filename'])

        file_details.append({
            'filename': file_info['filename'],
            'status': file_info['status'],
            'processing_time': file_info['processing_time'],
            'output_size_chars': size,
            'output_file': markdown_file
        })

    return quality_flags, file_details


def generate_metrics(args) -> Dict[str, Any]:
    """Generate comprehensive quality metrics."""

    # Parse log file
    log_data = parse_log_file(args.log_file)

    all_files = log_data['successful_files'] + log_data['failed_files']
    total_files = len(all_files)
    successful_count = len(log_data['successful_files'])
    failed_count = len(log_data['failed_files'])

    # Calculate average processing time
    if log_data['successful_files']:
        avg_time = sum(f['processing_time'] for f in log_data['successful_files']) / len(log_data['successful_files'])
    else:
        avg_time = 0

    # Analyze output files
    quality_flags, file_details = analyze_output_files(
        args.output_dir,
        log_data['successful_files'],
        args.min_output_size
    )

    # Flag slow processing files
    slow_files = [
        f['filename'] for f in all_files
        if f['processing_time'] > args.slow_threshold
    ]

    if slow_files:
        quality_flags['slow_processing'] = slow_files

    # Compile metrics
    metrics = {
        'run_date': datetime.now().strftime("%Y-%m-%d"),
        'run_id': log_data['run_id'],
        'total_files': total_files,
        'successful': successful_count,
        'failed': failed_count,
        'success_rate_percent': round((successful_count / total_files * 100), 1) if total_files > 0 else 0,
        'avg_processing_time_seconds': round(avg_time, 1),
        'quality_flags': quality_flags,
        'failed_files': [f['filename'] for f in log_data['failed_files']],
        'file_details': file_details
    }

    return metrics


def print_summary(metrics: Dict[str, Any]):
    """Print a human-readable summary of the metrics."""

    print("\n" + "=" * 60)
    print("QUALITY METRICS SUMMARY")
    print("=" * 60)
    print(f"Run ID: {metrics['run_id']}")
    print(f"Date: {metrics['run_date']}")
    print()
    print(f"Total Files: {metrics['total_files']}")
    print(f"Successful: {metrics['successful']}")
    print(f"Failed: {metrics['failed']}")
    print(f"Success Rate: {metrics['success_rate_percent']}%")
    print(f"Avg Processing Time: {metrics['avg_processing_time_seconds']}s")
    print()

    # Print quality flags
    flags = metrics['quality_flags']
    total_flags = sum(len(v) for v in flags.values() if isinstance(v, list))

    if total_flags == 0:
        print("✓ No quality issues detected!")
    else:
        print(f"⚠ Quality Issues Detected: {total_flags}")
        print()

        if flags.get('short_outputs'):
            print(f"  Short Outputs ({len(flags['short_outputs'])}):")
            for f in flags['short_outputs']:
                print(f"    - {f}")

        if flags.get('missing_outputs'):
            print(f"  Missing Outputs ({len(flags['missing_outputs'])}):")
            for f in flags['missing_outputs']:
                print(f"    - {f}")

        if flags.get('large_outputs'):
            print(f"  Large Outputs ({len(flags['large_outputs'])}):")
            for f in flags['large_outputs']:
                print(f"    - {f}")

        if flags.get('slow_processing'):
            print(f"  Slow Processing ({len(flags['slow_processing'])}):")
            for f in flags['slow_processing']:
                print(f"    - {f}")

    if metrics['failed_files']:
        print()
        print(f"✗ Failed Files ({len(metrics['failed_files'])}):")
        for f in metrics['failed_files']:
            print(f"    - {f}")

    print()
    print("=" * 60)
    print()


def main():
    """Main execution function."""
    args = parse_arguments()

    # Generate metrics
    print(f"Analyzing log file: {args.log_file}")
    print(f"Output directory: {args.output_dir}")

    metrics = generate_metrics(args)

    # Determine output file
    if args.output_file:
        output_file = args.output_file
    else:
        output_file = f"data/output/processing_summary_{metrics['run_id']}.json"

    # Save metrics to JSON
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    print(f"\nMetrics saved to: {output_file}")

    # Print summary
    print_summary(metrics)

    # Suggest next steps
    print("Next Steps:")
    print(f"  1. Review quality flags above")
    print(f"  2. Generate review checklist:")
    print(f"     poetry run python scripts/generate_review_checklist.py --metrics_file {output_file}")


if __name__ == "__main__":
    main()
