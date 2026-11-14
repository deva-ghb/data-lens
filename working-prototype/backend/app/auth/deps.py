"""Dependencies every protected route uses: who is signed in, and which roles may enter."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app import db
from app.auth.security import COOKIE_NAME, read_session_token
from app.errors import ApiError
from app.models import Person, Role


def _not_signed_in() -> ApiError:
    return ApiError(401, "unauthorized", "Please sign in to continue.")


def current_user(request: Request, session: Annotated[Session, Depends(db.get_session)]) -> Person:
    """The signed-in, active person, or a 401 when the cookie is missing, invalid or expired."""
    token = request.cookies.get(COOKIE_NAME)
    person_id = read_session_token(token) if token else None
    person = session.get(Person, person_id) if person_id is not None else None
    if person is None or not person.active:
        raise _not_signed_in()
    return person


def require_roles(*roles: Role) -> Callable[[Person], Person]:
    """A dependency that lets only the listed roles through; anyone else gets a 403."""
    allowed = frozenset(roles)

    def guard(user: Annotated[Person, Depends(current_user)]) -> Person:
        if user.role not in allowed:
            raise ApiError(403, "forbidden", "You do not have access to this.")
        return user

    return guard
