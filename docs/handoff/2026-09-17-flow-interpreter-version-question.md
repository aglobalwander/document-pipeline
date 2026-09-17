# Interpreter version for pipeline-documents: 3.10 or 3.14?

**Date:** 2026-09-17
**From:** pipeline-documents (agent session with Scott)
**To:** flow — ecosystem runtime question; needs a ruling, not a code change from this repo
**Claim class:** `finding` for the facts below; each one cites the file, line or command that shows it.
No ruling is asserted. Nothing in this note is a canon row.
**Status:** resolved 2026-09-17 — flow ruled the narrow ceiling; Scott directed the floor raise to
3.13. Applied in `pyproject.toml` (`python = ">=3.13,<3.14"`), new `.python-version` (3.13),
re-resolved `poetry.lock`, 51 passed / 17 deselected on 3.13.15. Evidence returned in
`docs/handoff/OUTGOING.md` (2026-09-17, `[TO: flow]`).

## The ambiguity, in one line

This repo's project constraint admits Python 3.14, one declared dependency forbids it, the repo's own
docs say "3.10+" with no ceiling, no sibling repo and no `MAP.yml` field answers the question, and
Poetry on Scott's Mac resolves the conflict by silently building a 3.14 environment.

## The facts

1. **The project constraint admits 3.14.** `pyproject.toml`: `python = "^3.10"`. Poetry 2.x reads a
   caret on `3.10` as `>=3.10,<4.0`, so 3.14 satisfies the project constraint.
2. **One dependency forbids it.** Same file, main group:
   `youtube-transcript-api = {version = "~1.2.2", python = ">=3.10,<3.14"}`.
3. **The lock makes the exclusion silent.** `poetry.lock:6284-6290` records
   `youtube-transcript-api` 1.2.4 with `markers = "python_version < \"3.14\""`. On a 3.14
   interpreter the lock installs and *omits* that package rather than failing. `poetry.lock`
   `[metadata]` also carries `python-versions = "^3.10"`.
4. **The repo's docs admit 3.14 as much as 3.10.** `README.md:22` ("Python 3.10+ and Poetry are
   required."), `SYSTEM_MAP.md:5` ("Python 3.10+ managed by Poetry"). There is no `.python-version`
   file in this repo.
5. **Nothing in the ecosystem answers it.** `flow/ecosystem-map/MAP.yml`'s `pipeline_documents:`
   entry (line 673) has no interpreter or runtime key, and neither does any other repo entry
   (`grep -n "python|runtime|venv|poetry" ecosystem-map/MAP.yml` returns only the droplet and
   `runtime_index` hits). `.claude/rules/ecosystem-map.md` lists `layer`, `status`, `path`,
   `remote`, `depends_on`, `feeds_into` as required and `spawns`, `risk_flags` as optional — there
   is no field that could carry the answer today.

## What the machine actually did (local reproduction, 2026-09-17)

- The project's only Poetry environment was `document-pipeline-jOBnYz_R-py3.10`, Python **3.10.14**,
  created 2026-08-30. Its `pyvenv.cfg` shows `home = /opt/homebrew/Caskroom/mambaforge/base/bin`,
  `include-system-site-packages = false`, so it is an isolated venv built *from* the Conda base
  interpreter. `AGENTS.md` tells agents not to use "the available Conda environments" for repo
  commands; the rule is not broken in letter, but the interpreter provenance is undocumented.
- At 14:56 a plain `poetry run` with Homebrew ahead on `PATH` auto-created
  `document-pipeline-jOBnYz_R-py3.14`: Poetry 2.4.1 picks the first satisfying `python3` on `PATH`,
  and `/opt/homebrew/.../python3.14` satisfies `^3.10`. That environment is empty of project
  packages (`ModuleNotFoundError: No module named 'pymupdf'`) and its creation failed part-way with
  a `virtualenv` pip-seed `FileNotFoundError` under the pipx Poetry venv, which left `poetry run`
  broken in this repo until the 3.10 environment was re-activated.
- Recovery, verified: `poetry env use /opt/homebrew/Caskroom/mambaforge/base/bin/python3.10` →
  `Using virtualenv: …jOBnYz_R-py3.10`; then `poetry run python -c "import pymupdf"` → `3.10.14`
  and `poetry run pytest -q` → **51 passed, 17 deselected**. This is local machine state (the
  activated-env marker in Poetry's config), not a repo change.
- **Claim boundary.** This is a reproduction on Scott's Mac only. We did not test whether a 3.14
  environment installs once the pip-seed problem is bypassed: the 3.14 exclusion is read from
  `poetry.lock` markers and `pyproject.toml`, not observed in an installed 3.14 environment. The
  pip-seed failure is an environment-creation defect and may be unrelated to the version question.

## Why the `<3.14` cap looks vestigial (context for the ruling, not the ruling)

- The live YouTube path is **yt-dlp**, which carries no `<3.14` cap:
  `doc_processing/loaders/youtube_loader.py:8` (`import yt_dlp`), and `batch_youtube_download.py`
  is yt-dlp based. `tests/test_youtube_loader.py` mocks `yt_dlp`.
- `youtube-transcript-api` is imported only by archived ad-hoc scripts:
  `scripts/archive/youtube_adhoc/extract_youtube_chinese_subtitles.py:9` and
  `scripts/archive/youtube_adhoc/nike_transcript.py:6`.
- So the pin that decides the interpreter question appears to protect archived code, not the live
  pipeline. **Not verified:** whether those archived scripts still need to be runnable.

## Why this is live rather than theoretical

- `_01_hubs/data_analysis/.python-version` contains `3.14.0`.
- `_02_platforms/studio_lab/pyproject.toml:6` says `requires-python = ">=3.10"`, and flow's
  `ecosystem-map/work_ledger.yml` (2026-09-04 entry) records consolidating Studio Lab's `.venv`
  "onto its verified Python 3.14 venv".
- Two sibling repos therefore run 3.14 while this one cannot install one of its declared
  dependencies there. An agent that reads "Python 3.10+" plus sibling practice reasonably guesses
  3.14 — which is exactly what happened here.

## The two questions for flow

1. **Ruling.** Is the intended interpreter for pipeline-documents 3.10 (dependency set unchanged)
   or 3.14 (relax or drop the archived `youtube-transcript-api` pin, and say whether the archived
   scripts stay runnable)? This repo will apply whichever ruling flow records; it will not decide a
   cross-repo runtime question on its own.
2. **Registration.** Will flow record a per-repo interpreter fact so agents stop inferring it from
   `PATH` — an optional `runtime:` key in `ecosystem-map/MAP.yml` (for example
   `runtime: {python: "3.10"}`), or a per-repo line in `ecosystem-map/TOOLING.md`? If yes, flow owns
   the schema/validator change; this repo will supply the verified value and re-check the lock.

## What this session did not do

- No change to `pyproject.toml`, `poetry.lock`, dependencies, or any repo file.
- No dispatch tag, no scheduled run, and no entry claiming flow's acceptance.