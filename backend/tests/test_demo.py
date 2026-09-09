from sqlalchemy import func, select

from app.core.security import verify_password
from app.db.demo import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_account
from app.db.session import get_sessionmaker
from app.models import BodyScan, Intervention, LabReport, Result, User


async def test_demo_seed_is_rich_idempotent_and_has_known_login(database: None) -> None:
    async with get_sessionmaker()() as db:
        existing = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing is not None:
            await db.delete(existing)
            await db.commit()

        assert await seed_demo_account(db) is True
        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        assert user is not None
        assert user.password_hash is not None
        assert verify_password(DEMO_PASSWORD, user.password_hash)

        reports = await db.scalar(
            select(func.count(LabReport.id)).where(LabReport.user_id == user.id)
        )
        results = await db.scalar(
            select(func.count(Result.id)).join(LabReport).where(LabReport.user_id == user.id)
        )
        scans = await db.scalar(select(func.count(BodyScan.id)).where(BodyScan.user_id == user.id))
        interventions = await db.scalar(
            select(func.count(Intervention.id)).where(Intervention.user_id == user.id)
        )
        assert (reports, results, scans, interventions) == (8, 96, 12, 4)

        assert await seed_demo_account(db) is False
        assert (
            await db.scalar(select(func.count(LabReport.id)).where(LabReport.user_id == user.id))
        ) == 8

        await db.delete(user)
        await db.commit()
