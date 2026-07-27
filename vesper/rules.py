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


def _warning_tokens_with_case(value: str) -> str:
    """Normalize layout and punctuation while preserving warning capitalization."""
    return " ".join(re.findall(r"[A-Za-z0-9]+", value or ""))


def _tokens_appear_in_order(expected: str, observed: str) -> bool:
    """Allow unrelated OCR column text between required warning words."""
    cursor = 0
    compact_observed = observed.replace(" ", "")
    for token in expected.split():
        position = compact_observed.find(token, cursor)
        if position < 0:
            return False
        cursor = position + len(token)
    return True


def _find_number(pattern: re.Pattern[str], text: str) -> float | None:
    match = pattern.search(text)
    return float(match.group("value").replace(",", ".")) if match else None


def extract_regulated_values(text: str) -> dict[str, float | bool | None]:
    abv = _find_number(ALCOHOL_RE, text)
    proof = _find_number(PROOF_RE, text)
    ml = _find_number(NET_ML_RE, text)
    liters = _find_number(NET_L_RE, text)
    if abv is None and re.search(
        r"(?:alcohol|alc\.?)\s*(?:/|\s+by\s+)?\s*(?:volume|vol\.?)", text, re.I
    ):
        percent = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s*%", text)
        if percent:
            abv = float(percent.group(1).replace(",", "."))
    if proof is None:
        proof_anchor = re.search(r"\bproof\b", text, re.I)
        if proof_anchor:
            preceding = re.findall(r"(?<![%\d])(\d{1,3}(?:[.,]\d+)?)(?!\s*%)", text[:proof_anchor.start()])
            candidates = [float(value.replace(",", ".")) for value in preceding]
            proof = next((value for value in reversed(candidates) if value <= 200), None)
    if ml is None:
        ml_anchor = re.search(r"\bm\s*l\b", text, re.I)
        if ml_anchor:
            preceding = re.findall(r"(?<!\d)(\d{1,4}(?:[.,]\d+)?)(?!\s*%)", text[:ml_anchor.start()])
            candidates = [float(value.replace(",", ".")) for value in preceding]
            ml = next((value for value in reversed(candidates) if value <= 4000), None)
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
    warning_capitalization_exact = GOVERNMENT_WARNING in text
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
        "government_warning_capitalization_exact": warning_capitalization_exact,
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


def compare_proof(expected: float | None, label_abv: float | None, found: float | None) -> CheckResult:
    if expected is None and found is None:
        return CheckResult(
            "Proof (optional)", "Not expected", "Not shown",
            Status.MATCH, "Proof is optional and was not expected or shown."
        )
    if expected is None:
        return CheckResult(
            "Proof (optional)", "Not expected", f"{found:g} proof",
            Status.POSSIBLE_MATCH,
            "Proof is optional, but the label shows a value that was not entered."
        )
    if found is None:
        return CheckResult(
            "Proof (optional)", f"{expected:g} proof", "Not shown",
            Status.UNABLE, "A proof value was expected, but no proof statement was detected."
        )
    status = Status.MATCH if abs(expected - found) <= 0.1 else Status.MISMATCH
    consistency_note = ""
    if label_abv is not None and abs(found - (label_abv * 2)) > 0.1:
        status = Status.MISMATCH
        consistency_note = " It also does not equal twice the label's stated ABV."
    return CheckResult(
        "Proof (optional)", f"{expected:g} proof", f"{found:g} proof", status,
        "The proof matches the entered application value and stated ABV."
        if status == Status.MATCH else
        "The label proof differs from the entered application value." + consistency_note
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


def compare_warning(expected: str, text: str) -> CheckResult:
    expected = expected.strip()
    if not expected:
        return CheckResult(
            "Government warning", "No expectation entered", "Not evaluated",
            Status.UNABLE, "Enter the expected government warning wording before verification."
        )
    normalized_expected = compact_warning(expected)
    normalized_text = compact_warning(text)
    case_sensitive_expected = _warning_tokens_with_case(expected)
    case_sensitive_text = _warning_tokens_with_case(text)
    expected_words = normalized_expected.split()
    observed_words = set(normalized_text.split())
    score = (
        sum(1 for word in expected_words if word in observed_words) / len(expected_words)
        if expected_words else 0.0
    )
    if _tokens_appear_in_order(case_sensitive_expected, case_sensitive_text):
        return CheckResult(
            "Government warning", "Entered wording and capitalization",
            "Complete wording detected",
            Status.MATCH,
            "The entered warning wording and capitalization were found exactly.",
            score,
        )
    if _tokens_appear_in_order(normalized_expected, normalized_text):
        return CheckResult(
            "Government warning",
            "Entered wording and capitalization",
            "Wording detected with capitalization or formatting variance",
            Status.POSSIBLE_MATCH,
            "The wording is present, but capitalization or formatting requires visual review.",
            score,
        )
    if score >= 0.90:
        return CheckResult(
            "Government warning", "Entered wording and capitalization", "Possible OCR variance",
            Status.POSSIBLE_MATCH,
            "Most warning words were found, but exact wording needs visual review.", score
        )
    return CheckResult(
        "Government warning", "Entered wording and capitalization",
        "Missing or materially incomplete", Status.MISMATCH,
        "The entered warning wording was not detected.", score
    )


def validate_expected(expected: ExpectedLabel) -> list[str]:
    errors: list[str] = []
    if not expected.brand_name.strip():
        errors.append("Brand name is required.")
    if not expected.class_type.strip():
        errors.append("Class/type is required.")
    if not 0.5 <= expected.abv <= 100:
        errors.append("ABV must be between 0.5 and 100 for this prototype.")
    if expected.proof is not None and not 1 <= expected.proof <= 200:
        errors.append("Proof must be between 1 and 200.")
    if expected.proof is not None and abs(expected.proof - (expected.abv * 2)) > 0.1:
        errors.append("Expected proof must equal twice the expected ABV.")
    if expected.net_contents_ml not in AUTHORIZED_FILL_ML:
        errors.append("Net contents must use a current authorized standard of fill.")
    if not expected.government_warning.strip():
        errors.append("Expected government warning wording is required.")
    return errors
