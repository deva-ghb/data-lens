"""Who may see what. The API checks every read against this table.

Follows design sections 5.2 and 5.14 and concept doc sections 9.2 and 10:
- the worker sees their own profile and health record;
- the foreman sees actions for the crew, never answers or results;
- the planner and shift manager see tiers, work-term reasons and controls, never a diagnosis;
- the permit issuer sees counts only;
- the HSE head sees aggregates and every record, but not health detail;
- the clinician sees health detail;
- the Authority sees district and employer aggregates of 10 or more and a redacted audit trail;
- the admin onboards people and runs the site clock.
"""

from typing import Literal

from app.models import Role

DataScope = Literal[
    "own_profile",
    "own_health",
    "crew_actions",
    "site_tiers",
    "permit_counts",
    "aggregates",
    "all_records",
    "health_detail",
    "district_aggregates",
    "employer_aggregates",
    "audit_redacted",
    "admin",
]

ACCESS: dict[Role, frozenset[DataScope]] = {
    Role.WORKER: frozenset({"own_profile", "own_health"}),
    Role.FOREMAN: frozenset({"own_profile", "crew_actions"}),
    Role.PLANNER: frozenset({"own_profile", "site_tiers", "permit_counts"}),
    Role.SHIFT_MANAGER: frozenset({"own_profile", "site_tiers", "permit_counts"}),
    Role.PERMIT_ISSUER: frozenset({"own_profile", "permit_counts"}),
    Role.HSE_HEAD: frozenset(
        {"own_profile", "aggregates", "all_records", "site_tiers", "permit_counts", "crew_actions"}
    ),
    Role.CLINICIAN: frozenset({"own_profile", "health_detail", "aggregates"}),
    Role.AUTHORITY: frozenset(
        {"own_profile", "district_aggregates", "employer_aggregates", "audit_redacted"}
    ),
    Role.ADMIN: frozenset({"own_profile", "admin"}),
}


def can(role: Role, scope: DataScope) -> bool:
    return scope in ACCESS.get(role, frozenset())
