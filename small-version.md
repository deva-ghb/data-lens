# Data Lens: end to end flow

Short version of large-version.txt.
We follow one lasher through one night shift and watch every step fire.
All people and figures are synthetic.
Multipliers in the walkthrough are illustrative.

## The idea

An incident happens when an activity's intrinsic risk meets an unsafe act, behaviour or condition (UABC).
The signals that say how likely that meeting is tomorrow already exist.
They sit in different systems: HSE platform, HR roster and training, clinic, weather, the worker's phone.
Nobody joins them before the shift.
Data Lens joins them and turns the result into a decision the planner, permit issuer and foreman can act on before work starts.

Today the safety system is thorough about what already happened and silent about what is about to.
Three gaps cause that:

- Assignment is blind. The planner does not know five of twelve lashers are on a third night, or that a camp block lost its cooling.
- The permit assumes the crew is fit. It checks the task, equipment and weather. Readiness is nobody's field.
- Every warning sign is reviewed after the fact, by different teams, monthly or quarterly.

## Setup (once per site)

- Activity register: every activity with hazards, severity, exposure hours, grade 1 to 5 and its safe working practice (SWP) items.
- Behavioural groups: people with the same training path and exposure, 20 or more per group, each with an unsafe-act rate against the site average.
- Sensitivity matrix: for each hazard, how much each readiness deficit (fatigue, heat, physical, acute state, behaviour, competency) raises it. High, medium, low. Set in a two-hour workshop with a port safety head and the clinical lead.
- Feeds: nine, in five classes (clinical, workplace, environmental, community, worker reported).

## The walkthrough

The activity: lashing at height on deck. Grade 5, 1,440 worker-hours a week, 14 SWP items.
The worker: a new arrival on contractor induction only, on a third night in a row, height refresher not done.

### 1. Evening before: the engine scores tomorrow's roster

The engine takes four layers and multiplies them.
R is relative risk against a crew with no shortfalls on the same activity.

| Layer | What it holds | Value for our lasher |
|---|---|---|
| Intrinsic | The activity: grade, hazards, exposure. Sets the scale and the tier thresholds. | Grade 5 |
| Control | How well controls held, from the UABC record. Activity rate vs site average. | 1.15 (11 unsafe acts, 6 behaviours, 7 conditions, 3 near misses in 12 months, all on nights) |
| Condition | Tomorrow's shift: heat, dust, night, pace, camp the night before. | 1.25 (WBGT 34 at 12:00, 11 of 40 cooling units failed in Camp Block C) |
| Profile | The person: health, behavioural group, work pattern. | 1.35 (third night, short sleep in 2 of 10 check-ins, contractor group at 1.6 capped) |

R = 1.15 x 1.25 x 1.35 = about 1.94.

Rules that keep this honest:

- Every multiplier is capped. The group factor caps at 1.6 and moves a tier by at most one step.
- Thresholds depend on grade. Grade 5 hits "fit with controls" at 1.3 and "reassign today" at 1.9. Grades 1 and 2 are not scored per person.
- Published relative risks seed the weights: 1.17 on heatwave days, 1.36 on a fourth night. The back-test then moves them.

### 2. The tier

R of 1.94 is over 1.9, so the lasher lands in **Reassign today**.

| Tier | Meaning | Control | Who decides |
|---|---|---|---|
| Fit | Within the activity's demands | None, logged | Automatic |
| Fit with controls | One or two dimensions below the line | Shorter exposure, extra work-rest cycle, buddy, cooler hours | Planner, foreman confirms |
| Reassign today | A hazard this worker is sensitive to is active | Swap to lower-hazard work in the same competency | Planner, shift manager approves |
| Refer | A health signal needs a clinician first | Occupational health screening, worker told first | Clinician |

A tier lasts one shift, is never exported, and is never used for hiring, discipline, pay or contract decisions.

### 3. Planner and worker

- The planner sees the tier, a work-term reason and the control. Never a diagnosis.
- The engine proposes a swap: ground twist-lock handling instead of lashing on deck.
- Alert budget: at most three reassignment recommendations per shift per planner, two prompts per foreman. The rest goes into the shift brief.
- Crew rules also apply: no more than a quarter of a crew on extra controls in heat tier 2 or above, arrivals under seven days capped at two per gang, one experienced worker on every high-hazard task.
- The planner accepts or declines with a logged reason. The shift manager approves.
- The lasher sees their own tier and the reason, in their own language, and can contest it.

### 4. The permit

The lashing permit keeps its normal lifecycle: requested, assessed, issued, live, suspended, closed.
Data Lens adds a people-and-conditions block:

- Crew readiness as counts (fit, fit with controls, reassign, refer). No names.
- Crew status: green, amber, red. Red blocks issue until the planner settles open reassignments.
- Top drivers with source and freshness, the forecast for the window, and confidence (how many checked in).

If an early warning touches this permit, its controls arrive as drafts: an earlier window, work-rest cycles, buddy pairs, a suspend condition such as "suspend if deck WBGT stays over 32 for 30 minutes".
The issuer can edit them and signs.
The link to the permit system is one JSON record per permit. Mocked in the POC.

### 5. Shift start: re-score on live data

The engine runs again on the check-ins.
Each worker does three taps.
A worker who has not checked in is unknown, not fit.
If a feed is late, the warning names it. Nothing is filled in silently.

### 6. During the shift: the permit stays live

- On-site WBGT crosses the limit. The work-rest cycle changes. The foreman confirms on their phone. The permit log records it.
- A worker taps "I feel unwell". They go to the cool room, the clinician is notified, the permit shows the event without a name.

### 7. Meanwhile: a pattern forms across the camp

Clinic heat visits from Camp Block C are double the usual.
Camp fault tickets show 11 of 40 cooling units down.
Those are two different signal classes (clinical and community) agreeing on the same place and period.
That is the trigger.
With fewer than two classes live, nothing above Watch is raised.

The system opens an **early warning record**, before anyone is hurt.

### 8. The early warning record (10 steps)

The copilot drafts each section. A named role confirms it.

1. Detection: which signals moved, vs baseline. HSE head confirms.
2. Activity and controls: the SWP control that should hold and what deviates. Linked by AI.
3. History: earlier warnings at the same place and how they closed. Linked by AI.
4. Drivers: contribution by signal, location and time. Stops at something the organisation controls. HSE head confirms.
5. Risk assessment: likelihood x severity on the site 5 by 5 matrix. HSE head confirms.
6. Verify on the ground: an inspection with one check per driver. Results raise confidence or record a false alarm.
7. Controls (CAPA): inform, adjust, restrict or escalate. Each action has an owner, due date and effectiveness check. HSE head creates.
8. Permits affected: conditions drafted into every touched permit. Issuer signs each.
9. Learning: a one-minute card, a toolbox talk, a proposed SWP change. HSE head shares.
10. Close: outcome recorded either way. This is how lead time, sensitivity and false alarms get measured.

### 9. If something does happen: the incident record

Same workflow, opened after the event.
Reported from a phone in under a minute, with a photo, voice note or a few words.
The copilot drafts the record, classifies by potential not outcome, traces the safety chain (activity, hazard, control that should have held, unsafe act, unsafe condition, outcome), proposes five whys, scores risk, builds an inspection, ranks actions.
A person confirms each step.
This part already exists in the GYTWorkz Safety Copilot demo.

### 10. Closing the loop

Every closed record feeds four things:

- Control risk: each confirmed incident, near miss, hazard report and observation card updates the activity's UABC history and its control multiplier.
- Behavioural groups: rates recompute weekly. A refresher or 90 clean cards moves a person to another group.
- Weights: closed outcomes propose changes to the sensitivity cells and thresholds. A person approves. Nothing moves silently.
- SWP: lessons propose new line items, for example a night-time cooling check before any heat tier 2 day.

Test of a closed loop: tomorrow's prediction is better than today's.

## What the behavioural group does here

Our lasher's group runs 1.6 times the site unsafe-act rate.
The record shows the contractor induction skips the terminal's lashing sequence.
The copilot does not warn about the people.
It proposes a site height refresher, a cap of two per gang, and a change to the induction.
Origin, nationality, religion, ethnicity and language are never inputs.

## Who sees what

- Worker: own tier, reason and health record.
- Foreman: actions for the crew. No answers, no results.
- Planner: tier, work-term reason, control.
- Permit issuer: counts only.
- HSE head: aggregates and every record.
- Clinician: health detail. Decides fit, fit with restrictions or not today.
- Public health and labour inspector: district aggregates of 10 or more.

The employer never sees medical data, only the fitness outcome.
Any group under 10 is hidden everywhere, and totals are rounded so it cannot be recovered by subtraction.
AI drafts. People decide: reassigning, signing a permit and restricting on health grounds are locked to people.

## Does it work

Back-test on 90 synthetic days, 400 workers, four injected events:

- Lead time: 72 hours or more on all four.
- Sensitivity: 4 of 4.
- PPV: 66%. About 1 in 3 warnings is a false alarm.
- Unsafe acts on grade 4 and 5 work fall by about a third.

Synthetic data and expert-set weights. This shows the method runs end to end, not the hit rate of a real site.
The pilot measures the same things on real records.
