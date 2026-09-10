"""Photo import for body composition, with confirmation as the write gate."""

import io
import json
from typing import Any

import pytest
from httpx import AsyncClient
from PIL import Image

from app.api.routes import body_extractions as routes
from app.core.config import get_settings
from app.services import anonymization as anonymization_service
from tests.conftest import UserFactory

ANSWER = {
    "measured_at": "2026-09-10T07:35",
    "device": "Withings Body+",
    "results": [
        {"source_name": "Weight", "metric_slug": "weight", "value": 78.4, "unit": "kg"},
        {
            "source_name": "Body fat",
            "metric_slug": "body-fat-pct",
            "value": 19.2,
            "unit": "%",
        },
        {"source_name": "Body score", "metric_slug": None, "value": 84, "unit": None},
    ],
}


def image_bytes() -> bytes:
    image = Image.new("RGB", (800, 600), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def configure(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_model", "test/fake-model", raising=False)
    monkeypatch.setattr(settings, "storage_path", str(tmp_path), raising=False)
    monkeypatch.setattr(anonymization_service, "ocr_lines", lambda image: [])
    monkeypatch.setattr(anonymization_service, "decode_barcodes", lambda image: [])
    monkeypatch.setattr(anonymization_service, "_blur_faces", lambda image: image)


def stub_model(monkeypatch: pytest.MonkeyPatch, answer: object = ANSWER) -> None:
    async def fake(content: list[dict[str, Any]], settings: Any) -> tuple[str, str]:
        assert "composição corporal" in content[0]["text"]
        return json.dumps(answer), "test/fake-model"

    monkeypatch.setattr(routes, "ask_model", fake)


async def upload(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/body/extractions",
        files={"file": ("balanca.png", image_bytes(), "image/png")},
    )
    assert response.status_code == 202, response.text
    return response.json()


async def test_previews_known_values_and_keeps_proprietary_scores_unmatched(
    user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_model(monkeypatch)
    job = await upload(user_client)

    preview = (await user_client.get(f"/api/body/extractions/{job['id']}")).json()["preview"]
    assert preview["device"] == "Withings Body+"
    assert preview["results"][0]["metric_slug"] == "weight"
    assert preview["results"][1]["metric_slug"] == "body-fat-pct"
    assert preview["results"][2]["metric_id"] is None
    assert "unmatched" in preview["results"][2]["warnings"]
    assert (await user_client.get("/api/body/scans")).json() == []


async def test_confirmation_writes_only_selected_values_as_an_import(
    user_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_model(monkeypatch)
    job = await upload(user_client)
    preview = (await user_client.get(f"/api/body/extractions/{job['id']}")).json()["preview"]

    response = await user_client.post(
        f"/api/body/extractions/{job['id']}/confirm",
        json={
            "measured_at": "2026-09-10T07:35:00Z",
            "device": "Withings Body+",
            "values": [
                {
                    "metric_id": preview["results"][0]["metric_id"],
                    "value": 78.3,
                }
            ],
        },
    )

    assert response.status_code == 201, response.text
    scan = response.json()
    assert scan["source"] == "import"
    assert scan["device"] == "Withings Body+"
    assert len(scan["values"]) == 1
    assert scan["values"][0]["value"] == "78.3000"


async def test_rejects_non_images(user_client: AsyncClient) -> None:
    response = await user_client.post(
        "/api/body/extractions",
        files={"file": ("dados.pdf", b"%PDF-not-an-image", "application/pdf")},
    )
    assert response.status_code == 415


async def test_jobs_are_private(
    make_user: UserFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, _ = await make_user()
    stranger, _ = await make_user()
    stub_model(monkeypatch)
    job = await upload(owner)

    assert (await stranger.get(f"/api/body/extractions/{job['id']}")).status_code == 404
