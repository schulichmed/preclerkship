# -*- coding: utf-8 -*-
"""
Purpose: Draw the upper extremity radiology overview: a visual map of the module's own
         X-rays, read in order (systematic read -> shoulder -> elbow -> wrist -> osteoarthritis).
Author:  Noor Simsam
Date:    2026-10-24
Input:   the module PDF "Upper Limb Radiology" (--pdf), which every picture is cropped from,
         and the giant cell tumour slide (--gct), which the PDF export drops after its caption
Output:  an SVG with the crops embedded as JPEG data URIs (--out), optional PNG preview (--png)

The layout is tools/picture_map.py; this file is the content.
The module has no Grashey image; that view stays text only. Each elbow check shows the
slide's normal films, and the same slide's abnormal films become a finding of their own.

    python3 tools/pathways/src/msk-w9-02_2.py --pdf "<Upper Limb Radiology.pdf>" \
        --gct "<vault>/Attachments/giant cell tumour of the distal radius - lecture slide.jpg" \
        --out "<vault>/Attachments/upper extremity radiology overview.svg" --png /tmp/p.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import picture_map  # noqa: E402

# picture_map's CROPS shape, keeping the annotated panel where a slide pairs a plain film
# with a labelled one
CROPS = {
    "bone": ((13, 0), (0.52, 0, 1, 1)),
    "ap_shoulder": ((17, 0), (0.5, 0, 1, 1)),
    "y_view": ((20, 0), (0.5, 0, 1, 1)),
    "axillary": ((21, 0), (0.333, 0, 0.667, 1)),
    "oa_shoulder": ((28, 1), (0, 0, 0.5, 1)),
    "neck_fracture": ((30, 0), (0.5, 0, 1, 1)),
    "dislocation": ((31, 0), (0.645, 0.07, 1, 1)),   # drops the drawing and an "RG" mark
    "ap_elbow": ((33, 0), (0.52, 0, 1, 1)),
    "lat_elbow": ((39, 0), (0, 0, 1, 1)),             # p34's labelled lateral carries a logo
    "fat_pads": ((41, 0), (0, 0, 1, 1)),
    "effusion": [((41, 1), (0, 0, 1, 1)), ((41, 2), (0, 0, 1, 1))],   # normal | effusion
    "humeral_line": ((42, 0), (0, 0, 0.475, 1)),          # two normal children
    "supracondylar": ((42, 0), (0.49, 0, 1, 1)),          # line off the capitellum's centre
    "radiocapitellar": ((44, 0), (0, 0, 0.454, 1)),       # normal A-D
    "radiocapitellar_abn": ((44, 0), (0.535, 0, 1, 1)),
    "oa_elbow": ((45, 0), (0.5, 0, 1, 1)),
    "lipoma": ((46, 0), (0.5, 0, 1, 1)),
    "carpals": ((50, 0), (0.53, 0, 1, 1)),
    "lat_wrist": ((51, 0), (0.5, 0, 1, 1)),
    "gilula": ((53, 0), (0, 0, 1, 1)),
    "scaphoid": ((54, 0), (0.5, 0, 1, 1)),
    "radius_fracture": ((55, 0), (0.53, 0, 1, 1)),
}

# A card: title, picture (or None), lines. "• " lines hang-indent; **x** is bold.
ROOT = {
    "title": "Read every upper-limb X-ray the same way",
    "img": "bone",
    "lines": [
        "1 · **Skeletal maturity**: physis (growth plate) visible and unfused = immature · fused = mature",
        "2 · **Bone**: cortex, medulla, density, generalized bone disease",
        "3 · **Alignment**: fracture, dislocation",
        "4 · **Joints**: inflammation, narrowing, degeneration",
        "5 · **Soft tissues**: abnormal even when the bones look normal",
        "Bone pathology, **TIMS-C**: Trauma, tumours · Infection, inflammatory, idiopathic · "
        "Metabolic, malignancy · Systemic, senile (osteoarthritis) · Congenital",
    ],
}

BANDS = [
    {"name": "SHOULDER", "colour": "teal", "rows": [
        {"label": "STANDARD SERIES (trauma, osteoarthritis): AP · Y-view · Grashey",
         "note": "No Grashey image in this year's module. It also reads the axillary view.",
         "cards": [
             {"title": "AP (front-to-back)", "img": "ap_shoulder", "lines": [
                 "• **Anatomical neck** = head–neck junction",
                 "• **Surgical neck** = just below the head (a reference line, not a structure)",
                 "• Labrum = fibrocartilage, does **not** show"]},
             {"title": "Y-view (trans-scapular)", "img": "y_view", "lines": [
                 "• Y = coracoid (anterior) + spine and acromion (posterior) + scapular body",
                 "• **Humeral head centred over the glenoid**"]},
             {"title": "Axillary", "img": "axillary", "lines": [
                 "• Beam through the armpit",
                 "• **Coracoid + lesser tuberosity = anterior**: orients the film",
                 "• Os acromiale (unfused) is **not** a fracture"]},
         ]},
        {"label": "FINDINGS", "cards": [
            {"title": "Dislocation: the Y-view decides", "img": "dislocation", "kind": "bad", "lines": [
                "• **Anterior** = head under the coracoid (**subcoracoid**)",
                "• **Posterior** = head farther from the coracoid",
                "• Subluxation = partial contact · dislocation = complete loss"]},
            {"title": "Surgical neck fracture", "img": "neck_fracture", "kind": "bad", "lines": [
                "• Fracture line along the surgical neck, mild displacement"]},
        ]},
    ]},
    {"name": "ELBOW", "colour": "purple", "rows": [
        {"label": "STANDARD VIEWS: AP · lateral", "cards": [
            {"title": "AP", "img": "ap_elbow", "lines": [
                "• Orient by the **medial epicondyle (bigger)** and the ulna (medial)",
                "• Medial → lateral: medial epicondyle · trochlea · **capitellum** · lateral epicondyle",
                "• Sublime tubercle = ulnar collateral ligament attachment"]},
            {"title": "Lateral", "img": "lat_elbow", "wide": True, "lines": [
                "• Ulna: **olecranon, trochlear notch, coronoid**: all fracture-prone",
                "• Radius: head, neck, **tuberosity** (biceps)",
                "• **The best view for alignment**"]},
        ]},
        {"label": "CHECK ON THE LATERAL: fat pads + two lines (normal films)", "cards": [
            {"title": "Fat pads", "img": "fat_pads", "lines": [
                "• Anterior fat pad = **normal**",
                "• Posterior fat pad: **not normally seen**",
                "• Olecranon bursa: not normally distended"]},
            {"title": "Anterior humeral line", "img": "humeral_line", "lines": [
                "• Along the anterior humeral cortex → **centre of the capitellum** (slight variation is fine)",
                "• Wider physis = younger child"]},
            {"title": "Radiocapitellar line", "img": "radiocapitellar", "lines": [
                "• Along the radial shaft → **centre of the capitellum on EVERY view** (AP, oblique, lateral)"]},
        ]},
        {"label": "FINDINGS: TRAUMA", "cards": [
            {"title": "Effusion: posterior fat pad sign", "img": "effusion", "kind": "bad", "lines": [
                "• Normal (left) | prominent anterior + **visible posterior fat pad** (right)",
                "• **Posterior fat pad seen = ALWAYS abnormal**",
                "• Child → **supracondylar fracture** · adult → **radial head or neck fracture**"]},
            {"title": "Supracondylar fracture (child)", "img": "supracondylar", "kind": "bad", "lines": [
                "• Anterior humeral line through the **anterior part** of the capitellum",
                "• + elevated posterior fat pad + open physis"]},
            {"title": "Radiocapitellar line misses", "img": "radiocapitellar_abn", "kind": "bad", "lines": [
                "• Supracondylar fractures, one with an elevated posterior fat pad",
                "• Last film: **anterior radial head dislocation**, the head fully in front of the capitellum"]},
        ]},
        {"label": "FINDINGS: SOFT TISSUES (osteoarthritis: see the last band)", "cards": [
            {"title": "Soft-tissue mass, normal bones", "img": "lipoma", "kind": "bad", "lines": [
                "• Well-defined, low-density oval mass = **lipoma** (confirmed on CT or MRI)",
                "• **Always look at the soft tissues**"]},
        ]},
    ]},
    {"name": "WRIST", "colour": "orange", "rows": [
        {"label": "STANDARD VIEWS: AP · lateral, then the arcs of Gilula on the AP", "cards": [
            {"title": "AP: carpal bones, radial → ulnar", "img": "carpals", "lines": [
                "• Proximal row: **scaphoid, lunate, triquetrum, pisiform**",
                "• Distal row: **trapezium, trapezoid, capitate, hamate**",
                "• Distal radioulnar joint, radial + ulnar styloids",
                "• TFCC (triangular fibrocartilage complex) is radiolucent: calcification there = TFCC problem"]},
            {"title": "Lateral", "img": "lat_wrist", "lines": [
                "• **Lister's tubercle** (dorsal radius): check it for fracture",
                "• Carpals overlap, so **the AP is essential for fractures**"]},
            {"title": "Arcs of Gilula (AP)", "img": "gilula", "lines": [
                "1 · Proximal surfaces of the proximal row",
                "2 · Distal surfaces of the proximal row",
                "3 · Proximal surfaces of the distal row",
                "• **Break, step-off or widening → carpal injury**"]},
        ]},
        {"label": "FINDINGS: check every bone, since a fracture can keep the arcs intact", "cards": [
            {"title": "Scaphoid + triquetrum fractures", "img": "scaphoid", "kind": "bad", "lines": [
                "• Lucent line through the scaphoid's proximal pole and the triquetrum",
                "• Arcs preserved"]},
            {"title": "Distal radius + ulnar styloid", "img": "radius_fracture", "kind": "bad", "lines": [
                "• Transverse distal radius fracture + ulnar styloid base",
                "• Arcs intact"]},
            {"title": "Giant cell tumour of bone", "img": "gct", "kind": "bad", "wide": True, "lines": [
                "• **Expanded** distal radius, large **lytic** lesion",
                "• Markedly thinned cortex",
                "• Reaches the subarticular surface"]},
        ]},
    ]},
    {"name": "OSTEOARTHRITIS", "colour": "brown", "rows": [
        {"label": "ANY JOINT = 3 FINDINGS, graded mild, moderate or severe on the combination", "cards": [
            {"title": "The three findings", "img": None, "lines": [
                "1 · **Joint space narrowing** (cartilage is radiolucent, so lost cartilage narrows the gap)",
                "2 · **Subchondral sclerosis** (denser, not stronger)",
                "3 · **Marginal osteophytes**"]},
            {"title": "Shoulder", "img": "oa_shoulder", "lines": [
                "• Narrowing, sclerosis and osteophytes at the glenohumeral joint"]},
            {"title": "Elbow", "img": "oa_elbow", "lines": [
                "• Osteophytes + **intra-articular bony bodies**"]},
        ]},
    ]},
]


if __name__ == "__main__":
    picture_map.main(__doc__, ROOT, BANDS, CROPS, extras=("gct",))
