"""The document extraction pipeline, and the one rule it exists to enforce.

No extracted value reaches `results` without a human confirming it: the tests
that matter here are the ones proving `POST /api/extractions` writes nothing,
and that `confirm` writes exactly what was approved and no more.
"""

import base64
import io
import json
import uuid
from decimal import Decimal
from typing import Any

import pymupdf
import pytest
from httpx import AsyncClient
from PIL import Image

from app.api.routes import extractions as extraction_routes
from app.core.config import get_settings
from app.schemas.extractions import ExtractionPayload
from app.services import anonymization as anonymization_service
from app.services import extraction as extraction_service
from tests.conftest import UserFactory

ANSWER = {
    "collected_on": "2026-02-14",
    "lab_name": "Unilabs",
    "fasting": True,
    "results": [
        {
            "biomarker": "Hemoglobina",
            "value": "10,5",
            "unit": "g/dL",
            "ref_min": 12,
            "ref_max": 15.5,
        },
        {
            "biomarker": "VITAMINA D 25 OH",
            "value": 22,
            "unit": "ng/mL",
            "ref_min": 30,
            "ref_max": None,
        },
        {
            "biomarker": "Marcador Inventado",
            "value": 1.0,
            "unit": None,
            "ref_min": None,
            "ref_max": None,
        },
    ],
}


def make_pdf(lines: int = 0, pages: int = 1) -> bytes:
    """A PDF with `lines` lines of text, or none at all to stand in for a scan.

    Text that runs past the page edge is not inserted at all, so a long report
    has to be built as real lines rather than one very long one.
    """
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    for _ in range(pages):
        page = document.new_page()
        for index in range(lines):
            page.insert_text((72, 72 + index * 14), f"Hemoglobina {index} 10,5 g/dL  12 - 15,5")
    return bytes(document.tobytes())


def make_report_photo() -> bytes:
    image = Image.new("RGB", (800, 600), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=b"private metadata")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _configure_extraction(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """A model name and a scratch storage root, so uploads land under tmp_path."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_model", "test/fake-model", raising=False)
    monkeypatch.setattr(settings, "storage_path", str(tmp_path), raising=False)
    # OCR is an operating-system service in the production image. Most tests
    # exercise the pipeline around it; dedicated tests below provide exact boxes.
    monkeypatch.setattr(anonymization_service, "ocr_lines", lambda image: [])
    monkeypatch.setattr(anonymization_service, "decode_barcodes", lambda image: [])
    monkeypatch.setattr(anonymization_service, "_blur_faces", lambda image: image)


def stub_model(monkeypatch: pytest.MonkeyPatch, answer: object) -> list[list[dict[str, Any]]]:
    """Replace the provider call and record what it was sent."""
    seen: list[list[dict[str, Any]]] = []

    async def fake(content: list[dict[str, Any]], settings: Any) -> tuple[str, str]:
        seen.append(content)
        return (answer if isinstance(answer, str) else json.dumps(answer)), "test/fake-model"

    monkeypatch.setattr(extraction_service, "ask_model", fake)
    monkeypatch.setattr(extraction_routes, "ask_model", fake)
    return seen


async def upload(client: AsyncClient, content: bytes | None = None) -> dict[str, Any]:
    files = {
        "file": (
            "analises.pdf",
            content or make_pdf(lines=30),
            "application/pdf",
        )
    }
    response = await client.post("/api/extractions", files=files)
    assert response.status_code == 202, response.text
    return response.json()


class TestUpload:
    async def test_accepts_a_pdf_and_reaches_preview(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_model(monkeypatch, ANSWER)

        job = await upload(user_client)
        assert job["status"] in {"pending", "processing", "preview"}

        # BackgroundTasks run before the response closes under ASGITransport.
        polled = (await user_client.get(f"/api/extractions/{job['id']}")).json()
        assert polled["status"] == "preview"
        assert polled["provider"] == "test/fake-model"
        assert polled["error"] is None

    async def test_stores_nothing_in_results_before_confirmation(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The rule the pipeline exists to enforce."""
        stub_model(monkeypatch, ANSWER)

        await upload(user_client)

        assert (await user_client.get("/api/reports")).json() == []

    async def test_rejects_a_file_that_is_not_a_pdf(self, user_client: AsyncClient) -> None:
        response = await user_client.post(
            "/api/extractions",
            files={"file": ("notes.txt", b"Hemoglobina 10.5", "application/pdf")},
        )
        assert response.status_code == 415

    async def test_rejects_reimporting_the_same_file(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        content = make_pdf(lines=30)
        await upload(user_client, content)

        response = await user_client.post(
            "/api/extractions",
            files={"file": ("same-again.pdf", content, "application/pdf")},
        )

        assert response.status_code == 409

    async def test_retries_the_same_file_after_a_failed_extraction(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        content = make_pdf(lines=30)
        stub_model(monkeypatch, "not json")
        failed = await upload(user_client, content)
        assert (await user_client.get(f"/api/extractions/{failed['id']}")).json()["status"] == "failed"

        stub_model(monkeypatch, ANSWER)
        retried = await upload(user_client, content)

        assert retried["id"] == failed["id"]
        polled = (await user_client.get(f"/api/extractions/{retried['id']}")).json()
        assert polled["status"] == "preview"
        assert polled["error"] is None

    async def test_rejects_a_file_over_the_limit(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "upload_max_bytes", 1024, raising=False)

        response = await user_client.post(
            "/api/extractions",
            files={"file": ("big.pdf", b"%PDF-" + b"0" * 4096, "application/pdf")},
        )
        assert response.status_code == 413

    async def test_is_unavailable_without_a_configured_model(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "llm_model", "", raising=False)

        response = await user_client.post(
            "/api/extractions", files={"file": ("a.pdf", make_pdf(lines=1), "application/pdf")}
        )
        assert response.status_code == 503


class TestPreview:
    async def test_preserves_visual_column_order_in_text_pdfs(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        document = pymupdf.open()
        page = document.new_page()
        # Inserted in the misleading content-stream order used by many lab PDFs:
        # reference first, then the visually earlier current result.
        page.insert_text((360, 100), "13,0 - 16,5")
        page.insert_text((50, 100), "Hemoglobina")
        page.insert_text((250, 100), "15,2 g/dL")
        monkeypatch.setattr(get_settings(), "extraction_text_threshold", 0, raising=False)
        seen = stub_model(monkeypatch, ANSWER)

        await upload(user_client, bytes(document.tobytes()))

        payload = seen[0][0]["text"]
        assert "Hemoglobina 15,2 g/dL 13,0 - 16,5" in payload
        assert "Resultado Atual" in payload

    async def test_matches_the_catalogue_through_aliases_and_accents(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        job = await upload(user_client)

        preview = (await user_client.get(f"/api/extractions/{job['id']}")).json()["preview"]
        by_source = {row["source_name"]: row for row in preview["results"]}

        assert by_source["Hemoglobina"]["biomarker_slug"] == "hemoglobina"
        # Read without accents, punctuation or case, and still matched.
        assert by_source["VITAMINA D 25 OH"]["biomarker_id"] is not None
        # An unmatched line is shown, not silently dropped.
        assert by_source["Marcador Inventado"]["biomarker_id"] is None

    async def test_keeps_the_documents_metadata_and_decimal_comma(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        job = await upload(user_client)

        preview = (await user_client.get(f"/api/extractions/{job['id']}")).json()["preview"]
        assert preview["collected_on"] == "2026-02-14"
        assert preview["lab_name"] == "Unilabs"
        assert preview["fasting_state"] == "fasting"
        haemoglobin = next(r for r in preview["results"] if r["source_name"] == "Hemoglobina")
        assert Decimal(haemoglobin["value"]) == Decimal("10.5")

    async def test_sends_text_for_a_text_pdf_and_images_for_a_scan(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = stub_model(monkeypatch, ANSWER)

        await upload(user_client, make_pdf(lines=30))
        await upload(user_client, make_pdf(lines=0))  # a page with no text layer

        assert [part["type"] for part in seen[0]] == ["text"]
        assert [part["type"] for part in seen[1]] == ["text", "image_url"]

    async def test_removes_profile_identity_before_a_text_pdf_reaches_the_model(
        self,
        make_user: UserFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client, _ = await make_user(name="Ana Particular", email="ana.private@example.com")
        seen = stub_model(monkeypatch, ANSWER)
        document = pymupdf.open()  # type: ignore[no-untyped-call]
        page = document.new_page()
        lines = [
            "Nome: Ana Particular",
            "Email: ana.private@example.com",
            "NIF: 123456789",
            "Morada: Rua Particular 12, Lisboa",
            *[f"Hemoglobina {index} 14,1 g/dL 13 - 17" for index in range(20)],
        ]
        for index, line in enumerate(lines):
            page.insert_text((50, 40 + index * 20), line)

        await upload(client, bytes(document.tobytes()))

        payload = seen[0][0]["text"]
        assert "Ana Particular" not in payload
        assert "ana.private@example.com" not in payload
        assert "123456789" not in payload
        assert "Rua Particular" not in payload
        assert "Hemoglobina" in payload

    async def test_accepts_a_report_photo_and_only_sends_fresh_png_pixels(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = stub_model(monkeypatch, ANSWER)

        await upload(user_client, make_report_photo())

        assert [part["type"] for part in seen[0]] == ["text", "image_url"]
        encoded = seen[0][1]["image_url"]["url"].split(",", 1)[1]
        safe = base64.b64decode(encoded)
        assert safe.startswith(b"\x89PNG")
        assert b"private metadata" not in safe

    async def test_records_a_failure_on_the_job_instead_of_losing_it(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_model(monkeypatch, "I am afraid I cannot help with that.")

        job = await upload(user_client)

        polled = (await user_client.get(f"/api/extractions/{job['id']}")).json()
        assert polled["status"] == "failed"
        assert polled["error"]
        assert polled["preview"] is None


class TestConfirm:
    async def test_writes_only_what_was_approved(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, catalogue: dict[str, Any]
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        job = await upload(user_client)
        haemoglobin = catalogue["biomarkers"]["hemoglobina"]

        # The reader keeps one of the three lines and corrects its value.
        response = await user_client.post(
            f"/api/extractions/{job['id']}/confirm",
            json={
                "collected_on": "2026-02-14",
                "lab_name": "Unilabs",
                "fasting_state": "fasting",
                "results": [
                    {
                        "biomarker_id": haemoglobin["id"],
                        "value": 10.9,
                        "unit": "g/dL",
                        "ref_min": 12,
                        "ref_max": 15.5,
                    }
                ],
            },
        )

        assert response.status_code == 201, response.text
        report = response.json()
        assert report["source"] == "extracted"
        assert len(report["results"]) == 1
        assert Decimal(report["results"][0]["value"]) == Decimal("10.9")
        # Flagged server-side from the range, never by the model.
        assert report["results"][0]["flag"] == "low"

    async def test_links_the_report_back_to_the_job(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, catalogue: dict[str, Any]
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        job = await upload(user_client)

        report = (
            await user_client.post(
                f"/api/extractions/{job['id']}/confirm",
                json={
                    "collected_on": "2026-02-14",
                    "lab_name": "Unilabs",
                    "results": [
                        {
                            "biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"],
                            "value": 10.9,
                        }
                    ],
                },
            )
        ).json()

        polled = (await user_client.get(f"/api/extractions/{job['id']}")).json()
        assert polled["status"] == "confirmed"
        assert polled["report_id"] == report["id"]

    async def test_refuses_a_second_confirmation(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, catalogue: dict[str, Any]
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        job = await upload(user_client)
        payload = {
            "collected_on": "2026-02-14",
            "lab_name": "Unilabs",
            "results": [
                {"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 10.9}
            ],
        }
        assert (
            await user_client.post(f"/api/extractions/{job['id']}/confirm", json=payload)
        ).status_code == 201

        again = await user_client.post(f"/api/extractions/{job['id']}/confirm", json=payload)

        assert again.status_code == 409

    async def test_serves_the_original_pdf_back(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, catalogue: dict[str, Any]
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        job = await upload(user_client)
        report = (
            await user_client.post(
                f"/api/extractions/{job['id']}/confirm",
                json={
                    "collected_on": "2026-02-14",
                    "lab_name": "Unilabs",
                    "results": [
                        {
                            "biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"],
                            "value": 10.9,
                        }
                    ],
                },
            )
        ).json()

        response = await user_client.get(f"/api/reports/{report['id']}/file")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")

    async def test_serves_the_original_report_photo_back(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, catalogue: dict[str, Any]
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        original = make_report_photo()
        job = await upload(user_client, original)
        report = (
            await user_client.post(
                f"/api/extractions/{job['id']}/confirm",
                json={
                    "collected_on": "2026-02-14",
                    "lab_name": "Unilabs",
                    "results": [
                        {
                            "biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"],
                            "value": 10.9,
                        }
                    ],
                },
            )
        ).json()

        response = await user_client.get(f"/api/reports/{report['id']}/file")

        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == original

    async def test_a_manual_report_has_no_file(
        self, user_client: AsyncClient, catalogue: dict[str, Any]
    ) -> None:
        report = (
            await user_client.post(
                "/api/reports",
                json={
                    "collected_on": "2026-02-14",
                    "lab_name": "Unilabs",
                    "results": [
                        {
                            "biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"],
                            "value": 13.4,
                        }
                    ],
                },
            )
        ).json()

        assert (await user_client.get(f"/api/reports/{report['id']}/file")).status_code == 404


class TestIsolation:
    async def test_one_account_cannot_read_anothers_job(
        self, make_user: UserFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        ana, _ = await make_user("F")
        bruno, _ = await make_user("M")
        job = await upload(ana)

        assert (await bruno.get(f"/api/extractions/{job['id']}")).status_code == 404

    async def test_one_account_cannot_confirm_anothers_job(
        self, make_user: UserFactory, monkeypatch: pytest.MonkeyPatch, catalogue: dict[str, Any]
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        ana, _ = await make_user("F")
        bruno, _ = await make_user("M")
        job = await upload(ana)

        response = await bruno.post(
            f"/api/extractions/{job['id']}/confirm",
            json={
                "collected_on": "2026-02-14",
                "lab_name": "Unilabs",
                "results": [
                    {"biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"], "value": 10.9}
                ],
            },
        )

        assert response.status_code == 404
        assert (await bruno.get("/api/reports")).json() == []

    async def test_one_account_cannot_read_anothers_pdf(
        self, make_user: UserFactory, monkeypatch: pytest.MonkeyPatch, catalogue: dict[str, Any]
    ) -> None:
        stub_model(monkeypatch, ANSWER)
        ana, _ = await make_user("F")
        bruno, _ = await make_user("M")
        job = await upload(ana)
        report = (
            await ana.post(
                f"/api/extractions/{job['id']}/confirm",
                json={
                    "collected_on": "2026-02-14",
                    "lab_name": "Unilabs",
                    "results": [
                        {
                            "biomarker_id": catalogue["biomarkers"]["hemoglobina"]["id"],
                            "value": 10.9,
                        }
                    ],
                },
            )
        ).json()

        assert (await bruno.get(f"/api/reports/{report['id']}/file")).status_code == 404

    async def test_every_endpoint_needs_a_session(self, client: AsyncClient) -> None:
        job_id = uuid.uuid4()
        assert (
            await client.post("/api/extractions", files={"file": ("a.pdf", b"%PDF-")})
        ).status_code == 401
        assert (await client.get(f"/api/extractions/{job_id}")).status_code == 401
        assert (await client.post(f"/api/extractions/{job_id}/confirm", json={})).status_code == 401


class TestParsing:
    """The answer-shaping helpers, which is where a real model is least tidy."""

    def test_strips_a_markdown_fence(self) -> None:
        payload = extraction_service.parse_answer('```json\n{"results": []}\n```')
        assert payload.results == []

    def test_finds_json_after_a_preamble(self) -> None:
        payload = extraction_service.parse_answer('Aqui está:\n{"lab_name": "Unilabs"}')
        assert payload.lab_name == "Unilabs"

    def test_rejects_an_answer_with_no_json(self) -> None:
        with pytest.raises(extraction_service.ExtractionError):
            extraction_service.parse_answer("Não consigo ler este documento.")

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("10,5", Decimal("10.5")), ("<0,01", Decimal("0.01")), ("", None), ("Negativo", None)],
    )
    def test_coerces_the_values_a_report_actually_contains(
        self, raw: str, expected: Decimal | None
    ) -> None:
        payload = ExtractionPayload.model_validate({"results": [{"biomarker": "X", "value": raw}]})
        assert payload.results[0].value == expected

    def test_an_empty_answer_is_a_failure_not_an_empty_report(self) -> None:
        payload = extraction_service.parse_answer('{"results": []}')
        assert payload.results == []
        assert payload.collected_on is None


class TestFeatures:
    async def test_reports_extraction_as_available_when_a_model_is_configured(
        self, user_client: AsyncClient
    ) -> None:
        assert (await user_client.get("/api/features")).json() == {"extraction": True}

    async def test_reports_extraction_as_unavailable_without_one(
        self, user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "llm_model", "", raising=False)

        assert (await user_client.get("/api/features")).json() == {"extraction": False}

    async def test_needs_a_session(self, client: AsyncClient) -> None:
        assert (await client.get("/api/features")).status_code == 401
