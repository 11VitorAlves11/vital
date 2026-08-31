import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    BiomarkerCategory,
    FastingState,
    ReferenceKind,
    ReportSource,
    ResultFlag,
)
from app.schemas.catalog import ReferenceBandOut

#: Longest fast worth recording. Beyond four days it is a clinical event of its
#: own, not the context of a blood draw, and the value is far likelier a typo.
MAX_FASTING_HOURS = 96


class CaveatOut(BaseModel):
    """A reason to read the value with care. The wording is the client's."""

    code: str
    values: dict[str, str] = Field(default_factory=dict)


class ResultIn(BaseModel):
    biomarker_id: int
    value: Decimal
    # Defaults to the catalogue unit; the lab's own wording wins when given.
    unit: str | None = Field(default=None, max_length=50)
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None
    #: The assay, as the report names it.
    method: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        if self.ref_min is not None and self.ref_max is not None and self.ref_min >= self.ref_max:
            raise ValueError("ref_min must be below ref_max")
        return self


class CollectionContext(BaseModel):
    """The pre-analytical half of a report, shared by manual entry and confirmation."""

    collected_on: date
    #: Wall-clock moment of the draw. Its date has to be `collected_on`.
    collected_at: datetime | None = None
    fasting_state: FastingState = FastingState.UNKNOWN
    fasting_hours: int | None = Field(default=None, ge=0, le=MAX_FASTING_HOURS)

    @model_validator(mode="after")
    def _check_collection(self) -> Self:
        if self.collected_at is not None:
            if self.collected_at.tzinfo is not None:
                raise ValueError("collected_at is a local wall-clock time, without an offset")
            if self.collected_at.date() != self.collected_on:
                raise ValueError("collected_at must fall on collected_on")
        # Hours of a fast nobody claims happened describe nothing.
        if self.fasting_hours is not None and self.fasting_state is not FastingState.FASTING:
            raise ValueError("fasting_hours only applies when fasting_state is 'fasting'")
        return self


class ReportCreate(CollectionContext):
    lab_name: str = Field(min_length=1, max_length=200)
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
    #: As the laboratory reported it — what the report itself would show.
    value: Decimal
    unit: str
    # The same reading in the catalogue's unit; null when it was not convertible.
    canonical_value: Decimal | None = None
    canonical_unit: str | None = None
    ref_min: Decimal | None
    ref_max: Decimal | None
    reference_kind: ReferenceKind
    #: The ordinal scale this value was read against, in `canonical_unit`.
    reference_bands: list[ReferenceBandOut] | None = None
    #: Which step of that scale it landed on ("insuficiência"), for ordinal markers.
    band_label: str | None = None
    method: str | None = None
    #: What the collection context, or the assay, means for reading this value.
    caveats: list[CaveatOut] = Field(default_factory=list)
    flag: ResultFlag | None


class ReportSummary(BaseModel):
    id: uuid.UUID
    collected_on: date
    collected_at: datetime | None
    lab_name: str
    fasting_state: FastingState
    fasting_hours: int | None
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
    collected_at: datetime | None
    lab_name: str
    fasting_state: FastingState
    fasting_hours: int | None
    source: ReportSource
    notes: str | None
    created_at: datetime
    has_file: bool
    results: list[ResultOut]
