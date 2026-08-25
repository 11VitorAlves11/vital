"""OIDC login against a stand-in provider.

The real handshake needs an identity provider; what has to be pinned down here is
what Vital does with the claims it gets back — including refusing to hand an
existing account to a new subject.
"""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.responses import RedirectResponse

from app.api.routes import auth as auth_routes
from app.core.config import get_settings
from app.main import app
from tests.conftest import TEST_PASSWORD


class FakeClient:
    """Stands in for the authlib client: no network, fixed claims."""

    def __init__(self, claims: dict[str, Any]) -> None:
        self.claims = claims
        self.redirect_uri: str | None = None

    async def authorize_redirect(self, request: Any, redirect_uri: str) -> RedirectResponse:
        self.redirect_uri = redirect_uri
        return RedirectResponse(f"https://idp.example/authorize?redirect_uri={redirect_uri}")

    async def authorize_access_token(self, request: Any) -> dict[str, Any]:
        return {"userinfo": self.claims}


class FakeOAuth:
    def __init__(self, client: FakeClient) -> None:
        self.client = client

    def create_client(self, name: str) -> FakeClient:
        return self.client


@pytest.fixture
def oidc_mode() -> Iterator[None]:
    settings = get_settings()
    original = settings.auth_mode
    settings.auth_mode = "oidc"
    try:
        yield
    finally:
        settings.auth_mode = original


@pytest.fixture
def fake_provider(
    oidc_mode: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[[dict[str, Any]], FakeClient]]:
    def install(claims: dict[str, Any]) -> FakeClient:
        client = FakeClient(claims)
        monkeypatch.setattr(auth_routes, "get_oauth", lambda: FakeOAuth(client))
        return client

    yield install


async def test_config_reports_oidc(client: AsyncClient, oidc_mode: None) -> None:
    assert (await client.get("/api/auth/config")).json() == {"mode": "oidc"}


async def test_local_endpoints_are_absent_in_oidc_mode(
    client: AsyncClient, oidc_mode: None
) -> None:
    response = await client.post(
        "/auth/register", json={"email": "x@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 404
    response = await client.post(
        "/auth/login", json={"email": "x@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 404


async def test_login_redirects_to_the_provider(
    client: AsyncClient, fake_provider: Any, database: None
) -> None:
    provider = fake_provider({"sub": "irrelevant"})
    response = await client.get("/auth/login")
    assert response.status_code == 307
    assert response.headers["location"].startswith("https://idp.example/authorize")
    assert provider.redirect_uri.endswith("/auth/callback")


async def test_callback_creates_the_account_and_starts_a_session(
    client: AsyncClient, fake_provider: Any, database: None
) -> None:
    subject = f"sub-{uuid.uuid4().hex}"
    fake_provider({"sub": subject, "email": f"{subject}@example.com", "name": "Ana"})

    response = await client.get("/auth/callback", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == get_settings().frontend_url
    assert response.cookies.get(get_settings().session_cookie_name)

    me = (await client.get("/api/users/me")).json()
    assert me["name"] == "Ana"
    assert me["email"] == f"{subject}@example.com"
    # No provider releases it, so it stays unset until the user says so.
    assert me["sex"] is None


async def test_second_callback_reuses_the_same_account(
    client: AsyncClient, fake_provider: Any, database: None
) -> None:
    subject = f"sub-{uuid.uuid4().hex}"
    claims = {"sub": subject, "email": f"{subject}@example.com", "name": "Ana"}
    fake_provider(claims)

    first = (await client.get("/auth/callback")).cookies
    assert first is not None
    first_id = (await client.get("/api/users/me")).json()["id"]

    await client.post("/auth/logout")
    await client.get("/auth/callback")
    assert (await client.get("/api/users/me")).json()["id"] == first_id


async def test_a_new_subject_cannot_claim_an_existing_email(
    client: AsyncClient, fake_provider: Any, database: None
) -> None:
    email = f"{uuid.uuid4().hex}@example.com"
    fake_provider({"sub": f"sub-{uuid.uuid4().hex}", "email": email})
    assert (await client.get("/auth/callback", follow_redirects=False)).status_code == 302

    other = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    fake_provider({"sub": f"sub-{uuid.uuid4().hex}", "email": email})
    try:
        response = await other.get("/auth/callback", follow_redirects=False)
        assert response.status_code == 409
    finally:
        await other.aclose()


async def test_a_token_without_a_subject_is_refused(
    client: AsyncClient, fake_provider: Any, database: None
) -> None:
    fake_provider({"email": "sem-sub@example.com"})
    assert (await client.get("/auth/callback", follow_redirects=False)).status_code == 401
