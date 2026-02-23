#!/usr/bin/env python
"""
Generate a review checklist for Claude Code interactive review workflow.

This script creates a markdown checklist that prioritizes files with quality
issues and provides instructions for using Claude Code to review and improve outputs.

Usage:
    python scripts/generate_review_checklist.py --metrics_file data/output/processing_summary_*.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate review checklist for Claude Code workflow'
    )

    parser.add_argument('--metrics_file', type=str, default=None,
                        help='Path to the processing metrics JSON file')

    parser.add_argument('--output_file', type=str, default='data/output/REVIEW_CHECKLIST.md',
                        help='Output file for the checklist (default: data/output/REVIEW_CHECKLIST.md)')

    parser.add_argument('--output_dir', type=str, default='data/output/markdown',
                        help='Directory containing markdown output files')

    return parser.parse_args()


def find_latest_metrics(output_dir: str = 'data/output') -> str:
    """Find the most recent metrics file if none is specified."""
    metrics_files = list(Path(output_dir).glob('processing_summary_*.json'))

    if not metrics_files:
        print(f"No metrics files found in {output_dir}")
        print("Please run generate_quality_metrics.py first")
        sys.exit(1)

    # Sort by modification time and return the latest
    latest = max(metrics_files, key=lambda p: p.stat().st_mtime)
    return str(latest)


def load_metrics(metrics_file: str) -> Dict[str, Any]:
    """Load metrics from JSON file."""
    with open(metrics_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def categorize_files(metrics: Dict[str, Any]) -> Dict[str, List[str]]:
    """Categorize files into priority groups based on quality flags."""

    priority_review = []
    standard_review = []
    failed_files = []

    flags = metrics.get('quality_flags', {})

    # Collect all flagged files
    flagged = set()
    for flag_type, files in flags.items():
        if isinstance(files, list):
            flagged.update(files)

    # Categorize based on file details
    for file_detail in metrics.get('file_details', []):
        filename = file_detail['filename']

        if filename in flagged:
            priority_review.append({
                'filename': filename,
                'flags': get_file_flags(filename, flags)
            })
        else:
            standard_review.append(filename)

    # Add failed files
    failed_files = metrics.get('failed_files', [])

    return {
        'priority': priority_review,
        'standard': standard_review,
        'failed': failed_files
    }


def get_file_flags(filename: str, flags: Dict[str, List[str]]) -> List[str]:
    """Get all flags associated with a specific file."""
    file_flags = []

    flag_descriptions = {
        'short_outputs': 'Short output (possible OCR failure)',
        'missing_outputs': 'Missing output file',
        'large_outputs': 'Large output (check for issues)',
        'slow_processing': 'Slow processing (complex layout)'
    }

    for flag_type, flagged_files in flags.items():
        if isinstance(flagged_files, list) and filename in flagged_files:
            file_flags.append(flag_descriptions.get(flag_type, flag_type))

    return file_flags


def generate_checklist(metrics: Dict[str, Any], output_dir: str) -> str:
    """Generate the markdown checklist content."""

    categorized = categorize_files(metrics)

    # Build the checklist markdown
    lines = []

    # Header
    lines.append("# Theory of Change PDF Review Checklist")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Run ID**: {metrics.get('run_id', 'unknown')}")
    lines.append(f"**Total Files**: {metrics.get('total_files', 0)}")
    lines.append(f"**Success Rate**: {metrics.get('success_rate_percent', 0)}%")
    lines.append(f"**Flagged for Review**: {len(categorized['priority'])}")
    lines.append("")

    # Instructions
    lines.append("## How to Use This Checklist with Claude Code")
    lines.append("")
    lines.append("This checklist helps you systematically review PDF processing outputs with Claude Code.")
    lines.append("")
    lines.append("### Review Workflow:")
    lines.append("")
    lines.append("1. **Open a markdown file**: `" + output_dir + "/[filename]_docling.md`")
    lines.append("2. **Ask Claude Code**: \"Review this document for quality issues and suggest improvements\"")
    lines.append("3. **Common review tasks**:")
    lines.append("   - Fix OCR errors and garbled text")
    lines.append("   - Improve markdown formatting (headings, lists, tables)")
    lines.append("   - Extract and structure key information")
    lines.append("   - Clean up references and citations")
    lines.append("4. **Save improvements**: Save as `[filename]_reviewed.md` in the same directory")
    lines.append("5. **Check off** the item below when complete")
    lines.append("")

    lines.append("### Example Claude Code Prompts:")
    lines.append("")
    lines.append("```")
    lines.append("Review this markdown and fix any OCR errors")
    lines.append("This table is poorly formatted - can you restructure it?")
    lines.append("Extract the key findings from this document into a bullet list")
    lines.append("This section seems garbled - can you infer the correct text?")
    lines.append("```")
    lines.append("")

    # Priority Review Section
    if categorized['priority']:
        lines.append("## Priority Review (Quality Issues Detected)")
        lines.append("")
        lines.append("These files have been flagged with quality issues and should be reviewed first:")
        lines.append("")

        for item in categorized['priority']:
            filename = item['filename']
            flags = item['flags']
            base_name = filename.replace('.pdf', '')
            markdown_file = f"{output_dir}/{base_name}_docling.md"

            flag_str = ", ".join(flags)
            lines.append(f"- [ ] **{filename}** ⚠️ {flag_str}")
            lines.append(f"      - File: `{markdown_file}`")
            lines.append("")

    # Failed Files Section
    if categorized['failed']:
        lines.append("## Failed Processing (Needs Investigation)")
        lines.append("")
        lines.append("These files failed during processing:")
        lines.append("")

        for filename in categorized['failed']:
            lines.append(f"- [ ] **{filename}** ❌ Processing failed")
            lines.append(f"      - Check log file for error details")
            lines.append(f"      - May need manual processing or different settings")
            lines.append("")

    # Standard Review Section
    if categorized['standard']:
        lines.append("## Standard Review (Optional)")
        lines.append("")
        lines.append("These files processed successfully without quality flags:")
        lines.append("")

        for filename in categorized['standard']:
            base_name = filename.replace('.pdf', '')
            markdown_file = f"{output_dir}/{base_name}_docling.md"
            lines.append(f"- [ ] {filename}")
            lines.append(f"      - File: `{markdown_file}`")

        lines.append("")

    # Statistics Section
    lines.append("---")
    lines.append("")
    lines.append("## Review Progress")
    lines.append("")
    lines.append("Track your progress as you work through the checklist:")
    lines.append("")
    lines.append(f"- Priority items: 0 of {len(categorized['priority'])} complete")
    lines.append(f"- Failed items: 0 of {len(categorized['failed'])} investigated")
    lines.append(f"- Standard items: 0 of {len(categorized['standard'])} reviewed")
    lines.append("")

    # Tips Section
    lines.append("## Tips for Efficient Review")
    lines.append("")
    lines.append("### Focus on Priority Items First")
    lines.append("Files flagged with quality issues are most likely to benefit from review.")
    lines.append("")
    lines.append("### Work in Sections")
    lines.append("Don't paste entire documents into Claude Code. Work section by section:")
    lines.append("- Paste a paragraph or section")
    lines.append("- Ask for specific improvements")
    lines.append("- Copy the improved version back")
    lines.append("- Move to the next section")
    lines.append("")
    lines.append("### Use Specific Prompts")
    lines.append("The more specific your request, the better the results:")
    lines.append("- ✓ \"Fix OCR errors in this paragraph\"")
    lines.append("- ✓ \"Convert this text table to proper markdown table format\"")
    lines.append("- ✗ \"Make this better\"")
    lines.append("")
    lines.append("### Save Incrementally")
    lines.append("Save your reviewed content frequently to avoid losing work.")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main execution function."""
    args = parse_arguments()

    # Find or load metrics file
    if args.metrics_file:
        metrics_file = args.metrics_file
    else:
        print("No metrics file specified. Looking for latest...")
        metrics_file = find_latest_metrics()

    print(f"Using metrics file: {metrics_file}")

    # Load metrics
    metrics = load_metrics(metrics_file)

    # Generate checklist
    checklist_content = generate_checklist(metrics, args.output_dir)

    # Save checklist
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    with open(args.output_file, 'w', encoding='utf-8') as f:
        f.write(checklist_content)

    print(f"\n✓ Review checklist generated: {args.output_file}")
    print()
    print("Next Steps:")
    print(f"  1. Open the checklist: {args.output_file}")
    print(f"  2. Start with priority review items")
    print(f"  3. Use Claude Code to review and improve each file")
    print(f"  4. Check off items as you complete them")
    print()


if __name__ == "__main__":
    main()
