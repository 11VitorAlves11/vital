import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ExtractionStatus, FastingState
from app.schemas.reports import CollectionContext


def _decimal_or_none(value: object) -> Decimal | None:
    """Models answer with strings, commas and stray units. None beats a guess."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float | Decimal):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip().replace(",", ".").lstrip("<>≤≥~").strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except ArithmeticError:
            return None
    return None


class ExtractedResult(BaseModel):
    """One line as the model read it, before any matching against the catalogue."""

    biomarker: str = Field(min_length=1, max_length=200)
    value: Decimal | None = None
    unit: str | None = Field(default=None, max_length=50)
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None
    #: The assay, when the report prints one next to the line.
    method: str | None = Field(default=None, max_length=120)

    @field_validator("value", "ref_min", "ref_max", mode="before")
    @classmethod
    def _coerce(cls, value: object) -> Decimal | None:
        return _decimal_or_none(value)

    @field_validator("unit", "method", mode="before")
    @classmethod
    def _blank_string_is_none(cls, value: object) -> object:
        return value or None


class ExtractionPayload(BaseModel):
    """The whole answer. Every field is optional: a document the model could not
    date is still worth previewing, with the date left for a human to fill in."""

    collected_on: date | None = None
    #: Wall-clock moment of the draw, when the report states one.
    collected_at: datetime | None = None
    lab_name: str | None = Field(default=None, max_length=200)
    fasting: bool | None = None
    results: list[ExtractedResult] = Field(default_factory=list)

    @field_validator("collected_on", "collected_at", mode="before")
    @classmethod
    def _blank_date_is_none(cls, value: object) -> object:
        return value or None

    @field_validator("lab_name", mode="before")
    @classmethod
    def _blank_name_is_none(cls, value: object) -> object:
        return value or None


class PreviewResult(BaseModel):
    """A read line paired with the catalogue entry it was matched to, if any.

    An unmatched line is still shown: silently dropping a value the reader can
    see on their own report is worse than showing it as needing a choice.
    """

    biomarker_id: int | None
    biomarker_name: str | None
    biomarker_slug: str | None
    # What the document itself called it, kept so the reader can check the match.
    source_name: str
    value: Decimal | None
    unit: str | None
    ref_min: Decimal | None
    ref_max: Decimal | None
    method: str | None
    warnings: list[str] = Field(default_factory=list)


class ExtractionPreview(BaseModel):
    collected_on: date | None
    collected_at: datetime | None
    lab_name: str | None
    #: The model's boolean, widened into the three states the report stores.
    fasting_state: FastingState
    results: list[PreviewResult]


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ExtractionStatus
    filename: str | None
    provider: str | None
    error: str | None
    report_id: uuid.UUID | None
    created_at: datetime
    # Only once the status is `preview`; a job still running has nothing to show.
    preview: ExtractionPreview | None = None


class ConfirmResult(BaseModel):
    biomarker_id: int
    value: Decimal
    unit: str | None = Field(default=None, max_length=50)
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None
    method: str | None = Field(default=None, max_length=120)
    source_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        if self.ref_min is not None and self.ref_max is not None and self.ref_min >= self.ref_max:
            raise ValueError("ref_min must be below ref_max")
        return self


class ExtractionConfirm(CollectionContext):
    """What the human approved, which is what actually gets stored.

    It is a full payload rather than a diff: the reader may have corrected a
    misread decimal, dropped a line the model invented or matched one it could
    not, and the endpoint should not have to guess which.
    """

    lab_name: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    results: list[ConfirmResult] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_biomarkers(self) -> Self:
        seen = {result.biomarker_id for result in self.results}
        if len(seen) != len(self.results):
            raise ValueError("a report cannot carry the same biomarker twice")
        return self
