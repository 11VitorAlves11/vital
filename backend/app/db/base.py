"""Metadata aggregator: importing this module registers every table on `Base`.

Alembic's autogenerate and the test fixtures rely on it, so a new model is only
ever added to `app/models/__init__.py`.
"""

from app.models import (
    Base,
    Biomarker,
    BodyMetric,
    BodyScan,
    BodyScanValue,
    Intervention,
    LabReport,
    Result,
    User,
)

__all__ = [
    "Base",
    "Biomarker",
    "BodyMetric",
    "BodyScan",
    "BodyScanValue",
    "Intervention",
    "LabReport",
    "Result",
    "User",
]
