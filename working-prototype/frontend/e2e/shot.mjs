// Viewport screenshots of chosen pages: node e2e/shot.mjs user width path [path...]
import { chromium } from "@playwright/test";
const [user, width, ...paths] = process.argv.slice(2);
const BASE = "http://localhost:5173";
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: Number(width), height: Number(width) < 500 ? 844 : 900 } });
const page = await context.newPage();
await page.request.post(`${BASE}/api/auth/login`, { data: { email: `${user}@mirsalterminals.com`, password: "welcome@123" } });
for (const p of paths) {
  const [path, scroll] = p.split("@");
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(500);
  if (scroll) await page.evaluate((y) => window.scrollTo(0, Number(y)), scroll);
  await page.waitForTimeout(200);
  const name = `/Users/devamacha/localdisk/E/claude-share/.playwright-mcp/v-${user.split(".")[0]}${path.split("/").join("-")}${scroll ? "-" + scroll : ""}-${width}.png`;
  await page.screenshot({ path: name, fullPage: process.env.FULL === "1" });
  console.log(name);
}
await browser.close();
