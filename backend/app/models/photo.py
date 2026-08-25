import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import Pose, pg_enum


class ProgressPhoto(Base):
    """A photo of the body over time, stored stripped of everything but pixels.

    What the camera wrote alongside the image — where it was taken, on what, at
    what second — is not part of what the reader asked to keep, and a photo of
    someone's body is the last file that should carry their home address.
    """

    __tablename__ = "progress_photos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    taken_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    pose: Mapped[Pose] = mapped_column(pg_enum(Pose, "pose"), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
