# Changelog

## 1.0.0 - 2025-04-27

### Added

- Initial stable release of the Document Processing Pipeline.
- Support for processing PDF, DOCX, PPTX, TXT, MD, JSON, Audio, Image, and Video files.
- Ability to process directly from YouTube URLs.
- Modular architecture with extensible loaders, processors, and transformers.
- Integration with OpenAI and Gemini LLMs for advanced processing (OCR, native PDF).
- Support for various output formats: Text, Markdown, JSON, CSV, Excel.
- Weaviate v4 integration for data ingestion and querying.
- Command-line interface via `scripts/run_pipeline.py`.
- Basic documentation (README.md, USER_GUIDE.md, OVERVIEW.md).
- Modular test suite.
- Configuration management using `pyproject.toml` and environment variables.
- JSON to CSV and JSON to Excel transformers with template support.
- Hybrid OCR mode for intelligent PDF and image processing.
- Troubleshooting section in USER_GUIDE.md.

### Changed

- Reorganized script files from the root directory into the `scripts/` directory.
- Updated README.md to reflect the new directory structure.
- Improved clarity in USER_GUIDE.md regarding Weaviate configuration and removed placeholder text.

### Removed

- Removed HybridPPTXProcessor as MarkItDownPPTXProcessor is used.

### Fixed

- Addressed encoding error handling for DOCX files (as seen in initial user interaction).