"""Local anonymisation for documents before they cross the LLM boundary.

The original upload is never changed. Text PDFs are reduced to sanitised text;
scans and photographed reports are decoded, re-encoded without metadata and
have OCR-located PII, machine-readable codes and faces removed locally.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFilter, ImageOps


class AnonymizationError(RuntimeError):
    """The document cannot safely be prepared for an external model."""


@dataclass(frozen=True, slots=True)
class Identity:
    name: str | None = None
    email: str | None = None
    birth_date: date | None = None

    @property
    def exact_values(self) -> tuple[str, ...]:
        values = [self.name, self.email]
        if self.birth_date:
            values.extend(
                [
                    self.birth_date.isoformat(),
                    self.birth_date.strftime("%d/%m/%Y"),
                    self.birth_date.strftime("%d-%m-%Y"),
                ]
            )
        return tuple(value for value in values if value)


_LABELS = re.compile(
    r"\b(nome|name|utente|patient|nif|n[úu]mero\s+(?:de\s+)?(?:utente|identifica[cç][aã]o)|"
    r"data\s+de\s+nascimento|date\s+of\s+birth|morada|endere[cç]o|address|"
    r"m[eé]dico\s+requisitante|requesting\s+doctor|email|e-mail|telefone|phone)\b",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_NATIONAL_ID = re.compile(r"(?<!\d)\d{9}(?!\d)")


def _fold(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value).casefold()
        if not unicodedata.combining(character)
    )


def is_sensitive(text: str, identity: Identity) -> bool:
    folded = _fold(text)
    return bool(
        _LABELS.search(folded)
        or _EMAIL.search(text)
        or _NATIONAL_ID.search(text)
        or any(_fold(value) in folded for value in identity.exact_values if len(value.strip()) >= 3)
    )


def redact_text(text: str, identity: Identity) -> str:
    """Drop complete sensitive lines so neither their labels nor values escape."""
    return "\n".join(
        "[DADO ANONIMIZADO]" if is_sensitive(line, identity) else line for line in text.splitlines()
    )


def ocr_lines(image: Image.Image) -> list[tuple[str, tuple[int, int, int, int]]]:
    """Return OCR text and the union of its word boxes, grouped by visual line."""
    try:
        data: dict[str, list[Any]] = pytesseract.image_to_data(
            image, lang="por+eng", output_type=pytesseract.Output.DICT
        )
    except Exception as error:
        raise AnonymizationError("Local OCR failed; the image was not sent to the model") from error

    grouped: dict[tuple[int, int, int], list[int]] = {}
    count = len(data.get("text", []))
    for index in range(count):
        if not str(data["text"][index]).strip():
            continue
        key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        grouped.setdefault(key, []).append(index)

    lines: list[tuple[str, tuple[int, int, int, int]]] = []
    for indexes in grouped.values():
        text = " ".join(str(data["text"][index]).strip() for index in indexes)
        left = min(int(data["left"][index]) for index in indexes)
        top = min(int(data["top"][index]) for index in indexes)
        right = max(int(data["left"][index]) + int(data["width"][index]) for index in indexes)
        bottom = max(int(data["top"][index]) + int(data["height"][index]) for index in indexes)
        lines.append((text, (left, top, right, bottom)))
    return lines


def decode_barcodes(image: Image.Image) -> list[Any]:
    """Decode locally when libzbar is present (installed in the API image)."""
    try:
        from pyzbar.pyzbar import decode
    except ImportError as error:
        raise AnonymizationError(
            "Local barcode detection is unavailable; the image was not sent to the model"
        ) from error
    return list(decode(image))


def _blur_faces(image: Image.Image) -> Image.Image:
    pixels = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(  # type: ignore[attr-defined]
        cv2.data.haarcascades  # type: ignore[attr-defined]
        + "haarcascade_frontalface_default.xml"
    )
    for x, y, width, height in cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5):
        box = (int(x), int(y), int(x + width), int(y + height))
        region = image.crop(box).filter(ImageFilter.GaussianBlur(radius=max(width, height) / 7))
        image.paste(region, box)
    return image


def anonymize_image(image: Image.Image, identity: Identity) -> bytes:
    """Return metadata-free PNG pixels with locally detectable PII removed."""
    clean = (ImageOps.exif_transpose(image) or image).convert("RGB")
    clean = _blur_faces(clean)
    draw = ImageDraw.Draw(clean)

    for text, (left, top, right, bottom) in ocr_lines(clean):
        if is_sensitive(text, identity):
            padding = max(4, (bottom - top) // 4)
            box = (
                max(0, left - padding),
                max(0, top - padding),
                min(clean.width, right + padding),
                min(clean.height, bottom + padding),
            )
            draw.rectangle(box, fill="black")

    for barcode in decode_barcodes(clean):
        rect = barcode.rect
        padding = 8
        draw.rectangle(
            (
                max(0, rect.left - padding),
                max(0, rect.top - padding),
                min(clean.width, rect.left + rect.width + padding),
                min(clean.height, rect.top + rect.height + padding),
            ),
            fill="black",
        )

    output = io.BytesIO()
    clean.save(output, format="PNG", optimize=True)
    return output.getvalue()
