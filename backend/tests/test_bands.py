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
from app.services.bands import bands_for, classify

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
        ("body-fat-pct", "bands_m", "10", "normal", "Atleta"),
        ("body-fat-pct", "bands_m", "1.5", "alert", "Abaixo do essencial"),
        ("body-fat-pct", "bands_f", "33", "alert", "Obesidade"),
        ("waist-circumference", "bands_m", "96", "warn", "Risco aumentado"),
        ("waist-circumference", "bands_f", "79", "normal", "Sem risco acrescido"),
    ],
)
def test_seeded_bands_classify_against_their_published_standard(
    slug: str, sex: str, value: str, expected_flag: str, expected_label: str
) -> None:
    bands = _seed_metric(slug)[sex]
    assert classify(Decimal(value), bands) == (expected_flag, expected_label)  # type: ignore[arg-type]
