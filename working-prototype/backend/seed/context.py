"""Shared state while the generator runs: the random source, lookups and pending rows.

Rows are collected as plain dicts per model and written in bulk at the end, so the
injected events can adjust them before anything reaches the database.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
from sqlalchemy import insert
from sqlalchemy.orm import Session

from seed.workforce import CrewDef, WorkerSpec


@dataclass
class Ctx:
    session: Session
    rng: np.random.Generator
    zone_id: dict[str, int] = field(default_factory=dict)
    activity_id: dict[str, int] = field(default_factory=dict)
    activity_grade: dict[str, int] = field(default_factory=dict)
    employer_id: dict[str, int] = field(default_factory=dict)
    competency_id: dict[str, int] = field(default_factory=dict)
    feed_id: dict[str, int] = field(default_factory=dict)
    clinic_id: int = 0
    crews: list[CrewDef] = field(default_factory=list)
    crew_by_name: dict[str, CrewDef] = field(default_factory=dict)
    gang_id: dict[str, int] = field(default_factory=dict)
    workers: list[WorkerSpec] = field(default_factory=list)
    person_id: dict[int, int] = field(default_factory=dict)  # index in workers -> person id
    key_person: dict[str, int] = field(default_factory=dict)  # email local part -> person id
    shift_id: dict[tuple[date, str], int] = field(default_factory=dict)
    # person id -> list of (date, shift kind, zone name, activity code)
    worked: dict[int, list[tuple[date, str, str, str]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    rows: dict[type, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))

    def add(self, model: type, **values: Any) -> None:
        self.rows[model].append(values)

    def flush_rows(self, *models: type) -> None:
        for model in models:
            pending = self.rows.pop(model, [])
            for start in range(0, len(pending), 5000):
                self.session.execute(insert(model), pending[start : start + 5000])
        self.session.flush()

    def pick(self, items: list[Any]) -> Any:
        return items[int(self.rng.integers(0, len(items)))]

    def worker_ids(self, predicate: Any) -> list[int]:
        return [self.person_id[i] for i, w in enumerate(self.workers) if predicate(w)]
