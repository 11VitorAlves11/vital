"""Password hashing and the signed session cookie.

The session is stateless: a signed token carrying the user id and an issue time,
verified on every request. No session table, no session store — one fewer service
to run at home, at the cost of not being able to revoke a single session early.
"""

import uuid

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings

# bcrypt silently ignores everything past 72 bytes, so an over-long password would
# otherwise be a shorter password in disguise.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 10

_SESSION_SALT = "vital.session"


class PasswordTooLongError(ValueError):
    """Raised when a password exceeds what bcrypt can actually hash."""


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(f"password exceeds {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_SESSION_SALT)


def issue_session(user_id: uuid.UUID) -> str:
    return _serializer().dumps(str(user_id))


def read_session(token: str) -> uuid.UUID | None:
    """Return the user id carried by a valid, unexpired token, else None."""
    try:
        raw = _serializer().loads(token, max_age=get_settings().session_max_age)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None
