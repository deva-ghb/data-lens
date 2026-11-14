from sqlalchemy.orm import Session

from app.engine.weights import ensure_weights_v0, load_weights
from seed.catalog import ACTIVITIES, EMPLOYERS, GROUPS, HAZARDS, KEY_USERS, ZONES, classify_group


def test_thirteen_activities_with_grades_as_listed() -> None:
    grades = {a.code: a.grade for a in ACTIVITIES}
    assert grades == {
        "LASH_DECK": 5,
        "QC_OPS": 5,
        "MOORING": 5,
        "HOLD_CONFINED": 5,
        "HOT_WORK": 4,
        "REACH_STACKER": 4,
        "TT_DRIVING": 4,
        "TWIST_GROUND": 3,
        "REEFER": 3,
        "WORKSHOP_MECH": 3,
        "CONTAINER_INSPECT": 2,
        "YARD_HOUSEKEEPING": 2,
        "GATE_CLERK": 1,
    }
    lash = next(a for a in ACTIVITIES if a.code == "LASH_DECK")
    assert lash.name == "Lashing at height on deck"
    assert lash.exposure_hours_week == 1440
    assert len(lash.swp_items) == 14
    assert lash.lower_hazard_alternative == "TWIST_GROUND"
    hazard_codes = {h.code for h in HAZARDS}
    for activity in ACTIVITIES:
        assert set(activity.hazards) <= hazard_codes


def test_sensitivity_matrix_matches_spec_rows(session: Session) -> None:
    ensure_weights_v0(session)
    weights = load_weights(session)
    dims = ["fatigue", "heat_strain", "physical", "acute", "safety_behaviour", "competency"]
    expected = {
        "FALL_HEIGHT": "HHMHHH",
        "STRUCK_PLANT": "HMLMHM",
        "DROPPED_LOAD": "MMLLHH",
        "HEAT_ILLNESS": "HHMHLL",
        "MANUAL_HANDLING": "MMHMML",
        "HOT_WORK_CONFINED": "HHMHHH",
    }
    assert set(weights.sens) == set(expected)
    for hazard, letters in expected.items():
        assert [weights.sens[hazard][d] for d in dims] == list(letters)


def test_weights_v0_constants_match_plan(session: Session) -> None:
    ensure_weights_v0(session)
    w = load_weights(session)
    assert w.version == "v0"
    assert w.sens_value == {"H": 0.35, "M": 0.20, "L": 0.08}
    assert w.thresholds[5] == (1.3, 1.9)
    assert w.thresholds[4] == (1.4, 2.1)
    assert w.thresholds[3] == (1.5, 2.4)
    assert 1 not in w.thresholds and 2 not in w.thresholds
    assert w.fatigue_by_night == {1: 1.0, 2: 1.05, 3: 1.12, 4: 1.36}
    assert w.heat_by_tier == {0: 1.0, 1: 1.08, 2: 1.17, 3: 1.17}
    assert w.control_formula_k == 0.5
    assert w.group_cap == 1.6


def test_ensure_weights_v0_is_idempotent(session: Session) -> None:
    first = ensure_weights_v0(session)
    second = ensure_weights_v0(session)
    assert first.id == second.id


def test_key_users_and_reference_data() -> None:
    emails = {u.email for u in KEY_USERS}
    assert "arjun.thapa@mirsalterminals.com" in emails
    roles = {u.role for u in KEY_USERS}
    assert roles == {
        "admin",
        "hse_head",
        "planner",
        "shift_manager",
        "permit_issuer",
        "foreman",
        "clinician",
        "authority",
        "worker",
    }
    assert [e.name for e in EMPLOYERS] == [
        "Mirsal Terminals",
        "Sahel Marine Services",
        "Bayan Manpower Contracting",
    ]
    assert {z.name for z in ZONES} >= {"Camp Block C", "Berth 2", "Yard Block 4"}
    assert len(GROUPS) == 6


def test_group_classification_follows_training_tenure_and_roster() -> None:
    new_arrival = {
        "tenure_months": 4,
        "induction": "contractor",
        "competencies": {"LASHING"},
        "courses": {},
        "nights_in_row_max_14d": 3,
        "months_since": {},
    }
    assert classify_group(new_arrival) == "NEW_CONTRACTOR"
    veteran = {
        "tenure_months": 30,
        "induction": "site",
        "competencies": {"LASHING"},
        "courses": {"HEIGHT_REFRESHER"},
        "nights_in_row_max_14d": 2,
        "months_since": {"HEIGHT_REFRESHER": 5},
    }
    assert classify_group(veteran) == "EXP_INHOUSE"
    assert classify_group({**veteran, "nights_in_row_max_14d": 4}) == "EXP_NIGHTS"
    driver = {
        "tenure_months": 20,
        "induction": "site",
        "competencies": {"TT_DRIVER"},
        "courses": {"DRIVING_REFRESHER"},
        "nights_in_row_max_14d": 1,
        "months_since": {"DRIVING_REFRESHER": 20},
    }
    assert classify_group(driver) == "YARD_OVERDUE"
    assert classify_group({**driver, "months_since": {"DRIVING_REFRESHER": 3}}) == (
        "YARD_REFRESHED"
    )
    assert classify_group({**driver, "competencies": {"MOORING"}}) == "MOORING_ALL"
    assert classify_group({**driver, "competencies": {"GATE"}}) is None
