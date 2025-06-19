# Pipeline Documents Documentation

Welcome to the Pipeline Documents documentation! This guide will help you navigate the available documentation and find what you need quickly.

## 📚 Documentation Structure

### Core Documentation

- **[OVERVIEW.md](OVERVIEW.md)** - System architecture, design principles, and component overview
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete guide for using the pipeline, including installation and configuration
- **[COMMANDS.md](COMMANDS.md)** - Quick reference for all available commands and options

### Specialized Guides

Located in the [`guides/`](guides/) directory:

- **[OCR_GUIDE.md](guides/OCR_GUIDE.md)** - Comprehensive guide for OCR and PDF processing strategies
- **[PYMUPDF_USAGE.md](guides/PYMUPDF_USAGE.md)** - Detailed usage guide for the PyMuPDF processor
- **[WEAVIATE_GUIDE.md](guides/WEAVIATE_GUIDE.md)** - Complete guide for Weaviate vector database integration

## 🚀 Quick Start

### For New Users

1. Start with **[USER_GUIDE.md](USER_GUIDE.md)** to understand the system and get it running
2. Reference **[COMMANDS.md](COMMANDS.md)** for quick command examples
3. Explore specialized guides based on your needs

### For Developers

1. Read **[OVERVIEW.md](OVERVIEW.md)** to understand the architecture
2. Check the project [README.md](../README.md) for development setup
3. Refer to specialized guides for component-specific details

## 📖 Documentation by Use Case

### "I want to process PDFs"
- Start with [USER_GUIDE.md](USER_GUIDE.md#pdf-processing-strategies)
- For optimization: [OCR_GUIDE.md](guides/OCR_GUIDE.md)
- For fast text extraction: [PYMUPDF_USAGE.md](guides/PYMUPDF_USAGE.md)

### "I want to use vector search"
- See [WEAVIATE_GUIDE.md](guides/WEAVIATE_GUIDE.md)
- Quick commands in [COMMANDS.md](COMMANDS.md#targeted-collections)

### "I want to process other document types"
- [USER_GUIDE.md](USER_GUIDE.md) covers DOCX, PPTX, images, audio, video
- [COMMANDS.md](COMMANDS.md#format-transforms) for quick examples

### "I want to optimize costs"
- [OCR_GUIDE.md](guides/OCR_GUIDE.md#cost-analysis) for processing cost comparison
- [USER_GUIDE.md](USER_GUIDE.md#processing-strategies) for fallback chain configuration

## 🔧 Common Tasks

| Task | Documentation |
|------|---------------|
| Install and setup | [USER_GUIDE.md](USER_GUIDE.md#overview) |
| Process a single PDF | [COMMANDS.md](COMMANDS.md#quick-ingest-commands) |
| Batch process documents | [USER_GUIDE.md](USER_GUIDE.md#examples) |
| Configure OCR fallback | [OCR_GUIDE.md](guides/OCR_GUIDE.md#processing-strategies) |
| Setup Weaviate | [WEAVIATE_GUIDE.md](guides/WEAVIATE_GUIDE.md#quick-start) |
| Add custom processors | [OVERVIEW.md](OVERVIEW.md) → Extending section |

## 📂 Archive

Historical and development-specific documentation is stored in [`archive/`](archive/) for reference:
- Implementation plans
- Migration guides
- Progress summaries

## 🤝 Contributing

When adding new documentation:
1. Place user-facing guides in the main `docs/` directory
2. Put specialized guides in `docs/guides/`
3. Move outdated docs to `docs/archive/`
4. Update this README with links to new documents

## 📞 Getting Help

1. Check the relevant documentation first
2. Search existing [GitHub issues](https://github.com/yourusername/pipeline-documents/issues)
3. Review code examples in the `scripts/` directory
4. Open a new issue with the `documentation` label for doc-specific questions

---

*Last updated: January 2025*