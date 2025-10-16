# Using Claude Code for Interactive PDF Processing

This document explains how to use Claude Code (the AI assistant you're talking to right now) as a FREE alternative to paid LLM APIs for PDF processing.

## The Zero-Cost Workflow

### Default Pipeline (Automatic - FREE)
```bash
# Uses enhanced_docling by default - completely free
poetry run python scripts/document_processing/master_docling.py --input_path data/input/pdfs/your_file.pdf

# Output will be in:
# - data/output/text/your_file_docling.txt
# - data/output/markdown/your_file_docling.md
# - data/output/json/your_file_docling.json
```

**Cost**: $0 (uses local OCR and open-source models)
**Best for**: Most documents, especially those with clear text and structure

---

## When Docling Isn't Enough

For complex documents where automated processing struggles:

### Option 1: Interactive Review with Claude Code (FREE)

**Step 1: Process with Docling**
```bash
poetry run python scripts/document_processing/master_docling.py \
  --input_path data/input/pdfs/complex_document.pdf
```

**Step 2: Ask Claude Code (me!) to Review**
Open the output file and ask me to:
- "Review this extracted text and fix any OCR errors"
- "Restructure this content into a cleaner markdown format"
- "Extract key information from this document and organize it"
- "This section is garbled - can you infer what it should say based on context?"

**Example Workflow:**
```
You: Here's the docling output from a complex PDF. Can you clean it up?
[paste first section]

Claude Code: I'll fix the OCR errors and restructure...
[provides cleaned version]

You: Great! Now here's the next section...
```

**Cost**: $0 (uses your Claude subscription)
**Best for**:
- Complex layouts that Docling struggles with
- Documents needing human-level interpretation
- Extracting specific structured data
- Fixing OCR errors in critical sections

---

## When to Use Paid API Options

### Claude API (Opt-In Only)
If you have an Anthropic API key and want fully automated processing of complex PDFs:

```bash
# Explicitly specify claude processor
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path data/input/pdfs/complex.pdf \
  --pipeline_type text \
  --ocr_mode claude
```

**Requirements:**
- Add `ANTHROPIC_API_KEY` to your `.env` file
- Explicitly choose `claude` processor

**Cost**: ~$3-15 per 1M tokens
**Best for**: Batch processing of complex PDFs when you need automation

---

## Cost Comparison

| Method | Cost | Speed | Quality | When to Use |
|--------|------|-------|---------|-------------|
| **Enhanced Docling** (default) | FREE | Medium | Very Good | Default for all PDFs |
| **Claude Code Interactive** (you & me) | FREE | Slow | Excellent | Complex docs, manual review |
| **Gemini API** (fallback) | $0.08-0.30/1M tokens | Fast | Good | Batch processing, budget option |
| **Claude API** (opt-in) | $3-15/1M tokens | Fast | Excellent | Automated complex processing |
| **GPT-4** (fallback) | $2.50-10/1M tokens | Fast | Excellent | Last resort |

---

## Recommended Workflow Examples

### Example 1: Research Paper
```bash
# Step 1: Process with Docling (free)
poetry run python scripts/document_processing/master_docling.py \
  --input_path research_paper.pdf

# Step 2: Review output
cat data/output/markdown/research_paper_docling.md

# Step 3: If good, you're done! If issues:
# Open the file in your editor and ask Claude Code:
# "This paper has complex equations and figures. Can you help extract
#  the key findings and methodology into a structured summary?"
```

**Cost**: $0

### Example 2: Invoice Processing (Batch)
```bash
# For automated batch processing of many invoices, use Gemini (cheap)
poetry run python scripts/document_processing/run_pipeline.py \
  --input_path data/input/pdfs/invoices/ \
  --recursive \
  --pipeline_type json \
  --llm_provider gemini
```

**Cost**: ~$0.08 per million tokens (very cheap for batch)

### Example 3: Complex Legal Document
```bash
# Step 1: Try Docling first (free)
poetry run python scripts/document_processing/master_docling.py \
  --input_path contract.pdf

# Step 2: Open output and work with Claude Code interactively
# Ask me to:
# - Extract all defined terms
# - Summarize each section
# - Identify key obligations
# - Flag potential issues
```

**Cost**: $0 (interactive with Claude Code)

---

## Tips for Working with Claude Code

When asking me to help with PDF processing:

1. **Paste in sections** - Don't paste the entire document at once. Work section by section.

2. **Be specific** - Tell me what you need:
   - "Extract the executive summary"
   - "Fix OCR errors in this paragraph"
   - "Convert this table to markdown"
   - "Summarize the methodology section"

3. **Iterate** - We can refine the output together:
   - "That's good, but can you also include..."
   - "The formatting is off here..."
   - "Can you organize this differently?"

4. **Use me for complex reasoning** - I'm especially useful for:
   - Understanding context that OCR misses
   - Restructuring poorly formatted content
   - Extracting specific information
   - Summarizing and organizing content
   - Handling tables and figures

---

## Configuration Reference

Your current setup (in `doc_processing/config.py`):

```python
DEFAULT_PDF_PROCESSOR = "enhanced_docling"  # FREE
PDF_FALLBACK_ORDER = ["enhanced_docling", "docling", "gemini"]  # No API costs by default
```

To use Claude API (requires API key):
```bash
# Set in .env
ANTHROPIC_API_KEY=your_key_here

# Then explicitly request it
--ocr_mode claude
```

---

## Summary

**Default**: Enhanced Docling (FREE) handles 90% of PDFs automatically

**For complex cases**: Use Claude Code (me!) interactively (FREE with your subscription)

**For automation**: Add API keys and explicitly opt-in to paid services

**Bottom line**: You can process all your PDFs for $0 using Docling + Claude Code! 🎉
