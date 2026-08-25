"""Interventions CRUD and the overlay they produce on a series."""

from typing import Any

from httpx import AsyncClient

CREATINE = {
    "kind": "suplemento",
    "name": "Creatina monohidratada",
    "dose": "5 g/dia",
    "started_on": "2026-02-01",
}


async def test_create_list_and_filter(user_client: AsyncClient) -> None:
    assert (await user_client.post("/api/interventions", json=CREATINE)).status_code == 201
    await user_client.post(
        "/api/interventions",
        json={"kind": "treino", "name": "Hipertrofia 4x/semana", "started_on": "2026-01-01"},
    )

    everything = (await user_client.get("/api/interventions")).json()
    assert [item["name"] for item in everything] == [
        "Creatina monohidratada",
        "Hipertrofia 4x/semana",
    ]
    supplements = (await user_client.get("/api/interventions?kind=suplemento")).json()
    assert len(supplements) == 1


async def test_an_open_intervention_has_no_end_date(user_client: AsyncClient) -> None:
    created = (await user_client.post("/api/interventions", json=CREATINE)).json()
    assert created["ended_on"] is None

    ended = await user_client.patch(
        f"/api/interventions/{created['id']}", json={"ended_on": "2026-05-01"}
    )
    assert ended.json()["ended_on"] == "2026-05-01"


async def test_an_end_date_cannot_precede_the_start(user_client: AsyncClient) -> None:
    response = await user_client.post(
        "/api/interventions", json={**CREATINE, "ended_on": "2026-01-01"}
    )
    assert response.status_code == 422

    created = (await user_client.post("/api/interventions", json=CREATINE)).json()
    patched = await user_client.patch(
        f"/api/interventions/{created['id']}", json={"ended_on": "2025-12-01"}
    )
    assert patched.status_code == 422


async def test_delete(user_client: AsyncClient) -> None:
    created = (await user_client.post("/api/interventions", json=CREATINE)).json()
    assert (await user_client.delete(f"/api/interventions/{created['id']}")).status_code == 204
    assert (await user_client.get("/api/interventions")).json() == []


async def test_only_interventions_overlapping_the_points_are_returned(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    """An overlay stretching past the plotted range would suggest a correlation
    that is not on the chart."""
    marker_id = catalogue["biomarkers"]["hemoglobina"]["id"]
    for collected_on in ("2026-03-01", "2026-06-01"):
        await user_client.post(
            "/api/reports",
            json={
                "collected_on": collected_on,
                "lab_name": "Synlab",
                "results": [{"biomarker_id": marker_id, "value": 14}],
            },
        )

    await user_client.post(
        "/api/interventions",
        json={
            "kind": "suplemento",
            "name": "Dentro do período",
            "started_on": "2026-04-01",
            "ended_on": "2026-05-01",
        },
    )
    await user_client.post(
        "/api/interventions",
        json={
            "kind": "dieta",
            "name": "Terminou antes",
            "started_on": "2025-01-01",
            "ended_on": "2025-06-01",
        },
    )
    await user_client.post(
        "/api/interventions",
        json={"kind": "treino", "name": "Começou depois", "started_on": "2027-01-01"},
    )
    await user_client.post(
        "/api/interventions",
        json={"kind": "medicacao", "name": "Ainda em curso", "started_on": "2026-01-01"},
    )

    series = (await user_client.get(f"/api/biomarkers/{marker_id}/series")).json()
    assert sorted(item["name"] for item in series["interventions"]) == [
        "Ainda em curso",
        "Dentro do período",
    ]


async def test_no_points_means_no_overlay(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    await user_client.post("/api/interventions", json=CREATINE)
    marker_id = catalogue["biomarkers"]["hemoglobina"]["id"]
    series = (await user_client.get(f"/api/biomarkers/{marker_id}/series")).json()
    assert series["points"] == []
    assert series["interventions"] == []
