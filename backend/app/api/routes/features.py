"""What this instance can do.

Vital is self-hosted, so two deployments of the same version differ in what is
configured. The interface asks rather than guesses: an import button that is
always there and always answers 503 is worse than one that is not there.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import AppSettings, CurrentUser

router = APIRouter(prefix="/features", tags=["features"])


class FeaturesOut(BaseModel):
    extraction: bool


@router.get("", response_model=FeaturesOut)
async def read_features(user: CurrentUser, settings: AppSettings) -> FeaturesOut:
    return FeaturesOut(extraction=settings.extraction_enabled)
