import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ExtractionStatus


class ExtractedBodyValue(BaseModel):
    source_name: str = Field(min_length=1, max_length=200)
    metric_slug: str | None = Field(default=None, max_length=100)
    value: Decimal | None = None
    unit: str | None = Field(default=None, max_length=50)

    @field_validator("value", mode="before")
    @classmethod
    def decimal_or_none(cls, value: object) -> Decimal | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return Decimal(str(value).replace(",", "."))
        except ArithmeticError:
            return None


class BodyExtractionPayload(BaseModel):
    measured_at: datetime | None = None
    device: str | None = Field(default=None, max_length=100)
    results: list[ExtractedBodyValue] = Field(default_factory=list)


class BodyPreviewValue(BaseModel):
    metric_id: int | None
    metric_slug: str | None
    metric_name: str | None
    expected_unit: str | None
    source_name: str
    source_unit: str | None
    value: Decimal | None
    warnings: list[str] = Field(default_factory=list)


class BodyExtractionPreview(BaseModel):
    measured_at: datetime | None
    device: str | None
    results: list[BodyPreviewValue]


class BodyExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ExtractionStatus
    filename: str | None
    provider: str | None
    error: str | None
    body_scan_id: uuid.UUID | None
    created_at: datetime
    preview: BodyExtractionPreview | None = None


class ConfirmBodyValue(BaseModel):
    metric_id: int
    value: Decimal


class BodyExtractionConfirm(BaseModel):
    measured_at: datetime
    device: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    values: list[ConfirmBodyValue] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_metrics(self) -> "BodyExtractionConfirm":
        if len({item.metric_id for item in self.values}) != len(self.values):
            raise ValueError("a scan cannot carry the same metric twice")
        return self
