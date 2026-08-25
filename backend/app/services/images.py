"""Turning an upload into a photo that carries nothing but pixels.

The image is decoded and re-encoded rather than filtered: a metadata stripper
has to know every block it might find, while a fresh encode starts from the
pixels and carries across only what is put there. GPS coordinates, camera serial
and capture time do not survive, because they are never written.
"""

import io

from PIL import Image, ImageOps
from PIL.Image import Resampling

from app.core.config import Settings


class ImageError(ValueError):
    """An upload that is not a usable photo, phrased for the reader."""


def process(content: bytes, settings: Settings) -> tuple[bytes, int, int]:
    """Returns (jpeg, width, height), oriented upright and free of metadata."""
    # A decompression bomb is a small file that decodes to gigabytes. Pillow's
    # own guard is a warning by default; here it is a refusal.
    Image.MAX_IMAGE_PIXELS = settings.photo_max_pixels

    try:
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            # Phones record rotation in EXIF rather than in the pixels. Applying
            # it before the strip is what keeps the photo upright afterwards.
            upright = ImageOps.exif_transpose(image) or image
            upright = upright.convert("RGB")
            upright.thumbnail(
                (settings.photo_max_dimension, settings.photo_max_dimension), Resampling.LANCZOS
            )
            buffer = io.BytesIO()
            # No exif= argument: a fresh encode with nothing carried over.
            upright.save(buffer, format="JPEG", quality=88, optimize=True)
            return buffer.getvalue(), upright.width, upright.height
    except Image.DecompressionBombError as error:
        raise ImageError("The image is too large to process") from error
    except (OSError, ValueError) as error:
        raise ImageError("The file could not be read as an image") from error
