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
    value: Decimal


class DashboardItem(BaseModel):
    biomarker: BiomarkerOut
    value: Decimal
    unit: str
    flag: ResultFlag | None
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
