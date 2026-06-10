#!/usr/bin/env python3
"""Validate Economics depth JSON: per-unit understandings, issues, topics, AO depths.

Real guide shape (2022): each unit opens with a recommended-time marker;
units 2-4 carry two real-world issues each (inquiry question + conceptual
understandings + key concepts); unit 1 carries unit-level conceptual
understandings. Topics are N.N blocks with AO-depth markers, diagram lines,
and bold-marked HL-only content.
"""
import json
import sys

d = json.load(open(sys.argv[1]))
units = d["units"]
assert [u["number"] for u in units] == [1, 2, 3, 4]

n_topics = sum(len(u["topics"]) for u in units)
assert n_topics >= 28, f"only {n_topics} topics"  # 31 expected (2+12+7+10)

n_issues = sum(len(u["issues"]) for u in units)
assert n_issues == 6, f"expected 6 real-world issues, got {n_issues}"
for u in units:
    for iss in u["issues"]:
        assert iss["question"].endswith("?"), f"issue question malformed: {iss['question'][:60]}"
        assert iss["conceptual_understandings"], f"issue without understandings (unit {u['number']})"
        assert iss["key_concepts"], f"issue without key concepts (unit {u['number']})"

n_und = sum(len(u.get("conceptual_understandings", [])) for u in units) \
    + sum(len(i["conceptual_understandings"]) for u in units for i in u["issues"])
assert n_und >= 8, f"only {n_und} conceptual understandings"
assert units[0].get("conceptual_understandings"), "unit 1 unit-level understandings missing"

n_blocks = n_hl = n_ao4 = 0
for u in units:
    for t in u["topics"]:
        assert t["code"] and t["title"], t
        for b in t["blocks"]:
            n_blocks += 1
            assert set(b.get("ao_depth", [])) <= {"AO1", "AO2", "AO3", "AO4"}, b["ao_depth"]
            n_hl += bool(b.get("hl_only"))
            n_ao4 += "AO4" in b.get("ao_depth", [])
assert n_hl > 0, "no HL-only blocks found (the guide bolds HL-only content)"
assert n_ao4 > 0, "no AO4 (skills) blocks found"

print(f"OK: {n_topics} topics, {n_issues} issues, {n_und} understandings, "
      f"{n_blocks} content blocks ({n_hl} HL-only, {n_ao4} AO4/skill) across 4 units")
