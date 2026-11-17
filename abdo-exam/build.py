"""
Purpose: Build the abdominal clinical skills page (abdo-exam/index.html) from the
         manoeuvre tables in the medwiki note "Summary Notes - Abdominal Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; clips.json
       (the Health Education Media Library's abdominal exam videos, by test, region or card);
       videos.json (Geeky Medics, the teaching channel); videos_other.json (other channels)
Output: abdo-exam/index.html

The note is the single source of the steps and positive findings: edit the note,
then rerun this script. Which problem heading each manoeuvre sits under, and its
picture, are set here. How the page looks lives in clinical-skills/exam_page.py,
shared by every exam page.
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
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Abdominal Clinical Skills.md"

WEEK3 = "PPES 1 · Week 3"
# section number in the note -> region on the page
REGIONS = {
    3: ("patient", "Look at the patient", WEEK3, "#3d6fb6"),
    4: ("inspect", "Inspect the abdomen", WEEK3, "#23798a"),
    5: ("auscultate", "Auscultate", WEEK3, "#7a3fb0"),
    6: ("percuss", "Percuss", WEEK3, "#a8366f"),
    7: ("palpate", "Palpate", WEEK3, "#b4501f"),
    8: ("liver", "Liver", WEEK3, "#7d6413"),
    9: ("spleen", "Spleen", WEEK3, "#2f6b4f"),
    10: ("ascites", "Ascites", WEEK3, "#4d5590"),
    11: ("appendix", "Appendicitis tests", "PoM 1 · Gastroenterology", "#8a3b3b"),
    12: ("finish", "Finishing and next steps", "PPES 1 · PoM 1", "#566b2f"),
}

# the note's opening sections, shown as the first band
GENERAL = [(1, "The general approach"), (2, "Before you examine: the GI history")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Asterixis": ("Hands: liver and kidney failure", "asterixis.jpg"),
    "Clubbing": ("Hands: gut and liver disease", "clubbing.jpg"),
    "Liver stigmata (hands, face, chest)": ("Chronic liver disease", "liver-stigmata.jpg"),
    "Inspection from the side and the foot": ("Shape, skin and movement", "inspection-side-and-foot.jpg"),
    "Hernia check (head raise or cough)": ("Hernia or mass", "hernia-check.jpg"),
    "Bowel sounds": ("Is the bowel working?", "bowel-sounds.jpg"),
    "Bruits (aorta, renal, iliac, femoral)": ("Narrowed artery", "bruits.jpg"),
    "Percussion of the four quadrants": ("Gas, mass or enlarged organ", "percussion-four-quadrants.jpg"),
    "Light palpation": ("Tenderness and masses", "light-palpation.jpg"),
    "Deep palpation": ("Tenderness and masses", "deep-palpation.jpg"),
    "Guarding": ("Peritonitis", "guarding.jpg"),
    "Head-raise test for tenderness": ("Wall or deeper?", "head-raise-tenderness.jpg"),
    "Aorta width": ("Aortic aneurysm", "aorta-width.jpg"),
    "Kidneys (bimanual)": ("Kidneys", "kidneys.jpg"),
    "Liver span (percussion)": ("Hepatomegaly", "liver-span.jpg"),
    "Liver edge (palpation)": ("Hepatomegaly", "liver-edge.jpg"),
    "Murphy's sign": ("Gallbladder", "murphys-sign.jpg"),
    "Castell's sign (percussion)": ("Splenomegaly", "castells-sign.jpg"),
    "Spleen tip (palpation)": ("Splenomegaly", "spleen-tip-palpation.jpg"),
    "Shifting dullness": ("Fluid in the belly", "shifting-dullness.jpg"),
    "Fluid wave": ("Fluid in the belly", "fluid-wave.jpg"),
    "Rebound tenderness": ("Peritonitis", "rebound-tenderness.jpg"),
    "McBurney's point": ("Appendicitis", "mcburneys-point.jpg"),
    "Rovsing's sign": ("Appendicitis", "rovsings-sign.jpg"),
    "Psoas test": ("Appendicitis", "psoas-test.jpg"),
    "Obturator test": ("Appendicitis", "obturator-test.jpg"),
    "Leg edema": ("Fluid in the legs", "leg-edema.jpg"),
    "Inguinal nodes and hernias": ("Groin", "inguinal-hernia.jpg"),
}

# The TOSCE sentence for the whole exam sits in the general card; each region adds its own.
OPENING = {}

EXAM = exam_page.Exam(
    key="abdo", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS, opening=OPENING,
    h1="Abdominal exam",
    lead='Inspect, listen, percuss and palpate, then the liver, spleen, ascites and appendicitis tests.',
    find="Find a manoeuvre (e.g. spleen)",
    root="Inspect → Auscultate → Percuss → Palpate → Organs → Ascites",
    root_note="Listen before you touch, and ask where it hurts and examine that spot last, watching the patient's face "
              "the whole time.",
    video_credit='Video demonstrations from the <a href="https://rsc.lib.uwo.ca/s/healthedu/item-set">Health Education Media Library</a> '
                 "(Western Libraries; Arthur Labatt Family School of Nursing), CC BY-NC 4.0, played from the library's own server; "
                 "each opens only when you tap it. Teaching videos from Geeky Medics and other channels open from YouTube when tapped. "
                 "Photographs of the manoeuvres are from the same library; sign photographs and illustrations are credited at the foot, and the concept diagrams are drawn for this page.",
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
    video_page="https://www.youtube.com/watch?v=PYAnF6GJY2I",
    region_video={"The general approach": ["geeky-abdominal-exam"]},
    other_video=json.loads((HERE / "videos_other.json").read_text(encoding="utf-8")),
    general_title="General approach", general_week="Every abdominal exam",
    spine_heading="What to look for", spine_title="Before the manoeuvres", pearls_heading="Pearls", count_noun="manoeuvres",
)

# Hamzah Algodi's own demonstration videos (his permission, 2026-11); shown on the spine cards
EXAM.walk = {
 "The general approach": [
  {
   "id": "dDWKOcZKzLQ",
   "title": "GI demonstration",
   "channel": "Hamzah Algodi"
  }
 ]
}
EXAM.video_credit += ' Demonstration videos by Hamzah Algodi ("*Unofficial* Schulich Clinical Skills"), used with his permission.'

# captions for the landmark diagrams taken from the upper-year student notes
for _key, _cap in {'inspect': 'Surface landmarks · tap to enlarge', 'percuss': 'Quadrants and regions · tap to enlarge', 'palpate': 'What lies underneath · tap to enlarge'}.items():
    EXAM.region_text.setdefault(_key, {})['landmark_caption'] = _cap

if __name__ == "__main__":
    exam_page.build(EXAM)
