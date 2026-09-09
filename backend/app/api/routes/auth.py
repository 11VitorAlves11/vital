"""Authentication — OIDC against any provider, or local email + password.

Which one is live is decided by AUTH_MODE; the endpoints of the other mode answer
404 so a misconfigured deployment fails visibly instead of half-working.
"""

import uuid
from functools import lru_cache
from typing import Any

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.deps import AppSettings, DbSession
from app.core.config import Settings, get_settings
from app.core.security import (
    PasswordTooLongError,
    hash_password,
    issue_session,
    verify_password,
)
from app.models import User
from app.schemas.auth import AuthConfigOut, LoginIn, RegisterIn
from app.schemas.users import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
config_router = APIRouter(prefix="/auth", tags=["auth"])

OIDC_CLIENT_NAME = "oidc"

# Hashing a throwaway password on unknown emails keeps the response time of a wrong
# email and a wrong password comparable, so login cannot be used to enumerate users.
_DUMMY_HASH = hash_password("not-a-real-password")


@lru_cache
def get_oauth() -> OAuth:
    settings = get_settings()
    client_kwargs: dict[str, Any] = {"scope": settings.oidc_scopes}
    if settings.oidc_pkce:
        # PKCE: authlib generates the verifier, keeps it in the signed session
        # cookie for the round trip, and sends it at the token exchange. It binds
        # the authorization code to this browser, so a code intercepted on the
        # redirect cannot be spent by anyone else.
        client_kwargs["code_challenge_method"] = "S256"

    oauth = OAuth()
    oauth.register(
        name=OIDC_CLIENT_NAME,
        server_metadata_url=settings.oidc_metadata_url,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        client_kwargs=client_kwargs,
    )
    return oauth


def _require_mode(settings: Settings, mode: str) -> None:
    if settings.auth_mode != mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"AUTH_MODE is not '{mode}'"
        )


def set_session_cookie(response: Response, user_id: uuid.UUID, settings: Settings) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        issue_session(user_id),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookies_secure,
        path="/",
    )


@config_router.get("/config", response_model=AuthConfigOut)
async def auth_config(settings: AppSettings) -> AuthConfigOut:
    """Public: the login page has to know which form to render before anyone is logged in."""
    return AuthConfigOut(mode=settings.auth_mode)


@router.get("/login", name="oidc_login")
async def oidc_login(request: Request, settings: AppSettings) -> Response:
    _require_mode(settings, "oidc")
    redirect_uri = settings.oidc_redirect_uri or str(request.url_for("oidc_callback"))
    client = get_oauth().create_client(OIDC_CLIENT_NAME)
    redirect: Response = await client.authorize_redirect(request, redirect_uri)
    return redirect


@router.get("/callback", name="oidc_callback")
async def oidc_callback(request: Request, db: DbSession, settings: AppSettings) -> Response:
    _require_mode(settings, "oidc")
    client = get_oauth().create_client(OIDC_CLIENT_NAME)
    try:
        token: dict[str, Any] = await client.authorize_access_token(request)
    except OAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC authentication failed"
        ) from exc

    claims: dict[str, Any] = token.get("userinfo") or {}
    subject = claims.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC token carried no subject"
        )

    user = (await db.execute(select(User).where(User.oidc_sub == subject))).scalar_one_or_none()
    if user is None:
        email = claims.get("email")
        # Accounts are never linked by email: an unverified address at the provider
        # would otherwise be enough to take over an existing account.
        if (
            email
            and (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account already exists with this email address",
            )
        user = User(oidc_sub=subject, email=email, name=claims.get("name"))
        db.add(user)
        await db.commit()
        await db.refresh(user)

    response = RedirectResponse(settings.frontend_url, status_code=status.HTTP_302_FOUND)
    set_session_cookie(response, user.id, settings)
    return response


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterIn, response: Response, db: DbSession, settings: AppSettings
) -> User:
    _require_mode(settings, "local")
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists with this email address",
        )
    try:
        password_hash = hash_password(payload.password)
    except PasswordTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    user = User(
        email=payload.email,
        password_hash=password_hash,
        name=payload.name,
        sex=payload.sex,
        birth_date=payload.birth_date,
        height_cm=payload.height_cm,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    set_session_cookie(response, user.id, settings)
    return user


@router.post("/login", response_model=UserOut)
async def local_login(
    payload: LoginIn, response: Response, db: DbSession, settings: AppSettings
) -> User:
    _require_mode(settings, "local")
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user is None or user.password_hash is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    set_session_cookie(response, user.id, settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: AppSettings) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookies_secure,
    )
