"""Tests for pairwise Pearson correlation analysis (P2-02).

Verifies that the 5 evaluation dimensions are measured independently —
no pair should have |r| > 0.7 (halo effect detection).
"""

from __future__ import annotations

from pathlib import Path

from evaluate.correlation import (
    IndependenceResult,
    compute_correlation_matrix,
    check_independence,
    extract_scores_from_ledger,
    format_correlation_matrix,
)

DIMENSIONS = (
    "clarity",
    "value_proposition",
    "cta",
    "brand_voice",
    "emotional_resonance",
)


def _make_independent_scores(n: int = 30) -> list[dict[str, float]]:
    """Generate synthetic scores with known independence (low correlation).

    Uses a simple deterministic pattern where each dimension varies
    independently based on different offsets.
    """
    scores: list[dict[str, float]] = []
    for i in range(n):
        scores.append({
            "clarity": 5.0 + (i % 7) * 0.5,
            "value_proposition": 3.0 + ((i * 3) % 11) * 0.5,
            "cta": 4.0 + ((i * 7) % 9) * 0.6,
            "brand_voice": 6.0 + ((i * 5) % 8) * 0.4,
            "emotional_resonance": 2.0 + ((i * 11) % 13) * 0.5,
        })
    return scores


def _make_correlated_scores(n: int = 30) -> list[dict[str, float]]:
    """Generate synthetic scores where clarity and value_proposition are highly correlated."""
    scores: list[dict[str, float]] = []
    for i in range(n):
        base = 3.0 + (i % 10) * 0.7
        scores.append({
            "clarity": base,
            "value_proposition": base + 0.1,  # nearly identical to clarity
            "cta": 4.0 + ((i * 7) % 9) * 0.6,
            "brand_voice": 6.0 + ((i * 5) % 8) * 0.4,
            "emotional_resonance": 2.0 + ((i * 11) % 13) * 0.5,
        })
    return scores


def _make_negative_correlated_scores(n: int = 30) -> list[dict[str, float]]:
    """Generate scores where clarity and cta are negatively correlated."""
    scores: list[dict[str, float]] = []
    for i in range(n):
        base = 3.0 + (i % 10) * 0.7
        scores.append({
            "clarity": base,
            "value_proposition": 5.0 + ((i * 3) % 11) * 0.4,
            "cta": 10.0 - base,  # inverse of clarity
            "brand_voice": 6.0 + ((i * 5) % 8) * 0.4,
            "emotional_resonance": 2.0 + ((i * 11) % 13) * 0.5,
        })
    return scores


# --- Data Structure Tests ---


def test_matrix_has_all_10_pairs() -> None:
    """5 dimensions produce 10 unique pairs in the correlation matrix."""
    scores = _make_independent_scores()
    matrix = compute_correlation_matrix(scores)
    assert len(matrix) == 10
    # Verify all pairs present
    expected_pairs = set()
    dims = list(DIMENSIONS)
    for i in range(len(dims)):
        for j in range(i + 1, len(dims)):
            expected_pairs.add((dims[i], dims[j]))
    assert set(matrix.keys()) == expected_pairs


def test_independence_result_structure() -> None:
    """IndependenceResult has pass/fail, max_r, and violating_pairs."""
    scores = _make_independent_scores()
    matrix = compute_correlation_matrix(scores)
    result = check_independence(matrix)
    assert isinstance(result, IndependenceResult)
    assert isinstance(result.passes, bool)
    assert isinstance(result.max_correlation, float)
    assert isinstance(result.violating_pairs, list)
    assert isinstance(result.matrix, dict)


# --- Independence Tests ---


def test_perfectly_independent_dimensions() -> None:
    """Synthetic independent data produces all |r| < 0.5."""
    scores = _make_independent_scores(50)
    matrix = compute_correlation_matrix(scores)
    for pair, r in matrix.items():
        assert abs(r) < 0.5, (
            f"Pair {pair} has r={r:.3f}, expected < 0.5 for independent data"
        )


def test_perfectly_correlated_pair_detected() -> None:
    """Highly correlated pair (r ~ 1.0) is detected and flagged."""
    scores = _make_correlated_scores()
    matrix = compute_correlation_matrix(scores)
    r = matrix[("clarity", "value_proposition")]
    assert abs(r) > 0.9, f"Expected r > 0.9, got {r:.3f}"

    result = check_independence(matrix)
    assert result.passes is False
    assert ("clarity", "value_proposition") in result.violating_pairs


def test_threshold_boundary() -> None:
    """r = 0.69 passes, r = 0.71 fails at threshold 0.7."""
    # Passing matrix: all below 0.7
    passing_matrix = {
        (DIMENSIONS[i], DIMENSIONS[j]): 0.69
        for i in range(5) for j in range(i + 1, 5)
    }
    result_pass = check_independence(passing_matrix, threshold=0.7)
    assert result_pass.passes is True

    # Failing matrix: one pair above 0.7
    failing_matrix = dict(passing_matrix)
    failing_matrix[("clarity", "value_proposition")] = 0.71
    result_fail = check_independence(failing_matrix, threshold=0.7)
    assert result_fail.passes is False
    assert ("clarity", "value_proposition") in result_fail.violating_pairs


def test_negative_correlation_detected() -> None:
    """Negative correlation (r = -0.8) also exceeds threshold (uses |r|)."""
    scores = _make_negative_correlated_scores()
    matrix = compute_correlation_matrix(scores)
    r = matrix[("clarity", "cta")]
    assert r < -0.7, f"Expected r < -0.7, got {r:.3f}"

    result = check_independence(matrix)
    assert result.passes is False
    assert ("clarity", "cta") in result.violating_pairs


# --- Ledger Extraction Tests ---


def test_extract_scores_from_ledger(tmp_path: Path) -> None:
    """Extracts dimension scores from AdEvaluated events in ledger."""
    from iterate.ledger import log_event

    ledger_path = str(tmp_path / "ledger.jsonl")
    for i in range(5):
        log_event(ledger_path, {
            "event_type": "AdEvaluated",
            "ad_id": f"ad_{i:03d}",
            "brief_id": "b001",
            "cycle_number": 1,
            "action": "evaluation",
            "inputs": {},
            "outputs": {
                "scores": {
                    "clarity": {"score": 7.0 + i * 0.2},
                    "value_proposition": {"score": 6.5 + i * 0.3},
                    "cta": {"score": 7.5 - i * 0.1},
                    "brand_voice": {"score": 8.0},
                    "emotional_resonance": {"score": 6.0 + i * 0.4},
                },
            },
            "scores": {},
            "tokens_consumed": 200,
            "model_used": "gemini-2.0-flash",
            "seed": "42",
        })

    scores = extract_scores_from_ledger(ledger_path)
    assert len(scores) == 5
    assert all(set(s.keys()) == set(DIMENSIONS) for s in scores)
    assert scores[0]["clarity"] == 7.0
    assert scores[2]["value_proposition"] == 6.5 + 2 * 0.3


def test_extract_scores_empty_ledger(tmp_path: Path) -> None:
    """Empty or missing ledger returns empty list."""
    scores = extract_scores_from_ledger(str(tmp_path / "missing.jsonl"))
    assert scores == []


# --- Edge Cases ---


def test_single_ad_returns_empty_matrix() -> None:
    """Need >= 2 data points for correlation; single ad returns empty."""
    scores = [{"clarity": 7.0, "value_proposition": 7.0, "cta": 7.0,
               "brand_voice": 7.0, "emotional_resonance": 7.0}]
    matrix = compute_correlation_matrix(scores)
    assert len(matrix) == 0


# --- Formatting ---


def test_format_correlation_matrix_readable() -> None:
    """Formatted matrix is human-readable string."""
    scores = _make_independent_scores()
    matrix = compute_correlation_matrix(scores)
    formatted = format_correlation_matrix(matrix)
    assert isinstance(formatted, str)
    assert "CLAR" in formatted
    assert "VP" in formatted
    # Should contain r values
    assert "0." in formatted or "-0." in formatted
