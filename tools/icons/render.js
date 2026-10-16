// Renders share.html and icon.html to the PNGs the site serves from its root.
// node tools/icons/render.js   (needs Playwright; run from the repo root)
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');
const path = require('path');
const here = (f) => 'file://' + path.resolve(__dirname, f);
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  await p.goto(here('share.html')); await p.waitForLoadState('networkidle');
  await p.screenshot({ path: 'share.png' });
  for (const [size, out] of [[512, 'icon-512.png'], [192, 'icon-192.png'], [180, 'apple-touch-icon.png']]) {
    const q = await b.newPage({ viewport: { width: 512, height: 512 }, deviceScaleFactor: size / 512 });
    await q.goto(here('icon.html')); await q.waitForLoadState('networkidle');
    await q.screenshot({ path: out });
  }
  await b.close();
})();
