"""Everything the server decides about a single result, decided in one place.

A result arrives as a number, a unit and whatever interval the report printed
next to it. What gets stored is that, plus a canonical value, the shape of the
interval and a flag — none of which the client is allowed to supply. Manual
entry, extraction confirmation and re-flagging after a profile change all come
through here, so the three can never drift apart.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.models.biomarker import Biomarker
from app.models.enums import ReferenceKind, ResultFlag, Sex
from app.models.lab_report import Result
from app.services.flags import NO_REFERENCE, bounded, canonical_reference, compute_flag
from app.services.units import to_canonical


@dataclass(frozen=True, slots=True)
class Classification:
    """The derived half of a result row."""

    unit: str
    canonical_value: Decimal | None
    canonical_unit: str | None
    conversion_factor: Decimal | None
    reference_kind: ReferenceKind
    reference_bands: list[dict[str, Any]] | None
    flag: ResultFlag | None


def classify(
    biomarker: Biomarker,
    sex: Sex | None,
    value: Decimal,
    unit: str | None,
    ref_min: Decimal | None,
    ref_max: Decimal | None,
) -> Classification:
    """Derive the stored fields for one reading.

    The interval and the value it is compared against have to be in the same
    unit, and they are not always in the same one: a range printed on the report
    is in the unit the report used, while the catalogue's own bounds and bands
    are canonical. So a catalogue interval is applied to the canonical value, and
    a value we could not convert simply goes unflagged.
    """
    reported_unit = unit or biomarker.unit_default
    canonical_value, canonical_unit, factor = to_canonical(biomarker, value, reported_unit)

    catalogue = canonical_reference(biomarker, sex)
    lab_range_given = ref_min is not None or ref_max is not None

    if catalogue.kind is not ReferenceKind.ORDINAL_BANDS and lab_range_given:
        # The lab's own interval, in the lab's own unit, against the value as printed.
        reference, subject = bounded(ref_min, ref_max), value
    elif canonical_value is not None:
        reference, subject = catalogue, canonical_value
    else:
        reference, subject = NO_REFERENCE, value

    return Classification(
        unit=reported_unit,
        canonical_value=canonical_value,
        canonical_unit=canonical_unit,
        conversion_factor=factor,
        reference_kind=reference.kind,
        # Snapshot: correcting the catalogue later must not reinterpret this draw.
        reference_bands=list(reference.bands) if reference.bands else None,
        flag=compute_flag(subject, reference),
    )


def apply(result: Result, classification: Classification) -> None:
    """Write a classification onto a result row."""
    result.unit = classification.unit
    result.canonical_value = classification.canonical_value
    result.canonical_unit = classification.canonical_unit
    result.conversion_factor = classification.conversion_factor
    result.reference_kind = classification.reference_kind
    result.reference_bands = classification.reference_bands
    result.flag = classification.flag


def build(
    biomarker: Biomarker,
    sex: Sex | None,
    value: Decimal,
    unit: str | None,
    ref_min: Decimal | None,
    ref_max: Decimal | None,
    method: str | None = None,
) -> Result:
    """A new, fully classified result for `biomarker`."""
    result = Result(
        biomarker_id=biomarker.id,
        value=value,
        ref_min=ref_min,
        ref_max=ref_max,
        # Recorded as the report wrote it: what makes two draws comparable or
        # not is which assay produced them, not our normalisation of its name.
        method=method,
    )
    apply(result, classify(biomarker, sex, value, unit, ref_min, ref_max))
    return result
