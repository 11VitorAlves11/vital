"""Reports and results: CRUD, plus the flag each value gets on the way in."""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def _create(ac: AsyncClient, catalogue: dict[str, Any], **overrides: Any) -> Any:
    payload: dict[str, Any] = {
        "collected_on": "2026-03-01",
        "lab_name": "Synlab Braga",
        "fasting": True,
        "results": [{"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 14.1}],
    }
    payload.update(overrides)
    return await ac.post("/api/reports", json=payload)


async def test_create_returns_the_report_with_its_results(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    response = await _create(user_client, catalogue)
    assert response.status_code == 201
    body = response.json()
    assert body["lab_name"] == "Synlab Braga"
    assert body["source"] == "manual"
    assert len(body["results"]) == 1
    assert body["results"][0]["biomarker_slug"] == "hemoglobina"
    # Unit falls back to the catalogue's when the lab's wording is not given.
    assert body["results"][0]["unit"] == "g/dL"


async def test_flags_are_computed_server_side(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    response = await ac.post(
        "/api/reports",
        json={
            "collected_on": "2026-03-01",
            "lab_name": "Synlab",
            "results": [
                # Below the male canonical range (13–17): no lab range given.
                {"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 11},
                # The lab's own range wins, and 200 is above its 150 ceiling.
                {
                    "biomarker_id": catalogue["biomarkers"]["ferritina"]["id"],
                    "value": 200,
                    "ref_min": 15,
                    "ref_max": 150,
                },
            ],
        },
    )
    flags = {item["biomarker_slug"]: item["flag"] for item in response.json()["results"]}
    assert flags == {"hemoglobina": "low", "ferritina": "high"}


async def test_a_client_supplied_flag_is_ignored(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    response = await _create(
        user_client,
        catalogue,
        results=[
            {
                "biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"],
                "value": 14.1,
                "flag": "high",
            }
        ],
    )
    assert response.json()["results"][0]["flag"] == "normal"


async def test_value_without_any_range_is_left_unflagged(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex=None)
    response = await ac.post(
        "/api/reports",
        json={
            "collected_on": "2026-03-01",
            "lab_name": "Synlab",
            "results": [
                {"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 14.1}
            ],
        },
    )
    assert response.json()["results"][0]["flag"] is None


async def test_correcting_the_profile_sex_re_flags_the_history(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    # 12.5 is low for the male range (13–17) and normal for the female one (12–15).
    await ac.post(
        "/api/reports",
        json={
            "collected_on": "2026-03-01",
            "lab_name": "Synlab",
            "results": [
                {"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 12.5}
            ],
        },
    )
    reports = (await ac.get("/api/reports")).json()
    detail = (await ac.get(f"/api/reports/{reports[0]['id']}")).json()
    assert detail["results"][0]["flag"] == "low"

    await ac.patch("/api/users/me", json={"sex": "F"})
    detail = (await ac.get(f"/api/reports/{reports[0]['id']}")).json()
    assert detail["results"][0]["flag"] == "normal"


async def test_unknown_biomarker_is_rejected(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    response = await _create(
        user_client, catalogue, results=[{"biomarker_id": 999_999, "value": 1}]
    )
    assert response.status_code == 422


async def test_the_same_biomarker_cannot_appear_twice(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    marker_id = catalogue["biomarkers"]["hemoglobina"]["id"]
    response = await _create(
        user_client,
        catalogue,
        results=[{"biomarker_id": marker_id, "value": 1}, {"biomarker_id": marker_id, "value": 2}],
    )
    assert response.status_code == 422


async def test_a_report_needs_at_least_one_result(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    assert (await _create(user_client, catalogue, results=[])).status_code == 422


async def test_listing_filters_by_date_and_counts_results(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    await _create(user_client, catalogue, collected_on="2026-01-15")
    await _create(user_client, catalogue, collected_on="2026-06-15")

    everything = (await user_client.get("/api/reports")).json()
    assert [item["collected_on"] for item in everything] == ["2026-06-15", "2026-01-15"]
    assert everything[0]["result_count"] == 1

    window = (await user_client.get("/api/reports?from=2026-05-01&to=2026-12-31")).json()
    assert [item["collected_on"] for item in window] == ["2026-06-15"]


async def test_delete_removes_the_report_and_its_results(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    report_id = (await _create(user_client, catalogue)).json()["id"]
    assert (await user_client.delete(f"/api/reports/{report_id}")).status_code == 204
    assert (await user_client.get(f"/api/reports/{report_id}")).status_code == 404
    marker_id = catalogue["biomarkers"]["hemoglobina"]["id"]
    assert (await user_client.get(f"/api/biomarkers/{marker_id}/series")).json()["points"] == []
