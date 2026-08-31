"""Lab-result classification against a reference interval."""

from decimal import Decimal

import pytest

from app.models.biomarker import Biomarker
from app.models.enums import BiomarkerCategory, ReferenceKind, ResultFlag, Sex
from app.services.flags import band_label, bounded, canonical_reference, compute_flag

FERRITIN = Biomarker(
    slug="ferritina",
    name="Ferritina",
    category=BiomarkerCategory.FERRO,
    unit_default="ng/mL",
    canonical_unit="ng/mL",
    unit_conversions={},
    reference_kind=ReferenceKind.TWO_SIDED,
    ref_min_m=Decimal("30"),
    ref_max_m=Decimal("400"),
    ref_min_f=Decimal("15"),
    ref_max_f=Decimal("150"),
    aliases=["Ferritina sérica"],
)

VITAMIN_D = Biomarker(
    slug="vitamin-d-25-oh",
    name="Vitamina D (25-OH)",
    category=BiomarkerCategory.VITAMINAS,
    unit_default="ng/mL",
    canonical_unit="ng/mL",
    unit_conversions={"nmol/L": 0.4006},
    reference_kind=ReferenceKind.ORDINAL_BANDS,
    ordinal_bands=[
        {"label": "deficiência", "min": None, "max": 20, "flag": "low"},
        {"label": "insuficiência", "min": 20, "max": 30, "flag": "low"},
        {"label": "suficiência", "min": 30, "max": 100, "flag": "normal"},
        {"label": "excesso", "min": 100, "max": None, "flag": "high"},
    ],
    aliases=["25-OH-D"],
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
    reference = bounded(Decimal("30"), Decimal("400"))
    assert compute_flag(Decimal(value), reference) is expected


def test_no_range_means_no_flag() -> None:
    """An unclassified value is honest; a green chip against nothing is not."""
    assert compute_flag(Decimal("12"), bounded(None, None)) is None


def test_bounds_name_the_shape_they_form() -> None:
    assert bounded(Decimal("1"), Decimal("2")).kind is ReferenceKind.TWO_SIDED
    assert bounded(None, Decimal("2")).kind is ReferenceKind.UPPER_BOUND
    assert bounded(Decimal("1"), None).kind is ReferenceKind.LOWER_BOUND
    assert bounded(None, None).kind is ReferenceKind.NONE


def test_a_lower_bound_never_flags_a_value_as_high() -> None:
    """HDL > 40 says nothing about how high is too high."""
    reference = bounded(Decimal("40"), None)
    assert compute_flag(Decimal("39"), reference) is ResultFlag.LOW
    assert compute_flag(Decimal("95"), reference) is ResultFlag.NORMAL


def test_an_upper_bound_never_flags_a_value_as_low() -> None:
    """ALT < 56 says nothing about how low is too low."""
    reference = bounded(None, Decimal("56"))
    assert compute_flag(Decimal("3"), reference) is ResultFlag.NORMAL
    assert compute_flag(Decimal("57"), reference) is ResultFlag.HIGH


def test_canonical_reference_follows_sex() -> None:
    assert canonical_reference(FERRITIN, Sex.M).minimum == Decimal("30")
    assert canonical_reference(FERRITIN, Sex.M).maximum == Decimal("400")
    assert canonical_reference(FERRITIN, Sex.F).minimum == Decimal("15")
    assert canonical_reference(FERRITIN, Sex.F).maximum == Decimal("150")


def test_canonical_reference_is_withheld_when_sex_is_unknown() -> None:
    reference = canonical_reference(FERRITIN, None)
    assert reference.kind is ReferenceKind.NONE
    assert (reference.minimum, reference.maximum) == (None, None)


@pytest.mark.parametrize(
    ("value", "flag", "label"),
    [
        ("8", ResultFlag.LOW, "deficiência"),
        ("20", ResultFlag.LOW, "insuficiência"),
        ("29.9", ResultFlag.LOW, "insuficiência"),
        ("30", ResultFlag.NORMAL, "suficiência"),
        ("31", ResultFlag.NORMAL, "suficiência"),
        ("140", ResultFlag.HIGH, "excesso"),
    ],
)
def test_ordinal_bands_classify_and_name_the_step(value: str, flag: ResultFlag, label: str) -> None:
    reference = canonical_reference(VITAMIN_D, Sex.M)
    assert reference.kind is ReferenceKind.ORDINAL_BANDS
    assert compute_flag(Decimal(value), reference) is flag
    assert band_label(Decimal(value), reference) == label


def test_ordinal_bands_do_not_need_a_known_sex() -> None:
    """The scale is a clinical consensus, not a sex-specific range."""
    assert canonical_reference(VITAMIN_D, None).kind is ReferenceKind.ORDINAL_BANDS


def test_a_bounded_reference_has_no_band_label() -> None:
    assert band_label(Decimal("100"), bounded(Decimal("30"), Decimal("400"))) is None
