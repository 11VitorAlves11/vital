"""Values a report's own canonical numbers make computable — no database, no report."""

from decimal import Decimal

from app.services import derived_biomarkers as derived


def test_ldl_is_computed_by_friedewald() -> None:
    # 220 - 50 - 150/5 = 140.
    measured = {
        "colesterol-total": Decimal(220),
        "hdl": Decimal(50),
        "triglicerideos": Decimal(150),
    }
    [ldl] = [item for item in derived.derive(measured) if item.biomarker_slug == "ldl"]
    assert ldl.value == Decimal("140.0000")
    assert ldl.source_slugs == ("colesterol-total", "hdl", "triglicerideos")


def test_ldl_is_suppressed_above_the_friedewald_triglyceride_limit() -> None:
    measured = {
        "colesterol-total": Decimal(220),
        "hdl": Decimal(50),
        "triglicerideos": Decimal(401),
    }
    assert "ldl" not in [item.biomarker_slug for item in derived.derive(measured)]


def test_ldl_is_computed_right_at_the_triglyceride_limit() -> None:
    """400 itself is still valid — the limit is exclusive of nothing below it."""
    measured = {
        "colesterol-total": Decimal(220),
        "hdl": Decimal(50),
        "triglicerideos": Decimal(400),
    }
    assert "ldl" in [item.biomarker_slug for item in derived.derive(measured)]


def test_ldl_is_not_computed_when_the_lab_already_reported_one() -> None:
    """A lab's own LDL is a real assay; Friedewald's estimate has no business
    standing in for it."""
    measured = {
        "colesterol-total": Decimal(220),
        "hdl": Decimal(50),
        "triglicerideos": Decimal(150),
        "ldl": Decimal(130),
    }
    assert "ldl" not in [item.biomarker_slug for item in derived.derive(measured)]


def test_ldl_needs_all_three_inputs() -> None:
    """CT and HDL alone still support non-HDL and the ratio — just not LDL."""
    measured = {"colesterol-total": Decimal(220), "hdl": Decimal(50)}
    assert "ldl" not in [item.biomarker_slug for item in derived.derive(measured)]


def test_non_hdl_is_total_minus_hdl() -> None:
    measured = {"colesterol-total": Decimal(220), "hdl": Decimal(50)}
    [item] = [i for i in derived.derive(measured) if i.biomarker_slug == "nao-hdl"]
    assert item.value == Decimal("170.0000")
    assert item.source_slugs == ("colesterol-total", "hdl")


def test_ct_hdl_ratio_is_computed_and_rounded_to_two_places() -> None:
    measured = {"colesterol-total": Decimal(220), "hdl": Decimal(48)}
    [item] = [i for i in derived.derive(measured) if i.biomarker_slug == "racio-ct-hdl"]
    assert item.value == Decimal("4.58")  # 220 / 48 = 4.5833...


def test_ct_hdl_ratio_is_not_computed_against_a_zero_hdl() -> None:
    """A zero would be a data error, not a real reading — dividing by it is not
    a value to show, not a crash to raise."""
    measured = {"colesterol-total": Decimal(220), "hdl": Decimal(0)}
    assert "racio-ct-hdl" not in [item.biomarker_slug for item in derived.derive(measured)]


def test_neutrophil_lymphocyte_ratio_is_computed() -> None:
    measured = {"neutrofilos": Decimal("4.2"), "linfocitos": Decimal("1.4")}
    [item] = [
        i for i in derived.derive(measured) if i.biomarker_slug == "racio-neutrofilos-linfocitos"
    ]
    assert item.value == Decimal("3.00")


def test_nothing_is_derived_from_an_empty_report() -> None:
    assert derived.derive({}) == []


def test_the_lipid_panel_and_the_leucogram_derive_independently() -> None:
    """One family present, the other absent, produces only what its own inputs support."""
    measured = {
        "colesterol-total": Decimal(220),
        "hdl": Decimal(50),
        "triglicerideos": Decimal(150),
    }
    slugs = {item.biomarker_slug for item in derived.derive(measured)}
    assert slugs == {"ldl", "nao-hdl", "racio-ct-hdl"}
