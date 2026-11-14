# Data Lens working prototype: design

Date: 15 November 2026.
Source spec: `../../large-version.txt` (full concept doc) and `../../small-version.md` (walkthrough).
Roles input: `../../user-capabliites.txt`.
Due: engineering prototype for Challenge 06 on 20 November 2026.

## 1. Intent

Data Lens is the GYTWorkz with HealthVizor entry to the Future Health Digital Innovation Challenge, Challenge 06 (Population and Workforce Health Early Warning).
The concept doc describes a closed-loop HSE system that predicts the risk of every work assignment before the shift and turns it into a decision for the planner, the permit issuer and the foreman.
This build is the working engineering prototype the doc promises for 20 November.
Judges and the team must be able to log in as any role and use a real product, not a clickable design.
It also produces a narrated demo video that follows the lasher story from `small-version.md`.

## 2. Goals, non-goals, anti-goals

Goals:

- Every screen reads from and writes to a real database through a real API.
- The risk engine, the early warning detector and the back-test compute their numbers from raw seeded records.
  The lasher's R of about 1.94 and the "Reassign today" tier come out of the formula, not out of a seeded field.
- Every role can complete its own decisions end to end: check in, contest, accept or decline swaps, approve, sign or hold a permit, confirm warning sections, create actions, clear a worker as fit.
- AI (Azure OpenAI) drafts every copilot section, and a named person confirms it.
- A polished, light, minimal interface with careful spacing, elegant dropdowns and no overlapping controls at desktop and phone widths.
- A narrated demo video of the full story, about 5 minutes, recorded from the running app.

Non-goals:

- Live connections to a real permit-to-work system, HRMS, terminal operating system, WhatsApp, wearables, lab systems or a real clinic.
- Learned model weights.
  Version zero weights are expert-set and back-test-tuned, as the doc states.
- An optimiser for the roster.
  Greedy swaps only.
- The industry switcher with six sector registers.
  Ports only.
- Production deployment, single sign-on, multi-tenancy.

Anti-goals (failure even if it technically works):

- Any UI mock: a hardcoded screen, a fake button, a number typed into a component, a "coming soon" panel, or a simulated chat thread.
- A derived value (tier, R, warning level, back-test measure) stored as seed data instead of computed.
  The only exception is AI-written text, which is generated once and stored with its provenance.
- A role seeing what the doc says it must not see, enforced only in the UI.
  Every boundary is enforced in the API.
- Origin, nationality, religion, ethnicity or language used as a model input or group definition.
- Overlapping, cramped or clipped controls anywhere.

## 3. Constraints

- Work only inside `HealthChallenge/pivot-14-nov/working-prototype/`.
- SQLite now, through an ORM, so a later move to Postgres is a configuration change.
- The SQLite database file is committed.
- Every user's password is `welcome@123`.
- Azure OpenAI credentials come from a `.env` that Deva provides.
  `.env` is never committed and its values are never printed.
- AI output that is already in the seed is not regenerated at runtime.
- All people, sites, employers, clinics and figures are synthetic.

## 4. Approaches

1. **Python backend (FastAPI, SQLAlchemy 2, Alembic, SQLite) with a React 18, Vite and TypeScript frontend. Chosen.**
   Matches the stack Deva used for WhiteHats.
   Python suits the engine, the Monte Carlo split and the back-test.
   SQLAlchemy and Alembic make the database swap a configuration change.
2. Next.js full stack in TypeScript with Prisma.
   One language and an easy database swap, but the scoring and back-test maths are weaker in TypeScript and nothing carries over from WhiteHats.
3. Django with server-rendered pages.
   A free admin, but polished dropdowns, phone views and live permit updates are much harder to make feel like a product.

Deva handed over the choice of stack; option 1 is Claude's call.

## 5. Decisions

### 5.1 Scope (Deva's choice: full closed loop)

About 15 working modules, all live:

1. Home: the copilot brief per role, the drafts waiting for this person, the permit board summary, the watchers, and a question box that answers from the same data and declines at the role boundary.
2. Activities: the 13-activity port register with grade, hazards, exposure hours, SWP items, UABC history, control multiplier and sensitivity profile.
3. Behavioural groups: the six groups from doc section 5.4, with rates and multipliers computed from records, and the copilot's proposed actions.
4. Assignment risk: tomorrow's roster with tiers, the layer-by-layer build of R for any worker on any activity, crew rules, the alert budget, greedy swap proposals and the Monte Carlo split between conditions and crew.
5. Early warnings: site and district views of deviation from each zone's own baseline, the open warnings and their explanation.
6. Warning record: the ten-step record from doc section 7.1, with "show reasoning" panels, confidence, and confirmation by the named role.
7. Permits: the board and the single permit with the people-and-conditions block, drafted conditions, sign, hold, send back, suspend, live events and the JSON people-factor record.
8. Incidents and hazards: phone-first reporting with text and photo (voice depends on the open question in section 7), copilot drafting, safety chain, five whys, risk score.
9. Inspections: checklists built from drivers; results change confidence or record a false alarm.
10. Actions (CAPA): across warnings and incidents, by hierarchy of controls, with owner, due date and effectiveness check.
11. Learning: one-minute cards, toolbox talks, proposed SWP changes, read counts by crew.
12. Health (clinician): the screening list with lab trends; fit, fit with restrictions or not today, which reaches the planner without the reason.
13. Analytics: validation (the back-test with six measures and a feed switch-off panel) and impact (editable inputs, computed outcome).
14. Governance: the role-by-data matrix, the small-cell threshold, autonomy settings per action, the line against employment use, and the append-only audit trail.
15. Signals: the nine feeds with class, cadence, latency and freshness, plus connecting a new feed by CSV upload with the copilot mapping columns and excluding free text.
16. Phone views for the worker and the foreman: three-tap check-in, own tier and reason in the worker's chosen language, contest, "I feel unwell", cards, and the foreman's confirmations.
17. Admin: onboarding people, assigning roles and employers, and setting the site clock.

### 5.2 Roles (Deva's choice: 7 roles plus admin)

Worker, foreman, planner, shift manager, permit issuer, HSE head, occupational health clinician, admin.
The public health officer and the labour inspector merge into one read-only **Authority** role.
It sees district aggregates of 10 or more and the audit trail, and decides where to inspect and what to report.
Visibility follows doc sections 9.2 and 10 and `user-capabliites.txt`, and is enforced in the API.

### 5.3 Organisation, users and logos

- Organisation: **Mirsal Terminals**, a fictional container terminal in Abu Dhabi, with its workers' accommodation **Mirsal Workers Village** (camp blocks A to E).
  Deva wrote "Mislal Terminal"; Claude reads it as a voice-typing slip for Mirsal.
- Employers: Mirsal Terminals (in-house) and two fictional contractors, Sahel Marine Services and Bayan Manpower Contracting.
- Clinic: Mirsal Village Clinic.
- Every organisation gets a proper drawn SVG logo (a mark plus a wordmark), never initials or a monogram.
  Data Lens also gets a product logo.
- Login emails use `firstname.lastname@mirsalterminals.com` for everyone, including contractor workers and the Authority user.
  This is Claude's call, for one simple login pattern.
- Named role users (synthetic): admin, HSE head, planner, shift manager, permit issuer, two foremen, clinician, Authority.
  Every one of the 400 workers also has a login.
  The README and the login page's help text list the key accounts.
- All passwords are `welcome@123`, hashed in the database.
- Names are diverse and realistic.
  Names, origin and language never feed the model.

### 5.4 Seeded data

A deterministic generator script (fixed random seed) writes **raw records only**:

- 400 workers across three employers, with roles, competencies, training records, induction pathway, tenure, preferred display language and camp block.
- 13 port activities with hazards, severity, grade, exposure hours, SWP items and competencies, as in the doc.
- 90 days of history (1 May to 29 July 2026), around one vessel call.
  The vessel berths on the night shift of 29 July, and the site clock defaults to the evening of 28 July.
- Rosters and shift patterns, check-ins, sickness absence, observation cards, near misses, incidents, hazard reports, clinic visits by syndrome, lab panels, hourly weather and WBGT, air quality, camp fault tickets and on-site deck WBGT.
- Four injected events for the back-test.
  One is the Camp Block C cooling failure from the story, which is open on the scenario date.
  The other three are historical (for example a dust and respiratory cluster, a night-shift fatigue near-miss cluster and a mobile-plant struck-by pattern) and are closed in the history.
- The sensitivity matrix v0 and grade thresholds from the doc, as configuration.

Everything else is computed: readiness vectors, group rates, control multipliers, R, tiers, warnings, baselines and back-test measures.

### 5.5 Engine, detector and back-test

- The formula is doc section 3.2: R = Intrinsic × Control × Condition × Profile, with Profile as the product of [1 + (m_f − 1) × sens(a, f)].
- Caps, grade thresholds (grade 5: 1.3 and 1.9; grade 3: 1.5 and 2.4; grades 1 and 2 not scored per person), the group factor capped at 1.6 and limited to one tier step, and published seeds (1.17 heat, 1.36 fourth night).
- Crew rules and the alert budget from doc section 6.3.
- Greedy swaps within competency and contract.
  A Monte Carlo split of tomorrow's risk between conditions and crew.
- The detector uses per-zone baselines, the two-class rule, Watch and higher levels, named late feeds, and "unknown, not fit" for workers without a check-in.
- The back-test replays the 90 days, seeing each day once.
  It reports lead time, sensitivity, PPV, false alarms, data latency and behaviour with feeds missing.
  The action line is swept from 1.2 to 2.0 times baseline.
- The doc's walkthrough is the golden test: the engine must reproduce the lasher's numbers (Control 1.15, Condition 1.25, Profile 1.35, R ≈ 1.94, Reassign today).
- The doc's back-test figures (72 hours or more of lead time, 4 of 4, PPV 66%) are targets for the seed design, not values to display.
  The screen shows whatever the run computes.

### 5.6 AI integration (Azure OpenAI)

- One server-side client reads the endpoint, key, API version and deployment names from `.env`.
- AI drafts: the role brief, the ten warning-record sections, the incident record (classification, safety chain, five whys, risk, inspection, actions), learning cards and toolbox talks, the worker's reason in their chosen language, the question box answers, and the column mapping for a new feed.
- AI drafts for history and the scenario date are generated once by a seeding script that calls Azure, and are stored with model, deployment, prompt version and timestamp.
  At runtime only new events call Azure: a new incident, a new warning, a question, a translation not yet stored.
- Every AI section shows sure, unsure, what would change it, confidence, and a "show reasoning" panel.
  A person confirms each section.
  Reassigning, signing a permit and restricting on health grounds are locked to people.
- If Azure is unreachable, the screen says so and the person can write the section by hand.
  Nothing is filled in silently.

### 5.7 Feeds and live weather (Deva's choice: seeded plus live weather)

- All nine feeds have 90 days of seeded history.
- A real ingest job also pulls the live Abu Dhabi forecast hourly from the free Open-Meteo service and derives an estimated WBGT.
  It is stored in the same feed tables, marked as live.
- Signals shows both sources with freshness.
  If the live pull fails, the feed is marked late and named wherever it is used.
- The story runs on the scenario date (summer heat).
  Assignment risk can switch tomorrow's conditions between the scenario forecast and the live forecast, so a viewer sees today's real Abu Dhabi weather move the condition layer.
- On-site deck WBGT during the shift arrives through a real sensor-ingest API.
  A replay script posts the seeded readings the way a gateway would, which drives the "WBGT crosses the limit" moment in the demo.

### 5.8 Permits and phones

- The permit-to-work system is built into the app with the full lifecycle: requested, assessed, issued, live, suspended, closed.
- The JSON people-factor record is a real API endpoint per permit, the contract a real integration would implement.
- Phone views are mobile-first routes in the same app.
  There is no WhatsApp thread; notifications reach phones in the app.

### 5.9 Privacy and governance

- Role-based access in the API, matching doc section 10.
- Small-cell suppression with an adjustable threshold (default 10) and rounding of totals.
- Tiers expire with the shift, have no export, and are not recorded against the worker.
- An append-only audit log of every AI draft, human decision, declined question and threshold change, with model version, evidence and person.

### 5.10 Interface

- A light, minimal, professional theme.
  Theme checkpoint: Claude proposes three palettes rendered on real components (select, table, tier chips, buttons, a form, a chart), and Deva picks one.
- Accessible primitives (Radix) for selects, menus, popovers, dialogs and tabs, styled through design tokens.
- Charts follow the dataviz skill.
- A spacing scale, consistent control heights and focus states.
  An automated layout check at 1440 px and 390 px fails the build on overlapping or clipped controls.

### 5.11 Quality

- Engine unit tests, including the golden lasher test.
- API tests for every role boundary.
- Playwright end-to-end tests for each role's flow and the full story.
- Lint and type checks clean.

### 5.12 Demo video

- Built with the generating-narrated-videos skill, following the WhiteHats demo-video pattern: reset script, recorder, script.json, build.
- About 5 minutes, following the lasher's night from evening scoring to the closed loop.
- Narration in Deva's voice style, spoken by Azure Speech if the same resource supports it, otherwise a system voice, and Deva is told which was used.

### 5.13 Repository and checkpoints

- Layout: `working-prototype/{backend, frontend, docs, video}`, with the SQLite file under `backend/data/`.
- `working-prototype` becomes its own git repository.
  The database is committed; `.env`, footage and build output are not.
- Checkpoints with Deva:
  0. This design.
  1. Theme.
  2. Build complete: all modules working and tests green.
  3. Full flow ready for recording.
  Then the video.
  At each checkpoint the work is finished and refined, so the review takes about a minute.

### 5.14 Calls made after the builder review (Claude's calls, for Deva to check)

Model numbers v0:

- Claude sets every number the doc leaves open: all 13 activities, numeric values behind H, M and L, readiness multipliers, and the condition breakdown (heat tier, dust, night, pace).
- They live in one versioned configuration (weights v0), so the 16 November workshop output can replace them as weights v1 without touching code.
- The golden test pins weights v0 and the scenario snapshot, so a later weights version cannot silently break it.

Golden test:

- Intrinsic sets the scale and the tier thresholds from the grade, and contributes 1.0 to the product.
  That is the only reading under which 1.15 × 1.25 × 1.35 ≈ 1.94 holds.
- H, M and L numbers and the readiness multipliers are back-solved so the lasher's layers come out at Control 1.15, Condition 1.25 and Profile 1.35, each within ±0.02.
  R must be 1.94 ± 0.03 and the tier "Reassign today".
- The behavioural group factor of 1.6 is the raw group multiplier.
  The activity sensitivity scales it down inside Profile, which is how a 1.6 group rate and a 1.35 profile can coexist.
- Observation, near-miss, incident and hazard records are seeded for 12 months, so the control layer can be computed from the full "12 months" the doc quotes.
  The other feeds are seeded for 90 days.

Site clock:

- The app runs on a site clock stored in the database.
  It stays where it is until the admin moves it, or until the demo replay script advances it.
- Every time-based rule uses the site clock: shift boundaries and tier expiry, due dates, effectiveness checks, feed freshness for seeded feeds, and the times on new records.
- The live weather feed is judged against real time and labelled "live" everywhere it appears.
  Using the live forecast in assignment risk is an explicit choice the viewer makes.
- A reset command restores the scenario snapshot (database file and clock), so every demo take and every review starts from the same place.

Privacy details:

- The audit log stores reassignments against a per-shift token, not the worker's identity.
  Only the worker and the planner of that shift can resolve the token, and only while the shift lasts.
- The Authority role sees a redacted audit trail (roles, not names), district counts of 10 or more, and employer-level counts of 10 or more.
- If a worker declines to share the clinician's outcome with the employer, the planner sees "outcome not shared", and the engine treats the worker as unknown, not fit, for graded work.

Closed loop at runtime:

- A confirmed record (incident, near miss, observation, closed warning) updates the activity's UABC history immediately.
  The control multiplier and baselines change on the next engine run: the evening run, the shift-start re-score, or a re-score the planner starts.
  The demo can show a new confirmed near miss moving the lasher's control layer on re-score.
- "Weights learn" is in scope as proposals: closed outcomes propose a new weights version, a person approves it, and the engine then uses it.
  Weights are versioned, and the back-test can run against any version.

HealthVizor scoring:

- Health readiness and profile scores are computed in the app, behind a scoring service boundary with the same contract HealthVizor's API would offer.
  Swapping in the live HealthVizor service later is a configuration change.
  The demo does not claim HealthVizor's live service computed the scores.

## 6. Left to the builder

- The exact table design, API shape and frontend structure.
- The fictional people's names, the vessel name and the camp details.
- The logo designs, within "a real mark, not initials".
- The exact Monte Carlo setup and the greedy swap order.
- The content of the three historical injected events.
- The copy and prompts, within Deva's voice and the plain-language rule for user-facing text.

## 7. Deva's answers after the builder review

- Hosting: the prototype runs locally; judges see the narrated video, and the team runs it locally.
  No public deployment, so no shared-password exposure and no concurrent judges.
- Deadline: ignore the date and build the whole thing properly.
  There is no cut line.
- Decisions API: OpenAI's Decisions API (`POST /v1/decisions`), which returns typed answers (a probability for a predicate, a pick from a fixed set, or a score on ordered levels) for text, images and JSON.
  Verified on 15 November 2026 to work on Deva's Azure endpoint with the `gpt-6-luna` deployment.
  Use it only where the step is a classification, a yes or no, or a score.
  Generative text (briefs, record sections, five whys, cards, translations, answers) uses `gpt-6-luna` through the Responses API with structured output.
- Where the Decisions API is used:
  - Incident triage: incident type and potential severity (choice, score), and photo checks such as "harness not clipped" or "person under a suspended load" (predicates on the photo).
  - Risk assessment: likelihood and severity on the site's 5 by 5 matrix (score, levels 1 to 5), shown with per-level probabilities and confidence.
  - Question box role boundary: which data scopes a question needs (choice per scope), so a question outside the role is declined before any text is generated.
  - New feed connection: for each column, which field it maps to (choice) and whether it is free text (predicate), up to 400 columns in one call.
  - Inspection results and contests: whether a supervisor's note confirms the driver (predicate), and which category a worker's contest falls into (choice).
- `.env`: present with `AZURE_OPENAI_ENDPOINT` (a chat-completions URL on an Azure AI Services host) and `AZURE_OPENAI_API_KEY`.
  The backend derives the v1 base URL from the endpoint.
  Deployments confirmed: `gpt-6-luna` (chat, responses, decisions), `gpt-5.6-luna`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-4.1-mini`.
  No image-generation deployment is used.
- Design approved by Deva on 15 November 2026.
