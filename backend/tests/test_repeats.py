"""Reminders to repeat one biomarker, and whether they still need to be."""

from datetime import date
from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


def _shift(months: int) -> tuple[int, int]:
    """(year, month) `months` away from today — negative goes to the past."""
    today = date.today()
    total = today.year * 12 + (today.month - 1) + months
    return total // 12, total % 12 + 1


async def _report(
    ac: AsyncClient,
    catalogue: dict[str, Any],
    collected_on: str,
    value: float = 22,
    biomarker: str = "vitamin-d-25-oh",
) -> str:
    marker = catalogue["biomarkers"][biomarker]["id"]
    response = await ac.post(
        "/api/reports",
        json={
            "collected_on": collected_on,
            "lab_name": "Synlab Braga",
            "results": [{"biomarker_id": marker, "value": value}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return str(body["results"][0]["id"])


async def _schedule(
    ac: AsyncClient, result_id: str, months_ahead: int = 3, note: str | None = None
) -> dict[str, Any]:
    year, month = _shift(months_ahead)
    payload: dict[str, Any] = {"result_id": result_id, "target_year": year, "target_month": month}
    if note is not None:
        payload["note"] = note
    response = await ac.post("/api/repeats", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_creating_a_repeat_resolves_the_biomarker_from_the_result(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    result_id = await _report(user_client, catalogue, "2026-01-12")
    body = await _schedule(user_client, result_id, note="Ver se a suplementação resultou")

    assert body["biomarker_slug"] == "vitamin-d-25-oh"
    assert body["biomarker_name"] == "Vitamina D (25-OH)"
    assert body["source_result_id"] == result_id
    assert body["note"] == "Ver se a suplementação resultou"
    assert body["status"] == "upcoming"


async def test_a_target_in_the_past_is_rejected(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    result_id = await _report(user_client, catalogue, "2026-01-12")
    response = await user_client.post(
        "/api/repeats",
        json={"result_id": result_id, "target_year": 2020, "target_month": 1},
    )
    assert response.status_code == 422


async def test_a_target_too_far_ahead_is_rejected(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    result_id = await _report(user_client, catalogue, "2026-01-12")
    response = await user_client.post(
        "/api/repeats",
        json={"result_id": result_id, "target_year": date.today().year + 50, "target_month": 1},
    )
    assert response.status_code == 422


async def test_scheduling_from_someone_elses_result_is_refused(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    mine, _ = await make_user()
    theirs, _ = await make_user()
    result_id = await _report(theirs, catalogue, "2026-01-12")
    year, month = _shift(3)
    response = await mine.post(
        "/api/repeats",
        json={"result_id": result_id, "target_year": year, "target_month": month},
    )
    assert response.status_code == 404


async def test_status_is_upcoming_until_the_target_month_arrives(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    result_id = await _report(user_client, catalogue, "2026-01-12")
    await _schedule(user_client, result_id, months_ahead=6)

    listed = (await user_client.get("/api/repeats")).json()
    assert listed[0]["status"] == "upcoming"


async def test_status_is_due_once_the_target_month_has_come_with_nothing_newer(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    result_id = await _report(user_client, catalogue, "2026-01-12")
    await _schedule(user_client, result_id, months_ahead=0)

    listed = (await user_client.get("/api/repeats")).json()
    assert listed[0]["status"] == "due"


async def test_a_newer_result_fulfils_the_schedule_even_before_the_target_month(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    """The point was a fresh reading. Once one exists, the reminder has done its job."""
    result_id = await _report(user_client, catalogue, "2026-01-12")
    await _schedule(user_client, result_id, months_ahead=6)
    await _report(user_client, catalogue, "2026-02-01", value=30)

    listed = (await user_client.get("/api/repeats")).json()
    assert listed[0]["status"] == "fulfilled"


async def test_listing_filters_by_status(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    due_result = await _report(user_client, catalogue, "2026-01-12")
    await _schedule(user_client, due_result, months_ahead=0)

    upcoming_result = await _report(
        user_client, catalogue, "2026-01-13", value=145, biomarker="ferritina"
    )
    await _schedule(user_client, upcoming_result, months_ahead=6)

    due_only = (await user_client.get("/api/repeats?status=due")).json()
    assert len(due_only) == 1
    assert due_only[0]["status"] == "due"

    upcoming_only = (await user_client.get("/api/repeats?status=upcoming")).json()
    assert len(upcoming_only) == 1
    assert upcoming_only[0]["status"] == "upcoming"


async def test_deleting_a_schedule(user_client: AsyncClient, catalogue: dict[str, Any]) -> None:
    result_id = await _report(user_client, catalogue, "2026-01-12")
    body = await _schedule(user_client, result_id)

    assert (await user_client.delete(f"/api/repeats/{body['id']}")).status_code == 204
    assert (await user_client.get("/api/repeats")).json() == []


async def test_deleting_someone_elses_schedule_is_refused(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    mine, _ = await make_user()
    theirs, _ = await make_user()
    result_id = await _report(theirs, catalogue, "2026-01-12")
    body = await _schedule(theirs, result_id)

    assert (await mine.delete(f"/api/repeats/{body['id']}")).status_code == 404


async def test_deleting_the_source_report_does_not_delete_the_schedule(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    """The reminder outlives the draw that prompted it — it is checked against a
    snapshot of that draw's date, not a live pointer to it."""
    result_id = await _report(user_client, catalogue, "2026-01-12")
    reports = (await user_client.get("/api/reports")).json()
    await _schedule(user_client, result_id, months_ahead=0)

    assert (await user_client.delete(f"/api/reports/{reports[0]['id']}")).status_code == 204

    listed = (await user_client.get("/api/repeats")).json()
    assert len(listed) == 1
    assert listed[0]["source_result_id"] is None
    assert listed[0]["status"] == "due"


async def test_the_dashboard_surfaces_only_due_repeats(
    user_client: AsyncClient, catalogue: dict[str, Any]
) -> None:
    due_result = await _report(user_client, catalogue, "2026-01-12")
    await _schedule(user_client, due_result, months_ahead=0, note="repetir agora")

    upcoming_result = await _report(
        user_client, catalogue, "2026-01-13", value=145, biomarker="ferritina"
    )
    await _schedule(user_client, upcoming_result, months_ahead=6)

    dashboard = (await user_client.get("/api/dashboard")).json()
    assert len(dashboard["due_repeats"]) == 1
    assert dashboard["due_repeats"][0]["note"] == "repetir agora"


async def test_schedules_never_leak_between_accounts(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    mine, _ = await make_user()
    theirs, _ = await make_user()
    result_id = await _report(theirs, catalogue, "2026-01-12")
    await _schedule(theirs, result_id)

    assert (await mine.get("/api/repeats")).json() == []
