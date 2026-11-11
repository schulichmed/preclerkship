"""
Purpose: Build the MSK clinical skills chart page (msk-exam/index.html) from the
         special-test tables in the medwiki note "Summary Notes - MSK Clinical Skills".
Author: Noor Simsam
Date: 2026-10-26
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; videos.json
       (MSK Medicine); videos_other.json (videos from other channels for tests MSK Medicine
       has none for)
Output: msk-exam/index.html

The note is the single source of the steps and positive findings: edit the note,
then rerun this script. Which problem heading each test sits under, and its
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
NOTE = VAULT / "01 - Lectures/99 - PoM 2/03 - MSK/Summary Notes - MSK Clinical Skills.md"

# section number in the note -> region on the page
REGIONS = {
    4: ("cspine", "Cervical spine", "Week 1", "#3d6fb6"),
    5: ("lspine", "Lumbar spine", "Week 1", "#23798a"),
    6: ("shoulder", "Shoulder", "Week 2", "#7a3fb0"),
    7: ("elbow", "Elbow", "Week 2", "#a8366f"),
    8: ("wrist", "Wrist and hand", "Week 2", "#b4501f"),
    9: ("hip", "Hip", "Week 3", "#7d6413"),
    10: ("knee", "Knee", "Week 3", "#2f6b4f"),
    11: ("ankle", "Ankle and foot", "Week 3", "#4d5590"),
}

# the note's opening sections, shown as the first band
GENERAL = [(1, "Approach to every joint"), (2, "Gait"),
           (3, "Neuro screen: sensation, muscle strength, reflexes")]


# test name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Spurling's maneuver": ("Nerve root compression (radiculopathy)", "spurling-s-maneuver.jpg"),
    "Cervical distraction": ("Nerve root compression (radiculopathy)", None),
    "Straight leg raise (Lasègue)": ("Low lumbar root (L5/S1): disc herniation", "straight-leg-raise-lasegue.jpg"),
    "Bragard's sign": ("Low lumbar root (L5/S1): disc herniation", "bragard-s-sign.jpg"),
    "Bowstring sign": ("Low lumbar root (L5/S1): disc herniation", None),
    "Crossed straight leg raise": ("Low lumbar root (L5/S1): disc herniation", None),
    "Femoral stretch test": ("Upper lumbar root (L2-L4)", "femoral-nerve-stretch-test.jpg"),
    "Modified Schober's test": ("Inflammatory back disease", "modified-schober-test.jpg"),
    "Adam's forward bend test": ("Scoliosis", "adam-s-forward-bend-test.jpg"),
    "Painful arc": ("Impingement", "painful-arc-shoulder.jpg"),
    "Neer's test": ("Impingement", "neer-test.jpg"),
    "Hawkins test": ("Impingement", "hawkins-kennedy-test.jpg"),
    "Empty can test": ("Rotator cuff tendon", "empty-can-jobe-test.jpg"),
    "Resisted external rotation": ("Rotator cuff tendon", "resisted-external-rotation-drawn.jpg"),
    "Lift-off test": ("Rotator cuff tendon", "lift-off-gerber-test.jpg"),
    "Belly press test": ("Rotator cuff tendon", "belly-press-test.jpg"),
    "Bear hug test": ("Rotator cuff tendon", "bear-hug-test-drawn.jpg"),
    "Drop arm test": ("Rotator cuff tendon", "drop-arm-test-drawn.jpg"),
    "External rotation lag sign": ("Rotator cuff tendon", None),
    "Speed's test": ("Biceps tendon", "speed-s-test.jpg"),
    "Yergason's test": ("Biceps tendon", "yergason-s-test.jpg"),
    "Apprehension test": ("Anterior instability", "shoulder-apprehension-and-relocation-test.jpg"),
    "Relocation test (Fowler's sign)": ("Anterior instability", "shoulder-apprehension-and-relocation-test.jpg"),
    "Scarf test (cross-arm)": ("AC joint", "scarf-test-drawn.jpg"),
    "Valgus and varus stress": ("Collateral ligaments", "elbow-valgus-stress-test.jpg"),
    'Lateral epicondylitis ("tennis elbow")': ("Tendons at the epicondyles", None),
    'Medial epicondylitis ("golfer\'s elbow")': ("Tendons at the epicondyles", None),
    "Tinel's sign (elbow)": ("Ulnar nerve", None),
    "Tinel's sign (wrist)": ("Carpal tunnel (median nerve)", "tinel-s-sign-wrist.jpg"),
    "Phalen's test": ("Carpal tunnel (median nerve)", "phalen-s-test.jpg"),
    "1st CMC grind test": ("Thumb base arthritis", "cmc-grind-test.jpg"),
    "Finkelstein's test": ("De Quervain's tenosynovitis", "finkelstein-s-test.jpg"),
    "Thomas test": ("Flexion contracture", "thomas-test-drawn.jpg"),
    "Trendelenburg sign": ("Weak hip abductors", "trendelenburg-sign.jpg"),
    "Stinchfield test": ("Inside the hip joint", "stinchfield-test.jpg"),
    "FABER test (Flexion, ABduction, External Rotation)": ("SI joint (or hip)", "faber-patrick-test.jpg"),
    "Thigh thrust": ("SI joint (or hip)", "thigh-thrust.jpg"),
    "FADIR test (Flexion, ADduction, Internal Rotation)": ("Hip joint or SI joint", None),
    "Ober's test": ("IT band", "obers-test-drawn.jpg"),
    "True and apparent leg length": ("Leg length", "true-leg-length-measurement.jpg"),
    "Wipe (bulge) test": ("Effusion", "wipe-bulge-test.jpg"),
    "Patellar ballottement": ("Effusion", "patellar-ballottement.jpg"),
    "Valgus / varus stress": ("Collateral ligaments (MCL, LCL)", "valgus-varus-stress.jpg"),
    "Lachman test": ("Cruciate ligaments (ACL, PCL)", "lachman-test.jpg"),
    "Anterior drawer": ("Cruciate ligaments (ACL, PCL)", "anterior-drawer.jpg"),
    "Posterior drawer": ("Cruciate ligaments (ACL, PCL)", "posterior-drawer.jpg"),
    "Posterior sag sign": ("Cruciate ligaments (ACL, PCL)", "posterior-sag-sign.jpg"),
    "McMurray's test": ("Meniscus", "mcmurray-s-test.jpg"),
    "Thessaly's test": ("Meniscus", "thessaly-test.jpg"),
    "Crouch compression (duck walk)": ("Meniscus", None),
    "Patellar apprehension": ("Patella", "patellar-apprehension-test.jpg"),
    "Patellar grind (Osmond-Clarke)": ("Patella", "patellar-grind-clarke-test.jpg"),
    "Anterior drawer (ankle)": ("Ligaments (sprain)", "ankle-anterior-drawer.jpg"),
    "Talar tilt": ("Ligaments (sprain)", "talar-tilt.jpg"),
    "Passive external rotation": ("Ligaments (sprain)", "passive-external-rotation.jpg"),
    "Lateral ankle ligament stress": ("Ligaments (sprain)", "lateral-ankle-ligament-stress.jpg"),
    "Thompson test": ("Achilles rupture", "thompson-simmonds-test.jpg"),
    "Homan's sign": ("Deep vein thrombosis", None),
    "Metatarsal squeeze": ("Morton's neuroma", None),
}

# test name -> MSK Medicine video page slug (mskmedicine.com/clinical_skills/<slug>/)
VIDEO = {
    "Spurling's maneuver": "spurlings-test", "Cervical distraction": "cervical-distraction-test",
    "Straight leg raise (Lasègue)": "straight-leg-raise", "Bragard's sign": "braggards-sign",
    "Bowstring sign": "bowstring-sign", "Crossed straight leg raise": "crossed-straight-leg-raise",
    "Femoral stretch test": "femoral-stretch-test", "Modified Schober's test": "modified-schobers-test",
    "Painful arc": "painful-arc-rotator-cuff-impingement", "Neer's test": "neers-test",
    "Hawkins test": "hawkins-test", "Empty can test": "empty-can-test",
    "Resisted external rotation": "external-rotation-test-infraspinatus-teres-minor",
    "Lift-off test": "lift-off-test", "Belly press test": "belly-press-test", "Speed's test": "speeds-test",
    "Yergason's test": "yergusons-test", "Apprehension test": "apprehension-test-shoulder",
    "Relocation test (Fowler's sign)": "fowlers-sign-relocation-test", "Scarf test (cross-arm)": "scarf-test",
    "Valgus and varus stress": "elbow-valgus-varus-stress-tests",
    'Lateral epicondylitis ("tennis elbow")': "lateral-epicondylitis-tests",
    'Medial epicondylitis ("golfer\'s elbow")': "medial-epicondylitis-tests",
    "Tinel's sign (elbow)": "tinels-sign-elbow", "Tinel's sign (wrist)": "tinels-sign-median-nerve-carpal-tunnel",
    "Phalen's test": "phalens-sign", "1st CMC grind test": "1st-cmc-grind-test",
    "Finkelstein's test": "finkelsteins-test", "Thomas test": "thomas-flexion-contracture-test",
    "Trendelenburg sign": "trendelenberg-sign", "Stinchfield test": "stinchfields-test",
    "FABER test (Flexion, ABduction, External Rotation)": "faber-test", "Ober's test": "obers-test",
    "FADIR test (Flexion, ADduction, Internal Rotation)": "fadir-test",
    "True and apparent leg length": "true-leg-length-measurement",
    "Valgus / varus stress": "knee-valgus-and-varus-stress-tests", "Lachman test": "lachman-maneuvers",
    "Anterior drawer": "anterior-drawer-knee", "Posterior drawer": "posterior-drawer-sign-pcl",
    "Posterior sag sign": "pcl-sulcus-sag-signs", "McMurray's test": "mcmurrays-test",
    "Thessaly's test": "thessalys-test", "Crouch compression (duck walk)": "crouch-compression-test-knee",
    "Patellar apprehension": "patellar-apprehension-test", "Patellar grind (Osmond-Clarke)": "patellar-grind-test",
    "Anterior drawer (ankle)": "anterior-drawer-ankle-atfl", "Talar tilt": "talar-tilt-test-cfl",
    "Lateral ankle ligament stress": "lateral-ankle-ligament-tests", "Thompson test": "thompson-test",
    "Homan's sign": "homans-sign-dvt", "Metatarsal squeeze": "metatarsal-squeeze-test-mortons-neuroma",
    "Ottawa ankle and foot rules": "ottawa-ankle-rules",
}
REGION_VIDEO = {
    "cspine": ["cervical-spine-look-feel-move"], "lspine": ["lumbar-spine-look-feel-move"],
    "shoulder": ["shoulder-look-feel-move"], "elbow": ["elbow-exam-look-feel-move"],
    "wrist": ["hand-wrist-look-feel-move"], "hip": ["hip-exam-look-feel-move"],
    "knee": ["knee-exam-look-feel-move"], "ankle": ["ankle-exam-look-feel-move"],
}

# the gait card: the two overview videos, then each abnormal gait's own (gait name as the note's table has it)
GAIT = {
    "title": "Gait",
    "watch": [("Gait cycle", "gait-cycle"), ("Gait assessment", "gait-assessment")],
    "videos": {
        "Antalgic": [("Antalgic gait", "antalgic-gait")],
        "Trendelenburg": [("Trendelenburg gait", "trendelenberg-gait")],
        "Foot drop": [("Steppage & foot slap", "steppage-foot-slap-gait-patterns-foot-drop"),
                      ("Circumduction", "circumduction-gait")],
        "Ataxic": [("Ataxic gait", "ataxic-gait-pattern")],
    },
}

# the neuro screen card: each limb's videos sit over its own half of the root table
ROOTS = {
    "title": "Neuro screen: sensation, muscle strength, reflexes",
    "upper": {"myotome": "myotomal-motor-screen-upper", "dermatome": "sensory-dermatomal-screen-upper",
              "reflex": "upper-extremity-reflexes"},
    "lower": {"myotome": "myotomal-motor-screen-lower", "dermatome": "sensory-dermatomal-screen-lower",
              "reflex": "lower-extermity-reflexes"},
    "mrc": "manual-muscle-testing-mmt-mrc-scale",
}

# normal range of motion, from the course objectives (degrees: 0 to N), drawn as dials
ROM = {
    "shoulder": [("Flexion", 180), ("Extension", 50), ("Abduction", 180), ("Adduction", 45),
                 ("External rotation", 50), ("Internal rotation", 50)],
    "elbow": [("Extension", 5), ("Flexion", 145), ("Pronation", 90), ("Supination", 90)],
    "wrist": [("Wrist extension", 80), ("Wrist flexion", 80), ("Pronation", 90), ("Supination", 90),
              ("Ulnar deviation", 30), ("Radial deviation", 20)],
    "hip": [("Flexion", 135), ("External rotation", 45), ("Internal rotation", 35), ("Abduction", 45),
            ("Adduction", 20)],
    "knee": [("Flexion (from full extension)", 135)],
    "ankle": [("Plantar flexion", 50), ("Dorsiflexion", 20), ("Inversion", 35), ("Eversion", 20),
              ("1st MTP flexion", 45), ("1st MTP extension", 70)],
    "cspine": [("Flexion", 90), ("Extension", 90), ("Rotation", 90), ("Lateral flexion", 45)],
    "lspine": "No numeric norms in the objectives. Check extension, flexion, lateral flexion and rotation "
              "for smoothness and symmetry.",
}

# region -> (the complaint, the joints above and below), for the line to say at the start of a TOSCE
JOINTS = {
    "cspine": ("neck", "the shoulder and thoracic spine"), "lspine": ("low back", "the hip and thoracic spine"),
    "shoulder": ("shoulder", "the neck and elbow"), "elbow": ("elbow", "the shoulder and wrist"),
    "wrist": ("wrist and hand", "the elbow and neck"), "hip": ("hip", "the low back and knee"),
    "knee": ("knee", "the hip and ankle"), "ankle": ("ankle and foot", "the knee and low back"),
}
OPENING = {key: f"I would normally inspect the other side and examine the joint above and below ({joints}), "
              f"but in the interest of time I will focus on the {complaint} complaint."
           for key, (complaint, joints) in JOINTS.items()}

# fracture rules the note gives as prose: one card, no picture
OTTAWA = {
    "num": "6", "name": "Ottawa ankle and foot rules", "problem": "Fracture: X-ray or not?", "img": None,
    "for": "Who needs an <b>X-ray</b> (age 18 or over)",
    "steps": ["Press the <b>back edge and tip of each malleolus</b> (distal 6 cm of tibia and fibula)",
              "Press the <b>base of the 5th metatarsal</b> and the <b>navicular</b>",
              "Ask them to <b>walk 4 steps</b>"],
    "pos": "<b>Any bony tenderness there</b>, or <b>cannot bear weight for 4 steps</b> (right after the injury and in the emergency department) → X-ray",
}


EXAM = exam_page.Exam(
    key="msk", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS, opening=OPENING,
    h1="MSK exam, by region",
    lead='Every exam from the suggested-videos list: the general exam first (approach, gait, neuro screen), then each region\'s look, feel and move, its special tests grouped under the problem you suspect, and its pearls. Built from the course objectives; videos for each test are at <a href="https://mskmedicine.com">mskmedicine.com</a>. For the dermatomes and myotomes drawn on a body, see the body map.',
    find='Find a test or a problem (e.g. meniscus, ulnar)',
    root='Every joint: Look → Feel → Move → Special tests → Neurovascular',
    root_note="Compare left with right · examine the joint above and below · watch gait for the back and legs. A test counts only when it reproduces the patient's own symptom or differs from the other side.",
    video_credit='Videos by <a href="https://mskmedicine.com">MSK Medicine</a>, played from their YouTube channel; where they have none, a video from another teaching channel, named on its button. Each opens only when you tap it.',
    general_week="Week 1 · every joint", pearls_heading="Pearls and X-rays",
    video=VIDEO, video_page="https://mskmedicine.com/clinical_skills/{slug}/", region_video=REGION_VIDEO, official_region_video=True,
    other_video=json.loads((HERE / "videos_other.json").read_text(encoding="utf-8")),
    extra_cards={"ankle": [OTTAWA]},
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
    gait=GAIT, roots=ROOTS, rom=ROM, rom_source="Values from the course objectives",
    # on the hip, FABER, FADIR and the extra thigh thrust share one heading (they are the
    # lumbar spine's SI joint tests there)
    region_tests={"hip": {
        "FABER test (Flexion, ABduction, External Rotation)": ("Hip joint or SI joint", "faber-patrick-test.jpg"),
        "Thigh thrust": ("Hip joint or SI joint", "thigh-thrust.jpg"),
    }},
)

# Hamzah Algodi's own demonstration videos (his permission, 2026-11); shown on the spine cards
EXAM.walk = {
 "shoulder": [
  {
   "id": "1C0lCTyXhBs",
   "title": "Shoulder",
   "channel": "Hamzah Algodi"
  }
 ],
 "elbow": [
  {
   "id": "vwn1Yzwz9I0",
   "title": "Elbow",
   "channel": "Hamzah Algodi"
  }
 ],
 "wrist": [
  {
   "id": "wm2bP1J4U_g",
   "title": "Wrist",
   "channel": "Hamzah Algodi"
  }
 ],
 "hip": [
  {
   "id": "rkIvc4056zk",
   "title": "Hip",
   "channel": "Hamzah Algodi"
  }
 ],
 "knee": [
  {
   "id": "Cqf56oiCyJQ",
   "title": "Knee",
   "channel": "Hamzah Algodi"
  }
 ],
 "ankle": [
  {
   "id": "R-rKtuYcr1M",
   "title": "Ankle",
   "channel": "Hamzah Algodi"
  }
 ],
 "cspine": [
  {
   "id": "vKui90nHHu8",
   "title": "Cervical spine",
   "channel": "Hamzah Algodi"
  }
 ],
 "lspine": [
  {
   "id": "u3j78jgIfps",
   "title": "Lumbar spine",
   "channel": "Hamzah Algodi"
  }
 ]
}
EXAM.video_credit += ' Demonstration videos by Hamzah Algodi ("*Unofficial* Schulich Clinical Skills"), used with his permission. Range-of-motion clips (cropped to the moving limb, re-encoded small) from Schulich School of Medicine and Dentistry (Health Education Media Library, Western Libraries), CC BY-NC 4.0; each button links to its library item page.'


if __name__ == "__main__":
    exam_page.build(EXAM)
