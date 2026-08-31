import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import InterventionKind, Pose, ResultFlag, TimelineKind

#: Events per page. Enough to fill a tall screen twice over, so scrolling
#: usually reaches the next batch before the reader does.
PAGE_SIZE = 40


class TimelineSummaryItem(BaseModel):
    """One line of a card's compact body — a flagged result, a metric reading."""

    label: str
    value: str
    flag: ResultFlag | None = None


class TimelineEvent(BaseModel):
    """One row of the timeline, whatever it is underneath.

    Deliberately flat and already worded for display. The alternative — a union
    the client switches on — puts the same six-way branch in every consumer, and
    the server is the only place that can word "3 fora do intervalo" once.
    """

    #: Unique across kinds, which the id of the underlying row is not.
    id: str
    kind: TimelineKind
    #: The day the timeline sorts and groups by.
    occurred_on: date
    # The hour, only where it means something. A collection at 08:15 is worth
    # showing; the minute an appointment was recorded is noise.
    occurred_at: datetime | None = None
    #: Set only for events with duration. Null on an open-ended one.
    ended_on: date | None = None
    #: True for a period rather than a moment — drawn as a bar, not a node.
    has_duration: bool = False
    title: str
    subtitle: str | None = None
    summary: list[TimelineSummaryItem] = Field(default_factory=list)
    #: Where the full thing lives, or null when the card is all there is.
    href: str | None = None
    #: The specific intervention kind, for the events that have one.
    intervention_kind: InterventionKind | None = None
    pose: Pose | None = None
    photo_id: uuid.UUID | None = None


class TimelineOut(BaseModel):
    events: list[TimelineEvent]
    # The kinds this account actually has anything of. The filter offers these
    # and no others: a control that can only ever return nothing is a dead end.
    available_kinds: list[TimelineKind]
    #: `occurred_on` to continue from, or null at the end of the history.
    next_before: date | None = None
