#!/usr/bin/env python
"""Convert DOCX to Markdown using MarkitDown library directly."""

import os
import sys
from pathlib import Path

def main():
    """Convert DOCX to Markdown using MarkitDown library directly."""
    try:
        # Import MarkitDown
        from markitdown import MarkItDown
        
        # Input and output paths
        input_path = "data/input/docx/day_1_.docx"
        output_path = "data/output/markdown/day_1_markitdown_direct.md"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Initialize MarkItDown converter
        print(f"Converting {input_path} to Markdown...")
        md = MarkItDown(enable_plugins=False)
        
        # Convert the file
        result = md.convert(input_path)
        
        # Save result to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result.text_content)
        
        print(f"Conversion successful! Output saved to {output_path}")
        
    except ImportError as e:
        print(f"Error: Required library not found - {e}")
        print("Try installing with: pip install 'markitdown[docx]'")
        sys.exit(1)
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()