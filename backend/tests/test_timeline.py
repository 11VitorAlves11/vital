"""The event timeline — backlog 2.1 and 2.2.

One chronological list across four tables, paged by date, filtered by kind.
"""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def _report(
    ac: AsyncClient, catalogue: dict[str, Any], collected_on: str, **extra: Any
) -> Any:
    payload = {
        "collected_on": collected_on,
        "lab_name": "Synlab Braga",
        "results": [{"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 14.1}],
        **extra,
    }
    response = await ac.post("/api/reports", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _intervention(ac: AsyncClient, **extra: Any) -> Any:
    payload = {"kind": "suplemento", "name": "Vitamina D", "started_on": "2025-10-01", **extra}
    response = await ac.post("/api/interventions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _scan(ac: AsyncClient, catalogue: dict[str, Any], measured_at: str) -> Any:
    response = await ac.post(
        "/api/body/scans",
        json={
            "measured_at": measured_at,
            "device": "Tanita",
            "values": [{"metric_id": catalogue["metrics"]["bmi"]["id"], "value": 24.2}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_the_timeline_merges_every_source_newest_first(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    await _report(ac, catalogue, "2026-03-01")
    await _scan(ac, catalogue, "2026-05-01T08:00:00Z")
    await _intervention(ac)

    body = (await ac.get("/api/timeline")).json()
    assert [event["kind"] for event in body["events"]] == [
        "body_composition",
        "lab_report",
        "intervention",
    ]
    assert [event["occurred_on"] for event in body["events"]] == [
        "2026-05-01",
        "2026-03-01",
        "2025-10-01",
    ]


async def test_an_event_with_duration_says_so(make_user: UserFactory) -> None:
    """A supplement started in October and never stopped is a period, not a point."""
    ac, _ = await make_user()
    await _intervention(ac)
    [event] = (await ac.get("/api/timeline")).json()["events"]
    assert event["has_duration"] is True
    assert event["ended_on"] is None
    assert event["intervention_kind"] == "suplemento"


async def test_the_hour_travels_only_where_it_means_something(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    await _report(ac, catalogue, "2026-03-01", collected_at="2026-03-01T08:15:00")
    await _intervention(ac)

    events = {event["kind"]: event for event in (await ac.get("/api/timeline")).json()["events"]}
    assert events["lab_report"]["occurred_at"] == "2026-03-01T08:15:00"
    # A supplement did not start at an hour; claiming one would be an invention.
    assert events["intervention"]["occurred_at"] is None


async def test_a_report_card_carries_what_is_out_of_range(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    await _report(
        ac,
        catalogue,
        "2026-03-01",
        results=[
            {"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 11},
            {"biomarker_id": catalogue["biomarkers"]["ferritina"]["id"], "value": 200},
        ],
    )
    [event] = (await ac.get("/api/timeline")).json()["events"]
    # Only what is worth a glance: a normal value says nothing a count does not.
    assert [item["label"] for item in event["summary"]] == ["Hemoglobina"]
    assert event["summary"][0]["flag"] == "low"
    assert event["summary"][0]["value"] == "11 g/dL"


async def test_the_filter_offers_only_the_kinds_that_exist(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """A control that can only ever return nothing is a dead end."""
    ac, _ = await make_user(sex="M")
    assert (await ac.get("/api/timeline")).json()["available_kinds"] == []

    await _report(ac, catalogue, "2026-03-01")
    await _intervention(ac)
    body = (await ac.get("/api/timeline")).json()
    assert body["available_kinds"] == ["lab_report", "intervention"]


async def test_filtering_by_kind_narrows_the_list(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    await _report(ac, catalogue, "2026-03-01")
    await _intervention(ac)

    body = (await ac.get("/api/timeline?kinds=intervention")).json()
    assert [event["kind"] for event in body["events"]] == ["intervention"]
    # The filter's own options still come from the whole history.
    assert body["available_kinds"] == ["lab_report", "intervention"]


async def test_paging_walks_backwards_without_losing_a_day(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user(sex="M")
    days = [f"2026-0{month}-01" for month in range(1, 7)]
    for day in days:
        await _report(ac, catalogue, day)

    seen: list[str] = []
    cursor: str | None = ""
    while cursor is not None:
        query = f"?limit=2&before={cursor}" if cursor else "?limit=2"
        body = (await ac.get(f"/api/timeline{query}")).json()
        seen += [event["occurred_on"] for event in body["events"]]
        cursor = body["next_before"]

    # Every day exactly once, newest first, with no overlap between pages.
    assert seen == sorted(days, reverse=True)


async def test_one_account_never_sees_anothers_timeline(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    alice, _ = await make_user(sex="M")
    bob, _ = await make_user(sex="M")
    await _report(alice, catalogue, "2026-03-01")

    assert (await bob.get("/api/timeline")).json()["events"] == []


async def test_a_day_that_fills_a_page_is_not_dropped(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """The one case with no day boundary to cut at: returning nothing would
    leave the reader on a page that never advances."""
    ac, _ = await make_user(sex="M")
    for lab in ("Synlab", "Unilabs", "Germano de Sousa"):
        await _report(ac, catalogue, "2026-03-01", lab_name=lab)

    body = (await ac.get("/api/timeline?limit=2")).json()
    assert len(body["events"]) == 2
    assert body["next_before"] == "2026-03-01"
