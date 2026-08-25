"""Body composition: scans, clinically recomputed flags, and the metrics grid."""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def test_bmi_bands_match_the_who_classification(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    bmi_id = catalogue["metrics"]["bmi"]["id"]

    overweight = await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [{"metric_id": bmi_id, "value": 27}],
        },
    )
    assert overweight.status_code == 201
    value = overweight.json()["values"][0]
    assert value["flag"] == "warn"
    assert value["label"] == "Pré-obesidade"

    normal = await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-04-01T08:00:00Z",
            "values": [{"metric_id": bmi_id, "value": 22}],
        },
    )
    assert normal.json()["values"][0]["flag"] == "normal"
    assert normal.json()["values"][0]["label"] == "Normal"


async def test_trend_only_metrics_are_never_flagged(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    response = await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [
                {"metric_id": catalogue["metrics"]["weight"]["id"], "value": 82.4},
                {"metric_id": catalogue["metrics"]["metabolic-age"]["id"], "value": 31},
                {"metric_id": catalogue["metrics"]["visceral-fat-index"]["id"], "value": 9},
            ],
        },
    )
    for value in response.json()["values"]:
        assert value["flag"] is None, value
        assert value["label"] is None, value


async def test_bands_follow_the_users_sex(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """22% body fat is 'aceitável' for a man and 'fitness' for a woman."""
    metric_id = catalogue["metrics"]["body-fat-pct"]["id"]
    payload = {
        "measured_at": "2026-03-01T08:00:00Z",
        "values": [{"metric_id": metric_id, "value": 22}],
    }

    man, _ = await make_user(sex="M")
    woman, _ = await make_user(sex="F")

    assert (await man.post("/api/body/scans", json=payload)).json()["values"][0][
        "label"
    ] == "Aceitável"
    assert (await woman.post("/api/body/scans", json=payload)).json()["values"][0][
        "label"
    ] == "Fitness"


async def test_no_flag_while_the_sex_is_unknown(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex=None)
    response = await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [{"metric_id": catalogue["metrics"]["bmi"]["id"], "value": 27}],
        },
    )
    assert response.json()["values"][0]["flag"] is None
    # The catalogue still says a standard exists, so the UI can ask for the missing bit.
    assert (await ac.get("/api/body/metrics")).json()[0]["source"] == "OMS"


async def test_setting_the_sex_later_flags_the_existing_history(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex=None)
    await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [{"metric_id": catalogue["metrics"]["bmi"]["id"], "value": 27}],
        },
    )
    await ac.patch("/api/users/me", json={"sex": "F"})
    assert (await ac.get("/api/body/scans")).json()[0]["values"][0]["flag"] == "warn"


async def test_the_same_metric_cannot_appear_twice_in_a_scan(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    metric_id = catalogue["metrics"]["weight"]["id"]
    response = await user_client.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [
                {"metric_id": metric_id, "value": 80},
                {"metric_id": metric_id, "value": 81},
            ],
        },
    )
    assert response.status_code == 422


async def test_unknown_metric_is_rejected(user_client: AsyncClient) -> None:
    response = await user_client.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [{"metric_id": 999_999, "value": 1}],
        },
    )
    assert response.status_code == 422


async def test_scan_listing_filters_by_date(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    weight_id = catalogue["metrics"]["weight"]["id"]
    for moment in ("2026-01-05T08:00:00Z", "2026-07-05T08:00:00Z"):
        await user_client.post(
            "/api/body/scans",
            json={"measured_at": moment, "values": [{"metric_id": weight_id, "value": 80}]},
        )

    everything = (await user_client.get("/api/body/scans")).json()
    assert len(everything) == 2
    window = (await user_client.get("/api/body/scans?from=2026-06-01&to=2026-12-31")).json()
    assert len(window) == 1
    assert window[0]["measured_at"].startswith("2026-07-05")


async def test_summary_carries_the_latest_value_and_a_sparkline(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    weight_id = catalogue["metrics"]["weight"]["id"]
    for moment, value in (("2026-01-05T08:00:00Z", 84), ("2026-02-05T08:00:00Z", 82)):
        await ac.post(
            "/api/body/scans",
            json={"measured_at": moment, "values": [{"metric_id": weight_id, "value": value}]},
        )

    summary = {item["metric"]["slug"]: item for item in (await ac.get("/api/body/summary")).json()}
    assert summary["weight"]["latest"]["value"] == "82.0000"
    assert [point["value"] for point in summary["weight"]["sparkline"]] == ["84.0000", "82.0000"]
    # Metrics never measured stay off the grid rather than showing an empty card.
    assert "bmi" not in summary


async def test_delete_removes_the_scan(user_client: AsyncClient, catalogue: dict[str, Any]) -> None:
    response = await user_client.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [{"metric_id": catalogue["metrics"]["weight"]["id"], "value": 80}],
        },
    )
    scan_id = response.json()["id"]
    assert (await user_client.delete(f"/api/body/scans/{scan_id}")).status_code == 204
    assert (await user_client.get("/api/body/scans")).json() == []
    assert (await user_client.delete(f"/api/body/scans/{scan_id}")).status_code == 404
