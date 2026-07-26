from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    MATCH = "Match"
    POSSIBLE_MATCH = "Possible Match"
    MISMATCH = "Mismatch"
    UNABLE = "Unable to Determine"


@dataclass(frozen=True)
class ExpectedLabel:
    brand_name: str
    class_type: str
    abv: float
    net_contents_ml: int


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float | None
    provider: str
    elapsed_seconds: float
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    field: str
    expected: str
    observed: str
    status: Status
    explanation: str
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationReport:
    overall_status: Status
    checks: tuple[CheckResult, ...]
    extracted: dict[str, Any]
    disclaimer: str = (
        "Decision-support result only. It is not a TTB approval, legal opinion, "
        "or substitute for human label review."
    )

