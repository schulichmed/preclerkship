# -*- coding: utf-8 -*-
"""
Purpose: pin what curriculum_audit.py does with a `misfiled` verdict
Author: Noor Sims
Date: 2026-10-06
Input: temporary question banks and note rosters built in tmp_path
Output: pytest results
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import curriculum_audit as ca  # noqa: E402


def question(qid, week, label, lecture, family="hipponotes"):
    return {"qid": qid, "num": qid.rsplit("Q", 1)[1], "week": week, "weekLabel": label,
            "lecture": lecture, "lectureMeta": "x", "family": family, "source": "hippo",
            "sourceLabel": "HippoNotes", "stem": "<p>s</p>", "kind": "mcq",
            "options": [{"letter": "A", "html": "a"}], "correct": ["A"], "answer": "<p>a</p>",
            "flags": [], "tags": [], "review": [], "retired": False}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo with endo and repro banks, note rosters and a vault of two lectures."""
    root = tmp_path / "repo"
    (root / "pom2" / "data" / "questions").mkdir(parents=True)
    (root / "pom2" / "data" / "notes").mkdir(parents=True)
    endo = [question("hippo-endo-Q1", 2, "Week 2 - Thyroid", "Thyroid")]
    repro = [question("hippo-repro-Q47", 6, "Week 6 - Labour", "Labour"),
             question("hippo-repro-Q50", 6, "Week 6 - Labour", "Labour")]
    (root / "pom2/data/questions/endo.json").write_text(json.dumps(endo), encoding="utf-8")
    (root / "pom2/data/questions/repro.json").write_text(json.dumps(repro), encoding="utf-8")
    for slug, weeks in (("endo", [(2, "Week 2 - Thyroid"), (3, "Week 3 - Adrenal")]),
                        ("repro", [(5, "Week 5 - Pregnancy"), (6, "Week 6 - Labour")])):
        notes = {"block": slug, "weeks": [{"week": w, "label": lab, "lectures": []}
                                          for w, lab in weeks]}
        (root / f"pom2/data/notes/{slug}.json").write_text(json.dumps(notes), encoding="utf-8")
    vault = tmp_path / "vault" / "01 - Lectures" / "99 - PoM 2"
    (vault / "02 - Repro" / "Week 5").mkdir(parents=True)
    (vault / "02 - Repro" / "Week 5" / "11 - Approach to First Trimester Bleeding & Ultrasound.md").write_text("# x")
    (vault / "01 - Endocrinology" / "Week 3").mkdir(parents=True)
    (vault / "01 - Endocrinology" / "Week 3" / "01 - Adrenal Gland Disease.md").write_text("# x")
    monkeypatch.setattr(ca, "ROOT", root)
    monkeypatch.setattr(ca, "LECTURE_NOTES", vault)
    return root


def bank(root, slug):
    return json.loads((root / f"pom2/data/questions/{slug}.json").read_text(encoding="utf-8"))


def test_misfiled_rewrites_week_label_lecture_and_review(repo):
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
           "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    q = bank(repo, "repro")[0]
    assert q["week"] == 5
    assert q["weekLabel"] == "Week 5 - Pregnancy"
    assert q["lecture"] == "Approach to First Trimester Bleeding & Ultrasound"
    assert q["review"] == [{"w": 5, "n": "11", "t": "Approach to First Trimester Bleeding & Ultrasound"}]
    assert q["refiled"] == {"from": {"block": "repro", "week": 6, "lecture": "Labour"},
                            "on": "2026-10-06"}
    assert q["qid"] == "hippo-repro-Q47"


def test_misfiled_is_idempotent(repo, capsys):
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
           "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    before = (repo / "pom2/data/questions/repro.json").read_bytes()
    ca.apply_rows([row], checked="2026-10-07")
    assert (repo / "pom2/data/questions/repro.json").read_bytes() == before
    assert "already refiled   1" in capsys.readouterr().out


def test_misfiled_outside_block_moves_banks(repo):
    row = {"qid": "hippo-repro-Q50", "verdict": "misfiled", "week": 3,
           "against": "01 - Adrenal Gland Disease", "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    assert [q["qid"] for q in bank(repo, "repro")] == ["hippo-repro-Q47"]
    moved = [q for q in bank(repo, "endo") if q["qid"] == "hippo-repro-Q50"]
    assert len(moved) == 1
    assert moved[0]["week"] == 3 and moved[0]["weekLabel"] == "Week 3 - Adrenal"
    assert moved[0]["refiled"]["from"]["block"] == "repro"


def test_misfiled_unknown_lecture_is_refused(repo, capsys):
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "99 - No Such Lecture", "evidence": "", "note": ""}
    before = (repo / "pom2/data/questions/repro.json").read_bytes()
    ca.apply_rows([row], checked="2026-10-06")
    assert (repo / "pom2/data/questions/repro.json").read_bytes() == before
    assert "hippo-repro-Q47" in capsys.readouterr().err


def test_misfiled_does_not_touch_off_curriculum(repo):
    qs = bank(repo, "repro")
    qs[0]["family"] = "offcurriculum"
    qs[0]["offCurriculum"] = {"reason": "retired", "from": "hipponotes", "against": "x",
                              "checked": "2026-10-05"}
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
           "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    assert bank(repo, "repro")[0]["week"] == 6


def test_report_counts_review_week_disagreement_and_week_titles(repo, capsys):
    qs = bank(repo, "repro")
    qs[0]["review"] = [{"w": 5, "n": "11", "t": "Approach to First Trimester Bleeding & Ultrasound"}]
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    ca.report()
    out = capsys.readouterr().out
    assert "misfiled 1: hippo-repro-Q47" in out
    assert "lecture is the week title 2: hippo-repro-Q47, hippo-repro-Q50" in out


def test_candidates_names_both_reasons(repo, capsys):
    qs = bank(repo, "repro")
    qs[0]["review"] = [{"w": 5, "n": "11", "t": "Approach to First Trimester Bleeding & Ultrasound"}]
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    ca.candidates("pom2", "repro", None)
    out = capsys.readouterr().out
    assert "review week 5 != filed week 6" in out
    assert "lecture is the week title" in out


def test_misfiled_wrong_case_lecture_is_refused(repo, capsys, monkeypatch):
    """The real vault sits on a case-insensitive drive, so emulate one here."""
    real_exists = Path.exists

    def case_blind_exists(self):
        if real_exists(self):
            return True
        parent = self.parent
        return real_exists(parent) and parent.is_dir() and any(
            p.name.lower() == self.name.lower() for p in parent.iterdir())

    monkeypatch.setattr(Path, "exists", case_blind_exists)
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "11 - APPROACH TO FIRST TRIMESTER BLEEDING & ULTRASOUND",
           "evidence": "", "note": ""}
    before = (repo / "pom2/data/questions/repro.json").read_bytes()
    ca.apply_rows([row], checked="2026-10-06")
    assert (repo / "pom2/data/questions/repro.json").read_bytes() == before
    assert "hippo-repro-Q47" in capsys.readouterr().err


def test_misfiled_against_unnumbered_note(repo):
    """An In-Class note has no NN prefix; its review record carries n == "" and the whole stem."""
    week5 = ca.LECTURE_NOTES / "02 - Repro" / "Week 5"
    (week5 / "In-Class - Amenorrhea.md").write_text("# x")
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "In-Class - Amenorrhea", "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    q = bank(repo, "repro")[0]
    assert q["week"] == 5
    assert q["lecture"] == "In-Class - Amenorrhea"
    assert q["review"] == [{"w": 5, "n": "", "t": "In-Class - Amenorrhea"}]


def test_rerefile_keeps_original_from(repo):
    """A second refile to another lecture updates the filing but keeps where it first came from."""
    week5 = ca.LECTURE_NOTES / "02 - Repro" / "Week 5"
    (week5 / "09 - Pathology of 1st Trimester Bleeding.md").write_text("# x")
    first = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
             "against": "09 - Pathology of 1st Trimester Bleeding", "evidence": "", "note": ""}
    second = dict(first, against="11 - Approach to First Trimester Bleeding & Ultrasound")
    ca.apply_rows([first], checked="2026-10-06")
    ca.apply_rows([second], checked="2026-10-07")
    q = bank(repo, "repro")[0]
    assert q["lecture"] == "Approach to First Trimester Bleeding & Ultrasound"
    assert q["refiled"] == {"from": {"block": "repro", "week": 6, "lecture": "Labour"},
                            "on": "2026-10-07"}


def test_refiled_questions_join_their_new_week(repo):
    """A refile moves the question next to its new week's questions, so no heading repeats."""
    qs = [question("hippo-repro-Q40", 5, "Week 5 - Pregnancy", "Pregnancy"),
          question("hippo-repro-Q50", 6, "Week 6 - Labour", "Labour"),
          question("hippo-repro-Q47", 6, "Week 6 - Labour", "Labour"),
          question("hippo-repro-Q41", 5, "Week 5 - Pregnancy", "Pregnancy"),
          question("hippo-repro-Q48", 6, "Week 6 - Labour", "Labour")]
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    rows = [{"qid": qid, "verdict": "misfiled", "week": 5,
             "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
             "evidence": "", "note": ""} for qid in ("hippo-repro-Q48", "hippo-repro-Q47")]
    ca.apply_rows(rows, checked="2026-10-06")
    after = bank(repo, "repro")
    assert [q["qid"] for q in after] == ["hippo-repro-Q40", "hippo-repro-Q41", "hippo-repro-Q47",
                                         "hippo-repro-Q48", "hippo-repro-Q50"]
    weeks = [q["week"] for q in after]
    assert weeks == sorted(weeks)


def test_already_filed_there_is_not_refiled(repo, capsys):
    """A question its source already filed under the row's lecture gains no `refiled` record."""
    qs = bank(repo, "repro")
    rec = {"w": 5, "n": "11", "t": "Approach to First Trimester Bleeding & Ultrasound"}
    qs[0].update(week=5, weekLabel="Week 5 - Pregnancy", lecture=rec["t"], review=[rec])
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    ca.apply_rows([{"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
                    "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
                    "evidence": "", "note": ""}], checked="2026-10-06")
    assert "refiled" not in bank(repo, "repro")[0]
    assert "already refiled   1" in capsys.readouterr().out


def test_mark_vault_writes_refiled_marker_once(repo, tmp_path, monkeypatch, capsys):
    """A misfiled vault question gets a `refiled` comment, not a `set:` family marker."""
    qs = bank(repo, "repro") + [question("workbook-repro-Q5", 6, "Week 6 - Labour", "Labour",
                                         family="workbook")]
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    notes = tmp_path / "vault" / "00 - Practice Questions"
    (notes / "Preclerkship Workbook").mkdir(parents=True)
    note = notes / "Preclerkship Workbook" / "Preclerkship Workbook - Reproduction.md"
    note.write_text("# 4\nstem four\n\n# 5\nstem five\n", encoding="utf-8")
    monkeypatch.setattr(ca, "QUESTION_NOTES", notes)
    row = {"qid": "workbook-repro-Q5", "verdict": "misfiled", "week": 5,
           "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
           "evidence": "", "note": ""}
    ca.mark_vault([row], dry=False)
    lines = note.read_text(encoding="utf-8").split("\n")
    i = lines.index("# 5")
    assert lines[i + 1] == ("<!-- refiled | week: 5 | lecture: 11 - Approach to First Trimester "
                            "Bleeding & Ultrasound | qid: workbook-repro-Q5 -->")
    assert "set:" not in note.read_text(encoding="utf-8")
    assert "marked 1," in capsys.readouterr().out
    ca.mark_vault([row], dry=False)
    assert "marked 0, already marked 1" in capsys.readouterr().out


def test_refiled_question_takes_its_neighbours_week_label(repo):
    """Where its family already has a heading for the week, a refiled question uses that one."""
    qs = [question("hippo-repro-Q40", 5, "Week 5 - Older wording", "Pregnancy")] + bank(repo, "repro")
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    ca.apply_rows([{"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
                    "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
                    "evidence": "", "note": ""}], checked="2026-10-06")
    moved = [q for q in bank(repo, "repro") if q["qid"] == "hippo-repro-Q47"][0]
    assert moved["weekLabel"] == "Week 5 - Older wording"
