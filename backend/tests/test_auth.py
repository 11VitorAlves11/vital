"""Local authentication, the session cookie, and what happens without one."""

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from httpx import AsyncClient
from itsdangerous import TimestampSigner

from app.core.config import get_settings
from app.core.security import (
    MAX_CLOCK_SKEW_SECONDS,
    hash_password,
    issue_session,
    read_session,
    verify_password,
)
from tests.conftest import TEST_PASSWORD, UserFactory

PROTECTED = [
    "/api/users/me",
    "/api/biomarkers",
    "/api/body/metrics",
    "/api/body/scans",
    "/api/body/summary",
    "/api/reports",
    "/api/interventions",
    "/api/dashboard",
]


async def test_auth_config_is_public(client: AsyncClient) -> None:
    response = await client.get("/api/auth/config")
    assert response.status_code == 200
    assert response.json() == {"mode": get_settings().auth_mode}


@pytest.mark.parametrize("path", PROTECTED)
async def test_every_endpoint_requires_a_session(client: AsyncClient, path: str) -> None:
    assert (await client.get(path)).status_code == 401


async def test_register_sets_an_httponly_session_cookie(
    client: AsyncClient, database: None
) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": f"{uuid.uuid4().hex}@example.com", "password": TEST_PASSWORD, "sex": "M"},
    )
    assert response.status_code == 201
    assert response.cookies.get(get_settings().session_cookie_name)
    header = response.headers["set-cookie"]
    assert "HttpOnly" in header
    assert "SameSite=lax" in header
    assert "Path=/" in header
    assert (await client.get("/api/users/me")).status_code == 200


async def test_registration_stores_the_height_given_up_front(
    client: AsyncClient, database: None
) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": TEST_PASSWORD,
            "height_cm": 168,
        },
    )
    assert response.status_code == 201
    assert response.json()["height_cm"] == "168.0"
    assert (await client.get("/api/users/me")).json()["height_cm"] == "168.0"


async def test_registration_rejects_an_out_of_range_height(
    client: AsyncClient, database: None
) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": TEST_PASSWORD,
            "height_cm": 50,
        },
    )
    assert response.status_code == 422


async def test_registration_never_returns_the_password_hash(make_user: UserFactory) -> None:
    _, user = await make_user()
    assert "password" not in user
    assert "password_hash" not in user


async def test_duplicate_email_is_rejected(client: AsyncClient, database: None) -> None:
    email = f"{uuid.uuid4().hex}@example.com"
    payload: dict[str, Any] = {"email": email, "password": TEST_PASSWORD}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    assert (await client.post("/auth/register", json=payload)).status_code == 409


async def test_short_passwords_are_rejected(client: AsyncClient, database: None) -> None:
    response = await client.post(
        "/auth/register", json={"email": f"{uuid.uuid4().hex}@example.com", "password": "curta"}
    )
    assert response.status_code == 422


async def test_login_logout_round_trip(client: AsyncClient, make_user: UserFactory) -> None:
    _, user = await make_user()

    wrong = await client.post("/auth/login", json={"email": user["email"], "password": "nope-nope"})
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Invalid email or password"

    unknown = await client.post(
        "/auth/login", json={"email": "ninguem@example.com", "password": TEST_PASSWORD}
    )
    # Identical wording: a different message would say whether the account exists.
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == "Invalid email or password"

    good = await client.post(
        "/auth/login", json={"email": user["email"], "password": TEST_PASSWORD}
    )
    assert good.status_code == 200
    assert (await client.get("/api/users/me")).json()["id"] == user["id"]

    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/api/users/me")).status_code == 401


async def test_expired_session_is_refused(user_client: AsyncClient) -> None:
    settings = get_settings()
    original = settings.session_max_age
    settings.session_max_age = -1
    try:
        assert (await user_client.get("/api/users/me")).status_code == 401
    finally:
        settings.session_max_age = original


async def test_tampered_session_is_refused(user_client: AsyncClient) -> None:
    settings = get_settings()
    user_client.cookies.set(settings.session_cookie_name, "forged.session.token")
    assert (await user_client.get("/api/users/me")).status_code == 401


async def test_session_for_a_deleted_user_is_refused(client: AsyncClient, database: None) -> None:
    client.cookies.set(get_settings().session_cookie_name, issue_session(uuid.uuid4()))
    assert (await client.get("/api/users/me")).status_code == 401


async def test_oidc_endpoints_are_absent_in_local_mode(client: AsyncClient) -> None:
    assert (await client.get("/auth/login")).status_code == 404
    assert (await client.get("/auth/callback")).status_code == 404


async def test_session_token_round_trip() -> None:
    user_id = uuid.uuid4()
    assert read_session(issue_session(user_id)) == user_id
    assert read_session("not-a-token") is None


@contextmanager
def _clock_offset(seconds: int) -> Iterator[None]:
    """Issue tokens as if this machine's clock were `seconds` off from real time."""
    original = TimestampSigner.get_timestamp
    TimestampSigner.get_timestamp = lambda self: int(time.time()) + seconds  # type: ignore[method-assign]
    try:
        yield
    finally:
        TimestampSigner.get_timestamp = original  # type: ignore[method-assign]


def _token_stamped(offset_seconds: int, user_id: uuid.UUID) -> str:
    """A session token signed by us, but timestamped somewhere else in time."""
    with _clock_offset(offset_seconds):
        return issue_session(user_id)


async def test_a_token_from_the_near_future_is_still_read() -> None:
    """A clock that stepped back must not sign everybody out.

    Machines do step their clocks — after a suspend, or when NTP first syncs —
    and a token stamped seconds ahead carries a signature only this instance
    could have produced.
    """
    user_id = uuid.uuid4()
    assert read_session(_token_stamped(5, user_id)) == user_id
    assert read_session(_token_stamped(MAX_CLOCK_SKEW_SECONDS - 1, user_id)) == user_id


async def test_a_token_from_far_ahead_or_long_past_is_refused() -> None:
    """The tolerance is for skew, not for extending a session by either end."""
    user_id = uuid.uuid4()
    assert read_session(_token_stamped(MAX_CLOCK_SKEW_SECONDS + 60, user_id)) is None
    expired = -(get_settings().session_max_age + 60)
    assert read_session(_token_stamped(expired, user_id)) is None


async def test_passwords_are_hashed_not_stored() -> None:
    hashed = hash_password(TEST_PASSWORD)
    assert TEST_PASSWORD not in hashed
    assert hashed.startswith("$2b$")
    assert verify_password(TEST_PASSWORD, hashed)
    assert not verify_password("outra-password", hashed)


async def test_profile_updates_are_scoped_to_the_caller(make_user: UserFactory) -> None:
    ac, _ = await make_user(sex=None)
    response = await ac.patch("/api/users/me", json={"name": "Ana", "sex": "F"})
    assert response.status_code == 200
    assert response.json()["name"] == "Ana"
    assert response.json()["sex"] == "F"
