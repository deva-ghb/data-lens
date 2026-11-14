# Data Lens Working Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.
> This plan is worked across many turns and sessions: tick each box as it is done, and start every session by finding the first unticked box.

**Goal:** A working, locally run Data Lens prototype for a fictional UAE container terminal (Mirsal Terminals), with real data, a real computed risk engine, Azure OpenAI drafting, every role's flow working end to end, and a narrated demo video.

**Architecture:** FastAPI backend with SQLAlchemy 2 and Alembic over SQLite, holding raw seeded records and computing everything derived (engine, detector, back-test) in Python packages under `backend/app/`.
React 18 with Vite and TypeScript frontend, Radix primitives styled by design tokens, one app serving desktop role screens and the two phone views.
AI drafts go through one Azure OpenAI client that stores every output with provenance, and seeded drafts are generated once.

**Tech Stack:** Python 3.12, uv, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, argon2-cffi, PyJWT, httpx, numpy, openai (Azure client), pytest. Node 20, React 18.3.1, react-router-dom 6.30, @tanstack/react-query 5, @radix-ui primitives, lucide-react, @fontsource fonts, Vitest, Playwright. Video: `~/.claude/skills/generating-narrated-videos`.

**Spec:** `docs/specs/2026-11-15-data-lens-prototype-design.md` (approved 15 Nov 2026), which argues from `../large-version.txt` and `../small-version.md`.

All paths below are relative to `HealthChallenge/pivot-14-nov/working-prototype/`.

## Global Constraints

- No UI mock of any kind: no hardcoded screen data, no fake buttons, no "coming soon", no simulated chat threads. Every number on screen comes from the API.
- Derived values (R, tiers, warnings, group rates, control multipliers, baselines, back-test measures) are computed, never seeded. Only AI text and AI images are generated once and stored.
- Every visibility rule is enforced in the API; the UI only reflects it.
- No model input or group definition uses origin, nationality, religion, ethnicity or language. The people table has no nationality, religion or ethnicity columns.
- Organisation: Mirsal Terminals; email pattern `firstname.lastname@mirsalterminals.com`; every password `welcome@123`, stored hashed (argon2).
- Roles (exact enum values): `worker`, `foreman`, `planner`, `shift_manager`, `permit_issuer`, `hse_head`, `clinician`, `authority`, `admin`.
- Every organisation has a drawn SVG logo (mark plus wordmark), never initials or a monogram.
- Database: SQLite file `backend/data/datalens.db`, committed; scenario snapshot `backend/data/scenario.db`, committed. `.env`, video footage and build output are git-ignored.
- `.env` values are never printed or logged; refer to variable names only.
- No regular expressions in code or config without Deva's sign-off first (show pattern, must-match, must-not-match). Prefer parsing libraries.
- AI: `gpt-6-luna` on Deva's Azure endpoint for both the Responses API (written drafts) and the Decisions API (typed answers). Decisions API only where the step is a yes or no, a pick from a fixed set, or a score. No image generation.
- Never use the em dash character in code, copy, docs or commit messages; use a hyphen.
- Commit messages carry no AI co-author line (Deva's instruction overrides the default attribution).
- Long Markdown files: one sentence per line.
- User-facing copy is plain business language: short sentences, no jargon, no internal names.
- Interface: light, minimal theme from Checkpoint 1; 8 px spacing scale; control height 36 px (desktop) and 44 px (phone); no overlapping or clipped controls at 1440 px and 390 px widths.
- Weights v0 constants pinned by this plan: sensitivity H = 0.35, M = 0.20, L = 0.08; grade thresholds grade 5 (1.3, 1.9), grade 4 (1.4, 2.1), grade 3 (1.5, 2.4), grades 1 and 2 not scored per person; behavioural group multiplier cap 1.6 and at most one tier step; published seeds heat 1.17 (heat tier 2 or above), fourth consecutive night 1.36.
- Heat tiers from WBGT (°C): tier 0 below 27, tier 1 from 27, tier 2 from 30, tier 3 from 32.
- Small-cell threshold default 10, adjustable; suppressed cells hidden; every total in a view with suppression rounded to the nearest 5.
- Alert budget: at most 3 reassignment recommendations per shift per planner and 2 prompts per foreman.
- Crew rules: at most a quarter of a high-hazard crew on extra controls in heat tier 2 or above; arrivals under 7 acclimatisation days capped at 2 per gang; at least one experienced worker (group 1 or equivalent) on every grade 4 or 5 task.

## Review Focus

1. A worker with no check-in at shift start: shown as Unknown, never Fit, counted as unknown on the permit (test in Task 15).
2. A late or missing feed (clinic stale, live weather down, a feed switched off): named on every warning and screen it touches, level drops one step, nothing filled in silently (tests in Tasks 16, 21).
3. Two people acting on the same record out of order (planner declines after shift manager approves; issuer signs a permit whose crew went red): invalid state changes return 409 and the screen explains why (tests in Tasks 25, 26).
4. A filter that narrows an aggregate below the small-cell threshold (one employer in one camp block, a small district): cells hidden and totals rounded, never recoverable by subtraction (test in Task 7, used in Tasks 27, 33).
5. Azure unreachable or returning malformed output: the section says "Draft not available", the person can write it by hand, and nothing crashes (test in Task 18, exercised in Task 28).

---

## Phase 0: Foundations

### Task 1: Repository and backend skeleton

**Files:**
- Create: `.gitignore`, `README.md`, `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/alembic.ini`, `backend/migrations/env.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.main:app` (FastAPI); `app.config.Settings` with `database_url: str = "sqlite:///data/datalens.db"`, `azure_openai_endpoint: str | None`, `azure_openai_api_key: str | None`, property `azure_v1_base` (the endpoint up to `/openai/` plus `openai/v1`), `ai_text_model: str = "gpt-6-luna"`, `ai_decisions_model: str = "gpt-6-luna"`, `jwt_secret: str`; `app.db.Base`, `app.db.get_session() -> Iterator[Session]`, `app.db.engine`.

- [ ] **Step 1:** `git init` inside `working-prototype`; `.gitignore` covers `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `video/footage*/`, `video/build/`, `frontend/dist/`, `test-results/`. Keep `backend/data/*.db` tracked.
- [ ] **Step 2: Write the failing test** `test_health_returns_ok`: `GET /api/health` returns 200 and `{"status": "ok"}`.
- [ ] **Step 3:** Run `cd backend && uv run pytest tests/test_health.py -v`. Expected: FAIL (no app).
- [ ] **Step 4:** Create the uv project (Python 3.12) with the backend dependencies from Tech Stack; implement `main.py` with an `/api` router and `/api/health`; `config.py` reads `.env` from `working-prototype/.env` through pydantic-settings; `db.py` creates the engine with SQLite foreign keys on; Alembic wired to `Base.metadata`.
- [ ] **Step 5:** Run the test. Expected: PASS. Run `uv run ruff check .` clean.
- [ ] **Step 6:** Commit `chore: backend skeleton and repository`.

### Task 2: Frontend skeleton

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Produces: `apiGet<T>(path: string): Promise<T>`, `apiSend<T>(method: "POST"|"PUT"|"PATCH"|"DELETE", path: string, body?: unknown): Promise<T>`, both sending cookies and throwing `ApiError { status: number; code: string; message: string }`; Vite dev server on 5173 proxying `/api` to 8000.

- [ ] **Step 1: Write the failing test** `apiGet throws ApiError with status and message on 403`, using a stubbed `fetch`.
- [ ] **Step 2:** Run `cd frontend && npx vitest run`. Expected: FAIL.
- [ ] **Step 3:** Scaffold Vite React TS with exact versions from Tech Stack, React Query provider, router with a placeholder route that calls `/api/health` and renders its status (real call).
- [ ] **Step 4:** Run vitest. Expected: PASS. `npx tsc --noEmit` and eslint clean.
- [ ] **Step 5:** Add `start.sh` at the root that runs backend (`uvicorn app.main:app --port 8000`) and frontend dev server together. Run it; the page shows "ok" from the API.
- [ ] **Step 6:** Commit `chore: frontend skeleton`.

### CHECKPOINT 1: Theme (settled by Deva on 15 Nov 2026)

- [x] Deva supplied a reference (a shift-pattern grid) and said "I want this kind of theme". Recorded in `docs/checkpoints/theme/decision.md` (written in Task 4 Step 1) as:
  - White page (`#FFFFFF`) with a faint grey canvas for app chrome (`#FAFAFB`); hairline borders (`#E6E8EC`).
  - Soft pastel fills with a slightly deeper pastel border for every categorical block: periwinkle (`#E4E8F7` fill, `#CDD4EE` border) and mint (`#E6F3EB` fill, `#C8E2D1` border) as the two lead tints; further tints (sand, rose, lilac, sky) derived at the same lightness for tiers and chart series.
  - Text near-black (`#1F2328`) at regular weight inside blocks; labels and column heads light grey (`#7A808A`), small, never bold.
  - Corner radius 6 px on blocks and controls; 8 px gaps between blocks; generous row height (about 56 px for grid rows).
  - Inter typeface, tabular numerals for times and figures.
  - Accent for primary actions and focus: a muted indigo drawn from the periwinkle family; no saturated colours except the crew-status red and amber, kept as soft fills with a dark text.
  - Every token checked to WCAG AA for text with the dataviz validator.

### Task 3: Removed

The theme proposals are no longer needed; Task 4 implements the settled theme directly.

### Task 4: Design tokens, UI kit and logos

**Files:**
- Create: `frontend/src/theme/tokens.css`, `frontend/src/theme/base.css`, `frontend/src/ui/{Button,Select,Menu,Dialog,Tabs,Field,TextArea,Table,TierChip,StatusDot,Card,Stat,EmptyState,ErrorState,Skeleton,Toast,ReasoningPanel,AiSection,ConfirmBar}.tsx`, `frontend/src/ui/charts/{LineChart,BarChart,HeatGrid,Sparkline}.tsx`, `frontend/src/brand/{DataLensLogo,MirsalLogo,SahelLogo,BayanLogo,ClinicLogo}.tsx`
- Delete: `frontend/src/pages/ThemeLab.tsx`, `frontend/src/theme/proposals/`
- Test: `frontend/src/ui/ui.test.tsx`

**Interfaces:**
- Produces: `<Select value onValueChange options={{value,label,hint?}[]} placeholder? disabled? />`; `<TierChip tier="fit"|"fit_with_controls"|"reassign"|"refer"|"unknown" />`; `<AiSection draft={AiDraft} onConfirm onEdit confirmLabel />` where `AiDraft = { id: string; kind: string; content: string; sure: string[]; unsure: string[]; would_change: string[]; confidence: number; reasoning: { evidence: string[]; rules: string[]; inferences: string[]; rejected: string[] }; status: "draft"|"confirmed"|"unavailable"; confirmed_by?: string; model?: string }`; `<ReasoningPanel reasoning />`; logo components accept `size` and `variant="mark"|"full"`.

- [ ] **Step 0:** Write `docs/checkpoints/theme/decision.md` from Checkpoint 1; load the `artifact-design` and `dataviz` skills for palette and chart guidance; the reference image is at `docs/checkpoints/theme/reference.png`.
- [ ] **Step 1: Write the failing tests:** `Select opens, shows options, keyboard selects with ArrowDown+Enter`; `TierChip renders the plain label "Reassign today" for reassign`; `AiSection with status unavailable shows "Draft not available" and an editable text area`.
- [ ] **Step 2:** Run vitest. Expected: FAIL.
- [ ] **Step 3:** Implement tokens from the chosen palette, the 8 px spacing scale, type scale (Inter via @fontsource unless Checkpoint 1 chose otherwise), control heights per Global Constraints, focus rings. Radix-based Select and Menu with item padding 8 px 12 px, check icon, scroll buttons, max height 320 px, collision-aware positioning, and width matched to trigger.
- [ ] **Step 4:** Draw logos as SVG: Mirsal Terminals (a quay crane over a wave line), Sahel Marine Services (a dhow sail), Bayan Manpower Contracting (a hard hat with a rising arc), Mirsal Village Clinic (a palm leaf inside a soft cross), Data Lens (a lens aperture with a pulse line). No letters inside any mark.
- [ ] **Step 5:** Run vitest. Expected: PASS. Commit `feat: design tokens, UI kit and logos`.

---

## Phase 1: Data and access

### Task 5: Domain models and first migration

**Files:**
- Create: `backend/app/models/{__init__,org,people,activities,roster,feeds,records,warnings,permits,actions,learning,health,governance,ai}.py`, `backend/migrations/versions/0001_initial.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Produces (SQLAlchemy models, tables named in snake case plural):
  - org: `Employer(id, name, kind: "in_house"|"contractor", logo_key)`, `Zone(id, name, kind: "berth"|"yard_block"|"camp_block"|"district", parent_id)`, `Clinic(id, name, zone_id)`.
  - people: `Person(id, employer_id, first_name, last_name, email, role, job_title, hire_date, site_arrival_date, induction: "site"|"contractor", camp_zone_id, display_language, password_hash, active)`, `Competency(id, code, name)`, `PersonCompetency(person_id, competency_id, valid_until)`, `TrainingRecord(id, person_id, course_code, completed_on)`.
  - activities: `Activity(id, code, name, grade 1..5, exposure_hours_week, severity 1..5, competency_id, lower_hazard_alternative_id)`, `Hazard(id, code, name)`, `ActivityHazard(activity_id, hazard_id)`, `SwpItem(id, activity_id, seq, text, active)`.
  - roster: `Shift(id, date, kind: "day"|"night", start_at, end_at)`, `Gang(id, name, foreman_id)`, `Assignment(id, shift_id, person_id, activity_id, gang_id, source: "roster"|"swap")`, `CheckIn(id, person_id, shift_id, at, sleep_hours_band, feeling: "good"|"tired"|"unwell", hydration_ok)`, `Absence(id, person_id, date, kind)`.
  - feeds: `Feed(id, code, name, signal_class: "clinical"|"workplace"|"environmental"|"community"|"worker_reported", cadence_minutes, allowed_delay_minutes, location_level, enabled, source: "seeded"|"live"|"uploaded")`, `FeedReading(id, feed_id, zone_id, at, metric, value, source)`, `ClinicVisit(id, clinic_id, person_id, zone_id, at, syndrome)`, `CampTicket(id, zone_id, opened_at, closed_at, kind, units_affected, units_total)`, `LabPanel(id, person_id, at, panel, value, flag)`.
  - records: `Observation(id, activity_id, zone_id, person_id nullable, at, kind: "unsafe_act"|"unsafe_behaviour"|"unsafe_condition"|"safe", shift_kind, text)`, `NearMiss`, `Incident(id, activity_id, zone_id, reported_by, at, text, photo_key, potential_severity, status, ...)`, `HazardReport`.
  - warnings: `WarningRecord(id, opened_at, zone_id, level: "watch"|"warning"|"alert", status, outcome: null|"right"|"early"|"false_alarm"|"missed", closed_at)`, `WarningStep(id, warning_id, step 1..10, draft_id, status, confirmed_by, confirmed_at)`.
  - permits: `Permit(id, number, activity_id, zone_id, shift_id, status: "requested"|"assessed"|"issued"|"live"|"suspended"|"closed", issuer_id)`, `PermitCondition(id, permit_id, text, origin: "issuer"|"warning", warning_id, status: "draft"|"accepted"|"edited"|"rejected")`, `PermitEvent(id, permit_id, at, kind, text, actor_id)`.
  - actions: `Action(id, source_kind, source_id, title, control_level: "eliminate"|"substitute"|"engineer"|"administrative"|"ppe", owner_id, due_on, status, effectiveness_check_on, effective: bool|null)`, `Inspection(id, source_kind, source_id, zone_id, due_at, status)`, `InspectionCheck(id, inspection_id, driver, question, result: null|"confirmed"|"not_found", note)`.
  - learning: `LearningItem(id, kind: "card"|"toolbox_talk"|"swp_change", source_kind, source_id, draft_id, status)`, `LearningRead(item_id, person_id, at)`.
  - health: `FitnessOutcome(id, person_id, decided_by, at, outcome: "fit"|"fit_with_restrictions"|"not_today", restriction_text, share_with_employer: bool)`, `UnwellEvent(id, person_id, shift_id, at, permit_id)`.
  - governance: `SiteClock(id=1, now)`, `Setting(key, value)`, `WeightsVersion(id, version, status: "active"|"proposed"|"retired", body_json, approved_by, approved_at)`, `AuditEntry(id, at, actor_id, actor_role, action, subject_kind, subject_ref, evidence_json, model_version)` (no update or delete path).
  - ai: `AiDraft(id, kind, subject_kind, subject_id, prompt_version, model, deployment, content, sure_json, unsure_json, would_change_json, confidence, reasoning_json, status, created_at)`, `AiImage(id, kind, subject_id, path, model, prompt, created_at)`.
  - Engine outputs (computed, written by engine runs): `ScoreRun(id, kind: "evening"|"shift_start"|"manual", shift_id, weights_version_id, ran_at, conditions_source: "scenario"|"live")`, `AssignmentScore(id, run_id, assignment_id, intrinsic, control, condition, profile, r, tier, drivers_json, confidence, group_step_limited)`, `SwapProposal(id, run_id, assignment_id, to_activity_id, status: "proposed"|"accepted"|"declined"|"approved"|"rejected", reason, decided_by)`, `Contest(id, assignment_score_id, person_id, text, status)`.

- [ ] **Step 1: Write the failing tests:** `test_people_has_no_protected_columns` (Person columns exclude `nationality`, `religion`, `ethnicity`, `origin`); `test_audit_entry_cannot_be_updated` (an ORM update to AuditEntry raises); `test_tables_created_from_migration` (alembic upgrade head on a temp DB creates every table above).
- [ ] **Step 2:** Run `uv run pytest tests/test_models.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement the models; block AuditEntry update and delete through a `before_flush` listener; generate and hand-check the migration.
- [ ] **Step 4:** Run tests. Expected: PASS. Commit `feat: domain models and initial migration`.

### Task 6: Authentication and role access

**Files:**
- Create: `backend/app/auth/{security,deps,router}.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `hash_password(p: str) -> str`, `verify_password(p: str, h: str) -> bool`; `POST /api/auth/login {email, password}` sets an httpOnly cookie `dl_session` (JWT, 12 h); `POST /api/auth/logout`; `GET /api/auth/me -> {id, name, role, employer, email, display_language}`; dependencies `current_user() -> Person`, `require_roles(*roles) -> Callable`.

- [ ] **Step 1: Write the failing tests:** `test_login_with_welcome_password_succeeds`; `test_login_with_wrong_password_returns_401_without_revealing_which_field`; `test_require_roles_blocks_other_roles_with_403`; `test_email_login_is_case_insensitive`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with argon2-cffi and PyJWT; secret from settings, generated into `.env.example` documentation only.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: authentication and role guards`.

### Task 7: Site clock, audit log, access policy and small-cell suppression

**Files:**
- Create: `backend/app/clock.py`, `backend/app/audit.py`, `backend/app/policy/{access,suppression}.py`
- Test: `backend/tests/test_policy.py`

**Interfaces:**
- Produces: `site_now(session) -> datetime`; `set_site_now(session, at, actor)` (audited); `current_shift(session) -> Shift`; `audit(session, actor, action, subject_kind, subject_ref, evidence=None, model_version=None)`; `ACCESS: dict[role, set[DataScope]]` with `DataScope` in `{"own_profile","own_health","crew_actions","site_tiers","permit_counts","aggregates","all_records","health_detail","district_aggregates","employer_aggregates","audit_redacted","admin"}`; `can(role, scope) -> bool`; `suppress(cells: list[Cell], k: int) -> SuppressedTable` where suppressed cells become `None` and every total is `round_to_5(total)`; `shift_token(person_id, shift_id) -> str` (HMAC, used in audit for reassignments).

- [ ] **Step 1: Write the failing tests:**
  - `test_suppression_hides_cells_below_threshold`: cells [12, 4, 30] with k=10 give [12, None, 30].
  - `test_totals_rounded_so_hidden_cell_not_recoverable`: total of [12, 4, 30] is reported as 45 (46 rounded to 5), and total minus visible cells does not equal 4.
  - `test_threshold_setting_is_read_from_settings_table`.
  - `test_reassignment_audit_uses_shift_token_not_person_id`.
  - `test_planner_cannot_read_health_detail` and `test_authority_reads_audit_redacted_only` (`can()` truth table matches spec 5.2 and 5.14).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. `round_to_5(n) = 5 * round(n / 5)`.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: site clock, audit, access policy, suppression`.

### Task 8: Reference catalogue and weights v0

**Files:**
- Create: `backend/seed/catalog.py`, `backend/app/engine/weights.py`, `backend/seed/weights_v0.json`
- Test: `backend/tests/test_catalog.py`

**Interfaces:**
- Produces: `ACTIVITIES` (13 entries), `HAZARDS` (6, the rows of spec sensitivity matrix), `GROUPS` (6 definitions with `defines(person, history) -> bool`), `EMPLOYERS`, `ZONES`, `KEY_USERS`; `load_weights(session, version=None) -> Weights` with fields `sens: dict[hazard_code, dict[dimension, "H"|"M"|"L"]]`, `sens_value: {"H":0.35,"M":0.20,"L":0.08}`, `thresholds: dict[grade, tuple[float,float]]`, `factor_caps`, `fatigue_by_night: {1:1.0, 2:1.05, 3:1.12, 4:1.36}`, `heat_by_tier: {0:1.0, 1:1.08, 2:1.17, 3:1.17}`, `condition_terms`, `control_formula_k: 0.5`, `group_cap: 1.6`.
- Activities (code, grade): `LASH_DECK` Lashing at height on deck (5, 1440 worker-hours a week, 14 SWP items, lower-hazard alternative `TWIST_GROUND`); `QC_OPS` Quay crane operation (5); `MOORING` Mooring and unmooring (5); `HOLD_CONFINED` Hold cleaning in a confined space (5); `HOT_WORK` Hot work in the workshop (4); `REACH_STACKER` Reach stacker operation (4); `TT_DRIVING` Terminal tractor driving (4); `TWIST_GROUND` Ground twist-lock handling (3); `REEFER` Reefer plugging and monitoring (3); `WORKSHOP_MECH` Workshop mechanical maintenance (3); `CONTAINER_INSPECT` Container inspection and sealing (2); `YARD_HOUSEKEEPING` Yard housekeeping (2); `GATE_CLERK` Gate clerk (1).
- Key users (all `@mirsalterminals.com`): `hessa.almansoori` admin; `layla.haddad` hse_head; `daniel.mensah` planner; `khalid.alnuaimi` shift_manager; `priya.raman` permit_issuer; `joseph.kariuki` foreman (deck gang 3); `tomas.reyes` foreman (yard); `sara.ibrahim` clinician; `ahmed.alshamsi` authority; `arjun.thapa` worker (the lasher: Bayan Manpower, contractor induction, arrived 4 months ago, Camp Block C, height refresher not done).

- [ ] **Step 1: Write the failing tests:** `test_thirteen_activities_with_grades_as_listed`; `test_sensitivity_matrix_matches_spec_rows` (fall from height: H,H,M,H,H,H; struck by plant: H,M,L,M,H,M; dropped load: M,M,L,L,H,H; heat illness: H,H,M,H,L,L; manual handling: M,M,H,M,M,L; hot work and confined space: H,H,M,H,H,H); `test_weights_v0_constants_match_plan`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement; `weights_v0.json` is the single source and is loaded into `WeightsVersion` as `v0`, status active.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: reference catalogue and weights v0`.

### Task 9: Raw history generator

**Files:**
- Create: `backend/seed/generate.py`, `backend/seed/names.py`, `backend/seed/weather_archive.py`, `backend/seed/data/abu_dhabi_2025_hourly.json`, `backend/scripts/seed.py`
- Test: `backend/tests/test_seed.py`

**Interfaces:**
- Consumes: catalogue and models.
- Produces: `uv run python scripts/seed.py --fresh` builds `data/datalens.db` deterministically (seed 20260729); `generate(session, rng)`.
- Content: 400 workers (Mirsal in-house about 45 percent, Sahel 30, Bayan 25) plus the key users; group membership emerges from records so that group sizes land at 48, 26, 22, 58, 31, 34; 5 camp blocks (A to E, 40 cooling units each); 4 berths, 6 yard blocks, 2 districts; day and night shifts 1 May to 29 Jul 2026; rosters with realistic night rotations; check-ins at about 85 percent response; observation cards, near misses, incidents and hazard reports for 12 months (1 Aug 2025 to 28 Jul 2026); every other feed for 90 days; MV Saffron Horizon berthing at Berth 2 on the night shift of 29 Jul.
- Weather: hourly temperature, humidity, wind and radiation for Abu Dhabi (24.45 N, 54.38 E) for 1 May to 29 Jul 2025, fetched once from the Open-Meteo archive and committed as JSON, then mapped to 2026 dates. Seeded deck WBGT derives from it with the formula in Task 23.

- [ ] **Step 1: Write the failing tests:** `test_seed_is_deterministic` (two runs give identical row counts and identical first 50 observation rows); `test_four_hundred_workers_three_employers`; `test_every_feed_has_90_days`; `test_uabc_history_spans_12_months`; `test_no_derived_tables_populated` (ScoreRun, AssignmentScore, WarningRecord for open events are empty after seeding).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Fetch the archive once (`weather_archive.py`, run manually, output committed). Implement the generator, with names drawn from a broad international list; names never influence any other generated value.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: deterministic raw history generator`.

### Task 10: Injected events and the lasher's story

**Files:**
- Create: `backend/seed/events.py`
- Test: `backend/tests/test_events.py`

**Interfaces:**
- Produces: `inject(session, rng)`, called by `generate` after the base history; `INJECTED_EVENTS` list with `{code, zone, window, signals, closed}` used by the back-test as ground truth.
- Events: `E1_DUST_RESP` respiratory cluster in Yard Block 4 with high PM10 (May, closed); `E2_NIGHT_FATIGUE` night lashing near-miss cluster (June, closed); `E3_PLANT_STRUCK` reach stacker struck-by pattern in Yard Block 2 (early July, closed); `E4_CAMP_C_COOLING` Camp Block C: 11 of 40 cooling units down from 25 Jul, clinic heat visits from Block C at about twice baseline, on the scenario date open.
- Story facts the seed must make true (then computed by the engine): `LASH_DECK` has 11 unsafe acts, 6 unsafe behaviours, 7 unsafe conditions and 3 near misses in 12 months, all on nights; Arjun Thapa is on his third consecutive night on 29 Jul, short sleep in 2 of his last 10 check-ins, height refresher not completed; forecast WBGT 34 at 12:00 on 29 Jul; one worker in his gang cleared by the clinician on 19 Jul.

- [ ] **Step 1: Write the failing tests:** `test_lash_deck_uabc_counts_match_story`; `test_arjun_third_night_on_29_july`; `test_camp_c_tickets_11_of_40`; `test_camp_c_clinic_heat_visits_about_double_baseline` (ratio between 1.8 and 2.4 over 25 to 28 Jul).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS. Run `scripts/seed.py --fresh`; commit `feat: injected events and story facts` with the database file.

---

## Phase 2: The engine

### Task 11: Readiness vector

**Files:**
- Create: `backend/app/engine/readiness.py`
- Test: `backend/tests/engine/test_readiness.py`

**Interfaces:**
- Produces: `@dataclass ReadinessInputs(person_id, consecutive_nights, acclimatisation_days, short_sleep_checkins_last10, latest_checkin: CheckIn|None, competencies_current: set[str], training_missing: set[str], group_code: str|None, fitness_outcome: FitnessOutcome|None, lab_flags: int)`; `gather_inputs(session, person_id, shift_id) -> ReadinessInputs`; `readiness(inputs, weights) -> dict[Dimension, Factor]` where `Dimension` is `"fatigue"|"heat_strain"|"physical"|"acute"|"safety_behaviour"|"competency"` and `Factor = {multiplier: float, deficit: float 0..1, confidence: float, freshness_hours: float, source: str, reason: str}`.

- [ ] **Step 1: Write the failing tests:** `test_inputs_dataclass_has_no_protected_fields`; `test_third_night_fatigue_multiplier` (1.12 before short-sleep adjustment); `test_group_multiplier_capped_at_1_6`; `test_missing_checkin_lowers_confidence_and_marks_acute_unknown`; `test_reason_text_uses_work_terms_not_diagnosis` (no lab or syndrome words in `reason`).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: readiness vector`.

### Task 12: Layers, score, tier and the golden test

**Files:**
- Create: `backend/app/engine/{layers,score}.py`
- Test: `backend/tests/engine/test_golden_lasher.py`, `backend/tests/engine/test_score.py`

**Interfaces:**
- Consumes: `readiness()`, `load_weights()`.
- Produces: `intrinsic(activity) -> Intrinsic(grade, thresholds, value=1.0)`; `control(session, activity_id, at, weights) -> LayerResult`; `condition(session, shift_id, activity, weights, source="scenario"|"live") -> LayerResult`; `profile(readiness, activity, weights) -> LayerResult`; `score(session, assignment_id, weights, conditions_source) -> ScoreResult(intrinsic, control, condition, profile, r, tier, drivers: list[Driver], confidence, group_step_limited: bool)`; `Driver = {layer, name, contribution, source, freshness_hours}`.
- Algorithm the tests do not fully determine:

```text
control   = clamp(1 + k * (rate_activity / rate_site - 1), 0.8, 1.5), rates = UABC events per 1,000 worker-hours over 12 months
condition = product over terms t of [1 + (c_t - 1) * sens_t(activity)]   terms: heat tier, dust, night, pace, camp recovery
profile   = product over dimensions f of [1 + (m_f - 1) * sens(hazard_max, f)], sens from the activity's highest-sensitivity hazard row
R         = 1.0 * control * condition * profile
tier      = refer if a health signal needs a clinician; unknown if no check-in at shift start re-score;
            else by grade thresholds; then if removing the group factor lowers the tier by more than one step, raise it back to one step above
```

- [ ] **Step 1: Write the failing golden test** `test_lasher_reproduces_walkthrough`: on the seeded scenario for Arjun on `LASH_DECK` night shift 29 Jul with weights v0: `control == approx(1.15, abs=0.02)`, `condition == approx(1.25, abs=0.02)`, `profile == approx(1.35, abs=0.02)`, `r == approx(1.94, abs=0.03)`, `tier == "reassign"`.
- [ ] **Step 2: Write the failing unit tests:** `test_grade_2_not_scored_per_person`; `test_grade_3_thresholds_1_5_and_2_4`; `test_group_factor_moves_tier_at_most_one_step`; `test_unwell_checkin_gives_refer`; `test_drivers_sorted_by_contribution_with_source_and_freshness`.
- [ ] **Step 3:** Run. Expected: FAIL.
- [ ] **Step 4:** Implement; tune only the condition term values and seed facts (never the test) until the golden test passes, and record the tuned values in `weights_v0.json`.
- [ ] **Step 5:** Run. Expected: PASS. Commit `feat: four-layer score and golden lasher test`.

### Task 13: Crew rules, alert budget and greedy swaps

**Files:**
- Create: `backend/app/engine/{crew_rules,budget,swaps}.py`
- Test: `backend/tests/engine/test_crew.py`

**Interfaces:**
- Produces: `check_crew_rules(scores: list[ScoreResult], gang, heat_tier) -> list[RuleBreach(rule, detail)]`; `apply_budget(recommendations, planner_limit=3, foreman_limit=2) -> (shown, rolled_into_brief)`; `propose_swaps(session, run_id, scores, weights) -> list[SwapProposal]` (greedy: highest R first, candidate activities within the person's competencies and the employer's contract scope, pick the lowest resulting R that keeps every crew rule, stop at budget).

- [ ] **Step 1: Write the failing tests:** `test_quarter_of_crew_on_controls_rule_in_heat_tier_2`; `test_arrivals_under_7_days_capped_at_2_per_gang`; `test_high_hazard_task_keeps_one_experienced_worker`; `test_budget_shows_three_and_rolls_rest_into_brief`; `test_arjun_swap_proposal_is_ground_twist_lock_handling`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: crew rules, alert budget, greedy swaps`.

### Task 14: Monte Carlo split of risk

**Files:**
- Create: `backend/app/engine/montecarlo.py`
- Test: `backend/tests/engine/test_montecarlo.py`

**Interfaces:**
- Produces: `split_risk(session, shift_id, weights, n=2000, seed=7) -> {total_expected: float, conditions_share: float, crew_share: float, p10: float, p90: float}`; uncertain inputs sampled: forecast WBGT (normal, sd 1.5 °C), attendance (Bernoulli per worker from absence history), check-in response (Bernoulli 0.85).

- [ ] **Step 1: Write the failing tests:** `test_shares_sum_to_one`; `test_same_seed_same_result`; `test_hotter_forecast_raises_conditions_share`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with numpy; shares by variance decomposition (vary one group of inputs while holding the other at its mean).
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: Monte Carlo split between conditions and crew`.

### Task 15: Engine runs and the learning layer

**Files:**
- Create: `backend/app/engine/run.py`, `backend/app/engine/groups.py`, `backend/app/engine/learn.py`
- Test: `backend/tests/engine/test_run.py`

**Interfaces:**
- Produces: `run_scores(session, shift_id, kind, conditions_source="scenario", actor=None) -> ScoreRun` (scores every graded assignment, writes `AssignmentScore` and `SwapProposal` rows, audits); `recompute_groups(session, at) -> list[GroupRate(code, people, unsafe_per_100_cards, multiplier)]`; `propose_weights_from_outcomes(session) -> WeightsVersion|None` (status proposed); `approve_weights(session, version_id, actor)`.

- [ ] **Step 1: Write the failing tests:**
  - `test_evening_run_scores_every_graded_assignment_for_29_july_night`.
  - `test_worker_without_checkin_is_unknown_at_shift_start` (Review Focus 1).
  - `test_group_rates_within_0_05_of_spec_table` (0.8, 1.6, 1.3, 0.9, 1.4, 1.0).
  - `test_confirmed_near_miss_raises_control_on_next_run`.
  - `test_proposed_weights_not_used_until_approved`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: engine runs, group recompute, weights proposals`.

---

## Phase 3: Detector and back-test

### Task 16: Baselines and the early warning detector

**Files:**
- Create: `backend/app/detector/{baselines,detect,open_record}.py`
- Test: `backend/tests/detector/test_detect.py`

**Interfaces:**
- Produces: `baseline(session, feed_code, zone_id, day) -> Baseline(mean, sd, days_used)` (rolling 28 days before `day`, excluding days inside open warnings); `detect(session, day, action_line=1.5, feeds_off=frozenset()) -> list[Signal(zone_id, level, index, classes_agreeing, contributions: list[Contribution(feed, zone, period, ratio)], late_feeds: list[str])]`; `open_warning(session, signal, actor="system") -> WarningRecord` (creates 10 `WarningStep` rows, step 2 and 3 marked "linked by AI").
- Rules: index = mean of per-feed ratio to baseline among feeds above 1.0; level `watch` when one class is up or index at or above 0.8 times the action line; `warning` when two or more classes agree in the same zone and period and index at or above the action line; `alert` when index at or above 1.5 times the action line with three classes; fewer than two live classes caps at `watch`; clinic or weather missing drops one level; records without location count only toward the district.

- [ ] **Step 1: Write the failing tests:** `test_camp_c_raises_warning_on_27_july` (clinical plus community agree); `test_single_class_never_above_watch`; `test_clinic_feed_off_drops_one_level_and_is_named` (Review Focus 2); `test_unlocated_records_count_to_district_only`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: early warning detector`.

### Task 17: Back-test harness

**Files:**
- Create: `backend/app/backtest/{harness,measures}.py`, `backend/scripts/backtest.py`
- Test: `backend/tests/backtest/test_backtest.py`

**Interfaces:**
- Produces: `run_backtest(session, action_line, feeds_off=frozenset(), weights_version=None) -> BacktestResult(lead_time_hours: dict[event, float|None], sensitivity: (found, total), ppv: float, false_alarms_per_30d: float, latency_by_feed: dict[str, float], budget_breaches: int, warnings: list)`; `sweep(session, lines=[1.2,1.3,...,2.0]) -> list[BacktestResult]` and `choose_action_line(results) -> float` (most sensitive line with zero budget breaches); results stored in `Setting("backtest_last")` for the screen.
- The harness replays day by day and lets the detector see each day once (no future reads; enforced by passing a `day` cut-off into every query).

- [ ] **Step 1: Write the failing tests:** `test_no_future_reads` (a sentinel row dated after the cut-off is never returned); `test_all_four_events_found_with_lead_time_at_least_72h` (the seed design target); `test_ppv_between_0_5_and_0_8`; `test_switching_off_clinic_feed_degrades_result`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. If targets miss, adjust the seed signal strength in `events.py`, never the measures.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: back-test harness and measures`.

---

## Phase 4: AI

### Task 18: Azure OpenAI client, provenance and fallback

**Files:**
- Create: `backend/app/ai/{client,drafts,schemas}.py`, `backend/app/ai/prompts/` (one `.md` per kind, with a `version:` header)
- Test: `backend/tests/ai/test_client.py`

**Interfaces:**
- Produces: `get_or_draft(session, kind, subject_kind, subject_id, context: dict, language="en") -> AiDraft` (returns a stored draft for the same kind, subject and prompt version; otherwise calls the Responses API on `ai_text_model` with JSON-schema output and stores it; on any failure stores nothing and returns an `AiDraft` with status `unavailable`); `decide(session, subject_kind, subject_id, input: str | list, questions: list[Question]) -> Decisions | None` (calls `POST {azure_v1_base}/decisions` on `ai_decisions_model`; `Question = Predicate(name, instructions) | Choice(name, instructions, choices: list[(value, description)]) | Score(name, instructions, levels: list[(label, description)])` with 1 to 400 questions and 2 to 10 levels; returns answers keyed by name with probability, choice or score, per-option probabilities and confidence; stored as `AiDecision` rows with provenance; returns `None` on failure); `ai_available() -> bool`; text kinds: `brief`, `warning_step_1` to `warning_step_10`, `incident_record`, `learning_card`, `toolbox_talk`, `swp_change`, `reason_translation`, `question_answer`.
- Add model `AiDecision(id, subject_kind, subject_id, model, questions_json, answers_json, created_at)` and its migration.
- Every call is audited with model and prompt version.

- [ ] **Step 1: Write the failing tests:** `test_stored_draft_reused_without_calling_azure`; `test_timeout_returns_unavailable_and_stores_nothing` (Review Focus 5); `test_malformed_json_returns_unavailable`; `test_decide_parses_predicate_choice_and_score_answers` (recorded response fixture); `test_decide_rejects_more_than_400_questions`; `test_decide_refusal_answer_is_kept_as_refusal`; `test_env_values_never_logged` (capture logs, assert the key value is absent).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with the `openai` package's `OpenAI` client pointed at `azure_v1_base` with the `api-key` header (Responses API), and `httpx` for `/decisions`. Record one real response of each kind as test fixtures.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: Azure OpenAI client with provenance and fallback`.

### Task 19: Prompts and the role boundary for questions

**Files:**
- Modify: `backend/app/ai/prompts/*.md`
- Create: `backend/app/ai/context.py`
- Test: `backend/tests/ai/test_context.py`

**Interfaces:**
- Produces: `build_context(session, user, kind, subject) -> dict` (only data the user's role may see, via `can()`); `answer_question(session, user, text) -> AiDraft` (first calls `decide()` with one choice question per `DataScope` ("needed" or "not needed"); if any needed scope is outside `can(user.role, scope)`, declines with the boundary named and audits the decline, without generating text; if `decide()` fails, answers only from the user's own scopes and says so).
- Prompt rules: plain business language, no diagnosis in planner or permit text, state sure / unsure / would change, never name a person in permit or aggregate text.

- [ ] **Step 1: Write the failing tests:** `test_planner_context_has_no_health_detail`; `test_permit_context_has_counts_not_names`; `test_planner_question_about_lab_results_is_declined_and_audited` (stub `decide()` marks `health_detail` needed; assert no text call made).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement and write the prompts.
- [ ] **Step 4:** Run. Expected: PASS. Commit `feat: role-scoped AI context and prompts`.

### Task 20: Authored AI seed content (no Azure calls)

Deva's instruction (15 Nov): generate all synthetic data yourself.
The drafts and decisions that history and the scenario need are written by the builder as seed content, not generated through Azure.
Azure (`gpt-6-luna`) is called only at runtime for new events.

**Files:**
- Create: `backend/seed/ai_content/` (one JSON file per kind: `briefs.json`, `warnings_closed.json`, `warning_camp_c.json`, `incidents.json`, `learning.json`, `reasons_translated.json`), `backend/seed/ai_load.py`, `docs/azure-deployments.md`
- Test: `backend/tests/ai/test_ai_seed.py`

**Interfaces:**
- Produces: `load_ai_content(session)` called by `scripts/seed.py`: writes `AiDraft` and `AiDecision` rows with `model = "authored-seed"` and the current prompt version, so `get_or_draft` reuses them and never calls Azure for seeded subjects.
- Content needed: the three closed warnings' ten steps (all confirmed, with outcomes), the Camp Block C warning's step 1 to 3 drafts (unconfirmed, for the demo), historical incidents' records with triage and 5 by 5 answers, learning items, Arjun's reason in his display language, the role briefs for 28 Jul evening and 29 Jul shift start.
- Every authored text follows the same JSON shape as a live draft (content, sure, unsure, would change, confidence, reasoning) and quotes only figures that the engine and detector actually compute on the seed (check them against the computed values).

- [ ] **Step 1: Write the failing tests:** `test_seeded_subjects_never_call_azure` (counting stub client, zero calls when opening every seeded record); `test_authored_figures_match_computed` (numbers in the Camp Block C step 1 draft equal the detector's output for that zone and period).
- [ ] **Step 2:** Run. Expected: FAIL. Write the content and the loader. Run. Expected: PASS.
- [ ] **Step 3:** Write `docs/azure-deployments.md` with the confirmed deployment names (no keys or host names). Read all authored content once more for plain language and no em dashes.
- [ ] **Step 4:** Snapshot: copy `datalens.db` to `scenario.db`. Commit `feat: authored AI seed content` with both database files.

---

## Phase 5: Feeds

### Task 21: Live weather feed

**Files:**
- Create: `backend/app/feeds/weather_live.py`, `backend/app/feeds/scheduler.py`
- Test: `backend/tests/feeds/test_weather.py`

**Interfaces:**
- Produces: `estimate_wbgt(temp_c: float, rh_pct: float) -> float` using `e = (rh/100) * 6.105 * exp(17.27 * T / (237.7 + T))`, `WBGT = 0.567 * T + 0.393 * e + 3.94`; `heat_tier(wbgt) -> int` per Global Constraints; `pull_live_forecast(session) -> int` (Open-Meteo forecast for 24.45 N, 54.38 E, next 48 h hourly, stored as `FeedReading(source="live")`); scheduler runs it hourly inside the app process.

- [ ] **Step 1: Write the failing tests:** `test_wbgt_known_value` (T=40, RH=40 gives 33.2 ± 0.3); `test_heat_tier_boundaries` (26.9→0, 27→1, 30→2, 32→3); `test_failed_pull_marks_feed_late_and_keeps_old_rows` (Review Focus 2).
- [ ] **Step 2:** Run. Expected: FAIL. Implement. Run. Expected: PASS.
- [ ] **Step 3:** Commit `feat: live weather feed with WBGT estimate`.

### Task 22: Sensor ingest, replay and new feed upload

**Files:**
- Create: `backend/app/feeds/{ingest,csv_connect}.py`, `backend/scripts/replay_sensor.py`
- Test: `backend/tests/feeds/test_ingest.py`

**Interfaces:**
- Produces: `POST /api/ingest/sensor` with a gateway token header and `{sensor_id, zone_code, at, metric: "wbgt", value}`; on a live permit in that zone, WBGT over 32 for 30 minutes raises a permit event and a foreman prompt for the work-rest change. `scripts/replay_sensor.py --from 2026-07-29T10:00 --speed 60` posts seeded deck WBGT readings and advances the site clock. `POST /api/signals/connect` takes a CSV and calls `decide()` once with, per column, a choice question (target field from the fixed feed schema, or "ignore") and a predicate ("is free text"), using the header and 20 sample values as input JSON; returns the proposed mapping with confidence; `POST /api/signals/connect/{id}/confirm` creates the feed and loads rows.

- [ ] **Step 1: Write the failing tests:** `test_wbgt_over_32_for_30_min_creates_permit_event_and_foreman_prompt`; `test_bad_gateway_token_rejected`; `test_free_text_columns_never_loaded`.
- [ ] **Step 2:** Run. Expected: FAIL. Implement. Run. Expected: PASS.
- [ ] **Step 3:** Commit `feat: sensor ingest, replay and feed connect`.

---

## Phase 6: Modules (API plus screens)

Each task below adds one router under `backend/app/api/` and its pages under `frontend/src/pages/`, with API tests and one Playwright test in `frontend/e2e/`.
Every page has loading, empty and error states from the UI kit.
Every page is checked by eye at 1440 px and 390 px before the commit, and anything misaligned is fixed in the same task.

### Task 23: App shell, login and the role home brief

**Files:**
- Create: `backend/app/api/home.py`, `frontend/src/layout/{AppShell,Sidebar,TopBar,PhoneShell}.tsx`, `frontend/src/pages/{Login,Home}.tsx`, `frontend/src/auth/useMe.ts`
- Test: `backend/tests/api/test_home.py`, `frontend/e2e/home.spec.ts`

**Interfaces:**
- Produces: `GET /api/home -> {brief: AiDraft, decisions: Decision[3], waiting: DraftRef[], permits_summary, watchers}`; navigation items per role from `GET /api/auth/me`; worker and foreman land on `/m`.

- [ ] **Step 1:** Failing tests: `test_home_brief_is_role_specific`; e2e `each key user logs in and lands on their home` (looping over KEY_USERS).
- [ ] **Step 2:** Implement: login page with both logos and the help line listing the demo accounts; sidebar by role; site clock shown in the top bar; question box on Home calling `answer_question`.
- [ ] **Step 3:** Tests pass; visual check; commit `feat: shell, login, role home brief`.

### Task 24: Activities and behavioural groups

**Files:**
- Create: `backend/app/api/{activities,groups}.py`, `frontend/src/pages/{Activities,ActivityDetail,Groups}.tsx`
- Test: `backend/tests/api/test_activities.py`, `frontend/e2e/activities.spec.ts`

- [ ] **Step 1:** Failing tests: `test_activity_detail_shows_computed_control_multiplier`; `test_group_list_never_includes_member_names`; e2e `HSE head opens Lashing at height and sees grade 5, 14 SWP items and UABC history`.
- [ ] **Step 2:** Implement register table, activity detail (hazards, SWP items, UABC chart by month and shift, sensitivity profile), groups with computed rates, multipliers and copilot proposals.
- [ ] **Step 3:** Pass, visual check, commit `feat: activities and behavioural groups`.

### Task 25: Assignment risk, swaps and approval

**Files:**
- Create: `backend/app/api/assignments.py`, `frontend/src/pages/{Roster,AssignmentBuild}.tsx`
- Test: `backend/tests/api/test_assignments.py`, `frontend/e2e/assignments.spec.ts`

**Interfaces:**
- Produces: `GET /api/roster?shift_id=` (tiers, work-term reasons, controls; no health detail); `POST /api/runs {shift_id, kind, conditions_source}`; `GET /api/assignments/{id}/build` (layer by layer); `POST /api/swaps/{id}/accept|decline {reason}` (planner); `POST /api/swaps/{id}/approve|reject` (shift manager); `GET /api/risk-split?shift_id=`.

- [ ] **Step 1:** Failing tests: `test_planner_sees_reason_not_diagnosis`; `test_decline_requires_reason`; `test_shift_manager_approval_applies_swap_and_audits_with_token`; `test_decline_after_approval_returns_409` (Review Focus 3); e2e `planner accepts Arjun's swap, shift manager approves, roster shows ground twist-lock handling`.
- [ ] **Step 2:** Implement roster with tier filter Selects, crew rule breaches, budget banner, the layer-build view (four bars multiplying into R, drivers with source and freshness, scenario versus live forecast switch), Monte Carlo split card.
- [ ] **Step 3:** Pass, visual check, commit `feat: assignment risk, swaps and approval`.

### Task 26: Permits to work

**Files:**
- Create: `backend/app/api/permits.py`, `backend/app/permits/lifecycle.py`, `frontend/src/pages/{PermitBoard,PermitDetail}.tsx`
- Test: `backend/tests/api/test_permits.py`, `frontend/e2e/permits.spec.ts`

**Interfaces:**
- Produces: `transition(permit, to_status, actor)` with allowed moves requested→assessed→issued→live→(suspended↔live)→closed and send-back assessed→requested; `GET /api/permits`, `GET /api/permits/{id}` (people-and-conditions block as counts), `POST /api/permits/{id}/{sign|hold|send-back|suspend|resume|close}`, `PATCH /api/permits/{id}/conditions/{cid}`, `GET /api/permits/{id}/people-factor.json` (readiness counts, crew status, drivers, added controls, confidence, closing condition, audit reference).

- [ ] **Step 1:** Failing tests: `test_red_crew_blocks_issue_with_409`; `test_permit_shows_counts_never_names`; `test_people_factor_json_matches_contract_keys`; `test_warning_conditions_arrive_as_drafts_and_issuer_can_edit`; e2e `issuer edits the suspend condition and signs once the swap is settled`.
- [ ] **Step 2:** Implement board (columns by status, crew status dots), detail with conditions, live event log, JSON view.
- [ ] **Step 3:** Pass, visual check, commit `feat: permits to work`.

### Task 27: Early warnings and the ten-step record

**Files:**
- Create: `backend/app/api/warnings.py`, `frontend/src/pages/{Warnings,WarningRecord}.tsx`
- Test: `backend/tests/api/test_warnings.py`, `frontend/e2e/warning.spec.ts`

- [ ] **Step 1:** Failing tests: `test_steps_confirm_only_by_named_role` (steps 1, 4, 5, 7, 9 by hse_head; 8 by permit_issuer per permit; 6 completed by foreman); `test_step_9_drafts_only_from_confirmed_sections`; `test_close_requires_outcome`; `test_district_view_suppresses_small_cells` (Review Focus 4); e2e `HSE head walks Camp Block C warning from detection to permits affected`.
- [ ] **Step 2:** Implement site map grid of zones with deviation, district view, the record as a vertical stepper of `AiSection`s with confirm, edit and reasoning, outcome buttons (right, early, false alarm) feeding Task 15's proposals.
- [ ] **Step 3:** Pass, visual check, commit `feat: early warnings and warning record`.

### Task 28: Incidents, hazards and inspections

**Files:**
- Create: `backend/app/api/{incidents,inspections}.py`, `frontend/src/pages/{Incidents,IncidentRecord,ReportIncident,Inspections,InspectionRun}.tsx`
- Test: `backend/tests/api/test_incidents.py`, `frontend/e2e/incident.spec.ts`

- [ ] **Step 1:** Failing tests: `test_report_with_text_and_photo_creates_draft_record`; `test_triage_uses_decisions_for_type_severity_and_photo_checks` (stubbed `decide()` answers land on the record with confidence); `test_risk_matrix_cell_from_likelihood_and_severity_scores` (scores 3.6 and 4.2 round to cell L4 S4); `test_azure_down_still_saves_report_and_allows_manual_record` (Review Focus 5); `test_inspection_result_updates_warning_confidence`; e2e `foreman reports a near miss from the phone in under a minute, HSE head confirms the record`.
- [ ] **Step 2:** Implement phone-first report (text and photo upload; voice notes only if a speech-to-text deployment is confirmed at the time), the triage call to `decide()` (incident type choice, potential severity score 1 to 5, likelihood score 1 to 5, photo predicates), the written record from `get_or_draft` (safety chain, five whys, ranked actions), inspections from drivers with one check per driver, where each result note is checked by a `decide()` predicate ("does this note confirm the driver").
- [ ] **Step 3:** Pass, visual check, commit `feat: incidents, hazards and inspections`.

### Task 29: Actions and learning

**Files:**
- Create: `backend/app/api/{actions,learning}.py`, `frontend/src/pages/{Actions,Learning}.tsx`
- Test: `backend/tests/api/test_actions.py`, `frontend/e2e/actions.spec.ts`

- [ ] **Step 1:** Failing tests: `test_action_requires_owner_due_date_and_effectiveness_check`; `test_actions_sorted_by_hierarchy_of_controls`; `test_effectiveness_check_closes_linked_warning_on_site_clock`; `test_read_counts_by_crew_suppressed_below_threshold`.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** Pass, visual check, commit `feat: actions and learning`.

### Task 30: Health (clinician) and consent

**Files:**
- Create: `backend/app/api/health.py`, `frontend/src/pages/{ScreeningList,WorkerHealth}.tsx`
- Test: `backend/tests/api/test_health_module.py`, `frontend/e2e/health.spec.ts`

- [ ] **Step 1:** Failing tests: `test_only_clinician_reads_lab_trends`; `test_outcome_reaches_planner_without_reason`; `test_not_shared_outcome_shows_as_not_shared_and_engine_treats_unknown`; `test_clinician_decision_is_audited`.
- [ ] **Step 2:** Implement screening list (refer tier and unwell events), lab trend sparklines, outcome form, cohort trend release control.
- [ ] **Step 3:** Pass, visual check, commit `feat: clinician health module`.

### Task 31: Worker and foreman phones

**Files:**
- Create: `backend/app/api/phone.py`, `frontend/src/pages/phone/{WorkerHome,CheckIn,MyTier,Contest,Unwell,Cards,ForemanHome,Confirm}.tsx`
- Test: `backend/tests/api/test_phone.py`, `frontend/e2e/phone.spec.ts`

- [ ] **Step 1:** Failing tests: `test_checkin_is_three_taps` (sleep band, feeling, hydration in one POST); `test_worker_sees_reason_in_display_language`; `test_contest_creates_record_visible_to_planner`; `test_unwell_notifies_clinician_and_permit_without_name`; `test_foreman_sees_actions_not_answers`; e2e at 390 px `Arjun checks in, reads his reason, contests; Joseph confirms the work-rest change`.
- [ ] **Step 2:** Implement in `PhoneShell` with 44 px controls and bottom navigation.
- [ ] **Step 3:** Pass, visual check, commit `feat: worker and foreman phones`.

### Task 32: Analytics: validation and impact

**Files:**
- Create: `backend/app/api/analytics.py`, `backend/app/analytics/impact.py`, `frontend/src/pages/{Validation,Impact}.tsx`
- Test: `backend/tests/api/test_analytics.py`, `frontend/e2e/analytics.spec.ts`

**Interfaces:**
- Produces: `impact(inputs) -> {lti_avoided, workdays_avoided}` with defaults 40 LTIs a year, 40 percent hot-exposure, 20 percent fourth-or-later night, 70 percent acted on, 50 percent effectiveness, 20 workdays per injury; `POST /api/analytics/backtest {action_line, feeds_off}` runs the harness.

- [ ] **Step 1:** Failing tests: `test_impact_defaults_give_1_6_lti_and_31_workdays` (± 0.1 and ± 1); `test_feed_switch_off_reruns_and_degrades`.
- [ ] **Step 2:** Implement six measure tiles, lead-time chart, action-line sweep chart, feed switch panel, impact form with live result.
- [ ] **Step 3:** Pass, visual check, commit `feat: validation and impact analytics`.

### Task 33: Governance, audit and the Authority view

**Files:**
- Create: `backend/app/api/{governance,authority}.py`, `frontend/src/pages/{Governance,AuditTrail,District}.tsx`
- Test: `backend/tests/api/test_governance.py`, `frontend/e2e/governance.spec.ts`

- [ ] **Step 1:** Failing tests: `test_threshold_change_is_audited_and_applies_everywhere`; `test_autonomy_setting_per_action` (tell me / draft it / do it and tell me; reassign, sign, health restriction locked to people); `test_authority_sees_redacted_trail_and_counts_of_10_or_more`; `test_no_export_endpoint_for_tiers`.
- [ ] **Step 2:** Implement role-by-data matrix (rendered from `ACCESS`), threshold control, autonomy table, the line against employment use, audit trail with filters, Authority district page.
- [ ] **Step 3:** Pass, visual check, commit `feat: governance, audit and authority view`.

### Task 34: Signals and admin

**Files:**
- Create: `backend/app/api/{signals,admin}.py`, `frontend/src/pages/{Signals,ConnectFeed,People,SiteClock}.tsx`, `backend/scripts/reset.py`
- Test: `backend/tests/api/test_admin.py`, `frontend/e2e/admin.spec.ts`

**Interfaces:**
- Produces: `GET /api/signals` (nine feeds plus uploaded ones: class, cadence, latency, freshness, live or seeded); admin `POST /api/admin/people` (onboard with role and employer), `PATCH /api/admin/people/{id}`, `PUT /api/admin/clock`; `uv run python scripts/reset.py` restores `scenario.db` over `datalens.db`.

- [ ] **Step 1:** Failing tests: `test_onboarded_person_can_log_in_with_welcome_password`; `test_only_admin_moves_clock`; `test_reset_restores_scenario`.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** Pass, visual check, commit `feat: signals and admin`.

---

## Phase 7: Quality sweep

### Task 35: Role boundary sweep

**Files:**
- Test: `backend/tests/api/test_rbac_matrix.py`

- [ ] **Step 1:** Write a table-driven test calling every route as every role and asserting 200 or 403 exactly as `ACCESS` and spec 5.2 say. Run; fix every mismatch at the API.
- [ ] **Step 2:** Commit `test: role boundary sweep`.

### Task 36: Layout and overlap check

**Files:**
- Create: `frontend/e2e/layout.spec.ts`

- [ ] **Step 1:** For every route and every key user at 1440 px and 390 px, open each Select and Menu on the page, then assert: no two interactive elements' bounding boxes intersect; no element is clipped (`scrollWidth > clientWidth` on controls and table cells without an ellipsis); no horizontal page scroll; open dropdown content stays inside the viewport. Save screenshots to `docs/checkpoints/build/`.
- [ ] **Step 2:** Run; fix every failure in the components or pages. Look at every screenshot by eye and fix anything that looks off even if the check passes.
- [ ] **Step 3:** Commit `test: layout and overlap check`.

### Task 37: Full story end to end

**Files:**
- Create: `frontend/e2e/story.spec.ts`

- [ ] **Step 1:** One test runs the whole lasher story on a reset scenario: evening run, planner and shift manager settle the swap, Arjun's phone, permit signed, shift-start re-score with a missing check-in, sensor replay crosses 32 for 30 minutes and the foreman confirms, an unwell tap, Camp Block C warning through ten steps, an action and a learning card, the warning closed with an outcome, a weights proposal approved.
- [ ] **Step 2:** Run the whole suite: `uv run pytest`, `npx vitest run`, `npx playwright test`, ruff, eslint, `tsc --noEmit`. All green, no flaky retries.
- [ ] **Step 3:** Commit `test: full story end to end`.

### CHECKPOINT 2: Build complete

- [ ] Send Deva: a one-screen summary (modules done, test counts), 8 key screenshots, the login table, and `./start.sh`. Fix anything Deva flags before moving on.

---

## Phase 8: Flow

### Task 38: Demo flow and reset

**Files:**
- Create: `video/flow.md`, `video/reset_take.py`

- [ ] **Step 1:** Load `~/VOICE.md`. Write `flow.md`: the story as about 25 shots, each with who is logged in, what they do, and the one sentence that will be said. Target 5 minutes.
- [ ] **Step 2:** `reset_take.py` runs `scripts/reset.py`, sets the clock to 28 Jul 18:00, and checks the AI drafts the take needs are present.
- [ ] **Step 3:** Rehearse the flow by hand through the Playwright MCP; fix any rough edge in the product found on the way.
- [ ] **Step 4:** Commit `docs: demo flow`.

### CHECKPOINT 3: Flow ready for recording

- [ ] Send Deva `flow.md` as a short shot list with 6 to 8 screenshots of the key moments. Proceed on yes.

---

## Phase 9: Video

### Task 39: Record

**Files:**
- Create: `video/rec.mjs`, `video/kit.mjs` (copied from the skill)

- [ ] **Step 1:** Load the `generating-narrated-videos` skill; run its `setup.sh` in `video/`.
- [ ] **Step 2:** Write `rec.mjs` with one beat per shot in `flow.md`, two screens (desktop 1920 by 1080 and a phone at 390 by 844 for Arjun and Joseph), `glide/click/type` for every action.
- [ ] **Step 3:** `REHEARSE=1 node rec.mjs` until clean; then record after `reset_take.py`.

### Task 40: Build and check the video

**Files:**
- Create: `video/script.json`, `video/README.md`

- [ ] **Step 1:** Write `script.json` lines from `flow.md` in Deva's voice (short sentences, at most one dry line per minute, no em dashes).
- [ ] **Step 2:** Build with the skill's `build.py` (Azure Speech if the resource supports it, else system voice) to `video/build/DataLens-demo.mp4`.
- [ ] **Step 3:** Pull a frame every 10 seconds and look at each: cursor visible, no blank frames, each line matches the screen, audio length matches. Fix and rebuild.
- [ ] **Step 4:** Write `video/README.md` (how to make it again). Commit `feat: demo video pipeline`.

### CHECKPOINT 4: Video delivered

- [ ] Send Deva the MP4 path, its length, which voice engine was used, and anything that fell back.
