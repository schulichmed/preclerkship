# -*- coding: utf-8 -*-
"""
Purpose: pin that mark_inherited.py writes the Inherited callout once, under the right headings,
         and only where the note has no warning and the section is not near the threshold
Author: Noor Sims
Date: 2026-10-06
Input: the synthetic vault from test_inherited_sections (no real PDF)
Output: pytest results
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))      # the synthetic vault fixture
import inherited_sections as isx  # noqa: E402
import mark_inherited as mi  # noqa: E402
from test_inherited_sections import vault, note_path  # noqa: E402,F401

CALLOUT = ("> [!warning] Inherited\n"
           "> Not in this year's slides (Approach to Neonatal Care Online Module Cheng Aug 2025.pdf). "
           "Kept for reference; not examinable this year unless the lecture says otherwise.")
STEM = "09 - Approach to Neonatal Care"


def test_marks_inherited_top_sections_and_inherited_children_only(vault):
    n = mi.mark("repro", dry=False)
    text = note_path(vault).read_text(encoding="utf-8")
    assert n == 2
    assert "# Neonatal Resuscitation\n" + CALLOUT + "\n\nVentilation" in text
    assert "#### Neonatal Sepsis\n" + CALLOUT + "\n\n![[neonatal sepsis]]" in text
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


def test_warned_note_is_skipped_and_listed(vault, monkeypatch, capsys):
    monkeypatch.setattr(isx, "PARTIAL", {STEM: "only part of the lecture's decks"})
    before = note_path(vault).read_bytes()
    assert mi.mark("repro", dry=False) == 0
    assert note_path(vault).read_bytes() == before
    out = capsys.readouterr().out
    assert f"skipped: note warning partial: {STEM}: Neonatal Resuscitation" in out
    assert f"skipped: note warning partial: {STEM}: Neonatal Sepsis" in out


def test_near_threshold_section_is_skipped_and_listed(vault, monkeypatch, capsys):
    monkeypatch.setattr(isx, "NEAR_THRESHOLD", 0.0)       # every scored inherited section is flagged
    before = note_path(vault).read_bytes()
    assert mi.mark("repro", dry=True) == 0
    assert note_path(vault).read_bytes() == before
    out = capsys.readouterr().out
    assert f"skipped: near-threshold: {STEM}: Neonatal Resuscitation" in out
    assert "would mark" not in out


def write_sections(vault, tmp_path, edit=None):
    """Write the live audit as JSON, optionally editing the records first."""
    out = tmp_path / "build" / "repro.json"
    isx.write_json([isx.audit_note(note_path(vault), isx.deck_files(), isx.embed_index())], out)
    if edit:
        data = json.loads(out.read_text(encoding="utf-8"))
        edit(data)
        out.write_text(json.dumps(data), encoding="utf-8")
    return out


def test_reads_the_saved_json_without_reading_decks(vault, tmp_path, monkeypatch):
    sections = write_sections(vault, tmp_path)

    def no_decks(path):
        raise AssertionError("read a deck")

    monkeypatch.setattr(isx, "deck_pages", no_decks)
    assert mi.mark("repro", dry=False, sections=sections) == 2
    text = note_path(vault).read_text(encoding="utf-8")
    assert "# Neonatal Resuscitation\n" + CALLOUT + "\n\nVentilation" in text
    assert mi.mark("repro", dry=True, sections=sections) == 0     # stale line numbers still found


def test_json_gate_reads_warnings_and_flags(vault, tmp_path, capsys):
    def flag_resuscitation(data):
        for s in data[0]["sections"]:
            if s["heading"] == "Neonatal Resuscitation":
                s["flags"] = ["near-threshold"]
    sections = write_sections(vault, tmp_path, flag_resuscitation)
    assert mi.mark("repro", dry=True, sections=sections) == 1
    assert f"skipped: near-threshold: {STEM}: Neonatal Resuscitation" in capsys.readouterr().out

    def warn(data):
        data[0]["warnings"] = ["dense"]
    sections = write_sections(vault, tmp_path, warn)
    assert mi.mark("repro", dry=True, sections=sections) == 0


def test_older_json_without_warnings_or_flags_counts_as_clean(vault, tmp_path):
    def strip(data):
        del data[0]["warnings"]
        for s in data[0]["sections"]:
            del s["flags"]
    sections = write_sections(vault, tmp_path, strip)
    assert mi.mark("repro", dry=True, sections=sections) == 2


def test_callout_already_below_a_blank_line_is_not_doubled(vault):
    p = note_path(vault)
    text = p.read_text(encoding="utf-8").replace(
        "# Neonatal Resuscitation\n", "# Neonatal Resuscitation\n\n" + CALLOUT + "\n")
    p.write_text(text, encoding="utf-8")
    assert mi.mark("repro", dry=False) == 1                       # only Neonatal Sepsis
    assert p.read_text(encoding="utf-8").count("> [!warning] Inherited") == 2


def test_a_heading_left_out_by_the_reader_is_not_marked(vault, capsys):
    assert mi.mark("repro", dry=False, leave_out={"Neonatal Resuscitation"}) == 1
    text = note_path(vault).read_text(encoding="utf-8")
    assert "# Neonatal Resuscitation\n> [!warning]" not in text
    assert "#### Neonatal Sepsis\n" + CALLOUT in text
    assert f"skipped: left out by reader: {STEM}: Neonatal Resuscitation" in capsys.readouterr().out


def crafted(tmp_path, body):
    """A one-section note and its record, for the insertion-point tests."""
    note = tmp_path / "note.md"
    note.write_text(body, encoding="utf-8")
    rec = {"note": "note", "path": note, "decks": ["Deck.pdf"], "deck_label": "Deck.pdf", "warnings": [],
           "sections": [{"level": 1, "heading": "Old", "line": 0, "verdict": "inherited",
                         "flags": [], "parent": None}]}
    return note, rec


def test_existing_callout_under_the_heading_is_kept_apart(tmp_path):
    note, rec = crafted(tmp_path, "# Old\n> [!note] Keep me\n> body\n")
    assert mi.mark_note(rec, dry=False) == 1
    text = note.read_text(encoding="utf-8")
    assert text.startswith("# Old\n> [!warning] Inherited\n> Not in this year's slides (Deck.pdf).")
    assert "otherwise.\n\n> [!note] Keep me\n> body\n" in text
    assert mi.mark_note(rec, dry=False) == 0


def test_heading_straight_after_gets_no_blank_line(tmp_path):
    note, rec = crafted(tmp_path, "# Old\n## Child\ntext\n")
    mi.mark_note(rec, dry=False)
    assert "otherwise.\n## Child\ntext\n" in note.read_text(encoding="utf-8")


def test_blank_line_already_there_is_not_doubled(tmp_path):
    note, rec = crafted(tmp_path, "# Old\n\ntext\n")
    mi.mark_note(rec, dry=False)
    assert "otherwise.\n\ntext\n" in note.read_text(encoding="utf-8")


SEPSIS = f"{STEM}: Neonatal Sepsis"


def test_include_marks_a_near_threshold_section(vault, monkeypatch, capsys):
    monkeypatch.setattr(isx, "NEAR_THRESHOLD", 0.0)       # every scored inherited section is flagged
    assert mi.mark("repro", dry=True, include={SEPSIS}) == 1
    out = capsys.readouterr().out
    assert f"included: {SEPSIS}" in out
    assert f"would mark {SEPSIS}" in out
    assert f"skipped: near-threshold: {STEM}: Neonatal Resuscitation" in out
    assert mi.mark("repro", dry=False, include={SEPSIS}) == 1
    text = note_path(vault).read_text(encoding="utf-8")
    assert "#### Neonatal Sepsis\n" + CALLOUT + "\n\n![[neonatal sepsis]]" in text
    assert "# Neonatal Resuscitation\n> [!warning]" not in text


def test_include_passes_a_warned_note_and_stays_idempotent(vault, monkeypatch, capsys):
    monkeypatch.setattr(isx, "PARTIAL", {STEM: "only part of the lecture's decks"})
    assert mi.mark("repro", dry=False, include={SEPSIS}) == 1
    before = note_path(vault).read_bytes()
    capsys.readouterr()
    assert mi.mark("repro", dry=False, include={SEPSIS}) == 0
    assert note_path(vault).read_bytes() == before
    out = capsys.readouterr().out
    assert f"included: {SEPSIS}" in out
    assert f"skipped: note warning partial: {STEM}: Neonatal Resuscitation" in out


def test_include_naming_nothing_is_reported(vault, capsys):
    mi.mark("repro", dry=True, include={f"{STEM}: Apgar Score", "Nope: Nothing"})
    out = capsys.readouterr().out
    assert f"include matched nothing: {STEM}: Apgar Score" in out    # taught, not inherited
    assert "include matched nothing: Nope: Nothing" in out


def test_leave_out_wins_over_include(vault, capsys):
    assert mi.mark("repro", dry=True, include={SEPSIS}, leave_out={SEPSIS}) == 1
    assert f"skipped: left out by reader: {SEPSIS}" in capsys.readouterr().out
