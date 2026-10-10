# Pathway specs

One JSON file per drawn pathway figure, rendered by `tools/pathway_svg.py`
into the vault's `Attachments/<name>.svg`, which the lecture note embeds as
`![[<name>.svg]]` where its mermaid flowchart used to be. The exemplar is
[osteoporosis_pathway.json](osteoporosis_pathway.json); read it before
writing a new one.

```bash
python tools/pathway_svg.py tools/pathways/<id>.json --out <where>.svg --png <preview>.png
```

The exit code is 1 on a layout error (a word wider than its box, two boxes
overlapping, an edge to an unknown node). Warnings (an edge crossing a box, a
label sitting on a box) print but pass; the preview decides those.

## How to turn a mermaid flowchart into a spec

The mermaid chart is the source of the facts. The spec changes the drawing,
not the content:

- Every node, label and fact in the mermaid chart appears in the spec. Nothing
  is added that the chart or the note under it does not say. Where a mermaid
  node is a long run-on, split it into a `title` and `lines`, but keep the
  words.
- The reader follows the flow top to bottom, left to right, without any arrow
  crossing a box or another arrow. Place the boxes by hand (`x`, `y`, `w`) on
  a 920 px canvas; let `h` follow from the text unless a row of boxes should
  share a height.
- A decision ("Early or late?") is a plain box whose title ends in `?`; its
  answers are the edge labels. Keep labels short (one to four words) and give
  each one a `label_at` where the midpoint would sit on an arrow or box.
- "Any ONE of these" rows at the top (diagnosis criteria, indications) use
  `any_of`: free-standing boxes with OR between them. Use it only when the
  chart really is "any one of"; most charts have no such row.
- A `-.-` link in mermaid means "goes with", not "leads to": draw it with
  `"dashed": true`, or fold the attached box into a `panels` entry (a titled
  bullet list, like the risk factors) under the chart.

## Colour is for outcomes

Steps, questions and tests stay `plain`. Colour marks what the reader is
looking for:

| kind | use |
|---|---|
| `ok` | the answer, treat, yes, normal |
| `warn` | intermediate, suggest, caution, borderline |
| `bad` | no, stop, do not treat, danger, abnormal |
| `anti` / `ana` | two drug families or two arms that must stay distinct (teal, purple) |
| `info` | one neutral highlight (a key number, a named test) |
| `lo` | a plain step the mermaid marked `class X lo` (a learning objective) |
| `dark` | a root heading bar; rarely needed now that `any_of` exists |

A chart with every box coloured says nothing. Three or four coloured boxes on a
plain chart is usual; the osteoporosis exemplar has eight across fourteen boxes
only because it ends in two drug families.

Lines starting with `~` are drawn muted and italic: a qualifier ("everyone
gets this too", "on a bone density scan"), not a fact.

## Checking the drawing

Render the preview and look at it. Then check, in this order:

1. Every fact in the mermaid chart is in the picture, and nothing else is.
2. No text touches a box edge; no arrow crosses a box; no two arrows cross
   where they could be routed apart; no label sits on an arrow.
3. The flow reads in one direction, and the coloured boxes are the outcomes.

Fix the spec, not the SVG.
