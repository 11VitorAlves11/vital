"""Reading a lab report PDF with an LLM.

The pipeline is deliberately dull: pull the text out with PyMuPDF, fall back to
page images when there is no text to pull, ask the model for JSON, validate it,
and match the names it returned against the catalogue. Nothing here writes a
result — the output is a preview a human still has to confirm.
"""

import base64
import json
import logging
import re
import unicodedata
from typing import Any

import pymupdf
from pydantic import ValidationError

from app.core.config import Settings
from app.models.biomarker import Biomarker
from app.schemas.extractions import (
    ExtractedResult,
    ExtractionPayload,
    ExtractionPreview,
    PreviewResult,
)

logger = logging.getLogger(__name__)

PROMPT = """Extrai todos os resultados de análises clínicas deste documento.
Responde APENAS com JSON válido, sem markdown:
{
  "collected_on": "YYYY-MM-DD",
  "lab_name": "...",
  "fasting": true,
  "results": [
    {"biomarker": "...", "value": 0.0, "unit": "...",
     "ref_min": 0.0, "ref_max": 0.0}
  ]
}
Usa null quando um campo não constar. Converte vírgulas decimais para ponto.
Não inventes valores: transcreve apenas o que está no documento."""


class ExtractionError(RuntimeError):
    """Anything that stops a job reaching preview, phrased for the reader."""


def page_contents(pdf_bytes: bytes, settings: Settings) -> list[dict[str, Any]]:
    """The message content for the model: text when the PDF has any, else images.

    The heuristic is the spec's — under `extraction_text_threshold` characters a
    page is a scan, and sending its empty text layer would extract nothing while
    still costing a call.
    """
    try:
        # PyMuPDF ships annotations but leaves these two entry points untyped.
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as error:  # pymupdf raises several unrelated types
        raise ExtractionError("The file could not be read as a PDF") from error

    with document:
        if document.page_count == 0:
            raise ExtractionError("The PDF has no pages")
        if document.page_count > settings.extraction_max_pages:
            raise ExtractionError(
                f"The PDF has {document.page_count} pages; "
                f"the limit is {settings.extraction_max_pages}"
            )

        pages = [
            document.load_page(index)  # type: ignore[no-untyped-call]
            for index in range(document.page_count)
        ]
        texts = [page.get_text() for page in pages]
        average = sum(len(text.strip()) for text in texts) / len(texts)

        if average >= settings.extraction_text_threshold:
            return [{"type": "text", "text": f"{PROMPT}\n\n---\n\n{'\n\n'.join(texts)}"}]

        # A scan. 144 dpi is twice the PDF default: enough for the small print a
        # reference range is set in, without doubling the payload again.
        content: list[dict[str, Any]] = [{"type": "text", "text": PROMPT}]
        for page in pages:
            png = page.get_pixmap(dpi=144).tobytes("png")
            encoded = base64.b64encode(png).decode()
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
            )
        return content


def parse_answer(text: str) -> ExtractionPayload:
    """Validate the model's JSON, fences and preamble included."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", candidate).strip()
    if not candidate.startswith("{"):
        # Some models introduce the JSON no matter how the prompt is worded.
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            raise ExtractionError("The model did not answer with JSON")
        candidate = candidate[start : end + 1]

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ExtractionError("The model's answer was not valid JSON") from error
    if not isinstance(data, dict):
        raise ExtractionError("The model's answer was not a JSON object")

    try:
        return ExtractionPayload.model_validate(data)
    except ValidationError as error:
        raise ExtractionError("The model's answer did not have the expected shape") from error


async def ask_model(content: list[dict[str, Any]], settings: Settings) -> tuple[str, str]:
    """Returns (answer, provider). Imported lazily: LiteLLM is a heavy import and
    an instance with no model configured should never pay for it."""
    from litellm import acompletion

    try:
        response = await acompletion(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            api_base=settings.llm_base_url or None,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            timeout=settings.llm_timeout,
        )
    except Exception as error:
        # The provider's message can carry the API key or the prompt; the reader
        # gets the type of failure and the log gets no health data either way.
        logger.warning("Extraction call failed: %s", type(error).__name__)
        raise ExtractionError("The model could not be reached") from error

    answer = response.choices[0].message.content or ""
    if not answer.strip():
        raise ExtractionError("The model returned an empty answer")
    return answer, settings.llm_model


def normalise(name: str) -> str:
    """Fold to something two spellings of the same marker can both reach.

    Portuguese lab reports vary in accents, case, punctuation and parentheses —
    "Vitamina D (25-OH)", "VITAMINA D 25 OH" and "vitamina d 25-oh" are one marker.
    """
    folded = unicodedata.normalize("NFKD", name.casefold())
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded).split())


def build_index(biomarkers: list[Biomarker]) -> dict[str, Biomarker]:
    """Name and every alias, normalised. First writer wins, so a catalogue name
    is never shadowed by another marker's alias."""
    index: dict[str, Biomarker] = {}
    for biomarker in biomarkers:
        for candidate in (biomarker.slug, biomarker.name, *biomarker.aliases):
            index.setdefault(normalise(candidate), biomarker)
    return index


def match(result: ExtractedResult, index: dict[str, Biomarker]) -> Biomarker | None:
    return index.get(normalise(result.biomarker))


def build_preview(payload: ExtractionPayload, biomarkers: list[Biomarker]) -> ExtractionPreview:
    index = build_index(biomarkers)
    return ExtractionPreview(
        collected_on=payload.collected_on,
        lab_name=payload.lab_name,
        fasting=payload.fasting,
        results=[
            PreviewResult(
                biomarker_id=matched.id if matched else None,
                biomarker_name=matched.name if matched else None,
                biomarker_slug=matched.slug if matched else None,
                source_name=result.biomarker,
                value=result.value,
                # The lab's own wording wins; the catalogue unit is the fallback.
                unit=result.unit or (matched.unit_default if matched else None),
                ref_min=result.ref_min,
                ref_max=result.ref_max,
            )
            for result in payload.results
            for matched in [match(result, index)]
        ],
    )
