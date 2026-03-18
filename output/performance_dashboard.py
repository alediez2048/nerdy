"""Performance Feedback dashboard panel — Evaluator vs. Reality (PF-07).

Assembles data from PF-01 through PF-05 ledger events into a dashboard-ready
format. Produces a self-contained HTML snippet for the 9th dashboard panel.
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluate.correlation import DIMENSIONS
from iterate.ledger import read_events_filtered


@dataclass
class PerformancePanelData:
    """Dashboard-ready data for the Evaluator vs. Reality panel."""

    correlation_heatmap: dict[tuple[str, str], float]  # (dim, metric) -> r
    weight_comparison: dict[str, dict[str, float]]  # {original: {...}, recalibrated: {...}, delta: {...}}
    accuracy_summary: dict[str, float]  # {precision_at_k, recall_at_k, true_positive, ...}
    top_predictors: list[tuple[str, str, float]]  # [(dimension, metric, r), ...]
    key_findings: list[str]
    loop_status: str  # "simulated" | "live"
    sample_size: int


def get_performance_panel_data(ledger_path: str) -> PerformancePanelData:
    """Assemble performance panel data from ledger events.

    Reads PerformanceIngested, WeightsRecalibrated, and AccuracyReported events.
    """
    # Default empty state
    correlation_heatmap: dict[tuple[str, str], float] = {}
    weight_comparison: dict[str, dict[str, float]] = {}
    accuracy_summary: dict[str, float] = {}
    top_predictors: list[tuple[str, str, float]] = []
    key_findings: list[str] = []
    sample_size = 0

    # Read recalibration events
    recal_events = read_events_filtered(ledger_path, event_type="WeightsRecalibrated")
    if recal_events:
        latest = recal_events[-1]
        inputs = latest.get("inputs", {})
        outputs = latest.get("outputs", {})

        original = inputs.get("original_weights", {})
        recalibrated = outputs.get("recalibrated_weights", {})
        deltas = outputs.get("delta_per_dimension", {})

        weight_comparison = {
            "original": original,
            "recalibrated": recalibrated,
            "delta": deltas,
        }

        # Build correlation heatmap from correlation_basis
        corr_basis = inputs.get("correlation_basis", {})
        target_metric = inputs.get("target_metric", "ctr")
        for dim, r in corr_basis.items():
            correlation_heatmap[(dim, target_metric)] = r

        # Top predictors from correlation basis
        sorted_corr = sorted(corr_basis.items(), key=lambda x: abs(x[1]), reverse=True)
        top_predictors = [(dim, target_metric, r) for dim, r in sorted_corr[:5]]

    # Read performance events for sample size
    perf_events = read_events_filtered(ledger_path, event_type="PerformanceIngested")
    sample_size = len(perf_events)

    # Build findings from all available data
    if weight_comparison:
        deltas = weight_comparison.get("delta", {})
        gained = [(d, v) for d, v in deltas.items() if v > 0.01]
        lost = [(d, v) for d, v in deltas.items() if v < -0.01]
        if gained:
            top_gain = max(gained, key=lambda x: x[1])
            key_findings.append(
                f"{_dim_label(top_gain[0])} gained the most weight "
                f"({top_gain[1]:+.1%}) based on performance correlation."
            )
        if lost:
            top_loss = min(lost, key=lambda x: x[1])
            key_findings.append(
                f"{_dim_label(top_loss[0])} lost the most weight "
                f"({top_loss[1]:+.1%}) — less predictive of real outcomes than assumed."
            )

    if top_predictors:
        best = top_predictors[0]
        key_findings.append(
            f"Strongest predictor: {_dim_label(best[0])} → {best[1]} (r={best[2]:+.3f})."
        )

    if sample_size > 0:
        key_findings.append(f"Analysis based on {sample_size} performance records (simulated).")

    if not key_findings:
        key_findings.append("No performance data ingested yet. Run the PF pipeline to populate.")

    return PerformancePanelData(
        correlation_heatmap=correlation_heatmap,
        weight_comparison=weight_comparison,
        accuracy_summary=accuracy_summary,
        top_predictors=top_predictors,
        key_findings=key_findings,
        loop_status="simulated",
        sample_size=sample_size,
    )


def _dim_label(dim: str) -> str:
    labels = {
        "clarity": "Clarity",
        "value_proposition": "Value Proposition",
        "cta": "Call to Action",
        "brand_voice": "Brand Voice",
        "emotional_resonance": "Emotional Resonance",
    }
    return labels.get(dim, dim)


def format_panel_html(data: PerformancePanelData) -> str:
    """Generate a self-contained HTML snippet for the performance feedback panel."""
    # Weight comparison table rows
    weight_rows = ""
    if data.weight_comparison:
        original = data.weight_comparison.get("original", {})
        recalibrated = data.weight_comparison.get("recalibrated", {})
        deltas = data.weight_comparison.get("delta", {})

        for dim in DIMENSIONS:
            orig = original.get(dim, 0.2)
            recal = recalibrated.get(dim, 0.2)
            delta = deltas.get(dim, 0.0)
            color = "#2ecc71" if delta > 0.01 else "#e74c3c" if delta < -0.01 else "#95a5a6"
            sign = "+" if delta > 0 else ""
            weight_rows += f"""
            <tr>
                <td>{_dim_label(dim)}</td>
                <td>{orig:.1%}</td>
                <td>{recal:.1%}</td>
                <td style="color: {color}; font-weight: bold;">{sign}{delta:.1%}</td>
            </tr>"""

    # Correlation heatmap rows
    corr_rows = ""
    if data.top_predictors:
        for dim, metric, r in data.top_predictors:
            strength = "strong" if abs(r) > 0.4 else "moderate" if abs(r) > 0.2 else "weak"
            color = "#2ecc71" if abs(r) > 0.4 else "#f39c12" if abs(r) > 0.2 else "#e74c3c"
            corr_rows += f"""
            <tr>
                <td>{_dim_label(dim)}</td>
                <td>{metric.replace('_', ' ').title()}</td>
                <td style="color: {color}; font-weight: bold;">{r:+.3f}</td>
                <td>{strength}</td>
            </tr>"""

    # Findings list
    findings_html = ""
    for finding in data.key_findings:
        findings_html += f"<li>{finding}</li>\n"

    # Status badge
    status_color = "#f39c12" if data.loop_status == "simulated" else "#2ecc71"
    status_label = "Simulated Data" if data.loop_status == "simulated" else "Live Data"

    html = f"""
    <div class="panel" id="performance-feedback">
        <div class="panel-header">
            <h2>Panel 9: Evaluator vs. Reality</h2>
            <span class="status-badge" style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">{status_label}</span>
        </div>

        <div class="panel-section">
            <h3>Weight Recalibration (Before → After)</h3>
            <p class="note">Weights adjusted based on dimension-to-performance correlations. Blend: 70% data-driven + 30% prior.</p>
            <table class="data-table">
                <thead>
                    <tr><th>Dimension</th><th>Original</th><th>Recalibrated</th><th>Delta</th></tr>
                </thead>
                <tbody>{weight_rows}</tbody>
            </table>
        </div>

        <div class="panel-section">
            <h3>Dimension → Performance Correlations</h3>
            <table class="data-table">
                <thead>
                    <tr><th>Dimension</th><th>Metric</th><th>Pearson r</th><th>Strength</th></tr>
                </thead>
                <tbody>{corr_rows}</tbody>
            </table>
        </div>

        <div class="panel-section">
            <h3>Key Findings</h3>
            <ul class="findings-list">{findings_html}</ul>
        </div>

        <div class="panel-footer">
            <p class="disclaimer">
                Data source: Simulated performance records (PF-02). Copy quality contributes ~30% of CTR variance.
                Production deployment requires real Meta Ads Manager data to validate these correlations.
            </p>
            <p class="sample-info">Sample size: {data.sample_size} records</p>
        </div>
    </div>
    """
    return html
