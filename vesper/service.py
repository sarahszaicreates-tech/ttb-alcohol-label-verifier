from .models import ExpectedLabel, Status, VerificationReport
from .rules import (
    compare_abv,
    compare_name,
    compare_net_contents,
    compare_proof,
    compare_warning,
    extract_regulated_values,
)


def _overall(statuses: list[Status]) -> Status:
    if Status.MISMATCH in statuses:
        return Status.MISMATCH
    if Status.UNABLE in statuses:
        return Status.UNABLE
    if Status.POSSIBLE_MATCH in statuses:
        return Status.POSSIBLE_MATCH
    return Status.MATCH


def verify_label_text(text: str, expected: ExpectedLabel) -> VerificationReport:
    extracted = extract_regulated_values(text)
    checks = (
        compare_name("Brand name", expected.brand_name, text),
        compare_name("Class/type", expected.class_type, text),
        compare_abv(expected.abv, extracted["abv"]),
        compare_proof(extracted["abv"], extracted["proof"]),
        compare_net_contents(expected.net_contents_ml, extracted["net_contents_ml"]),
        compare_warning(extracted),
    )
    return VerificationReport(
        overall_status=_overall([check.status for check in checks]),
        checks=checks,
        extracted=extracted,
    )

