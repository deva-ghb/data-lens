"""Small-cell suppression: any group below the threshold is hidden in every view.

Totals are always rounded to the nearest 5, so a hidden cell cannot be recovered
by subtracting the visible cells from the total.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Setting

DEFAULT_THRESHOLD = 10
THRESHOLD_KEY = "small_cell_threshold"


@dataclass(frozen=True)
class Cell:
    label: str
    value: int


@dataclass(frozen=True)
class ShownCell:
    label: str
    value: int | None  # None means hidden because the group is too small


@dataclass(frozen=True)
class SuppressedTable:
    cells: list[ShownCell]
    total: int
    suppressed_count: int
    threshold: int


def round_to_5(n: int) -> int:
    # Half-up rounding on whole numbers, so the result never depends on banker's rounding.
    return 5 * ((n + 2) // 5)


def small_cell_threshold(session: Session) -> int:
    setting = session.get(Setting, THRESHOLD_KEY)
    return int(setting.value) if setting is not None else DEFAULT_THRESHOLD


def suppress(cells: list[Cell], k: int) -> SuppressedTable:
    shown = [ShownCell(c.label, c.value if c.value >= k else None) for c in cells]
    return SuppressedTable(
        cells=shown,
        total=round_to_5(sum(c.value for c in cells)),
        suppressed_count=sum(1 for c in shown if c.value is None),
        threshold=k,
    )
