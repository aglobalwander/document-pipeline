"""Clean + structure ACARA Technologies (Design + Digital) standards from the Excel into
records ready for Hub (new framework) + the KM deconstruction pipeline. Deterministic, no LLM."""
import json, re
from pathlib import Path
import pandas as pd

SRC = "data/input/excel/ACARA Design Standards Database.xlsx"
OUT = Path("data/output/acara"); OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(SRC)
df["Strand"] = df["Strand"].ffill()
df["CdCode"] = df["CdCode"].ffill()

# subject_area + strand_type from the strand label; subject from code prefix
PREFIX_SUBJECT = {"ACTDEK":"Design and Technologies","ACTDEP":"Design and Technologies",
                  "ACTDIK":"Digital Technologies","ACTDIP":"Digital Technologies"}
PREFIX_STRANDTYPE = {"ACTDEK":"Knowledge and Understanding","ACTDIK":"Knowledge and Understanding",
                     "ACTDEP":"Processes and Production Skills","ACTDIP":"Processes and Production Skills"}

records = []
for code, grp in df.dropna(subset=["CdCode"]).groupby("CdCode", sort=False):
    rows = grp["ContentDesc"].dropna().tolist()
    if not rows: continue
    content = str(rows[0]).strip()                 # first non-null = the content description (standard)
    elaborations = [str(r).strip() for r in rows[1:] if str(r).strip()]   # rest = elaborations
    pref = re.match(r"([A-Z]+)", str(code)).group(1)
    records.append({
        "framework": "acara_technologies",
        "standard_id": str(code).strip(),
        "subject_area": PREFIX_SUBJECT.get(pref, ""),
        "strand": str(grp["Strand"].iloc[0]).strip(),
        "strand_type": PREFIX_STRANDTYPE.get(pref, ""),
        "standard_text": content,
        "elaborations": elaborations,
        "elaboration_count": len(elaborations),
        "grade_band": "9-10",  # inferred: codes are the highest in each ACARA Technologies strand (senior band); verify vs ACARA canon
    })

(OUT/"acara_technologies_standards.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
# flat CSV (one row per standard; elaborations joined)
flat = [{**{k:v for k,v in r.items() if k!="elaborations"}, "elaborations": " ||| ".join(r["elaborations"])} for r in records]
pd.DataFrame(flat).to_csv(OUT/"acara_technologies_standards.csv", index=False)
# elaborations long-form CSV (one row per elaboration)
elab = [{"standard_id":r["standard_id"],"elaboration":e} for r in records for e in r["elaborations"]]
pd.DataFrame(elab).to_csv(OUT/"acara_technologies_elaborations.csv", index=False)

import collections
by_subj = collections.Counter(r["subject_area"] for r in records)
by_strand = collections.Counter(f'{r["subject_area"]} — {r["strand_type"]}' for r in records)
print(f"structured {len(records)} ACARA standards (+ {len(elab)} elaborations)")
print("by subject:", dict(by_subj))
print("by strand:", dict(by_strand))
print("output ->", OUT)
