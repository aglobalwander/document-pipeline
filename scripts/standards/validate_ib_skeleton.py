#!/usr/bin/env python3
"""Validate an IB skeleton JSON against the Economics pilot contract (spec section 3)."""
import json
import sys

sk = json.load(open(sys.argv[1]))

aos = sk["assessment_objectives"]
assert [a["code"] for a in aos] == ["AO1", "AO2", "AO3", "AO4"], f"AO codes: {[a['code'] for a in aos]}"
assert all(a["grain"] == "course" for a in aos)
assert all(a["objective_type"] == "Assessment Objective" for a in aos)
assert all(a["bullets"]["SL"] and a["bullets"]["HL"] for a in aos), "AO bullets missing a level"

units = sk["units"]
assert [u["number"] for u in units] == [1, 2, 3, 4]
assert units[1]["title"] == "Microeconomics", units[1]["title"]
assert all(u["hours"].get("SL") and u["hours"].get("HL") for u in units), "unit hours missing a level"
n_topics = sum(len(u["topics"]) for u in units)
assert n_topics >= 28, f"only {n_topics} topics across units"
assert all(t["code"] and t["title"] for u in units for t in u["topics"])

concepts = {c["label"] for c in sk["concepts"]}
assert concepts == {"scarcity", "choice", "efficiency", "equity", "economic well-being",
                    "sustainability", "change", "interdependence", "intervention"}, concepts

assert len(sk["aims"]) >= 3, f"only {len(sk['aims'])} aims"
assert set(sk["levels"]) == {"SL", "HL"}

comps = {(c["name"], c["level"]) for c in sk["assessment_components"]}
assert ("Paper 3", "HL") in comps, "HL Paper 3 missing"
assert ("Paper 3", "SL") not in comps, "Paper 3 must be HL-only"
for lvl in ("SL", "HL"):
    for name in ("Paper 1", "Paper 2", "Portfolio"):
        assert (name, lvl) in comps, f"{name} {lvl} missing"
for c in sk["assessment_components"]:
    assert c["weighting_pct"], f"component {c['name']} {c['level']} missing weighting"
    assert c["aligned_aos"], f"component {c['name']} {c['level']} missing aligned AOs"

print(f"OK: 4 AOs, 4 units ({n_topics} topics), 9 concepts, {len(sk['aims'])} aims, "
      f"{len(sk['assessment_components'])} assessment components, HL/SL")
