import re

from .models import CheckResult, ExpectedLabel, Status
from .normalize import compact_warning, similarity


GOVERNMENT_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should "
    "not drink alcoholic beverages during pregnancy because of the risk of "
    "birth defects. (2) Consumption of alcoholic beverages impairs your "
    "ability to drive a car or operate machinery, and may cause health problems."
)

# 27 CFR 5.203(a), reflecting the sizes listed by TTB on May 21, 2026.
AUTHORIZED_FILL_ML = frozenset(
    {3750, 3000, 2000, 1800, 1750, 1500, 1000, 945, 900, 750, 720, 710,
     700, 570, 500, 475, 375, 355, 350, 331, 250, 200, 187, 100, 50}
)

ALCOHOL_RE = re.compile(
    r"(?P<value>\d{1,3}(?:[.,]\d+)?)\s*%\s*"
    r"(?:(?:alcohol|alc\.?)\s*(?:by\s*)?(?:volume|vol\.?))",
    re.IGNORECASE,
)
PROOF_RE = re.compile(r"(?P<value>\d{1,3}(?:[.,]\d+)?)\s*(?:degrees?\s+)?proof", re.I)
NET_ML_RE = re.compile(r"(?P<value>\d{1,4}(?:[.,]\d+)?)\s*m\s*l\b", re.I)
NET_L_RE = re.compile(r"(?P<value>\d(?:[.,]\d{1,3})?)\s*l(?:iter|itre)?s?\b", re.I)


def _find_number(pattern: re.Pattern[str], text: str) -> float | None:
    match = pattern.search(text)
    return float(match.group("value").replace(",", ".")) if match else None


def extract_regulated_values(text: str) -> dict[str, float | bool | None]:
    abv = _find_number(ALCOHOL_RE, text)
    proof = _find_number(PROOF_RE, text)
    ml = _find_number(NET_ML_RE, text)
    liters = _find_number(NET_L_RE, text)
    if ml is None and liters is not None:
        ml = liters * 1000
    warning_score = similarity(
        compact_warning(GOVERNMENT_WARNING), compact_warning(text)
    )
    # The full label contains extra text, so search for the normalized warning as
    # a contiguous phrase and also expose a partial score for OCR-damaged labels.
    required = compact_warning(GOVERNMENT_WARNING)
    observed = compact_warning(text)
    warning_exact = required in observed
    if warning_exact:
        warning_score = 1.0
    if not warning_exact:
        words = required.split()
        present = sum(1 for word in words if word in observed.split())
        warning_score = present / len(words)
    return {
        "abv": abv,
        "proof": proof,
        "net_contents_ml": ml,
        "government_warning_exact": warning_exact,
        "government_warning_score": warning_score,
    }


def compare_name(field: str, expected: str, text: str) -> CheckResult:
    normalized_expected = compact_warning(expected)
    normalized_text = compact_warning(text)
    if not normalized_expected:
        return CheckResult(field, expected, "", Status.UNABLE, "No expected value supplied.")
    if normalized_expected in normalized_text:
        return CheckResult(field, expected, expected, Status.MATCH, "Expected wording was found.")
    if normalized_expected.replace(" ", "") in normalized_text.replace(" ", ""):
        return CheckResult(
            field, expected, expected, Status.MATCH,
            "Expected wording was found after correcting OCR spacing."
        )
    # Compare expected text against same-sized OCR word windows.
    tokens, n = normalized_text.split(), len(normalized_expected.split())
    scores = [
        similarity(normalized_expected, " ".join(tokens[i : i + n]))
        for i in range(max(0, len(tokens) - n + 1))
    ]
    score = max(scores, default=0.0)
    if score >= 0.80:
        return CheckResult(
            field, expected, "OCR text contains a close variant", Status.POSSIBLE_MATCH,
            "Close textual match; confirm visually.", score
        )
    return CheckResult(
        field, expected, "Not found", Status.MISMATCH,
        "Expected wording was not found in OCR text.", score
    )


def compare_abv(expected: float, found: float | None) -> CheckResult:
    if found is None:
        return CheckResult(
            "Alcohol content", f"{expected:g}% alcohol by volume", "Not found",
            Status.UNABLE, "No TTB-compliant percent alcohol-by-volume statement was detected."
        )
    delta = abs(expected - found)
    status = Status.MATCH if delta < 0.01 else Status.MISMATCH
    return CheckResult(
        "Alcohol content", f"{expected:g}% alcohol by volume",
        f"{found:g}% alcohol by volume", status,
        "The stated percentage matches." if status == Status.MATCH else
        "The label percentage differs from the application value."
    )


def compare_proof(abv: float | None, proof: float | None) -> CheckResult:
    if proof is None:
        return CheckResult(
            "Proof (optional)", "If shown: 2 × stated ABV", "Not shown",
            Status.MATCH, "Proof is optional; no proof statement requires comparison."
        )
    if abv is None:
        return CheckResult(
            "Proof (optional)", "2 × stated ABV", f"{proof:g} proof",
            Status.UNABLE, "Proof was found, but the mandatory ABV statement was not."
        )
    expected_proof = abv * 2
    status = Status.MATCH if abs(expected_proof - proof) <= 0.1 else Status.MISMATCH
    return CheckResult(
        "Proof (optional)", f"{expected_proof:g} proof", f"{proof:g} proof", status,
        "Proof is consistent with stated ABV." if status == Status.MATCH else
        "Proof must equal twice the stated alcohol-by-volume percentage."
    )


def compare_net_contents(expected_ml: int, found: float | None) -> CheckResult:
    if found is None:
        return CheckResult(
            "Net contents", f"{expected_ml} mL", "Not found", Status.UNABLE,
            "No metric net-contents statement was detected."
        )
    status = Status.MATCH if abs(expected_ml - found) < 0.5 else Status.MISMATCH
    fill_note = (
        "Authorized standard of fill."
        if round(found) in AUTHORIZED_FILL_ML
        else "Detected size is not in the current authorized standards-of-fill list."
    )
    if round(found) not in AUTHORIZED_FILL_ML:
        status = Status.MISMATCH
    return CheckResult(
        "Net contents", f"{expected_ml} mL", f"{found:g} mL", status,
        ("Metric volume matches. " if abs(expected_ml - found) < 0.5 else
         "Metric volume differs from the application value. ") + fill_note
    )


def compare_warning(extracted: dict[str, float | bool | None]) -> CheckResult:
    score = float(extracted["government_warning_score"] or 0)
    if extracted["government_warning_exact"]:
        return CheckResult(
            "Government warning", "Exact statutory wording", "Complete wording detected",
            Status.MATCH, "All required warning words were found in order.", score
        )
    if score >= 0.90:
        return CheckResult(
            "Government warning", "Exact statutory wording", "Possible OCR variance",
            Status.POSSIBLE_MATCH,
            "Most warning words were found, but exact wording needs visual review.", score
        )
    return CheckResult(
        "Government warning", "Exact statutory wording", "Missing or materially incomplete",
        Status.MISMATCH, "The complete statutory warning was not detected.", score
    )


def validate_expected(expected: ExpectedLabel) -> list[str]:
    errors: list[str] = []
    if not expected.brand_name.strip():
        errors.append("Brand name is required.")
    if not expected.class_type.strip():
        errors.append("Class/type is required.")
    if not 0.5 <= expected.abv <= 100:
        errors.append("ABV must be between 0.5 and 100 for this prototype.")
    if expected.net_contents_ml not in AUTHORIZED_FILL_ML:
        errors.append("Net contents must use a current authorized standard of fill.")
    return errors
