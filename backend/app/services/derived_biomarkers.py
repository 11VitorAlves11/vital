"""Values a lab report does not print but its own numbers make computable.

A panel that has cholesterol, HDL and triglycerides carries an LDL whether or
not the lab printed one — Friedewald's estimate has been standard practice for
decades. Computed on read, exactly like the height-derived body indices (5.2):
a stored value would have to be chased down and rewritten whenever an input
result changed, and it would sit in the same table as a dosage, indistinguishable
from one. Everything here works on canonical (mg/dL, ×10⁹/L) values, so a panel
reported in mmol/L is no different from one reported in mg/dL.
"""

from dataclasses import dataclass
from decimal import Decimal

#: Above this, Friedewald's estimate of VLDL from triglycerides (TG/5) no
#: longer tracks reality — the ratio it assumes breaks down, and the LDL it
#: would produce is not a number to show anyone.
LDL_FRIEDEWALD_TG_LIMIT = Decimal(400)

_STEP = Decimal("0.0001")
_RATIO_STEP = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Derived:
    """A value the server computed, and what it computed it from."""

    biomarker_slug: str
    value: Decimal
    #: The measured markers it came from, in the order they enter the formula.
    source_slugs: tuple[str, ...]


def _ldl_friedewald(measured: dict[str, Decimal]) -> Derived | None:
    total, hdl, triglycerides = (
        measured.get("colesterol-total"),
        measured.get("hdl"),
        measured.get("triglicerideos"),
    )
    if total is None or hdl is None or triglycerides is None:
        return None
    if triglycerides > LDL_FRIEDEWALD_TG_LIMIT:
        return None
    value = (total - hdl - triglycerides / 5).quantize(_STEP)
    return Derived("ldl", value, ("colesterol-total", "hdl", "triglicerideos"))


def _non_hdl(measured: dict[str, Decimal]) -> Derived | None:
    total, hdl = measured.get("colesterol-total"), measured.get("hdl")
    if total is None or hdl is None:
        return None
    return Derived("nao-hdl", (total - hdl).quantize(_STEP), ("colesterol-total", "hdl"))


def _total_hdl_ratio(measured: dict[str, Decimal]) -> Derived | None:
    total, hdl = measured.get("colesterol-total"), measured.get("hdl")
    if total is None or not hdl:
        return None
    return Derived("racio-ct-hdl", (total / hdl).quantize(_RATIO_STEP), ("colesterol-total", "hdl"))


def _neutrophil_lymphocyte_ratio(measured: dict[str, Decimal]) -> Derived | None:
    neutrophils, lymphocytes = measured.get("neutrofilos"), measured.get("linfocitos")
    if neutrophils is None or not lymphocytes:
        return None
    return Derived(
        "racio-neutrofilos-linfocitos",
        (neutrophils / lymphocytes).quantize(_RATIO_STEP),
        ("neutrofilos", "linfocitos"),
    )


_FORMULAS = (_ldl_friedewald, _non_hdl, _total_hdl_ratio, _neutrophil_lymphocyte_ratio)


def derive(measured: dict[str, Decimal]) -> list[Derived]:
    """Every derived marker this report's canonical values support.

    Skips anything the report already measured directly: a lab that printed
    its own LDL has the assay that actually separated the lipoproteins, and
    Friedewald's estimate has no business standing in for it.
    """
    candidates = (formula(measured) for formula in _FORMULAS)
    return [item for item in candidates if item is not None and item.biomarker_slug not in measured]
