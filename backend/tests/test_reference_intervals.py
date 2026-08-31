"""Reference shapes and canonical units, end to end through the API.

Backlog 1.2 and 1.3: the four interval shapes, and a history that stays one
series when the laboratory changes the unit it reports in.
"""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def _report(
    ac: AsyncClient, collected_on: str, results: list[dict[str, Any]], lab: str = "Synlab"
) -> Any:
    response = await ac.post(
        "/api/reports",
        json={"collected_on": collected_on, "lab_name": lab, "results": results},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_the_four_shapes_are_named_on_the_result(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    markers = catalogue["biomarkers"]
    body = await _report(
        ac,
        "2026-03-01",
        [
            # Two numbers from the lab.
            {
                "biomarker_id": markers["creatinina"]["id"],
                "value": 1.0,
                "ref_min": 0.74,
                "ref_max": 1.35,
            },
            # ALT < 41: an upper bound and nothing else.
            {"biomarker_id": markers["alt"]["id"], "value": 30, "ref_max": 41},
            # HDL > 40: a lower bound and nothing else.
            {"biomarker_id": markers["hdl"]["id"], "value": 55, "ref_min": 40},
            # Vitamin D: a named scale, whatever the report printed beside it.
            {"biomarker_id": markers["vitamin-d-25-oh"]["id"], "value": 24},
        ],
    )
    kinds = {item["biomarker_slug"]: item["reference_kind"] for item in body["results"]}
    assert kinds == {
        "creatinina": "two_sided",
        "alt": "upper_bound",
        "hdl": "lower_bound",
        "vitamin-d-25-oh": "ordinal_bands",
    }


async def test_a_one_sided_bound_only_flags_on_its_own_side(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    markers = catalogue["biomarkers"]
    body = await _report(
        ac,
        "2026-03-01",
        [
            # Far under an upper bound is not "low" — nothing said how low is low.
            {"biomarker_id": markers["alt"]["id"], "value": 4, "ref_max": 41},
            # Far over a lower bound is not "high".
            {"biomarker_id": markers["hdl"]["id"], "value": 95, "ref_min": 40},
        ],
    )
    flags = {item["biomarker_slug"]: item["flag"] for item in body["results"]}
    assert flags == {"alt": "normal", "hdl": "normal"}


async def test_an_ordinal_marker_reports_the_step_it_landed_on(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """Vitamin D at 31 ng/mL is barely sufficient, and says so by name."""
    ac, _ = await make_user(sex="M")
    marker_id = catalogue["biomarkers"]["vitamin-d-25-oh"]["id"]
    body = await _report(ac, "2026-03-01", [{"biomarker_id": marker_id, "value": 31}])
    result = body["results"][0]
    assert result["reference_kind"] == "ordinal_bands"
    assert result["band_label"] == "suficiência"
    assert result["flag"] == "normal"
    assert [band["label"] for band in result["reference_bands"]] == [
        "deficiência grave",
        "deficiência",
        "insuficiência",
        "suficiência",
        "excesso",
    ]


async def test_an_ordinal_marker_is_classified_without_a_known_sex(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """The scale is clinical consensus, not a sex-specific range."""
    ac, _ = await make_user(sex=None)
    marker_id = catalogue["biomarkers"]["vitamin-d-25-oh"]["id"]
    body = await _report(ac, "2026-03-01", [{"biomarker_id": marker_id, "value": 18}])
    assert body["results"][0]["flag"] == "low"
    assert body["results"][0]["band_label"] == "deficiência"


async def test_a_change_of_unit_does_not_break_the_series(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """The acceptance criterion for 1.3: the same blood, two labs, one line."""
    ac, _ = await make_user(sex="M")
    marker_id = catalogue["biomarkers"]["vitamin-d-25-oh"]["id"]
    await _report(ac, "2026-01-01", [{"biomarker_id": marker_id, "value": 32}], lab="Synlab")
    await _report(
        ac,
        "2026-06-01",
        [{"biomarker_id": marker_id, "value": 80, "unit": "nmol/L"}],
        lab="Unilabs",
    )

    series = (await ac.get(f"/api/biomarkers/{marker_id}/series")).json()
    assert series["unit"] == "ng/mL"
    assert series["has_unconverted_points"] is False
    # Reported as they came, plotted on one scale: 80 nmol/L is 32.05 ng/mL.
    assert [point["value"] for point in series["points"]] == ["32.0000", "80.0000"]
    assert [point["unit"] for point in series["points"]] == ["ng/mL", "nmol/L"]
    assert [point["canonical_value"] for point in series["points"]] == ["32.0000", "32.0480"]


async def test_a_unit_the_catalogue_cannot_convert_is_left_unconverted(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """Guessing the factor would silently move the value; the point is dropped
    from the canonical line instead, and the series says so."""
    ac, _ = await make_user(sex="M")
    marker_id = catalogue["biomarkers"]["vitamin-d-25-oh"]["id"]
    body = await _report(
        ac, "2026-03-01", [{"biomarker_id": marker_id, "value": 32, "unit": "mg/dL"}]
    )
    result = body["results"][0]
    assert result["canonical_value"] is None
    assert result["flag"] is None

    series = (await ac.get(f"/api/biomarkers/{marker_id}/series")).json()
    assert series["has_unconverted_points"] is True


async def test_the_reference_bands_are_frozen_onto_the_result(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """1.1's rule extended to scales: the reading keeps the bands it was read
    against, so a later correction to the catalogue cannot rewrite the past."""
    ac, _ = await make_user(sex="M")
    marker_id = catalogue["biomarkers"]["vitamin-d-25-oh"]["id"]
    body = await _report(ac, "2026-03-01", [{"biomarker_id": marker_id, "value": 45}])
    stored = body["results"][0]["reference_bands"]

    fetched = (await ac.get(f"/api/reports/{body['id']}")).json()
    assert fetched["results"][0]["reference_bands"] == stored
