"""Band classification, without a database in the way.

The `[min, max)` convention is the whole reason these tests exist: a value exactly
on a limit belongs to the band above, and getting that wrong misclassifies people
sitting precisely on a clinical threshold.
"""

import json
from decimal import Decimal

import pytest

from app.db.seed import seed_dir
from app.models.body import BodyMetric
from app.models.enums import Sex
from app.services.bands import age_band_for, bands_for, classify

BMI_BANDS = [
    {"label": "Baixo peso", "min": None, "max": 18.5, "flag": "warn"},
    {"label": "Normal", "min": 18.5, "max": 25.0, "flag": "normal"},
    {"label": "Pré-obesidade", "min": 25.0, "max": 30.0, "flag": "warn"},
    {"label": "Obesidade grau III", "min": 40.0, "max": None, "flag": "alert"},
]


@pytest.mark.parametrize(
    ("value", "expected_flag", "expected_label"),
    [
        ("18.49", "warn", "Baixo peso"),
        ("18.5", "normal", "Normal"),  # lower limit is inclusive
        ("24.999", "normal", "Normal"),
        ("25", "warn", "Pré-obesidade"),  # upper limit is exclusive
        ("29.95", "warn", "Pré-obesidade"),
        ("40", "alert", "Obesidade grau III"),
        ("120", "alert", "Obesidade grau III"),
    ],
)
def test_band_limits_are_min_inclusive_max_exclusive(
    value: str, expected_flag: str, expected_label: str
) -> None:
    assert classify(Decimal(value), BMI_BANDS) == (expected_flag, expected_label)


def test_value_outside_every_band_is_not_classified() -> None:
    gapped = [{"label": "Só isto", "min": 10.0, "max": 20.0, "flag": "normal"}]
    assert classify(Decimal("21"), gapped) == (None, None)


def test_trend_only_metric_is_never_classified() -> None:
    assert classify(Decimal("74.2"), None) == (None, None)


def test_bands_are_picked_by_sex() -> None:
    metric = BodyMetric(
        slug="body-fat-pct",
        name="Gordura corporal",
        unit="%",
        bands_m=[{"label": "M", "min": None, "max": None, "flag": "normal"}],
        bands_f=[{"label": "F", "min": None, "max": None, "flag": "normal"}],
    )
    assert bands_for(metric, Sex.M) == metric.bands_m
    assert bands_for(metric, Sex.F) == metric.bands_f


def test_unknown_sex_yields_no_bands() -> None:
    """Guessing would mean applying the wrong standard and calling it a finding."""
    metric = BodyMetric(slug="bmi", name="IMC", unit="kg/m²", bands_m=BMI_BANDS, bands_f=BMI_BANDS)
    assert bands_for(metric, None) is None


def _seed_metric(slug: str) -> dict[str, object]:
    entries = json.loads((seed_dir() / "body_metrics.json").read_text(encoding="utf-8"))
    return next(entry for entry in entries if entry["slug"] == slug)


@pytest.mark.parametrize(
    ("slug", "sex", "value", "expected_flag", "expected_label"),
    [
        ("bmi", "bands_m", "27", "warn", "Pré-obesidade"),
        ("bmi", "bands_f", "22", "normal", "Normal"),
        ("bmi", "bands_m", "36", "alert", "Obesidade grau II"),
        ("waist-circumference", "bands_m", "96", "warn", "Risco aumentado"),
        ("waist-circumference", "bands_f", "79", "normal", "Sem risco acrescido"),
        ("ffmi", "bands_m", "16.4", "alert", "Massa magra reduzida"),
    ],
)
def test_seeded_bands_classify_against_their_published_standard(
    slug: str, sex: str, value: str, expected_flag: str, expected_label: str
) -> None:
    bands = _seed_metric(slug)[sex]
    assert classify(Decimal(value), bands) == (expected_flag, expected_label)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("sex", "value", "expected_label"),
    [
        ("bands_m", "10", "Atleta"),
        ("bands_m", "1.5", "Abaixo do essencial"),
        ("bands_f", "33", "Obesidade"),
    ],
)
def test_the_body_fat_scale_names_without_judging(
    sex: str, value: str, expected_label: str
) -> None:
    """The ACE categories are fitness classes, not clinical ones (decision D1).

    They still name the reading — the reader gets "Atleta" — but they no longer
    produce a flag, because a bioimpedance estimate against a fitness scale is
    not a verdict on anyone's health.
    """
    bands = _seed_metric("body-fat-pct")[sex]
    assert classify(Decimal(value), bands) == (None, expected_label)  # type: ignore[arg-type]


AGE_BRACKETS = [
    {
        "age_min": 20,
        "age_max": 30,
        "bands": [
            {"label": "Abaixo do percentil 10", "min": None, "max": 22.1, "flag": None},
            {"label": "Percentil 10–20", "min": 22.1, "max": 24.5, "flag": None},
            {"label": "Acima do percentil 90", "min": 43.2, "max": None, "flag": None},
        ],
    },
    {
        "age_min": 30,
        "age_max": 40,
        "bands": [{"label": "Percentil 50–60", "min": 29.9, "max": 32.1, "flag": None}],
    },
]


def test_age_band_picks_the_bracket_the_age_falls_in() -> None:
    metric = BodyMetric(
        slug="body-fat-pct", name="Gordura corporal", unit="%", age_bands_f=AGE_BRACKETS
    )
    assert age_band_for(metric, Sex.F, 25) == AGE_BRACKETS[0]["bands"]
    assert age_band_for(metric, Sex.F, 35) == AGE_BRACKETS[1]["bands"]


def test_age_band_bracket_limits_are_min_inclusive_max_exclusive() -> None:
    metric = BodyMetric(
        slug="body-fat-pct", name="Gordura corporal", unit="%", age_bands_f=AGE_BRACKETS
    )
    assert age_band_for(metric, Sex.F, 29) == AGE_BRACKETS[0]["bands"]
    assert age_band_for(metric, Sex.F, 30) == AGE_BRACKETS[1]["bands"]


def test_age_outside_every_bracket_has_no_context() -> None:
    """The reference studied ages 20–79; it has nothing to say about 15 or 85,
    and a gap here is the honest answer, not a bug to fill by extrapolating."""
    metric = BodyMetric(
        slug="body-fat-pct", name="Gordura corporal", unit="%", age_bands_f=AGE_BRACKETS
    )
    assert age_band_for(metric, Sex.F, 19) is None
    assert age_band_for(metric, Sex.F, 40) is None


def test_a_metric_with_no_age_reference_has_no_age_context() -> None:
    metric = BodyMetric(slug="bmi", name="IMC", unit="kg/m²")
    assert age_band_for(metric, Sex.M, 30) is None


def test_unknown_sex_or_age_yields_no_age_context() -> None:
    metric = BodyMetric(
        slug="body-fat-pct", name="Gordura corporal", unit="%", age_bands_f=AGE_BRACKETS
    )
    assert age_band_for(metric, None, 30) is None
    assert age_band_for(metric, Sex.F, None) is None


def test_the_seeded_age_bands_classify_body_fat_percentage_within_a_bracket() -> None:
    """22 % at 25 lands just inside the deficiency-adjacent low end for a woman
    that age (Imboden, 20–29): the published boundary was 22.1."""
    entry = _seed_metric("body-fat-pct")
    metric = BodyMetric(
        slug="body-fat-pct", name="Gordura corporal", unit="%", age_bands_f=entry["age_bands_f"]
    )
    bands = age_band_for(metric, Sex.F, 25)
    assert bands is not None
    _, label = classify(Decimal("22"), bands)
    assert label == "Abaixo do percentil 10"
    # Every band names without judging (D1/DT8): no age-context band ever flags.
    assert all(band["flag"] is None for band in bands)
