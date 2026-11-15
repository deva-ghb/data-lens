// Records every Data Lens flow as one story: node rec.mjs (REHEARSE=1 node rec.mjs to rehearse).
// Start the take first with ./take.sh. One browser window; the person signed in changes
// between scenes, the way a demo laptop is passed around a control room.
import { execFileSync } from 'node:child_process'
import { request } from 'playwright'
import { createRecorder, sleep } from './kit.mjs'

const WEB = 'http://localhost:5173'
const API = 'http://localhost:8000'
const PASSWORD = 'welcome@123'
const ONLY = process.env.ONLY // rehearse from a named act onwards is not supported; full runs only

// Off-camera helpers: a signed-in API client per person.
const clients = {}
async function api(user) {
  if (!clients[user]) {
    clients[user] = await request.newContext({ baseURL: API })
    const r = await clients[user].post('/api/auth/login', { data: { email: `${user}@mirsalterminals.com`, password: PASSWORD } })
    if (!r.ok()) throw new Error(`login ${user}: ${r.status()}`)
  }
  return clients[user]
}
async function setClock(utc) {
  const r = await (await api('hessa.almansoori')).put('/api/admin/clock', { data: { now: utc } })
  if (!r.ok()) throw new Error(`clock ${r.status()}`)
}

const rec = await createRecorder({ out: process.env.OUT ?? 'footage' })
const s = await rec.screen('app')
const page = s.page
const step = (name) => page.locator('li.step').filter({ has: page.locator('.step__name').getByText(name, { exact: true }) })

async function as(user, path, ready) {
  await page.context().clearCookies()
  const r = await page.request.post(`${WEB}/api/auth/login`, { data: { email: `${user}@mirsalterminals.com`, password: PASSWORD } })
  if (!r.ok()) throw new Error(`login ${user}: ${r.status()}`)
  await s.goto(`${WEB}${path}`, ready)
  await page.waitForLoadState('networkidle')
  await sleep(500)
}
async function into(locator, block = 'center') {
  await page.locator(locator).first().evaluate((el, b) => el.scrollIntoView({ behavior: 'smooth', block: b }), block)
  await sleep(900)
}
async function top() { await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await sleep(700) }
async function pick(combobox, option) {
  await s.click(combobox)
  await s.click(page.getByRole('option', { name: option }).first())
}

// ===== Act 1. Evening of 28 July: the planner ==========================================
await s.goto(`${WEB}/login`, 'text=Work email')
await rec.beat('login', s, async () => {
  await s.glide(720, 330)
  await sleep(1500)
  await s.type(page.getByLabel('Work email'), 'daniel.mensah@mirsalterminals.com', { delay: 20 })
  await s.type(page.getByLabel('Password'), PASSWORD, { delay: 28 })
  await s.click(page.getByRole('button', { name: 'Sign in' }))
  await page.getByText("Today's brief").waitFor()
  await sleep(1000)
})
await rec.beat('brief', s, async () => {
  await s.point(page.getByText("Today's decisions"))
  await sleep(2600)
  await s.point(page.getByText('Waiting for you'))
  await sleep(1400)
})
await rec.beat('score', s, async () => {
  await s.click(page.getByRole('link', { name: 'Assignment risk' }))
  await page.getByRole('button', { name: "Score tomorrow's roster" }).first().waitFor()
  await sleep(700)
  await s.click(page.getByRole('button', { name: "Score tomorrow's roster" }).first())
  await page.locator('.tier-tiles').waitFor()
  await sleep(1400)
})
await rec.beat('tiles', s, async () => {
  for (const t of ['fit', 'fit_with_controls', 'reassign']) {
    await s.point(page.locator(`.tier-tile--${t}`))
    await sleep(900)
  }
})
await rec.beat('marco', s, async () => {
  const card = page.locator('.rec', { hasText: 'Marco Villanueva' })
  await s.point(card.locator('.rec__name'))
  await sleep(500)
  await s.point(card.locator('p.small').first())
  await sleep(2800)
})
await rec.beat('build', s, async () => {
  await s.click(page.locator('.rec', { hasText: 'Marco Villanueva' }).locator('.rec__name'))
  await page.waitForLoadState('networkidle')
  await sleep(1400)
  await page.mouse.wheel(0, 400)
  await sleep(2400)
})
await rec.beat('split', s, async () => {
  await page.goBack()
  await page.locator('.split').waitFor()
  await sleep(400)
  await s.point(page.locator('.split'))
  await sleep(2400)
  await into('text=Crew rules')
  await s.point(page.getByText('Crew rules').first())
  await sleep(1600)
})
await rec.beat('accept', s, async () => {
  await top()
  const card = page.locator('.rec', { hasText: 'Marco Villanueva' })
  await s.point(card.locator('.rec__swap'))
  await sleep(900)
  await s.click(card.getByRole('button', { name: 'Accept swap' }))
  await page.getByText('Swap accepted').waitFor()
  await sleep(1300)
})
for (const name of ['Sandeep Mishra', 'Murali Kumar']) {
  await page.locator('.rec', { hasText: name }).getByRole('button', { name: 'Accept swap' }).click()
  await sleep(500)
}
await rec.wait('ask', s, async () => {
  await s.click(page.getByRole('link', { name: 'Home' }))
  await page.getByLabel('Your question').waitFor()
  await into('text=Ask the copilot')
  await s.type(page.getByLabel('Your question'), 'How many people are in Reassign today tonight, and why?', { delay: 24 })
  await s.click(page.getByRole('button', { name: 'Ask' }))
  await page.locator('.answer').waitFor({ timeout: 90_000 })
  await sleep(2600)
})
await rec.wait('decline', s, async () => {
  await page.getByLabel('Your question').fill('')
  await s.type(page.getByLabel('Your question'), "Show me Marco's lab results.", { delay: 28 })
  await s.click(page.getByRole('button', { name: 'Ask' }))
  await page.locator('.answer--declined').waitFor({ timeout: 90_000 })
  await sleep(2600)
})
await rec.beat('activities', s, async () => {
  await s.click(page.getByRole('link', { name: 'Activities' }))
  await page.getByText('Lashing at height on deck').first().waitFor()
  await sleep(1200)
  await s.click(page.getByText('Lashing at height on deck').first())
  await page.getByText('Safe working practice').waitFor()
  await sleep(1400)
  await page.mouse.wheel(0, 380)
  await sleep(1600)
})
await rec.beat('groups', s, async () => {
  await s.click(page.getByRole('link', { name: 'Behavioural groups' }))
  await page.getByText('What the copilot proposes').waitFor()
  await sleep(1200)
  await s.point(page.getByText('New arrivals, contractor induction only'))
  await sleep(2400)
})

// ===== Act 2. The shift manager ========================================================
await as('khalid.alnuaimi', '/swaps', 'text=Swaps to approve')
await rec.beat('approve', s, async () => {
  const card = page.locator('.rec', { hasText: 'Marco Villanueva' })
  await s.point(card.locator('.rec__swap'))
  await sleep(1100)
  await s.click(card.getByRole('button', { name: 'Approve', exact: true }))
  await page.getByText('Swap approved').waitFor()
  await sleep(1300)
})
for (let i = 0; i < 2; i++) {
  await page.getByRole('button', { name: 'Approve', exact: true }).first().click()
  await sleep(600)
}

// ===== Act 3. 29 July, afternoon: the HSE head and Camp Block C =======================
await setClock('2026-07-29T09:00:00')
await as('layla.haddad', '/warnings', 'text=Site map')
await rec.beat('sitemap', s, async () => {
  await s.point(page.locator('.zone', { hasText: 'Camp Block C' }))
  await sleep(2600)
})
await rec.beat('record', s, async () => {
  await into('text=Open warning records')
  await s.click(page.getByText('Camp Block C').last())
  await page.getByText('What moved').waitFor()
  await sleep(900)
  await s.point(page.getByText('What moved'))
  await sleep(2400)
})
await rec.beat('confirm', s, async () => {
  await s.point(step('Detection').locator('textarea'))
  await sleep(1400)
  await s.click(step('Detection').getByRole('button', { name: 'Confirm section' }))
  await sleep(1400)
  for (const name of ['Activity and controls', 'History and patterns']) {
    await step(name).getByRole('button', { name: 'Confirm section' }).click()
    await sleep(700)
  }
})
await rec.wait('draft', s, async () => {
  await into('text=Drivers')
  await s.click(step('Drivers').getByRole('button', { name: 'Draft this section' }))
  await step('Drivers').locator('textarea').waitFor({ timeout: 90_000 })
  await sleep(2200)
  await s.click(step('Drivers').getByRole('button', { name: 'Confirm section' }))
  await sleep(1200)
})
// Steps 5 to 7 are signed off camera, with the text a head of safety would write.
const warningId = Number(page.url().split('/').pop())
const hseApi = await api('layla.haddad')
for (const [n, text] of [
  [5, 'Likelihood 4, severity 4, score 16, red. Target after controls: likelihood 2, score 8.'],
  [6, 'Check one: how many cooling units run in Camp Block C tonight? Check two: who sleeps in the hot rooms and works graded night work?'],
  [7, 'Response level: adjust the work. Engineer: repair the eleven cooling units within 48 hours (owner: camp operator). Administrative: cool room open all night and heat-stressed residents moved off height work (owner: planner).'],
]) {
  const r = await hseApi.post(`/api/warnings/${warningId}/steps/${n}/confirm`, { data: { content: text } })
  if (!r.ok()) throw new Error(`step ${n}: ${r.status()}`)
}
await page.reload()
await page.getByText('What moved').waitFor()
await rec.beat('inspection', s, async () => {
  await into('text=Verify on the ground')
  await s.click(page.getByRole('button', { name: 'Build inspection' }))
  await sleep(2000)
})
await rec.beat('action', s, async () => {
  await into('text=Ranked by the hierarchy of controls')
  await s.click(page.getByRole('button', { name: 'Add action' }))
  const dialog = page.getByRole('dialog')
  await s.type(dialog.getByLabel('What will be done'), 'Repair the eleven cooling units in Camp Block C', { delay: 18 })
  await pick(dialog.getByRole('combobox', { name: 'Level' }), 'Engineer')
  await pick(dialog.getByRole('combobox', { name: 'Owner' }), 'Daniel Mensah')
  await s.click(dialog.getByRole('button', { name: 'Add action' }))
  await page.getByText('Action added').waitFor()
  await sleep(1400)
})

// ===== Act 4. 18:00: Marco's phone =====================================================
await setClock('2026-07-29T14:00:00')
await as('marco.villanueva', '/m', 'text=Check in for tonight')
await rec.beat('phone', s, async () => {
  await sleep(700)
  await into('.phone-local')
  await s.point(page.locator('.phone-local'))
  await sleep(2800)
})
await rec.beat('english', s, async () => {
  await s.click(page.getByRole('button', { name: 'Show in English' }))
  await sleep(2600)
})
await rec.beat('checkin', s, async () => {
  await top()
  await s.click(page.getByRole('button', { name: '6 to 7 hours' }))
  await s.click(page.getByRole('button', { name: 'Good', exact: true }))
  await s.click(page.getByRole('button', { name: 'Yes', exact: true }))
  await s.click(page.getByRole('button', { name: 'Send check-in' }))
  await sleep(1500)
})
await rec.wait('report', s, async () => {
  await s.click(page.getByRole('link', { name: 'Report' }))
  await page.getByLabel('What happened?').waitFor()
  await s.type(page.getByLabel('What happened?'), 'Rung loose on the lashing platform ladder at Berth 2, bay 30.', { delay: 22 })
  await s.click(page.getByRole('button', { name: 'Send report' }))
  await page.getByText('Report sent').waitFor({ timeout: 90_000 })
  await sleep(1500)
})
await rec.beat('cards', s, async () => {
  await s.click(page.getByRole('link', { name: 'Cards' }))
  await page.getByText('Safety cards').waitFor()
  await sleep(1200)
  await s.click(page.getByRole('button', { name: 'I have read this' }).first())
  await sleep(1200)
})

// ===== Act 5. The permit issuer ========================================================
// Step 8 is the issuer's: from her home page she signs which permits the warning touches.
await as('priya.raman', '/', "text=Today's brief")
await rec.beat('issuer-step', s, async () => {
  await s.click(page.getByRole('link', { name: 'confirm the permits affected' }))
  await step('Permits affected').getByRole('button', { name: 'Write it yourself' }).waitFor()
  await into('text=Permits affected')
  await s.click(step('Permits affected').getByRole('button', { name: 'Write it yourself' }))
  await s.type(step('Permits affected').getByRole('textbox'), 'Night permits for Camp Block C residents carry the deck WBGT stop rule and buddy pairs above the second tier.', { delay: 12 })
  await s.click(step('Permits affected').getByRole('button', { name: 'Confirm section' }))
  await sleep(1400)
})
await rec.beat('permits', s, async () => {
  await s.click(page.getByRole('link', { name: 'Permits to work' }))
  await page.locator('.permit-card').first().waitFor()
  await sleep(900)
  await s.point(page.locator('.permit-card').first())
  await sleep(1200)
  await s.point(page.locator('.crew-bar').nth(3))
  await sleep(1400)
})
await rec.beat('sign', s, async () => {
  await s.click(page.locator('.permit-card', { hasText: 'Berth 2' }).filter({ hasText: 'Lashing at height' }).first())
  await page.getByRole('button', { name: 'Assess' }).waitFor()
  await sleep(1000)
  const accept = page.getByRole('button', { name: 'Accept' })
  if (await accept.count()) {
    await into('text=Conditions')
    for (let i = 0; i < 8 && (await accept.count()); i++) await s.click(accept.first(), { after: 250 })
    await top()
  }
  await s.click(page.getByRole('button', { name: 'Assess' }))
  await sleep(800)
  await s.click(page.getByRole('button', { name: 'Sign and issue' }))
  await sleep(1600)
})
const permitPath = new URL(page.url()).pathname

// ===== Act 6. 19:00: shift start =======================================================
await as('hessa.almansoori', '/admin/clock', 'text=Story moments')
await rec.beat('clock', s, async () => {
  await s.click(page.getByRole('button', { name: 'Shift start, 29 July night' }))
  await sleep(1800)
})
await as('priya.raman', permitPath, 'text=Permit log')
await rec.beat('start', s, async () => {
  await s.click(page.getByRole('button', { name: 'Start work' }))
  await sleep(1500)
})
await as('daniel.mensah', '/roster', '.tier-tiles')
await rec.beat('rescore', s, async () => {
  await s.click(page.getByRole('button', { name: 'Re-score now' }))
  await page.getByText('manual re-score').waitFor()
  await sleep(700)
  await s.point(page.locator('.tier-tile--unknown'))
  await sleep(1100)
  await into('.roster__search')
  await s.type(page.getByRole('textbox', { name: 'Search workers' }), 'Kiran', { delay: 60 })
  await sleep(2000)
})
execFileSync('uv', ['run', 'python', 'scripts/replay_sensor.py', '--from', '2026-07-29T15:00', '--to', '2026-07-29T16:30', '--pause', '0', '--base-url', API], { cwd: '../backend', stdio: 'pipe' })
await as('joseph.kariuki', '/m/foreman', 'text=Confirm the change')
await rec.beat('foreman', s, async () => {
  await s.point(page.getByText('Confirm the change').first())
  await sleep(2400)
  await s.click(page.getByRole('button', { name: 'Confirm the change' }).first())
  await sleep(1800)
})
await as('sunita.subedi', '/m', 'text=I feel unwell')
await rec.beat('unwell', s, async () => {
  await s.click(page.getByRole('button', { name: 'I feel unwell' }))
  await sleep(1200)
  await s.click(page.getByRole('button', { name: 'Yes, tell the clinic' }))
  await sleep(1800)
})
await as('priya.raman', permitPath, 'text=Permit log')
await rec.beat('permitlog', s, async () => {
  await into('text=A crew member reported feeling unwell')
  await s.point(page.getByText('A crew member reported feeling unwell'))
  await sleep(2600)
})

// ===== Act 7. The HSE head's desk ======================================================
await as('layla.haddad', '/reports', 'text=Incidents and hazards')
await rec.wait('reportconfirm', s, async () => {
  await s.click(page.getByText('Rung loose on the lashing platform ladder').first())
  await page.getByRole('button', { name: 'Confirm the record' }).waitFor({ timeout: 90_000 })
  await sleep(2000)
  await s.click(page.getByRole('button', { name: 'Confirm the record' }))
  await page.getByText('Record confirmed').waitFor()
  await sleep(1200)
})
await rec.wait('learning', s, async () => {
  await s.goto(`${WEB}/warnings/${warningId}`, 'text=What moved')
  await into('text=Learning')
  await s.click(step('Learning').getByRole('button', { name: 'Draft this section' }))
  await step('Learning').locator('textarea').waitFor({ timeout: 90_000 })
  await sleep(2000)
  await s.click(step('Learning').getByRole('button', { name: 'Confirm section' }))
  await sleep(1000)
  await s.click(page.getByRole('link', { name: 'Learning' }))
  await page.getByRole('button', { name: 'Share with crews' }).first().waitFor()
  await sleep(900)
  await s.click(page.getByRole('button', { name: 'Share with crews' }).first())
  await sleep(1400)
})
await rec.beat('validation', s, async () => {
  await s.click(page.getByRole('link', { name: 'Validation' }))
  await page.getByText('Events found').waitFor()
  await sleep(900)
  await s.point(page.getByText('Events found'))
  await sleep(1100)
  await s.point(page.getByText('Shortest lead time'))
  await sleep(1300)
})
await rec.wait('feedsoff', s, async () => {
  await s.click(page.getByRole('button', { name: 'Clinic visits by syndrome' }))
  await s.click(page.getByRole('button', { name: 'Run the back-test again' }))
  await sleep(4000)
})
await rec.beat('impact', s, async () => {
  await s.click(page.getByRole('link', { name: 'Impact' }))
  await page.getByText('Lost-time injuries avoided a year').waitFor()
  await sleep(900)
  await page.getByLabel('Lost-time injuries a year').fill('')
  await s.type(page.getByLabel('Lost-time injuries a year'), '60', { delay: 80 })
  await s.click(page.getByRole('button', { name: 'Recalculate' }))
  await sleep(1600)
})

// ===== Act 8. The clinician and Marco's choice ========================================
await as('sara.ibrahim', '/health', 'text=Screening')
await rec.beat('clinic', s, async () => {
  await s.click(page.getByText('Marco Villanueva').first())
  await page.getByText('Lab trends').waitFor()
  await sleep(1600)
  await pick(page.getByRole('combobox', { name: 'Outcome' }), 'Fit with restrictions')
  const restriction = page.getByLabel('Restriction')
  if (await restriction.count()) await s.type(restriction, 'No height work on hot nights for two weeks.', { delay: 14 })
  await s.click(page.getByRole('button', { name: 'Record outcome' }))
  await sleep(1500)
})
await as('marco.villanueva', '/m', 'text=Your clinic outcome')
await rec.beat('consent', s, async () => {
  await into('text=Your clinic outcome')
  await s.point(page.getByText('Your clinic outcome'))
  await sleep(1600)
  await s.click(page.getByRole('button', { name: 'Share outcome' }))
  await sleep(1600)
})

// ===== Act 9. The authority ============================================================
await as('ahmed.alshamsi', '/district', 'text=District view')
await rec.beat('district', s, async () => {
  await s.point(page.getByText('Hidden').first())
  await sleep(2600)
})
await rec.beat('audit', s, async () => {
  await s.click(page.getByRole('link', { name: 'Audit trail' }))
  await page.locator('tbody tr').first().waitFor()
  await sleep(900)
  await s.point(page.locator('tbody tr').first())
  await sleep(2400)
})

// ===== Act 10. Governance and signals ==================================================
await as('layla.haddad', '/governance', 'text=Who sees what')
await rec.beat('governance', s, async () => {
  await s.point(page.getByText('Who sees what'))
  await sleep(1600)
  await into('text=Hide groups under')
  await s.point(page.getByLabel('Hide groups under'))
  await sleep(1400)
  await into('text=Model weights')
  await s.point(page.getByText('Model weights'))
  await sleep(1600)
})
await rec.beat('signals', s, async () => {
  await s.click(page.getByRole('link', { name: 'Signals' }))
  await page.getByText('Clinic visits by syndrome').first().waitFor()
  await sleep(1200)
  await s.point(page.getByText('Late').first())
  await sleep(1400)
  await s.click(page.getByRole('button', { name: 'Connect a feed' }))
  await sleep(1800)
  await page.keyboard.press('Escape')
  await sleep(500)
})

// ===== Act 11. The admin ================================================================
await as('hessa.almansoori', '/admin/people', 'text=Onboard a person')
await rec.beat('onboard', s, async () => {
  await s.click(page.getByRole('button', { name: 'Onboard a person' }))
  const dialog = page.getByRole('dialog')
  await s.type(dialog.getByLabel('First name'), 'Mei', { delay: 50 })
  await s.type(dialog.getByLabel('Last name'), 'Tanaka', { delay: 50 })
  await pick(dialog.getByRole('combobox', { name: 'Role' }), 'Foreman')
  await pick(dialog.getByRole('combobox', { name: 'Employer' }), 'Mirsal Terminals')
  await s.type(dialog.getByLabel('Job title'), 'Foreman, Deck Gang 8', { delay: 18 })
  await s.click(dialog.getByRole('button', { name: 'Create account' }))
  await page.getByText('Account created').waitFor()
  await sleep(1500)
})

// ===== Act 12. The morning after =======================================================
await setClock('2026-07-30T05:00:00')
await as('layla.haddad', `/warnings/${warningId}`, 'text=Close the record')
await rec.beat('close', s, async () => {
  await into('text=Close the record')
  await s.click(page.getByRole('button', { name: 'Record the outcome' }))
  await pick(page.getByRole('combobox', { name: 'Outcome' }), 'Right')
  await s.click(page.getByRole('button', { name: 'Close record' }))
  await sleep(1600)
  await top()
  await sleep(800)
})
await as('marco.villanueva', '/m', 'text=Hello')
await rec.beat('home', s, async () => {
  await sleep(3500)
})

await rec.finish()
for (const c of Object.values(clients)) await c.dispose()
if (ONLY) console.log('ONLY is ignored')
