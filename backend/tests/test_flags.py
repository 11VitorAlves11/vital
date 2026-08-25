"""Lab-result classification against a reference range."""

from decimal import Decimal

import pytest

from app.models.biomarker import Biomarker
from app.models.enums import BiomarkerCategory, ResultFlag, Sex
from app.services.flags import canonical_range, compute_flag, effective_range

FERRITIN = Biomarker(
    slug="ferritina",
    name="Ferritina",
    category=BiomarkerCategory.FERRO,
    unit_default="ng/mL",
    ref_min_m=Decimal("30"),
    ref_max_m=Decimal("400"),
    ref_min_f=Decimal("15"),
    ref_max_f=Decimal("150"),
    aliases=["Ferritina sérica"],
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("29.9", ResultFlag.LOW),
        ("30", ResultFlag.NORMAL),  # both limits are inclusive for lab ranges
        ("400", ResultFlag.NORMAL),
        ("400.1", ResultFlag.HIGH),
    ],
)
def test_flag_at_the_limits(value: str, expected: ResultFlag) -> None:
    assert compute_flag(Decimal(value), (Decimal("30"), Decimal("400"))) is expected


def test_no_range_means_no_flag() -> None:
    """An unclassified value is honest; a green chip against nothing is not."""
    assert compute_flag(Decimal("12"), (None, None)) is None


def test_one_sided_range_still_classifies() -> None:
    assert compute_flag(Decimal("5"), (Decimal("10"), None)) is ResultFlag.LOW
    assert compute_flag(Decimal("50"), (Decimal("10"), None)) is ResultFlag.NORMAL


def test_canonical_range_follows_sex() -> None:
    assert canonical_range(FERRITIN, Sex.M) == (Decimal("30"), Decimal("400"))
    assert canonical_range(FERRITIN, Sex.F) == (Decimal("15"), Decimal("150"))


def test_canonical_range_is_withheld_when_sex_is_unknown() -> None:
    assert canonical_range(FERRITIN, None) == (None, None)


def test_the_labs_own_range_wins_over_the_catalogue() -> None:
    """Ranges differ between labs and methods, so the one that came with the
    result is the one the result is judged against."""
    reference = effective_range(FERRITIN, Sex.F, Decimal("20"), Decimal("200"))
    assert reference == (Decimal("20"), Decimal("200"))
    assert compute_flag(Decimal("180"), reference) is ResultFlag.NORMAL


def test_a_one_sided_lab_range_is_not_topped_up_from_the_catalogue() -> None:
    assert effective_range(FERRITIN, Sex.F, None, Decimal("200")) == (None, Decimal("200"))


def test_catalogue_is_the_fallback_when_the_lab_reported_nothing() -> None:
    assert effective_range(FERRITIN, Sex.F, None, None) == (Decimal("15"), Decimal("150"))
