"""Indices height makes computable, and the ones it deliberately does not."""

from decimal import Decimal
from typing import Any

from httpx import AsyncClient

from app.services import anthropometrics
from tests.conftest import UserFactory


def test_an_index_is_mass_over_height_squared() -> None:
    # 78 kg at 1.78 m is 24.6 kg/m².
    [derived] = anthropometrics.derive({"weight": Decimal("78")}, Decimal("178"))
    assert derived.metric_slug == "bmi"
    assert derived.value == Decimal("24.6")
    assert derived.source_slug == "weight"


def test_nothing_is_derived_without_a_height() -> None:
    """The same rule as an unknown sex: no height, no index — never a guess."""
    assert anthropometrics.derive({"weight": Decimal("78")}, None) == []


def test_a_metric_the_scale_reported_is_left_alone() -> None:
    """The scale's own BMI was computed from the height in the device, which may
    be truer than a profile field nobody has touched in two years."""
    derived = anthropometrics.derive(
        {"weight": Decimal("78"), "bmi": Decimal("30")}, Decimal("178")
    )
    assert [item.metric_slug for item in derived] == []


def test_muscle_mass_yields_no_index() -> None:
    """EWGSOP2's 7.0/5.5 cut-offs are for *appendicular* muscle mass. A scale
    reports whole-body, which is around a third larger — dividing it by height
    squared and calling it ASMI would clear almost everyone."""
    derived = anthropometrics.derive({"skeletal-muscle-mass": Decimal("34")}, Decimal("178"))
    assert derived == []


async def test_the_profile_carries_height(user_client: AsyncClient) -> None:
    assert (await user_client.get("/api/users/me")).json()["height_cm"] is None
    updated = (await user_client.patch("/api/users/me", json={"height_cm": 178})).json()
    assert updated["height_cm"] == "178.0"


async def test_an_impossible_height_is_refused(user_client: AsyncClient) -> None:
    """A typo in height moves every derived index without looking wrong itself."""
    for value in (17.8, 1780):
        assert (
            await user_client.patch("/api/users/me", json={"height_cm": value})
        ).status_code == 422


async def test_a_weigh_in_gains_its_indices_once_height_is_known(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    metrics = catalogue["metrics"]
    scan = {
        "measured_at": "2026-03-01T08:00:00Z",
        "values": [
            {"metric_id": metrics["weight"]["id"], "value": 78},
            {"metric_id": metrics["fat-free-mass"]["id"], "value": 62},
            {"metric_id": metrics["fat-mass"]["id"], "value": 16},
        ],
    }

    without = (await ac.post("/api/body/scans", json=scan)).json()
    assert {value["metric_slug"] for value in without["values"]} == {
        "weight",
        "fat-free-mass",
        "fat-mass",
    }

    await ac.patch("/api/users/me", json={"height_cm": 178})
    scan["measured_at"] = "2026-06-01T08:00:00Z"
    with_height = (await ac.post("/api/body/scans", json=scan)).json()
    derived = {
        value["metric_slug"]: value
        for value in with_height["values"]
        if value["derived_from"] is not None
    }
    assert set(derived) == {"bmi", "ffmi", "fmi"}
    assert derived["bmi"]["value"] == "24.6"
    assert derived["ffmi"]["value"] == "19.6"
    assert derived["fmi"]["value"] == "5.0"
    # Marked as computed, and with no row of its own to be mistaken for one.
    assert derived["ffmi"]["derived_from"] == "fat-free-mass"
    assert derived["ffmi"]["id"] is None


async def test_a_derived_index_is_classified_like_any_other_value(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """FFMI below the GLIM threshold is the point of computing it at all."""
    ac, _ = await make_user(sex="M")
    await ac.patch("/api/users/me", json={"height_cm": 180})
    await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            # 54 kg of fat-free mass at 1.80 m is 16.7 kg/m², under the 17 cut-off.
            "values": [{"metric_id": catalogue["metrics"]["fat-free-mass"]["id"], "value": 54}],
        },
    )
    summary = {item["metric"]["slug"]: item for item in (await ac.get("/api/body/summary")).json()}
    assert summary["ffmi"]["latest"]["value"] == "16.7"
    assert summary["ffmi"]["latest"]["flag"] == "alert"
    assert summary["ffmi"]["latest"]["label"] == "Massa magra reduzida"


async def test_a_derived_index_has_a_series_of_its_own(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    await ac.patch("/api/users/me", json={"height_cm": 178})
    for moment, mass in (("2026-01-01T08:00:00Z", 60), ("2026-06-01T08:00:00Z", 63)):
        await ac.post(
            "/api/body/scans",
            json={
                "measured_at": moment,
                "values": [
                    {"metric_id": catalogue["metrics"]["fat-free-mass"]["id"], "value": mass}
                ],
            },
        )

    ffmi_id = catalogue["metrics"]["ffmi"]["id"]
    series = (await ac.get(f"/api/body/metrics/{ffmi_id}/series")).json()
    assert [point["value"] for point in series["points"]] == ["18.9", "19.9"]


async def test_correcting_the_height_moves_every_index(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """Computed on read, so a corrected height corrects the whole history at once
    rather than leaving stored indices behind at the old one."""
    ac, _ = await make_user(sex="M")
    await ac.patch("/api/users/me", json={"height_cm": 178})
    await ac.post(
        "/api/body/scans",
        json={
            "measured_at": "2026-03-01T08:00:00Z",
            "values": [{"metric_id": catalogue["metrics"]["weight"]["id"], "value": 78}],
        },
    )

    def bmi(body: list[dict[str, Any]]) -> str:
        return next(item["latest"]["value"] for item in body if item["metric"]["slug"] == "bmi")

    assert bmi((await ac.get("/api/body/summary")).json()) == "24.6"
    await ac.patch("/api/users/me", json={"height_cm": 168})
    assert bmi((await ac.get("/api/body/summary")).json()) == "27.6"
