from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ReferenceKind, ResultFlag
from app.schemas.catalog import BiomarkerOut, BodyMetricOut
from app.schemas.interventions import InterventionOut


class BiomarkerPoint(BaseModel):
    date: date
    #: As reported, in `unit` — shown in tables and tooltips.
    value: Decimal
    unit: str
    #: In the series' own unit — what the line is actually plotted from.
    canonical_value: Decimal | None = None
    lab_name: str
    # The lab's own range for this draw — what the shaded band is drawn from,
    # converted alongside the value so the band and the line share an axis.
    ref_min: Decimal | None = None
    ref_max: Decimal | None = None
    canonical_ref_min: Decimal | None = None
    canonical_ref_max: Decimal | None = None
    reference_kind: ReferenceKind
    band_label: str | None = None
    flag: ResultFlag | None = None
    report_id: str


class BiomarkerSeries(BaseModel):
    biomarker: BiomarkerOut
    points: list[BiomarkerPoint]
    #: The unit the whole series is plotted in, whatever the individual reports used.
    unit: str
    # True when at least one point could not be converted into it, so the chart
    # can say the line has a gap instead of quietly leaving a point out.
    has_unconverted_points: bool = False
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
