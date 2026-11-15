// Writes cards/icons.js: the line icons the story cards use, from the app's own icon set (lucide, ISC licence).
import fs from 'node:fs'
import path from 'node:path'
const dir = path.resolve('../frontend/node_modules/lucide-react/dist/esm/icons')
const NAMES = ['hard-hat', 'calendar-clock', 'badge-check', 'file-check', 'users', 'shield-check', 'stethoscope', 'landmark', 'user-cog', 'thermometer-sun', 'ship', 'radar', 'lock-keyhole', 'gauge', 'heart-handshake', 'sunrise', 'moon-star', 'clock', 'sun']
const out = {}
for (const n of NAMES) {
  const { __iconData } = await import(path.join(dir, `${n}.mjs`))
  const inner = __iconData.node.map(([tag, attrs]) => `<${tag} ${Object.entries(attrs).filter(([k]) => k !== 'key').map(([k, v]) => `${k}="${v}"`).join(' ')}/>`).join('')
  out[n] = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`
}
fs.writeFileSync('cards/icons.js', `window.ICONS = ${JSON.stringify(out, null, 1)};\n`)
console.log(Object.keys(out).length, 'icons')
