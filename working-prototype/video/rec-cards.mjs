// Films the story cards into footage-cards: node rec-cards.mjs (needs the app on :5173 for the logos).
import fs from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright'
import { createRecorder, sleep } from './kit.mjs'

// The real Data Lens and Mirsal marks, as the app draws them on its sign-in page.
const b = await chromium.launch()
const p = await b.newPage()
await p.goto('http://localhost:5173/login')
await p.locator('.dl-logo__mark').first().waitFor()
const marks = await p.locator('.dl-logo__mark').evaluateAll((els) => els.map((e) => e.outerHTML))
await b.close()
fs.writeFileSync('cards/logos.js', `window.LOGOS = ${JSON.stringify({ datalens: marks[0], mirsal: marks[marks.length - 1] })};\n`)

const CARDS = ['title', 'problem', 'idea', 'loop', 'crew', 'care', 'marco', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'end']
const rec = await createRecorder({ out: 'footage-cards' })
const s = await rec.screen('cards')
const file = 'file://' + path.resolve('cards/cards.html')
for (const c of CARDS) {
  await s.page.goto('about:blank')
  await rec.beat(`card-${c}`, s, async () => {
    await s.page.goto(`${file}?card=${c}`)
    await sleep(c === 'loop' ? 4200 : 3600)
  })
}
await rec.finish()
