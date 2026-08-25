from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — does not touch the database."""
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, Any]:
    """Readiness probe — verifies the database connection."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
