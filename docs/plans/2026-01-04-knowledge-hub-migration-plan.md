# Knowledge Hub Migration Plan

## Overview

Migrate ~5,100 curated educational documents from OneDrive research collection into the Knowledge Hub (Milvus). Directory-by-directory approach with user-driven prioritization.

**Source**: `/Users/scottwilliams/Library/CloudStorage/OneDrive-ShanghaiAmericanSchool/2_Models-Frameworks-Research`

**Already processed**: `__knowledge_base/` (literature, mem exports, consolidated)

**Goal**: Searchable reference + active working tool for PD, curriculum design, coaching

---

## Directory Inventory

| Priority | Directory | Files | Content Type |
|----------|-----------|------:|--------------|
| TBD | `language_arts` | 1,396 | Reading, writing, literacy resources |
| TBD | `_@Professional Organizations` | 1,221 | ASCD, Project Zero, LDC, Marzano, etc. |
| TBD | `Coaching Research and Resources` | 553 | Articles, models, podcasts, handbooks |
| TBD | `Instructional Resources` | 191 | TPT, Kagan, strategies, graphic organizers |
| TBD | `_Standards Frameworks` | 174 | ISTE, IB, NGSS, Common Core, WIDA |
| TBD | `MicroCredentials` | 172 | Credential programs |
| TBD | `Collaboration-Facilitation` | 147 | Liberating structures, protocols, dialogue |
| TBD | `SEL` | 113 | Social-emotional strategies |
| TBD | `Innovation` | 108 | IDEO, design thinking, systems innovation |
| TBD | `Visual Literacy` | 93 | Visual learning resources |
| TBD | `Marzano` | 90 | Scales, elements, research, playbooks |
| TBD | `@ Curriculum Blueprint` | 87 | Learning progressions, SBG, taxonomies |
| TBD | `Assessment` | 82 | Formative, performance tasks, rubrics |
| TBD | `@Unit and Lesson Plan Templates` | 75 | UBD, ACT, lesson models |
| TBD | `_Personalized Competency Based System` | 69 | CBE, personalization |
| TBD | `_Strategic Planning` | 41 | Theory of change, vision, change mgmt |
| TBD | `Differentiation` | 41 | Barbara Bray, IRIS PD |
| TBD | `Instructional Models` | 24 | Danielson, Marzano frameworks |
| TBD | `UBD` | 21 | Understanding by Design |
| TBD | `Understandings` | 19 | |
| TBD | `culturesofthinking` | 19 | Ron Ritchhart, thinking routines |
| TBD | `Questioning` | 15 | QFT, questioning strategies |
| TBD | `Leadership` | 14 | Capacity building, CEL |
| TBD | `Thinking Maps` | 13 | Visual thinking tools |
| TBD | `UDL` | 10 | Universal Design for Learning |
| TBD | `High Reliability Schools` | 10 | HRS framework |
| TBD | *20+ smaller directories* | ~50 | Various topics |

**Total: ~5,100 documents**

---

## Processing Strategy

### Per-Directory Workflow

For each directory the user prioritizes:

1. **Inventory** - List files, identify formats (PDF, DOCX, PPTX)
2. **Categorize** - Determine if Drupal-bound or Knowledge Hub only
3. **Process** - Run through document pipeline (enhanced_docling for PDFs)
4. **Tag** - Extract/assign topic metadata, source organization
5. **Chunk** - Split into searchable segments for Milvus
6. **Ingest** - Load into Knowledge Hub collection

### Output Destinations

| Content Type | Knowledge Hub | Drupal CSV |
|--------------|:-------------:|:----------:|
| Instructional techniques | Yes | `instructional_technique` |
| SEL strategies | Yes | `sel_strategy` |
| Protocols | Yes | `protocol` |
| Lesson models | Yes | `lesson_model` |
| Frameworks/research | Yes | No |
| Standards docs | Yes | No |
| Templates | Yes | No |

### Metadata Schema (JSONL)

```json
{
  "id": "edu:<category>:<source>:<filename>:chunk_<n>",
  "text": "extracted content...",
  "ns": "edu:<category>",
  "source_id": "filename.pdf",
  "source_path": "relative/path/to/file",
  "source_org": "Project Zero",
  "topics": ["thinking_routines", "visible_thinking"],
  "title": "Document Title",
  "chunk_index": 0,
  "doc_type": "educational_resource",
  "observed_at": "2026-01-04"
}
```

---

## Infrastructure (Existing)

### Document Pipeline
- `doc_processing/document_pipeline.py` - Core orchestration
- `doc_processing/processors/enhanced_docling_processor.py` - FREE PDF processing
- `scripts/document_processing/run_pipeline.py` - CLI entry point

### Knowledge Hub (Milvus)
- Collection: `knowledge_main` (or new `educational_resources`)
- Embedding: text-embedding-3-small
- Search: hybrid (BM25 + vector)

### Scripts to Create
1. `scripts/document_processing/batch_process_educational.py` - Directory batch processor
2. `scripts/document_processing/generate_knowledge_hub_jsonl.py` - JSONL generator
3. `doc_processing/models/educational_schemas.py` - Pydantic metadata schemas

---

## Existing Content (Avoid Duplicates)

### Already in Knowledge Hub
- 56,029 literature chunks
- Professional frameworks (Thrive Coaching, Learning Forward)
- 900 mem notes

### Already in Drupal
- 4,378 instructional techniques
- 220+ core practices
- 500+ SEL strategies

### Deduplication Approach
- Title fuzzy matching (rapidfuzz, 85% threshold)
- Content hash comparison
- Generate review report before import

---

## Execution Pattern

When user selects a directory:

```bash
# 1. Inventory
python scripts/document_processing/inventory_directory.py \
  --source "path/to/directory" \
  --output data/inventory/<dirname>.csv

# 2. Process (FREE with enhanced_docling)
python scripts/document_processing/batch_process_educational.py \
  --source "path/to/directory" \
  --category <category_name> \
  --output-dir data/output/educational

# 3. Generate JSONL for Knowledge Hub
python scripts/document_processing/generate_knowledge_hub_jsonl.py \
  --input data/output/educational/<category>/ \
  --output data/output/knowledge_hub/<category>.jsonl

# 4. Ingest to Milvus
# (via knowledge-management project tools)
```

---

## Estimated Effort

| Directory Size | Processing Time | Review Time |
|----------------|-----------------|-------------|
| Small (<50 files) | ~30 min | ~15 min |
| Medium (50-200) | ~2 hrs | ~30 min |
| Large (200-500) | ~4 hrs | ~1 hr |
| Very Large (500+) | ~8 hrs | ~2 hrs |

**Total estimate**: 40-60 hours processing + review (can run in background)

---

## Next Steps

1. User selects first directory to process
2. Create processing scripts (one-time)
3. Run batch process on selected directory
4. Review output, adjust as needed
5. Ingest to Knowledge Hub
6. Repeat for next directory

---

## Related Plans

- [Educational Materials Processing Plan](../../.claude/plans/iridescent-zooming-cake.md) - Original 319-doc plan for TPT, QFT, SEL, CFU subset
