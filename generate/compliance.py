"""Tiered compliance filter — Layer 3: regex/keyword (P2-06).

Three-layer defense-in-depth:
  Layer 1: Generation prompt constraints (P1-02)
  Layer 2: Evaluator score-based check (brand safety < 4.0)
  Layer 3: Regex pattern matching (this module) — cheapest, fastest, deterministic

A violation must beat ALL three layers to reach production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)

BRAND_SAFETY_SCORE_FLOOR = 4.0


@dataclass
class ComplianceViolation:
    """A single compliance violation found by the regex filter."""

    rule_name: str
    matched_text: str
    pattern: str
    severity: str  # "critical" or "warning"


@dataclass
class ComplianceResult:
    """Result of regex compliance check."""

    passes: bool
    violations: list[ComplianceViolation]


# Compliance patterns: (rule_name, pattern, severity)
_COMPLIANCE_PATTERNS: list[tuple[str, str, str]] = [
    # Guaranteed outcomes
    ("guaranteed_outcome", r"(?i)\bguarantee[ds]?\b", "critical"),
    ("guaranteed_outcome", r"(?i)\bnever\s+fail", "critical"),
    ("guaranteed_outcome", r"(?i)\balways\s+pass", "critical"),

    # Absolute promises
    ("absolute_promise", r"(?i)\b100\s*%", "critical"),
    ("absolute_promise", r"(?i)\balways\s+works?\b", "critical"),
    ("absolute_promise", r"(?i)\bproven\s+results\b", "warning"),

    # Unverified pricing
    ("unverified_pricing", r"\$\d+", "warning"),

    # Competitor references
    ("competitor_reference", r"(?i)\bPrinceton\s+Review\b", "critical"),
    ("competitor_reference", r"(?i)\bKaplan\b", "critical"),
    ("competitor_reference", r"(?i)\bKhan\s+Academy\b", "critical"),
    ("competitor_reference", r"(?i)\bChegg\b", "critical"),
    ("competitor_reference", r"(?i)\bSylvan\s+Learning\b", "critical"),

    # Fear-based language targeting the child
    ("fear_language", r"(?i)\bfalling\s+behind\b", "critical"),
    ("fear_language", r"(?i)\bleft\s+behind\b", "critical"),
    ("fear_language", r"(?i)\bdeficient\b", "critical"),
    ("fear_language", r"(?i)\b(?:don'?t|do\s+not)\s+let\s+them\s+fail\b", "critical"),
]


def check_compliance(text: str) -> ComplianceResult:
    """Check ad text against all compliance patterns.

    Args:
        text: The ad copy text to check.

    Returns:
        ComplianceResult with passes=True if no violations found.
    """
    violations: list[ComplianceViolation] = []

    for rule_name, pattern, severity in _COMPLIANCE_PATTERNS:
        matches = re.finditer(pattern, text)
        for match in matches:
            violations.append(ComplianceViolation(
                rule_name=rule_name,
                matched_text=match.group(),
                pattern=pattern,
                severity=severity,
            ))

    return ComplianceResult(
        passes=len(violations) == 0,
        violations=violations,
    )


def is_compliant(text: str) -> bool:
    """Convenience function: True if no compliance violations found.

    Args:
        text: The ad copy text to check.

    Returns:
        True if the text passes all compliance checks.
    """
    return check_compliance(text).passes


def check_evaluator_compliance(scores: dict[str, dict]) -> bool:
    """Layer 2: Check if evaluation scores indicate compliance issues.

    Any dimension score < 4.0 is a brand safety failure.

    Args:
        scores: Per-dimension score dicts from EvaluationResult.scores.

    Returns:
        True if all dimensions are above the brand safety floor.
    """
    for dim in DIMENSIONS:
        dim_data = scores.get(dim, {})
        score = float(dim_data.get("score", 5.0))
        if score < BRAND_SAFETY_SCORE_FLOOR:
            return False
    return True
