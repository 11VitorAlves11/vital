"""The collection context on a report, and what the API refuses to store.

Backlog 1.4 and 1.5, through the endpoints: an hour that contradicts the date, a
fast nobody claims happened, and the caveats a marker earns from either.
"""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def _create(ac: AsyncClient, catalogue: dict[str, Any], **overrides: Any) -> Any:
    payload: dict[str, Any] = {
        "collected_on": "2026-03-01",
        "lab_name": "Synlab",
        "results": [{"biomarker_id": catalogue["biomarkers"]["glicose"]["id"], "value": 92}],
    }
    payload.update(overrides)
    return await ac.post("/api/reports", json=payload)


async def test_the_collection_context_round_trips(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    response = await _create(
        user_client,
        catalogue,
        collected_at="2026-03-01T08:15:00",
        fasting_state="fasting",
        fasting_hours=12,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["collected_at"] == "2026-03-01T08:15:00"
    assert body["fasting_state"] == "fasting"
    assert body["fasting_hours"] == 12
    assert body["results"][0]["caveats"] == []


async def test_a_report_with_no_context_defaults_to_unknown(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    """Not "they had eaten" — nobody said, which is a different fact."""
    body = (await _create(user_client, catalogue)).json()
    assert body["fasting_state"] == "unknown"
    assert body["collected_at"] is None
    assert [caveat["code"] for caveat in body["results"][0]["caveats"]] == ["fasting_unknown"]


async def test_an_hour_on_another_day_is_refused(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    response = await _create(user_client, catalogue, collected_at="2026-03-02T08:15:00")
    assert response.status_code == 422


async def test_an_hour_with_an_offset_is_refused(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    """The hour is wall-clock: a marker peaks at 8 a.m. where the blood was drawn."""
    response = await _create(user_client, catalogue, collected_at="2026-03-01T08:15:00+01:00")
    assert response.status_code == 422


async def test_fasting_hours_without_a_fast_are_refused(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    response = await _create(user_client, catalogue, fasting_state="not_fasting", fasting_hours=12)
    assert response.status_code == 422


async def test_a_short_fast_is_raised_against_the_marker_that_needs_one(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    body = (
        await ac.post(
            "/api/reports",
            json={
                "collected_on": "2026-03-01",
                "lab_name": "Synlab",
                "fasting_state": "fasting",
                "fasting_hours": 4,
                "results": [
                    {"biomarker_id": catalogue["biomarkers"]["glicose"]["id"], "value": 92},
                    {"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 14.1},
                ],
            },
        )
    ).json()
    caveats = {
        item["biomarker_slug"]: [caveat["code"] for caveat in item["caveats"]]
        for item in body["results"]
    }
    assert caveats == {"glicose": ["fasting_too_short"], "hemoglobina": []}


async def test_the_method_travels_with_the_result_and_marks_its_change(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    marker_id = catalogue["biomarkers"]["creatinina"]["id"]
    for collected_on, method in (("2026-01-01", "Jaffe"), ("2026-06-01", "Enzimático")):
        response = await ac.post(
            "/api/reports",
            json={
                "collected_on": collected_on,
                "lab_name": "Synlab",
                "results": [{"biomarker_id": marker_id, "value": 0.95, "method": method}],
            },
        )
        assert response.status_code == 201, response.text

    series = (await ac.get(f"/api/biomarkers/{marker_id}/series")).json()
    assert [point["method"] for point in series["points"]] == ["Jaffe", "Enzimático"]
    codes = [[caveat["code"] for caveat in point["caveats"]] for point in series["points"]]
    # The first draw used a method the catalogue flags; the second changed it.
    assert codes[0] == ["low_reliability_method"]
    assert "method_changed" in codes[1]
