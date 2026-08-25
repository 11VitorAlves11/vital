from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.models import User
from app.schemas.users import UserOut, UserUpdate
from app.services.recompute import recompute_user_flags

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def read_me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession) -> User:
    changes = payload.model_dump(exclude_unset=True)
    sex_changed = "sex" in changes and changes["sex"] != user.sex
    for field, value in changes.items():
        setattr(user, field, value)
    if sex_changed:
        # Ranges and bands are sex-specific: leaving the history flagged under the
        # old sex would show values as normal (or not) against the wrong standard.
        await recompute_user_flags(db, user)
    await db.commit()
    await db.refresh(user)
    return user
