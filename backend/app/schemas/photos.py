import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Pose


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    taken_on: date
    pose: Pose
    # The stored dimensions, so a gallery can reserve the right box before the
    # image arrives instead of reflowing under the reader's cursor.
    width: int
    height: int
    notes: str | None
    created_at: datetime


class PhotoCreate(BaseModel):
    """The form fields beside the upload. The file itself is not modelled here."""

    taken_on: date
    pose: Pose = Pose.FRENTE
    notes: str | None = Field(default=None, max_length=2000)
