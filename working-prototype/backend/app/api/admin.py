"""Administration: the site clock (people and reset follow in the admin task)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.common import LOCAL, SessionDep, require_scope
from app.clock import set_site_now, site_now
from app.models import Person

router = APIRouter(prefix="/admin", tags=["admin"])


class ClockBody(BaseModel):
    now: datetime


@router.put("/clock")
def move_clock(
    body: ClockBody, session: SessionDep, user: Person = Depends(require_scope("admin"))
) -> dict[str, Any]:
    set_site_now(session, body.now.replace(tzinfo=None), user)
    session.commit()
    now = site_now(session)
    return {"site_now": now.isoformat(), "site_now_local": (now + LOCAL).isoformat()}


# --- people -------------------------------------------------------------------------------

from datetime import date  # noqa: E402

from sqlalchemy import or_, select  # noqa: E402

from app.api.common import not_found  # noqa: E402
from app.audit import audit  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.errors import ApiError  # noqa: E402
from app.models import Employer, Role, Zone  # noqa: E402

WELCOME = "welcome@123"
DOMAIN = "mirsalterminals.com"


def _person_out(session, p: Person) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    employer = session.get(Employer, p.employer_id)
    camp = session.get(Zone, p.camp_zone_id) if p.camp_zone_id else None
    return {
        "id": p.id,
        "name": f"{p.first_name} {p.last_name}",
        "email": p.email,
        "role": p.role.value,
        "employer": employer.name if employer else None,
        "job_title": p.job_title,
        "camp": camp.name if camp else None,
        "display_language": p.display_language,
        "active": p.active,
        "site_arrival_date": p.site_arrival_date.isoformat(),
    }


@router.get("/people")
def people(
    session: SessionDep,
    q: str = "",
    role: str | None = None,
    page: int = 1,
    user: Person = Depends(require_scope("admin")),
) -> dict[str, Any]:
    query = select(Person).order_by(Person.role, Person.last_name, Person.first_name)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                Person.email.like(like), Person.first_name.ilike(like), Person.last_name.ilike(like)
            )
        )
    if role:
        query = query.where(Person.role == Role(role))
    rows = session.scalars(query).all()
    size = 25
    return {
        "total": len(rows),
        "page": page,
        "page_size": size,
        "people": [_person_out(session, p) for p in rows[(page - 1) * size : page * size]],
    }


class PersonBody(BaseModel):
    first_name: str
    last_name: str
    role: str
    employer: str
    job_title: str
    camp: str | None = None
    display_language: str = "en"


@router.post("/people", status_code=201)
def onboard(
    body: PersonBody, session: SessionDep, user: Person = Depends(require_scope("admin"))
) -> dict[str, Any]:
    first, last = body.first_name.strip(), body.last_name.strip()
    if not first or not last or not body.job_title.strip():
        raise ApiError(422, "invalid_input", "First name, last name and job title are needed.")
    try:
        role = Role(body.role)
    except ValueError:
        raise ApiError(422, "invalid_input", "Choose a role.") from None
    employer = session.scalars(select(Employer).where(Employer.name == body.employer)).first()
    if employer is None:
        raise not_found("employer")
    local = f"{first}.{last}".lower().replace(" ", "").replace("'", "")
    email = f"{local}@{DOMAIN}"
    if session.scalars(select(Person.id).where(Person.email == email)).first():
        raise ApiError(409, "conflict", f"{email} is already in use.")
    camp = (
        session.scalars(select(Zone).where(Zone.name == body.camp)).first() if body.camp else None
    )
    today = site_now(session).date()
    p = Person(
        employer_id=employer.id,
        first_name=first,
        last_name=last,
        email=email,
        role=role,
        job_title=body.job_title.strip(),
        hire_date=today,
        site_arrival_date=today,
        induction="site" if employer.kind.value == "in_house" else "contractor",
        camp_zone_id=camp.id if camp else None,
        display_language=body.display_language,
        password_hash=hash_password(WELCOME),
    )
    session.add(p)
    session.flush()
    audit(session, user, "person_onboarded", "person", str(p.id), evidence={"role": role.value})
    session.commit()
    return _person_out(session, p)


class PersonPatch(BaseModel):
    role: str | None = None
    active: bool | None = None
    job_title: str | None = None


@router.patch("/people/{person_id}")
def update_person(
    person_id: int,
    body: PersonPatch,
    session: SessionDep,
    user: Person = Depends(require_scope("admin")),
) -> dict[str, Any]:
    p = session.get(Person, person_id)
    if p is None:
        raise not_found("person")
    if body.role:
        p.role = Role(body.role)
    if body.active is not None:
        if p.id == user.id and not body.active:
            raise ApiError(409, "conflict", "You cannot switch off your own account.")
        p.active = body.active
    if body.job_title:
        p.job_title = body.job_title.strip()
    audit(
        session,
        user,
        "person_updated",
        "person",
        str(p.id),
        evidence=body.model_dump(exclude_none=True),
    )
    session.commit()
    return _person_out(session, p)


__all__ = ["router", "date"]
