# -*- coding: utf-8 -*-
"""
Purpose: keep the explanation-to-note links (tools/note_links.py) honest - every
         link points at a lecture that has a note, names words the explanation
         really has, and is never a bare everyday word
Author: Ashish Saragadam
Date: 2026-10-16
Input: every course's data/questions/*.json and data/notes/*.json
Output: pytest results
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import note_links  # noqa: E402
import portal  # noqa: E402

BANKS = [(c, slug) for c in portal.COURSES for slug, *_ in c["blocks"]
         if (ROOT / c["slug"] / "data" / "questions" / (slug + ".json")).exists()]


def noted(course):
    """Every lecture a link may open: its own note, or the one covering it."""
    return {lec["id"]: (slug, w) for slug, w, lec in note_links.lectures(course, every=True)
            if lec.get("hasNote") is True or lec.get("coveredBy")}


@pytest.mark.parametrize("course,slug", BANKS, ids=["%s/%s" % (c["slug"], s) for c, s in BANKS])
def test_links_land(course, slug):
    notes = noted(course)
    qs = json.loads((ROOT / course["slug"] / "data" / "questions" / (slug + ".json")).read_text("utf-8"))
    for q in qs:
        terms = q.get("noteTerms") or []
        assert len(terms) <= note_links.MAX_LINKS, q["qid"]
        runs = [r for r, _wl in note_links.text_runs(q.get("answer"))]
        for text, block, lid, week, bold in terms:
            assert lid in notes, "%s links %s, which has no note" % (q["qid"], lid)
            assert notes[lid] == (block, week), q["qid"]
            assert any(text in r for r in runs), "%s: %r is not in its explanation" % (q["qid"], text)
            assert bold.lower() not in note_links.STOP, q["qid"]


def test_everyday_words_stay_plain():
    assert note_links.everyday(["Next", "step"])
    assert note_links.everyday(["Principle"])
    assert note_links.everyday(["Excludes"])
    assert not note_links.everyday(["thyroiditis"])
    assert not note_links.is_acronym("LOW")
    assert note_links.is_acronym("GLP-1")


def test_wiki_links_name_their_lecture():
    titles = {"abnormal uterine bleeding": [("repro", "repro-w4-15", 4, "15")]}
    q = {"answer": '<p>See <span class="wl">15 - Abnormal Uterine Bleeding</span>.</p>'}
    assert note_links.link_question(q, "repro", {}, {}, {}, titles) == [
        ["15 - Abnormal Uterine Bleeding", "repro", "repro-w4-15", 4, ""]]


def test_never_across_punctuation():
    index = {note_links.key_of(["fetal", "well-being"], False): {"surface": "fetal well-being",
                                                               "homes": {("b1", "b1-w1-01"): 1}}}
    q = {"answer": "<p>Assessment of fetal “well-being” by BPP.</p>"}
    assert note_links.link_question(q, "b1", index, {"b1-w1-01": 1}) == []
    q = {"answer": "<p>Assessment of fetal well-being by BPP.</p>"}
    assert note_links.link_question(q, "b1", index, {"b1-w1-01": 1})[0][0] == "fetal well-being"


def test_a_split_lecture_counts_as_reviewed():
    """A question that reviews "07.2" has reviewed msk-w8-07.2, so a
    one-word term it uses stays with that lecture instead of drifting to another."""
    week = {"msk-w8-07.2": 8, "msk-w8-07.1": 8, "msk-w8-07": 8}
    q = {"review": [{"w": 8, "n": "07.2", "t": "Clinical Approach"}]}
    assert note_links.reviewed_ids(q, week) == {"msk-w8-07.2"}


def test_a_one_word_term_stays_in_the_reviewed_week():
    """"orthosis" is bold in a lecture two weeks on; a cubital tunnel answer
    that reviews week 8 must not link there."""
    entry = {"surface": "orthosis", "homes": {("msk", "msk-w10-01.2"): 1}}
    near = lambda lid: lid.startswith("msk-w8")  # noqa: E731
    assert note_links.home(entry, "msk", {"msk-w8-07.2"}, True, near) is None
    assert note_links.home(entry, "msk", {"msk-w8-07.2"}, True) == ("msk", "msk-w10-01.2")
