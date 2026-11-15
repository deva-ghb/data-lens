// Visit every screen as the role that uses it, at desktop and phone width, and save a
// screenshot. Also collects console errors and failed API calls per page.
// Usage: node e2e/tour.mjs [only-role]
import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.BASE ?? "http://localhost:5173";
const OUT = new URL("../../docs/checkpoints/build/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const TOUR = {
  "daniel.mensah": ["/", "/roster", "/permits", "/activities", "/groups", "/actions"],
  "khalid.alnuaimi": ["/", "/swaps", "/permits"],
  "priya.raman": ["/", "/permits"],
  "layla.haddad": ["/", "/warnings", "/district", "/reports", "/inspections", "/actions", "/learning", "/activities", "/validation", "/impact", "/governance", "/audit", "/signals"],
  "sara.ibrahim": ["/", "/health"],
  "ahmed.alshamsi": ["/", "/district", "/governance", "/audit"],
  "hessa.almansoori": ["/", "/admin/people", "/admin/clock", "/signals"],
  "marco.villanueva": ["/m", "/m/report", "/m/cards"],
  "joseph.kariuki": ["/m/foreman", "/m/report"],
};
const only = process.argv[2];
const report = [];
const browser = await chromium.launch();

for (const [user, pages] of Object.entries(TOUR)) {
  if (only && user !== only) continue;
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    const errors = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("response", (r) => r.url().includes("/api/") && r.status() >= 500 && errors.push(`${r.status()} ${r.url()}`));
    const login = await page.request.post(`${BASE}/api/auth/login`, { data: { email: `${user}@mirsalterminals.com`, password: "welcome@123" } });
    if (!login.ok()) throw new Error(`login failed for ${user}`);
    if (user === "daniel.mensah" && width === 1440) await page.request.post(`${BASE}/api/runs`, { data: { kind: "evening" } });
    for (const path of pages) {
      errors.length = 0;
      await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(600);
      const name = `${user.split(".")[0]}${path === "/" ? "-home" : path.split("/").join("-")}-${width}.png`;
      await page.screenshot({ path: `${OUT}${name}`, fullPage: true });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      report.push({ user, path, width, errors: [...errors], horizontalScroll: overflow, shot: name });
    }
    await context.close();
  }
}
await browser.close();
writeFileSync(`${OUT}tour.json`, JSON.stringify(report, null, 2));
const bad = report.filter((r) => r.errors.length || r.horizontalScroll);
console.log(`${report.length} screens, ${bad.length} with problems`);
for (const r of bad) console.log(r.user, r.path, r.width, r.horizontalScroll ? "HORIZONTAL SCROLL" : "", r.errors.slice(0, 3).join(" | "));
