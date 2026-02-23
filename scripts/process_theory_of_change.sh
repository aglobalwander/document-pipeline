#!/bin/bash
# Batch process all PDFs in the theory_of_change directory
# Uses enhanced_docling processor for zero-cost processing

set -e  # Exit on error

# Configuration
INPUT_DIR="data/input/pdfs/theory_of_change"
OUTPUT_DIR="data/output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${OUTPUT_DIR}/processing_log_${TIMESTAMP}.txt"

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Initialize counters
TOTAL=0
SUCCESS=0
FAILED=0

echo "========================================" | tee "$LOG_FILE"
echo "Theory of Change PDF Batch Processing" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "Input directory: $INPUT_DIR" | tee -a "$LOG_FILE"
echo "Output directory: $OUTPUT_DIR" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Count total PDF files
TOTAL=$(find "$INPUT_DIR" -name "*.pdf" -type f | wc -l | tr -d ' ')
echo "Found $TOTAL PDF files to process" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Process each PDF file
CURRENT=0
for pdf in "$INPUT_DIR"/*.pdf; do
    if [ ! -f "$pdf" ]; then
        echo "No PDF files found in $INPUT_DIR" | tee -a "$LOG_FILE"
        exit 1
    fi

    CURRENT=$((CURRENT + 1))
    filename=$(basename "$pdf")

    echo "----------------------------------------" | tee -a "$LOG_FILE"
    echo "[$CURRENT/$TOTAL] Processing: $filename" | tee -a "$LOG_FILE"
    echo "Started: $(date)" | tee -a "$LOG_FILE"

    START_TIME=$(date +%s)

    # Run the processing
    if poetry run python scripts/document_processing/master_docling.py \
        --input_path "$pdf" >> "$LOG_FILE" 2>&1; then

        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        echo -e "${GREEN}✓ SUCCESS${NC}: $filename (${DURATION}s)" | tee -a "$LOG_FILE"
        SUCCESS=$((SUCCESS + 1))
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        echo -e "${RED}✗ FAILED${NC}: $filename (${DURATION}s)" | tee -a "$LOG_FILE"
        FAILED=$((FAILED + 1))
    fi

    echo "Completed: $(date)" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
done

# Print summary
echo "========================================" | tee -a "$LOG_FILE"
echo "Batch Processing Complete" | tee -a "$LOG_FILE"
echo "Finished: $(date)" | tee -a "$LOG_FILE"
echo "----------------------------------------" | tee -a "$LOG_FILE"
echo "Total files: $TOTAL" | tee -a "$LOG_FILE"
echo -e "${GREEN}Successful: $SUCCESS${NC}" | tee -a "$LOG_FILE"
echo -e "${RED}Failed: $FAILED${NC}" | tee -a "$LOG_FILE"
echo "Success rate: $(awk "BEGIN {printf \"%.1f\", ($SUCCESS/$TOTAL)*100}")%" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Output files located in:" | tee -a "$LOG_FILE"
echo "  - Text: ${OUTPUT_DIR}/text/" | tee -a "$LOG_FILE"
echo "  - Markdown: ${OUTPUT_DIR}/markdown/" | tee -a "$LOG_FILE"
echo "  - JSON: ${OUTPUT_DIR}/json/" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Next steps:" | tee -a "$LOG_FILE"
echo "  1. Generate quality metrics:" | tee -a "$LOG_FILE"
echo "     poetry run python scripts/generate_quality_metrics.py --log_file $LOG_FILE" | tee -a "$LOG_FILE"
echo "  2. Generate review checklist:" | tee -a "$LOG_FILE"
echo "     poetry run python scripts/generate_review_checklist.py" | tee -a "$LOG_FILE"
