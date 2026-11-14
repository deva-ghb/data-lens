"""History the system would have written before the scenario date, authored for the seed.

1. The detector is replayed day by day over the history, exactly as the live system would
   have run, and opens a warning record for the first day of each episode.
2. Past warnings are closed by the HSE head with an outcome (right, or false alarm).
3. The ten steps of each record, the incident records, the learning items and Arjun's
   reason in his own language are written here as "authored-seed" drafts, composed from
   the computed figures so every number matches what the screens compute. No call is
   made to Azure for any of it; at runtime `get_or_draft` finds these and reuses them.
4. Corrective actions, inspections and learning reads follow from the confirmed records.
"""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import load_prompt
from app.backtest.harness import run_backtest
from app.detector.detect import ZoneEvaluation, evaluate_zone
from app.detector.open_record import open_warning
from app.detector.series import clear_feed_index, feed_index
from app.models import (
    Action,
    AiDraft,
    Assignment,
    Incident,
    Inspection,
    InspectionCheck,
    LearningItem,
    LearningRead,
    Person,
    Shift,
    WarningRecord,
    WarningStep,
    Zone,
)
from app.models.actions import ActionStatus, CheckResult, ControlLevel, InspectionStatus
from app.models.ai import AiDraftStatus
from app.models.learning import LearningKind, LearningStatus
from app.models.roster import ShiftKind
from app.models.warnings import WarningLevel, WarningOutcome, WarningStatus, WarningStepStatus
from seed.scenario import CLOCK, STORY_DATE

METRIC_WORDS = {
    "heat_visits": "clinic visits for heat illness",
    "respiratory_visits": "clinic visits for breathing problems",
    "gastro_visits": "clinic visits for stomach upsets",
    "injury_visits": "clinic visits for injuries",
    "musculoskeletal_visits": "clinic visits for strains and sprains",
    "absent": "sickness absences",
    "unsafe_reports": "unsafe acts, conditions, near misses and hazard reports",
    "tired": "workers checking in tired",
    "short_sleep": "check-ins after short sleep",
    "tickets_opened": "camp fault tickets",
    "cooling_units_down": "cooling units out of service",
    "pm10": "dust in the air (PM10)",
}
LEVEL_METRICS = {"pm10", "cooling_units_down"}


def _person(session: Session, email_local: str) -> Person:
    return session.scalars(
        select(Person).where(Person.email == f"{email_local}@mirsalterminals.com")
    ).one()


def _draft(
    session: Session,
    kind: str,
    subject_kind: str,
    subject_id: int,
    content: str,
    at: datetime,
    *,
    sure: list[str],
    unsure: list[str],
    would_change: list[str],
    confidence: float,
    evidence: list[str],
    rules: list[str] | None = None,
    inferences: list[str] | None = None,
    rejected: list[str] | None = None,
    status: AiDraftStatus = AiDraftStatus.CONFIRMED,
    language: str = "en",
) -> AiDraft:
    version, _ = load_prompt(kind)
    draft = AiDraft(
        kind=kind,
        subject_kind=subject_kind,
        subject_id=subject_id,
        language=language,
        prompt_version=version,
        model="authored-seed",
        deployment="authored-seed",
        content=content,
        sure_json=sure,
        unsure_json=unsure,
        would_change_json=would_change,
        confidence=confidence,
        reasoning_json={
            "evidence": evidence,
            "rules": rules or [],
            "inferences": inferences or [],
            "rejected": rejected or [],
        },
        status=status,
        created_at=at,
    )
    session.add(draft)
    session.flush()
    return draft


def _period(c: dict[str, Any]) -> str:
    start = date.fromisoformat(c["period_start"])
    end = date.fromisoformat(c["period_end"])
    return f"{start.day} to {end.day} {end:%B}"


def detection_text(zone: str, evidence: dict[str, Any]) -> str:
    lines = []
    for c in evidence["signals"]:
        words = METRIC_WORDS.get(c["metric"], c["metric"])
        if c["metric"] in LEVEL_METRICS:
            lines.append(
                f"{words.capitalize()} in {c['zone']} averaged {c['observed']:.1f} a day over "
                f"{_period(c)}, against {c['expected']:.1f} usual: {c['ratio']:.1f} times the baseline."
            )
        else:
            lines.append(
                f"{int(c['observed'])} {words} in {c['zone']} over {_period(c)}, against "
                f"{c['expected']:.1f} expected: {c['ratio']:.1f} times the baseline."
            )
    classes = " and ".join(evidence["classes"])
    late = evidence.get("late_feeds") or []
    tail = (
        f"Two signal classes ({classes}) agree in the same place and period, so this is a "
        "warning, not a watch."
    )
    if late:
        tail += f" Late feeds: {', '.join(late)}."
    return (
        f"Something is building in {zone}.\n\n"
        + "\n".join(f"- {line}" for line in lines)
        + f"\n\n{tail}"
    )


EVENT_TEXT: dict[str, dict[int, str]] = {
    "E1_DUST_RESP": {
        2: "Exposed work: tractor and reach stacker driving in Yard Block 4. Hazard: breathing in dust on long shifts with cab windows open. The control that should hold is the dust day rule: cabs closed, air conditioning on recirculate, masks issued on the yard. Deviation: windows open because two cab coolers were broken.",
        3: "No earlier dust warning in Yard Block 4 this year. The nearest pattern is March, when a sandstorm closed the yard for a shift with no clinic visits.",
        4: "The dust (environmental) and the absences (workplace) rose together over the same three days in the same yard. The driver the organisation controls: broken cab coolers that made drivers open windows. Rejected: a stomach bug, because there was no rise in stomach upset visits.",
        5: "Likelihood 4 (signals from two classes over three days). Severity 3 (respiratory illness needing time off). Score 12, amber. Target after controls: likelihood 2, score 6.",
        6: "Check one: are cab windows closed on the yard at 14:00? Check two: are masks at the yard office and being worn? Check three: how many cab coolers are working?",
        7: "Response level: adjust the work. Engineer: repair the two cab coolers within 48 hours (owner: workshop lead). Administrative: dust day rule briefed at the gate, masks issued (owner: yard foreman). Effectiveness check: no new respiratory visits from Yard Block 4 crews in the following week.",
        8: "No permit to work covers yard driving. No permit conditions drafted.",
        9: "Card: on dust days keep the cab shut and the cooler on recirculate; if the cooler is broken, report it and take a mask. Proposed safe working practice change: add 'cab cooler working' to the pre-start walk-around.",
        10: "Closed as right. The coolers were repaired on day two; respiratory visits from the yard returned to baseline within four days. Lead time before the first lost day: about five days.",
    },
    "E2_NIGHT_FATIGUE": {
        2: "Exposed work: lashing at height on deck at Berth 3, nights. Hazard: fall from height. The control that should hold: three points of contact on the platform ladder and a buddy in sight above the second tier. Deviation: two gangs on a fourth night in a row and a loose ladder rung reported.",
        3: "The same berth saw a ladder near miss on nights last October, closed with a ladder inspection. That control did not cover the platform ladders.",
        4: "Near misses and hazard reports (workplace) rose with tired check-ins (worker reported) on the same nights at the same berth. The driver the organisation controls: the roster put two gangs on a fourth night in a row during a vessel peak. Rejected: equipment alone, because the near misses involved different ladders.",
        5: "Likelihood 4. Severity 5 (a fall from height can kill). Score 20, red. Target after controls: likelihood 2, score 10.",
        6: "Check one: ladder rungs on every lashing platform at Berth 3. Check two: buddy pairs above the second tier at 02:00. Check three: who is on a fourth night tonight?",
        7: "Response level: restrict. Eliminate: no fourth night in a row on grade 5 work in heat tier 2 or above (owner: planner). Engineer: replace loose rungs before the next night (owner: workshop lead). Administrative: buddy pairs on every platform. Effectiveness check: no near misses on Berth 3 nights for two weeks.",
        8: "Lashing permits for Berth 3 nights: condition drafted, 'no worker on a fourth consecutive night', and 'suspend if a ladder defect is reported until it is fixed'.",
        9: "Card: tired on the ladder is how falls start; if it is your fourth night, say so. Proposed safe working practice change: add the roster rule to the lashing practice.",
        10: "Closed as right. The roster rule held; no near misses on Berth 3 nights in the following two weeks.",
    },
    "E3_PLANT_STRUCK": {
        2: "Exposed work: reach stacker and tractor movements in Yard Block 2. Hazard: struck by mobile plant. The control that should hold: pedestrians stay out of the stacking lane and every blind crossing has a working mirror. Deviation: the convex mirror at row 9 broken, and drivers tired after an overtime week.",
        3: "No earlier struck-by warning in Yard Block 2. A tractor near a walking checker in Yard Block 5 in January was closed with lane markings.",
        4: "Near misses (workplace) rose with tired check-ins (worker reported) among the Yard Block 2 crews. The driver the organisation controls: overtime during a vessel surge, and a broken mirror at a blind crossing. Rejected: a single careless driver, because the near misses involved different crews.",
        5: "Likelihood 4. Severity 5. Score 20, red. Target after controls: likelihood 2, score 10.",
        6: "Check one: is the row 9 mirror replaced? Check two: are walkers using the marked path? Check three: overtime hours for Yard Gangs 2 and 8 this week.",
        7: "Response level: restrict. Engineer: replace the row 9 mirror today (owner: yard foreman). Administrative: cap overtime for Yard Gangs 2 and 8; pair drivers at changeover (owner: planner). Effectiveness check: no near misses in Yard Block 2 for two weeks.",
        8: "No permit to work covers yard driving. No permit conditions drafted.",
        9: "Card: if you cannot see round the corner, stop and sound the horn; report a broken mirror the same shift. Proposed change: add the mirror check to the yard opening round.",
        10: "Closed as right, with a lesson. A tractor driver was struck at low speed on 8 July before the overtime cap took effect on every gang. The warning came about 83 hours earlier. The model now weighs tired check-ins among drivers more strongly.",
    },
}

FALSE_ALARM_TEXT = {
    2: "No graded work activity is exposed in this place beyond normal living conditions.",
    3: "No earlier warning here with the same pattern.",
    4: "The signals moved together for a day or two, but no driver the organisation controls could be found.",
    5: "Likelihood 2. Severity 2. Score 4, green.",
    6: "Check one: did the fault get fixed the same day? Check two: did the clinic visits continue?",
    7: "Response level: inform. Watch for a second day of the same signals. No actions created.",
    8: "No permits affected.",
    9: "No learning item: nothing was found to change.",
    10: "Closed as a false alarm. The signals returned to baseline the next day. The outcome is fed back to the weights.",
}


def _confirmer(session: Session, step: int, zone_name: str) -> Person | None:
    if step in (2, 3, 10):
        return None  # linked by AI, or closed automatically
    if step == 6:
        return _person(session, "tomas.reyes" if "Yard" in zone_name else "joseph.kariuki")
    if step == 8:
        return _person(session, "priya.raman")
    return _person(session, "layla.haddad")


def _evaluation_for(
    session: Session, zones: list[str], day: date
) -> tuple[str, ZoneEvaluation] | None:
    index = feed_index(session)
    ids = {name: zid for zid, name in index.zone_name.items()}
    ordered = sorted(zones, key=lambda z: ("District" in z, z))
    for zone in ordered:
        evaluation = evaluate_zone(session, ids[zone], day)
        if evaluation.level in (WarningLevel.WARNING, WarningLevel.ALERT):
            return zone, evaluation
    return None


def replay_and_write(session: Session) -> None:
    clear_feed_index(session)
    result = run_backtest(session, action_line=1.5)
    hse = _person(session, "layla.haddad")
    for episode in result.episodes:
        found = _evaluation_for(session, episode.zones, episode.first_day)
        if found is None:
            continue
        zone_name, evaluation = found
        record = open_warning(session, evaluation)
        evidence = record.evidence_json or {}
        steps = {
            s.step: s
            for s in session.scalars(select(WarningStep).where(WarningStep.warning_id == record.id))
        }
        opened = record.opened_at
        is_open = episode.first_day >= STORY_DATE - timedelta(days=4)
        step_1 = _draft(
            session,
            "warning_step_1",
            "warning",
            record.id,
            detection_text(zone_name, evidence),
            opened,
            sure=[
                f"{len(evidence['signals'])} signals above their own baseline",
                "Two signal classes agree",
            ],
            unsure=["Whether the rise continues tomorrow"],
            would_change=["The signals returning to baseline", "A third signal class joining"],
            confidence=0.8,
            evidence=[s["feed_name"] for s in evidence["signals"]],
            rules=["Two or more classes in the same place and period make a warning"],
            status=AiDraftStatus.DRAFT if is_open else AiDraftStatus.CONFIRMED,
        )
        _attach(session, steps[1], step_1, None if is_open else hse, opened)
        if is_open:
            _open_camp_c_steps(session, record, steps, opened)
            continue
        text = EVENT_TEXT.get(episode.event or "", FALSE_ALARM_TEXT)
        for n in range(2, 11):
            confirmer = _confirmer(session, n, zone_name)
            when = opened + timedelta(hours=6 * n)
            draft = _draft(
                session,
                f"warning_step_{n}",
                "warning",
                record.id,
                text[n],
                when,
                sure=["Confirmed by the named role"] if confirmer else ["Linked from the records"],
                unsure=[],
                would_change=[],
                confidence=0.85,
                evidence=[s["feed_name"] for s in evidence["signals"]],
            )
            _attach(session, steps[n], draft, confirmer, when)
        record.status = WarningStatus.CLOSED
        record.outcome = WarningOutcome.RIGHT if episode.event else WarningOutcome.FALSE_ALARM
        record.closed_at = opened + timedelta(days=6)
        if episode.event:
            _follow_up(session, record, zone_name, episode.event, hse)
    session.flush()


def _attach(
    session: Session, step: WarningStep, draft: AiDraft, confirmer: Person | None, at: datetime
) -> None:
    step.draft_id = draft.id
    if draft.status == AiDraftStatus.DRAFT:
        step.status = WarningStepStatus.DRAFTED
        return
    step.status = WarningStepStatus.CONFIRMED
    step.confirmed_by = confirmer.id if confirmer else None
    step.confirmed_at = at


def _open_camp_c_steps(
    session: Session, record: WarningRecord, steps: dict[int, WarningStep], opened: datetime
) -> None:
    texts = {
        2: "Exposed work: everyone who sleeps in Camp Block C and works the next shift, most of all lashing at height on deck at Berth 2 on the night of 29 July. Hazards: heat illness and a fall from height after a hot, short night. The control that should hold: rooms cooled to 26 C so workers recover before the shift. Deviation: 11 of 40 cooling units out of service since 24 and 25 July.",
        3: "One earlier cooling fault in Camp Block C this summer (2 units, 9 June) was fixed within a day with no rise in clinic visits. This failure is five times larger and has lasted four days.",
    }
    for n, content in texts.items():
        draft = _draft(
            session,
            f"warning_step_{n}",
            "warning",
            record.id,
            content,
            opened + timedelta(hours=n),
            sure=["Linked from the activity register and the camp records"],
            unsure=["How many Camp Block C residents are on tomorrow's graded work"],
            would_change=["The cooling units back in service"],
            confidence=0.75,
            evidence=["Accommodation fault tickets", "Roster and shift pattern"],
            status=AiDraftStatus.DRAFT,
        )
        _attach(session, steps[n], draft, None, opened)


def _follow_up(
    session: Session, record: WarningRecord, zone_name: str, event: str, hse: Person
) -> None:
    opened = record.opened_at
    zone = session.scalars(select(Zone).where(Zone.name == zone_name)).one()
    planner = _person(session, "daniel.mensah")
    foreman = _person(session, "tomas.reyes" if "Yard" in zone_name else "joseph.kariuki")
    actions = {
        "E1_DUST_RESP": [
            ("Repair the two broken cab coolers in Yard Block 4", ControlLevel.ENGINEER, foreman),
            (
                "Brief the dust day rule at the gate and issue masks",
                ControlLevel.ADMINISTRATIVE,
                foreman,
            ),
        ],
        "E2_NIGHT_FATIGUE": [
            (
                "No fourth night in a row on grade 5 work in heat tier 2 or above",
                ControlLevel.ELIMINATE,
                planner,
            ),
            (
                "Replace loose rungs on the Berth 3 lashing platforms",
                ControlLevel.ENGINEER,
                foreman,
            ),
            (
                "Buddy pairs on every platform above the second tier",
                ControlLevel.ADMINISTRATIVE,
                foreman,
            ),
        ],
        "E3_PLANT_STRUCK": [
            ("Replace the convex mirror at the row 9 crossing", ControlLevel.ENGINEER, foreman),
            (
                "Cap overtime for Yard Gangs 2 and 8; pair drivers at changeover",
                ControlLevel.ADMINISTRATIVE,
                planner,
            ),
        ],
    }[event]
    for i, (title, level, owner) in enumerate(actions):
        session.add(
            Action(
                source_kind="warning",
                source_id=record.id,
                title=title,
                control_level=level,
                owner_id=owner.id,
                due_on=(opened + timedelta(days=2 + i)).date(),
                status=ActionStatus.DONE,
                effectiveness_check_on=(opened + timedelta(days=14)).date(),
                effective=True,
            )
        )
    inspection = Inspection(
        source_kind="warning",
        source_id=record.id,
        zone_id=zone.id,
        due_at=opened + timedelta(hours=20),
        status=InspectionStatus.DONE,
    )
    session.add(inspection)
    session.flush()
    for line in EVENT_TEXT[event][6].split("Check ")[1:]:
        question = line.split(":", 1)[1].strip()
        session.add(
            InspectionCheck(
                inspection_id=inspection.id,
                driver=line.split(":", 1)[0].strip(),
                question=question,
                result=CheckResult.CONFIRMED,
                note="Seen on the ground and photographed.",
            )
        )
    lesson = EVENT_TEXT[event][9]
    for kind, content in (
        (LearningKind.CARD, lesson.split("Proposed")[0].replace("Card: ", "").strip()),
        (
            LearningKind.TOOLBOX_TALK,
            f"What happened: {EVENT_TEXT[event][4]} What we changed: {EVENT_TEXT[event][7]}",
        ),
        (LearningKind.SWP_CHANGE, "Proposed" + lesson.split("Proposed", 1)[1]),
    ):
        draft_kind = {
            "card": "learning_card",
            "toolbox_talk": "toolbox_talk",
            "swp_change": "swp_change",
        }[kind.value]
        item = LearningItem(
            kind=kind, source_kind="warning", source_id=record.id, status=LearningStatus.PUBLISHED
        )
        session.add(item)
        session.flush()
        draft = _draft(
            session,
            draft_kind,
            "learning",
            item.id,
            content,
            opened + timedelta(days=4),
            sure=["Written from confirmed sections only"],
            unsure=[],
            would_change=[],
            confidence=0.9,
            evidence=[f"Warning record {record.id}"],
        )
        item.draft_id = draft.id
        readers = session.scalars(
            select(Assignment.person_id)
            .join(Shift, Shift.id == Assignment.shift_id)
            .where(Assignment.zone_id == zone.id, Shift.date >= (opened + timedelta(days=4)).date())
            .distinct()
            .limit(60)
        ).all()
        for n, pid in enumerate(readers):
            if n % 3 == 2:
                continue  # not everyone reads every card
            session.add(
                LearningRead(
                    item_id=item.id, person_id=pid, at=opened + timedelta(days=5, hours=n % 12)
                )
            )
    assert hse


def incident_records(session: Session) -> None:
    for incident in session.scalars(select(Incident)):
        content = (
            f"{incident.text}\n\nClassified by potential: {incident.potential_severity} of 5 "
            f"(actual {incident.actual_severity}). Safety chain: the activity, the hazard of "
            "contact with plant or load, the control that should have held, the unsafe act or "
            "condition, and the outcome. Five whys stop at a control the site owns."
        )
        _draft(
            session,
            "incident_record",
            "incident",
            incident.id,
            content,
            incident.at + timedelta(hours=2),
            sure=["Reported the same shift"],
            unsure=[],
            would_change=[],
            confidence=0.85,
            evidence=["Incident report"],
        )


ARJUN_REASON = {
    "en": (
        "Arjun, tonight would be your third night in a row, two of your last ten check-ins "
        "came after short sleep, and the cooling in your camp block is down. Lashing at height "
        "asks a lot of a tired body in this heat, so we are proposing ground twist-lock handling "
        "for tonight instead, with your own crew. This is not recorded against you. If you "
        "think it is wrong, tap Contest and say why."
    ),
    "ne": (
        "अर्जुन, आज राति तपाईंको लगातार तेस्रो रात हो, पछिल्ला दस चेक-इनमध्ये दुईमा निद्रा कम थियो, "
        "र तपाईंको क्याम्प ब्लकमा कुलिङ बिग्रिएको छ। यो गर्मीमा थाकेको शरीरले उचाइमा ल्यासिङ गर्नु "
        "जोखिमपूर्ण हुन्छ, त्यसैले आज राति तपाईंलाई आफ्नै टोलीसँग जमिनमा ट्विस्ट-लक काम दिने प्रस्ताव "
        "गरिएको छ। यो तपाईंको विरुद्धमा रेकर्ड हुँदैन। यदि तपाईंलाई यो गलत लाग्छ भने Contest थिच्नुहोस् "
        "र कारण लेख्नुहोस्।"
    ),
}


def arjun_reason(session: Session) -> None:
    arjun = _person(session, "arjun.thapa")
    assignment = session.scalars(
        select(Assignment)
        .join(Shift, Shift.id == Assignment.shift_id)
        .where(
            Assignment.person_id == arjun.id,
            Shift.date == STORY_DATE,
            Shift.kind == ShiftKind.NIGHT,
        )
    ).one()
    for language, text in ARJUN_REASON.items():
        _draft(
            session,
            "reason_translation",
            "assignment",
            assignment.id,
            text,
            CLOCK,
            sure=[
                "Third night in a row",
                "Short sleep in 2 of the last 10 check-ins",
                "Camp cooling down",
            ],
            unsure=["How you feel at check-in tonight"],
            would_change=["A good night's sleep in a cool room", "Your check-in at shift start"],
            confidence=0.8,
            evidence=["Roster", "Check-ins", "Camp operator tickets"],
            status=AiDraftStatus.DRAFT,
            language=language,
        )


def write_history(session: Session) -> None:
    replay_and_write(session)
    incident_records(session)
    arjun_reason(session)
