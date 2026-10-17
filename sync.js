/* Sign in with Google, and the same progress on every device.

   Progress lives in localStorage, one entry per block (see quiz.js), which is
   per browser: a phone and a laptop each keep their own. This file adds an
   optional account. Signed in, every entry of the course being read is copied
   to the reader's own corner of a Firestore database, and what another device
   put there is merged back in. Signed out, nothing here runs beyond drawing
   the button, and the site works exactly as it always has.

   The merge is the one restore already uses, applied per question: the
   record whose last answer is newer wins, so two devices answering different
   questions both keep their answers, and a stale device can never roll a
   newer answer back. Notes merge the same way by their own time stamp, a
   deleted note included (its tombstone has a time too). "Clear" is the one
   thing newer-wins cannot carry, since a cleared question has no record left
   to be newer: quiz.js notes the time of every clear under "reset:<prefix>",
   and a record answered at or before its question's clear is dropped.

   Each entry is one document, users/<uid>/<prefix>/<key>, holding the entry
   as JSON text and the server's time of the last write. A page asks only for
   the documents of its own course written since it last asked, so a page
   load with nothing new costs one read. Writes are spaced out (PUSH_DELAY),
   and each is a transaction that merges with what is there, so two devices
   writing at once cannot erase each other.

   Firebase is loaded from Google only once someone opens the sign-in panel or
   has signed in before on this browser, and only when tools/portal.py sets
   FIREBASE_CONFIG; with that empty no page loads this file at all. Every path
   here is wrapped so a network or SDK failure leaves the page as it was. */

(function () {
  "use strict";

  var CFG = window.PORTAL_SYNC_CFG;
  if (!CFG || (!CFG.firebase && !window.PORTAL_SYNC_MOCK)) return;

  var SDK = "https://www.gstatic.com/firebasejs/10.14.1/";
  var ON_KEY = "pc-sync-on";           // "1" once signed in on this browser
  var META_KEY = "pc-sync-meta:";      // + uid: {since: {prefix: ms}, sent: {key: hash}}
  var PUSH_DELAY = 5 * 60000;          // the free plan allows 20,000 writes a day
  var STALE = 60000;                   // pull again on return after this long
  var MAX_TEXT = 900000;               // a Firestore document holds 1 MiB

  /* the course this page reads and writes, or none on the hub and course
     index pages, which only offer the button */
  var BLOCK = window.QUIZ_BLOCK || null;
  var PREFIX = BLOCK ? (BLOCK.store || "nsq.v1.") : null;

  /* ---------- the merge, which never touches the network ---------- */

  function isObj(x) { return !!x && typeof x === "object" && !Array.isArray(x); }
  function num(x) { return typeof x === "number" && isFinite(x) ? x : -1; }

  function kindOf(key) {
    if (key.indexOf("memo:") === 0) return "memo";
    if (key.indexOf("reset:") === 0) return "reset";
    return "block";
  }

  /* a is this browser's copy and wins ties, so an identical remote copy
     changes nothing here */
  function merge(kind, a, b, resets) {
    a = isObj(a) ? a : null;
    b = isObj(b) ? b : null;
    var out = {}, k;
    if (kind === "reset") {
      [a, b].forEach(function (s) {
        if (!s) return;
        Object.keys(s).forEach(function (q) {
          if (num(s[q]) > num(out[q])) out[q] = s[q];
        });
      });
      return out;
    }
    if (kind === "memo") {
      out = a ? JSON.parse(JSON.stringify(a)) : { v: 1, memos: {} };
      if (!isObj(out.memos)) out.memos = {};
      var inc = b && isObj(b.memos) ? b.memos : {};
      Object.keys(inc).forEach(function (q) {
        var m = inc[q], have = out.memos[q];
        if (!isObj(m) || typeof m.t !== "string" || num(m.ts) < 0) return;
        if (isObj(have) && num(have.ts) >= m.ts) return;
        out.memos[q] = { t: m.t, ts: m.ts };
      });
      return out;
    }
    if (a) for (k in a) if (isObj(a[k])) out[k] = a[k];
    if (b) for (k in b) {
      if (!isObj(b[k])) continue;
      if (!out[k] || num(b[k].lastTs) > num(out[k].lastTs)) out[k] = b[k];
    }
    if (resets) for (k in out) {
      if (num(resets[k]) >= 0 && num(out[k].lastTs) <= resets[k]) delete out[k];
    }
    return out;
  }

  /* JSON with every object's keys sorted, so two copies holding the same
     records in a different order compare equal */
  function canon(x) {
    if (Array.isArray(x)) return "[" + x.map(canon).join(",") + "]";
    if (isObj(x)) {
      return "{" + Object.keys(x).sort().map(function (k) {
        return JSON.stringify(k) + ":" + canon(x[k]);
      }).join(",") + "}";
    }
    return JSON.stringify(x === undefined ? null : x);
  }

  function hash(s) {
    var h = 0x811c9dc5;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    }
    return h.toString(36) + "." + s.length.toString(36);
  }

  /* What is sent. The cloud copy keeps each question's last CLOUD_ATTEMPTS
     answers, which is all the review queue reads (the last wrong one and the
     right ones after it), so a whole class fits the free plan's storage with
     room to spare; this browser keeps all fifty. A block that would still not
     fit a document keeps fewer. */
  var CLOUD_ATTEMPTS = 5;
  function slim(obj, n) {
    var out = {};
    Object.keys(obj).forEach(function (q) {
      var r = obj[q], c = {};
      Object.keys(r).forEach(function (f) { c[f] = r[f]; });
      if (Array.isArray(c.attempts) && c.attempts.length > n) c.attempts = c.attempts.slice(-n);
      out[q] = c;
    });
    return out;
  }
  function fit(kind, obj) {
    if (kind !== "block") return JSON.stringify(obj);
    var text = JSON.stringify(slim(obj, CLOUD_ATTEMPTS));
    [3, 1].some(function (n) {
      if (text.length <= MAX_TEXT) return true;
      text = JSON.stringify(slim(obj, n));
      return false;
    });
    return text;
  }

  function parse(text) {
    if (typeof text !== "string" || !text) return null;
    try { var v = JSON.parse(text); return isObj(v) ? v : null; }
    catch (e) { return null; }
  }

  /* ---------- this browser's side ---------- */

  function readLocal(key) {
    try { return parse(window.localStorage.getItem(key)); }
    catch (e) { return null; }
  }

  function writeLocal(key, obj) {
    try { window.localStorage.setItem(key, JSON.stringify(obj)); return true; }
    catch (e) { return false; }
  }

  function getFlag(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function setFlag(k, v) {
    try { if (v === null) window.localStorage.removeItem(k); else window.localStorage.setItem(k, v); }
    catch (e) { /* storage refused: the flag only saves a click */ }
  }

  /* every entry of one course: its blocks, its notes and its clears */
  function localKeys(prefix) {
    var out = [], i, k;
    try {
      for (i = 0; i < window.localStorage.length; i++) {
        k = window.localStorage.key(i);
        if (!k) continue;
        if (k.indexOf(prefix) === 0 && k.length > prefix.length) out.push(k);
      }
    } catch (e) { /* refused: there is nothing to send */ }
    ["reset:" + prefix, "memo:" + prefix].forEach(function (k2) {
      if (readLocal(k2)) out.push(k2);
    });
    return out;
  }

  /* resets first, so the block merges after them already know every clear */
  function order(keys) {
    return keys.slice().sort(function (x, y) {
      return (kindOf(x) === "reset" ? 0 : 1) - (kindOf(y) === "reset" ? 0 : 1);
    });
  }

  function readMeta(uid) {
    var m = readLocal(META_KEY + uid) || {};
    if (!isObj(m.since)) m.since = {};
    if (!isObj(m.sent)) m.sent = {};
    return m;
  }

  /* ---------- Firebase ---------- */

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = function () { reject(new Error("could not load " + src)); };
      document.head.appendChild(s);
    });
  }

  function firebaseBackend() {
    var ready = null, auth = null, db = null;

    function col(uid, prefix) {
      return db.collection("users").doc(uid).collection(encodeURIComponent(prefix));
    }

    return {
      init: function () {
        if (ready) return ready;
        ready = loadScript(SDK + "firebase-app-compat.js").then(function () {
          return Promise.all([loadScript(SDK + "firebase-auth-compat.js"),
                              loadScript(SDK + "firebase-firestore-compat.js")]);
        }).then(function () {
          var fb = window.firebase;
          if (!fb.apps.length) fb.initializeApp(CFG.firebase);
          auth = fb.auth();
          db = fb.firestore();
        });
        ready.catch(function () { ready = null; });
        return ready;
      },
      onUser: function (cb) {
        auth.onAuthStateChanged(function (u) {
          cb(u ? { uid: u.uid, name: u.displayName || "", email: u.email || "", photo: u.photoURL || "" } : null);
        });
      },
      /* must run inside the click that asked for it, or the browser blocks
         the Google window as a pop-up nobody asked for */
      signIn: function () {
        var p = new window.firebase.auth.GoogleAuthProvider();
        p.setCustomParameters({ prompt: "select_account" });
        return auth.signInWithPopup(p);
      },
      signOut: function () { return auth.signOut(); },
      pull: function (uid, prefix, since) {
        var q = col(uid, prefix);
        if (since > 0) q = q.where("ts", ">", window.firebase.firestore.Timestamp.fromMillis(since));
        return q.get().then(function (snap) {
          return snap.docs.map(function (d) {
            var x = d.data();
            return { k: x.k, d: x.d, ts: x.ts && x.ts.toMillis ? x.ts.toMillis() : 0 };
          });
        });
      },
      /* fn gets the stored text (or null) and returns the text to store, or
         null to leave the document alone; it may run more than once */
      update: function (uid, prefix, key, fn) {
        var ref = col(uid, prefix).doc(encodeURIComponent(key));
        return db.runTransaction(function (t) {
          return t.get(ref).then(function (snap) {
            var text = fn(snap.exists ? snap.data().d : null);
            if (text !== null) {
              t.set(ref, { k: key, d: text, ts: window.firebase.firestore.FieldValue.serverTimestamp() });
            }
          });
        });
      },
      wipe: function (uid, prefixes) {
        return Promise.all(prefixes.map(function (p) {
          return col(uid, p).get().then(function (snap) {
            var batch = db.batch();
            snap.docs.forEach(function (d) { batch.delete(d.ref); });
            return batch.commit();
          });
        }));
      }
    };
  }

  /* the test script swaps in a fake with the same methods */
  var backend = window.PORTAL_SYNC_MOCK || firebaseBackend();

  /* ---------- syncing ---------- */

  var user = null;
  var state = "off";                   // off | idle | busy | error
  var lastSync = 0, lastError = "", timer = null, running = null, again = false;

  /* One pass for this page's course: take in what other devices wrote since
     the last pass, then send every entry that changed here since it was last
     sent. Resolves to the number of entries this browser took in. */
  function syncOnce() {
    if (!user || !PREFIX) return Promise.resolve(0);
    var uid = user.uid, meta = readMeta(uid), took = 0;
    var resets = function () { return readLocal("reset:" + PREFIX) || {}; };

    function keep(key, obj) {
      if (writeLocal(key, obj)) took++;
    }

    return backend.pull(uid, PREFIX, num(meta.since[PREFIX])).then(function (docs) {
      docs = docs.filter(function (d) {
        return typeof d.k === "string" && (d.k.indexOf(PREFIX) === 0 ||
               d.k === "memo:" + PREFIX || d.k === "reset:" + PREFIX);
      });
      var byKey = {};
      docs.forEach(function (d) { byKey[d.k] = d; });
      order(Object.keys(byKey)).forEach(function (key) {
        var d = byKey[key], kind = kindOf(key), local = readLocal(key);
        var remote = parse(d.d);
        if (!remote) return;
        var merged = merge(kind, local, remote, kind === "block" ? resets() : null);
        if (canon(merged) !== canon(local || {})) keep(key, merged);
        /* the cloud already holds exactly this: nothing to send for it */
        if (fit(kind, merged) === fit(kind, remote) || canon(merged) === canon(remote)) {
          meta.sent[key] = hash(canon(merged));
        }
        if (d.ts > num(meta.since[PREFIX])) meta.since[PREFIX] = d.ts;
      });
      writeLocal(META_KEY + uid, meta);

      var dirty = order(localKeys(PREFIX)).filter(function (key) {
        var local = readLocal(key);
        return local && meta.sent[key] !== hash(canon(local));
      });

      return dirty.reduce(function (chain, key) {
        return chain.then(function () {
          var kind = kindOf(key), merged = null;
          return backend.update(uid, PREFIX, key, function (stored) {
            var remote = parse(stored);
            merged = merge(kind, readLocal(key), remote, kind === "block" ? resets() : null);
            var text = fit(kind, merged);
            return (remote && text === fit(kind, remote)) ? null : text;
          }).then(function () {
            /* re-read, since an answer may have landed while the write was
               in flight: what is here now is merged with what came back */
            var now = readLocal(key);
            var final = merge(kind, now, merged, kind === "block" ? resets() : null);
            if (canon(final) !== canon(now || {})) keep(key, final);
            meta.sent[key] = hash(canon(merged));
            writeLocal(META_KEY + uid, meta);
          });
        });
      }, Promise.resolve());
    }).then(function () { return took; });
  }

  function sync() {
    if (!user || !PREFIX) return Promise.resolve();
    if (running) { again = true; return running; }
    clearTimeout(timer); timer = null;
    setState("busy");
    running = syncOnce().then(function (took) {
      lastSync = Date.now(); lastError = "";
      setState("idle");
      if (took) {
        try { window.dispatchEvent(new CustomEvent("portal:synced", { detail: { prefix: PREFIX } })); }
        catch (e) { /* an old browser without CustomEvent: the next load shows it */ }
      }
    }, function (e) {
      lastError = navigator.onLine === false ? "You're offline. It will sync when you're back."
                                             : "Couldn't reach the server. It will try again.";
      setState("error");
      if (window.console) console.warn("sync:", e);
      schedule();
    }).then(function () {
      running = null;
      if (again) { again = false; schedule(); }
    });
    return running;
  }

  function schedule() {
    if (!user || !PREFIX || timer) return;
    timer = setTimeout(function () { timer = null; sync(); }, PUSH_DELAY);
  }

  document.addEventListener("visibilitychange", function () {
    if (!user) return;
    if (document.hidden) { if (timer) sync(); }
    else if (Date.now() - lastSync > STALE) sync();
  });

  /* ---------- the button and its panel ---------- */

  var btn = null, pop = null, loading = null, inited = false;

  var CLOUD = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<path d="M7 18a5 5 0 0 1-.9-9.9A6 6 0 0 1 17.6 9 4.5 4.5 0 0 1 17.5 18z"/></svg>';
  var GOOGLE = '<svg viewBox="0 0 48 48" aria-hidden="true" focusable="false" class="g">' +
    '<path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.6 2.4 30.2 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.8 6C12.4 13.7 17.7 9.5 24 9.5z"/>' +
    '<path fill="#4285F4" d="M46.1 24.6c0-1.6-.1-3.1-.4-4.6H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.5 5.8c4.4-4 6.8-10 6.8-17.1z"/>' +
    '<path fill="#FBBC05" d="M10.5 28.7c-.5-1.4-.8-3-.8-4.7s.3-3.2.8-4.7l-7.8-6C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7z"/>' +
    '<path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.8 2.3-8.4 2.3-6.3 0-11.6-4.2-13.5-10l-7.8 6C6.6 42.6 14.6 48 24 48z"/></svg>';

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function ago(ts) {
    var s = Math.round((Date.now() - ts) / 1000);
    if (s < 45) return "just now";
    var m = Math.round(s / 60);
    if (m < 60) return m + " min ago";
    return Math.round(m / 60) + " h ago";
  }

  function setState(s) { state = s; paint(); }

  function paint() {
    if (!btn) return;
    btn.setAttribute("data-state", user ? state : "off");
    var label = user ? "Signed in as " + (user.name || user.email) + ". Sync settings"
                     : "Sign in to keep your progress on every device";
    btn.setAttribute("aria-label", label);
    btn.title = label;
    var face = user && user.photo
      ? '<img alt="" referrerpolicy="no-referrer" src="' + esc(user.photo) + '"><i class="dot"></i>'
      : user ? '<span class="initial">' + esc((user.name || user.email || "?").charAt(0).toUpperCase()) + '</span><i class="dot"></i>'
             : CLOUD;
    /* only on a change: a click on the old icon must still land inside the
       button when the document's close-on-outside-click handler sees it */
    if (btn.innerHTML !== face) btn.innerHTML = face;
    if (pop && !pop.hidden) paintPop();
  }

  function paintPop() {
    var html;
    if (!user) {
      html = '<p class="sync-h">Keep your progress everywhere</p>' +
        '<p>Sign in with Google and your answers, review queue and notes follow you to any browser or device. ' +
        'Everything also stays saved on this one, signed in or not.</p>' +
        '<button type="button" class="sync-google" data-act="in"' + (loading ? " disabled" : "") + '>' + GOOGLE +
        '<span>' + (loading ? "Loading…" : "Continue with Google") + '</span></button>' +
        (lastError ? '<p class="sync-err" role="alert">' + esc(lastError) + '</p>' : "");
    } else {
      var status = !PREFIX ? "Your progress syncs when you open a course's questions."
        : state === "busy" ? "Syncing…"
        : state === "error" ? lastError
        : lastSync ? "Synced " + ago(lastSync) + "." : "Ready to sync.";
      html = '<p class="sync-h">' + esc(user.name || "Signed in") + '</p>' +
        (user.email ? '<p class="sync-email">' + esc(user.email) + '</p>' : "") +
        '<p class="sync-status' + (state === "error" ? " sync-err" : "") + '" role="status">' + esc(status) + '</p>' +
        '<div class="sync-row">' +
        (PREFIX ? '<button type="button" data-act="now"' + (state === "busy" ? " disabled" : "") + '>Sync now</button>' : "") +
        '<button type="button" data-act="out">Sign out</button></div>' +
        '<button type="button" class="sync-wipe" data-act="wipe">Delete my saved copy from the cloud</button>';
    }
    pop.innerHTML = html;
  }

  function prepare() {
    if (loading || user) return;
    loading = backend.init().then(function () {
      inited = true;
      backend.onUser(function (u) {
        user = u;
        setFlag(ON_KEY, u ? "1" : null);
        if (u) sync();
        paint();
      });
    }, function () {
      lastError = "Sign-in couldn't load. Check your connection and try again.";
    }).then(function () { loading = null; paint(); });
    paint();
  }

  /* Fixed to the window, under the button: the hub's hero clips anything
     that overflows it, and the panel would be cut off at its bottom edge. */
  function place() {
    var r = btn.getBoundingClientRect();
    pop.style.top = Math.round(r.bottom + 8) + "px";
    pop.style.right = Math.max(16, Math.round(window.innerWidth - r.right)) + "px";
  }

  function open() {
    place();
    pop.hidden = false;
    btn.setAttribute("aria-expanded", "true");
    if (!user) prepare();
    paintPop();
  }

  function close() {
    pop.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  }

  function act(what) {
    if (what === "in") {
      if (loading) return;
      if (!inited) { prepare(); return; }
      lastError = "";
      backend.signIn().catch(function (e) {
        var code = e && e.code || "";
        if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") return;
        lastError = code === "auth/popup-blocked"
          ? "Your browser blocked the Google window. Allow pop-ups for this site and try again."
          : "Sign-in didn't finish. Please try again.";
        paint();
      });
    } else if (what === "now") {
      sync();
    } else if (what === "out") {
      backend.signOut().then(function () {
        user = null; state = "off"; lastSync = 0; setFlag(ON_KEY, null); paint();
      });
    } else if (what === "wipe") {
      if (!window.confirm("Delete the copy of your progress saved to your account? " +
                          "What's on this device stays, and you'll be signed out.")) return;
      var uid = user.uid;
      setState("busy");
      backend.wipe(uid, CFG.stores || (PREFIX ? [PREFIX] : [])).then(function () {
        setFlag(META_KEY + uid, null);
        return backend.signOut();
      }).then(function () {
        user = null; state = "off"; lastSync = 0; setFlag(ON_KEY, null); paint();
      }, function () {
        lastError = "Couldn't delete it just now. Please try again.";
        setState("error");
      });
    }
  }

  function mount() {
    var theme = document.getElementById("theme-btn");
    if (!theme || !theme.parentNode) return;
    var wrap = document.createElement("span");
    wrap.className = "sync-wrap";
    btn = document.createElement("button");
    btn.type = "button";
    btn.id = "sync-btn";
    btn.className = "theme-btn sync-btn";
    btn.setAttribute("aria-haspopup", "dialog");
    btn.setAttribute("aria-expanded", "false");
    pop = document.createElement("div");
    pop.className = "sync-pop";
    pop.id = "sync-pop";
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-label", "Sync your progress");
    pop.hidden = true;
    wrap.appendChild(btn);
    wrap.appendChild(pop);
    theme.parentNode.insertBefore(wrap, theme);

    btn.addEventListener("click", function () { if (pop.hidden) open(); else close(); });
    pop.addEventListener("click", function (e) {
      var t = e.target.closest ? e.target.closest("[data-act]") : null;
      if (t && !t.disabled) act(t.getAttribute("data-act"));
    });
    document.addEventListener("click", function (e) {
      if (!pop.hidden && e.target.isConnected !== false && !wrap.contains(e.target)) close();
    });
    window.addEventListener("resize", function () { if (!pop.hidden) place(); });
    /* follows the button as the page scrolls, and shuts once it is gone */
    window.addEventListener("scroll", function () {
      if (pop.hidden) return;
      if (btn.getBoundingClientRect().bottom < 0) close(); else place();
    }, { passive: true });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !pop.hidden) { close(); btn.focus(); }
    });
    paint();
  }

  try {
    mount();
    if (getFlag(ON_KEY) === "1") prepare();
  } catch (e) {
    if (window.console) console.warn("sync:", e);
  }

  window.PORTAL_SYNC = {
    /* quiz.js calls this after every save; the write goes out a little later */
    touch: function () { if (user) schedule(); },
    /* for the test script */
    _merge: merge, _canon: canon, _sync: function () { return sync(); }
  };
})();
