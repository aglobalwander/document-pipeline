#!/usr/bin/env python3
"""Build the final SAS course catalog JSON from master lists + descriptions.

Merges:
  - PDHS_MASTER / PXHS_MASTER (from extract_course_catalogs.py)
  - PDHS_DESCRIPTIONS (from data/pdhs_descriptions.py)
  - PXHS_DESCRIPTIONS (from data/pxhs_descriptions.py)

Output:
  data/output/json/sas_course_catalogs_2026-27.json
"""

import json
import sys
from pathlib import Path

# Add scripts/ and scripts/data/ to path so imports work
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR / "data"))

from extract_course_catalogs import PDHS_MASTER, PXHS_MASTER
from pdhs_descriptions import PDHS_DESCRIPTIONS
from pxhs_descriptions import PXHS_DESCRIPTIONS

OUTPUT_PATH = SCRIPTS_DIR.parent / "data" / "output" / "json" / "sas_course_catalogs_2026-27.json"


def build_course_record(name, codes, credits, grades, department, campus, descriptions):
    """Build a single course JSON record."""
    record = {
        "course_name": name,
        "course_codes": codes,
        "credits": credits,
        "grades": grades,
        "department": department,
        "campus": campus,
    }

    desc = descriptions.get(name)
    if desc:
        record["prerequisites"] = desc.get("prerequisites", "")
        record["course_description"] = desc.get("course_description", "")
        # Standard format fields
        if "main_topics" in desc:
            record["main_topics"] = desc["main_topics"]
        if "learning_outcomes" in desc:
            record["learning_outcomes"] = desc["learning_outcomes"]
        # Chinese Language format fields
        if "oral_language" in desc:
            record["oral_language"] = desc["oral_language"]
        if "reading" in desc:
            record["reading"] = desc["reading"]
        if "writing" in desc:
            record["writing"] = desc["writing"]
    else:
        record["prerequisites"] = ""
        record["course_description"] = ""

    return record


def main():
    courses = []
    pdhs_matched = set()
    pxhs_matched = set()
    pdhs_unmatched = []
    pxhs_unmatched = []

    # Build PDHS courses (try PDHS descriptions first, fall back to PXHS)
    for name, codes, credits, grades, department in PDHS_MASTER:
        if name in PDHS_DESCRIPTIONS:
            desc_source = PDHS_DESCRIPTIONS
            pdhs_matched.add(name)
        elif name in PXHS_DESCRIPTIONS:
            desc_source = PXHS_DESCRIPTIONS
            pdhs_matched.add(name)
        else:
            desc_source = {}
            pdhs_unmatched.append(name)

        record = build_course_record(name, codes, credits, grades, department, "PDHS", desc_source)
        courses.append(record)

    # Build PXHS courses
    for name, codes, credits, grades, department in PXHS_MASTER:
        # Try PXHS descriptions first, fall back to PDHS for shared courses
        if name in PXHS_DESCRIPTIONS:
            desc_source = PXHS_DESCRIPTIONS
            pxhs_matched.add(name)
        elif name in PDHS_DESCRIPTIONS:
            desc_source = PDHS_DESCRIPTIONS
            pxhs_matched.add(name)
        else:
            desc_source = {}
            pxhs_unmatched.append(name)

        record = build_course_record(name, codes, credits, grades, department, "PXHS", desc_source)
        courses.append(record)

    # Summary
    pdhs_total = len(PDHS_MASTER)
    pxhs_total = len(PXHS_MASTER)
    pdhs_with_desc = pdhs_total - len(pdhs_unmatched)
    pxhs_with_desc = pxhs_total - len(pxhs_unmatched)

    print(f"PDHS: {pdhs_with_desc}/{pdhs_total} courses with descriptions ({100*pdhs_with_desc/pdhs_total:.0f}%)")
    print(f"PXHS: {pxhs_with_desc}/{pxhs_total} courses with descriptions ({100*pxhs_with_desc/pxhs_total:.0f}%)")
    print(f"Total courses: {len(courses)}")

    if pdhs_unmatched:
        print(f"\nPDHS courses without descriptions ({len(pdhs_unmatched)}):")
        for name in pdhs_unmatched:
            print(f"  - {name}")

    if pxhs_unmatched:
        print(f"\nPXHS courses without descriptions ({len(pxhs_unmatched)}):")
        for name in pxhs_unmatched:
            print(f"  - {name}")

    # Count courses with actual description text
    with_desc = sum(1 for c in courses if c.get("course_description"))
    print(f"\nCourses with description text: {with_desc}/{len(courses)} ({100*with_desc/len(courses):.0f}%)")

    # Write JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    catalog = {
        "school": "Shanghai American School",
        "academic_year": "2026-27",
        "campuses": ["PDHS", "PXHS"],
        "total_courses": len(courses),
        "courses": courses,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\nOutput written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
