/* The notes half of a PoM 2 block page.

   data/notes/<slug>.json carries the block's whole lecture roster, taken from
   the vault folders, not only the lectures that have a note. A lecture with
   "hasNote": false renders as a dashed gap, so this view doubles as a map of
   what is still left to write - the same reasoning that keeps an empty question
   set visible on the other tab.

   The rail carries an index of every lecture in the block. A block runs to 36
   notes of a page or more each, so the week chips narrow the stream but cannot
   get you to a named lecture; the index is the way in, and it marks the note
   you are reading as you scroll.

   Any note can be sent to PDF on its own, or a whole week at once, so it can be
   annotated by hand afterwards. That runs through the browser's own print
   dialogue: the page marks what should survive, prints, and unmarks.

   Mermaid is only fetched if some lecture in this block actually has a pathway,
   and any pathway can be opened full size in its own tab - inside the stream a
   wide diagram is squeezed into the column and its labels shrink with it. */

(function () {
  "use strict";

  var BLOCK = window.QUIZ_BLOCK;

  var WEEKS = [];
  var NOTES_DRAFT = "";    // the block-wide draft warning, when the block has one
  var WK = Object.create(null);   // lecture id -> week key
  var week = "all";
  var booted = false;

  var IDX = Object.create(null);  // lecture id -> its row in the index
  var AT = Object.create(null);   // lecture id -> its place in the stream
  var CURRENT = null;             // the note the index is pointing at
  var PENDING = null;             // a clicked note whose scroll is still running
  var SETTLE = null;              // the jump still re-checking where it landed

  var query = "";                 // the search box, lowercased and trimmed
  var WORDS = [];                 // the query split by the rule in portal.js
  // the painting rule, its floor and its budget, is portal.js's as well
  var HITS = [];                  // every <mark> on the page, in reading order
  var AT_HIT = -1;                // which one the reader is standing on
  var HAY = Object.create(null);  // lecture id -> everything in it, lowercased
  var TITLE = Object.create(null);  // lecture id -> its number and name, lowercased
  var MARKED = [];                // notes currently carrying highlights
  var QT = null;                  // the keystroke debounce

  function byId(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function html(tag, cls, markup) {
    var n = el(tag, cls);
    if (markup) n.innerHTML = markup;
    return n;
  }

  function lectures() {
    var out = [];
    WEEKS.forEach(function (w) {
      (w.lectures || []).forEach(function (l) { out.push(l); });
    });
    return out;
  }

  /* Two lectures in a roster can carry the same id - endo week 3 has such a
     pair - and a repeated element id makes the second note unreachable: the
     index, the filter and getElementById all find the first one. The roster is
     the thing to fix, but the page must not mis-navigate while it is wrong, so
     every lecture gets a key that is unique on this page and the rest of the
     file addresses notes by that. */
  function assignKeys() {
    var used = Object.create(null);
    lectures().forEach(function (lec) {
      var base = lec.id || "lec", k = base, n = 2;
      while (used[k]) { k = base + "--" + (n++); }
      used[k] = true;
      lec.key = k;
    });
  }

  /* ---------- printing ---------- */

  /* The browser's print dialogue is the only PDF writer a static page has, and
     it is the right one - it produces a normal PDF that any annotator can mark
     up. Everything not in scope is hidden for the duration of the print. */
  function printScope(nodes) {
    var marked = [];
    nodes.forEach(function (n) { n.classList.add("print-me"); marked.push(n); });
    document.body.dataset.printing = "notes";

    /* Print is light: the stylesheets drop the dark tokens under print on
       their own, but a pathway is an SVG with the dark colours drawn into it,
       so a dark page goes light for the duration, its diagrams are drawn
       again, and the print waits for them. Ctrl+P skips this and prints the
       diagrams as drawn; there is no way to wait on a redraw from there. */
    var root = document.documentElement;
    var wasDark = root.getAttribute("data-theme") === "dark";
    if (wasDark) root.setAttribute("data-theme", "light");

    /* Two things can end a print, afterprint and the timer below, and the
       timer is the one that fires late: once afterprint has put the page
       back, the reader may have switched theme, and a second restore would
       undo that. So the restore runs once, the timer is cancelled when
       afterprint gets there first, and what it restores is the reader's
       choice as it stands now, the theme from before the print only when
       nothing is stored. */
    var timer = null, done = false;
    function clear() {
      if (done) return;
      done = true;
      clearTimeout(timer);
      marked.forEach(function (n) { n.classList.remove("print-me"); });
      delete document.body.dataset.printing;
      if (wasDark) {
        var chosen = null;
        try { chosen = localStorage.getItem("pc-theme"); } catch (e) {}
        root.setAttribute("data-theme", chosen === "light" || chosen === "dark" ? chosen : "dark");
      }
      window.removeEventListener("afterprint", clear);
    }
    window.addEventListener("afterprint", clear);
    // afterprint does not fire everywhere, so do not rely on it alone
    timer = setTimeout(clear, 60000);

    /* Two triggers for one redraw: portal.js redraws on its own whenever
       data-theme changes, and this call is the same redraw asked for
       explicitly, because the print has to wait on its promise. */
    redrawPathways().then(function () { window.print(); });
  }

  function printNote(art) {
    printScope([art]);
  }

  function printWeek(weekbar) {
    var nodes = [weekbar], n = weekbar.nextElementSibling;
    while (n && !n.classList.contains("weekbar")) {
      if (n.classList.contains("note") && !n.classList.contains("is-gap")
          && !n.classList.contains("is-covered")) nodes.push(n);
      n = n.nextElementSibling;
    }
    printScope(nodes);
  }

  function printAll() {
    var nodes = [].slice.call(
      document.querySelectorAll(
        "#note-stream .weekbar, #note-stream .note:not(.is-gap):not(.is-covered)"));
    printScope(nodes);
  }

  /* The note renderer is portal.js's, shared with the bank's note dialog.
     Looked up when called rather than at load, because portal.js is the
     later script tag on the page. */
  function shared() { return window.PORTAL_NOTES; }
  function written(lec) { return shared().written(lec); }
  function pdfButton(label, title, onClick) { return shared().pdfButton(label, title, onClick); }
  function displayName(lec) { return shared().displayName(lec); }
  /* a placeholder or a list row is an in-class session too, and says so the
     same way the note does */
  function addInClassTag(box, lec) { if (lec.inClass) box.appendChild(shared().inClassTag()); }
  function redrawPathways() { var s = shared(); return s.redrawPathways ? s.redrawPathways() : Promise.resolve(); }

  /* The search rule and the highlighter are portal.js's too, shared with the
     bank so the two boxes mean the same thing by a query. Checked rather than
     assumed: a page without them keeps its stream and index, unnarrowed. */
  function search() { return window.PORTAL_SEARCH; }

  /* ---------- one note may carry several lectures ---------- */

  function buildCovered(lec) {
    var art = el("article", "note is-covered");
    art.id = "n-" + lec.key;
    art.dataset.id = lec.key;
    var head = el("div", "note-head");
    head.appendChild(el("span", "note-num", lec.num));
    addInClassTag(head, lec);
    head.appendChild(el("h4", null, displayName(lec)));
    art.appendChild(head);

    var p = el("p", "covernote");
    p.appendChild(document.createTextNode("Written up with "));
    var a = el("button", "coverlink", lec.coveredBy.num + " · " + lec.coveredBy.name);
    a.type = "button";
    a.addEventListener("click", function () { goTo(lec.coveredBy.key); });
    p.appendChild(a);
    art.appendChild(p);
    return art;
  }

  function buildGap(lec) {
    var art = el("article", "note is-gap");
    art.id = "n-" + lec.key;
    art.dataset.id = lec.key;
    var head = el("div", "note-head");
    head.appendChild(el("span", "note-num", lec.num));
    addInClassTag(head, lec);
    head.appendChild(el("h4", null, displayName(lec)));
    art.appendChild(head);
    art.appendChild(el("span", "gapnote", "no note yet"));
    return art;
  }

  /* ---------- the lecture index ---------- */

  function buildIndex() {
    var box = byId("note-index");
    /* a page cached from before the index shipped still has to work */
    if (!box) return;
    var frag = document.createDocumentFragment();

    WEEKS.forEach(function (w) {
      var k = weekKey(w);
      var g = el("p", "lecgroup", k === "off" ? "Unscheduled" : "Week " + k);
      g.dataset.k = k;
      frag.appendChild(g);

      (w.lectures || []).forEach(function (lec) {
        var row = el("button", "lecrow"
          + (lec.hasNote === true ? "" : lec.coveredBy ? " is-covered" : " is-gap"));
        row.type = "button";
        row.dataset.id = lec.key;
        row.dataset.k = k;
        row.setAttribute("aria-current", "false");
        row.appendChild(el("span", "ln", lec.num));
        addInClassTag(row, lec);
        row.appendChild(el("span", "lt", displayName(lec)));
        // the row clips, so the whole name has to be reachable some other way
        row.title = lec.num + " \u00b7 " + (lec.inClass ? "In-class \u00b7 " : "") + displayName(lec);
        row.addEventListener("click", function () { goTo(lec.key); });
        IDX[lec.key] = row;
        frag.appendChild(row);
      });
    });

    box.appendChild(frag);
  }

  /* the filter bar is pinned over the top of the notes, so a note brought to
     the top has to land below it rather than under it */
  function barH() {
    /* where the bar's bottom edge sits once pinned: below the course nav, which
       is pinned too on a wide screen */
    var f = byId("note-filter");
    if (!f) return 0;
    return (parseFloat(window.getComputedStyle(f).top) || 0) + f.offsetHeight;
  }

  /* keep --nf-h at the bar's height, which wraps on a narrow window and grows a
     line when a search is counting hits; the sticky rail sits below it */
  function initFilterBar() {
    var f = byId("note-filter"), shell = byId("panel-notes");
    if (!f || !shell) return;
    function set() { shell.style.setProperty("--nf-h", f.offsetHeight + "px"); }
    set();
    if (window.ResizeObserver) new window.ResizeObserver(set).observe(f);
    else window.addEventListener("resize", set);
  }

  /* the same scroll the questions tab does, so a jump from the rail and a jump
     from the position bar put a note in the same place */
  /* spot, when given, is a word inside the note to land on instead of the
     note's top, held mid-screen so the sentence around it is in view */
  function goTo(id, spot) {
    var art = byId("n-" + id);
    if (!art) return;
    var at = spot || art;
    function gap() {
      return spot ? (window.innerHeight - spot.getBoundingClientRect().height) / 2 : 16 + barH();
    }
    PENDING = id;
    mark(id);
    var still = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function aim(smooth) {
      var top = Math.max(0, at.getBoundingClientRect().top + window.pageYOffset - gap());
      try { window.scrollTo({ top: top, behavior: smooth ? "smooth" : "auto" }); }
      catch (e) { window.scrollTo(0, top); }
    }
    aim(!still);

    /* The target is worked out once, but the page does not hold still while
       the scroll travels: lazy figures load as it passes them (most PoM 1
       figures carry no size, so nothing reserves their space) and diagrams
       swap source for taller SVG, all of which pushes the note further down.
       So once the scroll comes to rest, look again, and snap to the note if
       it has moved. Stops when the note is in place, when the page cannot
       scroll any further, after a few tries, or when the reader takes over. */
    var token = SETTLE = {}, tries = 0, lastY = -1, quiet = 0;
    function settle() {
      if (SETTLE !== token) return;
      var y = window.pageYOffset;
      if (y !== lastY) { lastY = y; quiet = 0; }
      else if (++quiet >= 6) {
        var off = at.getBoundingClientRect().top - gap();
        var atEnd = off > 0 &&
          y + window.innerHeight >= document.documentElement.scrollHeight - 1;
        if (Math.abs(off) < 2 || atEnd || ++tries > 8) { SETTLE = null; return; }
        aim(false);
        quiet = 0;
      }
      window.requestAnimationFrame(settle);
    }
    window.requestAnimationFrame(settle);
  }

  function mark(id) {
    if (CURRENT === id) return;
    if (CURRENT && IDX[CURRENT]) IDX[CURRENT].setAttribute("aria-current", "false");
    CURRENT = id;

    var row = IDX[id], box = byId("note-index");
    if (!row || !box) return;
    row.setAttribute("aria-current", "true");

    /* the index scrolls in its own right once it outgrows the rail, so the
       marked row has to be brought back into view - scrollIntoView would take
       the page with it, which is the one thing it must not do here */
    var top = row.offsetTop, bot = top + row.offsetHeight;
    if (top < box.scrollTop) box.scrollTop = top - 4;
    else if (bot > box.scrollTop + box.clientHeight) {
      box.scrollTop = bot - box.clientHeight + 4;
    }
  }

  /* Position is read from an IntersectionObserver for the reasons the questions
     tab gives: asking every note where it is on each scroll event costs frames,
     and a hidden note never intersects, so the week filter falls out of it for
     free. The sight line is the top fifth of the viewport.

     A browser without IntersectionObserver keeps a working index - you can
     still jump from it, it just does not follow you. */
  function initSpy() {
    if (!window.IntersectionObserver) return;
    var inView = Object.create(null);
    var notes = [].slice.call(document.querySelectorAll("#note-stream .note"));

    AT = Object.create(null);
    notes.forEach(function (a, i) { AT[a.dataset.id] = i; });

    var obs = new window.IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var id = e.target.dataset.id;
        if (e.isIntersecting) inView[id] = true;
        else delete inView[id];
      });

      /* At the top of the page the answer is always the first lecture listed,
         so it is not worth asking. Worth saying out loud, because the observer
         delivers its first batch before the web fonts and any diagrams have
         settled - at that moment the masthead has no height and half the block
         is briefly up at the sight line, which is enough to mark a lecture two
         weeks away and leave it there. */
      if (window.pageYOffset < 8) {
        var top = document.querySelector("#note-index .lecrow:not([hidden])");
        if (top) mark(top.dataset.id);
        return;
      }

      /* The questions tab takes the FIRST note crossing the line, because a
         question is a paragraph and the one above you is the one you are on.
         A note is pages long, so the same rule marks the lecture you have just
         left: if the next heading has reached the top of the screen, you have
         arrived at it. Hence the last one crossing, not the first. */
      var best = null, bestAt = -1;
      Object.keys(inView).forEach(function (id) {
        if (AT[id] !== undefined && AT[id] > bestAt) { bestAt = AT[id]; best = id; }
      });
      if (!best) return;

      /* A click owns the mark until its scroll actually arrives, or the index
         strobes through every note the page travels past on the way. Waiting
         for the arrival rather than running a timer matters here: the stream is
         90,000 pixels tall, and a smooth scroll across two weeks takes longer
         than any interval worth guessing at. */
      if (PENDING) {
        if (best !== PENDING) return;
        PENDING = null;
      }
      mark(best);
    }, { rootMargin: "0px 0px -80% 0px" });

    notes.forEach(function (a) { obs.observe(a); });

    /* ...unless the reader takes the wheel before it gets there, in which case
       they have changed their mind and the index should follow them, not the
       jump they walked away from */
    ["wheel", "touchstart", "keydown"].forEach(function (ev) {
      window.addEventListener(ev, function () { PENDING = null; SETTLE = null; }, { passive: true });
    });
  }

  /* ---------- search ---------- */

  /* What gets searched is the note as it was rendered, read back off the page
     rather than re-derived from the JSON. A note is a title, a framing
     paragraph, tables, callouts and key points in whatever order they were
     written, and textContent already carries all of it. Re-walking the blocks
     here would be a second parser that could disagree with the first.

     A lecture with no note still has its number and name in the haystack, so
     searching for one finds the gap where it will go rather than nothing. */
  function indexText() {
    lectures().forEach(function (lec) {
      var art = byId("n-" + lec.key);
      TITLE[lec.key] = (lec.num + " " + lec.name).toLowerCase();
      HAY[lec.key] = (lec.num + " " + lec.name + " " +
                      (art ? art.textContent : "")).toLowerCase();
    });
  }

  /* ---------- best match first ---------- */

  /* A search across a block of 40 notes still leaves a dozen or more that hold
     every word, most of them in passing. So while there is a query the stream
     and the index both run best match first (the score is portal.js's), the
     week headings step aside since the order is no longer by week, and the
     roster order comes back the moment the box is cleared.

     The nodes are moved rather than restyled: hits are walked, and the index
     marks the note being read, in document order, and moving the nodes keeps
     both of those true without teaching either about a second order. */
  var ORIG_STREAM = [], ORIG_INDEX = [];
  var RANKED = false;

  function snapshotOrder() {
    var s = byId("note-stream"), x = byId("note-index");
    ORIG_STREAM = s ? [].slice.call(s.children) : [];
    ORIG_INDEX = x ? [].slice.call(x.children) : [];
  }

  function reorder(box, nodes) {
    if (!box) return;
    var frag = document.createDocumentFragment();
    nodes.forEach(function (n) { frag.appendChild(n); });
    box.appendChild(frag);
  }

  /* refreshes the spy's idea of which note comes after which */
  function reindexAt() {
    AT = Object.create(null);
    [].forEach.call(document.querySelectorAll("#note-stream .note"), function (a, i) {
      AT[a.dataset.id] = i;
    });
  }

  function applyOrder(shownKeys) {
    var stream = byId("note-stream"), index = byId("note-index");
    var s = search();
    if (!WORDS.length || !s || !s.score) {
      if (RANKED) {
        reorder(stream, ORIG_STREAM);
        reorder(index, ORIG_INDEX);
        RANKED = false;
        reindexAt();
      }
      return;
    }
    var pos = Object.create(null);
    shownKeys.forEach(function (k, i) { pos[k] = i; });
    var score = Object.create(null);
    shownKeys.forEach(function (k) { score[k] = s.score(HAY[k] || "", TITLE[k] || "", WORDS); });
    var ranked = shownKeys.slice().sort(function (a, b) {
      return (score[b] - score[a]) || (pos[a] - pos[b]);
    });

    /* the head stays on top and the empty line at the foot; everything the
       filter hid keeps its roster order below the ranked notes, out of sight */
    var head = [], tail = [];
    ORIG_STREAM.forEach(function (n) {
      if (n.classList.contains("note") || n.classList.contains("weekbar")) {
        if (!(n.dataset.id in pos)) tail.push(n);
      } else if (n.id === "note-empty") tail.push(n);
      else head.push(n);
    });
    reorder(stream, head.concat(ranked.map(function (k) { return byId("n-" + k); })
                                      .filter(Boolean), tail));

    var rows = ranked.map(function (k) { return IDX[k]; }).filter(Boolean);
    reorder(index, rows.concat(ORIG_INDEX.filter(function (n) { return rows.indexOf(n) === -1; })));
    RANKED = true;
    reindexAt();
  }

  /* every word of the query, in any order, somewhere in the note: the bank's
     rule, and now this tab's */
  function hit(id) {
    var s = search();
    return !WORDS.length || !!(s && s.hit(HAY[id] || "", WORDS));
  }

  function unmark() {
    if (search()) search().unmark(MARKED);
    MARKED = [];
  }

  /* .pathway is skipped because mermaid parses that element's own text, and a
     <mark> inside it is a syntax error rather than a highlight. */
  function markHits(art, words, budget) {
    var s = search();
    if (!s) return 0;
    var made = s.mark(art, words, budget, ".pathway");
    if (made) MARKED.push(art);
    return made;
  }

  /* Filtering tells you WHICH notes hold the word; this walks you to the word
     itself, which is what Ctrl+F does and what the filter alone did not. The
     hits are collected in document order after a pass, so Next runs down the
     page rather than through the notes in roster order.

     The browser's own Ctrl+F is not a substitute: a note the filter has hidden
     is `hidden`, and find-in-page will not see inside it. */
  function collectHits() {
    HITS = [].slice.call(document.querySelectorAll("#note-stream mark.hit"));
    AT_HIT = -1;
    paintNav();
  }

  function paintNav() {
    var bar = byId("note-nav");
    if (!bar) return;
    bar.hidden = !query || !HITS.length;
    var pos = byId("note-nav-pos");
    if (pos) {
      var n = HITS.length + (capped() ? "+" : "");
      // before the first step there is no position to report, only a total
      pos.textContent = !HITS.length ? ""
        : AT_HIT < 0 ? n + (HITS.length === 1 ? " match" : " matches")
        : (AT_HIT + 1) + " of " + n;
    }
  }

  /* The budget stops painting part-way through a very common word, so the
     count has to say it is a floor rather than a total. */
  function capped() {
    var s = search();
    return !!s && HITS.length >= s.MARK_BUDGET;
  }

  function goHit(step) {
    if (!HITS.length) return;
    if (AT_HIT >= 0 && HITS[AT_HIT]) HITS[AT_HIT].classList.remove("on");
    AT_HIT = (AT_HIT + step + HITS.length) % HITS.length;
    var m = HITS[AT_HIT];
    m.classList.add("on");

    /* Centred rather than put at the top: a hit is a word inside a paragraph
       and the sentence around it is the reason you are looking at it. */
    var box = m.getBoundingClientRect();
    var mid = box.top + window.pageYOffset - (window.innerHeight / 2) + (box.height / 2);
    var still = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    try { window.scrollTo({ top: Math.max(0, mid), behavior: still ? "auto" : "smooth" }); }
    catch (e) { window.scrollTo(0, Math.max(0, mid)); }

    // the rail should follow the reader to the note they have landed in
    var art = m.closest && m.closest(".note");
    if (art && art.dataset.id) {
      PENDING = art.dataset.id;
      mark(art.dataset.id);
    }
    paintNav();
  }

  function setQuery(v) {
    var next = (v || "").replace(/^\s+|\s+$/g, "").toLowerCase();
    if (next === query) return;
    query = next;
    WORDS = search() ? search().words(query) : [];
    var clear = byId("note-q-clear");
    if (clear) clear.hidden = !query;
    applyFilter();
  }

  /* ---------- filter ---------- */

  /* Week numbers run across the whole year, not from 1 inside each block - msk
     starts at 7 - so the chip is labelled with the number the roster carries.
     The number, not w.label: those are long enough to be headings, not chips. */
  function weekKey(w) { return (w && w.n != null) ? String(w.n) : "off"; }

  function weekDefs() {
    var defs = [{ k: "all", label: "All", n: lectures().length }];
    WEEKS.forEach(function (w) {
      var k = weekKey(w);
      defs.push({
        k: k,
        label: k === "off" ? "Unscheduled" : "Week " + k,
        n: (w.lectures || []).length
      });
    });
    return defs;
  }

  function matches(lec) {
    return (week === "all" || WK[lec.key] === week) && hit(lec.key);
  }

  function applyFilter() {
    var shown = 0;
    /* every highlight from the last query comes off before this one goes on,
       and a note that is about to be hidden is left clean rather than carrying
       marks nobody can see */
    unmark();
    var s = search();
    var paint = s ? s.paintWords(WORDS) : [];
    var budget = paint.length ? s.MARK_BUDGET : 0;
    var shownKeys = [];
    lectures().forEach(function (lec) {
      var art = byId("n-" + lec.key);
      if (!art) return;
      var ok = matches(lec);
      art.hidden = !ok;
      if (ok) { shown++; shownKeys.push(lec.key); }
    });

    /* ordered before painting, so the mark budget is spent on the best notes
       rather than on whichever came first in the roster */
    applyOrder(shownKeys);
    [].forEach.call(document.querySelectorAll("#note-stream .note:not([hidden])"), function (art) {
      if (budget > 0) budget -= markHits(art, paint, budget);
    });

    // a week heading survives only while a lecture under it is still visible,
    // and not at all while the stream is ranked rather than in week order
    [].forEach.call(document.querySelectorAll("#note-stream .weekbar"), function (h) {
      if (RANKED) { h.hidden = true; return; }
      var any = false, n = h.nextElementSibling;
      while (n && !n.classList.contains("weekbar")) {
        if (n.classList.contains("note") && !n.hidden) { any = true; break; }
        n = n.nextElementSibling;
      }
      h.hidden = !any;
    });

    /* the index carries the same filter as the stream, read off the rows rather
       than from a lookup, so a roster that repeats an id cannot leave a row
       behind that never hides */
    [].forEach.call(document.querySelectorAll("#note-index .lecrow"), function (row) {
      row.hidden = !((week === "all" || row.dataset.k === week) &&
                     hit(row.dataset.id));
    });

    /* the week headings inside the index earn their line only on All, where the
       numbering restarts at 01 once per week and would otherwise be unreadable.
       A search thins the rows under them, so a heading left with nothing beneath
       it goes too - otherwise the rail reads as a list of empty weeks. */
    [].forEach.call(document.querySelectorAll("#note-index .lecgroup"), function (g) {
      if (week !== "all" || RANKED) { g.hidden = true; return; }
      var any = false, n = g.nextElementSibling;
      while (n && !n.classList.contains("lecgroup")) {
        if (n.classList.contains("lecrow") && !n.hidden) { any = true; break; }
        n = n.nextElementSibling;
      }
      g.hidden = !any;
    });

    /* Nothing is marked before the first scroll, because at the top of the page
       no note has reached the sight line yet - and the note the index was
       pointing at may have just been filtered away. Either way, fall back to the
       first lecture still listed; the observer corrects it to wherever the
       reader actually is as soon as one fires. */
    if (!CURRENT || (IDX[CURRENT] && IDX[CURRENT].hidden)) {
      if (CURRENT && IDX[CURRENT]) IDX[CURRENT].setAttribute("aria-current", "false");
      CURRENT = null;
      var first = document.querySelector("#note-index .lecrow:not([hidden])");
      if (first) mark(first.dataset.id);
    }

    byId("note-empty").hidden = shown > 0;
    collectHits();
    paintHits(shown);
    paintChips();
  }

  function paintHits(shown) {
    var line = byId("note-q-count");
    if (!line) return;
    // a query with no word past the floor narrows nothing, so it has no count
    line.hidden = !WORDS.length;
    line.textContent = shown === 1 ? "1 lecture matches"
                                   : shown + " lectures match, best first";
  }

  function counts() {
    var all = lectures();
    return { all: all.length, written: all.filter(written).length };
  }

  function paintChips() {
    [].forEach.call(document.querySelectorAll("#note-week-chips .chip"), function (b) {
      b.setAttribute("aria-pressed", week === b.dataset.k ? "true" : "false");
    });
  }

  function paintCoverage() {
    var c = counts();
    var tc = byId("tc-notes");
    if (tc) tc.textContent = c.written + "/" + c.all;

    var all = byId("print-all");
    if (all) all.disabled = c.written === 0;
  }

  /* ---------- boot ---------- */

  function buildRail() {
    /* a page cached from before the week filter shipped still has to work */
    var box = byId("note-week-chips");
    if (box) {
      weekDefs().forEach(function (d) {
        var b = el("button", "chip");
        b.type = "button";
        b.dataset.k = d.k;
        b.setAttribute("aria-pressed", d.k === "all" ? "true" : "false");
        b.appendChild(document.createTextNode(d.label));
        b.appendChild(el("span", "n", String(d.n)));
        b.addEventListener("click", function () { week = d.k; applyFilter(); });
        box.appendChild(b);
      });
    }

    buildSearch();
    buildIndex();
  }

  function buildSearch() {
    /* a page cached from before the search shipped still has to work */
    var box = byId("note-q");
    if (!box) return;

    /* Debounced, because every keystroke re-filters the stream and re-walks
       the text nodes of whatever still matches. 150ms is below the gap between
       two typed characters and above the cost of one pass. */
    box.addEventListener("input", function () {
      if (QT) window.clearTimeout(QT);
      QT = window.setTimeout(function () { setQuery(box.value); }, 150);
    });
    box.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.keyCode === 27) {
        box.value = "";
        setQuery("");
        return;
      }
      if (e.key === "Enter" || e.keyCode === 13) {
        /* Enter would submit if this box were ever wrapped in a form, and the
           debounce may not have run yet on a fast typist's last keystroke. */
        e.preventDefault();
        if (QT) { window.clearTimeout(QT); QT = null; setQuery(box.value); }
        goHit(e.shiftKey ? -1 : 1);
      }
    });

    var clear = byId("note-q-clear");
    if (clear) {
      clear.addEventListener("click", function () {
        box.value = "";
        setQuery("");
        box.focus();
      });
    }

    var prev = byId("note-nav-prev"), next = byId("note-nav-next");
    if (prev) prev.addEventListener("click", function () { goHit(-1); });
    if (next) next.addEventListener("click", function () { goHit(1); });

    document.addEventListener("keydown", function (e) {
      /* "/" jumps to the box, as it does in the bank; portal.js holds the
         guards, among them that the notes tab is the one showing */
      var s = search();
      if (s && s.jumpKey(e, box, "panel-notes")) return;

      /* F3 and ctrl/cmd-G are the find-again keys every browser already uses,
         and here they should walk THIS search rather than open the browser's,
         which cannot see inside a filtered-out note. */
      if (!query || !HITS.length) return;
      var again = (e.key === "F3" || e.keyCode === 114) ||
                  ((e.ctrlKey || e.metaKey) && (e.key === "g" || e.key === "G"));
      if (!again) return;
      e.preventDefault();
      goHit(e.shiftKey ? -1 : 1);
    });
  }

  /* the MSK skeleton, as a button above week 1 that opens it in its own tab:
     framed inline it kept resizing itself and left a blank gap below it. */
  function bodyMap(src) {
    var box = el("section", "bodymap");
    var open = el("a", "print-cta", "Where does it hurt? Open the body map");
    open.href = src; open.target = "_blank"; open.rel = "noopener";
    box.appendChild(open);
    return box;
  }

  function buildStream() {
    var stream = byId("note-stream"), frag = document.createDocumentFragment();

    /* the same head the questions tab gives each source family, so the notes
       open by saying what they are rather than dropping straight into week 1 */
    var c = counts();
    var head = el("div", "fam-head");
    /* the whole block as one PDF, in the heading's corner where the eye goes
       looking for it, rather than at the foot of the sidebar */
    var title = el("div", "fam-title");
    title.appendChild(el("h2", null, "Lecture notes"));
    var all = pdfButton("Save all as PDF", "Save every note as one PDF: print it, annotate it, keep it", printAll);
    all.id = "print-all";
    all.disabled = c.written === 0;
    title.appendChild(all);
    head.appendChild(title);
    /* the key to the objectives highlighter, on a block whose notes carry it */
    if (JSON.stringify(WEEKS).indexOf('class=\\"lo\\"') !== -1) {
      var key = el("p", "fam-key");
      key.appendChild(el("mark", "lo", "Highlighted"));
      key.appendChild(document.createTextNode(" text is what the lecture\u2019s learning " +
        "objectives ask for."));
      head.appendChild(key);
    }
    /* a block charted before its lectures were taught says so once, here,
       rather than repeating the same warning on top of every note */
    if (NOTES_DRAFT) {
      var dr = el("div", "callout k-warning");
      dr.appendChild(el("span", "ct", "Draft"));
      dr.appendChild(el("p", null, NOTES_DRAFT));
      head.appendChild(dr);
    }
    frag.appendChild(head);
    if (BLOCK.bodymap) frag.appendChild(bodyMap(BLOCK.bodymap));

    WEEKS.forEach(function (w) {
      var wb = el("div", "weekbar");
      wb.appendChild(el("h3", null, w.label || ("Week " + w.n)));
      if ((w.lectures || []).some(written)) {
        wb.appendChild(pdfButton("Save week as PDF",
          "Save every note in this week as one PDF",
          function () { printWeek(wb); }));
      }
      frag.appendChild(wb);
      (w.lectures || []).forEach(function (lec) {
        frag.appendChild(lec.hasNote === true ? shared().build(lec, { block: BLOCK.name, slug: BLOCK.slug, onPrint: printNote, lecq: BLOCK.lecq })
                         : lec.coveredBy ? buildCovered(lec) : buildGap(lec));
      });
    });

    var empty = el("div", "empty", "Nothing matches that filter.");
    empty.id = "note-empty";
    empty.hidden = true;
    frag.appendChild(empty);

    stream.innerHTML = "";
    stream.appendChild(frag);
  }

  /* the notes are long enough that scrolling back by hand is a chore, so the
     tab carries the same pill the questions tab does, with only the way to the
     top on it. It is inside the notes panel, so switching tabs takes it away. */
  function initTop() {
    var bar = byId("notebar");
    if (!bar) return;
    var queued = false;

    byId("nb-top").addEventListener("click", function () {
      var still = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      try { window.scrollTo({ top: 0, behavior: still ? "auto" : "smooth" }); }
      catch (e) { window.scrollTo(0, 0); }
    });

    function paint() { bar.hidden = window.pageYOffset <= 400; }
    window.addEventListener("scroll", function () {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(function () { queued = false; paint(); });
    }, { passive: true });
    paint();
  }

  /* The rail takes 250px of a page that is mostly notes, so it can be tucked
     away to give the notes the width, and brought back from a tab on the left
     edge. The choice is remembered on this device. Below 960px the rail sits
     above the notes instead of beside them, so there is nothing to tuck. */
  var TUCK_KEY = "nsq.railTucked";

  function initTuck() {
    var shell = byId("panel-notes");
    var rail = shell && shell.querySelector(".rail");
    if (!rail) return;

    var hide = document.createElement("button");
    hide.type = "button";
    hide.className = "rail-tuck";
    hide.textContent = "\u00ab Hide sidebar";
    hide.title = "Tuck the sidebar away to give the notes more room";
    rail.insertBefore(hide, rail.firstChild);

    var show = document.createElement("button");
    show.type = "button";
    show.className = "rail-show";
    show.textContent = "Sidebar \u00bb";
    show.title = "Bring back the lecture list";
    shell.appendChild(show);

    function set(tucked, remember) {
      shell.classList.toggle("is-tucked", tucked);
      hide.setAttribute("aria-expanded", tucked ? "false" : "true");
      show.setAttribute("aria-expanded", tucked ? "false" : "true");
      if (remember) {
        try { window.localStorage.setItem(TUCK_KEY, tucked ? "1" : "0"); } catch (e) {}
      }
    }
    hide.addEventListener("click", function () { set(true, true); show.focus(); });
    show.addEventListener("click", function () { set(false, true); hide.focus(); });

    var saved = null;
    try { saved = window.localStorage.getItem(TUCK_KEY); } catch (e) {}
    set(saved === "1", false);
  }

  /* ---------- a link straight to one note ---------- */

  /* b1.html#n-b1-w1-02 lands on that lecture, and b1.html#n-b1-w1-02&q=thyroid
     storm (the landing page's search) on the first place in it those words
     appear, highlighted. Read once the stream is built,
     again once the pathways have drawn because drawing swaps text for taller
     diagrams and moves everything below them, and again on every hashchange,
     because a same-document hash change never reloads the page and boot runs
     only once. A hash naming a note the roster lacks does nothing, which is
     better than a scroll to nowhere. */
  function wantedNote() {
    var h = window.location.hash || "";
    if (h.indexOf("#n-") !== 0) return null;
    var parts = h.slice(3).split("&q=");
    var q = "";
    try { q = parts[1] ? decodeURIComponent(parts[1]) : ""; } catch (e) {}
    return { id: parts[0], q: q };
  }

  var LANDED = { hash: null, spot: null };   // the word a search link was marked on, once per link

  /* the search link's words painted inside the one note, and the first of them;
     the next search in the sidebar clears them like any other marks */
  function spotFor(art, q) {
    if (LANDED.hash === window.location.hash) return LANDED.spot;
    LANDED.hash = window.location.hash;
    LANDED.spot = null;
    var s = search();
    if (!q || !s) return null;
    unmark();
    markHits(art, s.words(q.toLowerCase()), s.MARK_BUDGET);
    HITS = [].slice.call(art.querySelectorAll("mark.hit"));
    /* the first place the words sit together (one sentence, list item or table
       row), else simply the first of them */
    var words = s.words(q.toLowerCase());
    AT_HIT = HITS.length ? 0 : -1;
    for (var i = 0; i < HITS.length; i++) {
      var near = HITS[i].closest("p, li, tr, h3, h4, figcaption") || HITS[i].parentNode;
      var text = (near.textContent || "").toLowerCase();
      if (words.every(function (w) { return text.indexOf(w) !== -1; })) { AT_HIT = i; break; }
    }
    if (AT_HIT >= 0) {
      HITS[AT_HIT].classList.add("on");
      LANDED.spot = HITS[AT_HIT];
    }
    return LANDED.spot;
  }

  function goToWanted() {
    var want = wantedNote();
    var art = want ? byId("n-" + want.id) : null;
    if (!art) return;
    var spot = spotFor(art, want.q);
    /* already where goTo aims means the earlier scroll landed, and scrolling
       again would only restart it */
    var at = spot || art;
    var gap = spot ? (window.innerHeight - spot.getBoundingClientRect().height) / 2 : 16 + barH();
    if (Math.abs(at.getBoundingClientRect().top - gap) < 2) return;
    goTo(want.id, spot);
  }

  function start(data) {
    WEEKS = (data && data.weeks) || [];
    NOTES_DRAFT = (data && typeof data.draft === "string") ? data.draft : "";
    assignKeys();
    WEEKS.forEach(function (w) {
      (w.lectures || []).forEach(function (l) { WK[l.key] = weekKey(w); });
    });
    buildRail();
    buildStream();
    snapshotOrder();
    indexText();
    paintCoverage();
    applyFilter();
    initSpy();
    initTop();
    initTuck();
    initFilterBar();
    goToWanted();
    shared().drawPathways(byId("note-stream")).then(goToWanted);
    window.addEventListener("hashchange", goToWanted);
  }

  window.POM2_NOTES = {
    boot: function () {
      if (booted) return;
      booted = true;
      fetch("data/notes/" + BLOCK.slug + ".json" +
            /* build_pages.py stamps the file's content hash here. Without it this
               one fetch was the only thing on the page with no cache busting, so a
               browser could keep serving the previous deploy's bank however hard
               you refreshed. Older pages carry no hash and simply go without. */
            (BLOCK.nv ? "?v=" + BLOCK.nv : ""))
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(start)
        .catch(function () {
          var stream = byId("note-stream");
          stream.innerHTML = "";
          stream.appendChild(el("div", "empty",
            "The notes could not be loaded. If you are opening this file straight from disk, serve the folder over HTTP instead - browsers block local fetches."));
        });
    }
  };
})();
