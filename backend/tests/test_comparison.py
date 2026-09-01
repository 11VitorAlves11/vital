"""Two collections read against each other: what moved, and what cannot be read as movement."""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def _report(
    ac: AsyncClient, collected_on: str, results: list[dict[str, Any]], **extra: Any
) -> str:
    payload: dict[str, Any] = {
        "collected_on": collected_on,
        "lab_name": "Synlab Braga",
        "results": results,
        **extra,
    }
    response = await ac.post("/api/reports", json=payload)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _row(body: dict[str, Any], slug: str) -> dict[str, Any]:
    return next(row for row in body["rows"] if row["biomarker_slug"] == slug)


def _codes(row: dict[str, Any]) -> set[str]:
    return {caveat["code"] for caveat in row["caveats"]}


async def test_the_earlier_draw_is_the_previous_one_whatever_order_is_asked(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["hemoglobina"]["id"]
    older = await _report(user_client, "2026-01-10", [{"biomarker_id": marker, "value": 14}])
    newer = await _report(user_client, "2026-06-10", [{"biomarker_id": marker, "value": 15.4}])

    for a, b in ((older, newer), (newer, older)):
        body = (await user_client.get(f"/api/reports/compare?a={a}&b={b}")).json()
        assert body["previous"]["collected_on"] == "2026-01-10"
        assert body["current"]["collected_on"] == "2026-06-10"
        # Forward in time in both directions of asking: 14 → 15.4 is a rise.
        assert float(_row(body, "hemoglobina")["delta"]) == 1.4


async def test_delta_and_percent_change_are_computed(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["ferritina"]["id"]
    older = await _report(user_client, "2026-01-10", [{"biomarker_id": marker, "value": 40}])
    newer = await _report(user_client, "2026-06-10", [{"biomarker_id": marker, "value": 30}])

    row = _row(
        (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(), "ferritina"
    )
    assert float(row["delta"]) == -10
    assert float(row["percent_change"]) == -25
    assert row["unit"] == "ng/mL"
    assert row["previous"]["value"] == "40.0000"
    assert row["current"]["value"] == "30.0000"


async def test_percent_change_is_omitted_when_the_earlier_value_was_zero(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["pcr"]["id"]
    older = await _report(user_client, "2026-01-10", [{"biomarker_id": marker, "value": 0}])
    newer = await _report(user_client, "2026-06-10", [{"biomarker_id": marker, "value": 2}])

    row = _row((await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(), "pcr")
    assert float(row["delta"]) == 2
    assert row["percent_change"] is None


async def test_a_marker_present_in_only_one_collection_is_still_a_row(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    hemoglobin = catalogue["biomarkers"]["hemoglobina"]["id"]
    ferritin = catalogue["biomarkers"]["ferritina"]["id"]
    older = await _report(user_client, "2026-01-10", [{"biomarker_id": hemoglobin, "value": 14}])
    newer = await _report(user_client, "2026-06-10", [{"biomarker_id": ferritin, "value": 60}])

    body = (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json()
    dropped, added = _row(body, "hemoglobina"), _row(body, "ferritina")
    assert dropped["current"] is None and dropped["previous"]["value"] == "14.0000"
    assert added["previous"] is None and added["current"]["value"] == "60.0000"
    # Nothing to subtract, and no caveat either: an absent measurement is not a
    # doubtful one.
    assert (dropped["delta"], added["delta"]) == (None, None)
    assert _codes(dropped) == _codes(added) == set()


async def test_values_reported_in_different_units_are_put_on_one_scale(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["hemoglobina"]["id"]
    older = await _report(
        user_client, "2026-01-10", [{"biomarker_id": marker, "value": 140, "unit": "g/L"}]
    )
    newer = await _report(user_client, "2026-06-10", [{"biomarker_id": marker, "value": 15}])

    row = _row(
        (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(), "hemoglobina"
    )
    # 140 g/L is 14 g/dL: a change of supplier is not a change of one hundred and
    # twenty-five.
    assert float(row["delta"]) == 1
    assert row["unit"] == "g/dL"


async def test_the_same_unconvertible_unit_is_still_subtracted(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["hemoglobina"]["id"]
    older = await _report(
        user_client, "2026-01-10", [{"biomarker_id": marker, "value": 8, "unit": "mmol/L"}]
    )
    newer = await _report(
        user_client, "2026-06-10", [{"biomarker_id": marker, "value": 9, "unit": "mmol/L"}]
    )

    row = _row(
        (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(), "hemoglobina"
    )
    # The catalogue has no factor for mmol/L of haemoglobin, so neither value has
    # a canonical form — but both were reported the same way, and subtracting
    # them is still arithmetic on one scale.
    assert row["previous"]["canonical_value"] is None
    assert float(row["delta"]) == 1
    assert row["unit"] == "mmol/L"


async def test_units_with_no_conversion_between_them_are_not_subtracted(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["hemoglobina"]["id"]
    older = await _report(
        user_client, "2026-01-10", [{"biomarker_id": marker, "value": 8, "unit": "mmol/L"}]
    )
    newer = await _report(user_client, "2026-06-10", [{"biomarker_id": marker, "value": 15}])

    row = _row(
        (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(), "hemoglobina"
    )
    assert (row["delta"], row["percent_change"], row["unit"]) == (None, None, None)
    assert "units_incomparable" in _codes(row)


async def test_a_changed_assay_is_carried_as_a_caveat(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["glicose"]["id"]
    older = await _report(
        user_client, "2026-01-10", [{"biomarker_id": marker, "value": 90, "method": "hexoquinase"}]
    )
    newer = await _report(
        user_client,
        "2026-06-10",
        [{"biomarker_id": marker, "value": 96, "method": "glicose oxidase"}],
    )

    row = _row(
        (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(), "glicose"
    )
    assert "method_changed" in _codes(row)
    assert float(row["delta"]) == 6


async def test_a_reference_interval_that_moved_is_carried_as_a_caveat(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["ferritina"]["id"]
    older = await _report(
        user_client,
        "2026-01-10",
        [{"biomarker_id": marker, "value": 145, "ref_min": 15, "ref_max": 150}],
    )
    newer = await _report(
        user_client,
        "2026-06-10",
        [{"biomarker_id": marker, "value": 145, "ref_min": 20, "ref_max": 140}],
    )

    row = _row(
        (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(), "ferritina"
    )
    # The same number, classified two ways. Without this the reader would read the
    # change of flag as a change in the blood.
    assert float(row["delta"]) == 0
    assert (row["previous"]["flag"], row["current"]["flag"]) == ("normal", "high")
    assert "reference_changed" in _codes(row)


async def test_an_ordinal_scale_is_not_reported_as_a_moved_interval(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["vitamin-d-25-oh"]["id"]
    older = await _report(
        user_client,
        "2026-01-10",
        [{"biomarker_id": marker, "value": 22, "ref_min": 30, "ref_max": 100}],
    )
    newer = await _report(
        user_client,
        "2026-06-10",
        [{"biomarker_id": marker, "value": 41, "ref_min": 20, "ref_max": 80}],
    )

    row = _row(
        (await user_client.get(f"/api/reports/compare?a={older}&b={newer}")).json(),
        "vitamin-d-25-oh",
    )
    # The bands classify this marker, not the numbers the analyser printed, so
    # those numbers changing is not a change of reference (DT5).
    assert _codes(row) == set()
    assert (row["previous"]["band_label"], row["current"]["band_label"]) == (
        "insuficiência",
        "suficiência",
    )


async def test_a_report_cannot_be_compared_with_itself(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["hemoglobina"]["id"]
    only = await _report(user_client, "2026-01-10", [{"biomarker_id": marker, "value": 14}])
    assert (await user_client.get(f"/api/reports/compare?a={only}&b={only}")).status_code == 422


async def test_another_accounts_report_cannot_be_compared(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    marker = catalogue["biomarkers"]["hemoglobina"]["id"]
    mine, _ = await make_user()
    theirs, _ = await make_user()
    ours = await _report(mine, "2026-01-10", [{"biomarker_id": marker, "value": 14}])
    hidden = await _report(theirs, "2026-06-10", [{"biomarker_id": marker, "value": 15}])

    response = await mine.get(f"/api/reports/compare?a={ours}&b={hidden}")
    assert response.status_code == 404
