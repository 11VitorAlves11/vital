from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ResultFlag
from app.schemas.catalog import BiomarkerOut, BodyMetricOut
from app.schemas.interventions import InterventionOut


class BiomarkerPoint(BaseModel):
    date: date
    value: Decimal
    unit: str
    lab_name: str
    # The lab's own range for this draw — what the shaded band is drawn from.
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None
    flag: ResultFlag | None = None
    report_id: str


class BiomarkerSeries(BaseModel):
    biomarker: BiomarkerOut
    points: list[BiomarkerPoint]
    # Only those overlapping the period covered by the points, for the chart overlay.
    interventions: list[InterventionOut]


class BodyPoint(BaseModel):
    date: datetime
    value: Decimal
    flag: Literal["normal", "warn", "alert"] | None = None
    label: str | None = None
    scan_id: str


class BodySeries(BaseModel):
    metric: BodyMetricOut
    points: list[BodyPoint]
    interventions: list[InterventionOut]
