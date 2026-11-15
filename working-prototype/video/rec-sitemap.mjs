// Re-records the site map and warning record shots into footage-part2 (the builder swaps it in by beat id).
import { request } from 'playwright'
import { createRecorder, sleep } from './kit.mjs'

const WEB = 'http://localhost:5173'
const admin = await request.newContext({ baseURL: 'http://localhost:8000' })
await admin.post('/api/auth/login', { data: { email: 'hessa.almansoori@mirsalterminals.com', password: 'welcome@123' } })
await admin.put('/api/admin/clock', { data: { now: '2026-07-29T09:00:00' } })
const rec = await createRecorder({ out: 'footage-part2' })
const s = await rec.screen('app')
await s.page.request.post(`${WEB}/api/auth/login`, { data: { email: 'layla.haddad@mirsalterminals.com', password: 'welcome@123' } })
await s.goto(`${WEB}/warnings`, 'text=Site map')
await s.page.waitForLoadState('networkidle')
await sleep(600)
await rec.beat('sitemap', s, async () => {
  await s.point(s.page.locator('.zone', { hasText: 'Camp Block C' }))
  await sleep(2600)
})
await rec.beat('record', s, async () => {
  await s.page.locator('text=Open warning records').first().evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }))
  await sleep(900)
  await s.click(s.page.getByText('Camp Block C').last())
  await s.page.getByText('What moved').waitFor()
  await sleep(900)
  await s.point(s.page.getByText('What moved'))
  await sleep(2400)
})
await rec.finish()
await admin.dispose()
