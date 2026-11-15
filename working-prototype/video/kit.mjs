// Generic screen recorder: Playwright + the Chrome DevTools screencast, with a drawn cursor and timed beats.
//
//   import { createRecorder } from './kit.mjs'
//   const rec = await createRecorder({ out: 'footage' })
//   const s = await rec.screen('main', 'https://example.com')
//   await rec.beat('intro', s, async () => { await s.glide(600, 300); await s.click('a') })
//   await rec.finish()          // writes footage/beats.json and footage/main/{frames,track}.json
//
// Why the screencast and not recordVideo: frames arrive at 2x resolution with exact timestamps, so the builder
// can speed up waits, hold still screens and follow the cursor. Chrome only sends a frame when pixels change.
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a)

// Screencast frames carry no OS cursor, so the page draws one that follows the mouse and ripples on click.
const CURSOR = () => {
  const mount = () => {
    if (document.getElementById('__cur') || !document.body) return
    const c = document.createElement('div'); c.id = '__cur'
    c.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;left:0;top:0;width:22px;height:22px;margin:-3px 0 0 -3px;' +
      'background:url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'22\' height=\'22\'><path d=\'M3 2l14 8-6 1.5L8 18z\' fill=\'black\' stroke=\'white\' stroke-width=\'1.5\'/></svg>") no-repeat'
    document.body.appendChild(c)
    addEventListener('mousemove', (e) => { c.style.transform = `translate(${e.clientX}px,${e.clientY}px)` }, true)
    addEventListener('mousedown', (e) => {
      const r = document.createElement('div')
      r.style.cssText = `position:fixed;z-index:2147483646;pointer-events:none;left:${e.clientX - 18}px;top:${e.clientY - 18}px;width:36px;height:36px;border-radius:50%;border:3px solid #2563eb;transition:transform .5s,opacity .5s`
      document.body.appendChild(r)
      requestAnimationFrame(() => { r.style.transform = 'scale(1.6)'; r.style.opacity = '0' })
      setTimeout(() => r.remove(), 600)
    }, true)
  }
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', mount); else mount()
  new MutationObserver(mount).observe(document, { childList: true, subtree: true })
}

class Screen {
  constructor(rec, name, page, cdp) { Object.assign(this, { rec, name, page, cdp, frames: [], track: [], writes: [], n: 0, pos: { x: 100, y: 100 }, live: false }) }

  async start() {
    this.dir = path.join(this.rec.out, this.name)
    fs.mkdirSync(this.dir, { recursive: true })
    this.cdp.on('Page.screencastFrame', ({ data, sessionId }) => {
      this.cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {})
      const file = `${String(this.n++).padStart(6, '0')}.jpg`
      this.frames.push([Date.now(), file])
      this.writes.push(fs.promises.writeFile(path.join(this.dir, file), Buffer.from(data, 'base64')))
    })
  }
  async on() {
    if (this.live || this.rec.rehearse) return
    await this.page.bringToFront()
    const { width, height } = this.rec.view, k = this.rec.scale
    await this.cdp.send('Page.startScreencast', { format: 'jpeg', quality: 90, maxWidth: width * k, maxHeight: height * k, everyNthFrame: 1 })
    this.live = true
    const n = this.n
    for (let i = 0; i < 40 && this.n === n; i++) await sleep(25)   // wait for the first frame
  }
  async off() { if (this.live) { try { await this.cdp.send('Page.stopScreencast') } catch { /* page closed */ } this.live = false } }
  async close() {
    await this.off(); await Promise.all(this.writes)
    fs.writeFileSync(path.join(this.dir, 'frames.json'), JSON.stringify(this.frames))
    fs.writeFileSync(path.join(this.dir, 'track.json'), JSON.stringify(this.track))
  }

  // Human-paced pointer: eased glide, then click, then a pause so the viewer can see the result.
  async glide(x, y, ms) {
    const { x: x0, y: y0 } = this.pos
    const dur = ms ?? Math.min(900, Math.max(350, Math.hypot(x - x0, y - y0) * 0.9))
    const steps = Math.max(8, Math.round(dur / 16))
    for (let i = 1; i <= steps; i++) {
      const t = i / steps, e = t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
      await this.page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
      await sleep(dur / steps)
    }
    this.pos = { x, y }
    this.track.push([Date.now(), Math.round(x), Math.round(y)])
  }
  loc(target) { return typeof target === 'string' ? this.page.locator(target) : target }
  async point(target) {
    const l = this.loc(target).first()
    await l.waitFor({ state: 'visible', timeout: 30_000 })
    await l.scrollIntoViewIfNeeded()
    const b = await l.boundingBox()
    await this.glide(b.x + b.width / 2, b.y + b.height / 2)
  }
  async click(target, { after = 450 } = {}) { await this.point(target); await sleep(180); await this.loc(target).first().click(); await sleep(after) }
  async type(target, text, { delay = 35, after = 300 } = {}) { await this.point(target); await this.loc(target).first().click(); await this.page.keyboard.type(text, { delay }); await sleep(after) }
  async goto(url, readyLocator) { await this.page.goto(url); if (readyLocator) await this.loc(readyLocator).first().waitFor({ timeout: 30_000 }) }
}

export async function createRecorder({ out = 'footage', view = { width: 1440, height: 810 }, scale = 2, headless = true, rehearse = process.env.REHEARSE === '1', args = [], storageState } = {}) {
  out = path.resolve(out)
  fs.mkdirSync(out, { recursive: true })
  const browser = await chromium.launch({ headless, args: ['--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding', '--disable-background-timer-throttling', ...args] })
  const ctx = await browser.newContext({ viewport: view, deviceScaleFactor: scale, storageState })
  await ctx.addInitScript(CURSOR)
  const rec = { out, view, scale, rehearse, browser, ctx, screens: [], beats: [] }

  rec.screen = async (name, url) => {
    const page = await ctx.newPage()
    page.on('pageerror', (e) => log(`[${name}] page error:`, String(e)))
    const s = new Screen(rec, name, page, await ctx.newCDPSession(page))
    await s.start()
    rec.screens.push(s)
    if (url) await page.goto(url)
    return s
  }
  // A beat is one step of the story; the builder cuts and narrates by beat id. wait:true marks a long wait the
  // builder may speed up to fit the voice.
  rec.beat = async (id, s, fn, extra = {}) => {
    await s.on()
    const t0 = Date.now()
    log(`beat ${id} (${s.name})`)
    try { await fn() } finally { rec.beats.push({ id, who: s.name, t0, t1: Date.now(), ...extra }); await s.off() }
  }
  rec.wait = (id, s, fn) => rec.beat(id, s, fn, { wait: true })
  rec.finish = async () => {
    for (const s of rec.screens) await s.close()
    fs.writeFileSync(path.join(out, 'beats.json'), JSON.stringify(rec.beats, null, 1))
    await browser.close()
    log(`footage: ${out} (${rec.beats.length} beats)`)
  }
  return rec
}
