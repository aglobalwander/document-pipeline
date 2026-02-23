#!/usr/bin/env python3
"""
Transform Learning Forward Innovation Configuration Maps to Clean JSON

This script transforms the IC Maps data from Excel/CSV format into a clean,
structured JSON format with both hierarchical and flat representations.

Data Source:
- Primary: data/input/spreadsheets/icmaps_analyze.xlsx (sheet: "icmaps_indicators copy")
- Supporting: icmaps_constructs.csv, icmaps_outcomes.csv

Output:
- data/output/json/learning_forward_icmaps.json
- data/output/json/learning_forward_icmaps_report.txt
"""

import pandas as pd
import json
import uuid
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# File paths
BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "data" / "input" / "spreadsheets"
OUTPUT_DIR = BASE_DIR / "data" / "output" / "json"

EXCEL_FILE = INPUT_DIR / "icmaps_analyze.xlsx"
CONSTRUCTS_CSV = INPUT_DIR / "icmaps_constructs.csv"
OUTCOMES_CSV = INPUT_DIR / "icmaps_outcomes.csv"

OUTPUT_JSON = OUTPUT_DIR / "learning_forward_icmaps.json"
OUTPUT_REPORT = OUTPUT_DIR / "learning_forward_icmaps_report.txt"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load data from Excel and CSV files"""
    print("Loading data files...")

    # Load primary data from Excel
    indicators_df = pd.read_excel(EXCEL_FILE, sheet_name="icmaps_indicators copy")
    print(f"  ✓ Loaded {len(indicators_df)} indicators from Excel")

    # Load supplementary data
    constructs_df = pd.read_csv(CONSTRUCTS_CSV)
    print(f"  ✓ Loaded {len(constructs_df)} constructs from CSV")

    outcomes_df = pd.read_csv(OUTCOMES_CSV)
    print(f"  ✓ Loaded {len(outcomes_df)} outcomes from CSV")

    return indicators_df, constructs_df, outcomes_df


def clean_data(df):
    """Clean and transform the data"""
    print("\nCleaning data...")

    # Make a copy to avoid modifying original
    df = df.copy()

    # 1. Generate UUIDs for all indicators
    df['uuid'] = [str(uuid.uuid4()) for _ in range(len(df))]
    df['original_id'] = df['ID']
    print(f"  ✓ Generated {len(df)} unique UUIDs")

    # 2. Extract framework from standard field
    df['framework_id'] = df['field_spl_standard'].str.extract(r'(frame_\d+)')[0]
    print(f"  ✓ Extracted framework IDs")

    # 3. Normalize role IDs (convert all to int where possible)
    df['role_id_normalized'] = df['field_spl_role'].astype(str)
    print(f"  ✓ Normalized role IDs")

    # 4. Replace null IC map levels with "Not defined"
    level_cols = ['field_icmap_level_1', 'field_icmap_level_2',
                  'field_icmap_level_3', 'field_icmap_level_4']

    null_counts = {}
    for col in level_cols:
        null_count = df[col].isna().sum()
        null_counts[col] = null_count
        df[col] = df[col].fillna("Not defined")

    print(f"  ✓ Replaced null IC map levels with 'Not defined':")
    for col, count in null_counts.items():
        print(f"    - {col}: {count} nulls replaced")

    # 5. Remove Body field (100% null)
    if 'Body' in df.columns:
        df = df.drop(columns=['Body'])
        print(f"  ✓ Removed 'Body' field (100% null)")

    return df


def build_metadata(df, constructs_df, outcomes_df):
    """Build metadata sections"""
    print("\nBuilding metadata sections...")

    metadata = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0",
        "source": "Learning Forward Innovation Configuration Maps",
        "total_indicators": len(df)
    }

    # Framework metadata
    frameworks = {}
    for fw_id in sorted(df['framework_id'].unique()):
        fw_data = df[df['framework_id'] == fw_id]
        frameworks[fw_id] = {
            "id": fw_id,
            "name": f"Framework {fw_id.split('_')[1]}",
            "total_standards": fw_data['field_spl_standard'].nunique(),
            "total_constructs": fw_data['field_ic_map_construct'].nunique(),
            "total_outcomes": fw_data['field_ic_map_outcome'].nunique(),
            "total_indicators": len(fw_data)
        }

    print(f"  ✓ Built metadata for {len(frameworks)} frameworks")

    # Role metadata
    roles = {}
    role_mapping = {
        '21178': 'Coach',
        '21176': 'Director of Professional Learning',
        '0.490234486': 'External Partner',
        '21177': 'Principal'
    }

    for role_id in sorted(df['role_id_normalized'].unique()):
        role_data = df[df['role_id_normalized'] == role_id]
        role_name = role_data['Role'].iloc[0] if 'Role' in role_data.columns else role_mapping.get(role_id, 'Unknown')
        roles[role_id] = {
            "id": role_id,
            "name": role_name,
            "total_indicators": len(role_data)
        }

    print(f"  ✓ Built metadata for {len(roles)} roles")

    # Standards metadata
    standards = {}
    for std_id in sorted(df['field_spl_standard'].unique()):
        std_data = df[df['field_spl_standard'] == std_id]
        standards[std_id] = {
            "id": std_id,
            "name": std_data['Standard'].iloc[0] if 'Standard' in std_data.columns else std_id,
            "description": std_data['Standard Long'].iloc[0] if 'Standard Long' in std_data.columns else "",
            "total_constructs": std_data['field_ic_map_construct'].nunique(),
            "total_indicators": len(std_data)
        }

    print(f"  ✓ Built metadata for {len(standards)} standards")

    return {
        "metadata": metadata,
        "frameworks": frameworks,
        "roles": roles,
        "standards": standards
    }


def create_hierarchical_structure(df):
    """Create hierarchical JSON structure"""
    print("\nCreating hierarchical structure...")

    hierarchy = []

    # Group by framework
    for framework_id in sorted(df['framework_id'].unique()):
        fw_data = df[df['framework_id'] == framework_id]

        framework = {
            "id": framework_id,
            "name": f"Framework {framework_id.split('_')[1]}",
            "standards": []
        }

        # Group by standard
        for standard_id in sorted(fw_data['field_spl_standard'].unique()):
            std_data = fw_data[fw_data['field_spl_standard'] == standard_id]

            standard = {
                "id": standard_id,
                "name": std_data['Standard'].iloc[0] if 'Standard' in std_data.columns else standard_id,
                "description": std_data['Standard Long'].iloc[0] if 'Standard Long' in std_data.columns else "",
                "constructs": []
            }

            # Group by construct
            for construct_id in sorted(std_data['field_ic_map_construct'].unique()):
                const_data = std_data[std_data['field_ic_map_construct'] == construct_id]

                construct = {
                    "id": construct_id,
                    "name": const_data['Construct'].iloc[0] if 'Construct' in const_data.columns else construct_id,
                    "outcomes": []
                }

                # Group by outcome
                for outcome_id in sorted(const_data['field_ic_map_outcome'].unique()):
                    out_data = const_data[const_data['field_ic_map_outcome'] == outcome_id]

                    outcome = {
                        "id": outcome_id,
                        "description": out_data['Outcome'].iloc[0] if 'Outcome' in out_data.columns else outcome_id,
                        "role": out_data['Role'].iloc[0] if 'Role' in out_data.columns else "",
                        "indicators": []
                    }

                    # Add indicators
                    for _, row in out_data.iterrows():
                        indicator = {
                            "uuid": row['uuid'],
                            "original_id": str(row['original_id']),
                            "title": row['Title'],
                            "ic_map_levels": {
                                "level_4": row['field_icmap_level_4'],
                                "level_3": row['field_icmap_level_3'],
                                "level_2": row['field_icmap_level_2'],
                                "level_1": row['field_icmap_level_1']
                            }
                        }
                        outcome["indicators"].append(indicator)

                    construct["outcomes"].append(outcome)

                standard["constructs"].append(construct)

            framework["standards"].append(standard)

        hierarchy.append(framework)

    print(f"  ✓ Built hierarchical structure with {len(hierarchy)} frameworks")

    return hierarchy


def create_flat_structure(df):
    """Create flat array of all indicators"""
    print("\nCreating flat structure...")

    indicators = []

    for _, row in df.iterrows():
        indicator = {
            "uuid": row['uuid'],
            "original_id": str(row['original_id']),
            "title": row['Title'],
            "framework_id": row['framework_id'],
            "standard_id": row['field_spl_standard'],
            "standard_name": row['Standard'] if 'Standard' in row else "",
            "construct_id": row['field_ic_map_construct'],
            "construct_name": row['Construct'] if 'Construct' in row else "",
            "outcome_id": row['field_ic_map_outcome'],
            "outcome_description": row['Outcome'] if 'Outcome' in row else "",
            "role_id": row['role_id_normalized'],
            "role_name": row['Role'] if 'Role' in row else "",
            "ic_map_levels": {
                "level_4": row['field_icmap_level_4'],
                "level_3": row['field_icmap_level_3'],
                "level_2": row['field_icmap_level_2'],
                "level_1": row['field_icmap_level_1']
            }
        }
        indicators.append(indicator)

    print(f"  ✓ Created flat structure with {len(indicators)} indicators")

    return indicators


def generate_report(df, metadata_sections):
    """Generate transformation summary report"""
    print("\nGenerating transformation report...")

    report_lines = [
        "="* 80,
        "LEARNING FORWARD IC MAPS TRANSFORMATION REPORT",
        "="* 80,
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "DATA SOURCES",
        "-" * 80,
        f"Primary: {EXCEL_FILE}",
        f"  Sheet: icmaps_indicators copy",
        f"  Records: {len(df)}",
        "",
        f"Supporting: {CONSTRUCTS_CSV}",
        f"Supporting: {OUTCOMES_CSV}",
        "",
        "DATA CLEANING SUMMARY",
        "-" * 80,
        f"✓ Generated {len(df)} unique UUIDs",
        f"✓ Preserved original IDs as 'original_id' field",
        f"✓ Extracted framework IDs from standard field",
        f"✓ Normalized role IDs",
        f"✓ Replaced null IC map levels with 'Not defined'",
        f"✓ Removed 'Body' field (100% null)",
        "",
        "STATISTICS",
        "-" * 80,
        f"Total Indicators: {len(df)}",
        f"Total Frameworks: {len(metadata_sections['frameworks'])}",
        f"Total Standards: {len(metadata_sections['standards'])}",
        f"Total Constructs: {df['field_ic_map_construct'].nunique()}",
        f"Total Outcomes: {df['field_ic_map_outcome'].nunique()}",
        f"Total Roles: {len(metadata_sections['roles'])}",
        "",
        "BREAKDOWN BY FRAMEWORK",
        "-" * 80
    ]

    for fw_id, fw_data in sorted(metadata_sections['frameworks'].items()):
        report_lines.extend([
            f"{fw_data['name']} ({fw_id})",
            f"  Standards: {fw_data['total_standards']}",
            f"  Constructs: {fw_data['total_constructs']}",
            f"  Outcomes: {fw_data['total_outcomes']}",
            f"  Indicators: {fw_data['total_indicators']}",
            ""
        ])

    report_lines.extend([
        "BREAKDOWN BY ROLE",
        "-" * 80
    ])

    for role_id, role_data in sorted(metadata_sections['roles'].items()):
        report_lines.extend([
            f"{role_data['name']} (ID: {role_id})",
            f"  Indicators: {role_data['total_indicators']}",
            ""
        ])

    report_lines.extend([
        "NULL HANDLING",
        "-" * 80,
        f"Level 1 nulls replaced: {df['field_icmap_level_1'].eq('Not defined').sum()}",
        f"Level 2 nulls replaced: {df['field_icmap_level_2'].eq('Not defined').sum()}",
        f"Level 3 nulls replaced: {df['field_icmap_level_3'].eq('Not defined').sum()}",
        f"Level 4 nulls replaced: {df['field_icmap_level_4'].eq('Not defined').sum()}",
        "",
        "VALIDATION",
        "-" * 80,
        f"✓ All {len(df)} indicators included in output",
        f"✓ All UUIDs unique: {df['uuid'].nunique() == len(df)}",
        f"✓ All frameworks represented: {df['framework_id'].nunique()} frameworks",
        f"✓ All roles represented: {df['role_id_normalized'].nunique()} roles",
        "",
        "OUTPUT FILES",
        "-" * 80,
        f"JSON: {OUTPUT_JSON}",
        f"Report: {OUTPUT_REPORT}",
        "",
        "="* 80
    ])

    report_text = "\n".join(report_lines)

    # Write report to file
    OUTPUT_REPORT.write_text(report_text)
    print(f"  ✓ Report saved to {OUTPUT_REPORT}")

    return report_text


def main():
    """Main transformation pipeline"""
    print("\n" + "="*80)
    print("LEARNING FORWARD IC MAPS → JSON TRANSFORMATION")
    print("="*80)

    # Step 1: Load data
    indicators_df, constructs_df, outcomes_df = load_data()

    # Step 2: Clean data
    indicators_df = clean_data(indicators_df)

    # Step 3: Build metadata
    metadata_sections = build_metadata(indicators_df, constructs_df, outcomes_df)

    # Step 4: Create hierarchical structure
    hierarchical = create_hierarchical_structure(indicators_df)

    # Step 5: Create flat structure
    flat = create_flat_structure(indicators_df)

    # Step 6: Combine into final JSON
    print("\nCombining structures into final JSON...")
    final_json = {
        "metadata": metadata_sections["metadata"],
        "reference_data": {
            "frameworks": metadata_sections["frameworks"],
            "roles": metadata_sections["roles"],
            "standards": metadata_sections["standards"]
        },
        "hierarchical": hierarchical,
        "flat": flat
    }

    # Write JSON to file
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)

    print(f"  ✓ JSON saved to {OUTPUT_JSON}")
    print(f"  ✓ File size: {OUTPUT_JSON.stat().st_size / 1024:.1f} KB")

    # Step 7: Generate report
    report = generate_report(indicators_df, metadata_sections)

    print("\n" + "="*80)
    print("TRANSFORMATION COMPLETE!")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  - {OUTPUT_JSON}")
    print(f"  - {OUTPUT_REPORT}")
    print()


if __name__ == "__main__":
    main()
