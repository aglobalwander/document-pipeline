#!/usr/bin/env python
"""Convert files to Markdown using MarkitDown library directly."""

import os
import sys
from pathlib import Path

def main():
    """Convert file to Markdown using MarkitDown library directly."""
    if len(sys.argv) < 2:
        print("Usage: python direct_markitdown.py <input_file> [output_file]")
        sys.exit(1)
        
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # Import MarkitDown
        from markitdown import MarkItDown
        
        # Initialize MarkItDown converter
        print(f"Converting {input_path} to Markdown...")
        md = MarkItDown(enable_plugins=False)
        
        # Convert the file
        result = md.convert(input_path)
        
        # Save result to file or print to stdout
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.text_content)
            print(f"Conversion successful! Output saved to {output_path}")
        else:
            print(result.text_content)
        
    except ImportError as e:
        print(f"Error: Required library not found - {e}")
        print("Try installing with: pip install 'markitdown[all]'")
        sys.exit(1)
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()