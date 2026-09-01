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
    #: Context for this one value, as against the report's own note.
    note: str | None = Field(default=None, max_length=2000)

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
    #: Resolved to the account's own laboratory entity, created on first sight.
    lab_name: str = Field(min_length=1, max_length=200)
    doctor_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=8000)
    results: list[ResultIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_biomarkers(self) -> Self:
        seen = {result.biomarker_id for result in self.results}
        if len(seen) != len(self.results):
            raise ValueError("a report cannot carry the same biomarker twice")
        return self


class ReportPatch(BaseModel):
    """What can be corrected after the fact.

    Not the values: a wrong number is a wrong reading and belongs in a corrected
    report, not in an edit that leaves no trace of what was there before.
    """

    notes: str | None = Field(default=None, max_length=8000)
    doctor_name: str | None = Field(default=None, max_length=200)


class ResultPatch(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


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
    #: Context someone wrote against this one value, and when.
    note: str | None = None
    note_at: datetime | None = None
    #: What the collection context, or the assay, means for reading this value.
    caveats: list[CaveatOut] = Field(default_factory=list)
    flag: ResultFlag | None


class ResultPrefill(BaseModel):
    """What the last reading of this marker looked like, to save typing it again.

    Everything here is a suggestion the form fills in and the reader can
    overwrite. Nothing is applied server-side: a range that goes unedited has to
    be one someone looked at, not one the software assumed.
    """

    biomarker_id: int
    unit: str
    ref_min: Decimal | None
    ref_max: Decimal | None
    method: str | None
    #: Where and when the suggestion comes from, so it can be shown and doubted.
    lab_name: str
    collected_on: date
    # Whether it came from the laboratory the new report is for. A range from
    # another laboratory is that laboratory's, and carrying it across is exactly
    # what storing the range per result exists to prevent.
    same_lab: bool


class ReportSummary(BaseModel):
    id: uuid.UUID
    collected_on: date
    collected_at: datetime | None
    lab_id: uuid.UUID
    lab_name: str
    doctor_id: uuid.UUID | None
    doctor_name: str | None
    fasting_state: FastingState
    fasting_hours: int | None
    source: ReportSource
    notes: str | None
    notes_at: datetime | None
    created_at: datetime
    result_count: int
    # Whether GET /reports/{id}/file has anything to serve. The path itself never
    # leaves the server: it says where someone's blood work sits on disk.
    has_file: bool


class ComparisonRow(BaseModel):
    """One biomarker across the two collections.

    Either side may be null: a marker measured once and not the next time is part
    of what the comparison shows, not a row to leave out.
    """

    biomarker_id: int
    biomarker_slug: str
    biomarker_name: str
    category: BiomarkerCategory
    previous: ResultOut | None
    current: ResultOut | None
    #: Later minus earlier, in `unit`. Null when the two had no common scale.
    delta: Decimal | None
    #: Against the earlier value, in per cent. Null when that value was zero.
    percent_change: Decimal | None
    #: The unit the difference is expressed in, which is not always either report's.
    unit: str | None
    #: Why the two numbers may not be strictly subtractable — a changed assay, a
    #: reference interval that moved, units with no conversion between them.
    caveats: list[CaveatOut] = Field(default_factory=list)


class ReportComparison(BaseModel):
    """Two collections side by side, oldest first whatever order they were asked in."""

    previous: ReportSummary
    current: ReportSummary
    rows: list[ComparisonRow]


class ReportOut(BaseModel):
    id: uuid.UUID
    collected_on: date
    collected_at: datetime | None
    lab_id: uuid.UUID
    lab_name: str
    doctor_id: uuid.UUID | None
    doctor_name: str | None
    fasting_state: FastingState
    fasting_hours: int | None
    source: ReportSource
    notes: str | None
    notes_at: datetime | None
    created_at: datetime
    has_file: bool
    results: list[ResultOut]
