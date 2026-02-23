"""
Spreadsheet Parser Utility

Extracts structured data from messy Excel spreadsheets by reading both
content AND formatting (bold, merged cells) to identify structure.

Usage:
    from doc_processing.utils.spreadsheet_parser import parse_structured_spreadsheet

    data = parse_structured_spreadsheet(
        'path/to/file.xlsx',
        sheet_name='Sheet1'
    )

    # Returns structured dict with sections detected via formatting
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


def get_cell_info(ws: Worksheet, row: int, col: int) -> Dict[str, Any]:
    """Extract cell value and formatting info."""
    cell = ws.cell(row=row, column=col)

    return {
        "value": cell.value,
        "is_bold": cell.font.bold if cell.font else False,
        "is_italic": cell.font.italic if cell.font else False,
        "row": row,
        "col": col,
    }


def detect_sections(ws: Worksheet, max_rows: int = 200) -> List[Dict[str, Any]]:
    """
    Detect section headers based on formatting patterns.

    Section headers are typically:
    - Bold text
    - Followed by data rows with similar column structure
    - May have repeated header patterns (Purpose, Frequency, etc.)
    """
    sections = []
    current_section = None

    for row_num in range(1, min(max_rows, ws.max_row + 1)):
        row_cells = []
        is_header_row = False

        for col_num in range(1, min(10, ws.max_column + 1)):
            cell_info = get_cell_info(ws, row_num, col_num)
            if cell_info["value"] is not None:
                row_cells.append(cell_info)
                if cell_info["is_bold"]:
                    is_header_row = True

        if not row_cells:
            continue

        # Check if this is a section header (bold row)
        if is_header_row:
            # Save previous section
            if current_section and current_section["rows"]:
                sections.append(current_section)

            # Start new section
            current_section = {
                "header_row": row_num,
                "header_values": [c["value"] for c in row_cells if c["is_bold"]],
                "rows": []
            }
        elif current_section:
            # Add data row to current section
            current_section["rows"].append({
                "row_num": row_num,
                "values": [c["value"] for c in row_cells]
            })

    # Don't forget the last section
    if current_section and current_section["rows"]:
        sections.append(current_section)

    return sections


def parse_structured_spreadsheet(
    file_path: str,
    sheet_name: str,
    max_rows: int = 200
) -> Dict[str, Any]:
    """
    Parse an Excel spreadsheet, using formatting to detect structure.

    Args:
        file_path: Path to Excel file
        sheet_name: Name of sheet to parse
        max_rows: Maximum rows to process

    Returns:
        Dict with metadata and detected sections
    """
    wb = load_workbook(file_path)

    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' not found. Available: {wb.sheetnames}")

    ws = wb[sheet_name]

    # Get merged cell info
    merged_ranges = [str(m) for m in ws.merged_cells.ranges]

    # Detect sections via formatting
    sections = detect_sections(ws, max_rows)

    return {
        "metadata": {
            "source_file": str(Path(file_path).name),
            "sheet_name": sheet_name,
            "total_rows": ws.max_row,
            "total_cols": ws.max_column,
            "merged_ranges": merged_ranges[:20],  # First 20
        },
        "sections": sections
    }


def spreadsheet_to_json(
    file_path: str,
    sheet_name: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse spreadsheet and optionally save to JSON.

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet name
        output_path: Optional path to save JSON output

    Returns:
        Parsed data dict
    """
    data = parse_structured_spreadsheet(file_path, sheet_name)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    return data


# Quick summary for Claude Code to interpret
def summarize_spreadsheet(file_path: str, sheet_name: str) -> str:
    """
    Generate a text summary of spreadsheet structure for LLM interpretation.

    This is designed to be fed to Claude Code for semantic understanding.
    """
    data = parse_structured_spreadsheet(file_path, sheet_name)

    lines = [
        "=== Spreadsheet Structure Summary ===",
        f"File: {data['metadata']['source_file']}",
        f"Sheet: {data['metadata']['sheet_name']}",
        f"Size: {data['metadata']['total_rows']} rows x {data['metadata']['total_cols']} cols",
        f"Merged cells: {len(data['metadata']['merged_ranges'])}",
        "",
        f"=== Detected Sections ({len(data['sections'])}) ===",
    ]

    for i, section in enumerate(data['sections'], 1):
        header = ', '.join(str(h) for h in section['header_values'][:3])
        row_count = len(section['rows'])
        lines.append(f"\n{i}. [{header}] (Row {section['header_row']}, {row_count} data rows)")

        # Show first 3 data rows as sample
        for row in section['rows'][:3]:
            vals = ' | '.join(str(v)[:30] for v in row['values'][:4] if v)
            lines.append(f"   - {vals}")

        if len(section['rows']) > 3:
            lines.append(f"   ... and {len(section['rows']) - 3} more rows")

    return '\n'.join(lines)
