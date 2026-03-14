"""API call snapshot capture for forensic reproducibility (R3-Q4)."""

from __future__ import annotations

from datetime import datetime, timezone


def capture_snapshot(
    prompt: str,
    response: str,
    model: str,
    parameters: dict,
    seed: int,
) -> dict:
    """Capture full I/O snapshot for an API call. Ready to embed in ledger events.

    Returns a JSON-serializable dict with: prompt, response, model_version,
    timestamp, parameters, seed. Caller stores in ledger event's inputs/outputs.
    """
    return {
        "prompt": prompt,
        "response": response,
        "model_version": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "parameters": dict(parameters),
        "seed": seed,
    }
