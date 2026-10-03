# The visitor counter

The top right of the hub shows two numbers: how many browsers have ever opened
the portal, and how many have a page open right now. The portal is static, so
the counting happens here: a small Cloudflare Worker with one Durable Object
that every page pings about once a minute while its tab is visible
(`PRESENCE_SCRIPT` in `tools/portal.py`, which goes into every page's head).

- **Visitors** counts browsers, not people. Each one keeps a random id in
  localStorage (`pc-visitor`), so a laptop and a phone count as two, and
  clearing site data counts again. No address, cookie or name is stored.
- **Online** counts open tabs heard from in the last 90 seconds. A tab that
  closes says so as it goes, so the number drops at once; one that is hidden
  stops pinging and drops out within 90 seconds.
- The count starts at zero on the day it is deployed. Cloudflare Web Analytics
  (the other script in the head) still has the history from before.

Until it is deployed the pings fail quietly and the hub shows nothing in that
corner, so the pages can go out first.

## Set it up once

1. `cd tools/presence-worker && npx wrangler login`, signed in to the same
   Cloudflare account as the report relay (the free plan is enough).
2. `npx wrangler deploy`. It should print
   `https://preclerkship-presence.schulichmed.workers.dev`. If the subdomain
   differs, put the printed URL in `PRESENCE_URL` in `tools/portal.py` and run
   the three builders (`build_pages.py`, `build_index.py`, `build_hub.py`).

## Try it

```bash
curl -s -X POST https://preclerkship-presence.schulichmed.workers.dev/ \
  -H 'origin: https://schulichmed.github.io' -H 'content-type: application/json' \
  -d '{"site":"preclerkship","visitor":"testvisitor1","tab":"testtab0001"}'
```

The answer is `{"total": N, "online": M}`. That test adds one to the total
for good, so run it once.

## Cost

Each open tab makes one request a minute. The free plan allows 100,000 a day,
which is about 1,600 hours of reading a day across everyone. If the counter
ever runs out, the pings fail and the corner goes blank; nothing else on the
portal depends on it. To turn it off, set `PRESENCE_URL` to `""` and rebuild.
