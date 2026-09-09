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
    features,
    health,
    interventions,
    photos,
    providers,
    repeats,
    reports,
    timeline,
    users,
)
from app.core.config import get_settings
from app.db.demo import seed_demo_account
from app.db.seed import load_catalogue
from app.db.session import dispose_engine, get_sessionmaker
from app.services.recompute import recompute_every_users_flags

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with get_sessionmaker()() as db:
        biomarkers, body_metrics = await load_catalogue(db)
        demo_seeded = await seed_demo_account(db) if settings.seed_demo_data else False
        # The catalogue that just loaded may have corrected a band, a range or a
        # conversion factor. Anything already stored is re-derived against it, so
        # a correction reaches the history and not only the next draw.
        accounts = await recompute_every_users_flags(db)
    logger.info(
        "Catalogue loaded: %d biomarkers, %d body metrics; re-flagged %d account(s)",
        biomarkers,
        body_metrics,
        accounts,
    )
    if demo_seeded:
        logger.info("Synthetic demo account created and populated")
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
app.include_router(features.router, prefix="/api")
app.include_router(auth.router)
app.include_router(auth.config_router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(extractions.router, prefix="/api")
app.include_router(interventions.router, prefix="/api")
app.include_router(body.router, prefix="/api")
app.include_router(photos.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(timeline.router, prefix="/api")
app.include_router(repeats.router, prefix="/api")


@app.get("/api")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": "0.1.0"}
