"""The laboratories and doctors an account has actually used.

They exist so the history can be filtered by where it came from, and so a manual
entry can be pre-filled from the last report the same laboratory issued. Both
lists are per-account and scoped to the session user, like everything else here.
"""

import uuid

from fastapi import APIRouter
from sqlalchemy import Select, func, select
from sqlalchemy.orm import InstrumentedAttribute

from app.api.deps import CurrentUser, DbSession
from app.models import Doctor, Lab, LabReport
from app.schemas.providers import DoctorOut, LabOut

router = APIRouter(tags=["providers"])


def _with_counts[Provider: Lab | Doctor](
    model: type[Provider], column: InstrumentedAttribute[uuid.UUID | None]
) -> Select[tuple[Provider, int]]:
    """Each entity with the number of reports pointing at it, zero included."""
    return (
        select(model, func.count(LabReport.id).label("report_count"))
        .outerjoin(LabReport, column == model.id)
        .group_by(model.id)
        .order_by(func.count(LabReport.id).desc(), model.name)
    )


@router.get("/labs", response_model=list[LabOut])
async def list_labs(user: CurrentUser, db: DbSession) -> list[LabOut]:
    statement = _with_counts(Lab, LabReport.lab_id).where(Lab.user_id == user.id)
    return [
        LabOut(id=lab.id, name=lab.name, report_count=count, created_at=lab.created_at)
        for lab, count in (await db.execute(statement)).all()
    ]


@router.get("/doctors", response_model=list[DoctorOut])
async def list_doctors(user: CurrentUser, db: DbSession) -> list[DoctorOut]:
    statement = _with_counts(Doctor, LabReport.doctor_id).where(Doctor.user_id == user.id)
    return [
        DoctorOut(
            id=doctor.id,
            name=doctor.name,
            specialty=doctor.specialty,
            report_count=count,
            created_at=doctor.created_at,
        )
        for doctor, count in (await db.execute(statement)).all()
    ]
