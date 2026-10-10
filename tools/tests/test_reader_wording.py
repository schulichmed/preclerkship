# -*- coding: utf-8 -*-
"""
Purpose: keep maintainer vocabulary out of what readers see - no "vault" in shipped question,
         note or Anki JSON, nor in the explanation and pairing sources that merge into it
Author: Noor Sims
Date: 2026-10-09
Input: */data/*/*.json, tools/explanations/*.json, tools/pairings/*.json
Output: pytest results
"""
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
