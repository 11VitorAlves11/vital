"""Per-account model credentials, encrypted at rest on this instance."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.models.user import User


class CredentialError(RuntimeError):
    """A stored credential cannot safely be used."""


@dataclass(frozen=True, slots=True)
class ModelConfig:
    model: str
    base_url: str | None
    api_key: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.model.strip())


def _fernet(settings: Settings) -> Fernet:
    directory = Path(settings.storage_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".model-credentials.key"
    try:
        key = path.read_bytes()
    except FileNotFoundError:
        key = Fernet.generate_key()
        # Exclusive creation prevents two workers from replacing each other's key.
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            key = path.read_bytes()
        else:
            with os.fdopen(descriptor, "wb") as output:
                output.write(key)
    return Fernet(key.strip())


def encrypt_api_key(value: str, settings: Settings) -> str:
    return _fernet(settings).encrypt(value.encode()).decode()


def decrypt_api_key(value: str, settings: Settings) -> str:
    try:
        return _fernet(settings).decrypt(value.encode()).decode()
    except (InvalidToken, ValueError) as error:
        raise CredentialError("The stored model API key could not be decrypted") from error


def effective_model_config(user: User, settings: Settings) -> ModelConfig:
    key = (
        decrypt_api_key(user.llm_api_key_encrypted, settings)
        if user.llm_api_key_encrypted
        else settings.llm_api_key
    )
    return ModelConfig(
        model=user.llm_model if user.llm_model is not None else settings.llm_model,
        base_url=user.llm_base_url if user.llm_base_url is not None else settings.llm_base_url,
        api_key=key,
    )
