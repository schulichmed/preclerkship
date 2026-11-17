"""
Purpose: Build the breast clinical skills page (breast-exam/index.html) from the manoeuvre
         tables in the medwiki note "Summary Notes - Breast Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; clips.json
       (Health Education Media Library draping video); the Geeky Medics videos are set in EXAM.other_video
Output: breast-exam/index.html

The note is the single source of the steps and positive findings: edit the note,
then rerun this script. Which problem heading each manoeuvre sits under, and its
picture, are set here. How the page looks lives in clinical-skills/exam_page.py,
shared by every exam page. The drawn palpation diagrams come from make_diagrams.py.
"""

import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("exam_page", HERE.parent / "clinical-skills/exam_page.py")
exam_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exam_page)
VAULT = Path(os.environ.get("POM2_VAULT", "/mnt/c/Users/nsims/medwiki"))
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Breast Clinical Skills.md"
SESSION = "FoM · Breast Exam"

# section number in the note -> region on the page
REGIONS = {
    2: ("inspect", "Inspection", SESSION, "#3d6fb6"),
    3: ("palpate", "Palpating the breast", SESSION, "#a8366f"),
    4: ("axilla", "Axillary lymph nodes", SESSION, "#23798a"),
    5: ("male", "The male breast", SESSION, "#7d6413"),
}

# the note's opening section, shown as the first band
GENERAL = [(1, "The general approach")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Arms at sides": ("Anything visibly different", "arms-at-sides.jpg"),
    "Arms over head": ("Dimpling or a pull-in hidden at rest", "arms-over-head.jpg"),
    "Hands pressed on hips": ("Dimpling or a pull-in hidden at rest", "hands-pressed-on-hips.jpg"),
    "Leaning forward": ("Dimpling or a pull-in hidden at rest", None),
    "Lateral (outer) half": ("A lump in the breast tissue", "lateral-outer-half.jpg"),
    "Medial (inner) half": ("A lump in the breast tissue", "medial-inner-half.jpg"),
    "Nipple": ("Something under the nipple", None),
    "Mobility of a mass": ("What a lump is attached to", "mobility-of-a-mass.jpg"),
    "Axillary nodes": ("Spread to the nodes", "axillary-nodes.jpg"),
    "Male breast: inspect and palpate": ("A nodule in a man", "male-breast-inspect-palpate.jpg"),
    "Enlarged male breast": ("Fat, gland or cancer", "enlarged-male-breast.jpg"),
}

EXAM = exam_page.Exam(
    key="breast", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS,
    opening={
        "inspect": "I'd like to look at your breasts while you sit up, with your gown open to the waist. "
                   "I'll ask you to move your arms into a few positions. Is that all right?",
        "palpate": "Now I'd like to feel your breasts while you lie down. I'll cover one side while I examine the other, "
                   "and tell you before each step. Tell me if anything is tender, and I'll stop whenever you ask.",
        "axilla": "Last, I'd like to feel the lymph nodes under your arms, and above and below your collarbone. May I?",
        "male": "I'd like to look at and feel your chest and the tissue under your nipples. May I?",
    },
    h1="Breast exam",
    lead='Inspect, palpate the breast, then the axillary nodes.',
    find="Find a manoeuvre or a finding (e.g. dimpling, nipple)",
    root="Inspect, sitting → Palpate the breast, lying → Palpate the nipple → Axillary nodes",
    root_note="Compare one side with the other. Be systematic (the same pattern every time), and protect modesty and comfort: "
              "offer a chaperone, say each step before you do it, and uncover one breast at a time for palpation.",
    video_credit='The draping clip is from the <a href="https://rsc.lib.uwo.ca/s/healthedu/item-set">Health Education Media Library</a> '
                 "(Western Libraries), CC BY-NC 4.0, played from the library's own server. The walkthrough and the axillary clip are "
                 "from Geeky Medics on YouTube. Each opens only when you tap it.",
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
        other_video={"Arms at sides": {"id": "76g_tNWMhCE", "title": "Breast examination, full walkthrough", "channel": "Geeky Medics"},
                 "Axillary nodes": {"id": "MUcQ344kWRM", "title": "Axillary lymph node palpation (clip)", "channel": "Geeky Medics"}},
    general_title="General approach", general_week="Every breast exam",
    spine_heading="What to look for", spine_title="Before the manoeuvres", pearls_heading="Pearls", count_noun="manoeuvres",
)


if __name__ == "__main__":
    exam_page.build(EXAM)
