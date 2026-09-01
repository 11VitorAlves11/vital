import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.biomarker import Biomarker


class ScheduledRepeat(Base):
    """A reminder to repeat one biomarker around a future month.

    Whether it is still pending is never stored: it is read at query time from
    whether a newer result for the same biomarker already exists, the same way
    every other derived fact in this app is recomputed rather than cached (DT6).
    `source_collected_on` is the anchor for that check — snapshotted at creation
    so a schedule outlives the report that prompted it (`source_result_id` may
    go NULL if that report is later deleted; the schedule itself must not).
    """

    __tablename__ = "scheduled_repeats"
    __table_args__ = (
        CheckConstraint("target_month BETWEEN 1 AND 12", name="ck_scheduled_repeats_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    biomarker_id: Mapped[int] = mapped_column(
        ForeignKey("biomarkers.id"), nullable=False, index=True
    )
    #: The result that prompted this reminder. Context only — never read back to
    #: decide whether the schedule is fulfilled, so losing it changes nothing.
    source_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("results.id", ondelete="SET NULL")
    )
    #: Snapshot of that result's collection date. A newer result than this is
    #: what fulfils the schedule.
    source_collected_on: Mapped[date] = mapped_column(Date, nullable=False)
    target_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    biomarker: Mapped[Biomarker] = relationship(lazy="joined")
