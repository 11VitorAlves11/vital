import asyncio
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Settings are read once, at import time, so the test environment has to be in
# place before anything under app/ is imported.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AUTH_MODE", "local")
os.environ.setdefault("SECRET_KEY", "test-secret-not-used-anywhere-real")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import dispose_engine  # noqa: E402
from app.main import app  # noqa: E402

TEST_PASSWORD = "a-long-enough-password"

UserFactory = Callable[..., Awaitable[tuple[AsyncClient, dict[str, Any]]]]


def _database_reachable() -> bool:
    async def ping() -> bool:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            return False
        finally:
            await engine.dispose()
        return True

    return asyncio.run(ping())


@pytest.fixture(scope="session")
def database() -> None:
    """Rebuild the schema from the migrations, then load the catalogue.

    Going through Alembic rather than `create_all` means the suite runs against the
    schema the deployment actually gets, so model/migration drift fails the tests.
    """
    database_name = make_url(get_settings().database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.skip("refusing to rebuild a database whose name does not end in _test")
    if not _database_reachable():
        pytest.skip("no database reachable at DATABASE_URL")
    for arguments in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=BACKEND_DIR,
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [sys.executable, "-m", "app.db.seed"], cwd=BACKEND_DIR, check=True, capture_output=True
    )


@pytest.fixture(autouse=True)
async def _fresh_engine() -> AsyncIterator[None]:
    """Drop the cached engine between tests.

    Each test runs in its own event loop, and a connection pool outlives neither:
    reusing it raises "Event loop is closed" on the second test that touches the DB.
    """
    yield
    await dispose_engine()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def make_user(database: None) -> AsyncIterator[UserFactory]:
    """Register a fresh account and hand back a client already holding its session.

    Every test gets its own users, so user-scoped data cannot leak between tests
    the way it must not leak between accounts.
    """
    clients: list[AsyncClient] = []

    async def factory(sex: str | None = "M", **extra: Any) -> tuple[AsyncClient, dict[str, Any]]:
        ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        clients.append(ac)
        payload = {
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": TEST_PASSWORD,
            "sex": sex,
            **extra,
        }
        response = await ac.post("/auth/register", json=payload)
        assert response.status_code == 201, response.text
        return ac, response.json()

    yield factory

    for ac in clients:
        await ac.aclose()


@pytest.fixture
async def user_client(make_user: UserFactory) -> AsyncClient:
    ac, _ = await make_user()
    return ac


@pytest.fixture
async def catalogue(user_client: AsyncClient) -> dict[str, dict[str, Any]]:
    """Biomarkers and body metrics keyed by slug, as the API returns them."""
    biomarkers = (await user_client.get("/api/biomarkers")).json()
    metrics = (await user_client.get("/api/body/metrics")).json()
    return {
        "biomarkers": {item["slug"]: item for item in biomarkers},
        "metrics": {item["slug"]: item for item in metrics},
    }
