"""POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import db
from app.auth.deps import current_user
from app.auth.security import (
    COOKIE_NAME,
    SESSION_LIFETIME,
    create_session_token,
    hash_password,
    verify_password,
)
from app.errors import ApiError
from app.models import Employer, Person

router = APIRouter(prefix="/auth", tags=["auth"])

# Checked when the email is unknown, so a miss takes as long as a wrong password.
_DUMMY_HASH = hash_password("not-a-real-password")


class LoginBody(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    role: str
    employer: str
    email: str
    display_language: str


def _user_out(person: Person, session: Session) -> UserOut:
    employer = session.get(Employer, person.employer_id)
    return UserOut(
        id=person.id,
        name=f"{person.first_name} {person.last_name}",
        role=person.role.value,
        employer=employer.name if employer else "",
        email=person.email,
        display_language=person.display_language,
    )


@router.post("/login")
def login(
    body: LoginBody, response: Response, session: Annotated[Session, Depends(db.get_session)]
) -> UserOut:
    email = body.email.strip().lower()
    person = session.scalar(select(Person).where(Person.email == email))
    password_ok = verify_password(body.password, person.password_hash if person else _DUMMY_HASH)
    if person is None or not person.active or not password_ok:
        raise ApiError(
            401, "unauthorized", "Those sign-in details are not right. Please try again."
        )
    response.set_cookie(
        COOKIE_NAME,
        create_session_token(person.id),
        max_age=int(SESSION_LIFETIME.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,  # local prototype over plain http
    )
    return _user_out(person, session)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=False)


@router.get("/me")
def me(
    person: Annotated[Person, Depends(current_user)],
    session: Annotated[Session, Depends(db.get_session)],
) -> UserOut:
    return _user_out(person, session)
