"""Conversion of a reported value into the catalogue's canonical unit."""

from decimal import Decimal

import pytest

from app.models.biomarker import Biomarker
from app.models.enums import BiomarkerCategory, ReferenceKind, ResultFlag, Sex
from app.services import results as result_service
from app.services.units import normalise_unit, to_canonical

B12 = Biomarker(
    id=1,
    slug="vitamin-b12",
    name="Vitamina B12",
    category=BiomarkerCategory.VITAMINAS,
    unit_default="pg/mL",
    canonical_unit="pg/mL",
    unit_conversions={"pmol/L": 1.355, "ng/L": 1},
    reference_kind=ReferenceKind.TWO_SIDED,
    ref_min_m=Decimal("200"),
    ref_max_m=Decimal("900"),
    ref_min_f=Decimal("200"),
    ref_max_f=Decimal("900"),
    aliases=["Cobalamina"],
)

VITAMIN_D = Biomarker(
    id=2,
    slug="vitamin-d-25-oh",
    name="Vitamina D (25-OH)",
    category=BiomarkerCategory.VITAMINAS,
    unit_default="ng/mL",
    canonical_unit="ng/mL",
    unit_conversions={"nmol/L": 0.4006},
    reference_kind=ReferenceKind.ORDINAL_BANDS,
    ordinal_bands=[
        {"label": "insuficiência", "min": None, "max": 30, "flag": "low"},
        {"label": "suficiência", "min": 30, "max": 100, "flag": "normal"},
        {"label": "excesso", "min": 100, "max": None, "flag": "high"},
    ],
    aliases=["25-OH-D"],
)


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ("ng/mL", "ng/ml"),
        (" ng / mL ", "ng/ml"),
        ("μmol/L", "µmol/l"),  # Greek mu
        ("umol/L", "µmol/l"),  # ASCII stand-in
        ("ug/dL", "µg/dl"),
        ("10^3/uL", "10^3/µl"),
    ],
)
def test_notation_differences_are_folded(written: str, expected: str) -> None:
    assert normalise_unit(written) == expected


@pytest.mark.parametrize("written", ["U/L", "UI/L", "µUI/mL"])
def test_a_unit_of_activity_is_not_read_as_micro(written: str) -> None:
    """`U` is an enzyme or international unit; rewriting it as `µ` would be a
    different quantity entirely."""
    assert "µ" not in normalise_unit(written).replace("µu", "")
    assert normalise_unit(written).startswith(("u", "µu", "m"))


def test_the_canonical_unit_converts_to_itself() -> None:
    value, unit, factor = to_canonical(B12, Decimal("450"), "pg/mL")
    assert (value, unit, factor) == (Decimal("450"), "pg/mL", Decimal(1))


def test_a_known_unit_is_converted_exactly() -> None:
    value, unit, factor = to_canonical(B12, Decimal("300"), "pmol/L")
    assert unit == "pg/mL"
    assert factor == Decimal("1.355")
    # Through Decimal, not float: 300 × 1.355 is 406.5 and nothing near it.
    assert value == Decimal("406.500")


def test_an_unknown_unit_is_not_guessed_at() -> None:
    """Ten times the real value is worse than no canonical value at all."""
    assert to_canonical(B12, Decimal("300"), "mg/dL") == (None, None, None)


def test_a_missing_unit_is_read_as_the_canonical_one() -> None:
    value, unit, _ = to_canonical(B12, Decimal("450"), None)
    assert (value, unit) == (Decimal("450"), "pg/mL")


def test_a_series_stays_continuous_across_a_change_of_unit() -> None:
    """The point of 1.3: the same blood, reported two ways, plots as one line."""
    in_pg = result_service.classify(B12, Sex.M, Decimal("406.5"), "pg/mL", None, None)
    in_pmol = result_service.classify(B12, Sex.M, Decimal("300"), "pmol/L", None, None)
    assert in_pg.canonical_value == in_pmol.canonical_value
    assert in_pg.flag is in_pmol.flag is ResultFlag.NORMAL


def test_the_reported_value_is_never_rewritten() -> None:
    classified = result_service.classify(B12, Sex.M, Decimal("300"), "pmol/L", None, None)
    result = result_service.build(B12, Sex.M, Decimal("300"), "pmol/L", None, None)
    assert (result.value, result.unit) == (Decimal("300"), "pmol/L")
    assert result.canonical_value == classified.canonical_value


def test_a_catalogue_range_is_applied_to_the_converted_value() -> None:
    """150 pmol/L is 203 pg/mL — normal — even though 150 is under the range."""
    classified = result_service.classify(B12, Sex.M, Decimal("150"), "pmol/L", None, None)
    assert classified.flag is ResultFlag.NORMAL


def test_an_unconvertible_value_goes_unflagged() -> None:
    classified = result_service.classify(B12, Sex.M, Decimal("300"), "mg/dL", None, None)
    assert classified.canonical_value is None
    assert classified.reference_kind is ReferenceKind.NONE
    assert classified.flag is None


def test_the_labs_own_range_is_read_in_the_labs_own_unit() -> None:
    """A range printed next to the value shares its unit, so neither is converted."""
    classified = result_service.classify(
        B12, Sex.M, Decimal("300"), "pmol/L", Decimal("145"), Decimal("569")
    )
    assert classified.reference_kind is ReferenceKind.TWO_SIDED
    assert classified.flag is ResultFlag.NORMAL


def test_ordinal_bands_are_snapshotted_onto_the_result() -> None:
    classified = result_service.classify(VITAMIN_D, Sex.M, Decimal("70"), "nmol/L", None, None)
    assert classified.reference_kind is ReferenceKind.ORDINAL_BANDS
    assert classified.reference_bands == VITAMIN_D.ordinal_bands
    # 70 nmol/L is 28.04 ng/mL — under the sufficiency threshold.
    assert classified.flag is ResultFlag.LOW
