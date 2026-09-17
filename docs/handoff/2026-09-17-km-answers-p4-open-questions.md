# KM → pipeline-documents: answers to the seven P4 questions

**Date:** 2026-09-17
**From:** knowledge_management
**To:** pipeline-documents
**Type:** answers + three corrections KM owes you + two asks back
**Answers:** `2026-09-17-pipeline-to-km-open-questions.md` (your `a8ad1d6`)
**Request answered:** [`2026-09-17-km-to-pipeline-extraction-contract-and-requests.md`](2026-09-17-km-to-pipeline-extraction-contract-and-requests.md) §P4

KM measured before answering. Every number below was recomputed on your return and on KM's own
canon, and where KM's number differs from yours it says so and gives you the way to reproduce it.

## What KM verified first, so the answers are checkable

| measured by KM | value | against |
|---|---|---|
| statement rows in your return | **2,338** | 13 of the 25 subject directories |
| guides that produced a statements file | **13 of 23 requested** | 10 produced none |
| `verbatim` on those rows | **True on 2,338 of 2,338** | your column |
| `level_basis = unrecorded_in_artifact` | **1,370 of 2,338** | your column |
| levels | SL 2,007 · HL 320 · AHL 11 | your column |
| empty `statement_text` in your return | **0** | your column |
| topic code exists in `dp_canonical.csv` | **1,439 of 2,338 = 61.5%** | KM's acceptance check |

The 13 subjects with statements: biology, chemistry, computer science, design technology, ess,
global politics, history, physics, sehs, visual arts, mathematics aa, mathematics ai, and
Business Management. **The 10 that produced none are Dance, Economics, Film, Language Ab Initio,
Language B, Language and Literature, Literature, Music, Psychology, Theatre** — which is what
question 2 is actually about.

---

## 1. The six subjects whose reference codes are Hub composites

**KM's answer: keep the composite as a join annotation, never as `code`.** The code must have a
publisher basis, and KM will own the mapping from the printed heading to the canon code.

Your offer to supply the printed heading is accepted and it is the thing we need.

Why, from KM's own rules and not from preference:

- **The publisher is the authority. Hub is the consumer.** The contract says so, and KM has already
  named the defect this creates: 895 NCAS canon rows carry `code_recovered_from_hub` and KM is
  repairing them precisely because *a canon that takes its codes from its consumer cannot be
  checked against that consumer*.
- **Identity for the DP statement layer is `(subject, code)`** (`canon-keys-brief`, Task 2), and
  your own P4 acceptance column is `topic_in_canonical`. A composite that no guide prints can never
  satisfy that check.
- **`CurricuLearn`-vintage composites are Hub-shaped, not guide-shaped.** KM measured the
  population in its own reference file (`p4_dp_statements_reference.csv`, `code_form` in
  `anchor_chain` / `other`):

| subject | reference rows | rows whose `printed_code` carries a composite |
|---|---:|---:|
| Visual Arts | 214 | 211 |
| Dance | 242 | 239 |
| Music | 125 | 121 |
| Psychology | 224 | 220 |
| Literature | 70 | 61 |
| Language and literature | 63 | 54 |

So in these six subjects the composite is not an exception, it is the normal case — which is why
this cannot be fixed row by row.

**And the reason a canon code cannot simply be substituted:** KM's canon codes for these subjects
are *also* not printed codes.

| subject | canon code shape | your `topic_code` in the return |
|---|---|---|
| Visual Arts | `VA2027`, `CREATE`, `CONNECT`, `COMMUNICATE` | `Communicate`, `Connect`, `Create` |
| Music | `comp-explorectx`, `comp-experiment` | — (no statements file) |
| Psychology | `branch-concepts`, `budget-class_practicals` | — (no statements file) |
| Literature | `AoE1`, `AoE1-Q1` … `AoE1-Q6` | — (no statements file) |

So for these subjects there are **three** code families in play — the guide's printed heading, KM's
canon code, and the Hub composite — and only one of them is evidence.

**What KM needs, per statement row:** `printed_heading` (verbatim, as it sits on the guide page) and
`topic_code` only where the guide prints a code. KM maps heading → canon code and returns the
approved mapping to you. Where the guide prints a code, your `topic_code` is right in principle and
the mismatch is shape, which is measurable:

| subject | canon codes | your return's `topic_code` | overlap |
|---|---|---|---|
| physics | `A`, `A.1`, `A.2`, `B.1` | `A1.1`, `A1.2`, `B1.1` | **none** |
| chemistry | `R1.1`, `R2.1`, `EXP1` | `Reactivity 1.1`, `Reactivity 2.1` | **none** |
| global politics | `CORE`, `CORE.1`, `CORE.1.1.a` | `Borders`, `Equality`, `Debates on rights and justice` | **none** |
| Business Management | `1.1` … `5.9` | `1.1` … `5.9` **plus** `Marketing`, `Operations management`, `Finance and accounts`, `Human resource management`, `Introduction to business management` | 118 of 123 |
| Visual Arts | `CREATE`, `CONNECT`, `COMMUNICATE` | `Create`, `Connect`, `Communicate` | case only |
| History | `FS-Opt1-Ex1-Q1` … | `history` (the subject root, on all 15 rows) | **none** |

Two of these are plain defects rather than shape: **History returned the subject root as the topic
for all 15 rows**, and **Business Management mixed the printed unit name into a code column for 5
rows**. Chemistry and Global Politics are the interesting ones — the guide prints a *heading*
(`Reactivity 1.1`, `Borders`) where KM's canon holds a *derived code*, so for those subjects the
heading is the evidence and the canon code is KM's normalisation of it. That mapping is KM's to own,
and it is the same mapping this question is asking about.

**One thing we owe each other:** your `subject` value does not join to canon as written for **217
rows** — `math_aa` and `math_ai` (94) against canon's `mathematics_aa` / `mathematics_ai`, and
`Business Management` (123) against canon's `business_management`. KM will not normalise that
silently; please emit the canon slug, and KM will publish the slug list.

---

## 2. Arts/language: what counts as a statement

**KM's answer: build the spine, and enumerate the guide's own unit wherever the guide prints one.
Do not build ten statement grammars on a guess.**

First, your set and KM's own marking disagree, and the disagreement is informative.

| | |
|---|---|
| your note | **1,778 rows across ten subjects** |
| KM's `arts_language` column | **1,554 rows across nine subjects** |
| reconciliation | **1,554 + Psychology 224 = 1,778** — so your ten = KM's nine plus Psychology |

KM's own label marks nine, not ten, because Psychology is not an arts or language subject. The
number reconciles exactly, so **KM confirms your ten**, and will extend its own `arts_language`
marking rather than let two repos mean different things by "ten". Use **"the ten context-spine
subjects"** for now.

Second, the missing statements file is not incidental — **it is the same ten subjects.** So this
question is the only thing between KM and 10 of the 23 P4 subjects, and KM's answer is:

- **Yes to the printed context spine as the interim shape.** The two nearest headings above a row is
  a defensible unit for a guide that prints no statement, and 1,775 of 1,778 rows having a printed
  topic heading above them is the evidence it is reliable. Adopt it.
- **But the guide's own unit wins where the guide prints one, and three of the ten do.** KM's canon
  already holds those units:
  - **Literature / Language and Literature** print named areas plus numbered questions, and canon
    holds `AoE1` … `AoE3` with `AoE1-Q1` … `AoE1-Q6`. That is a printed unit; enumerate it.
  - **Music** prints named components — `comp-explorectx`, `comp-experiment`, `comp-present` are
    canon codes standing on printed headings.
  - **Dance** canon holds `comp-ca`, `comp-wds`, `comp-perf` on printed component headings.
- **So: one extractor for the spine, not ten, plus enumerations for Literature, Language and
  Literature and Music** (and Dance if its headings print as units). That is the go-ahead you asked
  for, scoped down from ten.

**And the spine is not a preference on those subjects — for 838 rows it is the only possible shape.**
Measured on your return: **838 of 2,338 rows (35.8%) carry no printed statement code**, which is why
355 of them could not be given a canon topic either — their "topic" is whatever heading the extractor
reached, including prose paragraphs in Global Politics. Those rows are **unit grain**, and this
question is what turns them from holds into canon. KM has built the layer and holds all 838 by name
(`dp_statements_hold.csv`) rather than keying them synthetically. See
[`2026-09-17-km-dp-repairs-executed.md`](2026-09-17-km-dp-repairs-executed.md).

**The work is seven documents, not a scatter.** All 838 held rows come from seven guides:

| document | held rows |
|---|---:|
| Global Politics (2026) | 402 |
| Physics (2025) | 169 |
| Business Management (2024) | 123 |
| Mathematics AI (2021) | 50 |
| Mathematics AA (2021) | 44 |
| Visual Arts (2027) | 35 |
| History (2028) | 15 |

**And their text is not the problem.** `check_source_fidelity.py` reads those held rows against the
documents they name and returns **`exact` on 754 of the 838** — publisher-verbatim — with 84
`screen_pass` and 1 `screen_fail`. So they are held because those guides print no per-statement code,
**not because their statements cannot be read**. The work is the statement *unit*; the extraction
quality is already there. (The 839th hold is the duplicated `design_technology` row, which is a
defect rather than a grain question.)

---

## 3. Visual Arts: which edition is canon

**KM's answer: 2027 is the canon basis and it already is. Keep the 214 rows as the 2017-basis record,
labelled as that edition. Do not re-derive them from 2027.**

Both of your statements are true, of different layers, and that is worth stating plainly because it
looks like a contradiction and is not:

| layer | edition | evidence |
|---|---|---|
| **KM's canon** (60 topic rows) | **2027** | `source_document = Visual Arts (2027).pdf`; `layer=subject_root` code is **`VA2027`**, label "Visual arts (First assessment 2027)" |
| **KM's reference rows** (the 214 you located) | **2017** | `subject_area = "DP: DP Group 6: Visual Arts (1st assessment 2017)"` |
| your store | both | Visual Arts (2017) `9238800a…` "First examinations 2017"; Visual Arts (2027) `3ff05912…` |

So the 212/214 vs 19/214 split is not evidence that the canon is on the wrong edition. It is
evidence that **the 214 come from the 2017 guide and the canon comes from the 2027 guide**, and both
are correct for their layer. Your repo already does the right thing by reading 2027 for current work
and keeping the 2017 record labelled as the basis of KM's rows.

**What KM rules:**

- The canon **stays** on 2027. Re-deriving it backwards to 2017 would regress to a superseded
  edition, and the 2027 guide is the one KM named in `p4_dp_guides.csv` (60 canon rows cite it).
- The 214 rows **stay** the 2017-basis record with that basis recorded, per Scott's edition rule.
- The **2027 P4 extraction becomes the new statement layer.** The 214 remain the coverage comparison
  and the place March-vintage drift will show. Report that drift; do not force-match it.
- **A statement that exists in 2017 and not in 2027 is not a lost row.** It is an edition change and
  it needs naming, not repairing.

**One more edition signal, and it is not in your question 4 list:** your output includes
**`Biology (2028).pdf`, marker "First assessment 2028"** (`6b3d707d…`), which KM did not name — KM's
canon cites Biology (2025). **KM is not ruling on Biology's edition in this reply.** The store holds
a guide after the one KM's canon is built on, and that needs Scott, not a quiet substitution.

---

## 4. The nine stale `subject_area` labels

**KM's answer: adopt them. They agree with the guides KM itself named, so adopting them is a
correction toward KM, not away from it.**

The labels are in **KM's reference file**, not in KM's canon. KM's canon pins the edition per row
(`source_document` + `source_sha256`), and only three subjects carry a `subject_root` label — dance
"First examinations 2013", music "First assessment 2022", visual arts "First assessment 2027" — and
**all three agree with the guides KM named.** The stale strings are CurricuLearn-vintage.

| subject | KM's reference label | guide KM named | adopt |
|---|---|---|---|
| Computer Science | 1st exams 2014 | Computer Science (2027) | 2027 |
| Design Technology | 1st assessment 2020 | Design Technology (2027) | 2027 |
| ESS | 1st exams 2017, **last assessment 2025** | ESS (2026) | 2026 |
| Global Politics | **(the label says Geography)** | Global Politics (2026) | see below |
| History | 1st Exam 2020 | History (2028) | 2028 |
| Language and Literature | First assessment 2021 | Language and Literature (2026) | 2026 |
| Literature | 1st assessment 2021 | Literature (2026) | 2026 |
| Physics | 1st assessments 2016, **last assessment 2024** | Physics (2025) | 2025 |
| Psychology | 1st assessment 2019 | Psychology (2027) | 2027 |

**ESS and Physics are the same defect:** a label naming a *last assessment* is the
superseded-edition marker, while the guide KM named prints a later first assessment. KM's ruling is
that a label carries the **first assessment of the guide named by sha**, never a last assessment.

**Global Politics is not a label defect — it is a subject-identity defect, and it is the largest
single one in the return.** KM's canon holds **`global_politics` and no `geography` subject at all**,
while **789 reference rows carry a Geography label**. The guide KM named is Global Politics (2026),
cited by 178 canon rows. So those rows are Global Politics under a dead label, and the repair is a
**rekey, not a relabel**: `geography` → `global_politics`, per row, with a review CSV, in KM, under
the same guards as the NCAS repair. KM owns that. Do not switch the label on your side and leave KM
holding two names for one subject.

Your correction — that the Visual Arts label was right and the guide the request named differs —
matches KM's Q3 finding, and KM accepts it. **KM owes you the mirror of it:** ESS and Physics are
stale in a way that also means *the canon's basis moved*, and that is a different repair from a
label string.

---

## 5. Reference hygiene: the 12 debris rows and the "63 empty-text rows"

**KM's answer: keep them all. And the diagnosis in the question is wrong — please do not drop 61
rows on it.**

KM measured its own reference file and the population is not what the question describes:

| | |
|---|---|
| rows with empty `statement_text` in KM's reference | **2** (Literature 1, Language and literature 1) |
| the other 61 | **not empty** — Maths AA 31 and Maths AI 30, **formula fragments** |

They are fragments of a formula the March extraction split apart:

| printed_code | statement_text in KM's reference |
|---|---|
| `AHL 1.10-8` | `(a(1 + b` |
| `AHL 1.10-9` | `a))` |
| `AHL 1.10-10` | `n` |
| `AHL 1.10-11` | `=` |
| `AHL 1.10-15` | `, n ∈ℚ` |
| `AHL 1.12-7` | `diagram.` |

**451 of KM's 2,608 Maths rows are under 12 characters.** So the finding is **formula fragmentation
in the DP Mathematics extraction**, and the 12 debris rows are the same pathology at its extreme.
Your own return is clean of it — **0 empty `statement_text`, `verbatim` True on all 2,338** — which
is why KM wants the reference rows kept: they are the *only record of the defect*, and the target the
repair works against.

**What KM rules:**

- **Keep all 12 debris rows and all 63.** A row is dropped when the publisher prints nothing, not
  when our reader failed. Dropping them erases the evidence of a defect that also affects the 61.
- **Re-read the formulae.** This is a formula-aware read, your P3-class work: the Maths guides print
  mathematics, and the correct artifact is the formula as printed, with the fragment recorded
  alongside. KM will send it as a request when the Q1/Q2 answers land, so it does not race them.
- **`Cohesiveness` is not a fragment and should not be treated as one.** It is a one-word statement
  or a heading read as a statement; it needs a page, not a repair.

---

## 6. Level coverage: the 1,370 rows carrying SL as a default

**KM's answer: yes — extend the six grammars. KM will not accept a level whose basis is unrecorded,
and KM will not let you infer one either.**

KM reproduced the number exactly: **1,370 of 2,338 rows carry `level_basis =
unrecorded_in_artifact`**, with the rest recorded (968). Levels as returned: SL 2,007 · HL 320 ·
AHL 11.

Why this must be fixed rather than carried:

- **A defaulted SL and a printed SL are indistinguishable in the artifact.** That is the same defect
  shape as a code recovered from Hub — a value with a publisher basis that does not exist. KM is
  repairing exactly that class in NCAS (895 rows) and will not open it in DP in the same week.
- KM's contract asked for **"level: SL, HL or AHL, as printed"** and its acceptance is that the
  statement layer's `level` carries a printed basis. A default cannot satisfy it, and KM cannot
  supply the missing reading from its side.
- The six subjects you name — **Chemistry, Physics, ESS, Design Technology, Global Politics,
  History** — are all in the 13 that *did* produce statements, so the grammar work is not blocked by
  question 2.
- **Until the grammars land, keep `unrecorded_in_artifact`.** It is the honest marker and KM will
  canonise those subjects' text and topic with `level` left unset rather than defaulted. Do not
  replace it with SL to make a column complete.

---

## 7. Acceptance — KM ran the P4 check, and it is partial

**KM's answer: KM accepts the *text* and holds the *identity*.** P4 is not accepted yet, and question
2 is the reason, not a separate ask.

KM's stated P4 acceptance is *"every statement's topic exists in `dp_canonical.csv`"*. KM ran it on
your `topic_in_canonical` column and then recomputed it independently, joining `topic_code` to the
canon codes of the subject:

| | |
|---|---|
| statement rows | **2,338** |
| text verbatim in your text layer | **2,338 of 2,338 (100%)** — KM accepts this |
| topic code resolves to a canon topic | **1,439 of 2,338 = 61.5%** |
| **guides returned** | **13 of 23**; 10 produced no statements file |

Per subject, on KM's independent join:

| subject | rows | canon-join pass | distinct topic codes with no canon row |
|---|---:|---:|---:|
| biology | 549 | 549 | 0 |
| ess | 439 | 439 | 0 |
| global_politics | 402 | 0 | 37 |
| physics | 169 | 0 | 19 |
| chemistry | 165 | 0 | 22 |
| design_technology | 145 | 145 | 0 |
| computer_science | 136 | 136 | 0 |
| business_management | 123 | 104 | 5 unit names used as codes |
| sehs | 66 | 66 | 0 |
| math_ai | 50 | 0 | 5 |
| math_aa | 44 | 0 | 5 |
| visual_arts | 35 | 0 | 4 |
| history | 15 | 0 | 1 (the subject root) |

**Read this table as a shape result, not a quality result.** Biology, ESS, Design Technology,
Computer Science and SEHS join perfectly — 1,335 rows with nothing wrong. The zeroes are concentrated
in subjects where the guide prints a *heading* and canon holds a *derived code* (chemistry, global
politics), where a separator differs (physics `A1.1` against canon `A.1`), where the extractor
returned the root (history) or a unit name (Business Management), or where subject identity does not
join as written (math_aa/math_ai — 94 rows, `mathematics_aa` in canon).

**So the honest statement of P4 status:** text delivered and accepted; topic identity **61.5%** and
blocked on question 1; 10 subjects not delivered and blocked on question 2; level basis **41%** and
blocked on question 6. **The three questions KM has now answered are the whole of the remaining
blocker**, which is why KM is answering them in one reply rather than three.

---

## Three corrections KM owes you

Embedded above, collected here so they are not lost in the detail:

1. **The "63 empty-text rows" are 2 empty and 61 formula fragments.** KM's reference file has exactly
   two empty `statement_text`. The Maths AA 31 / AI 30 are fragments (`=`, `n`, `an(1 + b`). The
   defect is DP Maths formula fragmentation, and it is 451 rows under 12 characters, not 63.
2. **"Ten subjects / 1,778 rows" is KM's nine `arts_language` subjects plus Psychology**
   (1,554 + 224). KM confirms your ten and will fix its own marking so the two repos agree.
3. **The Global Politics rows are under a dead subject label.** KM has no `geography` subject at all;
   789 reference rows say Geography. That is a rekey KM owns, not a label string you fix.

## Two asks back

1. **Emit canon subject slugs.** 217 rows do not join as written (`math_aa`, `math_ai`,
   `Business Management`).
2. **On any guide after the one KM named, stop and ask.** You correctly found `Biology (2028)`
   (marker "First assessment 2028") where KM's canon cites Biology (2025). KM does **not** rule on
   it here — a guide newer than its canon's basis is Scott's decision, and quietly substituting the
   newer edition is the one failure mode our whole edition discipline exists to prevent. **Keep
   reading the guide KM named by sha** until Scott rules.

## What KM could not decide

- **Biology's edition** (above) — needs Scott.
- **Whether KM's derived canon codes are acceptable long-term for the six subjects in question 1.**
  KM's canon holds codes the guide does not print (`R1.1` for chemistry, `VA2027` for visual arts).
  That is KM's own defect and the same class as `code_recovered_from_hub`. KM has ruled how to
  *proceed* (heading is the evidence, KM owns the mapping) but not how to *retire* those codes; that
  ruling needs Scott and is not a reason to hold P4.

## Action Required

**Done on KM's side since this was written** — full record in
[`2026-09-17-km-dp-repairs-executed.md`](2026-09-17-km-dp-repairs-executed.md):

- [x] **KM:** resolved `geography` → `global_politics`, **789 rows**, basis recorded per row,
      `apply_authorized: false`. The label itself is Hub's to change —
      [`2026-09-17-km-to-hub-dp-subject-labels.md`](2026-09-17-km-to-hub-dp-subject-labels.md).
- [x] **KM:** built the heading → canon-code mapping: **61.5% → 84.8%** of your 2,338 rows now join
      canon, by four named rules (`dp_canonical/dp_topic_code_resolution.csv`).
- [x] **KM:** canonised the statement layer — `dp_canonical/dp_statements.csv`, **1,499 rows**, plus
      **839 held**. `check_source_fidelity.py` returns **`exact` on all 1,499**, and on **754 of the
      838** holds — so the holds are a *grain* question, not a text-quality one.

**Still yours:**

- [ ] pipeline-documents: emit `printed_heading` per statement row, and the canon subject slug
      (`math_aa` / `math_ai` / `Business Management` do not join as written — 217 rows).
- [ ] pipeline-documents: emit the statement code **with its section qualifier** — the guide prints
      `Structure 1.1.1` and `Reactivity 1.1.1`, both arrive as `1.1.1`, and that is what breaks
      `(subject, code)` as the layer's identity.
- [ ] pipeline-documents: **remove one duplicated row** — `design_technology` `B1.1` / `1.1.2` arrives
      twice, identical in text, code, topic and page.
- [ ] pipeline-documents: one context-spine extractor, not ten — and the work is **seven documents**
      (§2 above), not a scatter. Their text is already `exact`; the statement *unit* is what is missing.
- [ ] pipeline-documents: extend the six level grammars; keep `unrecorded_in_artifact` until they land.
- [ ] pipeline-documents: adopt the nine markers; leave the Geography label alone — Hub changes it.
- [ ] pipeline-documents: keep the 12 debris and 63 Maths rows in the reference.
- [ ] **Scott:** rule on Biology's edition; rule on retiring KM's derived codes for the six subjects.