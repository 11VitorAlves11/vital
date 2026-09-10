"""Transcription and validation for body-composition screenshots."""

import json
import re
from decimal import Decimal

from pydantic import ValidationError

from app.models import BodyMetric
from app.schemas.body_extractions import (
    BodyExtractionPayload,
    BodyExtractionPreview,
    BodyPreviewValue,
    ExtractedBodyValue,
)
from app.services.extraction import ExtractionError
from app.services.text import normalise

PROMPT = """Transcreve as medições de composição corporal visíveis nesta imagem.
Responde APENAS com JSON válido, sem markdown, neste formato:
{
  "measured_at": "YYYY-MM-DDTHH:MM",
  "device": "marca ou modelo, se estiver visível",
  "results": [
    {"source_name": "texto original", "metric_slug": "slug", "value": 0.0, "unit": "..."}
  ]
}
Usa apenas estes slugs: bmi, body-fat-pct, waist-circumference, weight, fat-mass,
fat-free-mass, muscle-mass, muscle-rate, skeletal-muscle-mass, bone-mass,
protein-mass, protein-pct, water-mass, water-pct, subcutaneous-fat-pct,
visceral-fat-index, bmr, metabolic-age.
Não devolvas valores calculados como fmi ou ffmi, nem classificações da aplicação ou
balança como "excelente", "normal", "alto" ou pontuações corporais. Não convertas
unidades, não inventes campos ausentes e usa null quando a data, dispositivo, valor ou
unidade não estiver visível. Conserva em source_name o nome exatamente como aparece."""


ALIASES: dict[str, str] = {
    "imc": "bmi",
    "indice de massa corporal": "bmi",
    "peso": "weight",
    "weight": "weight",
    "gordura corporal": "body-fat-pct",
    "percentagem de gordura": "body-fat-pct",
    "body fat": "body-fat-pct",
    "body fat percentage": "body-fat-pct",
    "massa gorda": "fat-mass",
    "fat mass": "fat-mass",
    "massa livre de gordura": "fat-free-mass",
    "fat free body weight": "fat-free-mass",
    "massa muscular": "muscle-mass",
    "muscle mass": "muscle-mass",
    "taxa muscular": "muscle-rate",
    "muscle rate": "muscle-rate",
    "musculo esqueletico": "skeletal-muscle-mass",
    "skeletal muscle": "skeletal-muscle-mass",
    "massa ossea": "bone-mass",
    "bone mass": "bone-mass",
    "proteina": "protein-pct",
    "protein": "protein-pct",
    "massa proteica": "protein-mass",
    "protein mass": "protein-mass",
    "agua corporal": "water-pct",
    "body water": "water-pct",
    "massa de agua": "water-mass",
    "water weight": "water-mass",
    "gordura subcutanea": "subcutaneous-fat-pct",
    "subcutaneous fat": "subcutaneous-fat-pct",
    "gordura visceral": "visceral-fat-index",
    "visceral fat": "visceral-fat-index",
    "taxa metabolica basal": "bmr",
    "metabolismo basal": "bmr",
    "bmr": "bmr",
    "idade metabolica": "metabolic-age",
    "metabolic age": "metabolic-age",
    "perimetro abdominal": "waist-circumference",
    "circunferencia da cintura": "waist-circumference",
    "waist circumference": "waist-circumference",
}

UNIT_ALIASES: dict[str, set[str]] = {
    "%": {"", "percent", "percentagem"},
    "kg": {"kg", "quilograma", "quilogramas"},
    "cm": {"cm", "centimetro", "centimetros"},
    "kg/m²": {"kg m2", "kg m 2"},
    "índice": {"indice", "nivel", "level"},
    "kcal": {"kcal", "kcal dia", "kcal day"},
    "anos": {"ano", "anos", "year", "years"},
}

DERIVED_SLUGS = {"fmi", "ffmi"}

PLAUSIBLE: dict[str, tuple[Decimal, Decimal]] = {
    "weight": (Decimal("20"), Decimal("400")),
    "bmi": (Decimal("8"), Decimal("80")),
    "waist-circumference": (Decimal("30"), Decimal("250")),
    "visceral-fat-index": (Decimal("0"), Decimal("100")),
    "bmr": (Decimal("300"), Decimal("6000")),
    "metabolic-age": (Decimal("1"), Decimal("120")),
}


def parse_answer(text: str) -> BodyExtractionPayload:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", candidate).strip()
    if not candidate.startswith("{"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            raise ExtractionError("The model did not answer with JSON")
        candidate = candidate[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ExtractionError("The model's answer was not valid JSON") from error
    try:
        return BodyExtractionPayload.model_validate(data)
    except ValidationError as error:
        raise ExtractionError("The model's answer did not have the expected shape") from error


def _match(result: ExtractedBodyValue, metrics: dict[str, BodyMetric]) -> BodyMetric | None:
    if (
        result.metric_slug
        and result.metric_slug in metrics
        and result.metric_slug not in DERIVED_SLUGS
    ):
        return metrics[result.metric_slug]
    source = normalise(result.source_name)
    unit = normalise(result.unit) if result.unit else ""
    if source in {"proteina", "protein"} and unit == "kg":
        return metrics.get("protein-mass")
    if source in {"agua corporal", "body water"} and unit == "kg":
        return metrics.get("water-mass")
    alias_slug = ALIASES.get(source)
    return metrics.get(alias_slug) if alias_slug else None


def _warnings(result: ExtractedBodyValue, metric: BodyMetric | None) -> list[str]:
    warnings: list[str] = []
    if metric is None:
        warnings.append("unmatched")
    if result.value is None:
        warnings.append("missing_value")
    if metric is not None and result.unit:
        accepted = UNIT_ALIASES.get(metric.unit, {normalise(metric.unit)})
        if normalise(result.unit) not in accepted:
            warnings.append("unit_mismatch")
    if metric is not None and result.value is not None:
        bounds = PLAUSIBLE.get(metric.slug)
        if bounds is None and (metric.unit == "%" or metric.unit == "kg"):
            bounds = (Decimal("0"), Decimal("100") if metric.unit == "%" else Decimal("300"))
        if bounds and not bounds[0] <= result.value <= bounds[1]:
            warnings.append("implausible_value")
    return warnings


def build_preview(
    payload: BodyExtractionPayload, metric_rows: list[BodyMetric]
) -> BodyExtractionPreview:
    metrics = {metric.slug: metric for metric in metric_rows}
    matched = [(result, _match(result, metrics)) for result in payload.results]
    counts: dict[int, int] = {}
    for _, metric in matched:
        if metric:
            counts[metric.id] = counts.get(metric.id, 0) + 1
    return BodyExtractionPreview(
        measured_at=payload.measured_at,
        device=payload.device,
        results=[
            BodyPreviewValue(
                metric_id=metric.id if metric else None,
                metric_slug=metric.slug if metric else None,
                metric_name=metric.name if metric else None,
                expected_unit=metric.unit if metric else None,
                source_name=result.source_name,
                source_unit=result.unit,
                value=result.value,
                warnings=[
                    *_warnings(result, metric),
                    *(["duplicate"] if metric and counts[metric.id] > 1 else []),
                ],
            )
            for result, metric in matched
        ],
    )
