"""Files on disk, addressed by ids the caller never chooses.

Every path here is built from a user id and a job id — both UUIDs generated
server-side — so no part of a filename ever comes from the upload. Traversal is
not filtered out; it is never given the chance to arrive.
"""

import uuid
from pathlib import Path

from app.core.config import get_settings

PDF_MAGIC = b"%PDF-"


def reports_dir(user_id: uuid.UUID) -> Path:
    return Path(get_settings().storage_path) / "reports" / str(user_id)


def photos_dir(user_id: uuid.UUID) -> Path:
    return Path(get_settings().storage_path) / "photos" / str(user_id)


def _store(directory: Path, name: str, content: bytes) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(content)
    # Health data at rest: the file is the owner's to read, nobody else's.
    path.chmod(0o600)
    return str(path)


def store_pdf(user_id: uuid.UUID, job_id: uuid.UUID, content: bytes) -> str:
    return _store(reports_dir(user_id), f"{job_id}.pdf", content)


def store_photo(user_id: uuid.UUID, photo_id: uuid.UUID, content: bytes) -> str:
    return _store(photos_dir(user_id), f"{photo_id}.jpg", content)


def read_file(file_path: str) -> bytes | None:
    path = Path(file_path)
    return path.read_bytes() if path.is_file() else None


def looks_like_pdf(content: bytes) -> bool:
    """Checked on the bytes, not on the declared content type, which the client
    picks and can be wrong about without meaning any harm."""
    return content.startswith(PDF_MAGIC)


def discard(file_path: str) -> None:
    """Delete a stored upload. Missing is the desired end state, not an error."""
    Path(file_path).unlink(missing_ok=True)
