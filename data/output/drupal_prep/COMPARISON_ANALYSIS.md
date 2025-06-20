# Comparison Analysis: New Extractions vs Original standards.csv

## Key Improvements in New Extractions

### 1. **Hierarchical Organization**
**Original CSV:**
- Standards listed flat with limited hierarchy information
- `field_standards_hierarchy` and `field_standards_taxonomy` present but values often empty
- No clear organizational levels

**New Extractions:**
- Full 4-level hierarchy properly mapped
- Each standard has explicit hierarchy term IDs
- Clear organizational levels (`field_org_level_1`, `field_org_level_2`, `field_org_level_3`)
- Separate hierarchy_additions.csv files to create proper taxonomy structure

### 2. **Entity References and Relationships**
**Original CSV:**
- No EU/EQ references for NCAS or other frameworks
- Many reference fields (Marzano tiers, SEP, CCC, DCI) but unclear relationships

**New Extractions (NCAS example):**
- Explicit `field_eu_references` and `field_eq_references` 
- Separate CSV files for EUs and EQs as distinct entities
- Clear relationships between standards and their associated concepts
- 76 EUs and 130 EQs extracted with proper linking

### 3. **Standard Identifiers**
**Original CSV:**
- Mixed UUID formats
- Title field contains full standard code (e.g., "CCSS.ELA-Literacy.CCRA.R.1")

**New Extractions:**
- Consistent UUID generation based on framework and code
- Clean separation of title (standard code) and body (standard text)
- Predictable format: `framework-code` (e.g., `ncas-dance-da-cr1.1.iii`)

### 4. **Content Fidelity**
**Original CSV:**
- Some standards have incomplete text (e.g., ending with `<br>` tags)
- Mixed HTML formatting

**New Extractions:**
- Complete standard text extracted from source documents
- Consistent HTML formatting (`<p>` tags)
- Preserved full standard descriptions

### 5. **Framework-Specific Improvements**

#### NCAS
- **Original**: Not present in your CSV
- **New**: 507 standards with proper artistic process organization
- Includes Dance, Music, Theatre, Visual Arts, Media Arts
- EUs and EQs properly extracted and linked

#### Math Common Core  
- **Original**: Not present in your CSV
- **New**: 480 standards organized by Grade → Domain → Cluster
- Includes all K-8 standards with proper mathematical domain grouping

#### C3 Framework
- **Original**: Limited presence (only field references visible)
- **New**: 324 indicators across 4 dimensions
- Proper discipline separation (Civics, Economics, Geography, History, Psychology, Sociology)
- Grade-band organization (K-2, 3-5, 6-8, 9-12)

### 6. **Data Quality Issues Found**

**In New Extractions:**
- Some Math standards captured practice descriptions instead of actual standards (e.g., K.NBT.2-8 showing "Mathematical Practices")
- Very long standard texts in some cases (3.NBT.3 includes entire framework introduction)
- These can be cleaned up with targeted fixes

**Missing from New Extractions:**
- Many specialized fields from original (Marzano tiers, assessment references, unit associations)
- NGSS-specific fields (SEP, CCC, DCI)
- These could be added if source documents contain this information

## Recommendations

1. **Use new extractions for NCAS, Math CC, and C3** - They provide much better structure and completeness

2. **Merge approaches for existing frameworks**:
   - Keep your existing ELA Common Core, NGSS, etc. 
   - Consider re-extracting if you find source documents with EU/EQ information

3. **Enhance existing data** by adding:
   - Proper hierarchy term IDs
   - Organization levels
   - EU/EQ extractions where applicable

4. **Clean up extraction issues**:
   - Fix Math standards that captured wrong content
   - Truncate overly long descriptions
   - Add validation to ensure standard text vs metadata separation

The new extractions provide significantly better fidelity to the framework structures and include important relationships (EUs/EQs) that were missing from the original CSV.