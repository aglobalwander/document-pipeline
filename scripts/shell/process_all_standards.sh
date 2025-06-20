#!/bin/bash
# Process all standards frameworks with optimal settings

echo "Processing Standards Frameworks"
echo "=============================="

# Set up environment
cd "$(dirname "$0")"

# Process to text format first (fastest)
echo "Step 1: Extracting text from all PDFs..."
python scripts/process_standards_frameworks.py \
    --input-dir data/input/pdfs/standards \
    --output-dir data/output/text/standards \
    --pipeline-type text

# Optional: Also create markdown versions for better formatting
echo ""
echo "Step 2: Creating markdown versions (optional)..."
read -p "Do you want to also create markdown versions? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    python scripts/process_standards_frameworks.py \
        --input-dir data/input/pdfs/standards \
        --output-dir data/output/markdown/standards \
        --pipeline-type markdown
fi

# Optional: Create structured JSON
echo ""
echo "Step 3: Creating structured JSON (optional)..."
read -p "Do you want to create JSON versions? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    python scripts/process_standards_frameworks.py \
        --input-dir data/input/pdfs/standards \
        --output-dir data/output/json/standards \
        --pipeline-type json
fi

echo ""
echo "Processing complete!"
echo "Check output at:"
echo "  - Text: data/output/text/standards/"
echo "  - Markdown: data/output/markdown/standards/"
echo "  - JSON: data/output/json/standards/"