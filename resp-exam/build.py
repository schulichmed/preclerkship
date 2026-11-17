"""
Purpose: Build the respiratory clinical skills page (resp-exam/index.html) from the
         manoeuvre tables in the medwiki note "Summary Notes - Respiratory Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; clips.json
       (the Health Education Media Library's respiratory exam videos, by region or card)
Output: resp-exam/index.html

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
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Respiratory Clinical Skills.md"

# section number in the note -> region on the page
REGIONS = {
    3: ("general-inspection", "General inspection", "PPES 1 · Week 2", "#3d6fb6"),
    4: ("chest-inspection", "Chest inspection", "PPES 1 · Week 2", "#23798a"),
    5: ("palpation", "Palpation", "PPES 1 · Week 2", "#7a3fb0"),
    6: ("percussion", "Percussion", "PPES 1 · Week 2", "#a8366f"),
    7: ("auscultation", "Auscultation", "PPES 1 · Week 2", "#b4501f"),
    8: ("anterior", "Anterior chest", "PPES 1 · Week 2", "#7d6413"),
    9: ("together", "Putting it together", "PoM 1 · Respirology", "#2f6b4f"),
    10: ("finish", "Finishing the exam", "PoM 1 · Respirology", "#4d5590"),
}

# the note's opening sections, shown as the first band
GENERAL = [(1, "The general approach"), (2, "Before you examine: the respiratory history")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Clubbing (Schamroth sign)": ("Hands: chronic lung disease", "schamroth-sign.jpg"),
    "Asterixis": ("Hands: chronic lung disease", "asterixis.jpg"),
    "Capillary refill": ("Hands: chronic lung disease", "capillary-refill.jpg"),
    "Tracheal position": ("Neck: what is pushing or pulling", "tracheal-position.jpg"),
    "Cervical and supraclavicular lymph nodes": ("Neck: what is pushing or pulling", "cervical-lymph-nodes.jpg"),
    "Chest shape and skin (SEADS)": ("Shape and movement", "chest-shape.jpg"),
    "Respiratory movement and accessory muscles": ("Shape and movement", None),
    "Spine and renal angle tenderness": ("Tenderness", "cva-angle.jpg"),
    "Chest expansion": ("Movement and vibration", None),
    "Tactile fremitus": ("Movement and vibration", "tactile-fremitus.jpg"),
    "Percussing a lung field": ("Air, fluid or solid?", "percussing-a-lung-field.jpg"),
    "Diaphragmatic excursion": ("Diaphragm", "diaphragmatic-excursion.jpg"),
    "Auscultating a lung field": ("Breath sounds", "auscultating-a-lung-field.jpg"),
    "Egophony": ("Voice tests for consolidation", "egophony.jpg"),
    "Whispered pectoriloquy": ("Voice tests for consolidation", "whispered-pectoriloquy.jpg"),
    "Anterior percussion": ("Front lung fields", "anterior-percussion.jpg"),
    "Anterior auscultation": ("Front lung fields", "anterior-auscultation.jpg"),
    "Right middle lobe": ("Front lung fields", "right-middle-lobe.jpg"),
    "Clubbing (upper limb)": ("Hands and legs", "clubbing.jpg"),
    "Pitting edema (lower limbs)": ("Hands and legs", "pitting-edema-lower-limbs.jpg"),
}

EXAM = exam_page.Exam(
    key="resp", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS, opening={},
    h1="Respiratory exam",
    lead='Inspect, palpate, percuss and listen, back then front.',
    find="Find a manoeuvre or a finding (e.g. fremitus, crackles)",
    root="General inspection → Posterior chest → Anterior chest → Finish",
    root_note="Inspect, palpate, percuss, auscultate; compare left with right at the same level, and cover every lung "
              "field from apex to base. The right middle lobe can only be reached from the front.",
    video_credit='Videos and most photos from the <a href="https://rsc.lib.uwo.ca/s/healthedu/item-set">Health Education Media Library</a> '
                 "(Western Libraries; Schulich School of Medicine and Dentistry), CC BY-NC 4.0, played from the library's own server. "
                 "Each opens only when you tap it. "
                 "Other demonstrations are YouTube videos from Geeky Medics, Stanford Medicine 25, Top Hat Tutorials and WVSOM, loaded only when tapped. Barrel chest photo: Cabot, Physical Diagnosis (1912), public domain.",
    other_video={
        "Asterixis": {"id": "YphjuZBJVkI", "start": 0, "title": "Examination for asterixis", "channel": "Top Hat Tutorials"},
        "Respiratory movement and accessory muscles": {"id": "f5ydW0hnMcg", "start": 0, "title": "Stigmata of COPD: chest shape, accessory muscles", "channel": "Stanford Medicine 25"},
        "Chest expansion": {"id": "q6w3CClfhdk", "start": 198, "title": "Chest expansion (respiratory exam)", "channel": "Geeky Medics"},
        "Tactile fremitus": {"id": "RaRqot7iXIU", "start": 0, "title": "Tactile fremitus", "channel": "WVSOM Academic"},
        "Percussing a lung field": {"id": "E3FW11Mbb0I", "start": 0, "title": "Percussion of the lungs", "channel": "Geeky Medics"},
        "Anterior percussion": {"id": "q6w3CClfhdk", "start": 209, "title": "Lung percussion (respiratory exam)", "channel": "Geeky Medics"},
    },
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
    general_title="General approach", general_week="Every respiratory exam",
    spine_heading="What to do", spine_title="Before the manoeuvres", pearls_heading="Pearls", count_noun="manoeuvres",
)

# Hamzah Algodi's own demonstration videos (his permission, 2026-11); shown on the spine cards
EXAM.walk = {
 "The general approach": [
  {
   "id": "bc5zwWnkp5Q",
   "title": "Respiratory demonstration",
   "channel": "Hamzah Algodi"
  }
 ]
}
EXAM.video_credit += ' Demonstration videos by Hamzah Algodi ("*Unofficial* Schulich Clinical Skills"), used with his permission.'

# captions for the landmark diagrams taken from the upper-year student notes
for _key, _cap in {'chest-inspection': 'Chest wall landmarks · tap to enlarge', 'auscultation': 'Where each lobe lies · tap to enlarge'}.items():
    EXAM.region_text.setdefault(_key, {})['landmark_caption'] = _cap

if __name__ == "__main__":
    exam_page.build(EXAM)
