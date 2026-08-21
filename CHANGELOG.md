# Changelog

## Unreleased - 2026-07-20

### Added

- Kimi K3 text, multimodal, and strict JSON Schema client coverage.
- Kimi routing for JSON and structured pipeline transforms.
- Top-level CLI LLM options now propagate into JSON and structured transformers.
- Current Kimi K3 CLI/API integration and capability documentation.

### Changed

- Updated Kimi defaults from Moonshot V1 to `kimi-k3` and the global
  `https://api.moonshot.ai/v1` endpoint.
- Rebuilt the live documentation entry points around the actual Poetry commands
  and current script locations.
- Clarified that local extraction and downstream ingestion are separate stages.
- Declared the test runner and chunk-tokenizer dependencies in Poetry, scoped
  test discovery to `tests/`, and updated the LangChain splitter import.

### Security

- Documented the central credential store and prohibited tracked `.env` backup
  files from being treated as configuration.

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
