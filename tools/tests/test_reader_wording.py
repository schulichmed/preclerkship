# -*- coding: utf-8 -*-
"""
Purpose: keep maintainer vocabulary out of what readers see - no "vault" in shipped question,
         note or Anki JSON, nor in the explanation and pairing sources that merge into it
Author: Noor Sims
Date: 2026-10-09
Input: */data/*/*.json, tools/explanations/*.json, tools/pairings/*.json
Output: pytest results
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHIPPED = sorted(
    list(ROOT.glob("*/data/*/*.json"))
    + list((ROOT / "tools" / "explanations").glob("*.json"))
    + list((ROOT / "tools" / "pairings").glob("*.json"))
)
# "vaginal vault" is anatomy, not the medwiki vault
VAULT_WORD = re.compile(r"(?<!vaginal )\bvault\b", re.I)


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_vault_wording(path: Path) -> None:
    """Readers do not know what the vault is (issue #43); say "the notes" instead."""
    text = path.read_text(encoding="utf-8")
    hits = [text[max(0, m.start() - 50): m.end() + 30] for m in VAULT_WORD.finditer(text)]
    assert not hits, f"{len(hits)} reader-facing 'vault': {hits[:3]}"


# Restored module, case-based and assessment questions (2026-10-19) are framed as
# student notes from modules, in-class sessions and small-group sessions, so what a
# reader sees names no session format or platform. qid, source, family and the hidden
# lectureMeta / refiled / offCurriculum provenance keep the old words as join keys.
COURSE_MATERIAL = re.compile(r"\bDSSGs?\b|Elentra|\bRise (?:module|export)|\bCHSG\b", re.I)
READER_FIELDS = ("stem", "preamble", "options", "answer", "answerTitle", "flags", "pairs",
                 "review", "lecture", "weekLabel", "sourceLabel", "tags")
QUESTION_FILES = sorted(ROOT.glob("*/data/questions/*.json"))


@pytest.mark.parametrize("path", QUESTION_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_course_material_names(path: Path) -> None:
    """Questions read as student notes, not as named course material."""
    hits = []
    for q in json.loads(path.read_text(encoding="utf-8")):
        text = json.dumps({k: q.get(k) for k in READER_FIELDS}, ensure_ascii=False)
        hits += [f"{q['qid']}: {m.group(0)}" for m in COURSE_MATERIAL.finditer(text)]
    assert not hits, f"{len(hits)} reader-facing course-material names: {hits[:5]}"
