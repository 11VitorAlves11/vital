"""Rich synthetic data for the explicitly enabled local demo account."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models import (
    Biomarker,
    BodyMetric,
    BodyScan,
    BodyScanValue,
    Doctor,
    Intervention,
    Lab,
    LabReport,
    ScheduledRepeat,
    User,
)
from app.models.enums import FastingState, InterventionKind, ReportSource, ScanSource, Sex
from app.services import results as result_service
from app.services.bands import bands_for, classify
from app.services.text import normalise

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "VitalDemo2026!"


async def seed_demo_account(db: AsyncSession) -> bool:
    """Create the local demo once; keep its known login valid on every boot.

    Returns true only when the synthetic history was populated. Existing demo
    edits survive restarts, while deleting the account makes the next boot
    recreate the complete dataset.
    """
    user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            name="Conta Demo",
            sex=Sex.M,
            birth_date=date(1988, 6, 15),
            height_cm=Decimal("175.0"),
        )
        db.add(user)
        await db.flush()
    else:
        if not user.password_hash or not verify_password(DEMO_PASSWORD, user.password_hash):
            user.password_hash = hash_password(DEMO_PASSWORD)
        user.name = user.name or "Conta Demo"
        user.sex = user.sex or Sex.M
        user.birth_date = user.birth_date or date(1988, 6, 15)
        user.height_cm = user.height_cm or Decimal("175.0")

    report_count = await db.scalar(
        select(func.count(LabReport.id)).where(LabReport.user_id == user.id)
    )
    if report_count:
        await db.commit()
        return False

    labs = [
        Lab(user_id=user.id, name=name, normalised_name=normalise(name))
        for name in ("Laboratório Central", "Clínica do Parque")
    ]
    doctor = Doctor(
        user_id=user.id,
        name="Dra. Sofia Martins",
        normalised_name=normalise("Dra. Sofia Martins"),
        specialty="Medicina Geral e Familiar",
    )
    db.add_all([*labs, doctor])
    await db.flush()

    biomarkers = {item.slug: item for item in (await db.execute(select(Biomarker))).scalars().all()}
    draws = [
        (date(2024, 1, 18), [14.8, 46, 205, 132, 43, 151, 98, 5.6, 28, 3.2, 1.12, 32]),
        (date(2024, 5, 23), [14.6, 45, 198, 124, 46, 139, 94, 5.4, 31, 3.0, 1.08, 28]),
        (date(2024, 10, 10), [14.4, 44, 187, 113, 49, 126, 91, 5.2, 35, 2.7, 1.04, 24]),
        (date(2025, 2, 20), [14.5, 44, 180, 105, 52, 115, 89, 5.1, 38, 2.4, 1.02, 21]),
        (date(2025, 6, 19), [14.7, 45, 176, 101, 54, 104, 87, 5.0, 42, 2.1, 1.00, 18]),
        (date(2025, 10, 16), [14.8, 45, 171, 96, 57, 91, 86, 4.9, 46, 1.9, 0.98, 16]),
        (date(2026, 2, 12), [14.9, 46, 168, 92, 59, 84, 84, 4.8, 49, 1.7, 0.96, 14]),
        (date(2026, 7, 9), [15.0, 46, 165, 89, 61, 75, 83, 4.8, 52, 1.5, 0.95, 12]),
    ]
    slugs = (
        "hemoglobina",
        "hematocrito",
        "colesterol-total",
        "ldl",
        "hdl",
        "triglicerideos",
        "glicose",
        "hba1c",
        "vitamin-d-25-oh",
        "tsh",
        "creatinina",
        "pcr",
    )
    latest_results = {}
    for index, (collected_on, values) in enumerate(draws):
        report = LabReport(
            user_id=user.id,
            collected_on=collected_on,
            collected_at=datetime.combine(collected_on, datetime.min.time()).replace(
                hour=8, minute=15
            ),
            lab_id=labs[index % len(labs)].id,
            doctor_id=doctor.id,
            fasting_state=FastingState.FASTING,
            fasting_hours=12,
            source=ReportSource.MANUAL,
            notes="Dados sintéticos para demonstração. Não representam uma pessoa real.",
        )
        for slug, raw_value in zip(slugs, values, strict=True):
            marker = biomarkers[slug]
            result = result_service.build(
                marker,
                user.sex,
                Decimal(str(raw_value)),
                marker.unit_default,
                None,
                None,
                "Método sintético",
            )
            report.results.append(result)
            latest_results[slug] = result
        db.add(report)

    metrics = {item.slug: item for item in (await db.execute(select(BodyMetric))).scalars().all()}
    body_rows = [
        (date(2025, 8, 3), 84.2, 25.8, 94.0, 58.4, 50.2, 11),
        (date(2025, 9, 7), 83.1, 25.1, 92.5, 58.6, 50.8, 11),
        (date(2025, 10, 5), 81.9, 24.4, 91.0, 58.9, 51.5, 10),
        (date(2025, 11, 2), 80.8, 23.8, 89.5, 59.1, 52.0, 10),
        (date(2025, 12, 7), 79.7, 23.1, 88.0, 59.4, 52.6, 9),
        (date(2026, 1, 4), 78.9, 22.6, 86.5, 59.7, 53.1, 9),
        (date(2026, 2, 8), 78.1, 22.0, 85.0, 60.0, 53.7, 8),
        (date(2026, 3, 8), 77.5, 21.5, 84.0, 60.2, 54.1, 8),
        (date(2026, 4, 5), 76.9, 21.0, 83.0, 60.4, 54.5, 8),
        (date(2026, 5, 3), 76.4, 20.7, 82.0, 60.6, 54.8, 7),
        (date(2026, 6, 7), 75.9, 20.3, 81.0, 60.8, 55.1, 7),
        (date(2026, 7, 5), 75.5, 20.0, 80.5, 61.0, 55.4, 7),
    ]
    metric_slugs = (
        "weight",
        "body-fat-pct",
        "waist-circumference",
        "fat-free-mass",
        "water-pct",
        "visceral-fat-index",
    )
    for measured_on, *values in body_rows:
        scan = BodyScan(
            user_id=user.id,
            measured_at=datetime(
                measured_on.year, measured_on.month, measured_on.day, 7, 30, tzinfo=UTC
            ),
            source=ScanSource.MANUAL,
            device="Balança demo",
            notes="Medição sintética em condições consistentes.",
        )
        for slug, raw_value in zip(metric_slugs, values, strict=True):
            metric = metrics[slug]
            value = Decimal(str(raw_value))
            flag, _ = classify(value, bands_for(metric, user.sex))
            scan.values.append(BodyScanValue(metric_id=metric.id, value=value, flag=flag))
        db.add(scan)

    db.add_all(
        [
            Intervention(
                user_id=user.id,
                kind=InterventionKind.DIETA,
                name="Plano alimentar",
                started_on=date(2025, 8, 1),
                notes="Exemplo sintético.",
            ),
            Intervention(
                user_id=user.id,
                kind=InterventionKind.TREINO,
                name="Treino de força",
                dose="3 vezes/semana",
                started_on=date(2025, 9, 1),
                notes="Exemplo sintético.",
            ),
            Intervention(
                user_id=user.id,
                kind=InterventionKind.SUPLEMENTO,
                name="Vitamina D3",
                dose="2000 UI/dia",
                started_on=date(2024, 11, 1),
                ended_on=date(2026, 3, 31),
                notes="Exemplo sintético.",
            ),
            Intervention(
                user_id=user.id,
                kind=InterventionKind.OUTRO,
                name="Rotina de sono",
                dose="7–8 horas",
                started_on=date(2025, 1, 15),
                notes="Exemplo sintético.",
            ),
        ]
    )
    await db.flush()
    source = latest_results["vitamin-d-25-oh"]
    db.add(
        ScheduledRepeat(
            user_id=user.id,
            biomarker_id=source.biomarker_id,
            source_result_id=source.id,
            source_collected_on=draws[-1][0],
            target_year=2027,
            target_month=1,
            note="Repetir vitamina D no inverno (exemplo sintético).",
        )
    )
    await db.commit()
    return True
