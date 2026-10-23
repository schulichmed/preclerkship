/* The visitor counter.

   Every portal page pings this Worker about once a minute while its tab is
   visible, and the hub shows what comes back: how many browsers have ever
   opened the portal, and how many have a page open right now. A browser is
   the random id the page keeps in localStorage, so a person on a laptop and
   a phone counts twice and one who clears site data counts again; it is a
   head count of devices, not of people, and no address or cookie is kept.

   One Durable Object holds both numbers, so every ping sees the same count.
   The ids seen are stored (so the total survives restarts and a returning
   browser is not counted twice); who is online is kept in memory only, since
   it is stale in ninety seconds anyway. If Cloudflare evicts the object the
   online count starts from zero and refills within a minute. */

import { DurableObject } from "cloudflare:workers";

// A tab not heard from in this long has left. The page pings every 60s, so
// this allows one missed ping before the tab drops out.
const ONLINE_WINDOW_MS = 90 * 1000;
const ID_PATTERN = /^[a-z0-9]{8,40}$/;

export function validate(p) {
  if (!p || typeof p !== "object") return "not a ping";
  if (p.site !== "preclerkship") return "wrong site";
  if (!ID_PATTERN.test(p.visitor || "")) return "bad visitor";
  if (!ID_PATTERN.test(p.tab || "")) return "bad tab";
  return null;
}

export function corsHeaders(origin, allowed) {
  const list = (allowed || "").split(",").map(s => s.trim()).filter(Boolean);
  if (!origin || !list.includes(origin)) return null;
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Vary": "Origin",
  };
}

function reply(status, body, cors) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...(cors || {}) },
  });
}

export class Counter extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec("CREATE TABLE IF NOT EXISTS visitors (id TEXT PRIMARY KEY)");
    // Storage is billed per row read, and the free plan allows 5 million a
    // day: a COUNT(*) on every ping would read the whole table each minute
    // per tab and run through that by a couple of thousand visitors. So the
    // table is counted once when the object wakes and the total kept here.
    this.total = this.sql.exec("SELECT COUNT(*) AS n FROM visitors").one().n;
    this.known = new Set(); // visitors already stored since this wake
    this.tabs = new Map(); // tab id -> last ping, ms
  }

  ping(visitor, tab, leaving) {
    const now = Date.now();
    if (!this.known.has(visitor)) {
      const cursor = this.sql.exec("INSERT OR IGNORE INTO visitors (id) VALUES (?)", visitor);
      cursor.toArray();
      if (cursor.rowsWritten > 0) this.total += 1;
      this.known.add(visitor);
    }
    if (leaving) this.tabs.delete(tab);
    else this.tabs.set(tab, now);
    for (const [id, seen] of this.tabs) {
      if (now - seen > ONLINE_WINDOW_MS) this.tabs.delete(id);
    }
    return { total: this.total, online: this.tabs.size };
  }
}

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request.headers.get("origin"), env.ALLOWED_ORIGINS);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: cors ? 204 : 403, headers: cors || {} });
    }
    if (request.method !== "POST" || new URL(request.url).pathname !== "/") {
      return reply(404, { error: "not found" }, cors);
    }
    if (!cors) return reply(403, { error: "origin not allowed" }, null);

    // a leaving tab sends its last ping with sendBeacon, which posts text/plain
    let p;
    try { p = JSON.parse(await request.text()); } catch (e) { return reply(400, { error: "not json" }, cors); }
    const bad = validate(p);
    if (bad) return reply(400, { error: bad }, cors);

    // One object for the whole portal on purpose: both numbers are portal-wide,
    // and a class of a few hundred readers pinging once a minute is a few
    // requests a second, far below what one object can serve.
    const stub = env.COUNTER.getByName("portal");
    const counts = await stub.ping(p.visitor, p.tab, p.leaving === true);
    // the visitors from before the counter existed; see VISITOR_BASELINE
    counts.total += Number(env.VISITOR_BASELINE) || 0;
    return reply(200, counts, cors);
  },
};
