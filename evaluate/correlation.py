"""Pairwise Pearson correlation analysis for evaluation dimensions (P2-02).

Computes the 5×5 correlation matrix from evaluated ad scores.
Flags any dimension pair with |r| > 0.7 as a potential halo effect.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from iterate.ledger import read_events_filtered

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)


@dataclass
class IndependenceResult:
    """Result of checking dimension independence via correlation."""

    passes: bool
    max_correlation: float
    violating_pairs: list[tuple[str, str]]
    matrix: dict[tuple[str, str], float]


def _pearson_r(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient between two lists.

    Returns 0.0 if standard deviation of either list is zero.
    """
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

    if std_x == 0 or std_y == 0:
        return 0.0

    return cov / (std_x * std_y)


def compute_correlation_matrix(
    scores: list[dict[str, float]],
) -> dict[tuple[str, str], float]:
    """Compute pairwise Pearson correlation matrix for all dimension pairs.

    Args:
        scores: List of per-ad score dicts, each mapping dimension -> score.

    Returns:
        Dict mapping (dim_a, dim_b) tuples to Pearson r values.
        Returns empty dict if fewer than 2 data points.
    """
    if len(scores) < 2:
        return {}

    matrix: dict[tuple[str, str], float] = {}
    dims = list(DIMENSIONS)

    for i in range(len(dims)):
        for j in range(i + 1, len(dims)):
            d1, d2 = dims[i], dims[j]
            x = [s[d1] for s in scores]
            y = [s[d2] for s in scores]
            matrix[(d1, d2)] = round(_pearson_r(x, y), 4)

    return matrix


def check_independence(
    matrix: dict[tuple[str, str], float],
    threshold: float = 0.7,
) -> IndependenceResult:
    """Check whether all dimension pairs are below the correlation threshold.

    Args:
        matrix: Correlation matrix from compute_correlation_matrix().
        threshold: Maximum allowed |r| (default 0.7).

    Returns:
        IndependenceResult with pass/fail, violating pairs, and max correlation.
    """
    violating: list[tuple[str, str]] = []
    max_r = 0.0

    for pair, r in matrix.items():
        abs_r = abs(r)
        if abs_r > max_r:
            max_r = abs_r
        if abs_r > threshold:
            violating.append(pair)

    return IndependenceResult(
        passes=len(violating) == 0,
        max_correlation=round(max_r, 4),
        violating_pairs=violating,
        matrix=matrix,
    )


def extract_scores_from_ledger(ledger_path: str) -> list[dict[str, float]]:
    """Extract per-dimension scores from AdEvaluated events in the ledger.

    Reads first-cycle evaluations only to avoid regen bias.

    Args:
        ledger_path: Path to the JSONL ledger.

    Returns:
        List of score dicts, each mapping dimension name -> float score.
    """
    events = read_events_filtered(ledger_path, event_type="AdEvaluated")

    scores_list: list[dict[str, float]] = []
    for event in events:
        outputs = event.get("outputs", {})
        raw_scores = outputs.get("scores", {})

        if not raw_scores:
            continue

        flat: dict[str, float] = {}
        valid = True
        for dim in DIMENSIONS:
            dim_data = raw_scores.get(dim)
            if dim_data is None:
                valid = False
                break
            if isinstance(dim_data, dict):
                flat[dim] = float(dim_data.get("score", 5.0))
            elif isinstance(dim_data, (int, float)):
                flat[dim] = float(dim_data)
            else:
                valid = False
                break

        if valid and len(flat) == len(DIMENSIONS):
            scores_list.append(flat)

    return scores_list


def format_correlation_matrix(matrix: dict[tuple[str, str], float]) -> str:
    """Format the correlation matrix as a human-readable table.

    Args:
        matrix: Correlation matrix from compute_correlation_matrix().

    Returns:
        Formatted string suitable for logging or dashboard display.
    """
    if not matrix:
        return "No correlation data available (need >= 2 evaluated ads)."

    dims = list(DIMENSIONS)
    # Short labels for readability
    labels = {
        "clarity": "CLAR",
        "value_proposition": "VP",
        "cta": "CTA",
        "brand_voice": "BV",
        "emotional_resonance": "ER",
    }

    header = f"{'':>6}" + "".join(f"{labels[d]:>8}" for d in dims)
    lines = [header, "-" * len(header)]

    for i, d1 in enumerate(dims):
        row = f"{labels[d1]:>6}"
        for j, d2 in enumerate(dims):
            if i == j:
                row += f"{'1.000':>8}"
            elif i < j:
                r = matrix.get((d1, d2), 0.0)
                row += f"{r:>8.3f}"
            else:
                r = matrix.get((d2, d1), 0.0)
                row += f"{r:>8.3f}"
        lines.append(row)

    return "\n".join(lines)
