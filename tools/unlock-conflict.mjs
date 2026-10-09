// Unlocks the Orbi web panel when it is stuck on the "wan lan conflict" page.
//
// The router redirects the SPA to /conflict, but its web server answers /conflict
// with 404, so the CONTINUE button is never shown. This script loads index.html
// in place of /conflict, lets you log in, then presses CONTINUE for you
// (POST /dniapi/conflict). The browser stays open afterwards.
//
//   npm install playwright && npx playwright install chromium
//   node unlock-conflict.mjs                     # router at http://10.0.0.1
//   node unlock-conflict.mjs http://127.0.0.1:8088   # through orbi_proxy.py
//
// Your password is typed by you in the browser window; the script never sees it.

import { chromium } from 'playwright';

const ORBI = (process.argv[2] || 'http://10.0.0.1').replace(/\/$/, '');

const browser = await chromium.launch({ headless: false });
const page = await (await browser.newContext()).newPage();

// Do not use route.fulfill(): Chrome's Local Network Access checks then block the
// panel's API calls. Rewriting the request URL keeps the page on the router origin.
await page.route('**/conflict', (route) =>
  route.request().resourceType() === 'document'
    ? route.continue({ url: `${ORBI}/index.html` })
    : route.continue());

page.on('response', async (res) => {
  if (res.url().includes('/dniapi/conflict') && res.request().method() === 'POST') {
    console.log('POST /dniapi/conflict ->', res.status(), await res.text().catch(() => ''));
  }
});

await page.goto(`${ORBI}/index.html`);
console.log('Log in to the Orbi in the browser window. Waiting for the CONTINUE button...');

const btn = page.locator('#continue');
await btn.waitFor({ state: 'visible', timeout: 0 });
await btn.click();
console.log('CONTINUE pressed. Expect {"code":0}. Now fix the subnet overlap (see README).');
console.log('Close the browser window when you are done.');
await new Promise((resolve) => browser.on('disconnected', resolve));
