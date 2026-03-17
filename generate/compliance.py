"""Tiered compliance filter — Layer 3: regex/keyword (P2-06, PB-03).

Three-layer defense-in-depth:
  Layer 1: Generation prompt constraints (P1-02)
  Layer 2: Evaluator score-based check (brand safety < 4.0)
  Layer 3: Regex pattern matching (this module) — cheapest, fastest, deterministic

A violation must beat ALL three layers to reach production.

PB-03 additions:
  - Nerdy language rules: "your student" → critical, "SAT Prep" → critical
  - Fake urgency: "spots filling fast", "limited enrollment", etc. → critical
  - Corporate jargon: "unlock potential", "maximize score", etc. → warning
  - Online tutoring framing → critical
  - Competitor references downgraded from "critical" to "info" (comparisons with data allowed)
  - Severity model: critical (blocks), warning (flags), info (informational)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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
    severity: str  # "critical", "warning", or "info"


@dataclass
class ComplianceResult:
    """Result of regex compliance check."""

    passes: bool
    violations: list[ComplianceViolation] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(v.severity == "critical" for v in self.violations)

    @property
    def critical_violations(self) -> list[ComplianceViolation]:
        return [v for v in self.violations if v.severity == "critical"]

    @property
    def warnings(self) -> list[ComplianceViolation]:
        return [v for v in self.violations if v.severity == "warning"]


# Compliance patterns: (rule_name, pattern, severity)
_COMPLIANCE_PATTERNS: list[tuple[str, str, str]] = [
    # --- Guaranteed outcomes (original) ---
    ("guaranteed_outcome", r"(?i)\bguarantee[ds]?\b", "critical"),
    ("guaranteed_outcome", r"(?i)\bnever\s+fail", "critical"),
    ("guaranteed_outcome", r"(?i)\balways\s+pass", "critical"),
    ("score_guarantee", r"(?i)\bguaranteed?\s+\d{3,4}\b", "critical"),

    # --- Absolute promises (original) ---
    ("absolute_promise", r"(?i)\b100\s*%", "critical"),
    ("absolute_promise", r"(?i)\balways\s+works?\b", "critical"),
    ("absolute_promise", r"(?i)\bproven\s+results\b", "warning"),

    # --- Nerdy language rules (PB-03) ---
    ("nerdy_wrong_address", r"(?i)\byour\s+student\b", "critical"),
    ("nerdy_wrong_product", r"(?i)\bSAT\s+[Pp]rep\b", "critical"),
    ("online_tutoring_frame", r"(?i)\bonline\s+tutoring\b", "critical"),

    # --- Fake urgency (PB-03) ---
    ("fake_urgency", r"(?i)\bspots?\s+filling\s+fast\b", "critical"),
    ("fake_urgency", r"(?i)\blimited\s+enrollment\b", "critical"),
    ("fake_urgency", r"(?i)\bsecure\s+(?:their|your|a)\s+spot\b", "critical"),
    ("fake_urgency", r"(?i)\bdon'?t\s+miss\s+out\b", "critical"),
    ("fake_urgency", r"(?i)\bact\s+now\b", "critical"),
    ("fake_urgency", r"(?i)\blimited\s+time\b", "critical"),

    # --- Corporate jargon (PB-03) — warnings, not blockers ---
    ("corporate_jargon", r"(?i)\bunlock\s+(?:their\s+)?potential\b", "warning"),
    ("corporate_jargon", r"(?i)\bmaximize\s+score\s*(?:potential)?\b", "warning"),
    ("corporate_jargon", r"(?i)\btailored\s+support\b", "warning"),
    ("corporate_jargon", r"(?i)\bcustom\s+strategies\b", "warning"),
    ("corporate_jargon", r"(?i)\bgrowth\s+areas\b", "warning"),
    ("corporate_jargon", r"(?i)\bconcrete\s+score\s+gains\b", "warning"),
    ("corporate_jargon", r"(?i)\bdream\s+college\s+within\s+reach\b", "warning"),

    # --- Fear-based language targeting the child (original) ---
    ("fear_language", r"(?i)\bfalling\s+behind\b", "critical"),
    ("fear_language", r"(?i)\bleft\s+behind\b", "critical"),
    ("fear_language", r"(?i)\bdeficient\b", "critical"),
    ("fear_language", r"(?i)\b(?:don'?t|do\s+not)\s+let\s+them\s+fail\b", "critical"),

    # --- Competitor references — downgraded to "info" (PB-03) ---
    # Supplementary explicitly encourages competitor comparisons with real data.
    # These are informational flags, not violations.
    ("competitor_reference", r"(?i)\bPrinceton\s+Review\b", "info"),
    ("competitor_reference", r"(?i)\bKaplan\b", "info"),
    ("competitor_reference", r"(?i)\bKhan\s+Academy\b", "info"),
    ("competitor_reference", r"(?i)\bChegg\b", "info"),
    ("competitor_reference", r"(?i)\bSylvan(?:\s+Learning)?\b", "info"),
    ("competitor_reference", r"(?i)\bKumon\b", "info"),
    ("competitor_reference", r"(?i)\bMathnasium\b", "info"),

    # --- Unverified pricing (original, kept as warning) ---
    ("unverified_pricing", r"\$\d+", "warning"),
]


def check_compliance(text: str) -> ComplianceResult:
    """Check ad text against all compliance patterns.

    Critical violations block publication (passes=False).
    Warning violations are flagged but don't block (passes=True).
    Info violations are informational only (not counted as violations for pass/fail).

    Args:
        text: The ad copy text to check.

    Returns:
        ComplianceResult with passes=False only if critical violations exist.
    """
    violations: list[ComplianceViolation] = []

    for rule_name, pattern, severity in _COMPLIANCE_PATTERNS:
        for match in re.finditer(pattern, text):
            violations.append(ComplianceViolation(
                rule_name=rule_name,
                matched_text=match.group(),
                pattern=pattern,
                severity=severity,
            ))

    has_critical = any(v.severity == "critical" for v in violations)

    return ComplianceResult(
        passes=not has_critical,
        violations=violations,
    )


def is_compliant(text: str) -> bool:
    """Convenience function: True if no critical compliance violations found.

    Args:
        text: The ad copy text to check.

    Returns:
        True if the text passes all critical compliance checks.
    """
    return check_compliance(text).passes


def check_nerdy_positives(text: str) -> list[str]:
    """Check for approved Nerdy language patterns (informational).

    Returns list of positive patterns found in the text.
    Useful for evaluator bonuses and dashboard reporting.
    """
    positives: list[str] = []
    lower = text.lower()

    if "your child" in lower:
        positives.append("uses_your_child")
    if "sat tutoring" in lower:
        positives.append("uses_sat_tutoring")
    # Conditional claim: score number + timeframe/condition
    if re.search(r"(?i)\d{2,3}\s*points?\s*.{0,30}(?:sessions?|weeks?|month)", text):
        positives.append("conditional_claim")
    # Specific mechanism
    if re.search(r"(?i)(?:diagnostic|built-in\s+(?:calculator|tools?)|digital\s+SAT\s+interface)", text):
        positives.append("specific_mechanism")
    # Real competitor data (name + price)
    if re.search(r"(?i)(?:Princeton|Kaplan|Khan).{0,40}\$\d+", text):
        positives.append("competitor_comparison_with_data")

    return positives


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
