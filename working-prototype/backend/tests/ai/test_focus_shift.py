"""Before any run, the app plans for the shift the evening run will score."""

from datetime import date

from sqlalchemy.orm import Session

from app.ai.context import focus_shift
from app.models.roster import ShiftKind


def test_focus_shift_before_any_run_is_tomorrow_night(scenario: Session) -> None:
    shift = focus_shift(scenario)
    assert shift is not None
    assert (shift.date, shift.kind) == (date(2026, 7, 29), ShiftKind.NIGHT)
