import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import (
    auth,
    body,
    catalog,
    dashboard,
    extractions,
    health,
    interventions,
    reports,
    users,
)
from app.core.config import get_settings
from app.db.seed import load_catalogue
from app.db.session import dispose_engine, get_sessionmaker

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with get_sessionmaker()() as db:
        biomarkers, body_metrics = await load_catalogue(db)
    logger.info("Catalogue loaded: %d biomarkers, %d body metrics", biomarkers, body_metrics)
    yield
    await dispose_engine()


app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    lifespan=lifespan,
)

# Added first so it ends up innermost: it only holds the short-lived OIDC handshake
# state, and CORS has to stay outermost to answer preflights.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="vital_oidc_state",
    max_age=600,
    same_site="lax",
    https_only=settings.cookies_secure,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router)
app.include_router(auth.config_router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(extractions.router, prefix="/api")
app.include_router(interventions.router, prefix="/api")
app.include_router(body.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/api")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": "0.1.0"}
