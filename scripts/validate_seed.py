#!/usr/bin/env python3
"""Validate the clinical seed catalogue in seed/.

Runs in CI with no dependencies beyond the standard library, so a malformed
catalogue fails the pipeline before it can reach the database.
"""

from __future__ import annotations

import json
import sys
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
    for band in bands:
        if band.get("flag") not in FLAGS:
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


def check_body_metrics(entries: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for entry in entries:
        slug = entry.get("slug", "<sem slug>")
        for field in ("slug", "name", "unit", "bands_m", "bands_f", "source", "notes"):
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

    banded = sum(1 for m in body_metrics if m["bands_m"] is not None)
    print(
        f"Catálogo válido: {len(biomarkers)} biomarcadores, "
        f"{len(body_metrics)} métricas corporais ({banded} com bandas clínicas, "
        f"{len(body_metrics) - banded} trend-only)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
