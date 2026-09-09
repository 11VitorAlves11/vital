from fastapi import APIRouter

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.models import User
from app.schemas.users import ModelSettingsOut, ModelSettingsUpdate, UserOut, UserUpdate
from app.services.model_credentials import effective_model_config, encrypt_api_key
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


def _model_settings_out(user: User, settings: AppSettings) -> ModelSettingsOut:
    config = effective_model_config(user, settings)
    return ModelSettingsOut(
        model=config.model,
        base_url=config.base_url,
        has_api_key=bool(user.llm_api_key_encrypted or settings.llm_api_key),
        has_account_api_key=bool(user.llm_api_key_encrypted),
        uses_instance_model=user.llm_model is None,
        uses_instance_base_url=user.llm_base_url is None,
    )


@router.get("/me/model-settings", response_model=ModelSettingsOut)
async def read_model_settings(user: CurrentUser, settings: AppSettings) -> ModelSettingsOut:
    return _model_settings_out(user, settings)


@router.patch("/me/model-settings", response_model=ModelSettingsOut)
async def update_model_settings(
    payload: ModelSettingsUpdate, user: CurrentUser, db: DbSession, settings: AppSettings
) -> ModelSettingsOut:
    written = payload.model_fields_set
    if "model" in written:
        user.llm_model = payload.model.strip() if payload.model else None
    if "base_url" in written:
        user.llm_base_url = str(payload.base_url).rstrip("/") if payload.base_url else None
    if payload.clear_api_key:
        user.llm_api_key_encrypted = None
    elif payload.api_key is not None:
        user.llm_api_key_encrypted = encrypt_api_key(payload.api_key, settings)
    await db.commit()
    await db.refresh(user)
    return _model_settings_out(user, settings)
