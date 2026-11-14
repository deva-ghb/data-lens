// Lists elements wider than the viewport: node e2e/overflow.mjs user width path [path...]
import { chromium } from "@playwright/test";
const [user, width, ...paths] = process.argv.slice(2);
const BASE = "http://localhost:5173";
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: Number(width), height: 844 } });
const page = await context.newPage();
await page.request.post(`${BASE}/api/auth/login`, { data: { email: `${user}@mirsalterminals.com`, password: "welcome@123" } });
for (const path of paths) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  const wide = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const out = [];
    for (const el of document.querySelectorAll("body *")) {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 1 && r.width > 0) {
        let p = el.parentElement, clipped = false;
        while (p) { const s = getComputedStyle(p); if (s.overflowX === "auto" || s.overflowX === "hidden" || s.overflowX === "scroll") { const pr = p.getBoundingClientRect(); if (pr.right <= vw + 1) { clipped = true; break; } } p = p.parentElement; }
        if (!clipped) out.push(`${el.tagName.toLowerCase()}.${String(el.className).split(" ").join(".")} right=${Math.round(r.right)}`);
      }
    }
    return { vw, sw: document.documentElement.scrollWidth, out: out.slice(0, 12) };
  });
  console.log(path, JSON.stringify(wide, null, 1));
}
await browser.close();
