import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LabOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    #: How many of this account's reports came from here.
    report_count: int = 0
    created_at: datetime


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    specialty: str | None = None
    report_count: int = 0
    created_at: datetime
