
# Inherited Content Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every live handed-down PoM 2 endocrinology and reproduction question tests something this year's slides teach, every lecture-note body section the slides do not teach carries an Inherited callout, and the weekly pipeline checks questions against the slides rather than the whole note.

**Architecture:** Each vault lecture note is a chart region written this year from the slides, then a `> [!check] Objectives` callout, then a body that is often an upper year's notes. The 2026-10-05 audit read questions against the whole note, so five HippoNotes questions (hippo-repro-Q77 to Q81) passed as `current` on body sections of `09 - Approach to Neonatal Care` that the 2025 deck never teaches. The fix has four parts. `tools/curriculum_audit.py` gains an optional `slides` field on a verdict row so the Off-curriculum flag can say the slides do not teach it, and the five move now. A new `tools/inherited_sections.py` finds each note's deck on disk (PDF or PPTX, read with pymupdf), splits the body into sections, and scores each section by the best single slide it covers: a section no slide lands in is `inherited`. A new `tools/slides_shortlist.py` reuses that to list, per live handed-down question, its deck, the earlier audit's evidence quote, and whether that quote's terms are on the slides, which gives an Opus reader a shortlist to judge against the deck and the chart region. A new `tools/mark_inherited.py` writes the Inherited callout under each inherited section, and the pom2-week skill and the audit brief adopt the slide check.

**Tech Stack:** Python 3 (stdlib plus `pymupdf`, which is installed under `python3` and opens both `.pdf` and `.pptx`), pytest for `tools/tests/`, the medwiki Obsidian vault at `/mnt/c/Users/nsims/medwiki`.

**Spec:** this plan is its own spec. Background: `docs/superpowers/plans/2026-10-06-refile-misfiled-questions.md` (the previous plan, same conventions), `build/curriculum_audit/AUDIT_BRIEF.md` (the read method), `skills/pom2-week/SKILL.md` Stage 1 ("Most pre-existing medwiki lecture content is an upper year's notes") and Stage 4b, `tools/curriculum_audit.py` module docstring. The neonatal deck is `/mnt/c/Users/nsims/Downloads/Approach to Neonatal Care Online Module Cheng Aug 2025.pdf` (48 pages, text layer present on 44, 1242 words). Facts measured 2026-10-06: endo.json 693 questions (211 live handed-down: 58 hipponotes, 88 workbook, 65 reviews), repro.json 523 (219 live handed-down: 88 hipponotes, 90 workbook, 41 reviews); every live handed-down question has a `review`; 77 lecture notes across the six weeks, all with an Objectives callout; 1430 verdict rows on disk, 211 qids with two rows (a `_w*` row and a `_refile*` row).

## Global Constraints

- **qids never change.** Progress and Anki cards join on them.
- Question banks are written only through `curriculum_audit.save_bank` (compact `json.dumps(qs, ensure_ascii=False)`, UTF-8, LF, no trailing newline). No script in this plan writes a bank any other way.
- Off-curriculum questions keep their `offCurriculum` and `restored` records exactly as they are. `apply` already skips a question carrying either; do not change that.
- Scope: `pom2/data/questions/endo.json` and `repro.json` only. Do not read or edit msk, neuro, psych, fom, pom1 or t2c banks.
- The vault is never committed by us; Obsidian Git syncs it. `tools/inherited_sections.py` and `tools/slides_shortlist.py` never write the vault. Only `tools/mark_inherited.py` (Task 4) and the existing `curriculum_audit.py mark-vault` and `vault_backup.py questions` do.
- `build/` is gitignored (`.gitignore` line 5), so verdict files, shortlists and JSON reports stay on disk and are never in a commit. `git add` only the paths each task names.
- Python style as in `tools/curriculum_audit.py`: module docstring with Purpose / Author (Noor Sims) / Date / Input / Output and usage lines, type hints, numpy-style docstrings on every function, `pathlib`, `argparse`. No hardcoded absolute path except the existing pattern `Path(os.environ.get("MEDWIKI", "/mnt/c/Users/nsims/medwiki"))`; the deck folders follow the same pattern with `POM2_DECKS`.
- Lecture names are the vault's spelling: the `.md` filename under `/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2/<block>/Week N/`. `against` in a verdict row is the stem with its number, e.g. `"09 - Approach to Neonatal Care"`.
- Prose in the skill, the brief, the README and every callout keeps the author's voice: plain sentences, no em dashes.
- Rebuild after any bank change with exactly `python3 tools/build_pages.py && python3 tools/build_index.py && python3 tools/build_hub.py` (no `review_lectures.py --derive`, which drifts other courses), then `python3 tools/vault_backup.py questions`.
- Commit after each task, on `main`. Do not push; the controller pushes.
- Run tests with `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests -q`. 39 tests pass before this plan starts.

## Review Focus

Inputs the plan implies but no test fully exercises, most likely to bite first:

1. **A deck whose text layer is empty (image-only slides)** must be reported as `no usable text` and every section of its note given `no-deck`, never `inherited`. Test `test_empty_text_layer_is_no_usable_text` in Task 2; the constant is `DECK_MIN_TERMS`.
2. **A note with no body (chart only)** scores nothing and is printed as `no body`, skipped by Task 4's marker and by Task 3's shortlist. Test `test_chart_only_note_is_skipped` in Task 2.
3. **A question whose lecture has no deck on disk** stays `current` with `NO-DECK` in `note`; the shortlist prints it under its own heading and Task 3 Step 6 lists those lectures for the user. Test `test_no_deck_question_is_current_no_deck` in Task 3.
4. **The Inherited callout is idempotent**: running `mark_inherited.py` twice writes nothing the second time and a section whose next line already starts with `> [!warning] Inherited` is skipped. Test `test_marking_twice_changes_nothing` in Task 4.
5. **`apply` of the Task 1 file twice changes nothing**: the second run prints `already moved 5` and the bank bytes are identical. Verified by command in Task 1 Step 6 and by `test_not_covered_with_slides_is_idempotent` in Task 1.
6. **A wrong deck match** is worse than no deck, because it scores every section inherited. `inherited_sections.py` prints the deck it used per note; Task 2 Step 5 makes the implementer confirm each title slide before the thresholds are trusted.

---

### Task 1: Move hippo-repro-Q77 to Q81 off-curriculum against the neonatal slides

**Files:**
- Modify: `tools/curriculum_audit.py` (`off_sentence`, `off_flag_html`, `apply_rows`, `mark_vault`, module docstring)
- Modify: `tools/tests/test_curriculum_audit.py` (two tests appended)
- Create: `build/curriculum_audit/repro_neonatal_inherited.json` (gitignored, stays on disk)
- Modify via `apply` only: `pom2/data/questions/repro.json`
- Modify (generated): `pom2/*.html`, `index.html`, `pom2/data/notes/*.json` if the build touches them
- Modify (vault, not committed): `/mnt/c/Users/nsims/medwiki/00 - Practice Questions/HippoNotes - Reproduction.md` via `vault_backup.py questions`

**Interfaces:**
- Consumes: `apply_rows`, `MOVING_VERDICTS = ("outdated", "not-covered", "retired")`, `off_sentence(reason, against, evidence, bold)`, `off_flag_html(row)`, `save_bank`, `report`.
- Produces: a verdict row may carry an optional `"slides": "<deck filename>"`; when it does, the Off-curriculum flag reads "This year's lecture slides do not teach this. Checked against the slides of **<against>** (<slides>), which cover: “<evidence>”." and `offCurriculum` gains `"slides"`. Rows without `slides` render exactly as before.

- [ ] **Step 1: Write the failing tests**

Append to `tools/tests/test_curriculum_audit.py`:

```python


def test_not_covered_with_slides_names_the_deck(repo):
    row = {"qid": "hippo-repro-Q47", "verdict": "not-covered", "week": 6,
           "against": "09 - Approach to Neonatal Care",
           "slides": "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf",
           "evidence": "Apgar, newborn exam, growth, thermal, hypoglycemia, bilirubin, global",
           "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    q = bank(repo, "repro")[0]
    assert q["family"] == "offcurriculum"
    assert q["week"] == 6 and q["weekLabel"] == "Week 6"
    assert q["offCurriculum"] == {"reason": "not-covered", "from": "hipponotes",
                                  "against": "09 - Approach to Neonatal Care",
                                  "checked": "2026-10-06",
                                  "slides": "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf"}
    flag = q["flags"][0]["html"]
    assert flag.startswith("<p>This year's lecture slides do not teach this.")
    assert "Cheng Aug 2025.pdf" in flag and "which cover:" in flag
    assert q["qid"] == "hippo-repro-Q47"


def test_not_covered_with_slides_is_idempotent(repo, capsys):
    row = {"qid": "hippo-repro-Q47", "verdict": "not-covered", "week": 6,
           "against": "09 - Approach to Neonatal Care", "slides": "deck.pdf",
           "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    before = (repo / "pom2/data/questions/repro.json").read_bytes()
    ca.apply_rows([row], checked="2026-10-07")
    assert (repo / "pom2/data/questions/repro.json").read_bytes() == before
    assert "already moved   1" in capsys.readouterr().out


def test_not_covered_without_slides_renders_as_before(repo):
    row = {"qid": "hippo-repro-Q47", "verdict": "not-covered", "week": 6,
           "against": "09 - Approach to Neonatal Care", "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    q = bank(repo, "repro")[0]
    assert "slides" not in q["offCurriculum"]
    assert q["flags"][0]["html"] == (
        "<p>This year's lectures do not teach this. Checked against "
        "<strong>09 - Approach to Neonatal Care</strong>, the nearest lecture, "
        "which does not mention it.</p>")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests/test_curriculum_audit.py -q 2>&1 | tail -8`
Expected: the first test FAILS (flag starts with "This year's lectures do not teach this." and `offCurriculum` has no `slides`); the other two PASS already (they pin existing behaviour).

- [ ] **Step 3: Implement**

In `tools/curriculum_audit.py`:

(a) Module docstring: after the paragraph beginning "A moved question keeps its qid", add:

```
A row may carry ``"slides": "<deck filename>"`` when the check was made against
the lecture's slide deck rather than the whole note. The Off-curriculum flag
then says the slides do not teach it and names the deck, and ``offCurriculum``
keeps the deck name. Rows without ``slides`` render as before.
```

(b) Replace `off_sentence` with:

```python
def off_sentence(reason: str, against: str, evidence: str, bold: str, slides: str = "") -> str:
    """The plain sentence that says why a question is off-curriculum.

    Parameters
    ----------
    reason : str
        ``"outdated"``, ``"not-covered"`` or ``"retired"``.
    against : str
        The lecture note it was checked against.
    evidence : str
        A quote from that note or deck, possibly empty. Already escaped for
        the target format by the caller.
    bold : str
        A format string with one ``%s`` that emphasises the lecture name,
        e.g. ``"<strong>%s</strong>"`` or ``"**%s**"``.
    slides : str
        The deck filename when the check was against the slides, else empty.
        Already escaped by the caller.

    Returns
    -------
    str
        One or two sentences, no em dashes of its own.
    """
    lecture = bold % against
    if reason == "retired":
        lead = ("Its own source retired this question, so it is kept here rather than in "
                "the set it came from.")
        tail = f" Nearest lecture: {lecture}." if against else ""
        return lead + tail
    if slides:
        where = f"the slides of {lecture} ({slides})"
        if reason == "outdated":
            lead = ("This year's lecture teaches this differently, so the key here may not "
                    "match what you are examined on.")
            tail = (f" Checked against {where}, which say: “{evidence}”." if evidence
                    else f" Checked against {where}.")
        else:
            lead = "This year's lecture slides do not teach this."
            tail = (f" Checked against {where}, which cover: “{evidence}”." if evidence
                    else f" Checked against {where}, which do not mention it.")
        return lead + tail
    if reason == "outdated":
        lead = ("This year's lecture teaches this differently, so the key here may not "
                "match what you are examined on.")
        tail = f" Checked against {lecture}, which says: “{evidence}”." if evidence else \
            f" Checked against {lecture}."
    else:
        lead = "This year's lectures do not teach this."
        tail = (f" Checked against {lecture}, the nearest lecture, which says: "
                f"“{evidence}”." if evidence else
                f" Checked against {lecture}, the nearest lecture, which does not mention it.")
    return lead + tail
```

(c) In `off_flag_html`, change the call to:

```python
    text = off_sentence(row["verdict"], html.escape(row["against"]),
                        html.escape(row.get("evidence") or "").strip(), "<strong>%s</strong>",
                        html.escape(row.get("slides") or ""))
```

(d) In `apply_rows`, inside `if row["verdict"] in MOVING_VERDICTS:`, after the line that sets `q["offCurriculum"] = {...}`, add:

```python
            if row.get("slides"):
                q["offCurriculum"]["slides"] = row["slides"]
```

(e) In `mark_vault`, change the `sentence = off_sentence(...)` call to:

```python
            sentence = off_sentence(row["verdict"], row["against"],
                                    (row.get("evidence") or "").strip(), "**%s**",
                                    row.get("slides") or "")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests -q 2>&1 | tail -3`
Expected: 42 passed.

- [ ] **Step 5: Write the verdict file**

Create `build/curriculum_audit/repro_neonatal_inherited.json` with exactly this content (one row per question; `evidence` is what the deck does cover, so the flag reads "which cover: ..."):

```json
[
 {"qid": "hippo-repro-Q77", "verdict": "not-covered", "against": "09 - Approach to Neonatal Care", "week": 6,
  "slides": "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf",
  "evidence": "Apgar score, full newborn assessment, growth, thermal regulation, hypoglycemia, bilirubin, global perspectives",
  "note": "Tests the Neonatal Resuscitation Program's primary intervention; the note's Neonatal Resuscitation section is inherited and the 2025 deck has no resuscitation slide. She confirmed it was not taught."},
 {"qid": "hippo-repro-Q78", "verdict": "not-covered", "against": "09 - Approach to Neonatal Care", "week": 6,
  "slides": "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf",
  "evidence": "Apgar score, full newborn assessment, growth, thermal regulation, hypoglycemia, bilirubin, global perspectives",
  "note": "Tests cardiovascular transition at birth; the note's Newborn Transition section is inherited and the deck has no transition slide. She confirmed it was not taught."},
 {"qid": "hippo-repro-Q79", "verdict": "not-covered", "against": "09 - Approach to Neonatal Care", "week": 6,
  "slides": "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf",
  "evidence": "Apgar score, full newborn assessment, growth, thermal regulation, hypoglycemia, bilirubin, global perspectives",
  "note": "Tests TTN, RDS and meconium aspiration; the note's Respiratory Problems section is inherited and the deck has no respiratory slide. She confirmed it was not taught."},
 {"qid": "hippo-repro-Q80", "verdict": "not-covered", "against": "09 - Approach to Neonatal Care", "week": 6,
  "slides": "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf",
  "evidence": "Apgar score, full newborn assessment, growth, thermal regulation, hypoglycemia, bilirubin, global perspectives",
  "note": "Tests neonatal sepsis risk factors; the note's Neonatal Sepsis section is a transclusion of an inherited condition note and the deck only names sepsis as a cause of hypoglycemia. She confirmed it was not taught."},
 {"qid": "hippo-repro-Q81", "verdict": "not-covered", "against": "09 - Approach to Neonatal Care", "week": 6,
  "slides": "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf",
  "evidence": "Apgar score, full newborn assessment, growth, thermal regulation, hypoglycemia, bilirubin, global perspectives",
  "note": "Tests neonatal sepsis management; the note's Neonatal Sepsis section is a transclusion of an inherited condition note and the deck has no sepsis management slide. She confirmed it was not taught."}
]
```

- [ ] **Step 6: Apply, verify, apply again**

```bash
cd /home/nsims/repos/preclerkship
python3 tools/curriculum_audit.py apply --checked 2026-10-06 build/curriculum_audit/repro_neonatal_inherited.json
python3 tools/curriculum_audit.py report 2>&1 | grep -E "^== repro|hipponotes|offcurriculum|not-covered"
md5sum pom2/data/questions/repro.json
python3 tools/curriculum_audit.py apply --checked 2026-10-06 build/curriculum_audit/repro_neonatal_inherited.json
md5sum pom2/data/questions/repro.json
python3 - <<'EOF'
import json
for q in json.load(open('pom2/data/questions/repro.json')):
    if q['qid'] in ('hippo-repro-Q77','hippo-repro-Q78','hippo-repro-Q79','hippo-repro-Q80','hippo-repro-Q81'):
        print(q['qid'], q['family'], q['week'], q['weekLabel'], q['offCurriculum'].get('slides'))
        print('  ', q['flags'][0]['html'][:160])
EOF
```
Expected: first `apply` prints `repro  moved   5 ...`; `report` shows `hipponotes 83`, `offcurriculum 49`, and the `off-curriculum, not-covered` line includes all five qids; the second `apply` prints `already moved   5` and the two md5 sums are identical; each flag starts with `<p>This year's lecture slides do not teach this. Checked against the slides of <strong>09 - Approach to Neonatal Care</strong> (Approach to Neonatal Care Online Module Cheng Aug 2025.pdf), which cover:`.

- [ ] **Step 7: Rebuild and back up**

```bash
cd /home/nsims/repos/preclerkship
python3 tools/build_pages.py && python3 tools/build_index.py && python3 tools/build_hub.py
python3 tools/vault_backup.py questions --dry-run
python3 tools/vault_backup.py questions
grep -n "hippo-repro-Q77\|Off-curriculum" "/mnt/c/Users/nsims/medwiki/00 - Practice Questions/HippoNotes - Reproduction.md" | head -8
git status --short
```
Expected: the dry run lists the pom2 HippoNotes and Reviews notes; the grep shows Q77 under an `Off-curriculum` warning; `git status` shows only `tools/curriculum_audit.py`, `tools/tests/test_curriculum_audit.py`, `pom2/data/questions/repro.json` and generated pages (`pom2/*.html`, `index.html`, possibly `pom2/data/notes/*.json`). Nothing under `build/` appears (it is ignored).

- [ ] **Step 8: Commit**

```bash
cd /home/nsims/repos/preclerkship
git add tools/curriculum_audit.py tools/tests/test_curriculum_audit.py pom2/data/questions/repro.json pom2 index.html
git commit -m "Repro: move hippo-repro-Q77 to Q81 off-curriculum, the neonatal slides do not teach them; curriculum_audit rows may name the deck"
```

---

### Task 2: `tools/inherited_sections.py` finds the note sections the slides do not teach

**Files:**
- Create: `tools/inherited_sections.py`
- Create: `tools/tests/test_inherited_sections.py`
- Modify: `tools/README.md` (a short section after "Keeping the banks to this year's lectures")

**Interfaces:**
- Consumes: the vault at `MEDWIKI` (default `/mnt/c/Users/nsims/medwiki`), decks under `POM2_DECKS` (default `/mnt/c/Users/nsims/Downloads:/mnt/c/Users/nsims/OneDrive/Documents`, colon-separated) plus each note's own week folder (three weeks keep a `.pdf` beside the `.md`), `pymupdf`.
- Produces, for Tasks 3 and 4: `lecture_notes(block) -> list[Path]`, `split_note(text) -> NoteParts`, `sections(lines, start, embed) -> list[Section]`, `deck_files() -> list[Path]`, `decks_for(note, files) -> list[Path]`, `deck_pages(path) -> list[str]`, `terms(text) -> set[str]`, `audit_note(note, files, index) -> NoteResult`, the constants `SLIDES_AT`, `SLIDE_MIN_TERMS`, `SECTION_MIN_TERMS`, `DECK_MIN_TERMS`, `INHERITED_MARK = "> [!warning] Inherited"`. CLI: `python3 tools/inherited_sections.py --block {endo,repro} [--note <stem>] [--json <path>]`. It never writes the vault; `--json` may only write under `build/`.
- Verdicts per section: `slides` (score >= `SLIDES_AT`), `inherited` (score below), `no-deck` (no deck found, deck unreadable, or no usable text). A thin section (fewer than `SECTION_MIN_TERMS` distinct terms) takes its parent's verdict and prints `-` for its score.

**Scoring, and why.** A slide deck is terse (the neonatal deck is 1242 words across 48 slides, 303 distinct terms) while an inherited section runs to 600 words, so "fraction of the section's terms found in the deck" does not separate them: measured on the neonatal note on 2026-10-06 it gave Hypoglycemia 0.25 and Bilirubin 0.24 (taught) against Neonatal Sepsis 0.21 and Resuscitation 0.17 (inherited). What does separate them is the reverse direction per slide: for each slide with at least `SLIDE_MIN_TERMS` distinct terms, the fraction of that slide's terms that the section contains, and the section's score is the best slide. A taught section is the home of at least one slide; an inherited section is the home of none. Measured with a digits-dropping prototype: Resuscitation 0.17, Pulmonary Adaptation 0.17, Cardiovascular Adaptation 0.11, Respiratory Problems 0.25, Neonatal Sepsis 0.44 (an agenda slide), Newborn Vital Signs 0.17, versus Apgar 0.64, Full Newborn Assessment 1.00, Hypothermia 0.92, Hypoglycemia 1.00, Bilirubin & Jaundice 1.00, Global Perspectives with its Helping Babies Survive child 1.00. `SLIDES_AT = 0.5` sits in the gap. Step 5 re-measures with the real tokenizer before the constant is final.

- [ ] **Step 1: Write the failing tests**

Create `tools/tests/test_inherited_sections.py`:

```python
# -*- coding: utf-8 -*-
"""
Purpose: pin how inherited_sections.py splits a note, matches a deck and scores a section
Author: Noor Sims
Date: 2026-10-06
Input: a synthetic vault note and synthetic slide texts built in tmp_path (no real PDF)
Output: pytest results
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inherited_sections as isx  # noqa: E402

NOTE = """---
type: LectureNote
---
# Overview chart: <u>Approach to Neonatal Care</u>

**Every newborn is kept pink, warm and sweet.** Glucose 2.6 or more after the first feed.

---

> [!check] Objectives
> 1. Describe the Apgar score.
> 2. Model bilirubin physiology.

# Neonatal Resuscitation
Ventilation is the primary goal of neonatal resuscitation, unlike adult compressions for perfusion.
Positive pressure ventilation, intubation and epinephrine follow the resuscitation algorithm.

# Apgar Score
The Apgar score tells us how well the baby transitioned at birth, at 1 minute and 5 minutes.
Appearance, pulse, grimace, activity, respiration; 7 or more is normal, 4 to 6 is low.

# Extra Care for the Neonate
Babies need extra care.
#### Neonatal Sepsis
![[neonatal sepsis]]
#### Hypoglycemia
Screen infants of diabetic mothers, large for gestational age, small for gestational age and preterm.
Jittery, irritable, lethargic, poor feeding; symptomatic hypoglycemia means intravenous dextrose.
#### Thin
Short.
"""

SEPSIS = """Risk factors: chorioamnionitis, maternal group B streptococcus, prolonged rupture of membranes.
Blood culture, lumbar puncture, empiric ampicillin and gentamicin after the culture is drawn."""

SLIDES = [
    "Approach to Neonatal Care\nAnita Cheng",
    "Apgar Score\nappearance pulse grimace activity respiration\n1 minute 5 minutes\n7 normal 4-6 low",
    "Hypoglycemia Screening\ninfants diabetic mothers\nlarge gestational age\nsmall gestational age\npreterm\njittery irritable lethargic poor feeding",
    "Comprehension question 1",
]


@pytest.fixture
def vault(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    week = root / "01 - Lectures" / "99 - PoM 2" / "02 - Repro" / "Week 6"
    week.mkdir(parents=True)
    (week / "09 - Approach to Neonatal Care.md").write_text(NOTE, encoding="utf-8")
    (week / "Week 6.md").write_text("---\n---\n", encoding="utf-8")
    cond = root / "00 - Medications" / "00 - Conditions" / "Pediatrics"
    cond.mkdir(parents=True)
    (cond / "neonatal sepsis.md").write_text(SEPSIS, encoding="utf-8")
    decks = tmp_path / "decks"
    decks.mkdir()
    for name in ("Approach to Neonatal Care Online Module Cheng Aug 2025.pdf",
                 "2026 Applicant Information - Drug and Medical Device Small Business.pdf",
                 "Approach to the Small Fetus slides.pdf"):
        (decks / name).write_bytes(b"")
    monkeypatch.setattr(isx, "VAULT", root)
    monkeypatch.setattr(isx, "LECTURE_NOTES", root / "01 - Lectures" / "99 - PoM 2")
    monkeypatch.setattr(isx, "DECK_DIRS", [decks])
    monkeypatch.setattr(isx, "DECKS", {})
    monkeypatch.setattr(isx, "deck_pages", lambda path: list(SLIDES))
    return root


def note_path(root):
    return root / "01 - Lectures/99 - PoM 2/02 - Repro/Week 6/09 - Approach to Neonatal Care.md"


def test_split_note_separates_chart_and_body():
    parts = isx.split_note(NOTE)
    assert "pink, warm and sweet" in parts.chart
    assert "Objectives" not in "\n".join(parts.body)
    assert parts.body[0].strip() == ""  or parts.body[0].startswith("# Neonatal")
    assert NOTE.split("\n")[parts.body_start:][0] == parts.body[0]


def test_sections_two_levels_and_children_roll_up(vault):
    parts = isx.split_note(NOTE)
    index = isx.embed_index()
    secs = isx.sections(parts.body, parts.body_start, lambda n: isx.embed_text(n, index))
    tops = [s.heading for s in secs]
    assert tops == ["Neonatal Resuscitation", "Apgar Score", "Extra Care for the Neonate"]
    extra = secs[2]
    assert [c.heading for c in extra.children] == ["Neonatal Sepsis", "Hypoglycemia", "Thin"]
    assert "chorioamnionitis" in extra.children[0].text          # transclusion followed
    assert "chorioamnionitis" in extra.text                       # parent holds its children
    assert NOTE.split("\n")[extra.children[1].line] == "#### Hypoglycemia"


def test_slide_coverage_marks_taught_and_inherited(vault):
    result = isx.audit_note(note_path(vault), isx.deck_files(), isx.embed_index())
    by = {s.heading: s for s in result.flat()}
    assert result.decks[0].name == "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf"
    assert by["Apgar Score"].verdict == "slides" and by["Apgar Score"].score >= isx.SLIDES_AT
    assert by["Hypoglycemia"].verdict == "slides"
    assert by["Neonatal Resuscitation"].verdict == "inherited"
    assert by["Neonatal Sepsis"].verdict == "inherited"
    assert by["Extra Care for the Neonate"].verdict == "slides"   # the parent holds Hypoglycemia


def test_thin_child_takes_parent_verdict(vault):
    result = isx.audit_note(note_path(vault), isx.deck_files(), isx.embed_index())
    by = {s.heading: s for s in result.flat()}
    assert by["Thin"].score is None
    assert by["Thin"].verdict == by["Extra Care for the Neonate"].verdict


def test_empty_text_layer_is_no_usable_text(vault, monkeypatch):
    monkeypatch.setattr(isx, "deck_pages", lambda path: ["", " ", ""])
    result = isx.audit_note(note_path(vault), isx.deck_files(), isx.embed_index())
    assert result.deck_label.endswith("(no usable text)")
    assert {s.verdict for s in result.flat()} == {"no-deck"}


def test_no_deck_found(vault):
    (vault.parent / "decks" / "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf").unlink()
    result = isx.audit_note(note_path(vault), isx.deck_files(), isx.embed_index())
    assert result.deck_label == "no deck found"
    assert {s.verdict for s in result.flat()} == {"no-deck"}


def test_chart_only_note_is_skipped(vault):
    p = note_path(vault)
    p.write_text(NOTE.split("\n---\n")[0] + "\n", encoding="utf-8")
    result = isx.audit_note(p, isx.deck_files(), isx.embed_index())
    assert result.sections == [] and result.skipped == "no body"


def test_deck_match_needs_two_title_words(vault):
    files = isx.deck_files()
    fetus = vault / "01 - Lectures/99 - PoM 2/02 - Repro/Week 6/02 - Approach to the Small Fetus.md"
    assert [p.name for p in isx.decks_for(fetus, files)] == ["Approach to the Small Fetus slides.pdf"]


def test_override_wins_and_empty_override_means_no_deck(vault, monkeypatch):
    files = isx.deck_files()
    monkeypatch.setattr(isx, "DECKS", {"09 - Approach to Neonatal Care": []})
    assert isx.decks_for(note_path(vault), files) == []
    monkeypatch.setattr(isx, "DECKS", {"09 - Approach to Neonatal Care":
                                       ["Approach to the Small Fetus slides.pdf"]})
    assert [p.name for p in isx.decks_for(note_path(vault), files)] == ["Approach to the Small Fetus slides.pdf"]


def test_lecture_notes_skips_week_summary(vault):
    assert [p.name for p in isx.lecture_notes("repro")] == ["09 - Approach to Neonatal Care.md"]


def test_json_report_round_trips(vault, tmp_path):
    out = tmp_path / "build" / "repro.json"
    results = [isx.audit_note(note_path(vault), isx.deck_files(), isx.embed_index())]
    isx.write_json(results, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data[0]["note"] == "09 - Approach to Neonatal Care"
    assert {s["verdict"] for s in data[0]["sections"]} == {"slides", "inherited"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests/test_inherited_sections.py -q 2>&1 | tail -5`
Expected: collection error, `ModuleNotFoundError: No module named 'inherited_sections'`.

- [ ] **Step 3: Implement**

Create `tools/inherited_sections.py`:

```python
# -*- coding: utf-8 -*-
"""Find the lecture-note sections this year's slides do not teach.

Purpose: a PoM 2 lecture note is a chart written this year from the slides,
         an Objectives callout, and a body that is often an upper year's notes.
         This tool finds each note's slide deck on disk, reads it with pymupdf,
         splits the body into sections and scores each section by the best
         single slide it contains. A section no slide lands in is `inherited`.
Author:  Noor Sims
Date:    2026-10-06
Input:   the block's lecture notes under ``$MEDWIKI/01 - Lectures/99 - PoM 2``
         (default the author's vault), and decks (.pdf or .pptx) in the
         colon-separated folders of ``$POM2_DECKS`` (default Downloads and
         OneDrive/Documents) plus the note's own week folder
Output:  a table per note on stdout: the deck used, then one line per section
         with heading, word count, score and verdict; ``--json`` writes the
         same under build/. The vault is never written.

    python tools/inherited_sections.py --block repro
    python tools/inherited_sections.py --block endo --note "09 - Introduction to Obesity"
    python tools/inherited_sections.py --block repro --json build/inherited_sections/repro.json

Verdicts: ``slides`` when some slide with at least SLIDE_MIN_TERMS distinct
terms has at least SLIDES_AT of them inside the section; ``inherited`` when no
slide does; ``no-deck`` when no deck was found, it could not be opened, or its
text layer holds fewer than DECK_MIN_TERMS distinct terms (image-only slides).
A thin section (under SECTION_MIN_TERMS distinct terms) takes its parent's
verdict. Sections are the body's top heading level and the next level present
(the neonatal note uses ``#`` and ``####``); deeper headings belong to their
parent. ``![[note]]`` and ``![[note#Heading]]`` transclusions are followed.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("MEDWIKI", "/mnt/c/Users/nsims/medwiki"))
LECTURE_NOTES = VAULT / "01 - Lectures" / "99 - PoM 2"
DECK_DIRS = [Path(p) for p in os.environ.get(
    "POM2_DECKS", "/mnt/c/Users/nsims/Downloads:/mnt/c/Users/nsims/OneDrive/Documents").split(":")]
DECK_SUFFIXES = (".pdf", ".pptx")

# block slug -> (vault folder, course weeks)
BLOCKS = {"endo": ("01 - Endocrinology", (1, 2, 3)), "repro": ("02 - Repro", (4, 5, 6))}

# Calibrated on 09 - Approach to Neonatal Care against the 2025 Cheng deck on
# 2026-10-06: its inherited sections (Neonatal Resuscitation, Newborn
# Transition, Respiratory Problems, Neonatal Sepsis) scored 0.11 to 0.44 and
# its taught sections (Apgar, Full Newborn Assessment, Hypothermia,
# Hypoglycemia, Bilirubin, Global Perspectives) scored 0.64 to 1.00.
SLIDES_AT = 0.5          # a section is taught when some slide is at least half inside it
SLIDE_MIN_TERMS = 6      # a slide with fewer distinct terms (title-only, image-only) does not count
SECTION_MIN_TERMS = 10   # a section with fewer distinct terms is thin and takes its parent's verdict
DECK_MIN_TERMS = 50      # a deck with fewer distinct terms has no usable text layer

INHERITED_MARK = "> [!warning] Inherited"
OBJECTIVES_MARK = "> [!check]"

STOPWORDS = set("""
the a an and or of to in on for with at by from as is are was were be been being this
that these those it its into than then so if not no yes but also can may might should
would will which who whom whose what when where why how all any each every both few
more most other some such only own same too very just about above after again against
between during before below under over out up down off once here there per via etc vs
have has had does did done do make made used using use get take given give less least
high low higher lower normal common usually often typically include including includes
due based following first second third one two three four five within without while
because however therefore also multi column tip note warning check summary condition
""".split())

TOKEN_RE = re.compile(r"[a-z][a-z0-9]{3,}|\d[\d.,]{2,}")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
IMAGE_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|canvas|pdf)$", re.I)

# Note stem -> deck filenames (looked up in DECK_DIRS and the note's week
# folder). An entry wins over the loose title match; an empty list says there
# is no deck on disk and stops the matcher guessing. Filled on 2026-10-06 from
# the folder listings and confirmed slide by slide in the plan's Task 2 Step 5.
DECKS: dict[str, list[str]] = {
    "01 - Intro to Diabetes": [],
    "02 - Diagnosis and Management of Type 1 Diabetes": ["Diabetes Pathophysiology T1DM.pdf"],
    "03 - Pharmacology of Insulin": [],
    "05 - Type 2 Diabetes Mellitus - Diagnosis & Epidemiology": ["Diabetes Pathophysiology T2DM Final.pdf", "Hashmi  T2DMellitus.pdf"],
    "07 - Pharmacology of Glucose-Lowering Drugs": ["UME P2 Endocrine Pharmacology (Pharmacology of T2DM).pdf", "pharmacology_of_t2dm_2026_menti_post_after_.pdf"],
    "10 - Prevention of Complications of Diabetes": ["PreventionofDMComplications Hashmi 2024.pdf"],
    "12 - Prevention of Type 2 Diabetes": ["Diabetes Prevention Slides 2021.pdf"],
    "13 - Antihyperglycemic Drug Choices for T2DM (CBL)": ["antihyperglycemics_2026_students_blank_final_before.pptx"],
    "01 - Thyroid and Parathyroid Gland Physiology": ["Thyroid Part 1 2023.pdf", "Thyroid Part 2 2023.pdf", "Parathyroid Part1 2023.pdf", "Parathyroid Part2 2023.pdf"],
    "03 - Clinical Presentation and Evaluation of Hypothyroidism and Thyrotoxicosis": ["clinical_approach_to_hypothyroidism_and_thyrotoxicosis.pdf", "Morrison_ThyroidDysfunction_slides.pdf"],
    "04 - Clinical Presentation and Evaluation of Hyperparathyroidism and Hypoparathyroidism": ["Hyper Hypo Parathyroidism and Calcemia Slides.pdf"],
    "05 - Pathology of Thyroid Masses": ["Wehrli_ThyroidGlandPathology_slides_nv.pdf", "Clinical Presentation Investigation of Thyroid Masses - Morrison Weir.pdf", "thyroid_nodules_live_sep_2025_p2_post_after_.pdf"],
    "06 - Clinical Presentation and Evaluation of Osteoporosis": ["Osteoporosis clin presentation and invest 2024.pptx", "Osteoporosis treatment 2024.pdf", "Osteoporosis epi and tx gap.pdf"],
    "08 - Embryology & Histology": ["Farias_Embryogenesis_slides.pdf", "Normal Histology of the gyn tract_2020.pdf"],
    "09 - Hypothalamic-Pituitary-Gonadal Axis": ["Watson_HPG_Slides.pdf"],
    "01 - Clinical Presentation and Evaluation of Adrenal Gland Disease": ["Adrenal Insufficiency Van Uum 2024.pdf", "Adrenal Overproduction Adrenaline Incidentaloma VanUum 2024.pdf", "Adrenal Overproduction Cortisol VanUum2024.pdf", "Adrenal Overproduction Intro and Aldosterone Van Uum 2024.pdf"],
    "02 - Clinical Presentation and Evaluation of Pituitary Gland Disease": ["Pituitary Hormone Insufficiency 2024.pdf", "Pituitary Overproduction Cushing 2024.pdf", "Pituitary Overproduction Growth Hormone 2024.pdf", "Pituitary Overproduction Prolactin 2024.pdf"],
    "03 - Physiologic Changes that Lead to Puberty": ["Watson_Puberty_Slides.pdf", "Lovett_Puberty_MenstruationSlides.pdf"],
    "04 - Disorders of Puberty": ["P2_Gallego_AbnormalitiesOfPuberty.pdf"],
    "05 - Disorders of Growth": ["P2_Gallego_NormalGrowthShortStature.pdf"],
    "06 - Anatomy of the Female Pelvis, Perineum, & Sexual Function": ["06 - Anatomy of the Female Pelvis, Perineum, & Sexual Function.pdf", "AnatomyPelvisSlides2021.pdf"],
    "07 - Development of the Female Reproductive System": ["Development of the Female Reproductive Tract PDF Slides.pdf"],
    "09 - Disorders of Sexual Differentiation": ["Stein DSD-CAH 2024A.pdf", "Stein DSD-CAH 2024B.pdf"],
    "10 - Polyendocrine Metabolic Ovarian Syndrome (PMOS)": [],
    "03 - Contraception and Drugs Used in Gynecology": ["Contraception 2026.pdf", "Drugs used in gynecology slides.pdf"],
    "08 - Approach to Sexually Transmitted Infections": ["STI2021Slides.pdf"],
    "09 - Early Pregnancy Complications - Spontaneous Abortion and Ectopic": ["P2_Sovran_Spontaenous_Abortion.pdf", "ECTOPIC PREGNANCY Year 2.pdf", "p2_kirby_ectopicpregnancy_slides_post_after_.pptx"],
    "15 - Abnormal Uterine Bleeding": ["P2_Arntfield_AUB_Slides.pdf", "Weir_AUBPain_slides.pdf"],
    "16 - Genetic Screening for Pregnancy in Canada": ["saleh_prenatalgeneticsscreening_Asynchronous.pdf", "Repro Genetics Noninvasive Slides.pdf", "Repro-invasive testing 2023.pdf"],
    "17 - Early Pregnancy Counselling": [],
    "In-Class - Amenorrhea": [],
    "02 - Dilation and Curettage": [],
    "04 - Approach to and Pathology of a Pelvic Mass": ["Armstrong_OvarianNeoplasms_slides.pdf"],
    "09 - Pathology of 1st Trimester Bleeding": ["Pathology of Early Pregnancy_EG_notes.pdf"],
    "11 - Approach to First Trimester Bleeding & Ultrasound": ["P2_Schmidt_FirstTrimester_slides.pdf", "P2_Vilos_2021_Ultrasound.pdf"],
    "12 - Hypertension in Pregnancy": ["P2_Schmidt_Hypertensive Disorders in Pregnancy_slides.pdf"],
    "13 - Second Trimester Ultrasound": ["T2 Ultrasound Presentation_2021.pdf"],
    "15 - Care for Pregnancy in the First Trimester": ["common_concerns_in_pregnancy_post_before.pdf"],
    "17 - Physiologic Changes in Pregnancy": [],
    "02 - Approach to the Small Fetus": ["P2_Schmidt_IUGR_slides.pdf"],
    "04 - Process of Labour and Birth": ["P2Sovran_LabourSlides.pdf"],
    "05 - Abnormal Labour": ["Overview of Abnormal Labour and Birth Module.pdf", "AbnormalLabourOperativeDeliveriesandTOLAC.pdf", "AbnormalLabourPostpartumHemorrhage.pdf", "Induction and Augmentation.pdf"],
    "06 - Hemorrhagic Shock": ["P2_Sovran_HShock.pdf"],
    "08 - Postpartum Care": ["POSTPARTUMCARE LS Y2 V2.pdf"],
}

# words in a title or filename that say nothing about the lecture
TITLE_NOISE = set("""
approach clinical presentation evaluation introduction intro overview slides slide notes
module lecture lectures pdf year p2 ume y2 post before after final draft student students
material part online version revised blank cases case dssg cbl meds
""".split())


@dataclass
class Section:
    """One heading of a note body with the text under it.

    Attributes
    ----------
    level : int
        Heading depth, 1 for ``#``.
    heading : str
        Heading text.
    line : int
        0-based index of the heading line in the whole note.
    text : str
        Own text plus every child's, transclusions resolved.
    words : int
        Whitespace word count of ``text``.
    score : float or None
        Best slide coverage, None when thin or no deck.
    verdict : str
        ``slides``, ``inherited`` or ``no-deck``.
    children : list of Section
        Sections at the next heading level under this one.
    """
    level: int
    heading: str
    line: int
    text: str = ""
    words: int = 0
    score: float | None = None
    verdict: str = ""
    children: list["Section"] = field(default_factory=list)


@dataclass
class NoteParts:
    """A note split into its chart region and its body.

    Attributes
    ----------
    chart : str
        Text between the frontmatter and the first ``---`` after it.
    body : list of str
        Lines after that ``---`` and after the Objectives callout.
    body_start : int
        0-based index in the note of ``body[0]``.
    """
    chart: str
    body: list[str]
    body_start: int


@dataclass
class NoteResult:
    """What the tool found for one note."""
    note: Path
    decks: list[Path]
    deck_label: str
    sections: list[Section]
    skipped: str = ""

    def flat(self) -> list[Section]:
        """Every section, parents before their children, in note order."""
        out = []
        for s in self.sections:
            out.append(s)
            out.extend(s.children)
        return out


def clean_markup(text: str) -> str:
    """Strip HTML, embeds and wikilink brackets so only words remain.

    Parameters
    ----------
    text : str
        Obsidian markdown.

    Returns
    -------
    str
        The same text with ``<tags>`` and ``![[embeds]]`` removed and
        ``[[link|alias]]`` reduced to ``link``.
    """
    text = re.sub(r"<[^>]+>", " ", text)
    text = EMBED_RE.sub(" ", text)
    return re.sub(r"\[\[([^\]|#]*)[^\]]*\]\]", r"\1", text)


def tokens(text: str) -> list[str]:
    """Lower-case content words and numbers of a text, stopwords dropped.

    Parameters
    ----------
    text : str
        Any text; markup is cleaned first.

    Returns
    -------
    list of str
        Words of four or more letters and numbers of three or more
        characters, in order, minus STOPWORDS.
    """
    return [t for t in TOKEN_RE.findall(clean_markup(text).lower()) if t not in STOPWORDS]


def terms(text: str) -> set[str]:
    """The distinct tokens of a text."""
    return set(tokens(text))


def split_note(text: str) -> NoteParts:
    """Separate a lecture note into chart region and body.

    Parameters
    ----------
    text : str
        The whole note.

    Returns
    -------
    NoteParts
        ``body`` is empty when the note has no ``---`` after its frontmatter,
        i.e. it is chart only.
    """
    lines = text.split("\n")
    i = 0
    if lines and lines[0].strip() == "---":
        close = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), None)
        i = close + 1 if close is not None else 0
    end = next((k for k in range(i, len(lines)) if lines[k].strip() == "---"), None)
    if end is None:
        return NoteParts("\n".join(lines[i:]), [], len(lines))
    chart = "\n".join(lines[i:end])
    start = end + 1
    k = start
    while k < len(lines) and not lines[k].startswith(OBJECTIVES_MARK) and lines[k].strip() == "":
        k += 1
    if k < len(lines) and lines[k].startswith(OBJECTIVES_MARK):
        k += 1
        while k < len(lines) and lines[k].startswith(">"):
            k += 1
        start = k
    return NoteParts(chart, lines[start:], start)


def embed_index() -> dict[str, Path]:
    """Every ``.md`` note in the vault by lower-cased stem, for transclusions.

    Returns
    -------
    dict
        stem -> path; the first path seen wins for a duplicated stem.
    """
    index: dict[str, Path] = {}
    for p in VAULT.rglob("*.md"):
        index.setdefault(p.stem.lower(), p)
    return index


def embed_text(name: str, index: dict[str, Path]) -> str:
    """The text an ``![[...]]`` embed pulls in.

    Parameters
    ----------
    name : str
        The embed target, e.g. ``"neonatal sepsis"``,
        ``"hypothyroidism#Clinical Features"`` or ``"figure.png|caption"``.
    index : dict
        From ``embed_index``.

    Returns
    -------
    str
        The target note, or just the named heading's section of it, or an
        empty string for a picture, a canvas or a note not in the vault.
    """
    name = name.split("|", 1)[0].strip()
    heading = None
    if "#" in name:
        name, heading = name.split("#", 1)
    if IMAGE_RE.search(name):
        return ""
    p = index.get(name.strip().lower())
    if p is None:
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    if heading:
        m = re.search(r"^#+\s*" + re.escape(heading.strip()) + r"\s*$(.*?)(?=^#|\Z)",
                      text, re.M | re.S)
        return m.group(1) if m else ""
    return text


def sections(body: list[str], body_start: int, embed: Callable[[str], str]) -> list[Section]:
    """Split a note body at its top heading level and the next level present.

    Parameters
    ----------
    body : list of str
        Body lines from ``split_note``.
    body_start : int
        Index of ``body[0]`` in the note, so each section knows its line.
    embed : callable
        Resolves an embed target to text.

    Returns
    -------
    list of Section
        Top-level sections with their children; each section's ``text``
        includes its children's and every transclusion's text. A body with
        no heading at all is one section called ``(body)`` at line
        ``body_start``.
    """
    levels = sorted({len(m.group(1)) for ln in body if (m := HEADING_RE.match(ln))})
    if not levels:
        text = "\n".join(body)
        if not text.strip():
            return []
        s = Section(0, "(body)", body_start, _with_embeds(text, embed))
        s.words = len(s.text.split())
        return [s]
    top, child = levels[0], (levels[1] if len(levels) > 1 else None)
    out: list[Section] = []
    own: dict[int, list[str]] = {}
    cur_top = cur_child = None
    for k, ln in enumerate(body):
        m = HEADING_RE.match(ln)
        level = len(m.group(1)) if m else None
        if level == top:
            cur_top = Section(top, m.group(2), body_start + k)
            cur_child = None
            out.append(cur_top)
            own[id(cur_top)] = []
        elif level == child and cur_top is not None:
            cur_child = Section(child, m.group(2), body_start + k)
            cur_top.children.append(cur_child)
            own[id(cur_child)] = []
        else:
            target = cur_child if cur_child is not None else cur_top
            if target is not None:
                own[id(target)].append(ln)
    for s in out:
        for c in s.children:
            c.text = _with_embeds("\n".join(own[id(c)]), embed)
            c.words = len(c.text.split())
        s.text = "\n".join([_with_embeds("\n".join(own[id(s)]), embed)] + [c.text for c in s.children])
        s.words = len(s.text.split())
    return out


def _with_embeds(text: str, embed: Callable[[str], str]) -> str:
    """Append the text of every embed in ``text`` to it."""
    extra = [embed(name) for name in EMBED_RE.findall(text)]
    return "\n".join([text] + [e for e in extra if e])


def deck_pages(path: Path) -> list[str]:
    """The text of each slide of a deck.

    Parameters
    ----------
    path : Path
        A ``.pdf`` or ``.pptx``; pymupdf opens both.

    Returns
    -------
    list of str
        One string per page, empty for an image-only page.

    Raises
    ------
    RuntimeError
        When pymupdf cannot open the file.
    """
    import pymupdf
    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # pymupdf raises its own hierarchy
        raise RuntimeError(f"cannot open {path.name}: {exc}") from exc
    return [page.get_text() for page in doc]


def deck_files() -> list[Path]:
    """Every deck in DECK_DIRS.

    Returns
    -------
    list of Path
        ``.pdf`` and ``.pptx`` files, folders that do not exist skipped.
    """
    out = []
    for d in DECK_DIRS:
        if d.is_dir():
            out.extend(p for p in d.iterdir() if p.suffix.lower() in DECK_SUFFIXES)
    return out


def title_words(stem: str) -> set[str]:
    """The distinctive words of a note or deck title, stemmed to six letters.

    Parameters
    ----------
    stem : str
        A filename without suffix.

    Returns
    -------
    set of str
        Lower-case words of four or more letters, split on punctuation and
        camel case, minus STOPWORDS and TITLE_NOISE, each cut to six letters
        so ``hypertension`` meets ``hypertensive``.
    """
    stem = re.sub(r"^[\d.]+\s*-\s*", "", stem)
    stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    words = re.findall(r"[a-z]+", stem.lower())
    return {w[:6] for w in words if len(w) >= 4 and w not in STOPWORDS and w not in TITLE_NOISE}


def decks_for(note: Path, files: list[Path]) -> list[Path]:
    """The deck files that belong to a note.

    Parameters
    ----------
    note : Path
        The lecture note.
    files : list of Path
        From ``deck_files``. The note's own week folder is searched as well.

    Returns
    -------
    list of Path
        The DECKS entry when there is one (names resolved against ``files``
        and the week folder; an empty entry gives an empty list). Otherwise
        every file whose squashed name contains at least half of the note's
        title words and at least two of them (one when the title has only
        one), best score first.
    """
    local = [p for p in note.parent.iterdir() if p.suffix.lower() in DECK_SUFFIXES]
    pool = local + files
    if note.stem in DECKS:
        by_name = {p.name: p for p in pool}
        return [by_name[n] for n in DECKS[note.stem] if n in by_name]
    want = title_words(note.stem)
    if not want:
        return []
    need = min(2, len(want))
    scored = []
    for p in pool:
        squashed = re.sub(r"[^a-z0-9]", "", p.stem.lower())
        hit = sum(1 for w in want if w in squashed)
        if hit >= need and hit / len(want) >= 0.5:
            scored.append((hit / len(want), hit, p))
    scored.sort(key=lambda t: (-t[0], -t[1], t[2].name))
    return [p for _s, _h, p in scored]


def slide_coverage(section_terms: set[str], slides: list[set[str]]) -> float:
    """How much of the best-matching slide a section contains.

    Parameters
    ----------
    section_terms : set of str
        The section's distinct terms.
    slides : list of set of str
        Each slide's distinct terms; slides under SLIDE_MIN_TERMS are ignored.

    Returns
    -------
    float
        The largest fraction of one slide's terms found in the section.
    """
    best = 0.0
    for s in slides:
        if len(s) < SLIDE_MIN_TERMS:
            continue
        best = max(best, len(s & section_terms) / len(s))
    return best


def judge(secs: list[Section], slides: list[set[str]] | None) -> None:
    """Set score and verdict on every section and child.

    Parameters
    ----------
    secs : list of Section
        From ``sections``.
    slides : list of set of str or None
        Per-slide terms, or None when the note has no usable deck.
    """
    for s in secs:
        for item, parent in [(s, None)] + [(c, s) for c in s.children]:
            if slides is None:
                item.verdict = "no-deck"
                continue
            own = terms(item.text)
            if len(own) < SECTION_MIN_TERMS and parent is not None:
                item.score, item.verdict = None, parent.verdict
                continue
            item.score = slide_coverage(own, slides)
            item.verdict = "slides" if item.score >= SLIDES_AT else "inherited"


def audit_note(note: Path, files: list[Path], index: dict[str, Path]) -> NoteResult:
    """Find a note's deck and score its sections.

    Parameters
    ----------
    note : Path
        The lecture note.
    files : list of Path
        From ``deck_files``.
    index : dict
        From ``embed_index``.

    Returns
    -------
    NoteResult
        ``skipped`` is ``"no body"`` for a chart-only note. ``deck_label`` is
        the deck filenames joined with ``", "``, or ``"no deck found"``, or
        the filenames followed by ``" (no usable text)"`` or
        ``" (unreadable: ...)"``.
    """
    parts = split_note(note.read_text(encoding="utf-8", errors="replace"))
    secs = sections(parts.body, parts.body_start, lambda n: embed_text(n, index))
    decks = decks_for(note, files)
    if not secs:
        return NoteResult(note, decks, ", ".join(p.name for p in decks) or "no deck found", [], "no body")
    if not decks:
        judge(secs, None)
        return NoteResult(note, [], "no deck found", secs)
    label = ", ".join(p.name for p in decks)
    try:
        pages = [page for p in decks for page in deck_pages(p)]
    except RuntimeError as exc:
        judge(secs, None)
        return NoteResult(note, decks, f"{label} (unreadable: {exc})", secs)
    slides = [terms(page) for page in pages]
    if len(set().union(*slides)) < DECK_MIN_TERMS if slides else True:
        judge(secs, None)
        return NoteResult(note, decks, f"{label} (no usable text)", secs)
    judge(secs, slides)
    return NoteResult(note, decks, label, secs)


def lecture_notes(block: str) -> list[Path]:
    """The block's lecture notes in week and number order.

    Parameters
    ----------
    block : str
        ``"endo"`` or ``"repro"``.

    Returns
    -------
    list of Path
        Every ``.md`` under the block's week folders except ``Week N.md``.
    """
    folder, weeks = BLOCKS[block]
    out = []
    for w in weeks:
        d = LECTURE_NOTES / folder / f"Week {w}"
        if d.is_dir():
            out.extend(sorted(p for p in d.glob("*.md") if p.stem != f"Week {w}"))
    return out


def print_table(result: NoteResult) -> None:
    """Print one note's table."""
    print(f"== {result.note.stem}  [{result.note.parent.parent.name} / {result.note.parent.name}]")
    print(f"   deck: {result.deck_label}")
    if result.skipped:
        print(f"   {result.skipped}")
        return
    print(f"   {'section':60s} {'words':>5s} {'score':>5s}  verdict")
    for s in result.flat():
        name = ("#" * s.level + " " if s.level else "") + s.heading
        score = "-" if s.score is None else f"{s.score:.2f}"
        print(f"   {name[:60]:60s} {s.words:5d} {score:>5s}  {s.verdict}")


def write_json(results: list[NoteResult], out: Path) -> None:
    """Write the results as JSON under build/.

    Parameters
    ----------
    results : list of NoteResult
    out : Path
        Destination; its parent is created. Refuses a path inside the vault.
    """
    if VAULT in out.resolve().parents:
        raise SystemExit("refusing to write inside the vault")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = []
    for r in results:
        data.append({
            "note": r.note.stem, "week": r.note.parent.name, "decks": [p.name for p in r.decks],
            "deck_label": r.deck_label, "skipped": r.skipped,
            "sections": [{"level": s.level, "heading": s.heading, "line": s.line, "words": s.words,
                          "score": s.score, "verdict": s.verdict,
                          "parent": None if s in r.sections else next(
                              t.heading for t in r.sections if s in t.children)}
                         for s in r.flat()]})
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    """Parse the command line and print a table per note."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--block", required=True, choices=sorted(BLOCKS))
    ap.add_argument("--note", help="only the note with this stem, e.g. '09 - Approach to Neonatal Care'")
    ap.add_argument("--json", type=Path, help="also write the results here (under build/)")
    args = ap.parse_args()
    files = deck_files()
    index = embed_index()
    results = []
    for note in lecture_notes(args.block):
        if args.note and note.stem != args.note:
            continue
        r = audit_note(note, files, index)
        print_table(r)
        results.append(r)
    inherited = sum(1 for r in results for s in r.flat() if s.verdict == "inherited")
    nodeck = [r.note.stem for r in results if r.deck_label.startswith("no deck") or "(no usable" in r.deck_label or "(unreadable" in r.deck_label]
    print(f"\n{len(results)} notes, {inherited} inherited sections, {len(nodeck)} without a usable deck")
    for stem in nodeck:
        print(f"   no deck: {stem}", file=sys.stderr)
    if args.json:
        write_json(results, args.json)


if __name__ == "__main__":
    main()
```

Note on `audit_note`: the line `if len(set().union(*slides)) < DECK_MIN_TERMS if slides else True:` must be written as two clear lines instead; replace it with:

```python
    usable = len(set().union(*slides)) if slides else 0
    if usable < DECK_MIN_TERMS:
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests -q 2>&1 | tail -3`
Expected: 53 passed. If `test_slide_coverage_marks_taught_and_inherited` fails on `Neonatal Sepsis`, the synthetic sepsis text shares too many terms with the hypoglycemia slide; keep the fixture as written (it shares none) and look for a tokenizer bug instead.

- [ ] **Step 5: Calibrate on the real neonatal note, then confirm every deck match**

```bash
cd /home/nsims/repos/preclerkship
python3 tools/inherited_sections.py --block repro --note "09 - Approach to Neonatal Care"
```
Expected: deck line names `Approach to Neonatal Care Online Module Cheng Aug 2025.pdf`; `# Neonatal Resuscitation`, `# Newborn Transition` (with `#### Pulmonary Adaptation` and `#### Cardiovascular Adaptation`), `#### Respiratory Problems` and `#### Neonatal Sepsis` all `inherited` with scores below 0.5; `# Apgar Score`, `# Full Newborn Assessment`, `#### Hypothermia`, `#### Hypoglycemia`, `# Bilirubin & Jaundice` and `# Global Perspectives of Neonatal Care` all `slides` with scores of at least 0.5. If the real tokenizer (which keeps numbers) moves any of those across 0.5, adjust `SLIDES_AT` within 0.45 to 0.60 so the four inherited sit below and the six taught above, update the comment above the constants with the measured values, and say so in the task report. `#### Newborn Vital Signs` is not on either list; report its verdict without changing the threshold for it.

Then the whole block, both blocks:

```bash
python3 tools/inherited_sections.py --block repro --json build/inherited_sections/repro.json 2>&1 | tee build/inherited_sections/repro.txt | grep -E "^==|deck:"
python3 tools/inherited_sections.py --block endo --json build/inherited_sections/endo.json 2>&1 | tee build/inherited_sections/endo.txt | grep -E "^==|deck:"
```
For every note whose deck line is not `no deck found`, open the first deck's title slide and confirm it is that lecture:

```bash
python3 - <<'EOF'
import json, pymupdf
from pathlib import Path
import sys; sys.path.insert(0, "tools")
import inherited_sections as isx
files = isx.deck_files()
for block in ("endo", "repro"):
    for note in isx.lecture_notes(block):
        for p in isx.decks_for(note, files):
            try:
                first = pymupdf.open(p)[0].get_text().strip().replace("\n", " / ")[:90]
            except Exception as e:
                first = f"UNREADABLE {e}"
            print(f"{note.stem[:50]:50s} | {p.name[:55]:55s} | {first}")
EOF
```
Expected: each title slide names its lecture (or lecturer). A deck that belongs to another lecture is moved in `DECKS` (add the note stem with the right filenames, or `[]` to say none). Lectures expected to have no deck on disk from the 2026-10-06 listing: `01 - Intro to Diabetes`, `03 - Pharmacology of Insulin`, `10 - Polyendocrine Metabolic Ovarian Syndrome (PMOS)`, `17 - Early Pregnancy Counselling`, `In-Class - Amenorrhea`, `02 - Dilation and Curettage`, `17 - Physiologic Changes in Pregnancy`, and any the matcher finds nothing for (`01 - Abortion in Canada` through `08 - Postpartum Care` should all match). Paste the final `no deck:` list into the task report; the user exports those from OneNote.

Rerun the tests after any `DECKS` edit (the tests monkeypatch `DECKS`, so they do not depend on its contents).

- [ ] **Step 6: Document the tool**

In `tools/README.md`, after the paragraph that ends "`review_lectures.py --derive` re-derives every course, so diff the banks afterwards and keep only the changes you meant.", add:

```

## Finding what the slides do not teach

`inherited_sections.py` reads each lecture note of a block against the slide
deck on disk (a `.pdf` or `.pptx` under `$POM2_DECKS`, by default Downloads
and OneDrive/Documents, or beside the note), splits the body into sections
and scores each section by the best single slide it contains. A section no
slide lands in is `inherited`: an upper year's notes, not this year's
lecture. It prints the deck it used per note, or `no deck found`, and never
writes the vault.

```bash
python3 tools/inherited_sections.py --block repro
python3 tools/inherited_sections.py --block endo --json build/inherited_sections/endo.json
```

The thresholds are constants at the top of the file, calibrated on
`09 - Approach to Neonatal Care` against its 2025 deck. A deck whose text
layer is empty is reported as `no usable text` and its sections as `no-deck`,
never as inherited. `DECKS` maps a note to its deck filenames where the title
match would guess wrong.
```

- [ ] **Step 7: Commit**

```bash
cd /home/nsims/repos/preclerkship
git add tools/inherited_sections.py tools/tests/test_inherited_sections.py tools/README.md
git commit -m "inherited_sections: score each lecture-note section against its slide deck, calibrated on the neonatal note"
```

---

### Task 3: Rescore the handed-down questions against the slides

**Files:**
- Create: `tools/slides_shortlist.py`
- Create: `tools/tests/test_slides_shortlist.py`
- Create (gitignored): `build/curriculum_audit/endo_slides.prefill.json`, `repro_slides.prefill.json`, `endo_slides.txt`, `repro_slides.txt`, then the hand-written `endo_slides.json` and `repro_slides.json`
- Modify via `apply` only: `pom2/data/questions/endo.json`, `repro.json`
- Modify (generated): `pom2/*.html`, `index.html`, `pom2/data/notes/*.json`
- Modify (vault, not committed): workbook question notes via `mark-vault`; HippoNotes and Reviews notes via `vault_backup.py questions`

**Interfaces:**
- Consumes: from Task 2, `lecture_notes`, `deck_files`, `decks_for`, `embed_index`, `audit_note`, `terms`, `split_note`; from `curriculum_audit`, `bank_path`, `load_bank`, `load_rows`, `block_for_week`, `lecture_note`, `READ_FAMILIES`, `OFF`, `ROOT`.
- Produces: `python3 tools/slides_shortlist.py --block <slug>` prints one line per live handed-down question (qid, lecture, deck or NO-DECK, evidence score, section the evidence falls in and its verdict, SHORTLIST or ok) and writes `build/curriculum_audit/<slug>_slides.prefill.json` (one row per such question, in bank order, `verdict` already `current` for non-shortlisted and NO-DECK rows, empty string for shortlisted rows) and `build/curriculum_audit/<slug>_slides.txt` (the shortlist dumped for reading, in the brief's dump format plus the deck name and the evidence quotes). Constant `EVIDENCE_AT = 0.5`.
- Verdict rows written by the reader: `{"qid", "verdict": "current|not-covered", "against": "<NN - Lecture>", "week": <int>, "slides": "<deck filename(s)>", "evidence": "<quote from the deck or chart region, max 200 chars>", "note": ""|"NO-DECK"|"<one sentence>"}`. A NO-DECK row has `slides: ""`.

- [ ] **Step 1: Write the failing tests**

Create `tools/tests/test_slides_shortlist.py`:

```python
# -*- coding: utf-8 -*-
"""
Purpose: pin how slides_shortlist.py picks the questions to read against the deck
Author: Noor Sims
Date: 2026-10-06
Input: a synthetic bank, verdict files and vault built in tmp_path (no real PDF)
Output: pytest results
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import curriculum_audit as ca  # noqa: E402
import inherited_sections as isx  # noqa: E402
import slides_shortlist as ss  # noqa: E402
from test_inherited_sections import NOTE, SEPSIS, SLIDES  # noqa: E402


def question(qid, lecture, family="hipponotes", week=6, n="09"):
    return {"qid": qid, "num": qid.rsplit("Q", 1)[1], "week": week, "weekLabel": f"Week {week}",
            "lecture": lecture, "lectureMeta": "x", "family": family, "source": "hippo",
            "sourceLabel": "HippoNotes", "stem": "<p>Stem of " + qid + "</p>", "kind": "mcq",
            "options": [{"letter": "A", "html": "a"}, {"letter": "B", "html": "b"}],
            "correct": ["A"], "answer": "<p>Because.</p>", "flags": [], "tags": [],
            "review": [{"w": week, "n": n, "t": lecture}], "retired": False}


@pytest.fixture
def world(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "pom2/data/questions").mkdir(parents=True)
    (root / "build/curriculum_audit").mkdir(parents=True)
    vault = tmp_path / "vault"
    week = vault / "01 - Lectures/99 - PoM 2/02 - Repro/Week 6"
    week.mkdir(parents=True)
    (week / "09 - Approach to Neonatal Care.md").write_text(NOTE, encoding="utf-8")
    (week / "07 - Lactation.md").write_text(NOTE.replace("Neonatal Care", "Lactation"), encoding="utf-8")
    cond = vault / "00 - Medications/00 - Conditions/Pediatrics"
    cond.mkdir(parents=True)
    (cond / "neonatal sepsis.md").write_text(SEPSIS, encoding="utf-8")
    decks = tmp_path / "decks"
    decks.mkdir()
    (decks / "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf").write_bytes(b"")
    repro = [question("hippo-repro-Q1", "Approach to Neonatal Care"),
             question("hippo-repro-Q2", "Approach to Neonatal Care"),
             question("hippo-repro-Q3", "Lactation", n="07"),
             question("module-repro-Q4", "Approach to Neonatal Care", family="module"),
             question("hippo-repro-Q5", "Approach to Neonatal Care", family="offcurriculum")]
    (root / "pom2/data/questions/repro.json").write_text(json.dumps(repro), encoding="utf-8")
    rows = [{"qid": "hippo-repro-Q1", "verdict": "current", "against": "09 - Approach to Neonatal Care",
             "week": 6, "evidence": "Apgar score at 1 minute and 5 minutes, 7 or more is normal", "note": ""},
            {"qid": "hippo-repro-Q2", "verdict": "current", "against": "09 - Approach to Neonatal Care",
             "week": 6, "evidence": "chorioamnionitis, maternal group B streptococcus", "note": ""},
            {"qid": "hippo-repro-Q3", "verdict": "current", "against": "07 - Lactation",
             "week": 6, "evidence": "Apgar score at 1 minute and 5 minutes", "note": ""}]
    (root / "build/curriculum_audit/repro_w6.json").write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(ca, "ROOT", root)
    monkeypatch.setattr(ca, "LECTURE_NOTES", vault / "01 - Lectures/99 - PoM 2")
    monkeypatch.setattr(ss, "ROOT", root)
    monkeypatch.setattr(isx, "VAULT", vault)
    monkeypatch.setattr(isx, "LECTURE_NOTES", vault / "01 - Lectures/99 - PoM 2")
    monkeypatch.setattr(isx, "DECK_DIRS", [decks])
    monkeypatch.setattr(isx, "DECKS", {})
    monkeypatch.setattr(isx, "deck_pages", lambda path: list(SLIDES))
    return root


def test_shortlist_picks_evidence_off_the_slides_or_in_an_inherited_section(world):
    rows = ss.shortlist("repro")
    by = {r["qid"]: r for r in rows}
    assert set(by) == {"hippo-repro-Q1", "hippo-repro-Q2", "hippo-repro-Q3"}   # live handed-down only
    assert by["hippo-repro-Q1"]["status"] == "ok" and by["hippo-repro-Q1"]["evidence_score"] >= ss.EVIDENCE_AT
    assert by["hippo-repro-Q2"]["status"] == "SHORTLIST"
    assert by["hippo-repro-Q2"]["section"] == "Neonatal Sepsis" and by["hippo-repro-Q2"]["section_verdict"] == "inherited"


def test_no_deck_question_is_current_no_deck(world):
    rows = ss.shortlist("repro")
    q3 = next(r for r in rows if r["qid"] == "hippo-repro-Q3")
    assert q3["status"] == "NO-DECK" and q3["deck"] == ""
    prefill = ss.prefill(rows)
    row = next(r for r in prefill if r["qid"] == "hippo-repro-Q3")
    assert row["verdict"] == "current" and row["note"] == "NO-DECK" and row["slides"] == ""
    assert row["against"] == "07 - Lactation" and row["week"] == 6


def test_prefill_leaves_shortlisted_verdicts_empty_and_names_the_deck(world):
    prefill = ss.prefill(ss.shortlist("repro"))
    by = {r["qid"]: r for r in prefill}
    assert by["hippo-repro-Q1"]["verdict"] == "current"
    assert by["hippo-repro-Q2"]["verdict"] == ""
    assert by["hippo-repro-Q2"]["slides"] == "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf"
    assert [r["qid"] for r in prefill] == ["hippo-repro-Q1", "hippo-repro-Q2", "hippo-repro-Q3"]


def test_dump_lists_only_the_shortlist(world):
    text = ss.dump(ss.shortlist("repro"))
    assert "hippo-repro-Q2" in text and "Stem of hippo-repro-Q2" in text
    assert "hippo-repro-Q1" not in text and "hippo-repro-Q3" not in text
    assert "chorioamnionitis" in text          # the earlier evidence is shown for the reader
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests/test_slides_shortlist.py -q 2>&1 | tail -5`
Expected: `ModuleNotFoundError: No module named 'slides_shortlist'`.

- [ ] **Step 3: Implement**

Create `tools/slides_shortlist.py`:

```python
# -*- coding: utf-8 -*-
"""List the handed-down questions whose earlier audit evidence is not on the slides.

Purpose: the 2026-10-05 audit read questions against whole lecture notes, and
         a note body is often an upper year's. For every live workbook,
         HippoNotes and Schulich Reviews question this tool names the lecture
         it resolves to, that lecture's deck on disk, the earlier audit's
         evidence quote(s), whether the quote's terms are on the slides, and
         which note section the quote falls in and that section's verdict from
         inherited_sections.py. Questions whose evidence is off the slides, or
         falls in an inherited section, are the shortlist an Opus reader works
         against the deck and the chart region.
Author:  Noor Sims
Date:    2026-10-06
Input:   pom2/data/questions/<block>.json, build/curriculum_audit/*.json
         (verdict rows), the vault and decks inherited_sections.py reads
Output:  one line per question on stdout; build/curriculum_audit/<block>_slides.prefill.json
         (a verdict row per question, shortlisted ones with an empty verdict)
         and build/curriculum_audit/<block>_slides.txt (the shortlist dumped
         for reading). Reads the vault, never writes it.

    python tools/slides_shortlist.py --block repro

A lecture with no deck on disk cannot be judged against its slides: its
questions stay `current` with note "NO-DECK" and are listed for export.
"""

import argparse
import glob
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import curriculum_audit as ca  # noqa: E402
import inherited_sections as isx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

EVIDENCE_AT = 0.5    # fraction of an evidence quote's terms that must be on the slides
SECTION_AT = 0.6     # fraction of the quote's terms a section must hold to be where it falls

PREFILL = "{block}_slides.prefill.json"
DUMP = "{block}_slides.txt"
# verdict files the earlier reads wrote; the slides files this plan writes are excluded
EVIDENCE_GLOBS = ("*_w*.json", "*_refile*.json")


def strip_html(text: str) -> str:
    """Plain text of an HTML fragment."""
    return html.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def evidence_by_qid() -> dict[str, list[str]]:
    """Every earlier evidence quote per qid.

    Returns
    -------
    dict
        qid -> distinct non-empty quotes, in file order.
    """
    out: dict[str, list[str]] = {}
    paths = sorted({p for g in EVIDENCE_GLOBS
                    for p in glob.glob(str(ROOT / "build" / "curriculum_audit" / g))
                    if not p.endswith(".qids.json")})
    for row in ca.load_rows(paths):
        ev = (row.get("evidence") or "").strip()
        if ev and ev not in out.setdefault(row["qid"], []):
            out[row["qid"]].append(ev)
    return out


def resolve_note(q: dict) -> tuple[Path | None, str, int | None]:
    """The lecture note a question resolves to.

    Parameters
    ----------
    q : dict
        A question with ``review`` or ``lecture``.

    Returns
    -------
    tuple
        (note path or None, against stem, week). The stem comes from
        ``review[0]`` when it exists, else from ``lecture`` and ``week``.
    """
    rev = (q.get("review") or [None])[0]
    if rev:
        block = ca.block_for_week(int(rev["w"]))
        note = ca.lecture_note(block, rev) if block else None
        stem = note.stem if note else (f"{rev['n']} - {rev['t']}" if rev.get("n") else rev["t"])
        return note, stem, int(rev["w"])
    return None, q.get("lecture") or "", q.get("week")


def section_of(quote_terms: set[str], result: isx.NoteResult) -> tuple[str, str]:
    """The note section an evidence quote falls in.

    Parameters
    ----------
    quote_terms : set of str
    result : NoteResult
        From ``inherited_sections.audit_note``.

    Returns
    -------
    tuple
        (heading, verdict) of the child or top section holding the largest
        share of the quote's terms, if that share reaches SECTION_AT; else
        ("", "").
    """
    best, hit = (("", ""), 0.0)
    if not quote_terms:
        return best
    for s in result.flat():
        share = len(quote_terms & isx.terms(s.text)) / len(quote_terms)
        deeper = s.level > 0 and s.children == []
        if share > hit or (share == hit and deeper and share > 0):
            best, hit = (s.heading, s.verdict), share
    return best if hit >= SECTION_AT else ("", "")


def shortlist(block: str) -> list[dict]:
    """Score every live handed-down question of a block against its deck.

    Parameters
    ----------
    block : str
        ``"endo"`` or ``"repro"``.

    Returns
    -------
    list of dict
        One per question, in bank order: qid, family, against, week, deck,
        chart, evidence (list), evidence_score, section, section_verdict,
        status (``ok`` / ``SHORTLIST`` / ``NO-DECK``), stem, options, key,
        answer.
    """
    files = isx.deck_files()
    index = isx.embed_index()
    evidence = evidence_by_qid()
    cache: dict[Path, isx.NoteResult] = {}
    out = []
    for q in ca.load_bank(ca.bank_path(block)):
        if q.get("family") not in ca.READ_FAMILIES or q.get("family") == ca.OFF:
            continue
        note, against, week = resolve_note(q)
        quotes = evidence.get(q["qid"], [])
        row = {"qid": q["qid"], "family": q["family"], "against": against, "week": week,
               "deck": "", "chart": "", "evidence": quotes, "evidence_score": None,
               "section": "", "section_verdict": "", "status": "NO-DECK",
               "stem": strip_html(q.get("stem")),
               "options": [f"{o['letter']}. {strip_html(o.get('html'))}" for o in q.get("options") or []],
               "key": ", ".join(q.get("correct") or []), "answer": strip_html(q.get("answer"))[:400]}
        if note is None or not note.exists():
            row["status"] = "NO-NOTE"
            out.append(row)
            continue
        if note not in cache:
            cache[note] = isx.audit_note(note, files, index)
        res = cache[note]
        usable = res.decks and "(no usable" not in res.deck_label and "(unreadable" not in res.deck_label
        row["chart"] = isx.split_note(note.read_text(encoding="utf-8", errors="replace")).chart
        if not usable:
            out.append(row)
            continue
        row["deck"] = ", ".join(p.name for p in res.decks)
        slide_terms = set().union(*[isx.terms(pg) for p in res.decks for pg in isx.deck_pages(p)])
        scores = []
        for quote in quotes:
            qt = isx.terms(quote)
            scores.append(len(qt & slide_terms) / len(qt) if qt else 0.0)
        row["evidence_score"] = max(scores) if scores else 0.0
        heading, verdict = section_of(isx.terms(" ".join(quotes)), res) if quotes else ("", "")
        row["section"], row["section_verdict"] = heading, verdict
        off_slides = row["evidence_score"] < EVIDENCE_AT
        row["status"] = "SHORTLIST" if (off_slides or verdict == "inherited") else "ok"
        out.append(row)
    return out


def prefill(rows: list[dict]) -> list[dict]:
    """Verdict rows for every question, shortlisted ones left for the reader.

    Parameters
    ----------
    rows : list of dict
        From ``shortlist``.

    Returns
    -------
    list of dict
        Rows in the audit's shape plus ``slides``. ``ok`` rows are
        ``current`` with the first earlier evidence quote; ``NO-DECK`` rows
        are ``current`` with note ``NO-DECK``; ``SHORTLIST`` rows have an
        empty verdict and evidence for the reader to fill.
    """
    out = []
    for r in rows:
        first = (r["evidence"] or [""])[0][:200]
        if r["status"] == "SHORTLIST":
            out.append({"qid": r["qid"], "verdict": "", "against": r["against"], "week": r["week"],
                        "slides": r["deck"], "evidence": "", "note": ""})
        elif r["status"] == "ok":
            out.append({"qid": r["qid"], "verdict": "current", "against": r["against"], "week": r["week"],
                        "slides": r["deck"], "evidence": first, "note": ""})
        else:
            out.append({"qid": r["qid"], "verdict": "current", "against": r["against"], "week": r["week"],
                        "slides": "", "evidence": first, "note": r["status"]})
    return out


def dump(rows: list[dict]) -> str:
    """The shortlist as plain text for reading in slices.

    Parameters
    ----------
    rows : list of dict
        From ``shortlist``; only ``SHORTLIST`` rows are written.

    Returns
    -------
    str
        One block per question: qid, lecture, deck, the earlier evidence and
        where it fell, the stem, the options, the key and the answer.
    """
    parts = []
    for r in rows:
        if r["status"] != "SHORTLIST":
            continue
        parts.append("\n".join([
            f"### {r['qid']}  [{r['family']}]  week {r['week']}  {r['against']}",
            f"deck: {r['deck']}",
            f"earlier evidence (score {r['evidence_score']:.2f}; section: {r['section'] or '?'} {r['section_verdict']}):",
            *[f"  - {e}" for e in r["evidence"]],
            f"stem: {r['stem']}",
            *[f"  {o}" for o in r["options"]],
            f"key: {r['key']}",
            f"answer: {r['answer']}",
            ""]))
    return "\n".join(parts)


def main() -> None:
    """Print the table and write the prefill and the dump."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--block", required=True, choices=sorted(isx.BLOCKS))
    args = ap.parse_args()
    rows = shortlist(args.block)
    width = max([len(r["qid"]) for r in rows] + [3])
    print(f"{'qid':{width}s}  {'status':9s} {'evid':>5s} {'lecture':45s} {'section':35s} deck")
    for r in rows:
        score = "-" if r["evidence_score"] is None else f"{r['evidence_score']:.2f}"
        sec = f"{r['section'][:28]} [{r['section_verdict']}]" if r["section"] else ""
        print(f"{r['qid']:{width}s}  {r['status']:9s} {score:>5s} {r['against'][:45]:45s} {sec:35s} {r['deck'] or 'NO-DECK'}")
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"\n{len(rows)} live handed-down questions: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    nodeck = sorted({r["against"] for r in rows if r["status"] == "NO-DECK"})
    for stem in nodeck:
        print(f"   NO-DECK lecture: {stem}", file=sys.stderr)
    out = ROOT / "build" / "curriculum_audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / PREFILL.format(block=args.block)).write_text(
        json.dumps(prefill(rows), ensure_ascii=False, indent=1), encoding="utf-8")
    (out / DUMP.format(block=args.block)).write_text(dump(rows), encoding="utf-8")
    print(f"wrote {out / PREFILL.format(block=args.block)} and {out / DUMP.format(block=args.block)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests -q 2>&1 | tail -3`
Expected: 57 passed.

- [ ] **Step 5: Run both blocks and record the counts**

```bash
cd /home/nsims/repos/preclerkship
python3 tools/slides_shortlist.py --block repro 2>&1 | tail -25
python3 tools/slides_shortlist.py --block endo 2>&1 | tail -25
wc -l build/curriculum_audit/repro_slides.txt build/curriculum_audit/endo_slides.txt
```
Expected: repro reports 219 live handed-down questions and endo 211 (counts of 2026-10-06 after Task 1; recount with `len()` if they differ), each split into `ok`, `SHORTLIST`, `NO-DECK` and possibly `NO-NOTE`. Any `NO-NOTE` row means `review[0]` points at a note that is not on disk; list those qids in the task report and treat them as NO-DECK. Paste both summary lines and both `NO-DECK lecture:` lists into the task report.

- [ ] **Step 6: Read the shortlist against the slides, per block**

Follow `build/curriculum_audit/AUDIT_BRIEF.md` Method step 1 with `build/curriculum_audit/<slug>_slides.txt` as the dump: read it in slices of 20 to 30 questions (`sed -n` ranges), never the whole file at once. For each question's lecture, dump its deck text once to the scratchpad (`python3 -c 'import pymupdf,sys; print("\n".join(p.get_text() for p in pymupdf.open(sys.argv[1])))' "<deck path>"`), and read the note's chart region (above the first `---`), which is slide-derived. Decide:

- `current`: the discriminator that picks the key is stated on a slide, or in the chart region. `evidence` is a quote of at most 200 characters from the slide or the chart; `slides` is the deck filename(s) the prefill row already carries.
- `not-covered`: the discriminator is on no slide and not in the chart, and the only place the note teaches it is a body section (or a transclusion) `inherited_sections.py` calls `inherited`, or nowhere. `against` stays the lecture; `evidence` is what the deck does cover (so the flag reads "which cover: ..."); `note` names the body section the fact sat in.
- A wrong key on slide-taught material stays `current` with `KEY?` in `note`; add it to `build/curriculum_audit/KEY_ISSUES.md`.
- Never guess: if the deck text is garbled where the fact would be (small type, a figure), `current` with `UNVERIFIED` in `note`.
- Reaching the key by eliminating the other options does not count.
- The five Task 1 questions are already off-curriculum and are not in the shortlist.

Fill every empty `verdict` in `build/curriculum_audit/<slug>_slides.prefill.json` and save the completed list as `build/curriculum_audit/<slug>_slides.json`, then check it:

```bash
python3 - <<'EOF'
import json, sys
for slug in ("endo", "repro"):
    rows = json.load(open(f"build/curriculum_audit/{slug}_slides.json"))
    pre = json.load(open(f"build/curriculum_audit/{slug}_slides.prefill.json"))
    assert [r["qid"] for r in rows] == [r["qid"] for r in pre], slug
    empty = [r["qid"] for r in rows if r["verdict"] not in ("current", "not-covered")]
    nodeck = sum(1 for r in rows if r["note"] == "NO-DECK")
    moved = [r["qid"] for r in rows if r["verdict"] == "not-covered"]
    print(slug, len(rows), "rows; empty verdicts", empty, "; NO-DECK", nodeck, "; not-covered", len(moved))
EOF
```
Expected: `empty verdicts []` for both blocks. Then `rm build/curriculum_audit/*_slides.prefill.json`.

- [ ] **Step 7: Apply, mark the vault, rebuild, back up**

```bash
cd /home/nsims/repos/preclerkship
python3 tools/curriculum_audit.py apply build/curriculum_audit/endo_slides.json build/curriculum_audit/repro_slides.json
python3 tools/curriculum_audit.py report 2>&1 | grep -E "^==|misfiled|week title|not-covered"
python3 tools/curriculum_audit.py mark-vault --dry-run build/curriculum_audit/endo_slides.json build/curriculum_audit/repro_slides.json
python3 tools/curriculum_audit.py mark-vault build/curriculum_audit/endo_slides.json build/curriculum_audit/repro_slides.json
python3 tools/build_pages.py && python3 tools/build_index.py && python3 tools/build_hub.py
python3 tools/vault_backup.py questions
python3 -m pytest tools/tests -q 2>&1 | tail -2
git status --short
```
Expected: `apply` prints `moved N` per block equal to the not-covered counts of Step 6 and `week filled 0`; `report` shows `misfiled 0` and `lecture is the week title 0` for both blocks, null week 0, and the new qids under `off-curriculum, not-covered`; the dry run names only workbook qids as markable and the real run marks the same count; `git status` shows only the two banks and generated pages.

- [ ] **Step 8: Commit**

```bash
cd /home/nsims/repos/preclerkship
git add tools/slides_shortlist.py tools/tests/test_slides_shortlist.py pom2/data/questions/endo.json pom2/data/questions/repro.json pom2 index.html
git commit -m "Endo and repro: move the handed-down questions this year's slides do not teach; slides_shortlist lists what to read against the deck"
```

Task report must include: the per-block status counts from Step 5, the per-block not-covered qids with the body section each sat in, every `KEY?` and `UNVERIFIED`, and the NO-DECK lecture list under the heading "Export these decks from OneNote".

---

### Task 4: Mark inherited sections in the notes and teach the skill

**Files:**
- Create: `tools/mark_inherited.py`
- Create: `tools/tests/test_mark_inherited.py`
- Modify: `skills/pom2-week/SKILL.md` (Stage 1 after the Extra-content bullet; Stage 4b intro sentence, two table rows, the handed-down bullet, the procedure; Stage 7 bullet list)
- Modify: `build/curriculum_audit/AUDIT_BRIEF.md` (Reference bullet, Method steps 2 and 3, Output)
- Modify: `tools/README.md` (one paragraph in the section Task 2 added)
- Modify (vault, not committed): every endo and repro lecture note with an inherited section

**Interfaces:**
- Consumes: from Task 2, `lecture_notes`, `deck_files`, `embed_index`, `audit_note`, `INHERITED_MARK`, `NoteResult`, `Section`.
- Produces: `python3 tools/mark_inherited.py --block {endo,repro} [--dry-run] [--note <stem>]`. Under each top-level section with verdict `inherited` it inserts, directly after the heading line, exactly two lines:
  `> [!warning] Inherited`
  `> Not in this year's slides (<deck filename(s)>). Kept for reference; not examinable this year unless the lecture says otherwise.`
  When a top-level section is `slides` but a child is `inherited`, the child is marked instead. A section whose next line already starts with `> [!warning] Inherited` is skipped. `no-deck` notes are never touched. `--dry-run` prints `would mark <note stem>: <heading>` per insertion and writes nothing.

- [ ] **Step 1: Write the failing tests**

Create `tools/tests/test_mark_inherited.py`:

```python
# -*- coding: utf-8 -*-
"""
Purpose: pin that mark_inherited.py writes the Inherited callout once, under the right headings
Author: Noor Sims
Date: 2026-10-06
Input: the synthetic vault from test_inherited_sections (no real PDF)
Output: pytest results
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inherited_sections as isx  # noqa: E402
import mark_inherited as mi  # noqa: E402
from test_inherited_sections import vault, note_path  # noqa: E402,F401

CALLOUT = ("> [!warning] Inherited\n"
           "> Not in this year's slides (Approach to Neonatal Care Online Module Cheng Aug 2025.pdf). "
           "Kept for reference; not examinable this year unless the lecture says otherwise.")


def test_marks_inherited_top_sections_and_inherited_children_only(vault):
    n = mi.mark("repro", dry=False)
    text = note_path(vault).read_text(encoding="utf-8")
    assert n == 2
    assert "# Neonatal Resuscitation\n" + CALLOUT + "\nVentilation" in text
    assert "#### Neonatal Sepsis\n" + CALLOUT + "\n![[neonatal sepsis]]" in text
    assert "# Apgar Score\n> [!warning]" not in text
    assert "# Extra Care for the Neonate\n> [!warning]" not in text      # parent is slides
    assert "#### Hypoglycemia\n> [!warning]" not in text
    assert text.count("> [!warning] Inherited") == 2


def test_marking_twice_changes_nothing(vault):
    mi.mark("repro", dry=False)
    before = note_path(vault).read_bytes()
    assert mi.mark("repro", dry=False) == 0
    assert note_path(vault).read_bytes() == before


def test_dry_run_writes_nothing(vault, capsys):
    before = note_path(vault).read_bytes()
    n = mi.mark("repro", dry=True)
    assert n == 2 and note_path(vault).read_bytes() == before
    out = capsys.readouterr().out
    assert "would mark 09 - Approach to Neonatal Care: Neonatal Resuscitation" in out


def test_no_deck_note_is_left_alone(vault, monkeypatch):
    monkeypatch.setattr(isx, "deck_pages", lambda path: ["", ""])
    before = note_path(vault).read_bytes()
    assert mi.mark("repro", dry=False) == 0
    assert note_path(vault).read_bytes() == before


def test_keeps_lf_and_no_extra_blank_lines(vault):
    mi.mark("repro", dry=False)
    raw = note_path(vault).read_bytes()
    assert b"\r\n" not in raw
    assert b"# Neonatal Resuscitation\n> [!warning] Inherited\n> Not in" in raw
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests/test_mark_inherited.py -q 2>&1 | tail -5`
Expected: `ModuleNotFoundError: No module named 'mark_inherited'`.

- [ ] **Step 3: Implement**

Create `tools/mark_inherited.py`:

```python
# -*- coding: utf-8 -*-
"""Put an Inherited callout under every lecture-note section the slides do not teach.

Purpose: inherited_sections.py finds the body sections of a PoM 2 lecture
         note that no slide of this year's deck lands in. This tool writes a
         warning callout directly under each such heading so a reader, and
         the curriculum check, know the section is an upper year's notes and
         not this year's lecture. It is idempotent: a heading already
         followed by the callout is skipped.
Author:  Noor Sims
Date:    2026-10-06
Input:   the block's lecture notes and decks, as inherited_sections.py reads them
Output:  the same notes with two lines inserted under each inherited heading;
         ``--dry-run`` prints what would change and writes nothing. Notes
         with no usable deck are never touched.

    python tools/mark_inherited.py --block repro --dry-run
    python tools/mark_inherited.py --block repro
    python tools/mark_inherited.py --block endo --note "09 - Introduction to Obesity"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inherited_sections as isx  # noqa: E402

CALLOUT_BODY = ("> Not in this year's slides ({decks}). Kept for reference; "
                "not examinable this year unless the lecture says otherwise.")


def callout(decks: str) -> list[str]:
    """The two callout lines for a deck label.

    Parameters
    ----------
    decks : str
        Deck filename(s), as ``NoteResult.deck_label`` gives them.

    Returns
    -------
    list of str
        ``["> [!warning] Inherited", "> Not in this year's slides (...)..."]``.
    """
    return [isx.INHERITED_MARK, CALLOUT_BODY.format(decks=decks)]


def targets(result: isx.NoteResult) -> list[isx.Section]:
    """The sections to mark in one note.

    Parameters
    ----------
    result : NoteResult
        From ``inherited_sections.audit_note``.

    Returns
    -------
    list of Section
        Each top-level section with verdict ``inherited``; for a top-level
        section with any other verdict, each child with verdict
        ``inherited``. Empty when the note has no usable deck.
    """
    if not result.decks or "(no usable" in result.deck_label or "(unreadable" in result.deck_label:
        return []
    out = []
    for s in result.sections:
        if s.verdict == "inherited":
            out.append(s)
        else:
            out.extend(c for c in s.children if c.verdict == "inherited")
    return out


def mark_note(result: isx.NoteResult, dry: bool) -> int:
    """Insert the callout under each target heading of one note.

    Parameters
    ----------
    result : NoteResult
    dry : bool
        Print instead of writing.

    Returns
    -------
    int
        Insertions made (or that would be made).
    """
    todo = targets(result)
    if not todo:
        return 0
    lines = result.note.read_text(encoding="utf-8").split("\n")
    made = 0
    for s in sorted(todo, key=lambda t: -t.line):      # bottom up keeps earlier indices valid
        if lines[s.line].lstrip("#").strip() != s.heading:
            print(f"  heading moved, skipped: {result.note.stem}: {s.heading}", file=sys.stderr)
            continue
        if s.line + 1 < len(lines) and lines[s.line + 1].startswith(isx.INHERITED_MARK):
            continue
        if dry:
            print(f"would mark {result.note.stem}: {s.heading}")
        else:
            lines[s.line + 1:s.line + 1] = callout(result.deck_label)
        made += 1
    if made and not dry:
        with result.note.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines))
        print(f"marked {result.note.stem}: {made}")
    return made


def mark(block: str, dry: bool, only: str | None = None) -> int:
    """Mark every inherited section of a block.

    Parameters
    ----------
    block : str
        ``"endo"`` or ``"repro"``.
    dry : bool
        Print what would change, write nothing.
    only : str or None
        Restrict to the note with this stem.

    Returns
    -------
    int
        Insertions made across the block.
    """
    files = isx.deck_files()
    index = isx.embed_index()
    total = 0
    for note in isx.lecture_notes(block):
        if only and note.stem != only:
            continue
        total += mark_note(isx.audit_note(note, files, index), dry)
    print(f"{'would insert' if dry else 'inserted'} {total} Inherited callouts in {block}")
    return total


def main() -> None:
    """Parse the command line and mark one block."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--block", required=True, choices=sorted(isx.BLOCKS))
    ap.add_argument("--note", help="only the note with this stem")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    mark(args.block, args.dry_run, args.note)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests -q 2>&1 | tail -3`
Expected: 62 passed.

- [ ] **Step 5: Dry-run, then mark both blocks**

```bash
cd /home/nsims/repos/preclerkship
python3 tools/mark_inherited.py --block repro --dry-run
python3 tools/mark_inherited.py --block endo --dry-run
```
Read both lists. Expected for the neonatal note: `Neonatal Resuscitation`, `Newborn Transition`, `Respiratory Problems`, `Neonatal Sepsis`, and `Newborn Vital Signs` if Task 2 Step 5 left it inherited. A heading on the list that is plainly this year's material (its words are on a slide you can see) means the deck match or threshold is wrong for that note: fix `DECKS` or report it, do not mark it. Then:

```bash
python3 tools/mark_inherited.py --block repro
python3 tools/mark_inherited.py --block endo
python3 tools/mark_inherited.py --block repro --dry-run | tail -1
grep -n -A2 "^# Neonatal Resuscitation" "/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2/02 - Repro/Week 6/09 - Approach to Neonatal Care.md"
```
Expected: the second dry run prints `would insert 0 Inherited callouts in repro`; the grep shows the heading followed by `> [!warning] Inherited` and the `> Not in this year's slides (Approach to Neonatal Care Online Module Cheng Aug 2025.pdf). ...` line. Paste both insertion counts and the full list of marked headings per note into the task report.

- [ ] **Step 6: Teach Stage 1 of the skill**

In `skills/pom2-week/SKILL.md`, Stage 1, the bullet list under "So when OneNote and the existing note disagree" ends with the bullet:

```
- **Extra** content, in the note but not in this year's lecture, is left alone unless it
  contradicts OneNote. An upper year's note going deeper than the lecture is not a conflict, it
  is context.
```

Directly after that bullet (before the paragraph beginning `**Report every override**`), insert:

```

**Longer than the slides is the tell, and the extra gets labelled.** A body that runs well past
what the deck covers is an upper year's notes, not this year's lecture. When a note's body is
longer than its slides, run `python3 tools/inherited_sections.py --block <slug> --note "<NN -
Lecture>"` and read its table: a section marked `inherited` has no slide whose words it
carries. Then `python3 tools/mark_inherited.py --block <slug> --note "<NN - Lecture>" --dry-run`,
read the list, and the same without `--dry-run`. It puts a `> [!warning] Inherited` callout
directly under each such heading, naming the deck, and nothing else. The section stays in the
note as context, but a reader and Stage 4b both know not to count it as taught. Running either
tool twice changes nothing. A lecture with no deck on disk comes back `no deck found` and its
note is left as it is; name it in Stage 7 so she can export the deck from OneNote. *Observed
2026-10-06: `09 - Approach to Neonatal Care` carried Neonatal Resuscitation, Newborn Transition,
Respiratory Problems and Neonatal Sepsis sections that the 2025 deck never teaches, and five
HippoNotes questions passed the 2026-10-05 read on them.*
```

- [ ] **Step 7: Teach Stage 4b of the skill**

Still in `skills/pom2-week/SKILL.md`, make these five edits.

(a) Replace the sentence:

```
Each question gets one of these verdicts, against this year's notes for the block (follow
transclusions before calling anything absent; where a note is silent on an exact value, the slide
PDF decides):
```
with:
```
Each question gets one of these verdicts, against this year's slides for the block: the deck on
disk, and the note's chart region, which is written from the deck. The note body is context, not
the check. A body section under a `> [!warning] Inherited` callout does not count as taught, and
a transclusion counts only where the slides teach the same thing. Where no deck is on disk the
body stands in and the row says `NO-DECK`:
```

(b) In the verdict table, replace the `current` row with:

```
| `current` | the tested fact is on this year's slides for the block, or in the chart region written from them, and the key agrees | nothing |
```
and the `not-covered` row with:
```
| `not-covered` | the tested fact is on none of this year's slides for the block, or only a body section under an Inherited callout teaches it | move to Off-curriculum, name the lecture and its deck |
```

(c) Replace the sentence `Adjacent clinical depth the lecture does not go into (a drug the note never names, a staging
system the slides skip) is `not-covered`.` with:

```
Adjacent clinical depth the lecture does not go into (a drug the slides never name, a staging
system they skip) is `not-covered`. So is a fact that only an inherited section teaches: on
2026-10-05 hippo-repro-Q77 to Q81 passed on the neonatal note's resuscitation, transition,
respiratory and sepsis sections, none of which is in the 2025 deck, and she confirmed none was
taught.
```

(d) In the handed-down bullet, replace `the
  discriminator that picks the key has to be stated in this year's notes or slides.` with `the
  discriminator that picks the key has to be on this year's slides, or in the chart region
  written from them; the note body alone does not carry it.`

(e) In "The procedure": replace `Read each candidate, and **every question
whose lecture note Stage 1 changed this run**, against that note, the way the brief says.` with:

```
Read each candidate, and **every question
whose lecture note Stage 1 changed this run**, against that lecture's deck and chart region, the
way the brief says. `python3 tools/slides_shortlist.py --block <slug>` prints, per live
handed-down question, the deck it resolves to and whether the last read's evidence is on the
slides, and writes the shortlist to `build/curriculum_audit/<slug>_slides.txt` for reading. A
lecture it prints as `NO-DECK` cannot be judged: its questions stay `current` with `NO-DECK` in
`note`, and the lecture goes in the Stage 7 report.
```

In procedure step 1, replace `evidence a quote of at most 200 characters
   from the note or slide.` with `evidence a quote of at most 200 characters
   from the slide or the chart region (from the note body only on a `NO-DECK` row), and `slides`
   the deck filename so the Off-curriculum flag can name it.`

(f) In Stage 7's bullet list, after the bullet beginning `- Everything skipped and why:`, add:

```
- **Lectures with no deck on disk**, named, so she can export them from OneNote. Their questions
  were not checked against the slides this run.
```

- [ ] **Step 8: Update the brief and the README**

In `build/curriculum_audit/AUDIT_BRIEF.md`:

Replace the Reference bullet (from `- Reference (this year's slides, as synced into the notes on 2026-10-03):` through `other notes with `![[...]]`; follow those before calling a topic absent.`) with:

```
- Reference, in this order: the lecture's slide deck on disk (the file
  `python3 tools/inherited_sections.py --block <slug>` prints for the note, read with pymupdf),
  then the note's chart region (above the first `---`), which is written from the deck. The note
  body (from `> [!check] Objectives` down) is context, not the check: much of it is an upper
  year's notes. A body section under `> [!warning] Inherited` does not count as taught, and a
  transclusion counts only where the slides teach the same thing. Notes live at
  "/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2/01 - Endocrinology/Week N/NN - <Lecture>.md"
  and ".../02 - Repro/Week N/NN - <Lecture>.md"; endo is weeks 1-3, repro weeks 4-6.
  A lecture with no deck on disk cannot be judged: its questions stay `current` with "NO-DECK" in
  `note`, and the lecture is listed in your reply so it can be exported from OneNote.
```

Replace the Slide PDFs bullet (`- Slide PDFs, only when a note is silent on an exact value: ...` through `Do not use OneNote or any MCP tool.`) with:

```
- Slide decks: /mnt/c/Users/nsims/Downloads/ and /mnt/c/Users/nsims/OneDrive/Documents/ (.pdf and
  .pptx; `pymupdf.open` reads both under python3). Do not use OneNote or any MCP tool.
```

In Method step 2, replace `Read every lecture note for your week(s) once` with `Read every lecture's deck and chart region for your week(s) once`, and `Grep the whole block
   folder (both weeks' folders of the block if the question could sit elsewhere) before calling
   a fact not-covered: `grep -ril "<term>" "<block folder>"`.` with `Grep the deck texts of the
   block before calling a fact not-covered; a grep hit in a note body under an Inherited callout
   does not count.`

In Method step 3, replace the `current` bullet's first sentence `current: the tested discriminator is in this year's notes for the block and the key agrees.` with `current: the tested discriminator is on this year's slides for the block, or in the chart region, and the key agrees.` and the `not-covered` bullet with:

```
   - not-covered: the tested fact is on none of this year's slides for the block, or only a body
     section under an Inherited callout teaches it. Name the lecture; `evidence` is what its deck
     does cover, so the flag reads "which cover: ...".
```

In Output, replace the row shape with:

```
{"qid": "...", "verdict": "current|outdated|not-covered|misfiled", "against": "<NN - Lecture note name>",
 "week": <int week of that lecture>, "slides": "<deck filename(s), empty on a NO-DECK row>",
 "evidence": "<quote, max 200 chars, from the slide or chart region>", "note": "<one sentence; empty string if nothing to add>"}
```

In `tools/README.md`, at the end of the section "Finding what the slides do not teach" (added in Task 2), add:

```

`mark_inherited.py --block <slug> [--dry-run]` writes a `> [!warning] Inherited`
callout directly under each inherited heading, naming the deck, and is
idempotent. `slides_shortlist.py --block <slug>` lists every live handed-down
question with its deck and whether the last audit's evidence is on the slides,
and writes the shortlist to `build/curriculum_audit/<slug>_slides.txt` for a
reader; a lecture with no deck is `NO-DECK` and its questions stay current.
```

- [ ] **Step 9: Check the prose and commit**

```bash
cd /home/nsims/repos/preclerkship
grep -n "—" skills/pom2-week/SKILL.md build/curriculum_audit/AUDIT_BRIEF.md tools/README.md tools/mark_inherited.py tools/inherited_sections.py tools/slides_shortlist.py | grep -v "^.*:.*\"[^\"]*—" || echo "no em dashes"
python3 -m pytest tools/tests -q 2>&1 | tail -2
git add tools/mark_inherited.py tools/tests/test_mark_inherited.py skills/pom2-week/SKILL.md tools/README.md
git commit -m "mark_inherited: Inherited callout under note sections the slides do not teach; pom2-week checks questions against the slides and labels inherited sections"
```
Expected: the grep prints `no em dashes` (the only `—` allowed is inside `rosters_from_vault.py`, which is not in the list); 62 tests pass; the commit contains the four paths (the brief lives under `build/` and stays on disk).

---

### Task 5: Push

Done by the orchestrator, not an agent.

- [ ] **Step 1:** `cd /home/nsims/repos/preclerkship && git log --oneline -5 && git push origin main`.
- [ ] **Step 2:** Send the user the NO-DECK lecture list from Task 3's report so the decks can be exported from OneNote, and the list of marked headings from Task 4 so any wrongly marked section can be unmarked by deleting its two callout lines.

