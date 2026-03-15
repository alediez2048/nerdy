"""Self-healing orchestrator — wires SPC + mutation + ratchet (P4-02).

Detects quality drift via SPC, diagnoses the root cause using the
existing brief_mutation module (P1-08), and prescribes corrective action.
Logs all healing events to the ledger.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from iterate.spc import detect_quality_drift
from iterate.brief_mutation import diagnose_weakness
from iterate.quality_ratchet import get_ratchet_state

logger = logging.getLogger(__name__)


@dataclass
class HealingAction:
    """Record of a self-healing action."""

    trigger: str
    diagnosis: str
    action_taken: str
    outcome: str


def run_healing_check(
    ledger_path: str,
    config: dict,
) -> HealingAction | None:
    """Check for quality drift and prescribe healing action.

    Flow:
    1. Run SPC on recent batch scores
    2. If drift detected → diagnose weakest dimension from recent evals
    3. Prescribe brief mutation strategy
    4. Return healing action (caller executes the mutation)

    Args:
        ledger_path: Path to the JSONL ledger.
        config: Pipeline configuration dict.

    Returns:
        HealingAction if drift detected, None if system is in control.
    """
    # Step 1: SPC check
    spc_window = config.get("spc_window", 10)
    spc_result = detect_quality_drift(ledger_path, window=spc_window)

    if spc_result.in_control:
        # Also update ratchet state for monitoring
        ratchet_config = {
            "quality_threshold": config.get("quality_threshold", 7.0),
            "ratchet_window": config.get("ratchet_window", 5),
            "ratchet_buffer": config.get("ratchet_buffer", 0.5),
        }
        get_ratchet_state(ledger_path, ratchet_config)
        return None

    # Step 2: Diagnose from recent evaluations
    from iterate.ledger import read_events
    events = read_events(ledger_path)
    eval_events = [e for e in events if e.get("event_type") == "AdEvaluated"]

    if eval_events:
        recent_eval = eval_events[-1]
        scores_raw = recent_eval.get("outputs", {}).get("scores", {})
        # Convert to the format diagnose_weakness expects: {dim: {score, rationale}}
        scores: dict = {}
        for dim, val in scores_raw.items():
            if isinstance(val, dict):
                scores[dim] = val
            else:
                scores[dim] = {"score": val, "rationale": ""}
        ad_id = recent_eval.get("ad_id", "unknown")
    else:
        # No eval events — use default low scores
        scores = {
            "clarity": {"score": 5.0, "rationale": ""},
            "value_proposition": {"score": 5.0, "rationale": ""},
            "cta": {"score": 5.0, "rationale": ""},
            "brand_voice": {"score": 5.0, "rationale": ""},
            "emotional_resonance": {"score": 5.0, "rationale": ""},
        }
        ad_id = "unknown"

    diagnosis = diagnose_weakness(ad_id, scores)

    # Step 3: Build healing action
    trigger_desc = f"SPC violation: {', '.join(spc_result.violations[:3])}"
    diagnosis_desc = f"Weakest dimension: {diagnosis.weakest_dimension} (score: {diagnosis.score:.1f})"
    action_desc = f"Prescribe brief mutation: {diagnosis.suggested_mutation[:80]}"

    healing = HealingAction(
        trigger=trigger_desc,
        diagnosis=diagnosis_desc,
        action_taken=action_desc,
        outcome="pending",
    )

    logger.warning(
        "Self-healing triggered: %s → %s → %s",
        trigger_desc, diagnosis_desc, action_desc,
    )

    return healing
