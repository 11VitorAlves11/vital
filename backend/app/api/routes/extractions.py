"""PDF extraction (v1.1).

The rule the whole module is built around: **no extracted value is ever stored
without human confirmation**. `POST /api/extractions` only ever produces a
preview; `results` rows appear at `confirm`, and only for what the reader
approved there.

Every query is scoped to the session user, jobs and stored files alike.
"""

import hashlib
import logging
import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import or_, select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.api.routes.reports import to_report_out, utcnow
from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import Biomarker, BiomarkerMatchRule, ExtractionJob, LabReport, User
from app.models.enums import ExtractionStatus, ReportSource
from app.schemas.extractions import ExtractionConfirm, ExtractionOut, ExtractionPayload
from app.schemas.reports import ReportOut
from app.services import images, providers, storage
from app.services import results as result_service
from app.services.anonymization import Identity
from app.services.extraction import (
    ExtractionError,
    ask_model,
    build_preview,
    page_contents,
    parse_answer,
)
from app.services.model_credentials import CredentialError, effective_model_config
from app.services.text import normalise

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extractions", tags=["extractions"])


async def _owned_job(job_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ExtractionJob:
    statement = select(ExtractionJob).where(
        ExtractionJob.id == job_id,
        ExtractionJob.user_id == user.id,
        ExtractionJob.kind == "lab",
    )
    job = (await db.execute(statement)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    return job


async def run_extraction(job_id: uuid.UUID) -> None:
    """Read the PDF and park the answer on the job. Runs after the response.

    It opens its own session — the request's is long closed by the time this
    starts — and it never raises: a failure belongs on the job, where the reader
    polling for it can see what happened.
    """
    settings = get_settings()
    async with get_sessionmaker()() as db:
        job = await db.get(ExtractionJob, job_id)
        if job is None or job.kind != "lab":
            return
        job.status = ExtractionStatus.PROCESSING
        try:
            content = storage.read_file(job.file_path)
            if content is None:
                raise ExtractionError("The uploaded file is no longer on disk")
            owner = await db.get(User, job.user_id)
            if owner is None:
                raise ExtractionError("The account no longer exists")
            try:
                model_config = effective_model_config(owner, settings)
            except CredentialError as error:
                raise ExtractionError(str(error)) from error
            if not model_config.enabled:
                raise ExtractionError("Extraction is not configured for this account")
            model_settings = settings.model_copy(
                update={
                    "llm_model": model_config.model,
                    "llm_base_url": model_config.base_url,
                    "llm_api_key": model_config.api_key,
                }
            )
            job.provider = model_config.model
            await db.commit()
            identity = Identity(name=owner.name, email=owner.email, birth_date=owner.birth_date)
            safe_content = page_contents(content, model_settings, identity, job.media_type)
            answer, provider = await ask_model(safe_content, model_settings)
            payload = parse_answer(answer)
        except ExtractionError as error:
            job.status = ExtractionStatus.FAILED
            job.error = str(error)
            await db.commit()
            return
        except Exception:
            # Nothing about the document reaches the log, only that it failed.
            logger.exception("Extraction job %s failed unexpectedly", job_id)
            job.status = ExtractionStatus.FAILED
            job.error = "The extraction failed unexpectedly"
            await db.commit()
            return

        job.provider = provider
        job.raw_output = payload.model_dump(mode="json")
        job.status = ExtractionStatus.PREVIEW
        job.error = None
        await db.commit()


@router.post("", response_model=ExtractionOut, status_code=status.HTTP_202_ACCEPTED)
async def create_extraction(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    replace: Annotated[bool, Query()] = False,
) -> ExtractionOut:
    if not effective_model_config(user, settings).enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Extraction is not configured for this account",
        )

    content = await file.read(settings.upload_max_bytes + 1)
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The file is larger than {settings.upload_max_bytes // (1024 * 1024)} MB",
        )
    media_type = (
        "application/pdf"
        if storage.looks_like_pdf(content)
        else images.detect_media_type(content, settings)
    )
    if media_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, JPEG and PNG files are accepted",
        )

    file_sha256 = hashlib.sha256(content).hexdigest()
    duplicate = await db.scalar(
        select(ExtractionJob).where(
            ExtractionJob.user_id == user.id,
            ExtractionJob.kind == "lab",
            ExtractionJob.file_sha256 == file_sha256,
        )
    )
    if (
        duplicate is not None
        and duplicate.status is not ExtractionStatus.FAILED
        and not replace
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This file has already been imported",
        )

    # A failed provider call did not import anything. Reuse that audit record
    # and its stable storage path so correcting a key or model lets the reader
    # retry the exact document without weakening duplicate protection for jobs
    # that are active, awaiting confirmation, or already confirmed.
    if duplicate is not None:
        # A second click while the same document is already being read should
        # join that work, not start a competing background task for one row.
        if duplicate.status in {ExtractionStatus.PENDING, ExtractionStatus.PROCESSING}:
            return ExtractionOut.model_validate(duplicate)
        duplicate.file_path = storage.store_report_upload(
            user.id, duplicate.id, content, media_type
        )
        duplicate.media_type = media_type
        duplicate.filename = file.filename
        duplicate.status = ExtractionStatus.PENDING
        duplicate.provider = None
        duplicate.raw_output = None
        duplicate.error = None
        await db.commit()
        await db.refresh(duplicate)
        background.add_task(run_extraction, duplicate.id)
        return ExtractionOut.model_validate(duplicate)

    job = ExtractionJob(
        id=uuid.uuid4(),
        user_id=user.id,
        kind="lab",
        file_path="",
        file_sha256=file_sha256,
        media_type=media_type,
        # The upload's own name is stored to show back, never used as a path.
        filename=file.filename,
        status=ExtractionStatus.PENDING,
    )
    job.file_path = storage.store_report_upload(user.id, job.id, content, media_type)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background.add_task(run_extraction, job.id)
    return ExtractionOut.model_validate(job)


@router.get("/{job_id}", response_model=ExtractionOut)
async def read_extraction(job_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ExtractionOut:
    job = await _owned_job(job_id, user, db)
    out = ExtractionOut.model_validate(job)
    if job.status is ExtractionStatus.PREVIEW and job.raw_output is not None:
        # Rebuilt from the stored answer rather than cached, so a catalogue entry
        # added since the job ran now matches a line that did not before.
        biomarkers = (
            (
                await db.execute(
                    select(Biomarker).where(
                        or_(Biomarker.user_id.is_(None), Biomarker.user_id == user.id)
                    )
                )
            )
            .scalars()
            .all()
        )
        extracted_payload = ExtractionPayload.model_validate(job.raw_output)
        rules: Sequence[BiomarkerMatchRule] = []
        if extracted_payload.lab_name:
            rules = (
                (
                    await db.execute(
                        select(BiomarkerMatchRule).where(
                            BiomarkerMatchRule.user_id == user.id,
                            BiomarkerMatchRule.lab_name_normalised
                            == normalise(extracted_payload.lab_name),
                        )
                    )
                )
                .scalars()
                .all()
            )
        out.preview = build_preview(
            extracted_payload,
            list(biomarkers),
            {
                (
                    rule.lab_name_normalised,
                    rule.source_name_normalised,
                    rule.source_unit_normalised,
                ): rule.biomarker_id
                for rule in rules
            },
        )
    return out


@router.post("/{job_id}/confirm", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def confirm_extraction(
    job_id: uuid.UUID, payload: ExtractionConfirm, user: CurrentUser, db: DbSession
) -> ReportOut:
    """Store what the reader approved. The only path from a PDF into `results`."""
    job = await _owned_job(job_id, user, db)
    if job.status is ExtractionStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This extraction was already confirmed"
        )
    if job.status is not ExtractionStatus.PREVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This extraction has no preview to confirm"
        )

    requested = [result.biomarker_id for result in payload.results]
    catalogue = {
        biomarker.id: biomarker
        for biomarker in (
            (
                await db.execute(
                    select(Biomarker).where(
                        Biomarker.id.in_(requested),
                        or_(Biomarker.user_id.is_(None), Biomarker.user_id == user.id),
                    )
                )
            )
            .scalars()
            .all()
        )
    }
    unknown = sorted(set(requested) - catalogue.keys())
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown biomarker ids: {unknown}",
        )

    lab_id = (await providers.lab_for(db, user.id, payload.lab_name)).id
    report = await db.get(LabReport, job.report_id) if job.report_id else None
    if report is not None and report.user_id == user.id:
        # A confirmed duplicate is replaced atomically here, after the person
        # has reviewed the new preview. Until this point the old report remains
        # untouched and usable even when re-extraction fails.
        report.collected_on = payload.collected_on
        report.collected_at = payload.collected_at
        report.lab_id = lab_id
        report.fasting_state = payload.fasting_state
        report.fasting_hours = payload.fasting_hours
        report.notes = payload.notes
        report.notes_at = utcnow() if payload.notes else None
        report.file_path = job.file_path
        report.source = ReportSource.EXTRACTED
        report.results.clear()
        # Remove the old rows before inserting their replacements; the report
        # has a unique biomarker constraint and may contain the same markers.
        await db.flush()
    else:
        report = LabReport(
            user_id=user.id,
            collected_on=payload.collected_on,
            collected_at=payload.collected_at,
            lab_id=lab_id,
            fasting_state=payload.fasting_state,
            fasting_hours=payload.fasting_hours,
            notes=payload.notes,
            notes_at=utcnow() if payload.notes else None,
            # The stored PDF becomes the report's own, so the original stays one
            # click from the values that were read off it.
            file_path=job.file_path,
            source=ReportSource.EXTRACTED,
        )
    for entry in payload.results:
        biomarker = catalogue[entry.biomarker_id]
        if entry.source_name:
            lab_key = normalise(payload.lab_name)
            source_key = normalise(entry.source_name)
            unit_key = normalise(entry.unit) if entry.unit else ""
            rule = await db.scalar(
                select(BiomarkerMatchRule).where(
                    BiomarkerMatchRule.user_id == user.id,
                    BiomarkerMatchRule.lab_name_normalised == lab_key,
                    BiomarkerMatchRule.source_name_normalised == source_key,
                    BiomarkerMatchRule.source_unit_normalised == unit_key,
                )
            )
            known_names = {
                normalise(biomarker.name),
                *(normalise(alias) for alias in biomarker.aliases),
            }
            if rule is None and source_key not in known_names:
                rule = BiomarkerMatchRule(
                    user_id=user.id,
                    biomarker_id=biomarker.id,
                    lab_name=payload.lab_name.strip(),
                    lab_name_normalised=lab_key,
                    source_name=entry.source_name.strip(),
                    source_name_normalised=source_key,
                    source_unit=entry.unit.strip() if entry.unit else None,
                    source_unit_normalised=unit_key,
                )
                db.add(rule)
            elif rule is not None:
                # The latest explicit human confirmation is authoritative.
                rule.biomarker_id = biomarker.id
                rule.lab_name = payload.lab_name.strip()
                rule.source_name = entry.source_name.strip()
                rule.source_unit = entry.unit.strip() if entry.unit else None
        # Flags and unit conversion stay server-side, extracted or not: the model
        # is never asked to classify or convert, only to transcribe.
        report.results.append(
            result_service.build(
                biomarker,
                user.sex,
                entry.value,
                entry.unit,
                entry.ref_min,
                entry.ref_max,
                entry.method,
            )
        )

    db.add(report)
    await db.flush()
    job.status = ExtractionStatus.CONFIRMED
    job.report_id = report.id
    await db.commit()
    await db.refresh(report)
    return await to_report_out(report, user.sex, db)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_extraction(job_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    """Discard a job the reader does not want to confirm.

    A confirmed job keeps its file, because the report it produced links to it.
    """
    job = await _owned_job(job_id, user, db)
    if job.status is not ExtractionStatus.CONFIRMED:
        storage.discard(job.file_path)
    await db.delete(job)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
