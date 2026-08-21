# Document Processing Pipeline overview

The pipeline turns source files into clean, portable artifacts.

It can read PDFs, Word documents, PowerPoint files, text, images, recordings,
videos, and supported URLs. A loader opens the source, a processor extracts or
cleans the content, and an optional transformer reshapes the result as text,
Markdown, JSON, CSV, or XLSX.

```text
Source file -> extraction -> optional transformation -> output artifact
```

PDFs normally use Enhanced Docling on the local machine. That keeps routine OCR
free and private. Remote language or vision models are available for explicit
cases where local extraction is not enough; they are never required for the
default PDF path.

This repository does not own search or vector-database ingestion. It produces
the artifacts that downstream systems can ingest into Milvus, Postgres, or
another store under their own contracts.

Typical uses include:

- extracting Markdown from a report or slide deck;
- recovering text and tables from a scanned PDF;
- converting a document collection into normalized JSON;
- transcribing audio or video;
- preparing a resumable collection for downstream ingestion.

Start with the [user guide](USER_GUIDE.md). For exact commands, use the
[command reference](COMMANDS.md).
