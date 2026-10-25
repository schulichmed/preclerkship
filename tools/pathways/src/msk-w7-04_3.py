# -*- coding: utf-8 -*-
"""
Purpose: Draw the axial spine radiology map: the module's own X-rays read in order (ABCS ->
         cervical -> thoracic -> lumbar and sacrum -> whole spine -> normal variants).
Author:  Noor Simsam
Date:    2026-10-25
Input:   the module PDF "Axial spine radiology" (--pdf); every picture is cropped from it
Output:  an SVG with the crops embedded as JPEG data URIs (--out), optional PNG preview (--png)

The layout is tools/picture_map.py; this file is the content. It sits beside the lecture's
decision chart (msk-w7-04_2), which keeps the stability and next-step logic.
Skipped on purpose: slide 15's labelled lateral (a website logo), the labelled half of
slide 17 (an "EBM Consult" mark) and slide 72's limbus vertebra and Schmorl's nodes
(a LearningRadiology.com watermark); those two variants stay text only.

    python3 tools/pathways/src/msk-w7-04_3.py --pdf "<Axial spine radiology.pdf>" \
        --out "<vault>/Attachments/axial spine radiology map.svg" --png /tmp/p.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import picture_map  # noqa: E402

# picture_map's CROPS shape, keeping the annotated panel where a slide pairs a plain film
# with a labelled one
CROPS = {
    "c_ap": ((12, 0), (0.5, 0, 1, 1)),
    "c_lines": ((17, 0), (0.468, 0, 1, 1), "keep"),   # the line drawing + its film
    "c_oblique": ((21, 0), (0.5, 0, 1, 1)),
    "c_open_mouth": ((24, 0), (0.476, 0.49, 1, 1)),
    "t_ap": ((28, 0), (0.5, 0, 1, 1)),
    "t_lat": ((31, 0), (0.5, 0, 1, 1)),
    "t_swimmer": ((34, 0), (0.5, 0, 1, 1)),
    "l_ap": ((38, 0), (0.5, 0, 1, 1)),
    "l_lat": ((41, 0), (0.5, 0, 1, 1)),
    "l_pars": ((42, 0), (0.5, 0, 1, 1)),
    "l_scottie": ((43, 0), (0, 0, 0.53, 1)),
    "sacrum": ((45, 0), (0.5, 0, 1, 1)),
    "ext_teardrop": ((55, 0), (0.5, 0, 1, 1)),
    "dens": ((56, 0), (0.466, 0, 1, 1)),
    "c5_c7": ((57, 0), (0.5, 0, 1, 1)),
    "c4": ((58, 0), (0.5, 0, 1, 1)),
    "perched": ((59, 0), (0, 0, 1, 1)),
    "spinous_ap": ((60, 0), (0.29, 0, 0.687, 1)),
    "spondylosis": ((61, 0), (0.5, 0, 1, 1)),
    "abscess": ((62, 0), (0.5, 0, 1, 1)),
    "listhesis": ((64, 0), (0.5, 0, 1, 1)),
    "collar": ((66, 0), (0, 0, 1, 1)),
    "as_spine": ((67, 0), (0, 0.5, 1, 1)),
    "sacroiliitis": ((69, 0), (0, 0.5, 1, 1)),
    "cervical_rib": ((70, 0), (0, 0, 1, 1)),
    "screws": ((75, 0), (0, 0, 1, 1)),
    "vertebroplasty": ((76, 0), (0, 0, 1, 1)),
    "abc": ((77, 0), (0, 0, 1, 1)),
    "cobb": ((79, 0), (0.062, 0.17, 0.946, 0.83)),
    "scoliosis": ((80, 0), (0, 0, 1, 1)),
    "scoliosis_postop": ((82, 0), (0, 0, 1, 1)),
}

ROOT = {
    "title": "Read every spine film the same way: ABCS",
    "img": None,
    "lines": [
        "A · **Alignment** first: cervical **mild lordosis** · thoracic **kyphosis** · lumbar **lordosis**; "
        "a break tells you where to look",
        "B · **Bones**: follow the cortices · **vertebral body height** · pedicles, transverse processes",
        "C · **Cartilage and joints**: cartilage is invisible, so read the **disc spaces** and **facet joints**",
        "S · **Soft tissues**: prevertebral, paraspinal, then the **whole image** (lungs, stones, bowel, free air)",
        "**Stability: anterior body only = more likely stable · posterior elements involved = UNSTABLE**",
    ],
}

BANDS = [
    {"name": "CERVICAL SPINE", "colour": "teal", "rows": [
        {"label": "STANDARD VIEWS: AP · lateral · oblique (right + left) · open-mouth",
         "note": "Acute trauma: no obliques (don't move the neck), and most get CT. "
                 "Flexion and extension only if instability is suspected.",
         "cards": [
             {"title": "AP", "img": "c_ap", "lines": [
                 "• Count 7: **T1 meets the 1st rib**",
                 "• Spinous processes in a **straight line**, evenly spaced",
                 "• Uncinate processes enlarge in osteoarthritis"]},
             {"title": "Lateral: the 4 lines", "img": "c_lines", "wide": True, "lines": [
                 "• **The single most important view**",
                 "• Anterior vertebral · posterior vertebral · spinolaminar · spinous process: **smooth**",
                 "• Atlantodental interval **< 3 mm adult, < 5 mm child**",
                 "• Prevertebral tissue **< 7 mm at C2, < 22 mm at C6**"]},
             {"title": "Oblique", "img": "c_oblique", "lines": [
                 "• Opens the **neural foramina**, bordered by the pedicles",
                 "• Facets"]},
             {"title": "Open-mouth (odontoid)", "img": "c_open_mouth", "lines": [
                 "• **C1 lateral masses line up with C2**",
                 "• Joint spaces symmetric"]},
         ]},
        {"label": "FINDINGS: TRAUMA", "cards": [
            {"title": "Extension teardrop (C2)", "img": "ext_teardrop", "kind": "bad", "lines": [
                "• **Anteroinferior corner** of C2",
                "• Hyperextension injury"]},
            {"title": "Dens fracture", "img": "dens", "kind": "bad", "lines": [
                "• Type I tip · II base · III into the C2 body",
                "(types not needed in detail)"]},
            {"title": "C5–C7 comminuted", "img": "c5_c7", "kind": "bad", "lines": [
                "• **C7 compression fracture**: central height lost",
                "• Lines disrupted · C5–C6 disc space widened",
                "• Facets still congruent"]},
            {"title": "C4: UNSTABLE", "img": "c4", "kind": "bad", "lines": [
                "• Height lost, **fragment pushed back** toward the canal",
                "• **Posterior vertebral line broken** → past the back of the body"]},
        ]},
        {"label": "FINDINGS: FACET DISLOCATION", "cards": [
            {"title": "Perched facets (lateral)", "img": "perched", "kind": "bad", "wide": True, "lines": [
                "• **C5 slipped forward on C6**, facets incongruent and touching",
                "• → **MRI + urgent neurosurgery**"]},
            {"title": "Same on the AP", "img": "spinous_ap", "kind": "bad", "lines": [
                "• Spinous processes **off the midline**, unevenly spaced",
                "• Points to facet dislocation when there is no lateral"]},
        ]},
        {"label": "FINDINGS: NOT TRAUMA", "cards": [
            {"title": "Cervical spondylosis", "img": "spondylosis", "kind": "bad", "lines": [
                "• The commonest non-traumatic finding",
                "• **Disc-space narrowing · marginal osteophytes · endplate sclerosis**",
                "• Straightened lordosis (can be spasm)"]},
            {"title": "Retropharyngeal abscess", "img": "abscess", "kind": "bad", "lines": [
                "• Soft tissue **wider than the vertebral body at C5–C6**",
                "• Airway pushed forward · **air locules**"]},
        ]},
    ]},
    {"name": "THORACIC SPINE", "colour": "purple", "rows": [
        {"label": "STANDARD VIEWS: AP · lateral · swimmer's", "cards": [
            {"title": "AP", "img": "t_ap", "lines": [
                "• Count **T1 (1st rib) to T12 (12th rib)**",
                "• Pedicles oval with corticated margins · endplates sclerotic"]},
            {"title": "Lateral", "img": "t_lat", "lines": [
                "• Normal **kyphosis**",
                "• Pedicles elongated, bordering oval foramina · facets clearest mid to lower"]},
            {"title": "Swimmer's (arm raised)", "img": "t_swimmer", "lines": [
                "• For the **upper thoracic spine** hidden by soft tissue",
                "• **T1 = below the prominent C7 spinous process**"]},
        ]},
    ]},
    {"name": "LUMBAR SPINE AND SACRUM", "colour": "orange", "rows": [
        {"label": "STANDARD VIEWS: AP · lateral (oblique only when requested, for the pars)", "cards": [
            {"title": "AP", "img": "l_ap", "lines": [
                "• **L1 = below the 12th rib** (4 or 6 = transitional)",
                "• **Both pedicles** on every level"]},
            {"title": "Lateral", "img": "l_lat", "lines": [
                "• Bodies, endplates, disc spaces, pedicles, foramina"]},
            {"title": "Sacrum + sacroiliac joints", "img": "sacrum", "wide": True, "lines": [
                "• Sacral ala · lateral masses · foramina · coccyx (4–5 segments)",
                "• Sacroiliac joint is oblique: the AP shows only parts of it"]},
        ]},
        {"label": "THE PARS INTERARTICULARIS", "cards": [
            {"title": "Pars on the lateral", "img": "l_pars", "lines": [
                "• **Between the superior and inferior articular processes**",
                "• Its defect causes low back pain"]},
            {"title": "Oblique: the Scottie dog", "img": "l_scottie", "lines": [
                "• Nose = transverse process · eye = pedicle",
                "• Ear = superior facet · front leg = inferior facet",
                "• **Neck = pars interarticularis**"]},
        ]},
        {"label": "FINDINGS", "cards": [
            {"title": "Spondylolysis: the collar", "img": "collar", "kind": "bad", "lines": [
                "• Lucent line across the dog's neck at L5 = **pars defect**",
                "• The **Scottie dog collar sign**"]},
            {"title": "Isthmic spondylolisthesis", "img": "listhesis", "kind": "bad", "lines": [
                "• **L4 slips forward on L5** (4–5 mm, graded) + pars defect",
                "• Disc space narrowed",
                "• No pars defect, older adult = **degenerative**"]},
            {"title": "Aneurysmal bone cyst", "img": "abc", "kind": "bad", "wide": True, "lines": [
                "• Expansile **lytic** lesion replacing the right pedicle (normal left pedicle ringed)",
                "• Obvious on the AP, nearly invisible on the lateral: **read both views**"]},
        ]},
    ]},
    {"name": "WHOLE SPINE", "colour": "blue", "rows": [
        {"label": "INFLAMMATORY: ANKYLOSING SPONDYLITIS (mostly seronegative)", "cards": [
            {"title": "Spine", "img": "as_spine", "kind": "bad", "wide": True, "lines": [
                "• Ossified **anterior + posterior longitudinal ligaments**",
                "• Bony bridging across discs · fused facets → rigid spine",
                "• Fractures next to mobile segments"]},
            {"title": "Sacroiliitis", "img": "sacroiliitis", "kind": "bad", "lines": [
                "• **Erosions** of both subchondral plates → pseudo-widening",
                "• Sclerosis mostly on the **iliac** side · ankylosis late",
                "• Bone marrow edema needs **MRI**"]},
        ]},
        {"label": "SCOLIOSIS: sideways curve ± rotation", "cards": [
            {"title": "Cobb angle", "img": "cobb", "wide": True, "lines": [
                "• Superior endplate of the top tilted vertebra + inferior endplate of the bottom one",
                "• Angle between their perpendiculars",
                "• **> 10° = scoliosis · > 50° → consider surgery**"]},
            {"title": "Marked scoliosis", "img": "scoliosis", "kind": "bad", "lines": [
                "• Right thoracic (primary) + left lumbar (compensatory)",
                "• Rotation: the **pedicles shift**"]},
            {"title": "After correction", "img": "scoliosis_postop", "lines": [
                "• **Harrington rods + transpedicular screws**"]},
        ]},
        {"label": "HARDWARE", "cards": [
            {"title": "Transpedicular screws + rods", "img": "screws", "lines": [
                "• Screws through the pedicles, joined by posterior rods",
                "• Scoliosis, spondylolisthesis"]},
            {"title": "Vertebroplasty", "img": "vertebroplasty", "lines": [
                "• Cement in bodies with **painful compression fractures** (osteopenic bone)",
                "• Relieves pain, slows progression, **does not restore height**"]},
        ]},
    ]},
    {"name": "NORMAL VARIANTS: NOT DISEASE", "colour": "olive", "rows": [
        {"label": "DON'T CALL THESE PATHOLOGY", "cards": [
            {"title": "Cervical ribs", "img": "cervical_rib", "lines": [
                "• Extra rib off **C7**, here both sides; the right pseudoarticulates with the 1st rib",
                "• Osseous ones show, fibrous ones don't",
                "• Can cause neck pain and arm pain (neurovascular bundle)"]},
            {"title": "Limbus vertebra", "img": None, "lines": [
                "• Triangle of bone at the **anterosuperior corner**",
                "• Unfused ring apophysis · adolescents, often L4",
                "• **Not a fracture**"]},
            {"title": "Others", "img": None, "lines": [
                "• **Schmorl's nodes**: endplate depressions, usually incidental",
                "• **Transitional vertebrae**: lumbarization or sacralization",
                "• A curve **under 10°**",
                "(the module's limbus and Schmorl film carries a watermark)"]},
        ]},
    ]},
]


if __name__ == "__main__":
    picture_map.main(__doc__, ROOT, BANDS, CROPS)
