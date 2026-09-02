"""Two users, one database — the highest-priority property in the whole suite.

Health data has no sharing model in v1: if any of these fail, one household member
can read another's results, which is the worst thing this app could do.
"""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def _seed_user_data(ac: AsyncClient) -> dict[str, Any]:
    biomarkers = {item["slug"]: item for item in (await ac.get("/api/biomarkers")).json()}
    metrics = {item["slug"]: item for item in (await ac.get("/api/body/metrics")).json()}

    report = await ac.post(
        "/api/reports",
        json={
            "collected_on": "2026-03-01",
            "lab_name": "Synlab Braga",
            "results": [{"biomarker_id": biomarkers["hemoglobina"]["id"], "value": 14.1}],
        },
    )
    scan = await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [{"metric_id": metrics["bmi"]["id"], "value": 23.4}],
        },
    )
    intervention = await ac.post(
        "/api/interventions",
        json={"kind": "suplemento", "name": "Creatina", "started_on": "2026-02-01"},
    )
    return {
        "biomarkers": biomarkers,
        "metrics": metrics,
        "report": report.json(),
        "scan": scan.json(),
        "intervention": intervention.json(),
    }


async def test_lists_never_include_another_users_rows(make_user: UserFactory) -> None:
    alice, _ = await make_user()
    bob, _ = await make_user()
    await _seed_user_data(alice)

    assert (await bob.get("/api/reports")).json() == []
    assert (await bob.get("/api/body/scans")).json() == []
    assert (await bob.get("/api/body/summary")).json() == []
    assert (await bob.get("/api/interventions")).json() == []
    assert (await bob.get("/api/dashboard")).json()["categories"] == []


async def test_reading_by_id_is_scoped(make_user: UserFactory) -> None:
    alice, _ = await make_user()
    bob, _ = await make_user()
    data = await _seed_user_data(alice)

    assert (await bob.get(f"/api/reports/{data['report']['id']}")).status_code == 404


async def test_deleting_another_users_rows_is_a_404_not_a_deletion(
    make_user: UserFactory,
) -> None:
    alice, _ = await make_user()
    bob, _ = await make_user()
    data = await _seed_user_data(alice)

    assert (await bob.delete(f"/api/reports/{data['report']['id']}")).status_code == 404
    assert (await bob.delete(f"/api/body/scans/{data['scan']['id']}")).status_code == 404
    assert (await bob.delete(f"/api/interventions/{data['intervention']['id']}")).status_code == 404

    assert len((await alice.get("/api/reports")).json()) == 1
    assert len((await alice.get("/api/body/scans")).json()) == 1
    assert len((await alice.get("/api/interventions")).json()) == 1


async def test_patching_another_users_intervention_is_refused(make_user: UserFactory) -> None:
    alice, _ = await make_user()
    bob, _ = await make_user()
    data = await _seed_user_data(alice)

    response = await bob.patch(
        f"/api/interventions/{data['intervention']['id']}", json={"name": "Roubada"}
    )
    assert response.status_code == 404
    assert (await alice.get("/api/interventions")).json()[0]["name"] == "Creatina"


async def test_series_only_carry_the_callers_own_points(make_user: UserFactory) -> None:
    alice, _ = await make_user()
    bob, _ = await make_user()
    data = await _seed_user_data(alice)
    biomarker_id = data["biomarkers"]["hemoglobina"]["id"]
    metric_id = data["metrics"]["bmi"]["id"]

    assert (await alice.get(f"/api/biomarkers/{biomarker_id}/series")).json()["points"]
    assert (await bob.get(f"/api/biomarkers/{biomarker_id}/series")).json()["points"] == []
    assert (await bob.get(f"/api/body/metrics/{metric_id}/series")).json()["points"] == []


async def test_the_shared_catalogue_is_visible_to_everyone(make_user: UserFactory) -> None:
    """Scoping applies to the data, not to the catalogue — that one is shared by design."""
    alice, _ = await make_user()
    bob, _ = await make_user()
    assert len((await alice.get("/api/biomarkers")).json()) == 44
    assert len((await bob.get("/api/biomarkers")).json()) == 44
