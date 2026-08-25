from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import read_session
from app.db.session import get_session
from app.models import User

DbSession = Annotated[AsyncSession, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_current_user(request: Request, db: DbSession, settings: AppSettings) -> User:
    """Resolve the session cookie to a user, or fail with 401.

    Every endpoint outside /auth depends on this: there is no data in Vital that
    is not owned by exactly one user.
    """
    unauthorised = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise unauthorised
    user_id = read_session(token)
    if user_id is None:
        raise unauthorised
    user = await db.get(User, user_id)
    if user is None:
        raise unauthorised
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
