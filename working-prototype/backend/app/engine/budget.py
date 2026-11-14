"""The alert budget: at most three reassignment recommendations per shift per planner
and two prompts per foreman. The rest rolls into the shift brief, so the system does
not cry wolf."""

from typing import Any

PLANNER_LIMIT = 3
FOREMAN_LIMIT = 2


def apply_budget(
    items: list[dict[str, Any]], limit: int = PLANNER_LIMIT
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Highest relative risk first; the first `limit` are shown, the rest go to the brief."""
    ranked = sorted(items, key=lambda item: item["r"], reverse=True)
    return ranked[:limit], ranked[limit:]
