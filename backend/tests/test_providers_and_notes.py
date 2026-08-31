"""Laboratories and doctors as entities, notes at two levels, and the prefill.

Backlog 1.7, 1.8 and 4.2 — all three of which turn on a report knowing which
laboratory issued it.
"""

from typing import Any

from httpx import AsyncClient

from tests.conftest import UserFactory


async def _report(ac: AsyncClient, catalogue: dict[str, Any], **overrides: Any) -> Any:
    payload: dict[str, Any] = {
        "collected_on": "2026-03-01",
        "lab_name": "Synlab Braga",
        "results": [{"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 14.1}],
    }
    payload.update(overrides)
    response = await ac.post("/api/reports", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_two_reports_from_one_lab_share_its_entity(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """The acceptance criterion for 1.7, under the spellings a human produces."""
    ac, _ = await make_user()
    first = await _report(ac, catalogue, lab_name="Synlab Braga")
    second = await _report(ac, catalogue, collected_on="2026-06-01", lab_name="SYNLAB  braga")

    assert first["lab_id"] == second["lab_id"]
    labs = (await ac.get("/api/labs")).json()
    assert len(labs) == 1
    # Stored under the first spelling used; the second does not rename it.
    assert labs[0]["name"] == "Synlab Braga"
    assert labs[0]["report_count"] == 2


async def test_a_different_lab_is_a_different_entity(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user()
    await _report(ac, catalogue, lab_name="Synlab")
    await _report(ac, catalogue, collected_on="2026-06-01", lab_name="Unilabs")
    assert {lab["name"] for lab in (await ac.get("/api/labs")).json()} == {"Synlab", "Unilabs"}


async def test_one_account_never_sees_anothers_labs(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """Per-account, not global: a shared instance must not leak where people go."""
    alice, _ = await make_user()
    bob, _ = await make_user()
    await _report(alice, catalogue, lab_name="Synlab Braga")

    assert (await bob.get("/api/labs")).json() == []
    await _report(bob, catalogue, lab_name="Synlab Braga")
    alice_labs = (await alice.get("/api/labs")).json()
    bob_labs = (await bob.get("/api/labs")).json()
    assert alice_labs[0]["id"] != bob_labs[0]["id"]


async def test_the_history_can_be_filtered_by_origin(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user()
    synlab = await _report(ac, catalogue, lab_name="Synlab")
    await _report(ac, catalogue, collected_on="2026-06-01", lab_name="Unilabs")

    filtered = (await ac.get(f"/api/reports?lab_id={synlab['lab_id']}")).json()
    assert [item["id"] for item in filtered] == [synlab["id"]]


async def test_a_doctor_is_optional_and_reusable(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user()
    without = await _report(ac, catalogue)
    assert without["doctor_id"] is None

    first = await _report(ac, catalogue, collected_on="2026-04-01", doctor_name="Dra. Sofia Nunes")
    second = await _report(ac, catalogue, collected_on="2026-06-01", doctor_name="dra sofia nunes")
    assert first["doctor_id"] == second["doctor_id"]
    assert first["doctor_name"] == "Dra. Sofia Nunes"
    assert len((await ac.get("/api/doctors")).json()) == 1


async def test_a_report_note_is_stamped_when_it_is_written(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user()
    report = await _report(ac, catalogue)
    assert report["notes"] is None
    assert report["notes_at"] is None

    patched = (
        await ac.patch(f"/api/reports/{report['id']}", json={"notes": "Ferritina a subir."})
    ).json()
    assert patched["notes"] == "Ferritina a subir."
    assert patched["notes_at"] is not None


async def test_re_saving_an_unchanged_note_does_not_restamp_it(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """A year-old reading must not start looking like today's."""
    ac, _ = await make_user()
    report = await _report(ac, catalogue, notes="Primeira colheita do ano.")
    stamped = report["notes_at"]
    assert stamped is not None

    again = (
        await ac.patch(f"/api/reports/{report['id']}", json={"notes": "Primeira colheita do ano."})
    ).json()
    assert again["notes_at"] == stamped


async def test_a_note_lands_on_the_single_result_it_is_about(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """The acceptance criterion for 1.8: the note belongs to the point, not the draw."""
    ac, _ = await make_user()
    report = await _report(ac, catalogue)
    result_id = report["results"][0]["id"]

    patched = (
        await ac.patch(
            f"/api/reports/{report['id']}/results/{result_id}",
            json={"note": "Colheita às 11:30, fora da janela recomendada."},
        )
    ).json()
    assert patched["note"] == "Colheita às 11:30, fora da janela recomendada."
    assert patched["note_at"] is not None
    # And it comes back with the report, not only from the patch.
    fetched = (await ac.get(f"/api/reports/{report['id']}")).json()
    assert fetched["results"][0]["note"] == patched["note"]


async def test_a_note_can_be_written_with_the_result(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    ac, _ = await make_user()
    report = await _report(
        ac,
        catalogue,
        results=[
            {
                "biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"],
                "value": 14.1,
                "note": "Dador de sangue na semana anterior.",
            }
        ],
    )
    assert report["results"][0]["note"] == "Dador de sangue na semana anterior."


async def test_another_accounts_report_cannot_be_annotated(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    alice, _ = await make_user()
    bob, _ = await make_user()
    report = await _report(alice, catalogue)

    assert (await bob.patch(f"/api/reports/{report['id']}", json={"notes": "x"})).status_code == 404
    result_id = report["results"][0]["id"]
    response = await bob.patch(
        f"/api/reports/{report['id']}/results/{result_id}", json={"note": "x"}
    )
    assert response.status_code == 404


async def test_prefill_offers_the_last_reading_of_each_marker(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """Backlog 4.2: a known value should cost a biomarker, a value and a date."""
    ac, _ = await make_user()
    marker_id = catalogue["biomarkers"]["hemoglobina"]["id"]
    for collected_on, ref_max in (("2026-01-01", 17.0), ("2026-06-01", 17.5)):
        await _report(
            ac,
            catalogue,
            collected_on=collected_on,
            results=[
                {
                    "biomarker_id": marker_id,
                    "value": 14.1,
                    "unit": "g/dL",
                    "ref_min": 13,
                    "ref_max": ref_max,
                    "method": "Citometria de fluxo",
                }
            ],
        )

    [suggestion] = (await ac.get("/api/reports/prefill")).json()
    assert suggestion["biomarker_id"] == marker_id
    # The most recent one, not the first.
    assert suggestion["ref_max"] == "17.5000"
    assert suggestion["unit"] == "g/dL"
    assert suggestion["method"] == "Citometria de fluxo"
    assert suggestion["collected_on"] == "2026-06-01"
    assert suggestion["lab_name"] == "Synlab Braga"
    assert suggestion["same_lab"] is False


async def test_prefill_can_be_narrowed_to_one_laboratory(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    """A reference range belongs to the laboratory that issued it."""
    ac, _ = await make_user()
    marker_id = catalogue["biomarkers"]["hemoglobina"]["id"]
    synlab = await _report(
        ac,
        catalogue,
        lab_name="Synlab",
        results=[{"biomarker_id": marker_id, "value": 14.1, "ref_min": 13, "ref_max": 17}],
    )
    await _report(
        ac,
        catalogue,
        collected_on="2026-06-01",
        lab_name="Unilabs",
        results=[{"biomarker_id": marker_id, "value": 14.4, "ref_min": 13.5, "ref_max": 17.5}],
    )

    # Unfiltered, the newest wins; filtered, the laboratory's own range does.
    unfiltered = (await ac.get("/api/reports/prefill")).json()
    assert unfiltered[0]["ref_min"] == "13.5000"
    # Marked as coming from somewhere else, so the range is not applied blind.
    assert unfiltered[0]["same_lab"] is False

    narrowed = (await ac.get(f"/api/reports/prefill?lab_id={synlab['lab_id']}")).json()
    assert narrowed[0]["ref_min"] == "13.0000"
    assert narrowed[0]["lab_name"] == "Synlab"
    assert narrowed[0]["same_lab"] is True


async def test_prefill_never_reaches_another_account(
    make_user: UserFactory, catalogue: dict[str, Any]
) -> None:
    alice, _ = await make_user()
    bob, _ = await make_user()
    await _report(alice, catalogue)
    assert (await bob.get("/api/reports/prefill")).json() == []
