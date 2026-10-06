# -*- coding: utf-8 -*-
"""
Purpose: pin how inherited_sections.py splits a note, matches a deck and scores a section
Author: Noor Sims
Date: 2026-10-06
Input: a synthetic vault note and synthetic slide texts built in tmp_path (no real PDF)
Output: pytest results
"""
import json
import os
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
    monkeypatch.setattr(isx, "PARTIAL", {})
    monkeypatch.setattr(isx, "CACHE_DIR", tmp_path / "cache")
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
    assert result.deck_label == ("no deck found (no usable text: "
                                 "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf)")
    assert {s.verdict for s in result.flat()} == {"no-deck"}


def test_no_deck_found(vault):
    (vault.parent / "decks" / "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf").unlink()
    result = isx.audit_note(note_path(vault), isx.deck_files(), isx.embed_index())
    assert result.deck_label == "no deck found"
    assert {s.verdict for s in result.flat()} == {"no-deck"}


def test_chart_only_note_is_skipped(vault):
    p = note_path(vault)
    chart_only = "\n".join(NOTE.split("\n")[:7]) + "\n"     # frontmatter + chart, no closing ---
    assert "pink, warm and sweet" in chart_only and "Objectives" not in chart_only
    p.write_text(chart_only, encoding="utf-8")
    result = isx.audit_note(p, isx.deck_files(), isx.embed_index())
    assert result.sections == [] and result.skipped == "no body"
    p.write_text(NOTE.split("\n---\n")[0] + "\n", encoding="utf-8")   # frontmatter never closed
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
    assert data[0]["warnings"] == [] and data[0]["match"] == "title match"
    assert data[0]["deck_stats"][0]["pages"] == 4 and data[0]["deck_stats"][0]["counted"] == 2


def test_one_heading_level_keeps_plain_lines_as_text():
    body = ["# Only", "a plain line about thyroid hormone", "# Next", "another plain line"]
    secs = isx.sections(body, 10, lambda n: "")
    assert [s.heading for s in secs] == ["Only", "Next"]
    assert all(s.children == [] for s in secs)
    assert "thyroid hormone" in secs[0].text and secs[1].line == 12


NEONATAL = "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf"
FETUS = "Approach to the Small Fetus slides.pdf"
STEM = "09 - Approach to Neonatal Care"


def audit(root):
    return isx.audit_note(note_path(root), isx.deck_files(), isx.embed_index())


def test_clean_deck_raises_no_warning(vault):
    result = audit(vault)
    assert result.warnings == [] and result.match == "title match"
    st = result.deck_stats[0]
    assert (st.pages, st.counted, st.problem) == (4, 2, "")
    assert st.mean_terms == pytest.approx((9 + 14) / 2)


def test_dense_deck_warns(vault, monkeypatch):
    page = " ".join(f"term{i:03d}" for i in range(200))
    monkeypatch.setattr(isx, "deck_pages", lambda path: list(SLIDES) + [page, page])
    assert "dense" in audit(vault).warnings


def test_sparse_deck_warns(vault, monkeypatch):
    monkeypatch.setattr(isx, "deck_pages", lambda path: list(SLIDES) + [""] * 6)
    result = audit(vault)
    assert result.warnings == ["sparse"]
    assert {s.verdict for s in result.flat()} == {"slides", "inherited"}   # verdicts kept


def test_near_threshold_is_a_section_flag_and_partial_a_note_warning(vault, monkeypatch, tmp_path):
    monkeypatch.setattr(isx, "PARTIAL", {STEM: "only part of the lecture's decks"})
    result = audit(vault)
    assert result.warnings == ["partial"]
    assert all(s.flags == [] for s in result.flat())
    monkeypatch.setattr(isx, "NEAR_THRESHOLD", 0.0)
    result = audit(vault)
    assert result.warnings == ["partial"]                 # never a note-level warning
    by = {s.heading: s for s in result.flat()}
    assert by["Neonatal Resuscitation"].flags == ["near-threshold"]   # inherited, score 0.0
    assert by["Apgar Score"].flags == [] and by["Thin"].flags == []   # taught; thin has no score
    out = tmp_path / "build" / "near.json"
    isx.write_json([result], out)
    secs = {s["heading"]: s for s in json.loads(out.read_text(encoding="utf-8"))[0]["sections"]}
    assert secs["Neonatal Resuscitation"]["flags"] == ["near-threshold"] and secs["Apgar Score"]["flags"] == []


def test_missing_override_name_is_reported(vault, monkeypatch):
    monkeypatch.setattr(isx, "DECKS", {STEM: [NEONATAL, "Gone.pdf"]})
    result = audit(vault)
    assert result.deck_label == f"{NEONATAL} (missing: Gone.pdf)"
    assert result.match == "override" and "missing-deck" in result.warnings
    assert {s.verdict for s in result.flat()} == {"slides", "inherited"}
    monkeypatch.setattr(isx, "DECKS", {STEM: ["Gone.pdf"]})
    result = audit(vault)
    assert result.deck_label == "no deck found (missing: Gone.pdf)"
    assert result.warnings == ["missing-deck"] and {s.verdict for s in result.flat()} == {"no-deck"}


def test_unusable_deck_is_dropped_and_the_rest_scored(vault, monkeypatch):
    monkeypatch.setattr(isx, "DECKS", {STEM: [NEONATAL, FETUS]})
    monkeypatch.setattr(isx, "deck_pages", lambda path: list(SLIDES) if path.name == NEONATAL else ["", " "])
    result = audit(vault)
    assert result.deck_label == f"{NEONATAL} (no usable text: {FETUS})"
    assert [p.name for p in result.decks] == [NEONATAL]
    by = {s.heading: s for s in result.flat()}
    assert by["Apgar Score"].verdict == "slides" and by["Neonatal Resuscitation"].verdict == "inherited"
    assert "unusable-deck" in result.warnings


def test_unreadable_deck_is_named(vault, monkeypatch):
    def pages(path):
        if path.name == FETUS:
            raise RuntimeError(f"cannot open {path.name}: broken")
        return list(SLIDES)
    monkeypatch.setattr(isx, "DECKS", {STEM: [NEONATAL, FETUS]})
    monkeypatch.setattr(isx, "deck_pages", pages)
    result = audit(vault)
    assert result.deck_label == f"{NEONATAL} (unreadable: cannot open {FETUS}: broken)"


def test_deck_pages_reads_the_cache_until_the_file_changes(tmp_path, monkeypatch):
    import pymupdf
    deck = tmp_path / "d.pdf"
    deck.write_bytes(b"x")
    monkeypatch.setattr(isx, "CACHE_DIR", tmp_path / "cache")
    calls = []

    class Page:
        def get_text(self):
            return "alpha beta"

    class Doc:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def __iter__(self):
            return iter([Page(), Page()])

    def fake_open(path):
        calls.append(path)
        return Doc()

    monkeypatch.setattr(pymupdf, "open", fake_open)
    assert isx.deck_pages(deck) == ["alpha beta", "alpha beta"]
    assert isx.deck_pages(deck) == ["alpha beta", "alpha beta"]
    assert len(calls) == 1
    assert (tmp_path / "cache" / "deck_text" / "d.pdf.json").exists()
    os.utime(deck, ns=(1, 1))
    isx.deck_pages(deck)
    assert len(calls) == 2


def test_embed_index_is_cached_and_rebuilt_once_on_a_miss(vault, monkeypatch):
    walk = isx._walk_vault
    first = isx.embed_index()

    def no_walk():
        raise AssertionError("walked the vault")

    monkeypatch.setattr(isx, "_walk_vault", no_walk)
    second = isx.embed_index()
    assert second["neonatal sepsis"] == first["neonatal sepsis"]
    (vault / "00 - Medications" / "late note.md").write_text("chorioamnionitis late", encoding="utf-8")
    monkeypatch.setattr(isx, "_walk_vault", walk)
    assert "chorioamnionitis" in isx.embed_text("late note", second)
    monkeypatch.setattr(isx, "_walk_vault", no_walk)
    assert isx.embed_text("no such note", second) == ""        # one rebuild per run, not per miss
