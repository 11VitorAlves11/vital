from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import BiomarkerCategory, ResultFlag
from app.schemas.catalog import BiomarkerOut

# How many readings a dashboard sparkline carries. Enough to read a direction,
# few enough that the card stays a summary and not a chart.
SPARKLINE_POINTS = 8


class SparkPoint(BaseModel):
    date: date
    #: Canonical where the reading could be converted, as reported where it could not.
    value: Decimal


class DashboardItem(BaseModel):
    biomarker: BiomarkerOut
    #: The latest reading as the lab reported it — the number on the card.
    value: Decimal
    unit: str
    flag: ResultFlag | None
    #: Which step of an ordinal scale it landed on, for the markers that have one.
    band_label: str | None = None
    collected_on: date
    lab_name: str
    sparkline: list[SparkPoint]


class DashboardCategory(BaseModel):
    category: BiomarkerCategory
    items: list[DashboardItem]


class DashboardOut(BaseModel):
    categories: list[DashboardCategory]
    last_report_on: date | None
    report_count: int
