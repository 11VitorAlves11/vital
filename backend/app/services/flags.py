"""Classification of lab results against a reference range.

Three states only — `low`, `normal`, `high`. There is deliberately no borderline
state: the interval comes from the laboratory itself and there is no clinical basis
for inventing a margin around it.
"""

from decimal import Decimal

from app.models.biomarker import Biomarker
from app.models.enums import ResultFlag, Sex

Range = tuple[Decimal | None, Decimal | None]


def canonical_range(biomarker: Biomarker, sex: Sex | None) -> Range:
    """The catalogue's own range for this user — a fallback, never the primary source."""
    if sex is None:
        return None, None
    if sex is Sex.F:
        return biomarker.ref_min_f, biomarker.ref_max_f
    return biomarker.ref_min_m, biomarker.ref_max_m


def effective_range(
    biomarker: Biomarker,
    sex: Sex | None,
    ref_min: Decimal | None,
    ref_max: Decimal | None,
) -> Range:
    """The lab's range when it reported one, otherwise the catalogue's.

    Ranges vary between laboratories and methods, so a range that came with the
    result always wins — even a one-sided one.
    """
    if ref_min is not None or ref_max is not None:
        return ref_min, ref_max
    return canonical_range(biomarker, sex)


def compute_flag(value: Decimal, reference: Range) -> ResultFlag | None:
    """None when no range is available: an unclassified value is better than a wrong flag."""
    minimum, maximum = reference
    if minimum is None and maximum is None:
        return None
    if minimum is not None and value < minimum:
        return ResultFlag.LOW
    if maximum is not None and value > maximum:
        return ResultFlag.HIGH
    return ResultFlag.NORMAL
