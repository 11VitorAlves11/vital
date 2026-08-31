"""Re-flag everything a user owns.

Reference ranges and clinical bands are sex-specific, so correcting a profile has
to correct the history with it — otherwise old results keep a flag that the same
value would no longer get today. The same argument applies to the catalogue: a
band or a conversion factor corrected in seed/ has to reach the results already
stored, not only the next ones, which is why the whole instance is re-flagged
after the catalogue loads at start-up.

None of this touches a value or a range the laboratory reported. Only what the
server derived from them is rebuilt.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BodyScan, BodyScanValue, LabReport, Result, User
from app.services import results as result_service
from app.services.bands import bands_for, classify


async def recompute_user_flags(db: AsyncSession, user: User) -> None:
    results = (
        (await db.execute(select(Result).join(LabReport).where(LabReport.user_id == user.id)))
        .scalars()
        .all()
    )
    for result in results:
        result_service.apply(
            result,
            result_service.classify(
                result.biomarker,
                user.sex,
                result.value,
                result.unit,
                result.ref_min,
                result.ref_max,
            ),
        )

    values = (
        (await db.execute(select(BodyScanValue).join(BodyScan).where(BodyScan.user_id == user.id)))
        .scalars()
        .all()
    )
    for value in values:
        flag, _ = classify(value.value, bands_for(value.metric, user.sex))
        value.flag = flag


async def recompute_every_users_flags(db: AsyncSession) -> int:
    """Re-flag the whole instance against the catalogue as it stands now.

    Returns the number of accounts visited. Cheap enough to run on every boot of
    a self-hosted instance, and it is the only thing that keeps a corrected
    catalogue from applying to new draws alone.
    """
    users = (await db.execute(select(User))).scalars().all()
    for user in users:
        await recompute_user_flags(db, user)
    await db.commit()
    return len(users)
