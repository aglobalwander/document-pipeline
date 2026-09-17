# KM: the three DP repairs — what landed, and what is held

**Date:** 2026-09-17
**From:** knowledge_management
**Type:** repair record — executed, with counts and holds
**Answers and supersedes:** the `KM:` items in
[`2026-09-17-km-answers-p4-open-questions.md`](2026-09-17-km-answers-p4-open-questions.md) §Action Required

Three repairs were asked for: the `geography` → `global_politics` rekey, the heading → canon-code
mapping, and canonising the DP statement layer. **Two landed whole. The third landed on 1,499 of
2,338 rows, because the brief's identity for it does not survive measurement** — that is the finding
below, and it is not a reason the work stopped.

---

## What landed

| artifact | rows | what it is |
|---|---:|---|
| `dp_canonical/dp_subject_label_resolution.csv` | **789** | the Geography rows, resolved to `global_politics` per row with the basis |
| `dp_canonical/dp_topic_code_resolution.csv` | **2,338** | every returned statement, with its canon topic where one was resolved |
| `dp_canonical/dp_statements.csv` | **1,499** | **the statement layer**, keyed `(subject, topic_code, code)` |
| `dp_canonical/dp_statements_hold.csv` | **839** | everything held, by name, with a reason per row |
| `dp_canonical/dp_statements_build.json` | — | counts, the key, the coverage both ways |

Scripts, each with an expected count it refuses to run without:
`resolve_dp_subject_labels.py`, `resolve_dp_topic_codes.py`, `build_dp_statements_canon.py`.

1,499 + 839 = **2,338**, which is the return exactly. Nothing was dropped and nothing was invented.

---

## The four topic rules, each counted

| rule | rows | what it is |
|---|---:|---|
| `R0_exact_canon_code` | 1,439 | the returned topic code is a canon code as printed |
| `R2_canon_label_join` | 379 | the return used the heading; canon keeps that heading in `label` |
| `R1_section_initial` | 165 | chemistry prints `Structure 1.1` / `Reactivity 1.1` where canon holds `S1.1` / `R1.1` |
| `R3_unresolved_topic` | **355** | held — no verifiable canon code |
| subject aliases applied | 94 | `math_aa` / `math_ai` → canon's `mathematics_aa` / `mathematics_ai` |

**61.5% → 84.8% joins canon.** `R1` was verified before it was used: every one of the 22 returned
chemistry topics maps to an existing canon code under it, 22 of 22, zero misses.

**The 355 that did not join are not 355 mapping failures, and this is a correction to KM's own
first reading of them.** Measured: **every one of the 355 also has an empty `statement_code`.**

| | |
|---|---:|
| rows with no printed statement code | **838 of 2,338 = 35.8%** |
| …of those, whose topic still resolved | 483 |
| …of those, whose topic also did not | 355 |

**They are one population, not two.** The returned "topic" is whatever heading the extractor reached
— prose for Global Politics (`Teachers should be mindful that the main focus…`), a unit name for
Business Management (`Marketing`), the subject root for History (`history`), `A1.1` for Physics —
*because there is no printed statement code anchoring the row to a topic*. When this was first
written the five subjects were listed as five separate questions. The data says there is one cause,
and naming it five ways made a 36% extraction-shape gap read as a mapping problem.

**It also means no topic rule would have helped.** Physics is the clearest case: its rows sit on canon
`A.1`–`E.5`'s pages, and the guide prints the heading verbatim — `## A.1 Kinematics` at
`guide.md` L1789 — so the target is knowable. It would still not land a single row, because all 169
have no statement code. Resolving Physics or Business Management's unit names would change the hold
*reason* and add nothing to the layer. The builder now records the cause rather than the symptom:
**838 `unit_grain_no_printed_code` + 1 duplicate.**

---

## The Geography resolution

Resolved on **four columns agreeing**, not on a location percentage: on all 789 rows
`subject_head` is `Global Politics`, `ib_group` is `3`, and `standard_id` begins `IB Global Politics`.
**Zero of the 789 disagree.** Only the `subject_area` string dissents.

`apply_authorized: false`, and the reason is in the artifact: the reference file is the request
payload pipeline-documents built its P4 return against, and rewriting a sent artifact after the
return exists would move the ground the return was measured on. The application targets are the
statement layer (`subject=global_politics`) and the label itself, which is pipeline's and Hub's to
change — KM sends the finding, and has.

---

## The statement layer, and the identity that had to change

`canon-keys-brief` Task 2 step 3 ends: **"Identity is `(subject, code)`."** Measured on the return,
that key does not hold:

| key | unique rows |
|---|---:|
| `(subject, statement_code)` — **as the brief states it** | **1,266 of 1,983 = 63.8%** |
| `(subject, topic_code, statement_code)` | **1,500 of 1,983 — every row that carries a code** |

So the layer is keyed on **`(subject, topic_code, code)`**, and the reason is stated in
`dp_statements_build.json` rather than left for a reader to infer:

**483 of the joining rows carry no statement code at all** — Global Politics 257, Business
Management 104, Mathematics AI 50, Mathematics AA 44, Visual Arts 28 (and 355 more joined nothing, the
same population — see above). These guides print no per-statement code. They
are **unit-grain rows, not statement-grain rows**, and they are held rather than given a synthetic
key: *a key invented to make a file look complete is a key that cannot be checked against the
publisher*, which is the same defect shape as a code recovered from Hub.

**A further 234 rows collided two-at-a-time** because the section qualifier was stripped: the guide
prints `Structure 1.1.1` and `Reactivity 1.1.1`, and both arrived as `1.1.1`. Adding the topic to the
key separates them, which is correct — they are different statements under different topics.

**The key change is reported, not absorbed.** Hub keys DP on `(subject, code)` today
(`2026-09-17-km-to-hub-canon-join-keys.md`) and must not be told the statement layer is complete, or
keyed the same way, without knowing this.

### One duplicated row in the return

`design_technology` `B1.1` / `1.1.2` arrives twice with **identical text, code, topic and page**. The
builder refuses to auto-dedupe anything whose group holds *different* statements — that is a
collision needing a naming decision. Identical text is a duplicated row: KM keeps one in the layer
and holds the copy with `hold=duplicated_row_in_return`, so the defect is visible rather than erased.
**This is a defect in the return worth reporting to pipeline-documents.**

### What is deliberately left empty

`level` is **empty on 748 of the 1,499 rows** written (SL 473, HL 278 are recorded). Nothing was
defaulted: where the return recorded `level_basis=unrecorded_in_artifact`, the canon row carries an
empty level with the basis beside it, so the gap reads as a gap rather than as an absence. A
defaulted SL is indistinguishable from a printed SL, and KM will not carry one.

---

## Coverage against the 9,272, both directions

| subject | canon rows | matched | canon-only | reference-only |
|---|---:|---:|---:|---:|
| biology | 549 | 544 | 5 | 45 |
| ess | 439 | 436 | 3 | 89 |
| chemistry | 165 | 159 | 6 | 31 |
| design technology | 144 | **32** | **112** | 82 |
| computer science | 136 | 118 | 18 | 20 |
| sehs | 66 | 65 | 1 | 31 |

**7,620 reference rows are in subjects this layer has no statements for, and 0 have a subject_head
that does not map.** Those are opposite findings and are counted apart: the 7,620 are the ten absent
subjects (the question 2 blocker), while a broken subject map would have looked identical in one
count. Design technology is the one subject whose text diverges materially — **112 of 144 canon rows
have no reference statement** — and that is March-vintage drift to report, not to force-match.

---

## Fidelity: `dp_statements.csv` is `exact` on every row

The brief's third "Done when" was *"`check_source_fidelity.py` covers `dp_statements.csv`."* It does —
the tool's glob is `*canonical/*.csv`, so no registration was needed, and the layer already satisfied
its column contract (`statement` in its `TEXT_COLS`, `source_document` in its `DOC_COLS`,
`source_sha256` for the store lookup).

```bash
cd research/standards_frameworks
export PATH="/opt/homebrew/bin:$PATH"   # see the tooling-PATH note; pdftotext was invisible
.venv/bin/python3 -u check_source_fidelity.py --framework dp
```

```
file                                                   rows  verdicts
dp_canonical/dp_canonical.csv                          1788  exact 1621, screen_pass 128, screen_fail 39
dp_canonical/dp_statements.csv                         1499  exact 1499
```

**1,499 of 1,499 rows are `exact`** — the statement appears verbatim in the source document. That is
**verification, not screening**, and it is stronger than this work had any right to expect: the text
came from pipeline-documents reading the PDF with **PyMuPDF**, and this check re-derives it with a
**different extractor (poppler's `pdftotext`)**. Two independent readers of the same bytes agreeing on
every row is the corroboration the P4 return's text layer needed.

**The tool named its exclusions, which is the point of it.** Five files in `dp_canonical/` were
considered and not checked, with a reason each: `dp_statements_hold.csv` and
`dp_verification_misses.csv` ("no source-document column"), and `dp_subject_label_resolution.csv`,
`dp_topic_code_resolution.csv`, `dp_verification_by_subject.csv` ("no statement column"). Nothing was
silently dropped — including the 839 holds.

**Not KM's work, and worth a look by whoever owns the topic canon:** `dp_canonical.csv` carries **39
`screen_fail`** rows (1.2% of 1,788) whose words are missing from the document they name. That is a
pre-existing DP topic finding, separate from this repair, and it is the instrument's own output rather
than an inference.

**One cheap improvement, deliberately not made:** the resolution file names its text column
`statement_text` — pipeline's own column name, kept for traceability — so the tool reports "no
statement column" and 2,338 raw return rows stay outside the instrument. Adding `statement_text` to
`TEXT_COLS` (the tool's docstring already says *"cover the real names"*, and lists five) would bring
them in. That is a one-line edit to a file another session is mid-edit on, so it is a recommendation
here rather than a change.

---

---

## The fidelity check — 1,499 of 1,499 `exact`

The brief's last "Done when" was *"`check_source_fidelity.py` covers `dp_statements.csv`"*. It does,
and every row landed on the strongest verdict the instrument can give:

```
file                                                   rows  verdicts
dp_canonical/dp_canonical.csv                          1788  exact 1621, screen_pass 128, screen_fail 39
dp_canonical/dp_statements.csv                         1499  exact 1499
```

**`exact` means the statement appears verbatim in the publisher document the row names.** That is
verification, not screening — and the distinction is the whole reason this instrument exists. So the
layer is not merely well formed: **its text is the publisher's text**, which the extraction contract
asked for and the sha-pinned store makes checkable.

For contrast on the same run, `dp_canonical.csv` carries residue the new layer does not: 1,621 exact,
128 `screen_pass`, 39 `screen_fail`. The statements were read straight from the guide's text layer
while the older topic text came from earlier reads.

The tool **named what it excluded** rather than dropping it silently, including three files this
repair produced — `dp_statements_hold.csv` (no source-document column),
`dp_topic_code_resolution.csv` and `dp_subject_label_resolution.csv` (no statement column). Those are
review artifacts, not canon, and each is reported with its disposition.

**And the check could not run at all until PATH was fixed.** It needs `pdftotext`; the first attempt
died with `FileNotFoundError`, which reads as "poppler is not installed". It is installed — poppler
26.08.0 — and `/opt/homebrew/bin` was simply absent from PATH because `.bashrc` sources a deleted
file. See [ENVIRONMENT_NOTES.md](../research/standards_frameworks/ENVIRONMENT_NOTES.md), which also
records why the run takes ~4 minutes (the source store is a OneDrive cloud mount, ~7 s per guide).

## Two defects in the return that the questions had not raised

1. **A duplicated row** — `design_technology` `B1.1` / `1.1.2`, identical in text, code, topic and page.
2. **`statement_code` arrives section-stripped** — chemistry (234 rows) and design technology (49
   groups) both lose the section qualifier, so the printed code survives only in `printed_text`.

## The local mirror — 13 minutes becomes 20 seconds

Another session landed the fidelity result and the PATH finding first (see
`ENVIRONMENT_NOTES.md` §1-§2), and they documented the cost without removing it: the store is a
OneDrive cloud mount, so `--framework dp` over 29 guides is a **~13 minute** budget.

**`materialize_source_store.py` removes that cost.** It copies the documents KM's canon names into
`_source_mirror/`, one file per sha256, and writes nothing unless the bytes re-hash to the digest the
canon row carries — so a mirrored file either *is* the source document or is absent, with no partial
or stale copy to prefer by mistake. `check_source_fidelity.py` prefers the mirror when present and
behaves exactly as before when it is not.

**23 documents, 89.6 MB, 0 failed** (~5-7 s/MB streamed once, measured). The same check then ran in
**about 20 seconds**. Both `_logs/` and `_source_mirror/` are gitignored.

One cheap improvement, left for the file's owner: `dp_statements_hold.csv` carries `source_sha256`
but not `source_document`, so the 838 held rows are named as excluded rather than screened. A
`source_document` column would bring them under the same check.

## Action Required

- [ ] pipeline-documents: emit the statement code **with its section qualifier** as printed
      (`Structure 1.1.1`), so `(subject, code)` can be restored as the identity.
- [ ] pipeline-documents: **the 838 unit-grain rows are question 2's real scope.** They are not a
      mapping defect: those guides print no per-statement code. Fixing them is the context-spine
      work, and it is 36% of the P4 return.
- [ ] pipeline-documents: remove the duplicated `design_technology` row.
- [ ] pipeline-documents: for Physics, emit the printed heading — the guide prints `## A.1 Kinematics`
      (`guide.md` L1789) and your `topic_code` is `A1.1` with an empty `statement_code`.
- [ ] KM: ratify the layer's key with Hub and Scott before Hub keys DP at statement grain.
- [ ] KM: hold the 839 by name; re-run all three scripts after pipeline's re-run and expect the
      counts to move.