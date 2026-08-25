import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BiomarkerCategory, ReportSource, ResultFlag


class ResultIn(BaseModel):
    biomarker_id: int
    value: Decimal
    # Defaults to the catalogue unit; the lab's own wording wins when given.
    unit: str | None = Field(default=None, max_length=50)
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        if self.ref_min is not None and self.ref_max is not None and self.ref_min >= self.ref_max:
            raise ValueError("ref_min must be below ref_max")
        return self


class ReportCreate(BaseModel):
    collected_on: date
    lab_name: str = Field(min_length=1, max_length=200)
    fasting: bool | None = None
    notes: str | None = None
    results: list[ResultIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_biomarkers(self) -> Self:
        seen = {result.biomarker_id for result in self.results}
        if len(seen) != len(self.results):
            raise ValueError("a report cannot carry the same biomarker twice")
        return self


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    biomarker_id: int
    biomarker_slug: str
    biomarker_name: str
    category: BiomarkerCategory
    value: Decimal
    unit: str
    ref_min: Decimal | None
    ref_max: Decimal | None
    flag: ResultFlag | None


class ReportSummary(BaseModel):
    id: uuid.UUID
    collected_on: date
    lab_name: str
    fasting: bool | None
    source: ReportSource
    notes: str | None
    created_at: datetime
    result_count: int
    # Whether GET /reports/{id}/file has anything to serve. The path itself never
    # leaves the server: it says where someone's blood work sits on disk.
    has_file: bool


class ReportOut(BaseModel):
    id: uuid.UUID
    collected_on: date
    lab_name: str
    fasting: bool | None
    source: ReportSource
    notes: str | None
    created_at: datetime
    has_file: bool
    results: list[ResultOut]
