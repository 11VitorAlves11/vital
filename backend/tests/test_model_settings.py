from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import User
from app.services.model_credentials import decrypt_api_key


@pytest.fixture(autouse=True)
def _credential_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path))


async def test_model_settings_store_key_encrypted_and_never_return_it(
    user_client: Any,
) -> None:
    response = await user_client.patch(
        "/api/users/me/model-settings",
        json={
            "model": "openai/gpt-4.1-mini",
            "base_url": "https://models.example.test/v1",
            "api_key": "secret-provider-key",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "model": "openai/gpt-4.1-mini",
        "base_url": "https://models.example.test/v1",
        "has_api_key": True,
        "has_account_api_key": True,
        "uses_instance_model": False,
        "uses_instance_base_url": False,
    }
    assert "secret-provider-key" not in response.text

    me = (await user_client.get("/api/users/me")).json()
    async with get_sessionmaker()() as db:
        user = await db.scalar(select(User).where(User.id == me["id"]))
        assert user is not None
        assert user.llm_api_key_encrypted != "secret-provider-key"
        assert decrypt_api_key(user.llm_api_key_encrypted or "", get_settings()) == (
            "secret-provider-key"
        )

    read_back = await user_client.get("/api/users/me/model-settings")
    assert read_back.status_code == 200
    assert read_back.json()["has_api_key"] is True
    assert "secret-provider-key" not in read_back.text


async def test_model_settings_are_scoped_to_each_account(make_user: Any) -> None:
    first, _ = await make_user()
    second, _ = await make_user()
    assert (
        await first.patch("/api/users/me/model-settings", json={"model": "ollama/private-vision"})
    ).status_code == 200

    first_settings = (await first.get("/api/users/me/model-settings")).json()
    second_settings = (await second.get("/api/users/me/model-settings")).json()
    assert first_settings["model"] == "ollama/private-vision"
    assert second_settings["model"] != "ollama/private-vision"
    assert (await first.get("/api/features")).json()["extraction"] is True


async def test_stored_key_can_be_removed_without_sending_a_replacement(user_client: Any) -> None:
    await user_client.patch("/api/users/me/model-settings", json={"api_key": "temporary-key"})
    response = await user_client.patch("/api/users/me/model-settings", json={"clear_api_key": True})
    assert response.status_code == 200
    assert response.json()["has_api_key"] is False
    assert response.json()["has_account_api_key"] is False
