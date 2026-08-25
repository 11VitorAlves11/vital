"""Re-flag everything a user owns.

Reference ranges and clinical bands are sex-specific, so correcting a profile has
to correct the history with it — otherwise old results keep a flag that the same
value would no longer get today.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BodyScan, BodyScanValue, LabReport, Result, User
from app.services.bands import bands_for, classify
from app.services.flags import compute_flag, effective_range


async def recompute_user_flags(db: AsyncSession, user: User) -> None:
    results = (
        (await db.execute(select(Result).join(LabReport).where(LabReport.user_id == user.id)))
        .scalars()
        .all()
    )
    for result in results:
        reference = effective_range(result.biomarker, user.sex, result.ref_min, result.ref_max)
        result.flag = compute_flag(result.value, reference)

    values = (
        (await db.execute(select(BodyScanValue).join(BodyScan).where(BodyScan.user_id == user.id)))
        .scalars()
        .all()
    )
    for value in values:
        flag, _ = classify(value.value, bands_for(value.metric, user.sex))
        value.flag = flag
