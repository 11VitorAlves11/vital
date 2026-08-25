"""Progress photos (v1.1).

Two rules shape the module. The image is re-encoded on the way in, so what the
camera wrote beside it — where, on what, at what second — never reaches disk.
And the file only ever comes back through this router, behind the session: a
photo of someone's body is never served from a static path.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.models import ProgressPhoto
from app.models.enums import Pose
from app.schemas.photos import PhotoOut
from app.services import images, storage

router = APIRouter(prefix="/photos", tags=["photos"])


async def _owned_photo(photo_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ProgressPhoto:
    statement = select(ProgressPhoto).where(
        ProgressPhoto.id == photo_id, ProgressPhoto.user_id == user.id
    )
    photo = (await db.execute(statement)).scalar_one_or_none()
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return photo


@router.get("", response_model=list[PhotoOut])
async def list_photos(
    user: CurrentUser,
    db: DbSession,
    pose: Pose | None = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> list[ProgressPhoto]:
    statement = (
        select(ProgressPhoto)
        .where(ProgressPhoto.user_id == user.id)
        .order_by(ProgressPhoto.taken_on.desc(), ProgressPhoto.created_at.desc())
    )
    if pose is not None:
        statement = statement.where(ProgressPhoto.pose == pose)
    if date_from is not None:
        statement = statement.where(ProgressPhoto.taken_on >= date_from)
    if date_to is not None:
        statement = statement.where(ProgressPhoto.taken_on <= date_to)
    return list((await db.execute(statement)).scalars().all())


@router.post("", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def create_photo(
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    taken_on: Annotated[date, Form()],
    pose: Annotated[Pose, Form()] = Pose.FRENTE,
    notes: Annotated[str | None, Form()] = None,
) -> ProgressPhoto:
    content = await file.read(settings.upload_max_bytes + 1)
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The file is larger than {settings.upload_max_bytes // (1024 * 1024)} MB",
        )

    try:
        # Decoding is also the validation: a file Pillow cannot open is not an
        # image, whatever its name or declared type says.
        encoded, width, height = images.process(content, settings)
    except images.ImageError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(error)
        ) from error

    photo = ProgressPhoto(
        id=uuid.uuid4(),
        user_id=user.id,
        taken_on=taken_on,
        pose=pose,
        file_path="",
        width=width,
        height=height,
        notes=notes or None,
    )
    photo.file_path = storage.store_photo(user.id, photo.id, encoded)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


@router.get("/{photo_id}/file")
async def read_photo_file(photo_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    photo = await _owned_photo(photo_id, user, db)
    content = storage.read_file(photo.file_path)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo file missing")
    return Response(
        content=content,
        media_type="image/jpeg",
        # private, so no proxy in front of a self-hosted instance keeps a copy
        # of someone's body in a shared cache.
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    photo = await _owned_photo(photo_id, user, db)
    storage.discard(photo.file_path)
    await db.delete(photo)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
