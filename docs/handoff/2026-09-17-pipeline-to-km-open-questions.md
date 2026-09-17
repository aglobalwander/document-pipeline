# To knowledge-management — the P4 returns are in; here is everything we need from you in one place

**Date:** 2026-09-17
**From:** pipeline-documents (session with Scott)
**Claim class:** `finding` for the evidence below, `request` for the asks. Nothing here is a canon row.

Everything we have delivered is in `docs/handoff/OUTGOING.md` (2026-09-17 P4 entry) and under
`data/output/km_requests/2026-09-17/`. **Five answers unblock the rest.**

---

**1. The six subjects whose reference codes are Hub composite IDs — what should a code be?**

- **We have:** all 22 subjects located. But 236 rows survive *both* a strict and a tolerant
  topic-code check, and only in six subjects: Visual Arts 94, Dance 57, Music 34, Psychology 24,
  Literature 14, Language and Literature 13. Their `printed_code` values are Hub composites
  (`ArtMaking-C13`, `CompAnalysis-C10_2`, `Concepts-Bias-Desc`, `Experiment-creator-C1`, `AC-10`),
  which no guide prints.
- **We need:** do those rows keep the composite ID as their code, should the code be the printed
  heading they sit under (we can supply it — see 2), or something else?
- **Why it matters:** this is the only thing between you and a topic-tree-shaped P4 for those
  subjects.

**2. Arts/language: what counts as a statement?**

- **We have:** rather than build ten grammars on a guess, we gave each of your reference rows its
  printed context read from the guide itself (the two nearest headings above the row): 1,778 rows
  across the ten subjects, all but three with a printed topic heading above them.
- **We need:** is that the shape you want, or do you want the guides' own statement units enumerated?
  The latter is one extractor per subject and we want your go-ahead before building ten.

**3. Visual Arts edition**

- **We have:** the store holds the superseded 2017 guide, and your 214 rows locate **212/214
  (99.1%)** in it against **19/214 (8.9%)** in the 2027 guide the request named. Our repo now reads
  the 2027 guide for current work and keeps the 2017 record labelled as the basis of your rows
  (Scott's edition rule, recorded per artifact in `source.json`).
- **We need:** on your side, do the 214 canon rows stay the 2017 record labelled as that edition, or
  do you want them re-derived from the 2027 guide?

**4. Nine `subject_area` labels are stale**

- **We have:** ten labels disagree with the marker printed in the guide you named. For nine of them
  your content locates in that named guide at 87–100%, so the text is the newer edition and the
  label is not. Markers we read: Computer Science **2027**, Design Technology **2027**, ESS **2026**,
  Global Politics **2026**, History **2028**, Language and Literature **2026**, Literature **2026**,
  Physics **2025**, Psychology **2027**. Two extra defects: Global Politics' label says *Geography*,
  and ESS' label ends at "last assessment 2025" while the guide we hold prints 2026.
- **We need:** adopt these values, or tell us what to send instead. Labels are yours; we only read
  the markers.

**5. Reference hygiene: 12 debris rows and 63 empty-text rows**

- **We have:** 12 rows with 0.0 document coverage that read as fragments (`Col1`, `Col3`, `ofAB`,
  `(notA)`, `, wheren = ∑`, `cohesiveness`), and 63 rows with empty `statement_text` (Maths AA 31,
  Maths AI 30, Literature 1, Language and Literature 1). Ids and text are in
  `p4_dp_statements/statements_located.jsonl`.
- **We need:** keep them, or drop them from the reference?

---

**Two smaller calls also pending:**

**6. Level coverage.** `level` is a printed reading for 968 of our 2,338 statements. For six subjects
  (Chemistry, Physics, ESS, Design Technology, Global Politics, History) the extractors do not catch
  those guides' "Additional higher level" markers, so 1,370 rows carry `SL` as a default with
  `level_basis = unrecorded_in_artifact`. Do you want us to extend those grammars so every level is a
  reading? We will not infer levels without your answer.

**7. Acceptance.** P1 (including the Economics skeleton addendum), P2, P3 and P4 all await your
  acceptance check. Each return states what to check and where the counts live.

---

**Corrections we owe you, already applied in the return:** the topic-code problem is 236 rows in six
subjects, not 2,525 rows in nine (our first check compared codes literally, and tolerating the
layers' spacing / theme-name / dropped-letter forms resolved 2,289 of them); and the Visual Arts
label was *right* while the guide the request named differs — the mirror of point 4.