#!/bin/bash
# Process a single standards framework

if [ -z "$1" ]; then
    echo "Usage: ./process_single_framework.sh <framework_name>"
    echo ""
    echo "Available frameworks:"
    ls -1 data/input/pdfs/standards/ | grep -v README.md
    exit 1
fi

FRAMEWORK=$1
echo "Processing $FRAMEWORK framework..."

# Process with fallback chain
python scripts/process_standards_frameworks.py \
    --input-dir data/input/pdfs/standards \
    --output-dir data/output/text/standards \
    --pipeline-type text \
    --frameworks "$FRAMEWORK"

echo ""
echo "Processing complete!"
echo "Output saved to: data/output/text/standards/$FRAMEWORK/"