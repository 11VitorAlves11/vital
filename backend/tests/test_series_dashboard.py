"""Series and dashboard response shapes — what the charts are drawn from."""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def test_biomarker_series_is_chronological_and_carries_the_ranges(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    marker_id = catalogue["biomarkers"]["hemoglobina"]["id"]
    for collected_on, value in (("2026-06-01", 15.2), ("2026-01-01", 14.0)):
        await ac.post(
            "/api/reports",
            json={
                "collected_on": collected_on,
                "lab_name": "Synlab",
                "results": [
                    {
                        "biomarker_id": marker_id,
                        "value": value,
                        "ref_min": 13.5,
                        "ref_max": 17.5,
                    }
                ],
            },
        )

    series = (await ac.get(f"/api/biomarkers/{marker_id}/series")).json()
    assert [point["date"] for point in series["points"]] == ["2026-01-01", "2026-06-01"]
    point = series["points"][0]
    assert point["ref_min"] == "13.5000"
    assert point["ref_max"] == "17.5000"
    assert point["unit"] == "g/dL"
    assert point["lab_name"] == "Synlab"
    assert point["flag"] == "normal"
    # The canonical range travels with the catalogue entry — the dashed line.
    assert series["biomarker"]["ref_min"] == "13.0000"
    assert series["biomarker"]["ref_max"] == "17.0000"


async def test_body_series_carries_flag_and_label_per_point(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    metric_id = catalogue["metrics"]["bmi"]["id"]
    for moment, value in (("2026-01-01T08:00:00Z", 27), ("2026-06-01T08:00:00Z", 24)):
        await ac.post(
            "/api/body/scans",
            json={"measured_at": moment, "values": [{"metric_id": metric_id, "value": value}]},
        )

    series = (await ac.get(f"/api/body/metrics/{metric_id}/series")).json()
    assert [point["flag"] for point in series["points"]] == ["warn", "normal"]
    assert [point["label"] for point in series["points"]] == ["Pré-obesidade", "Normal"]
    assert len(series["metric"]["bands"]) == 6


async def test_series_of_an_unknown_id_is_a_404(user_client: AsyncClient) -> None:
    assert (await user_client.get("/api/biomarkers/999999/series")).status_code == 404
    assert (await user_client.get("/api/body/metrics/999999/series")).status_code == 404


async def test_dashboard_groups_by_category_with_the_latest_value(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    haemoglobin = catalogue["biomarkers"]["hemoglobina"]["id"]
    ferritin = catalogue["biomarkers"]["ferritina"]["id"]

    await ac.post(
        "/api/reports",
        json={
            "collected_on": "2026-01-01",
            "lab_name": "Synlab",
            "results": [
                {"biomarker_id": haemoglobin, "value": 14.0},
                {"biomarker_id": ferritin, "value": 60},
            ],
        },
    )
    await ac.post(
        "/api/reports",
        json={
            "collected_on": "2026-06-01",
            "lab_name": "Unilabs",
            "results": [{"biomarker_id": haemoglobin, "value": 15.5}],
        },
    )

    payload = (await ac.get("/api/dashboard")).json()
    assert payload["last_report_on"] == "2026-06-01"
    assert payload["report_count"] == 2

    categories = {entry["category"]: entry["items"] for entry in payload["categories"]}
    assert set(categories) == {"hematologia", "ferro"}

    haemoglobin_card = categories["hematologia"][0]
    assert haemoglobin_card["value"] == "15.5000"
    assert haemoglobin_card["collected_on"] == "2026-06-01"
    assert haemoglobin_card["lab_name"] == "Unilabs"
    assert haemoglobin_card["flag"] == "normal"
    assert [point["value"] for point in haemoglobin_card["sparkline"]] == ["14.0000", "15.5000"]

    # A biomarker measured once still gets a card, with a one-point sparkline.
    assert len(categories["ferro"][0]["sparkline"]) == 1


async def test_dashboard_is_empty_before_the_first_report(user_client: AsyncClient) -> None:
    payload = (await user_client.get("/api/dashboard")).json()
    assert payload == {"categories": [], "last_report_on": None, "report_count": 0}
