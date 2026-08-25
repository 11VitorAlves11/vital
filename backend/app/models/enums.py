from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def pg_enum[E: StrEnum](enum: type[E], name: str) -> SAEnum:
    """Postgres ENUM storing the member *values* (not the Python member names)."""
    return SAEnum(enum, name=name, values_callable=lambda e: [member.value for member in e])


class Sex(StrEnum):
    M = "M"
    F = "F"


class BiomarkerCategory(StrEnum):
    HEMATOLOGIA = "hematologia"
    BIOQUIMICA = "bioquimica"
    VITAMINAS = "vitaminas"
    FERRO = "ferro"
    HORMONAS = "hormonas"
    LIPIDOS = "lipidos"
    RENAL = "renal"
    HEPATICO = "hepatico"
    OUTRO = "outro"


class ReportSource(StrEnum):
    MANUAL = "manual"
    EXTRACTED = "extracted"


class ResultFlag(StrEnum):
    """Lab result classification — no borderline state (docs/vital-spec.md §2)."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ExtractionStatus(StrEnum):
    """Where a PDF is in the pipeline. `preview` is the human gate: nothing
    reaches `results` until someone confirms what the model read."""

    PENDING = "pending"
    PROCESSING = "processing"
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class Pose(StrEnum):
    """How a progress photo was taken, so a comparison lines two of a kind up."""

    FRENTE = "frente"
    LADO = "lado"
    COSTAS = "costas"
    OUTRO = "outro"


class InterventionKind(StrEnum):
    SUPLEMENTO = "suplemento"
    MEDICACAO = "medicacao"
    DIETA = "dieta"
    TREINO = "treino"
    OUTRO = "outro"


class ScanSource(StrEnum):
    MANUAL = "manual"
    IMPORT = "import"


class BandFlag(StrEnum):
    """Body-composition band classification — multi-class, so it does have `warn`."""

    NORMAL = "normal"
    WARN = "warn"
    ALERT = "alert"
