"""The permit-to-work lifecycle a site already runs: requested, assessed, issued, live,
suspended, closed. Every move is checked here, logged on the permit and audited."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.audit import audit
from app.clock import site_now
from app.models import Permit, PermitEvent, Person
from app.models.permits import PermitStatus as S

MOVES: dict[str, tuple[tuple[S, ...], S]] = {
    "assess": ((S.REQUESTED,), S.ASSESSED),
    "send-back": ((S.ASSESSED,), S.REQUESTED),
    "sign": ((S.ASSESSED,), S.ISSUED),
    "start": ((S.ISSUED,), S.LIVE),
    "suspend": ((S.LIVE,), S.SUSPENDED),
    "resume": ((S.SUSPENDED,), S.LIVE),
    "close": ((S.ISSUED, S.LIVE, S.SUSPENDED), S.CLOSED),
    "hold": ((S.ISSUED, S.LIVE), S.SUSPENDED),
}
WORDS = {
    "assess": "Assessed",
    "send-back": "Sent back to the requester",
    "sign": "Signed and issued",
    "start": "Work started",
    "suspend": "Suspended",
    "resume": "Resumed",
    "close": "Closed",
    "hold": "Held by the issuer",
}


class InvalidMove(Exception):
    pass


def transition(
    session: Session, permit: Permit, move: str, actor: Person, note: str | None = None
) -> Permit:
    if move not in MOVES:
        raise InvalidMove(f"Unknown action {move}.")
    allowed, target = MOVES[move]
    if permit.status not in allowed:
        raise InvalidMove(f"A {permit.status.value} permit cannot be {WORDS[move].lower()}.")
    permit.status = target
    if move == "sign":
        permit.issuer_id = actor.id
    now: datetime = site_now(session)
    text = WORDS[move] + (f": {note}" if note else ".")
    session.add(PermitEvent(permit_id=permit.id, at=now, kind=move, text=text, actor_id=actor.id))
    audit(
        session,
        actor,
        f"permit_{move.replace('-', '_')}",
        "permit",
        permit.number,
        evidence={"note": note},
    )
    session.flush()
    return permit
