"""Password hashing (argon2) and session tokens (signed JWT)."""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

COOKIE_NAME = "dl_session"
SESSION_LIFETIME = timedelta(hours=12)
_ALGORITHM = "HS256"

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """True only when the password matches. A malformed hash is a plain mismatch."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_session_token(person_id: int) -> str:
    expires = datetime.now(UTC) + SESSION_LIFETIME
    return jwt.encode({"sub": str(person_id), "exp": expires}, settings.jwt_secret, _ALGORITHM)


def read_session_token(token: str) -> int | None:
    """The person id in a valid, unexpired token, otherwise None."""
    try:
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]}
        )
        return int(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
