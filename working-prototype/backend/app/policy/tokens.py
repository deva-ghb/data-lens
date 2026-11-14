"""Per-shift tokens that stand in for a worker in the audit log.

A reassignment is not recorded against the worker. The audit entry carries a token
that only someone who knows the person and the shift can recompute.
"""

import hashlib
import hmac

from app.config import settings


def shift_token(person_id: int, shift_id: int) -> str:
    digest = hmac.new(
        settings.jwt_secret.encode(), f"{person_id}:{shift_id}".encode(), hashlib.sha256
    ).hexdigest()
    return f"st-{digest[:24]}"
