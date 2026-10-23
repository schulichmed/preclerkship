# -*- coding: utf-8 -*-
"""
Purpose: catch a key that gives itself away by length - an MCQ whose correct option is
         conspicuously longer than every distractor (issue #94)
Author: Noor Sims
Date: 2026-10-11
Input: the question banks listed in CHECKED
Output: pytest results
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Banks already swept. Add a bank here once its tells are fixed; the others still carry some.
CHECKED = ["pom2/data/questions/endo.json", "pom2/data/questions/repro.json"]
# A key at least this many times the longest distractor, and this many characters longer, is a tell
LENGTH_RATIO = 1.5
MIN_EXTRA_CHARS = 20
TAG = re.compile(r"<[^>]+>")


def option_length(html: str) -> int:
    """Visible length of an option, markup stripped."""
    return len(TAG.sub("", html or "").strip())


def length_tells(questions: list[dict]) -> list[str]:
    """Return 'qid (key n chars vs longest distractor m)' for every single-key MCQ whose key is a tell."""
    tells = []
    for q in questions:
        options = q.get("options") or []
        correct = q.get("correct") or []
        if q.get("retired") or q.get("kind") != "mcq" or len(correct) != 1 or len(options) < 3:
            continue
        lengths = {o["letter"]: option_length(o["html"]) for o in options}
        key = correct[0]
        if key not in lengths:
            continue
        longest_other = max(n for letter, n in lengths.items() if letter != key)
        if lengths[key] >= LENGTH_RATIO * longest_other and lengths[key] - longest_other >= MIN_EXTRA_CHARS:
            tells.append(f"{q['qid']} (key {lengths[key]} chars vs {longest_other})")
    return tells


@pytest.mark.parametrize("bank", CHECKED)
def test_key_is_not_conspicuously_longest(bank: str) -> None:
    """The medicine, not the formatting, should pick the key out of the set."""
    questions = json.loads((ROOT / bank).read_text(encoding="utf-8"))
    tells = length_tells(questions)
    assert not tells, f"{len(tells)} keys give themselves away by length: {tells}"
