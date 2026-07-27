from __future__ import annotations

import time
from functools import lru_cache
from io import BytesIO

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .models import OCRResult


class OCRUnavailableError(RuntimeError):
    pass


def preprocess_image(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("RGB")
    max_side = max(image.size)
    if max_side < 1600:
        scale = 1600 / max_side
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
    gray = ImageOps.grayscale(image)
    gray = ImageEnhance.Contrast(gray).enhance(1.7)
    return gray.filter(ImageFilter.SHARPEN)


@lru_cache(maxsize=1)
def _engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise OCRUnavailableError(
            f"RapidOCR could not initialize: {exc}. "
            "Install the runtime dependencies and restart the app."
        ) from exc
    return RapidOCR()


def run_local_ocr(data: bytes) -> OCRResult:
    start = time.perf_counter()
    image = preprocess_image(data)
    try:
        candidates = []
        for angle in (0, 90, 180, 270):
            candidate = image if angle == 0 else image.rotate(angle, expand=True, fillcolor="white")
            rows, _ = _engine()(np.asarray(candidate))
            rows = rows or []
            text = "\n".join(
                str(row[1]).strip()
                for row in rows
                if len(row) >= 3 and str(row[1]).strip()
            )
            confidences = [float(row[2]) for row in rows if len(row) >= 3]
            confidence = sum(confidences) / len(confidences) if confidences else 0.0
            # Correctly oriented prose yields more recognized characters while
            # confidence breaks ties between similarly complete readings.
            score = len("".join(text.split())) * max(confidence, 0.01)
            candidates.append((score, text, confidence))
    except OCRUnavailableError:
        raise
    except Exception as exc:
        raise OCRUnavailableError(f"Local OCR could not process this image: {exc}") from exc
    _, text, confidence_value = max(candidates, key=lambda item: item[0])
    lines = tuple(text.splitlines())
    confidence = confidence_value or None
    return OCRResult(
        text=text,
        confidence=confidence,
        provider="RapidOCR (local)",
        elapsed_seconds=time.perf_counter() - start,
        lines=lines,
    )
