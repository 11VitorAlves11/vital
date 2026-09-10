"""Human-confirmed body-composition extraction from photos and screenshots."""

import hashlib
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.api.routes.body import metric_catalogue, to_scan_out
from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import BodyMetric, BodyScan, BodyScanValue, ExtractionJob, User
from app.models.enums import ExtractionStatus, ScanSource
from app.schemas.body import BodyScanOut
from app.schemas.body_extractions import (
    BodyExtractionConfirm,
    BodyExtractionOut,
    BodyExtractionPayload,
)
from app.services import body_extraction, images, storage
from app.services.anonymization import Identity
from app.services.bands import bands_for, classify
from app.services.extraction import ExtractionError, ask_model, page_contents
from app.services.model_credentials import CredentialError, effective_model_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/body/extractions", tags=["body extractions"])


async def _owned(job_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ExtractionJob:
    job = await db.scalar(
        select(ExtractionJob).where(
            ExtractionJob.id == job_id,
            ExtractionJob.user_id == user.id,
            ExtractionJob.kind == "body",
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    return job


async def run_body_extraction(job_id: uuid.UUID) -> None:
    settings = get_settings()
    async with get_sessionmaker()() as db:
        job = await db.get(ExtractionJob, job_id)
        if job is None or job.kind != "body":
            return
        job.status = ExtractionStatus.PROCESSING
        try:
            content = storage.read_file(job.file_path)
            owner = await db.get(User, job.user_id)
            if content is None or owner is None:
                raise ExtractionError("The uploaded file is no longer available")
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
            safe_content = page_contents(
                content,
                model_settings,
                identity,
                job.media_type,
                prompt=body_extraction.PROMPT,
            )
            answer, provider = await ask_model(safe_content, model_settings)
            payload = body_extraction.parse_answer(answer)
        except ExtractionError as error:
            job.status = ExtractionStatus.FAILED
            job.error = str(error)
            await db.commit()
            return
        except Exception:
            logger.exception("Body extraction job %s failed unexpectedly", job_id)
            job.status = ExtractionStatus.FAILED
            job.error = "The extraction failed unexpectedly"
            await db.commit()
            return

        job.provider = provider
        job.raw_output = payload.model_dump(mode="json")
        job.status = ExtractionStatus.PREVIEW
        job.error = None
        await db.commit()


@router.post("", response_model=BodyExtractionOut, status_code=status.HTTP_202_ACCEPTED)
async def create_body_extraction(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
) -> BodyExtractionOut:
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
    media_type = images.detect_media_type(content, settings)
    if media_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG and PNG images are accepted",
        )
    digest = hashlib.sha256(content).hexdigest()
    duplicate = await db.scalar(
        select(ExtractionJob).where(
            ExtractionJob.user_id == user.id,
            ExtractionJob.kind == "body",
            ExtractionJob.file_sha256 == digest,
        )
    )
    if duplicate is not None and duplicate.status is not ExtractionStatus.FAILED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already imported")
    job = duplicate or ExtractionJob(id=uuid.uuid4(), user_id=user.id, file_path="")
    job.kind = "body"
    job.file_sha256 = digest
    job.media_type = media_type
    job.filename = file.filename
    job.status = ExtractionStatus.PENDING
    job.provider = None
    job.raw_output = None
    job.error = None
    job.body_scan_id = None
    job.file_path = storage.store_report_upload(user.id, job.id, content, media_type)
    if duplicate is None:
        db.add(job)
    await db.commit()
    await db.refresh(job)
    background.add_task(run_body_extraction, job.id)
    return BodyExtractionOut.model_validate(job)


@router.get("/{job_id}", response_model=BodyExtractionOut)
async def read_body_extraction(
    job_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> BodyExtractionOut:
    job = await _owned(job_id, user, db)
    output = BodyExtractionOut.model_validate(job)
    if job.status is ExtractionStatus.PREVIEW and job.raw_output is not None:
        metrics = (await db.execute(select(BodyMetric))).scalars().all()
        output.preview = body_extraction.build_preview(
            BodyExtractionPayload.model_validate(job.raw_output), list(metrics)
        )
    return output


@router.post("/{job_id}/confirm", response_model=BodyScanOut, status_code=status.HTTP_201_CREATED)
async def confirm_body_extraction(
    job_id: uuid.UUID, payload: BodyExtractionConfirm, user: CurrentUser, db: DbSession
) -> BodyScanOut:
    job = await _owned(job_id, user, db)
    if job.status is not ExtractionStatus.PREVIEW:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No preview to confirm")
    requested = [item.metric_id for item in payload.values]
    metrics = {
        metric.id: metric
        for metric in (
            (await db.execute(select(BodyMetric).where(BodyMetric.id.in_(requested))))
            .scalars()
            .all()
        )
    }
    unknown = sorted(set(requested) - metrics.keys())
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown body metric ids: {unknown}",
        )
    scan = BodyScan(
        user_id=user.id,
        measured_at=payload.measured_at,
        device=payload.device,
        notes=payload.notes,
        source=ScanSource.IMPORT,
    )
    for item in payload.values:
        metric = metrics[item.metric_id]
        flag, _ = classify(item.value, bands_for(metric, user.sex))
        scan.values.append(BodyScanValue(metric_id=metric.id, value=item.value, flag=flag))
    db.add(scan)
    await db.flush()
    job.status = ExtractionStatus.CONFIRMED
    job.body_scan_id = scan.id
    await db.commit()
    await db.refresh(scan)
    return to_scan_out(scan, user, await metric_catalogue(db))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_body_extraction(job_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    job = await _owned(job_id, user, db)
    if job.status is not ExtractionStatus.CONFIRMED:
        storage.discard(job.file_path)
    await db.delete(job)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
