#!/usr/bin/env python3
"""Validate the clinical seed catalogue in seed/.

Runs in CI with no dependencies beyond the standard library, so a malformed
catalogue fails the pipeline before it can reach the database.
"""

from __future__ import annotations

import json
import sys
from datetime import time
from pathlib import Path
from typing import Any

SEED = Path(__file__).resolve().parent.parent / "seed"

CATEGORIES = {
    "hematologia",
    "bioquimica",
    "vitaminas",
    "ferro",
    "hormonas",
    "lipidos",
    "renal",
    "hepatico",
    "outro",
}
FLAGS = {"normal", "warn", "alert"}
RESULT_FLAGS = {"low", "normal", "high"}
REFERENCE_KINDS = {"two_sided", "upper_bound", "lower_bound", "ordinal_bands", "none"}

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def check_biomarkers(entries: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for entry in entries:
        slug = entry.get("slug", "<sem slug>")
        for field in (
            "slug",
            "name",
            "category",
            "unit_default",
            "canonical_unit",
            "unit_conversions",
            "reference_kind",
            "aliases",
        ):
            if field not in entry:
                fail(f"biomarcador {slug}: falta o campo '{field}'")
        if slug in seen:
            fail(f"biomarcador {slug}: slug duplicado")
        seen.add(slug)
        if entry.get("category") not in CATEGORIES:
            fail(f"biomarcador {slug}: categoria inválida {entry.get('category')!r}")
        if not isinstance(entry.get("aliases"), list) or not entry["aliases"]:
            fail(f"biomarcador {slug}: 'aliases' tem de ser uma lista não vazia")
        for sex in ("m", "f"):
            lo, hi = entry.get(f"ref_min_{sex}"), entry.get(f"ref_max_{sex}")
            if lo is not None and hi is not None and lo >= hi:
                fail(f"biomarcador {slug}: ref_min_{sex} ({lo}) >= ref_max_{sex} ({hi})")
        check_units(slug, entry)
        check_reference_kind(slug, entry)
        check_preanalytics(slug, entry)


def check_units(slug: str, entry: dict[str, Any]) -> None:
    """A conversion factor multiplies someone's result, so the table is checked hard."""
    if not entry.get("canonical_unit"):
        fail(f"biomarcador {slug}: 'canonical_unit' não pode ser vazio")
    conversions = entry.get("unit_conversions")
    if not isinstance(conversions, dict):
        fail(f"biomarcador {slug}: 'unit_conversions' tem de ser um objeto")
        return
    for unit, factor in conversions.items():
        if not unit:
            fail(f"biomarcador {slug}: unidade sem nome em 'unit_conversions'")
        if not isinstance(factor, int | float) or isinstance(factor, bool) or factor <= 0:
            fail(f"biomarcador {slug}: fator de conversão inválido para {unit!r}: {factor!r}")
        if unit == entry.get("canonical_unit"):
            fail(f"biomarcador {slug}: {unit!r} é a unidade canónica e não precisa de fator")


def check_preanalytics(slug: str, entry: dict[str, Any]) -> None:
    """A sensitivity flag with nothing behind it is a warning nobody can act on."""
    if entry.get("fasting_min_hours") is not None and not entry.get("fasting_sensitive"):
        fail(f"biomarcador {slug}: 'fasting_min_hours' sem 'fasting_sensitive'")

    window = [entry.get("time_window_start"), entry.get("time_window_end")]
    if any(edge is not None for edge in window) and not entry.get("time_sensitive"):
        fail(f"biomarcador {slug}: janela horária sem 'time_sensitive'")
    if entry.get("time_sensitive") and any(edge is None for edge in window):
        fail(f"biomarcador {slug}: 'time_sensitive' exige janela horária completa")
    for edge in window:
        if edge is None:
            continue
        try:
            time.fromisoformat(edge)
        except (TypeError, ValueError):
            fail(f"biomarcador {slug}: hora inválida {edge!r} (esperado HH:MM)")
    if all(edge is not None for edge in window):
        start, end = (time.fromisoformat(edge) for edge in window)
        if start >= end:
            fail(f"biomarcador {slug}: janela horária com início depois do fim")

    methods = entry.get("low_reliability_methods")
    if methods is not None and not isinstance(methods, list):
        fail(f"biomarcador {slug}: 'low_reliability_methods' tem de ser uma lista")
    elif methods and not entry.get("notes"):
        # Naming an assay unreliable without saying why is an accusation, not data.
        fail(f"biomarcador {slug}: métodos de baixa fiabilidade exigem 'notes' a explicar porquê")

    if entry.get("seasonal") and not entry.get("notes"):
        fail(f"biomarcador {slug}: 'seasonal' exige 'notes' a explicar a variação")


def check_reference_kind(slug: str, entry: dict[str, Any]) -> None:
    """The declared shape has to be the shape the bounds actually form."""
    kind = entry.get("reference_kind")
    if kind not in REFERENCE_KINDS:
        fail(f"biomarcador {slug}: reference_kind inválido {kind!r}")
        return

    bands = entry.get("ordinal_bands")
    if kind == "ordinal_bands":
        if not bands:
            fail(f"biomarcador {slug}: reference_kind 'ordinal_bands' exige 'ordinal_bands'")
        else:
            check_ordinal_bands(slug, bands)
        return
    if bands:
        fail(f"biomarcador {slug}: 'ordinal_bands' definido mas reference_kind é {kind!r}")

    has_min = entry.get("ref_min_m") is not None or entry.get("ref_min_f") is not None
    has_max = entry.get("ref_max_m") is not None or entry.get("ref_max_f") is not None
    expected = {
        (True, True): "two_sided",
        (True, False): "lower_bound",
        (False, True): "upper_bound",
        (False, False): "none",
    }[(has_min, has_max)]
    if kind != expected:
        fail(f"biomarcador {slug}: reference_kind {kind!r} mas os limites formam {expected!r}")


def check_ordinal_bands(slug: str, bands: list[dict[str, Any]]) -> None:
    """Same contract as the body-composition bands, with the lab flag vocabulary."""
    if bands[0]["min"] is not None or bands[-1]["max"] is not None:
        fail(f"biomarcador {slug}: as bandas têm de cobrir todo o domínio (extremos null)")
    for band in bands:
        if band.get("flag") not in RESULT_FLAGS:
            fail(f"biomarcador {slug}: flag de banda inválida {band.get('flag')!r}")
        if not band.get("label"):
            fail(f"biomarcador {slug}: banda sem label")
        lo, hi = band["min"], band["max"]
        if lo is not None and hi is not None and lo >= hi:
            fail(f"biomarcador {slug}: banda '{band['label']}' com min >= max")
    for previous, current in zip(bands, bands[1:], strict=False):
        if previous["max"] != current["min"]:
            fail(
                f"biomarcador {slug}: lacuna ou sobreposição entre "
                f"'{previous['label']}' e '{current['label']}'"
            )


def check_bands(slug: str, sex: str, bands: list[dict[str, Any]]) -> None:
    if not bands:
        fail(f"métrica {slug} ({sex}): lista de bandas vazia — usar null para trend-only")
        return
    if bands[0]["min"] is not None or bands[-1]["max"] is not None:
        fail(f"métrica {slug} ({sex}): as bandas têm de cobrir todo o domínio (extremos null)")
    # All or none: a band set either classifies or only names. Half of each would
    # leave a reader unable to tell an unflagged band from an unjudged scale.
    flags = [band.get("flag") for band in bands]
    if any(flag is None for flag in flags) and any(flag is not None for flag in flags):
        fail(f"métrica {slug} ({sex}): bandas ou classificam todas ou nenhuma")
    for band in bands:
        if band.get("flag") is not None and band["flag"] not in FLAGS:
            fail(f"métrica {slug} ({sex}): flag inválida {band.get('flag')!r}")
        if not band.get("label"):
            fail(f"métrica {slug} ({sex}): banda sem label")
        lo, hi = band["min"], band["max"]
        if lo is not None and hi is not None and lo >= hi:
            fail(f"métrica {slug} ({sex}): banda '{band['label']}' com min >= max")
    for previous, current in zip(bands, bands[1:], strict=False):
        if previous["max"] != current["min"]:
            fail(
                f"métrica {slug} ({sex}): lacuna ou sobreposição entre "
                f"'{previous['label']}' e '{current['label']}'"
            )


def check_age_bands(slug: str, sex: str, brackets: list[dict[str, Any]]) -> None:
    """A second, age-partitioned layer of the same band shape.

    Unlike bands_m/bands_f, brackets do not have to cover every age: a
    reference that only studied ages 20–79 has nothing to say outside that
    range, and a gap there is the honest answer, not a bug.
    """
    if not brackets:
        fail(f"métrica {slug} ({sex}): age_bands vazio — usar null quando não há referência")
        return
    previous_max: float | None = None
    for bracket in brackets:
        age_min, age_max = bracket.get("age_min"), bracket.get("age_max")
        if age_min is None:
            fail(f"métrica {slug} ({sex}): escalão de idade sem 'age_min'")
            continue
        if age_max is not None and age_min >= age_max:
            fail(f"métrica {slug} ({sex}): escalão {age_min}–{age_max} com age_min >= age_max")
        if previous_max is not None and age_min < previous_max:
            fail(f"métrica {slug} ({sex}): escalões de idade sobrepostos em {age_min}")
        previous_max = age_max
        check_bands(f"{slug} [{age_min}–{age_max}]", sex, bracket.get("bands"))


def check_body_metrics(entries: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for entry in entries:
        slug = entry.get("slug", "<sem slug>")
        for field in (
            "slug",
            "name",
            "unit",
            "bands_m",
            "bands_f",
            "age_bands_m",
            "age_bands_f",
            "source",
            "trend_reason",
            "notes",
        ):
            if field not in entry:
                fail(f"métrica {slug}: falta o campo '{field}'")
        if slug in seen:
            fail(f"métrica {slug}: slug duplicado")
        seen.add(slug)

        has_m, has_f = entry.get("bands_m") is not None, entry.get("bands_f") is not None
        if has_m != has_f:
            fail(f"métrica {slug}: bandas definidas para um sexo apenas")
        if has_m and not entry.get("source"):
            fail(f"métrica {slug}: bandas clínicas exigem 'source' (proveniência do standard)")
        if not has_m and entry.get("source"):
            fail(f"métrica {slug}: métrica trend-only não deve declarar 'source'")
        if has_m:
            check_bands(slug, "M", entry["bands_m"])
            check_bands(slug, "F", entry["bands_f"])

        has_age_m = entry.get("age_bands_m") is not None
        has_age_f = entry.get("age_bands_f") is not None
        if has_age_m != has_age_f:
            fail(f"métrica {slug}: age_bands definidas para um sexo apenas")
        if has_age_m:
            check_age_bands(slug, "M", entry["age_bands_m"])
            check_age_bands(slug, "F", entry["age_bands_f"])

        # A metric that cannot produce a flag has to say why, in one line: the
        # card shows that sentence where a classified metric shows its standard.
        classifies = has_m and any(band.get("flag") is not None for band in entry["bands_m"])
        if not classifies and not entry.get("trend_reason"):
            fail(f"métrica {slug}: sem classificação, exige 'trend_reason' (a razão, numa linha)")
        if classifies and entry.get("trend_reason"):
            fail(f"métrica {slug}: classifica, por isso não declara 'trend_reason'")


def main() -> int:
    biomarkers = json.loads((SEED / "biomarkers.json").read_text(encoding="utf-8"))
    body_metrics = json.loads((SEED / "body_metrics.json").read_text(encoding="utf-8"))

    check_biomarkers(biomarkers)
    check_body_metrics(body_metrics)

    if errors:
        print(f"Catálogo inválido — {len(errors)} problema(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    def classifies(metric: dict[str, Any]) -> bool:
        bands = metric["bands_m"]
        return bands is not None and any(band.get("flag") is not None for band in bands)

    banded = sum(1 for m in body_metrics if classifies(m))
    named = sum(1 for m in body_metrics if m["bands_m"] is not None and not classifies(m))
    print(
        f"Catálogo válido: {len(biomarkers)} biomarcadores, "
        f"{len(body_metrics)} métricas corporais ({banded} com bandas clínicas, "
        f"{named} com bandas que nomeiam sem classificar, "
        f"{len(body_metrics) - banded - named} trend-only)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
