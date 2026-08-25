import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import get_sessionmaker


async def database_is_reachable() -> bool:
    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


@pytest.mark.asyncio
async def test_health_db_reports_a_reachable_database(client: AsyncClient) -> None:
    """Verifies the app is actually wired to Postgres.

    Skipped when no database is configured locally; CI always runs it against the
    Postgres service, so the wiring cannot silently rot.
    """
    if not await database_is_reachable():
        pytest.skip("no database reachable at DATABASE_URL")

    response = await client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
