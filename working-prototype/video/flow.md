# Data Lens demo: shot list

One night at Mirsal Terminals, told through Marco Villanueva, a lasher whose daughter waits for his call in Iloilo.
Every flow in the product appears once, in the order the site clock would reach it.
The spoken line for each shot is in `script.json`; the clicks are in `rec.mjs`.

## How to record

1. `./take.sh` resets the take database, starts the app with the copilot on, and warms the planner's brief.
2. `REHEARSE=1 node rec.mjs` runs the whole take without saving frames.
3. `node rec.mjs` records into `footage/`.
4. `set -a; . ../.env; set +a` loads the speech keys (names only, never printed).
5. `python3 ~/.claude/skills/generating-narrated-videos/scripts/build.py --script script.json --footage footage --out build/video.mp4` cuts and narrates.
6. `./mix.sh build/video.mp4 build/data-lens.mp4` lays the backing track under the voice.

## Acts

| Act | Site time | Who | Flows shown |
|---|---|---|---|
| 1 | Tue 28 Jul, 18:00 | Daniel, planner | Sign in, brief, score tomorrow's roster, tiers, Marco's reasons, score breakdown, conditions vs crew, crew rules, accept a swap, ask the copilot, a declined question, activity register, behavioural groups |
| 2 | 18:00 | Khalid, shift manager | Approve the swap |
| 3 | Wed 29 Jul, 13:00 | Layla, head of safety | Site map, Camp Block C record, confirm drafted sections, live draft of a section, build an inspection, add an action |
| 4 | 18:00 | Marco, worker phone | Reason in Filipino, English toggle, three-tap check-in, hazard report, safety cards |
| 5 | 18:00 | Priya, permit issuer | Sign the warning's permit section from her home page, permits grid, accept warning conditions, assess and sign |
| 6 | 19:00 | Hessa, Priya, Daniel, Joseph, Sunita | Site clock to shift start, start work, re-score with Kiran's missing check-in, deck heat and the foreman's confirmation, unwell report, permit log with no name |
| 7 | 20:30 | Layla | Confirm Marco's report, draft and share the learning, back-test, a feed switched off, impact calculator |
| 8 | 20:30 | Sara, clinician; Marco | Fitness outcome; Marco chooses to share it |
| 9 | 20:30 | Ahmed, authority | District view with small groups hidden, redacted audit trail |
| 10 | 20:30 | Layla | Governance, signals and connecting a feed |
| 11 | 20:30 | Hessa, admin | Onboard a new foreman |
| 12 | Thu 30 Jul, 09:00 | Layla; Marco | Close the warning as right; Marco's morning |

## Off camera

- The other two swaps are accepted and approved the same way as Marco's.
- Warning sections 5 to 7 are signed with text a head of safety would write.
- The Berth 2 deck sensor is replayed from 19:00 to 20:30 by `../backend/scripts/replay_sensor.py`.
