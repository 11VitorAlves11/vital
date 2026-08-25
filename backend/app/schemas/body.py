import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ScanSource
from app.schemas.catalog import BodyMetricOut


class ScanValueIn(BaseModel):
    metric_id: int
    value: Decimal


class BodyScanCreate(BaseModel):
    measured_at: datetime
    device: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    values: list[ScanValueIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_metrics(self) -> Self:
        seen = {value.metric_id for value in self.values}
        if len(seen) != len(self.values):
            raise ValueError("a scan cannot carry the same metric twice")
        return self


class ScanValueOut(BaseModel):
    id: uuid.UUID
    metric_id: int
    metric_slug: str
    metric_name: str
    unit: str
    value: Decimal
    # Both null for a trend-only metric, and for anyone whose sex is not set:
    # there is no honest way to pick between the male and female band sets.
    flag: Literal["normal", "warn", "alert"] | None = None
    label: str | None = None


class BodyScanOut(BaseModel):
    id: uuid.UUID
    measured_at: datetime
    source: ScanSource
    device: str | None
    notes: str | None
    values: list[ScanValueOut]


class BodySparkPoint(BaseModel):
    date: datetime
    value: Decimal


class BodyMetricSummary(BaseModel):
    """One card in the body-composition grid. Metrics never measured are omitted."""

    metric: BodyMetricOut
    latest: ScanValueOut
    measured_at: datetime
    sparkline: list[BodySparkPoint]
