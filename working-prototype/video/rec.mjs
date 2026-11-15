// Records the Data Lens story: node rec.mjs (REHEARSE=1 node rec.mjs to rehearse).
// Start the take first with ./take.sh. One browser window; the person signed in
// changes between scenes, the way a demo laptop would be passed around.
import { execFileSync } from 'node:child_process'
import { request } from 'playwright'
import { createRecorder, sleep } from './kit.mjs'

const WEB = 'http://localhost:5173'
const API = 'http://localhost:8000'
const PASSWORD = 'welcome@123'

const admin = await request.newContext({ baseURL: API })
await admin.post('/api/auth/login', { data: { email: 'hessa.almansoori@mirsalterminals.com', password: PASSWORD } })
const setClock = async (utc) => {
  const r = await admin.put('/api/admin/clock', { data: { now: utc } })
  if (!r.ok()) throw new Error(`clock ${r.status()}`)
}

const rec = await createRecorder({ out: process.env.OUT ?? 'footage' })
const s = await rec.screen('app')
const page = s.page

async function as(user, path, ready) {
  await page.context().clearCookies()
  const r = await page.request.post(`${WEB}/api/auth/login`, { data: { email: `${user}@mirsalterminals.com`, password: PASSWORD } })
  if (!r.ok()) throw new Error(`login ${user}: ${r.status()}`)
  await s.goto(`${WEB}${path}`, ready)
  await page.waitForLoadState('networkidle')
  await sleep(400)
}
const scrollTo = async (locator, block = 'center') => {
  await page.locator(locator).first().evaluate((el, b) => el.scrollIntoView({ behavior: 'smooth', block: b }), block)
  await sleep(900)
}
const top = async () => { await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await sleep(700) }

// --- Evening of 28 July: the planner ------------------------------------------------
await s.goto(`${WEB}/login`, 'text=Work email')
await rec.beat('login', s, async () => {
  await s.glide(720, 300)
  await sleep(1200)
  await s.type(page.getByLabel('Work email'), 'daniel.mensah@mirsalterminals.com', { delay: 22 })
  await s.type(page.getByLabel('Password'), PASSWORD, { delay: 30 })
  await s.click(page.getByRole('button', { name: 'Sign in' }))
  await page.getByText("Today's brief").waitFor()
  await sleep(1200)
})
await rec.beat('brief', s, async () => {
  await s.point(page.getByText("Today's decisions"))
  await sleep(2500)
  await s.point(page.getByText('Waiting for you'))
  await sleep(1500)
})

await rec.beat('score', s, async () => {
  await s.click(page.getByRole('link', { name: 'Assignment risk' }))
  await page.getByText('Score tomorrow').first().waitFor()
  await sleep(800)
  await s.click(page.getByRole('button', { name: "Score tomorrow's roster" }).first())
  await page.locator('.tier-tiles').waitFor()
  await sleep(1500)
})
await rec.beat('tiles', s, async () => {
  for (const t of ['fit', 'fit_with_controls', 'reassign']) {
    await s.point(page.locator(`.tier-tile--${t}`))
    await sleep(900)
  }
})
await rec.beat('arjun', s, async () => {
  const card = page.locator('.rec', { hasText: 'Arjun Thapa' })
  await s.point(card.locator('.rec__name'))
  await sleep(600)
  await s.point(card.locator('p.small').first())
  await sleep(2600)
})
await rec.beat('build', s, async () => {
  await s.click(page.locator('.rec', { hasText: 'Arjun Thapa' }).locator('.rec__name'))
  await page.waitForLoadState('networkidle')
  await sleep(1500)
  await page.mouse.wheel(0, 380)
  await sleep(2200)
})
await rec.beat('split', s, async () => {
  await page.goBack()
  await page.locator('.split').waitFor()
  await sleep(500)
  await s.point(page.locator('.split'))
  await sleep(2600)
})
await rec.beat('accept', s, async () => {
  const card = page.locator('.rec', { hasText: 'Arjun Thapa' })
  await s.point(card.locator('.rec__swap'))
  await sleep(900)
  await s.click(card.getByRole('button', { name: 'Accept swap' }))
  await page.getByText('Swap accepted').waitFor()
  await sleep(1400)
})
// The other two swaps are settled off camera, the same way.
for (const name of ['Sandeep Mishra', 'Murali Kumar']) {
  await page.locator('.rec', { hasText: name }).getByRole('button', { name: 'Accept swap' }).click()
  await sleep(500)
}

// --- The shift manager ----------------------------------------------------------------
await as('khalid.alnuaimi', '/swaps', 'text=Swaps to approve')
await rec.beat('approve', s, async () => {
  const card = page.locator('.rec', { hasText: 'Arjun Thapa' })
  await s.point(card.locator('.rec__swap'))
  await sleep(1200)
  await s.click(card.getByRole('button', { name: 'Approve', exact: true }))
  await page.getByText('Swap approved').waitFor()
  await sleep(1400)
})
for (let i = 0; i < 2; i++) {
  await page.getByRole('button', { name: 'Approve', exact: true }).first().click()
  await sleep(600)
}

// --- 29 July, 18:00: Arjun's phone ---------------------------------------------------
await setClock('2026-07-29T14:00:00')
await as('arjun.thapa', '/m', 'text=Check in for tonight')
await rec.beat('phone', s, async () => {
  await sleep(800)
  await scrollTo('.phone-local')
  await s.point(page.locator('.phone-local'))
  await sleep(2600)
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

// --- The permit issuer ------------------------------------------------------------------
await as('priya.raman', '/permits', 'text=Permits to work')
await rec.beat('permits', s, async () => {
  await s.point(page.locator('.permit-card').first())
  await sleep(1200)
  await s.point(page.locator('.crew-bar').nth(3))
  await sleep(1400)
})
await rec.beat('sign', s, async () => {
  await s.click(page.locator('.permit-card', { hasText: 'Berth 2' }).filter({ hasText: 'Lashing at height' }).first())
  await page.getByRole('button', { name: 'Assess' }).waitFor()
  await sleep(1200)
  await s.click(page.getByRole('button', { name: 'Assess' }))
  await sleep(900)
  await s.click(page.getByRole('button', { name: 'Sign and issue' }))
  await sleep(1600)
})
const permitUrl = page.url()

// --- 19:05: shift start ------------------------------------------------------------------
await setClock('2026-07-29T15:05:00')
await page.getByRole('button', { name: 'Start work' }).click()
await sleep(400)
await as('daniel.mensah', '/roster', '.tier-tiles')
await rec.beat('rescore', s, async () => {
  await s.click(page.getByRole('button', { name: 'Re-score now' }))
  await page.getByText('manual re-score').waitFor()
  await sleep(800)
  await s.point(page.locator('.tier-tile--unknown'))
  await sleep(1200)
  await scrollTo('.roster__search')
  await s.type(page.getByRole('textbox', { name: 'Search workers' }), 'Kiran', { delay: 60 })
  await sleep(2000)
})

// --- 19:00 to 20:30: the deck gets hot ------------------------------------------------
execFileSync('uv', ['run', 'python', 'scripts/replay_sensor.py', '--from', '2026-07-29T15:00', '--to', '2026-07-29T16:30', '--pause', '0', '--base-url', API], { cwd: '../backend', stdio: 'pipe' })
await as('joseph.kariuki', '/m/foreman', 'text=Confirm the change')
await rec.beat('foreman', s, async () => {
  await s.point(page.getByText('Confirm the change').first())
  await sleep(2200)
  await s.click(page.getByRole('button', { name: 'Confirm the change' }).first())
  await sleep(1800)
})

// --- The HSE head and Camp Block C ------------------------------------------------------
await as('layla.haddad', '/warnings', 'text=Site map')
await rec.beat('sitemap', s, async () => {
  await s.point(page.getByText('Camp Block C').first())
  await sleep(2400)
})
await rec.beat('record', s, async () => {
  await s.click(page.locator('a, button', { hasText: 'Camp Block C' }).last())
  await page.getByText('What moved').waitFor()
  await sleep(1000)
  await s.point(page.getByText('What moved'))
  await sleep(2400)
})
await rec.beat('confirm', s, async () => {
  const step = page.locator('li.step').filter({ has: page.locator('.step__name').getByText('Detection', { exact: true }) })
  await s.point(step.locator('textarea'))
  await sleep(1500)
  await s.click(step.getByRole('button', { name: 'Confirm section' }))
  await sleep(1800)
})
await rec.beat('validation', s, async () => {
  await s.goto(`${WEB}/validation`, 'text=Events found')
  await sleep(1000)
  await s.point(page.getByText('Events found'))
  await sleep(1200)
  await s.point(page.getByText('Shortest lead time'))
  await sleep(1800)
})

// --- The authority --------------------------------------------------------------------
await as('ahmed.alshamsi', '/district', 'text=District view')
await rec.beat('district', s, async () => {
  await s.point(page.getByText('Hidden').first())
  await sleep(2600)
})
await as('layla.haddad', '/audit', 'text=Audit trail')
await rec.beat('audit', s, async () => {
  await s.point(page.locator('tbody tr').first())
  await sleep(2600)
})

// --- The morning after -----------------------------------------------------------------
await setClock('2026-07-30T05:00:00')
await as('arjun.thapa', '/m/cards', 'text=Safety cards')
await rec.beat('morning', s, async () => {
  await sleep(800)
  await s.click(page.getByRole('button', { name: 'I have read this' }).first())
  await sleep(1500)
})
await rec.beat('home', s, async () => {
  await s.click(page.getByRole('link', { name: 'Today' }))
  await sleep(3000)
})

await rec.finish()
await admin.dispose()
console.log(`permit ${permitUrl}`)
