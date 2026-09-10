import uuid
from datetime import datetime

from pydantic import BaseModel


class BiomarkerMatchRuleOut(BaseModel):
    id: uuid.UUID
    lab_name: str
    source_name: str
    source_unit: str | None
    biomarker_id: int
    biomarker_name: str
    biomarker_unit: str
    created_at: datetime
