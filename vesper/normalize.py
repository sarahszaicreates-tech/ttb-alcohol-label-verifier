import re
import unicodedata
from difflib import SequenceMatcher


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def similarity(left: str, right: str) -> float:
    a, b = normalize_text(left), normalize_text(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def compact_warning(value: str) -> str:
    """Normalize OCR variance while preserving every required warning word."""
    return normalize_text(value)

