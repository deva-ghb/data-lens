import { expect, test, type Page } from "@playwright/test";

// Every key person's screens at desktop and phone width: nothing overlaps, nothing is cut
// off, nothing scrolls sideways, and every dropdown opens inside the screen.

const SCREENS: Record<string, string[]> = {
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
const WIDTHS = [1440, 390];
const SHOTS = "../docs/checkpoints/build";

async function signIn(page: Page, user: string) {
  const res = await page.request.post("/api/auth/login", { data: { email: `${user}@mirsalterminals.com`, password: "welcome@123" } });
  expect(res.ok()).toBe(true);
}

/** Problems on the page as it stands: sideways scroll, overlapping controls, clipped text. */
async function layoutProblems(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const out: string[] = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > doc.clientWidth + 1) out.push(`page scrolls sideways: ${doc.scrollWidth} > ${doc.clientWidth}`);

    const visible = (el: Element) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 1 && r.height > 1 && s.visibility !== "hidden" && s.display !== "none" && !el.closest(".visually-hidden");
    };
    const label = (el: Element) => `${el.tagName.toLowerCase()} "${(el.textContent || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "").trim().slice(0, 40)}"`;

    // Controls that are both on screen and not inside a scroll area that hides them.
    const controls = [...document.querySelectorAll("a[href], button, input, select, textarea, [role=combobox]")].filter(visible);
    for (let i = 0; i < controls.length; i++) {
      for (let j = i + 1; j < controls.length; j++) {
        const a = controls[i]!;
        const b = controls[j]!;
        if (a.contains(b) || b.contains(a)) continue;
        const ra = a.getBoundingClientRect();
        const rb = b.getBoundingClientRect();
        const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
        const h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
        if (w > 2 && h > 2) out.push(`overlap: ${label(a)} and ${label(b)}`);
      }
    }

    // Text cut off without an ellipsis: buttons, chips and table cells.
    for (const el of document.querySelectorAll("button, td, th, .pill, .dl-chip")) {
      if (!visible(el)) continue;
      const s = getComputedStyle(el);
      if (s.textOverflow === "ellipsis" || el.querySelector("[style*='ellipsis'], .roster__reason")) continue;
      if (el.closest(".dl-table-wrap") && el.tagName !== "BUTTON") continue; // a table scrolls inside its frame
      if (el.scrollWidth > el.clientWidth + 2 && s.overflowX !== "visible") out.push(`clipped: ${label(el)}`);
    }
    return out;
  });
}

/** Opens each dropdown and menu on the page and checks its list stays on screen. */
async function dropdownProblems(page: Page): Promise<string[]> {
  const out: string[] = [];
  const triggers = page.locator("[role=combobox], [aria-haspopup=menu]");
  const n = await triggers.count();
  for (let i = 0; i < n; i++) {
    const t = triggers.nth(i);
    if (!(await t.isVisible()) || !(await t.isEnabled())) continue;
    await t.scrollIntoViewIfNeeded();
    try {
      await t.click({ timeout: 5_000 });
    } catch {
      out.push(`dropdown ${i} could not be opened: ${(await t.textContent())?.trim() ?? ""}`);
      continue;
    }
    const list = page.locator("[role=listbox], [role=menu]").first();
    await list.waitFor({ state: "visible", timeout: 2_000 }).catch(() => undefined);
    if (await list.isVisible()) {
      const box = await list.boundingBox();
      const vp = page.viewportSize();
      if (box && vp && (box.x < 0 || box.y < 0 || box.x + box.width > vp.width + 1 || box.y + box.height > vp.height + 1)) {
        out.push(`dropdown ${i} opens off screen: ${JSON.stringify(box)}`);
      }
    }
    await page.keyboard.press("Escape");
    // Let the list finish closing before the next trigger is touched.
    await page.locator("[role=listbox], [role=menu]").first().waitFor({ state: "hidden", timeout: 3_000 }).catch(() => undefined);
  }
  return out;
}

test.beforeAll(async ({ playwright, baseURL }) => {
  // The planner's evening run, so every screen shows a scored roster.
  const request = await playwright.request.newContext({ baseURL });
  await request.post("/api/auth/login", { data: { email: "daniel.mensah@mirsalterminals.com", password: "welcome@123" } });
  const run = await request.post("/api/runs", { data: { kind: "evening", conditions_source: "scenario" } });
  expect(run.status()).toBe(201);
  await request.dispose();
});

for (const [user, paths] of Object.entries(SCREENS)) {
  for (const width of WIDTHS) {
    test(`${user} at ${width}px`, async ({ browser }) => {
      const context = await browser.newContext({ viewport: { width, height: width < 500 ? 844 : 900 } });
      const page = await context.newPage();
      const errors: string[] = [];
      page.on("console", (m) => {
        if (m.type() === "error") errors.push(m.text());
      });
      page.on("response", (r) => {
        if (r.status() >= 500) errors.push(`${r.status()} ${r.url()}`);
      });
      await signIn(page, user);
      const problems: string[] = [];
      for (const path of paths) {
        await page.goto(path, { waitUntil: "networkidle" });
        await page.waitForTimeout(300);
        for (const p of await layoutProblems(page)) problems.push(`${path}: ${p}`);
        for (const p of await dropdownProblems(page)) problems.push(`${path}: ${p}`);
        const name = `${user.split(".")[0]}${path === "/" ? "-home" : path.split("/").join("-")}-${width}`;
        await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
      }
      await context.close();
      expect(errors, "console errors and server errors").toEqual([]);
      expect(problems).toEqual([]);
    });
  }
}
