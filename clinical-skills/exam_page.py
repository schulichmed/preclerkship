"""
Purpose: The shared engine for every clinical skills exam page (msk-exam is the first). It reads
         an exam's vault note "Summary Notes - <System> Clinical Skills" and renders the page:
         the clinical skills bar, the root-to-regions fan, a colour band per region opening on
         its spine card and TOSCE line, the tests grouped side by side under the problem you
         suspect (picture, steps, positive, video), the pearls, search, Look/Test modes, credits.
Author: Noor Simsam
Date: 2026-10-28
Input: an Exam (one per <system>-exam/build.py): the note path, its regions, tests, videos and
       page text; the exam folder's img/credits.json and videos json files
Output: <system>-exam/index.html

Every exam page looks like this one: an exam's build.py holds only what is particular to that
exam, and anything about how a page looks or reads its note changes here, for all of them.
The page sits in the same portal shell as the topic pages topic.py builds (clinical-skills/build.py's
head, block bar, masthead and footer, styled by the portal's base.css and portal.css), so moving
between an exam and any other clinical skills page is seamless; its tab title and the eyebrow
come from the exam's row in SKILLS.
"""

import html
import importlib.util
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

LOG = logging.getLogger("exam_page")

# the clinical skills hub's build: its exam_nav() bar opens every exam page
_spec = importlib.util.spec_from_file_location("clinical_skills", Path(__file__).resolve().parent / "build.py")
clinical_skills = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clinical_skills)


@dataclass
class Exam:
    """What is particular to one exam page; everything else is shared.

    Attributes
    ----------
    key : str
        The exam's key in SKILLS in clinical-skills/build.py (lights it in the bar).
    folder : Path
        The exam's folder (<system>-exam/), holding img/, img/credits.json and the videos json.
    note : Path
        The vault note, the single source of the steps and findings.
    regions : dict
        Section number in the note -> (key, title, week, colour), in teaching order. Each region
        section holds its spine bullets, then one test table, then its pearls.
    general : list
        (section number, card title) for the note's opening sections, shown as the first band.
    tests : dict
        Test name as the note's table shows it -> (problem heading, picture in img/ or None).
    opening : dict
        Region key -> the TOSCE sentence said before that region's exam.
    h1, lead, find, root, root_note, video_credit : str
        Page text: the heading, the lead paragraph (HTML),
        the search placeholder, the spine shown at the root of the fan and its note (HTML), and who
        the videos are by (HTML).
    general_title, general_week, general_color : str
        The first band's header.
    spine_heading, spine_title : str
        Heading and card title of the spine card each region opens on.
    pearls_heading : str
        Heading of the card that closes each region.
    count_noun : str
        What a region's band header counts ("special tests", "manoeuvres").
    region_text : dict
        Region key -> {count_noun, spine_title, landmark_caption}, any of which overrides the
        exam-wide wording for that one region (neuro's "levels" and "The approach").
    video : dict
        Test name -> slug in the main channel's videos.json.
    video_page : str
        The main channel's page for a slug, with {slug} in it.
    region_video : dict
        Region key or general card title -> slugs of its videos.
    other_video : dict
        Test name -> {id, start, title, channel}: a YouTube video from another channel.
    clips : dict
        Test name, region key or general card title -> list of {mp4, title, page, secs}: video
        files played straight from their host (a course library such as Western's Health
        Education Media Library), each in a <video> made only when tapped.
    extra_cards : dict
        Region key -> test cards the note gives as prose, not table rows (MSK's Ottawa rules).
    walk : dict
        Region key or general card title -> list of {id, title, channel}: YouTube walkthroughs
        shown on that spine card, played only when tapped.
    """

    key: str
    folder: Path
    note: Path
    regions: dict
    general: list
    tests: dict
    opening: dict
    h1: str
    lead: str
    find: str
    root: str
    root_note: str
    video_credit: str
    general_title: str = "General exam"
    general_week: str = ""
    general_color: str = "#4a4f63"
    spine_heading: str = "General exam"
    spine_title: str = "Look · Feel · Move"
    pearls_heading: str = "Pearls"
    count_noun: str = "special tests"
    # what a card's two hidden parts are called: a history page asks and listens instead
    steps_label: str = "Steps"
    pos_label: str = "Positive"
    region_text: dict = field(default_factory=dict)
    video: dict = field(default_factory=dict)
    video_page: str = ""
    region_video: dict = field(default_factory=dict)
    other_video: dict = field(default_factory=dict)
    clips: dict = field(default_factory=dict)
    extra_cards: dict = field(default_factory=dict)
    walk: dict = field(default_factory=dict)
    # region key -> {test name: (problem, picture)}, overriding tests for that region only
    region_tests: dict = field(default_factory=dict)
    # region_video from the course's own suggested list (MSK Medicine for MSK) plays before
    # Hamzah Algodi's walk-throughs; a teaching channel picked for the page (Geeky Medics) plays after
    official_region_video: bool = False
    videos: dict = field(default_factory=dict, init=False)


def opening(exam: Exam, key: str) -> str:
    """The sentence that opens a region's exam in a TOSCE."""
    if key not in exam.opening:
        return ""
    return f'<p class="say"><b>Say first:</b> "{exam.opening[key]}"</p>'


def other_video(exam: Exam, name: str) -> str:
    """Render a click-to-play video from another channel (YouTube loads only when tapped)."""
    v = exam.other_video[name]
    start = f"&start={v['start']}" if v.get("start") else ""
    page = f"https://www.youtube.com/watch?v={v['id']}{start.replace('&start=', '&t=')}"
    return (f'<button class="vid" data-yt="{v["id"]}" data-start="{v.get("start", 0)}" data-page="{page}">'
            f'<span>▶ {html.escape(v["title"])} ({html.escape(v["channel"])})</span></button>')


def clips(exam: Exam, key: str) -> str:
    """Render the tap-to-play buttons for the video files filed under a test, region or card."""
    out = []
    for v in exam.clips.get(key, []):
        secs = f" ({v['secs'] // 60}:{v['secs'] % 60:02d})" if v.get("secs") else ""
        out.append(f'<button class="vid" data-mp4="{html.escape(v["mp4"])}" data-page="{html.escape(v["page"])}">'
                   f'<span>▶ {html.escape(v["title"])}{secs}</span></button>')
    return "".join(out)


def walks(exam: Exam, key: str) -> str:
    """Render the tap-to-play YouTube walkthroughs filed under a region or card."""
    return "".join(
        f'<button class="vid" data-yt="{v["id"]}" data-start="0" data-page="https://www.youtube.com/watch?v={v["id"]}">'
        f'<span>▶ {html.escape(v["title"])} ({html.escape(v["channel"])})</span></button>'
        for v in exam.walk.get(key, []))


def video(exam: Exam, slug: str, thumb: bool = False) -> str:
    """Render a click-to-play video from the exam's main channel (YouTube loads only when tapped).

    Parameters
    ----------
    exam : Exam
        The exam, for its videos.json and the channel's page address.
    slug : str
        The video's slug in videos.json.
    thumb : bool
        Show the video's thumbnail as the button, for the spine cards.

    Returns
    -------
    str
        HTML for the button, or a plain link when the page has no video.
    """
    v = exam.videos[slug]
    page = exam.video_page.format(slug=slug)
    title = html.escape(v["title"])
    if not v["id"]:
        return f'<a class="vid link" href="{page}" target="_blank" rel="noopener">{title} (page)</a>'
    img = (f'<img src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="" loading="lazy">'
           if thumb else "")
    return (f'<button class="vid{" big" if thumb else ""}" data-yt="{v["id"]}" data-page="{page}">{img}'
            f'<span>▶ {title}</span></button>')


def inline(md: str) -> str:
    """Convert the note's inline markdown (wikilinks, bold) to HTML text.

    Parameters
    ----------
    md : str
        One table cell.

    Returns
    -------
    str
        Escaped HTML: <b> for bold, ==highlights== dropped, and a tag for
        "(advanced: <session>)" and "(extra: ...)".
    """
    md = re.sub(r"\[\[[^\]|\\]*\\?\|([^\]]*)\]\]", r"\1", md)
    md = re.sub(r"\[\[([^\]]*)\]\]", r"\1", md)
    out = html.escape(md, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"==(.+?)==", r"\1", out)  # the note's objective highlights stay in the vault, off the page
    out = re.sub(r"\(advanced:\s*([^()]+)\)", r'<span class="tag">later: \1</span>', out)
    return re.sub(r"\(extra:\s*([^()]+)\)", r'<span class="tag" title="\1">extra</span>', out)


def plain(md: str) -> str:
    """Return a cell as plain text, for matching test names."""
    return re.sub(r"<[^>]+>", "", html.unescape(inline(md))).strip()


def read_sections(path: Path) -> dict[int, list[str]]:
    """Split the note into its numbered sections.

    Parameters
    ----------
    path : Path
        The summary note.

    Returns
    -------
    dict
        Section number -> the lines under its heading (heading excluded).
    """
    sections: dict[int, list[str]] = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        head = re.match(r"## (\d+)\. ", line)
        if head:
            current = int(head.group(1))
            sections[current] = []
        elif line.startswith("**High-yield") or line.startswith("**Image credits"):
            current = None
        elif current is not None:
            sections[current].append(line)
    return sections


def md_block(lines: list[str]) -> str:
    """Render the note's prose (paragraphs, nested bullets, tables) as HTML.

    Image embeds are dropped: the page shows only openly licensed pictures.

    Parameters
    ----------
    lines : list of str
        Markdown lines from one part of a section.

    Returns
    -------
    str
        HTML.
    """
    out, depth, table = [], 0, []

    def close_lists(to: int) -> None:
        nonlocal depth
        while depth > to:
            out.append("</li></ul>")
            depth -= 1

    def flush_table() -> None:
        if not table:
            return
        rows = [[inline(c.strip()).replace("&lt;br&gt;", "<br>") for c in re.split(r"(?<!\\)\|", r)[1:-1]]
                for r in table if not r.startswith("| ---")]
        head = "".join(f"<th>{c}</th>" for c in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows[1:])
        out.append(f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        table.clear()

    for line in lines:
        if line.startswith("|"):
            close_lists(0)
            table.append(line)
            continue
        flush_table()
        if not line.strip() or line.strip().startswith("![[") or line.strip() == "---":
            continue
        bullet = re.match(r"( *)- (.*)", line)
        if bullet:
            level = len(bullet.group(1)) // 2 + 1
            if level > depth:
                while depth < level:
                    out.append("<ul><li>")
                    depth += 1
            else:
                close_lists(level)
                out.append("</li><li>")
            out.append(inline(bullet.group(2)))
        else:
            close_lists(0)
            out.append(f"<p>{inline(line)}</p>")
    close_lists(0)
    flush_table()
    return "".join(out)


def split_region(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split a region section into the spine lines (look, feel, move for MSK) before its test table
    and the pearls after it."""
    first = next(i for i, l in enumerate(lines) if l.startswith("|"))
    last = max(i for i, l in enumerate(lines) if l.startswith("|"))
    return lines[:first], lines[last + 1:]

def read_note(exam: Exam) -> list[dict]:
    """Read every test row of the note's region tables, with its section number.

    Parameters
    ----------
    exam : Exam
        The exam, for its note and regions.

    Returns
    -------
    list of dict
        One dict per row: section, name, for, steps, pos.
    """
    rows, section = [], None
    for line in exam.note.read_text(encoding="utf-8").splitlines():
        head = re.match(r"## (\d+)\. ", line)
        if head:
            section = int(head.group(1))
            continue
        if section not in exam.regions or not line.startswith("| ") or line.startswith("| ---"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) < 4 or cells[2] in ("Steps", exam.steps_label) or cells[1] == "Looks for":
            continue
        steps = [re.sub(r"^\d+\.\s*", "", s) for s in cells[2].split("<br>")]
        # a leading "N. " on the name numbers the card (the order to do the region's tests in)
        num = re.match(r"(\d+)\.\s+", cells[0])
        cells[0] = cells[0][num.end():] if num else cells[0]
        # an advanced or extra tag on the name moves to the looks-for line, so the name stays the key
        tags = re.findall(r"\((?:advanced|extra):[^()]+\)", cells[0])
        name = re.sub(r"\s*\((?:advanced|extra):[^()]+\)", "", cells[0])
        rows.append({"section": section, "num": num.group(1) if num else "", "name": plain(name), "for": inline(" ".join([cells[1], *tags])),
                     "steps": [inline(s) for s in steps], "pos": inline(cells[3])})
    return rows


def build_regions(exam: Exam, rows: list[dict], sections: dict[int, list[str]]) -> list[dict]:
    """Group the note's rows into regions and, inside each, problem headings.

    Parameters
    ----------
    exam : Exam
        The exam, for its regions, general sections and test map.
    rows : list of dict
        Output of read_note.
    sections : dict
        Output of read_sections, for each region's spine and pearls.

    Returns
    -------
    list of dict
        The general band, then the regions in note order, each with its
        problems in first-seen order.
    """
    missing = [r["name"] for r in rows if r["name"] not in exam.tests]
    if missing:
        sys.exit(f"tests not mapped in tests: {missing}")
    regions = []
    if exam.general:
        regions.append({"key": "general", "title": exam.general_title, "week": exam.general_week,
                        "color": exam.general_color, "exam": None, "pearls": None,
                        "wide": [(title, md_block(sections[num])) for num, title in exam.general],
                        "problems": []})
    for num, (key, title, week, color) in exam.regions.items():
        before, after = split_or_all(sections[num])
        regions.append({"key": key, "title": title, "week": week, "color": color,
                        "exam": md_block(before), "pearls": md_block(after), "wide": []})
        regions[-1]["problems"] = problems_for(exam, rows, num, key)
    return regions


def split_or_all(lines: list[str]) -> tuple[list[str], list[str]]:
    """split_region, for a region whose section has no test table yet: all of it is the spine."""
    return split_region(lines) if any(l.startswith("|") for l in lines) else (lines, [])


def problems_for(exam: Exam, rows: list[dict], num: int, key: str) -> list[dict]:
    """Group one region's tests under their problem headings."""
    problems: dict[str, list] = {}
    for r in (r for r in rows if r["section"] == num):
        problem, img = exam.region_tests.get(key, {}).get(r["name"]) or exam.tests[r["name"]]
        problems.setdefault(problem, []).append({**r, "img": img})
    for extra in exam.extra_cards.get(key, []):
        problems.setdefault(extra["problem"], []).append(extra)
    return [{"name": k, "tests": v} for k, v in problems.items()]


def card(exam: Exam, t: dict) -> str:
    """Render one test card."""
    img = (f'<img src="img/{t["img"]}" alt="{html.escape(t["name"])}" loading="lazy">'
           if t.get("img") else "")
    steps = "".join(f"<li>{s}</li>" for s in t["steps"])
    words = " ".join([t["name"], re.sub(r"<[^>]+>", "", t["for"])]).lower()
    return (f'<article class="test" tabindex="0" data-words="{html.escape(words)}">'
            f'<h4>{f"""<span class="num">{t["num"]}.</span> """ if t.get("num") else ""}{html.escape(t["name"])}</h4><p class="for">{t["for"]}</p>{img}'
            f'<div class="hide h1"><span class="lbl">{html.escape(exam.steps_label)}</span><ol>{steps}</ol></div>'
            f'<div class="hide h2 pos"><span class="lbl">{html.escape(exam.pos_label)}</span><p>{t["pos"]}</p></div>'
            f'{f"""<div class="hide h2 vids">{video(exam, exam.video[t["name"]])}</div>""" if t["name"] in exam.video else ""}'
            f'{f"""<div class="hide h2 vids">{other_video(exam, t["name"])}</div>""" if t["name"] in exam.other_video else ""}'
            f'{f"""<div class="hide h2 vids">{clips(exam, t["name"])}</div>""" if t["name"] in exam.clips else ""}'
            f'<span class="pill">Tap to reveal</span></article>')


def wide_card(exam: Exam, title: str, body: str, slugs: list[str] | None = None, side: str = "",
              clip_key: str = "") -> str:
    """Render a full-width card of prose (a spine routine, gait, pearls), with its
    videos and a picture (side) beside the text when given; clip_key names its video files."""
    words = (title + " " + re.sub(r"<[^>]+>", " ", body)).lower()
    # official videos first (the course's suggested list), then Hamzah's, then the library's
    # range-of-motion clips folded into their own "Movements" accordion
    moves = exam.clips.get(clip_key, []) if clip_key else []
    walk = walks(exam, clip_key) if clip_key else ""
    region = "".join(video(exam, v, thumb=i == 0 and not (side or walk)) for i, v in enumerate(slugs or []))
    side += region + walk if exam.official_region_video else walk + region
    if moves:
        side += (f'<details class="acc moves"><summary>Movements ({len(moves)})</summary>'
                 f'<div>{clips(exam, clip_key)}</div></details>')
    return (f'<article class="test wide" tabindex="0" data-words="{html.escape(words)}">'
            f'<h4>{html.escape(title)}</h4><div class="hide h1 split"><div class="xprose">{body}</div>'
            f'{f"""<div class="aside">{side}</div>""" if side else ""}</div>'
            f'<span class="pill">Tap to reveal</span></article>')


def landmarks(exam: Exam, key: str) -> str:
    """Render the region's labelled landmark diagram (img/<key>-landmarks.jpg), when there is one."""
    name = f"{key}-landmarks.jpg"
    if not (exam.folder / "img" / name).exists():
        return ""
    caption = exam.region_text.get(key, {}).get("landmark_caption")
    alt = f"{html.escape(next(r[1] for r in exam.regions.values() if r[0] == key))} diagram" if caption else f"Landmarks to feel: {key}"
    return (f'<figure class="lm"><a href="img/{name}" target="_blank" rel="noopener">'
            f'<img src="img/{name}" alt="{alt}" loading="lazy"></a>'
            f'<figcaption>{html.escape(caption) if caption else "Landmarks to feel · tap to enlarge"}</figcaption></figure>')


def render(exam: Exam, regions: list[dict], credits: list[dict]) -> str:
    """Render the whole page."""
    chips = "".join(f'<a class="rchip" href="#{r["key"]}" style="--c:{r["color"]}">'
                    f'<b>{r["title"]}</b><span>{r["week"]}</span></a>' for r in regions)
    bands = []
    for r in regions:
        wides = [("", t, b, exam.region_video.get(t), "", t) for t, b in r["wide"]]
        if r["exam"]:
            wides.insert(0, (exam.spine_heading, exam.region_text.get(r["key"], {}).get("spine_title", exam.spine_title), opening(exam, r["key"]) + r["exam"],
                             exam.region_video.get(r["key"]), landmarks(exam, r["key"]), r["key"]))
        top = "".join(f'<div class="prob">{f"<h3>{html.escape(h)}</h3>" if h else ""}'
                      f'<div class="tests">{wide_card(exam, t, b, v, side, k)}</div></div>' for h, t, b, v, side, k in wides)
        probs = "".join(f'<div class="prob" style="--n:{min(len(p["tests"]), 4)}"><h3>{html.escape(p["name"])}</h3>'
                        f'<div class="tests">{"".join(card(exam, t) for t in p["tests"])}</div></div>'
                        for p in r["problems"])
        probs = f'<div class="probs">{probs}</div>'
        foot = (f'<div class="prob"><h3>{html.escape(exam.pearls_heading)}</h3><div class="tests">'
                f'{wide_card(exam, "Remember", r["pearls"])}</div></div>' if r["pearls"] else "")
        n = sum(len(p["tests"]) for p in r["problems"])
        noun = exam.region_text.get(r["key"], {}).get("count_noun", exam.count_noun)
        count = f" · {n} {noun}" if n else ""
        bands.append(f'<section class="band" id="{r["key"]}" style="--c:{r["color"]}">'
                     f'<header class="bandhead"><h2>{r["title"]}</h2><span>{r["week"]}{count}</span></header>'
                     f'{top}{probs}{foot}</section>')
    landmark_names = {f"Landmarks: {key}": (f"{title} diagram" if "landmark_caption" in exam.region_text.get(key, {})
                                            else f"{title} landmarks diagram")
                      for key, title, _w, _c in exam.regions.values()}
    # only a web address is linked: drawn pictures and textbook figures from student notes have none
    source = lambda c: (f', <a href="{html.escape(c["source_page_url"])}">source</a>'
                        if c["source_page_url"].startswith("http") else "")
    items = "".join(
        f'<li>{html.escape(landmark_names.get(c["test"], c["test"]))}: {html.escape(c["author"])}, {html.escape(c["licence"])}'
        f'{source(c)}</li>' for c in credits)
    cred = (f'<details class="acc"><summary>Image credits ({len(credits)})</summary><p>Images used for non-commercial teaching under their own licences '
            f'(Creative Commons or public domain; textbook figures from student notes remain their publishers&#39; copyright). Some were cropped to hide faces or handwriting.</p><ul>{items}</ul></details>') if credits else ""
    cs = clinical_skills
    sec, _key, name, taught, _page, _what = next(s for s in cs.SKILLS if s[1] == exam.key)
    sec_name = next(s[1] for s in cs.SECTIONS if s[0] == sec)
    eyebrow = f"Schulich Clinical Skills &middot; {html.escape(sec_name)} &middot; " + " &rarr; ".join(cs.COURSES[c] for c in taught)
    fill = {"HEAD": cs.head(f"{name} - Clinical skills"), "NAV": cs.exam_nav(exam.key), "FOOT": cs.FOOT,
            "EYEBROW": eyebrow,
            "H1": exam.h1, "LEAD": exam.lead, "FIND": exam.find, "ROOT": exam.root, "ROOT_NOTE": exam.root_note,
            "VIDEO_CREDIT": exam.video_credit, "COLS": str(len(regions)), "EDGE": f"{50 / len(regions):.1f}",
            "CHIPS": chips, "BANDS": "".join(bands), "CREDITS": cred}
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", lambda m: fill[m.group(1)], PAGE)


PAGE = """{{HEAD}}<style>
/* the exam's own pieces, in the portal's tokens (base.css): --card-bg, --text, --border, --accent */
.xm{--card:var(--card-bg);--ink:var(--text);--line:var(--border);--ok:#2f6b4f;--ok-bg:#e9f4ee;--rail:#6b6380;font-size:15px;line-height:1.5}
:root[data-theme="dark"] .xm{--ok:#7fd1a6;--ok-bg:#16291f;--rail:#a89fbb}
html{scroll-behavior:smooth}
.q-masthead .lead a{color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.xm h2,.xm h3{font-family:var(--serif);font-weight:600;margin:0;letter-spacing:-.01em}
.bar{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(6px);padding:10px 0;margin:4px 0 6px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-bottom:1px solid var(--line)}
.mode{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--card)}
.mode button{border:0;background:none;color:var(--ink);font:500 .85rem var(--sans);padding:7px 14px;cursor:pointer}
.mode button[aria-pressed="true"]{background:var(--q-accent,var(--accent));color:#fff}
.bar input{flex:1;min-width:180px;font:.88rem var(--sans);padding:8px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
.hint{font-size:.8rem;color:var(--muted);width:100%;margin:0}
/* the tree: root fans out to every region */
.tree{margin-top:22px}
.root{background:#201436;color:#fff;border-radius:12px;padding:12px 16px;text-align:center;max-width:760px;margin:0 auto}
.root b{font-family:var(--serif);font-size:18px;font-weight:600}
.root p{margin:4px 0 0;color:#d8cfe8;font-size:14px}
.stem{width:2px;height:18px;background:var(--rail);margin:0 auto}
.fan{display:grid;grid-template-columns:repeat({{COLS}},1fr);gap:8px;position:relative;padding-top:18px}
.fan::before{content:"";position:absolute;top:0;left:{{EDGE}}%;right:{{EDGE}}%;height:2px;background:var(--rail)}
.rchip{position:relative;display:block;text-align:center;text-decoration:none;color:#fff;background:var(--c);border-radius:10px;padding:8px 6px}
.rchip::before{content:"";position:absolute;top:-18px;left:50%;width:2px;height:12px;background:var(--rail)}
.rchip::after{content:"";position:absolute;top:-7px;left:calc(50% - 5px);border:5px solid transparent;border-top:6px solid var(--rail)}
.rchip b{display:block;font-size:14px}.rchip span{font-size:12px;opacity:.9}
@media (max-width:980px){.fan{grid-template-columns:repeat(5,1fr);padding-top:12px}.fan::before,.rchip::before,.rchip::after{display:none}.stem{display:none}}
@media (max-width:420px){.fan{grid-template-columns:repeat(2,1fr)}}
/* region bands */
.band{margin-top:28px;border-radius:14px;padding:10px;background:color-mix(in srgb,var(--c) 9%,transparent);scroll-margin-top:110px}
.bandhead{background:var(--c);color:#fff;border-radius:10px;padding:9px 14px;display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
.bandhead h2{font-size:22px}.bandhead span{font-size:13px;opacity:.9}
.prob{margin-top:12px}
.prob h3{font-size:16px;color:color-mix(in srgb,var(--c) 80%,var(--ink));margin:0 4px 6px}
.probs{display:flex;flex-wrap:wrap;gap:0 14px}
.probs>.prob{flex:var(--n) 1 calc(var(--n) * 250px + (var(--n) - 1) * 10px);min-width:0;max-width:calc(var(--n) * 380px + (var(--n) - 1) * 10px)}
.say{margin:0 0 8px;padding:8px 10px;border-left:3px solid var(--c);background:color-mix(in srgb,var(--c) 8%,var(--card));border-radius:6px}
.tests{display:grid;align-items:start;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
.test{background:var(--card);border:1.5px solid color-mix(in srgb,var(--c) 45%,var(--line));border-radius:10px;padding:10px 12px;position:relative;outline-offset:2px}
.test h4{margin:0;font-size:15px}.test h4 .num{color:var(--c)}
.test .for{margin:2px 0 6px;color:var(--muted);font-size:13px}
.test img{display:block;width:100%;height:170px;object-fit:contain;background:#fff;border-radius:8px;border:1px solid var(--line);margin-bottom:6px}
.test ol{margin:2px 0 0;padding-left:20px;font-size:13.5px}.test ol li{margin:2px 0}
.lbl{display:block;font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-top:6px}
.pos{background:var(--ok-bg);border-radius:8px;padding:2px 8px 6px;margin-top:8px}
.pos .lbl{color:var(--ok)}.pos p{margin:2px 0 0;font-size:13.5px}
.pill{display:none}
.vids{margin-top:8px}
.vid{display:flex;align-items:center;gap:6px;width:100%;text-align:left;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 8px;font:500 13px var(--sans);cursor:pointer;margin-top:6px;text-decoration:none}
.vid:hover{border-color:var(--c)}
.vid.big{flex-direction:column;align-items:stretch;padding:0;overflow:hidden}
.vid.big img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.vid.big span{padding:6px 8px}
.player{position:relative;aspect-ratio:16/9;margin-top:6px;border-radius:8px;overflow:hidden;background:#000}
.player iframe,.player video{position:absolute;inset:0;width:100%;height:100%;border:0;background:#000}
.split{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:16px}
@media (max-width:760px){.split{grid-template-columns:1fr}}
.aside .lm{margin:0}.aside .lm img{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
.aside figcaption{font-size:12px;color:var(--muted);margin-top:2px}
.test.wide{grid-column:1/-1}
.xprose{font-size:13.5px}.xprose ul{margin:4px 0;padding-left:20px}.xprose li{margin:2px 0}.xprose p{margin:6px 0}
.tw{overflow-x:auto;margin:6px 0}.xprose table{border-collapse:collapse;width:100%;font-size:13px}
.xprose th,.xprose td{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
.xprose th{background:color-mix(in srgb,var(--c) 14%,var(--card))}
.test.gone{display:none}.prob.gone,.band.gone{display:none}
/* test mode: reveal steps, then the positive */
body.quiz .test{cursor:pointer}
body.quiz .test .hide{display:none}
body.quiz .test[data-s="1"] .h1,body.quiz .test[data-s="2"] .h1,body.quiz .test[data-s="2"] .h2{display:block}
body.quiz .test:not([data-s="2"]) .pill{display:inline-block;margin-top:8px;font-size:12px;font-weight:600;color:var(--c);border:1px solid var(--c);border-radius:999px;padding:2px 10px}
body.quiz.hideimg .test img{display:none}
.tag{display:inline-block;font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:0 7px;margin-left:2px;vertical-align:1px}
.credits{margin-top:40px;font-size:12.5px;color:var(--muted)}.credits .credits ul{padding-left:18px}.acc{border:1px solid var(--line);border-radius:10px;margin-top:10px;background:var(--card)}
.acc>summary{cursor:pointer;padding:10px 14px;font-weight:600;font-size:14px;color:var(--ink);list-style:none;display:flex;justify-content:space-between;align-items:center}
.acc>summary::-webkit-details-marker{display:none}
.acc>summary::after{content:"+";font-size:18px;color:var(--muted)}
.acc[open]>summary::after{content:"-"}
.acc>p,.acc>ul{margin:0 14px 12px}
.acc.moves{border-radius:8px}.acc.moves>summary{padding:6px 8px;font-size:13px}.acc.moves>div{padding:0 8px 8px}.acc>ul{padding-left:18px}
:focus-visible{outline:3px solid var(--accent)}
</style>
{{NAV}}

<header class="q-masthead" id="content" tabindex="-1">
<div>
<p class="eyebrow">{{EYEBROW}}</p>
<h1>{{H1}}</h1>
<p class="lead">{{LEAD}}</p>
</div>
</header>

<main class="xm">
<div class="bar">
<div class="mode" role="group" aria-label="Mode"><button data-m="look" aria-pressed="true">Look</button><button data-m="quiz" aria-pressed="false">Test</button><button data-m="blind" aria-pressed="false">Test, no pictures</button></div>
<input type="search" id="q" placeholder="{{FIND}}">
<p class="hint" id="hint">Look: everything shown. Pick a region below to jump to it.</p>
</div>
<div class="tree">
<div class="root"><b>{{ROOT}}</b>
<p>{{ROOT_NOTE}}</p></div>
<div class="stem"></div>
<nav class="fan">{{CHIPS}}</nav>
</div>
{{BANDS}}
<section class="credits"><details class="acc"><summary>Video credits</summary><p>{{VIDEO_CREDIT}}</p></details>{{CREDITS}}</section>
</main>
<script>
(function(){
  var body=document.body, hint=document.getElementById('hint');
  var hints={look:'Look: everything shown. Pick a region below to jump to it.',
    quiz:'Test: say the steps, then tap the card to check them; tap again for the positive finding.',
    blind:'Test, no pictures: picture the test from its name alone, then tap to check.'};
  document.querySelectorAll('.mode button').forEach(function(b){
    b.addEventListener('click',function(){
      document.querySelectorAll('.mode button').forEach(function(x){x.setAttribute('aria-pressed',x===b)});
      var m=b.dataset.m; body.classList.toggle('quiz',m!=='look'); body.classList.toggle('hideimg',m==='blind');
      document.querySelectorAll('.test').forEach(function(t){t.dataset.s='0'});
      hint.textContent=hints[m];
    });
  });
  function step(t){ if(!body.classList.contains('quiz'))return; t.dataset.s=String(Math.min(2,(+t.dataset.s||0)+1)); }
  document.querySelectorAll('.test').forEach(function(t){
    t.addEventListener('click',function(e){if(!e.target.closest('summary'))step(t)});
    t.addEventListener('keydown',function(e){if(e.target.closest('summary'))return;if(e.key==='Enter'||e.key===' '){e.preventDefault();step(t)}});
  });
  document.addEventListener('click',function(e){
    var b=e.target.closest('.vid[data-yt],.vid[data-mp4]'); if(!b)return; e.stopPropagation();
    var d=document.createElement('div'); d.className='player';
    if(b.dataset.mp4){var v=document.createElement('video');v.src=b.dataset.mp4;v.controls=true;v.autoplay=true;v.playsInline=true;v.preload='metadata';
      d.appendChild(v);b.replaceWith(d);return;}
    d.innerHTML='<iframe src="https://www.youtube-nocookie.com/embed/'+b.dataset.yt+'?autoplay=1&rel=0'+(+b.dataset.start?'&start='+b.dataset.start:'')+'" title="'+b.textContent.replace(/"/g,'')+'" allow="autoplay; encrypted-media; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>';
    b.replaceWith(d);
  },true);
  document.getElementById('q').addEventListener('input',function(e){
    var q=e.target.value.trim().toLowerCase();
    document.querySelectorAll('.prob').forEach(function(p){
      var h=p.querySelector('h3'), ph=h?h.textContent.toLowerCase():'', any=false;
      p.querySelectorAll('.test').forEach(function(t){
        var words=t.dataset.words||t.textContent.toLowerCase();
        var hit=!q||ph.indexOf(q)>-1||words.indexOf(q)>-1; t.classList.toggle('gone',!hit); any=any||hit;});
      p.classList.toggle('gone',!any);
    });
    document.querySelectorAll('.band').forEach(function(b){b.classList.toggle('gone',!b.querySelector('.prob:not(.gone)'))});
  });
})();
</script>
{{FOOT}}"""


# Published pages describe where material came from in general terms ("student notes"), never by naming
# course documents, decks, facilitators or year-above packages. The vault notes keep the detail; this
# pass rewrites the rendered text. Order matters: the specific phrases go first.
PUBLIC_WORDING = [
    (r"\s*\((?:from the )?upper-year notes\)", ""),
    (r"\(upper-year mnemonic ", "(mnemonic "),
    (r"\s*\(the Geriatrics page in the course material is empty\)", ""),
    (r"\s*\(the Paeds page in the course material is empty, and the upper-year notes have no paediatric exam\)", ""),
    (r"\s*\(the slide table\)", ""),
    (r"(?i)(not) in (?:her |the )?course material or the (?:upper-year |student )notes", r"\1 covered by the sources used here"),
    (r"The Year 2 POCUS page in the course material is (?:<[^>]+>)*empty(?:<[^>]+>)* ?, and the (?:upper-year|student) notes do not cover these views",
     "No source covers these views in detail"),
    (r"The Year 2 POCUS page in the course material is\s+empty\s*, and the (?:upper-year|student) notes do not cover these views", "No source covers these views in detail"),
    (r"the objectives name them, but the faculty page is empty, so only", "the objectives name them, but no source covers them, so only"),
    (r"Openings for vital signs, respiratory and musculoskeletal come from course material;.*?textbook approach",
     "Openings come from the course objectives, student notes and the standard textbook approach"),
    (r"because no faculty slides were found for this session", "because the session has no further notes"),
    (r"\(the session has no slides in the course notebook\)", "(the session has no further notes)"),
    (r"the deck itself covers only", "the course covers only"),
    (r"\(the syllabus says", "(the course objectives say"),
    (r"the course syllabi", "the course objectives"),
    (r"Built from the course Clinical Skills material", "Built from the course Clinical Skills objectives"),
    (r"[Tt]he faculty assessment form for the primary physical exam skills", "The assessment form for the primary physical exam skills"),
    (r"The course material guide stops", "The course guide stops"),
    (r"not in the course material", "not in the course objectives"),
    (r"an upper-year student was told by a facilitator this earns a mark", "students report this earns a mark"),
    (r"an upper-year student flagged this as a marked step", "students flag this as a marked step"),
    (r"an upper-year package described stations", "student accounts describe stations"),
    (r"as the upper-year package put it", "as student accounts put it"),
    (r"The only safety items in the upper-year notes are", "The only safety items covered are"),
    (r"[Tt]he upper-year notes give", "Student notes give"),
    (r"upper-year (?:student )?(?:notes|templates)", "student notes"),
    (r"upper-year", "student"),
    (r"faculty facilitator", "faculty examiner"),
    (r"your facilitator's due date", "the due date"),
    (r"facilitators", "group leaders"),
    (r"facilitator", "group leader"),
    (r"[Ff]aculty OB/Gyne [Hh]istory (?:Gathering )?[Rr]eference", "course OB/Gyne history reference"),
    (r"[Ff]aculty [Ii]nterviewing [Tt]emplate", "course interviewing template"),
    (r"The faculty reference details", "The course reference details"),
    (r"No faculty notes back this( block)? yet", r"No course notes cover this\1 yet"),
]


def public_text(page: str) -> str:
    """Rewrite course-material wording across a rendered page, search words included.

    The phrases are plain words that appear in no tag or script, so the whole page is rewritten;
    case is ignored because the search words are lower-cased copies of the text.
    """
    for pattern, repl in PUBLIC_WORDING:
        page = re.sub(pattern, repl, page, flags=re.S | re.I)
    return page


def build(exam: Exam) -> None:
    """Write <exam folder>/index.html from the exam's note.

    Parameters
    ----------
    exam : Exam
        The exam to build.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    videos = exam.folder / "videos.json"
    exam.videos = json.loads(videos.read_text(encoding="utf-8")) if videos.exists() else {}
    sections = read_sections(exam.note)
    regions = build_regions(exam, read_note(exam), sections)
    credits_path = exam.folder / "img/credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else []
    used = {t["img"] for r in regions for p in r["problems"] for t in p["tests"] if t.get("img")}
    used |= {f"{r['key']}-landmarks.jpg" for r in regions
             if (exam.folder / "img" / f"{r['key']}-landmarks.jpg").exists()}
    for name in used:
        if not (exam.folder / "img" / name).exists():
            sys.exit(f"missing picture img/{name}")
    uncredited = used - {c["slug"] for c in credits}
    if uncredited:
        sys.exit(f"pictures with no entry in img/credits.json: {sorted(uncredited)}")
    credits = [c for c in credits if c["slug"] in used]
    (exam.folder / "index.html").write_text(public_text(render(exam, regions, credits)), encoding="utf-8")
    n = sum(len(p["tests"]) for r in regions for p in r["problems"])
    LOG.info("wrote %d tests in %d regions, %d pictures", n, len(regions), len(used))
