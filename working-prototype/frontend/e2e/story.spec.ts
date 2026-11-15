import { expect, test, type Browser, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";

// The lasher's night, start to finish, through the screens each person uses. The backend
// is a fresh copy of the scenario with the copilot off, so every section a person signs
// is written by that person, and every number comes from the engine.

const API = "http://localhost:8010";

async function signedIn(browser: Browser, user: string, width = 1440): Promise<Page> {
  const context = await browser.newContext({ viewport: { width, height: width < 500 ? 844 : 900 } });
  const page = await context.newPage();
  const res = await page.request.post("/api/auth/login", { data: { email: `${user}@mirsalterminals.com`, password: "welcome@123" } });
  expect(res.ok()).toBe(true);
  return page;
}

async function setClock(admin: Page, utc: string) {
  const res = await admin.request.put("/api/admin/clock", { data: { now: utc } });
  expect(res.ok()).toBe(true);
}

async function confirmWritten(page: Page, stepName: string, text: string) {
  const step = page.locator("li.step").filter({ has: page.locator(".step__name").getByText(stepName, { exact: true }) });
  await step.getByRole("button", { name: "Write it yourself" }).click();
  await step.getByRole("textbox").fill(text);
  await step.getByRole("button", { name: "Confirm section" }).click();
  await expect(step.getByText("Confirmed by")).toBeVisible();
}

test("the lasher's night, from the evening run to the closed warning", async ({ browser }) => {
  test.setTimeout(240_000);
  const admin = await signedIn(browser, "hessa.almansoori");

  // Evening of 28 July: the planner scores tomorrow night and accepts the three swaps.
  const planner = await signedIn(browser, "daniel.mensah");
  await planner.goto("/roster");
  await planner.getByRole("button", { name: "Score tomorrow's roster" }).first().click();
  const marco = planner.locator(".rec", { hasText: "Marco Villanueva" });
  await expect(marco).toContainText("Reassign today");
  await expect(marco).toContainText("relative risk 1.94");
  await expect(marco).toContainText("Ground twist-lock handling");
  for (let left = 3; left > 0; left--) {
    await expect(planner.getByRole("button", { name: "Accept swap" })).toHaveCount(left);
    await planner.getByRole("button", { name: "Accept swap" }).first().click();
  }
  await expect(planner.getByRole("button", { name: "Accept swap" })).toHaveCount(0);

  // The shift manager approves them.
  const manager = await signedIn(browser, "khalid.alnuaimi");
  await manager.goto("/swaps");
  for (let left = 3; left > 0; left--) {
    await expect(manager.getByRole("button", { name: "Approve", exact: true })).toHaveCount(left);
    await manager.getByRole("button", { name: "Approve", exact: true }).first().click();
  }
  await expect(manager.getByText("Swap approved").first()).toBeVisible();
  await expect(manager.getByText("Nothing to approve")).toBeVisible();

  // 29 July, 18:00 on site: Marco reads the change in Filipino and checks in.
  await setClock(admin, "2026-07-29T14:00:00");
  const phone = await signedIn(browser, "marco.villanueva", 390);
  await phone.goto("/m");
  await expect(phone.getByText("Tonight: Ground twist-lock handling")).toBeVisible();
  await expect(phone.locator(".phone-local")).toBeVisible();
  await phone.getByRole("button", { name: "Show in English" }).click();
  await phone.getByRole("button", { name: "6 to 7 hours" }).click();
  await phone.getByRole("button", { name: "Good" }).click();
  await phone.getByRole("button", { name: "Yes", exact: true }).click();
  await phone.getByRole("button", { name: "Send check-in" }).click();
  await expect(phone.getByText("Check in for tonight")).toHaveCount(0);

  // The permit issuer assesses and signs Deck Gang 3's lashing permit at Berth 2.
  const issuer = await signedIn(browser, "priya.raman");
  await issuer.goto("/permits");
  await issuer.locator(".permit-card", { hasText: "Berth 2" }).filter({ hasText: "Lashing at height" }).first().click();
  await issuer.getByRole("button", { name: "Assess" }).click();
  await issuer.getByRole("button", { name: "Sign and issue" }).click();
  await expect(issuer.getByText("Issued").first()).toBeVisible();
  const permitUrl = issuer.url();

  // 19:05: the shift-start re-score. Kiran never checked in, so he is Unknown, not fit.
  await setClock(admin, "2026-07-29T15:05:00");
  await planner.goto("/roster");
  await planner.getByRole("button", { name: "Re-score now" }).click();
  await expect(planner.getByText("manual re-score")).toBeVisible();
  await planner.getByRole("textbox", { name: "Search workers" }).fill("Kiran Shrestha");
  await expect(planner.getByRole("row", { name: "Kiran Shrestha" })).toContainText("Unknown");

  // The issuer starts work on the permit at the start of the shift.
  await issuer.goto(permitUrl);
  await issuer.getByRole("button", { name: "Start work" }).click();
  await expect(issuer.getByText("Live").first()).toBeVisible();

  // The deck sensor at Berth 2 holds above 32 C for half an hour; the foreman confirms.
  execFileSync("uv", ["run", "python", "scripts/replay_sensor.py", "--from", "2026-07-29T15:00", "--to", "2026-07-29T16:30", "--pause", "0", "--base-url", API], { cwd: "../backend", stdio: "pipe" });
  const foreman = await signedIn(browser, "joseph.kariuki", 390);
  await foreman.goto("/m/foreman");
  await foreman.getByRole("button", { name: "Confirm the change" }).first().click();
  await expect(foreman.getByText("Confirmed. The permit log has it.")).toBeVisible();

  // A crew-mate feels unwell and tells the clinic; the permit shows no name.
  const crewMate = await signedIn(browser, "sunita.subedi", 390);
  await crewMate.goto("/m");
  await crewMate.getByRole("button", { name: "I feel unwell" }).click();
  await crewMate.getByRole("button", { name: "Yes, tell the clinic" }).click();
  await expect(crewMate.getByText("The clinic has been told")).toBeVisible();
  await issuer.goto(permitUrl);
  await expect(issuer.getByText("A crew member reported feeling unwell")).toBeVisible();
  await expect(issuer.getByText("Sunita")).toHaveCount(0);

  // The Camp Block C warning, section by section, each signed by its named role.
  const hse = await signedIn(browser, "layla.haddad");
  await hse.goto("/warnings");
  await hse.getByText("Camp Block C").last().click();
  await expect(hse.getByRole("heading", { name: "Early warning: Camp Block C" })).toBeVisible();
  for (const name of ["Detection", "Activity and controls", "History and patterns"]) {
    const step = hse.locator("li.step").filter({ has: hse.locator(".step__name").getByText(name, { exact: true }) });
    await step.getByRole("button", { name: "Confirm section" }).click();
    await expect(step.getByText("Confirmed by")).toBeVisible();
  }
  await confirmWritten(hse, "Drivers", "Eleven of forty cooling units are down in Camp Block C, so residents sleep hot before night lashing.");
  await confirmWritten(hse, "Risk assessment", "Likelihood 4, severity 4, score 16. Target after controls: likelihood 2.");
  await confirmWritten(hse, "Verify on the ground", "Check one: how many cooling units run tonight? Check two: who sleeps in the hot rooms?");
  await confirmWritten(hse, "Controls", "Engineer: repair the cooling units within 48 hours. Administrative: cool room open all night.");
  const warningUrl = hse.url();
  await issuer.goto("/");
  await issuer.getByRole("link", { name: "confirm the permits affected" }).click();
  await confirmWritten(issuer, "Permits affected", "Night permits at Berth 2 carry the deck WBGT stop rule and buddy pairs.");
  await hse.reload();
  await confirmWritten(hse, "Learning", "Card: a hot room means a hot shift; tell your foreman. Proposed safe working practice change: check camp cooling before night rosters.");

  // An action with an owner, due date and check date; the learning shared with crews.
  await hse.getByRole("button", { name: "Add action" }).click();
  const dialog = hse.getByRole("dialog");
  await dialog.getByLabel("What will be done").fill("Repair the eleven cooling units in Camp Block C");
  await dialog.getByRole("combobox", { name: "Level" }).click();
  await hse.getByRole("option", { name: "Engineer" }).click();
  await dialog.getByRole("combobox", { name: "Owner" }).click();
  await hse.getByRole("option", { name: "Daniel Mensah" }).click();
  await dialog.getByRole("button", { name: "Add action" }).click();
  await expect(hse.getByText("Repair the eleven cooling units in Camp Block C")).toBeVisible();
  await hse.goto("/learning");
  await hse.getByRole("button", { name: "Share with crews" }).first().click();
  await expect(hse.getByRole("button", { name: "Share with crews" })).toHaveCount(2);

  // The morning after: the record is closed as right.
  await setClock(admin, "2026-07-30T05:00:00");
  await hse.goto(warningUrl);
  await hse.getByRole("button", { name: "Record the outcome" }).click();
  await hse.getByRole("combobox", { name: "Outcome" }).click();
  await hse.getByRole("option", { name: "Right" }).click();
  await hse.getByRole("button", { name: "Close record" }).click();
  await expect(hse.getByText("Closed: Right")).toBeVisible();
});
