# -*- coding: utf-8 -*-
"""
Purpose: pin how slides_shortlist.py picks the questions to read against the deck
Author: Noor Sims
Date: 2026-10-06
Input: a synthetic bank, verdict files, vault and saved section records built in tmp_path (no real PDF)
Output: pytest results
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))      # the neonatal fixtures below
import curriculum_audit as ca  # noqa: E402
import inherited_sections as isx  # noqa: E402
import slides_shortlist as ss  # noqa: E402
from test_inherited_sections import NOTE, SEPSIS, SLIDES  # noqa: E402

DECK = "Approach to Neonatal Care Online Module Cheng Aug 2025.pdf"


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
    (decks / DECK).write_bytes(b"")
    repro = [question("hippo-repro-Q1", "Approach to Neonatal Care"),
             question("hippo-repro-Q2", "Approach to Neonatal Care"),
             question("hippo-repro-Q3", "Lactation", n="07"),
             question("module-repro-Q4", "Approach to Neonatal Care", family="module"),
             question("hippo-repro-Q5", "Approach to Neonatal Care", family="offcurriculum"),
             question("reviews-repro-Q6", "Approach to Neonatal Care", family="reviews")]
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
    # live workbook and HippoNotes only: module, off-curriculum and reviews are left out
    assert set(by) == {"hippo-repro-Q1", "hippo-repro-Q2", "hippo-repro-Q3"}
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
    assert by["hippo-repro-Q2"]["slides"] == DECK
    assert [r["qid"] for r in prefill] == ["hippo-repro-Q1", "hippo-repro-Q2", "hippo-repro-Q3"]


def test_dump_lists_only_the_shortlist(world):
    text = ss.dump(ss.shortlist("repro"))
    assert "hippo-repro-Q2" in text and "Stem of hippo-repro-Q2" in text
    assert "hippo-repro-Q1" not in text and "hippo-repro-Q3" not in text
    assert "chorioamnionitis" in text          # the earlier evidence is shown for the reader
    assert DECK in text


def test_unnumbered_review_entry_resolves_to_its_note(world):
    week = ca.LECTURE_NOTES / "02 - Repro/Week 6"
    (week / "In-Class - Amenorrhea.md").write_text("---\n---\nchart\n", encoding="utf-8")
    q = question("workbook-repro-Q7", "Amenorrhea", family="workbook")
    q["review"] = [{"w": 6, "n": "", "t": "In-Class - Amenorrhea"}]
    note, against, week_no = ss.resolve_note(q)
    assert note == week / "In-Class - Amenorrhea.md"
    assert against == "In-Class - Amenorrhea" and week_no == 6


def saved_records() -> list[dict]:
    """Records in inherited_sections.write_json's shape. Apgar Score is marked
    inherited here although the slides teach it, so a test can tell the saved
    verdicts from rescored ones."""
    lines = NOTE.split("\n")

    def line(heading):
        return next(k for k, ln in enumerate(lines) if ln.startswith("#") and ln.lstrip("#").strip() == heading)

    def sec(level, heading, verdict, parent=None):
        return {"level": level, "heading": heading, "line": line(heading), "words": 10,
                "score": 0.1, "verdict": verdict, "parent": parent}

    return [
        {"note": "09 - Approach to Neonatal Care", "week": "Week 6", "decks": [DECK], "deck_label": DECK,
         "skipped": "", "sections": [
             sec(1, "Neonatal Resuscitation", "inherited"), sec(1, "Apgar Score", "inherited"),
             sec(1, "Extra Care for the Neonate", "slides"),
             sec(4, "Neonatal Sepsis", "inherited", "Extra Care for the Neonate"),
             sec(4, "Hypoglycemia", "slides", "Extra Care for the Neonate"),
             sec(4, "Thin", "slides", "Extra Care for the Neonate")]},
        {"note": "07 - Lactation", "week": "Week 6", "decks": [], "deck_label": "no deck found",
         "skipped": "", "sections": []},
    ]


def test_saved_records_give_the_section_verdicts_without_rescoring(world, monkeypatch):
    def no_audit(*_a, **_k):
        raise AssertionError("audit_note must not run when the saved records cover the note")
    monkeypatch.setattr(isx, "audit_note", no_audit)
    rows = ss.shortlist("repro", records=saved_records())
    by = {r["qid"]: r for r in rows}
    assert by["hippo-repro-Q1"]["section"] == "Apgar Score"
    assert by["hippo-repro-Q1"]["section_verdict"] == "inherited"      # from the records, not rescored
    assert by["hippo-repro-Q1"]["status"] == "SHORTLIST"
    assert by["hippo-repro-Q1"]["evidence_score"] >= ss.EVIDENCE_AT   # still checked against the deck text
    assert by["hippo-repro-Q2"]["section"] == "Neonatal Sepsis" and by["hippo-repro-Q2"]["deck"] == DECK
    assert by["hippo-repro-Q3"]["status"] == "NO-DECK"


def test_saved_records_read_each_deck_once(world, monkeypatch):
    calls = []
    monkeypatch.setattr(isx, "deck_pages", lambda path: calls.append(path.name) or list(SLIDES))
    ss.shortlist("repro", records=saved_records())
    assert calls == [DECK]


def add_question(root, qid, quote, n="09", lecture="Approach to Neonatal Care"):
    """Append a HippoNotes question to the bank with one earlier evidence quote."""
    bank = root / "pom2/data/questions/repro.json"
    qs = json.loads(bank.read_text(encoding="utf-8"))
    qs.append(question(qid, lecture, n=n))
    bank.write_text(json.dumps(qs), encoding="utf-8")
    extra = root / "build/curriculum_audit/repro_w6b.json"
    rows = json.loads(extra.read_text(encoding="utf-8")) if extra.exists() else []
    rows.append({"qid": qid, "verdict": "current", "against": f"{n} - {lecture}", "week": 6,
                 "evidence": quote, "note": ""})
    extra.write_text(json.dumps(rows), encoding="utf-8")


def slides_with(monkeypatch, *pages):
    """The neonatal slides plus extra pages, so a quote's terms are on the deck."""
    monkeypatch.setattr(isx, "deck_pages", lambda path: list(SLIDES) + list(pages))


def test_quote_split_between_slides_parent_and_inherited_child_is_shortlisted(world, monkeypatch):
    # "babies" and "care" are the parent's own text; the other three sit in the inherited child
    quote = "babies care chorioamnionitis maternal streptococcus"
    add_question(world, "hippo-repro-Q8", quote)
    slides_with(monkeypatch, quote)
    by = {r["qid"]: r for r in ss.shortlist("repro", records=saved_records())}
    q8 = by["hippo-repro-Q8"]
    assert q8["evidence_score"] >= ss.EVIDENCE_AT                  # on the deck as a bag of words
    assert q8["section"] == "Neonatal Sepsis" and q8["section_verdict"] == "inherited"
    assert q8["status"] == "SHORTLIST"


def test_quote_half_in_an_inherited_child_is_shortlisted_below_section_at(world, monkeypatch):
    # four terms are the slides parent's own text, four sit in the inherited child: the child
    # holds 0.5, under SECTION_AT, so the quote lands on the parent at 1.0
    quote = "babies need extra care chorioamnionitis maternal group streptococcus"
    add_question(world, "hippo-repro-Q13", quote)
    slides_with(monkeypatch, quote)
    by = {r["qid"]: r for r in ss.shortlist("repro", records=saved_records())}
    q13 = by["hippo-repro-Q13"]
    assert q13["section"] == "Extra Care for the Neonate" and q13["section_verdict"] == "slides"
    assert q13["inherited_share"] == 0.5
    assert q13["status"] == "SHORTLIST"


def test_quote_in_no_section_passes_only_when_the_chart_holds_it(world, monkeypatch):
    add_question(world, "hippo-repro-Q9", "every newborn kept pink, warm and sweet")
    add_question(world, "hippo-repro-Q10", "phototherapy threshold kernicterus nomogram")
    slides_with(monkeypatch, "newborn kept pink warm sweet",
                "phototherapy threshold kernicterus nomogram")
    by = {r["qid"]: r for r in ss.shortlist("repro", records=saved_records())}
    assert by["hippo-repro-Q9"]["section"] == "" and by["hippo-repro-Q9"]["chart_share"] >= ss.CHART_AT
    assert by["hippo-repro-Q9"]["status"] == "ok"
    assert by["hippo-repro-Q10"]["section"] == "" and by["hippo-repro-Q10"]["chart_share"] < ss.CHART_AT
    assert by["hippo-repro-Q10"]["status"] == "SHORTLIST"


def test_section_missing_from_the_records_is_named_and_shortlisted(world, monkeypatch, capsys):
    records = saved_records()
    records[0]["sections"] = [s for s in records[0]["sections"] if s["heading"] != "Hypoglycemia"]
    quote = "jittery irritable lethargic poor feeding intravenous dextrose"
    add_question(world, "hippo-repro-Q11", quote)
    slides_with(monkeypatch, quote)
    by = {r["qid"]: r for r in ss.shortlist("repro", records=records)}
    assert by["hippo-repro-Q11"]["section"] == "Hypoglycemia"
    assert by["hippo-repro-Q11"]["status"] == "SHORTLIST"
    assert "09 - Approach to Neonatal Care / Hypoglycemia" in capsys.readouterr().err


def test_record_deck_not_on_disk_is_named(world, capsys):
    records = saved_records()
    records[0]["decks"] = ["gone.pdf", DECK]
    by = {r["qid"]: r for r in ss.shortlist("repro", records=records)}
    assert by["hippo-repro-Q1"]["deck"] == DECK and by["hippo-repro-Q1"]["status"] != "NO-DECK"
    assert "gone.pdf" in capsys.readouterr().err


def test_unusable_extra_deck_in_the_label_still_checks_the_good_deck(world):
    records = saved_records()
    records[0]["deck_label"] = f"{DECK} (no usable text: bad.pdf)"
    by = {r["qid"]: r for r in ss.shortlist("repro", records=records)}
    assert by["hippo-repro-Q1"]["deck"] == DECK
    assert by["hippo-repro-Q1"]["status"] != "NO-DECK" and by["hippo-repro-Q1"]["evidence_score"] >= ss.EVIDENCE_AT


def test_question_with_no_note_is_prefilled_no_deck(world):
    add_question(world, "hippo-repro-Q12", "anything", n="99", lecture="Not A Note")
    rows = ss.shortlist("repro")
    q12 = next(r for r in rows if r["qid"] == "hippo-repro-Q12")
    assert q12["status"] == "NO-NOTE"
    row = next(r for r in ss.prefill(rows) if r["qid"] == "hippo-repro-Q12")
    assert row["verdict"] == "current" and row["note"] == "NO-DECK" and row["slides"] == ""


def test_load_records_missing_file_is_none(tmp_path):
    assert ss.load_records(tmp_path / "nope.json") is None
    path = tmp_path / "repro.json"
    path.write_text(json.dumps(saved_records()), encoding="utf-8")
    assert ss.load_records(path)[0]["note"] == "09 - Approach to Neonatal Care"
