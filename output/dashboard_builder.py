"""Dashboard HTML generator — single-file 8-panel dashboard (P5-02, P5-03, P5-04).

Generates a self-contained HTML file with embedded CSS and JavaScript
that reads dashboard_data.json and renders all 8 panels. Chart.js CDN
is the only external dependency.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TAB_NAMES = [
    "Pipeline Summary",
    "Iteration Cycles",
    "Quality Trends",
    "Dimension Deep-Dive",
    "Ad Library",
    "Token Economics",
    "System Health",
    "Competitive Intel",
]

DIMENSIONS = ("clarity", "value_proposition", "cta", "brand_voice", "emotional_resonance")
DIM_COLORS = {
    "clarity": "#4CAF50",
    "value_proposition": "#2196F3",
    "cta": "#FF9800",
    "brand_voice": "#9C27B0",
    "emotional_resonance": "#F44336",
}
DIM_LABELS = {
    "clarity": "Clarity",
    "value_proposition": "Value Proposition",
    "cta": "CTA",
    "brand_voice": "Brand Voice",
    "emotional_resonance": "Emotional Resonance",
}


def _format_number(value: int | float, fmt: str = "int") -> str:
    """Format a number for display."""
    if fmt == "pct":
        return f"{value * 100:.1f}%"
    if fmt == "usd":
        return f"${value:.2f}"
    if fmt == "score":
        return f"{value:.1f}"
    if fmt == "comma":
        return f"{value:,}"
    return str(value)


def _build_hero_cards(summary: dict) -> str:
    """Build Panel 1 hero KPI cards HTML."""
    metrics = [
        ("Ads Generated", summary.get("total_ads_generated", 0), "int", "#4CAF50"),
        ("Ads Published", summary.get("total_ads_published", 0), "int", "#2196F3"),
        ("Publish Rate", summary.get("publish_rate", 0), "pct", "#FF9800"),
        ("Avg Score", summary.get("avg_score", 0), "score", "#9C27B0"),
        ("Total Batches", summary.get("total_batches", 0), "int", "#00BCD4"),
        ("Total Tokens", summary.get("total_tokens", 0), "comma", "#607D8B"),
        ("Total Cost", summary.get("total_cost_usd", 0), "usd", "#795548"),
        ("Ads Discarded", summary.get("total_ads_discarded", 0), "int", "#F44336"),
    ]
    cards = []
    for label, value, fmt, color in metrics:
        formatted = _format_number(value, fmt)
        cards.append(
            f'<div class="hero-card" style="border-top: 4px solid {color};">'
            f'<div class="hero-value">{formatted}</div>'
            f'<div class="hero-label">{label}</div>'
            f'</div>'
        )
    return "\n".join(cards)


def _build_iteration_cards(cycles: list[dict]) -> str:
    """Build Panel 2 iteration cycle cards HTML."""
    if not cycles:
        return '<p class="empty-state">No iteration cycles recorded.</p>'
    cards = []
    for c in cycles:
        delta = c.get("score_after", 0) - c.get("score_before", 0)
        delta_sign = "+" if delta >= 0 else ""
        delta_color = "#4CAF50" if delta >= 0 else "#F44336"
        action = c.get("action_taken", "unknown")
        border_color = "#4CAF50" if action == "published" else "#F44336" if action == "discarded" else "#FF9800"
        badge_class = "badge-published" if action == "published" else "badge-discarded" if action == "discarded" else "badge-regen"
        cards.append(
            f'<div class="cycle-card" style="border-left: 4px solid {border_color};">'
            f'<div class="cycle-header">'
            f'<span class="cycle-ad-id">{c.get("ad_id", "?")}</span>'
            f'<span class="badge {badge_class}">{action}</span>'
            f'</div>'
            f'<div class="cycle-scores">'
            f'<span class="score-before">{c.get("score_before", 0):.1f}</span>'
            f'<span class="score-arrow" style="color: {delta_color};">→</span>'
            f'<span class="score-after">{c.get("score_after", 0):.1f}</span>'
            f'<span class="score-delta" style="color: {delta_color};">'
            f'({delta_sign}{delta:.1f})</span>'
            f'</div>'
            f'<div class="cycle-detail">Weakest: <strong>{c.get("weakest_dimension", "?")}</strong>'
            f' | Cycle {c.get("cycle", "?")}</div>'
            f'</div>'
        )
    return "\n".join(cards)


def _build_quality_trends(trends: dict) -> str:
    """Build Panel 3: Quality Trends with 4 chart view toggles."""
    batch_scores = trends.get("batch_scores", [])
    ratchet = trends.get("ratchet_history", [])

    batches_json = json.dumps([b["batch"] for b in batch_scores])
    scores_json = json.dumps([b["avg_score"] for b in batch_scores])
    threshold_json = json.dumps([b.get("threshold", 7.0) for b in batch_scores])
    ratchet_json = json.dumps([r["threshold"] for r in ratchet])

    return f"""
<div class="chart-toggles">
  <button class="toggle-btn active" onclick="showChart('scoreTrend')">Average Score</button>
  <button class="toggle-btn" onclick="showChart('distribution')">Score Distribution</button>
  <button class="toggle-btn" onclick="showChart('publishRate')">Publish Rate</button>
  <button class="toggle-btn" onclick="showChart('costBatch')">Cost per Batch</button>
</div>
<div id="chart-scoreTrend" class="chart-container">
  <canvas id="scoreTrendChart"></canvas>
</div>
<div id="chart-distribution" class="chart-container" style="display:none;">
  <canvas id="distributionChart"></canvas>
</div>
<div id="chart-publishRate" class="chart-container" style="display:none;">
  <canvas id="publishRateChart"></canvas>
</div>
<div id="chart-costBatch" class="chart-container" style="display:none;">
  <canvas id="costBatchChart"></canvas>
</div>
<script>
var scoreTrendCtx = document.getElementById('scoreTrendChart');
if (scoreTrendCtx) {{
  new Chart(scoreTrendCtx, {{
    type: 'line',
    data: {{
      labels: {batches_json},
      datasets: [
        {{ label: 'Avg Score', data: {scores_json}, borderColor: '#2196F3', fill: false, tension: 0.3 }},
        {{ label: 'Threshold (7.0)', data: {threshold_json}, borderColor: '#999', borderDash: [5,5], fill: false, pointRadius: 0 }},
        {{ label: 'Ratchet', data: {ratchet_json}, borderColor: '#F44336', borderDash: [3,3], fill: false, pointRadius: 2 }}
      ]
    }},
    options: {{ responsive: true, plugins: {{ title: {{ display: true, text: 'Quality Score Trend with Ratchet Line' }} }} }}
  }});
}}
// Score Distribution chart
var distCtx = document.getElementById('distributionChart');
if (distCtx) {{
  var distData = {json.dumps(trends.get("score_distribution", [0]*10))};
  new Chart(distCtx, {{
    type: 'bar',
    data: {{
      labels: ['0-1','1-2','2-3','3-4','4-5','5-6','6-7','7-8','8-9','9-10'],
      datasets: [{{ label: 'Count', data: distData,
        backgroundColor: distData.map(function(v, i) {{ return i >= 7 ? '#4CAF50' : i >= 5 ? '#FF9800' : '#F44336'; }}) }}]
    }},
    options: {{ responsive: true, plugins: {{ title: {{ display: true, text: 'Score Distribution (All Evaluations)' }} }},
      scales: {{ y: {{ beginAtZero: true }} }} }}
  }});
}}
// Publish Rate chart
var pubCtx = document.getElementById('publishRateChart');
if (pubCtx) {{
  var pubLabels = {json.dumps([b["batch"] for b in batch_scores])};
  var pubData = {json.dumps([b.get("publish_rate", 0) for b in batch_scores])};
  new Chart(pubCtx, {{
    type: 'bar',
    data: {{
      labels: pubLabels.map(function(b) {{ return 'Batch ' + b; }}),
      datasets: [{{ label: 'Publish Rate', data: pubData.map(function(r) {{ return r * 100; }}),
        backgroundColor: '#4CAF50' }}]
    }},
    options: {{ responsive: true, plugins: {{ title: {{ display: true, text: 'Publish Rate per Batch (%)' }} }},
      scales: {{ y: {{ beginAtZero: true, max: 100 }} }} }}
  }});
}}
// Cost per Batch chart
var costCtx = document.getElementById('costBatchChart');
if (costCtx) {{
  var costLabels = {json.dumps([b["batch"] for b in batch_scores])};
  var costData = {json.dumps([b.get("tokens", 0) for b in batch_scores])};
  new Chart(costCtx, {{
    type: 'bar',
    data: {{
      labels: costLabels.map(function(b) {{ return 'Batch ' + b; }}),
      datasets: [{{ label: 'Tokens', data: costData, backgroundColor: '#2196F3' }}]
    }},
    options: {{ responsive: true, plugins: {{ title: {{ display: true, text: 'Token Cost per Batch' }} }},
      scales: {{ y: {{ beginAtZero: true }} }} }}
  }});
}}
function showChart(name) {{
  ['scoreTrend','distribution','publishRate','costBatch'].forEach(n => {{
    var el = document.getElementById('chart-' + n);
    if (el) el.style.display = (n === name) ? 'block' : 'none';
  }});
  document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}}
</script>
"""


def _build_dimension_deep_dive(dd: dict) -> str:
    """Build Panel 4: Dimension trends + correlation heatmap."""
    trends = dd.get("dimension_trends", {})
    corr = dd.get("correlation_matrix", {})

    # Dimension trend chart data
    datasets = []
    for dim in DIMENSIONS:
        vals = trends.get(dim, [])
        color = DIM_COLORS.get(dim, "#333")
        label = DIM_LABELS.get(dim, dim)
        datasets.append(
            f'{{ label: "{label}", data: {json.dumps(vals)}, '
            f'borderColor: "{color}", fill: false, tension: 0.3 }}'
        )
    datasets_str = ",\n        ".join(datasets)
    n_points = max((len(trends.get(d, [])) for d in DIMENSIONS), default=0)
    labels_json = json.dumps(list(range(1, n_points + 1)))

    # Correlation heatmap as HTML table
    heatmap_rows = []
    dims_list = list(DIMENSIONS)
    # Header row
    header_cells = '<th></th>' + ''.join(
        f'<th class="corr-header">{DIM_LABELS.get(d, d)[:3]}</th>' for d in dims_list
    )
    heatmap_rows.append(f'<tr>{header_cells}</tr>')
    # Data rows
    for d1 in dims_list:
        cells = [f'<td class="corr-label">{DIM_LABELS.get(d1, d1)}</td>']
        for d2 in dims_list:
            r_val = corr.get(d1, {}).get(d2, 0.0)
            abs_r = abs(r_val)
            if abs_r > 0.7:
                bg = "#F44336"
                fg = "#fff"
                cls = "high-corr"
            elif abs_r > 0.3:
                bg = "#FFF3E0"
                fg = "#333"
                cls = "mid-corr"
            else:
                bg = "#E8F5E9"
                fg = "#333"
                cls = "low-corr"
            cells.append(
                f'<td class="corr-cell {cls}" style="background:{bg};color:{fg};">'
                f'{r_val:.2f}</td>'
            )
        heatmap_rows.append(f'<tr>{"".join(cells)}</tr>')

    heatmap_html = '<table class="corr-table">' + ''.join(heatmap_rows) + '</table>'

    return f"""
<div class="sub-panel-grid-2">
  <div class="sub-panel">
    <h3>Dimension Trend Lines</h3>
    <canvas id="dimTrendChart"></canvas>
  </div>
  <div class="sub-panel">
    <h3>Correlation Heatmap</h3>
    <p class="corr-legend"><span style="color:#F44336;">Red = r &gt; 0.7 (halo effect)</span> |
    <span style="color:#FF9800;">Amber = 0.3–0.7</span> |
    <span style="color:#4CAF50;">Green = &lt; 0.3</span></p>
    {heatmap_html}
  </div>
</div>
<script>
var dimCtx = document.getElementById('dimTrendChart');
if (dimCtx) {{
  new Chart(dimCtx, {{
    type: 'line',
    data: {{
      labels: {labels_json},
      datasets: [
        {datasets_str}
      ]
    }},
    options: {{
      responsive: true,
      plugins: {{ title: {{ display: true, text: 'Per-Dimension Score Trends' }} }},
      scales: {{ y: {{ min: 0, max: 10 }} }}
    }}
  }});
}}
</script>
"""


def _build_ad_library(ads: list[dict]) -> str:
    """Build Panel 5: Filterable ad library with expandable cards."""
    if not ads:
        return '<p class="empty-state">No ads in library.</p>'

    # Filter bar
    filter_html = """
<div class="filter-bar">
  <label>Filter by Status:
    <select id="filterStatus" onchange="filterAds()">
      <option value="all">All</option>
      <option value="published">Published</option>
      <option value="discarded">Discarded</option>
    </select>
  </label>
  <label>Sort by:
    <select id="sortAds" onchange="filterAds()">
      <option value="score-desc">Score (High → Low)</option>
      <option value="score-asc">Score (Low → High)</option>
      <option value="id">Ad ID</option>
    </select>
  </label>
  <label>Search:
    <input type="text" id="searchAds" placeholder="Search ad copy..." oninput="filterAds()">
  </label>
</div>
"""

    # Ad cards
    card_items = []
    for ad in ads:
        ad_id = ad.get("ad_id", "?")
        score = ad.get("aggregate_score", 0)
        status = ad.get("status", "unknown")
        copy_data = ad.get("copy", {})
        headline = copy_data.get("headline", "")
        primary = copy_data.get("primary_text", "")
        preview = primary[:100] + "..." if len(primary) > 100 else primary
        scores = ad.get("scores", {})
        rationale = ad.get("rationale", {})
        cycles = ad.get("cycle_count", 1)

        score_color = "#4CAF50" if score >= 7.0 else "#FF9800" if score >= 5.0 else "#F44336"
        badge_cls = "badge-published" if status == "published" else "badge-discarded"

        # Dimension score mini-bars
        dim_html = ""
        for dim in DIMENSIONS:
            val = scores.get(dim, 0)
            v = val if isinstance(val, (int, float)) else 0
            label = DIM_LABELS.get(dim, dim)[:3]
            dim_html += f'<span class="dim-score">{label}: {v}</span> '

        # Rationale details (hidden by default)
        rationale_html = ""
        for dim in DIMENSIONS:
            r_text = rationale.get(dim, "")
            if r_text:
                label = DIM_LABELS.get(dim, dim)
                rationale_html += f'<p><strong>{label}:</strong> {r_text}</p>\n'

        card_items.append(
            f'<div class="ad-card" data-status="{status}" data-score="{score}" '
            f'data-copy="{headline} {primary}">'
            f'<div class="ad-card-header">'
            f'<span class="ad-id">{ad_id}</span>'
            f'<span class="badge {badge_cls}">{status}</span>'
            f'</div>'
            f'<div class="ad-score" style="color:{score_color};">{score:.1f}<span class="score-unit">/10</span></div>'
            f'<div class="ad-headline">{headline}</div>'
            f'<div class="ad-preview">{preview}</div>'
            f'<div class="ad-dims">{dim_html}</div>'
            f'<div class="ad-meta">{cycles} cycle(s)</div>'
            f'<button class="expand-btn" onclick="toggleExpand(this)">Details</button>'
            f'<div class="ad-expanded" style="display:none;">'
            f'<div class="rationale-section">'
            f'<h4>Evaluation Rationale</h4>'
            f'{rationale_html}'
            f'</div>'
            f'</div>'
            f'</div>'
        )

    cards_html = "\n".join(card_items)

    return f"""
{filter_html}
<div class="ad-grid" id="adGrid">
{cards_html}
</div>
<script>
function toggleExpand(btn) {{
  var expanded = btn.nextElementSibling;
  expanded.style.display = expanded.style.display === 'none' ? 'block' : 'none';
  btn.textContent = expanded.style.display === 'none' ? 'Details' : 'Collapse';
}}
function filterAds() {{
  var status = document.getElementById('filterStatus').value;
  var sort = document.getElementById('sortAds').value;
  var search = document.getElementById('searchAds').value.toLowerCase();
  var cards = document.querySelectorAll('.ad-card');
  var arr = Array.from(cards);
  arr.forEach(function(c) {{
    var s = c.dataset.status;
    var copy = (c.dataset.copy || '').toLowerCase();
    var show = (status === 'all' || s === status) && (search === '' || copy.indexOf(search) >= 0);
    c.style.display = show ? '' : 'none';
  }});
  if (sort === 'score-desc') arr.sort(function(a,b) {{ return parseFloat(b.dataset.score) - parseFloat(a.dataset.score); }});
  else if (sort === 'score-asc') arr.sort(function(a,b) {{ return parseFloat(a.dataset.score) - parseFloat(b.dataset.score); }});
  else arr.sort(function(a,b) {{ return a.querySelector('.ad-id').textContent.localeCompare(b.querySelector('.ad-id').textContent); }});
  var grid = document.getElementById('adGrid');
  arr.forEach(function(c) {{ grid.appendChild(c); }});
}}
</script>
"""


def _build_token_economics(econ: dict) -> str:
    """Build Panel 6: Token Economics with 6 sub-panels."""
    by_stage = econ.get("by_stage", {})
    by_model = econ.get("by_model", {})
    cost_per_pub = econ.get("cost_per_published", 0)
    marginal = econ.get("marginal_analysis", {})
    recommendation = marginal.get("recommendation", {})
    gain_curve = marginal.get("gain_curve", {})
    dim_breakdown = marginal.get("dimension_breakdown", [])

    # Sub-panel 1: Cost Attribution pie
    stage_labels = json.dumps(list(by_stage.keys()))
    stage_values = json.dumps(list(by_stage.values()))

    # Sub-panel 2: Model routing
    model_labels = json.dumps(list(by_model.keys()))
    model_values = json.dumps(list(by_model.values()))

    # Sub-panel 3: Marginal gain curve
    gain_labels = json.dumps([f"Cycle {k}" for k in sorted(gain_curve.keys(), key=lambda x: int(x))] if gain_curve else [])
    gain_values = json.dumps([gain_curve[k] for k in sorted(gain_curve.keys(), key=lambda x: int(x))] if gain_curve else [])

    # Sub-panel 4: Auto-cap recommendation
    max_cycles = recommendation.get("max_cycles", "N/A")
    reason = recommendation.get("reason", "No recommendation available")
    savings = recommendation.get("savings_tokens", 0)

    # Sub-panel 5: Dimension breakdown table
    dim_rows = ""
    for d in dim_breakdown:
        dim_rows += (
            f'<tr><td>{d.get("dimension", "")}</td>'
            f'<td>{d.get("cycle_1", 0)}</td>'
            f'<td>{d.get("cycle_2", 0)}</td>'
            f'<td>{d.get("cycle_3", 0)}</td></tr>'
        )

    return f"""
<div class="sub-panel-grid-3">
  <div class="sub-panel econ-sub">
    <h3>Cost Attribution by Stage</h3>
    <canvas id="stageChart"></canvas>
  </div>
  <div class="sub-panel econ-sub">
    <h3>Model Routing Breakdown</h3>
    <canvas id="modelChart"></canvas>
  </div>
  <div class="sub-panel econ-sub">
    <h3>Marginal Gain Curve</h3>
    <canvas id="gainChart"></canvas>
  </div>
  <div class="sub-panel econ-sub">
    <h3>Recommended Max Cycles</h3>
    <div class="rec-card">
      <div class="rec-value">{max_cycles}</div>
      <div class="rec-label">cycles</div>
      <p class="rec-reason">{reason}</p>
      <p class="rec-savings">Est. savings: {savings:,} tokens</p>
    </div>
  </div>
  <div class="sub-panel econ-sub">
    <h3>Dimension Marginal Breakdown</h3>
    <table class="corr-table">
      <tr><th>Dimension</th><th>Cycle 1</th><th>Cycle 2</th><th>Cycle 3</th></tr>
      {dim_rows}
    </table>
  </div>
  <div class="sub-panel econ-sub">
    <h3>Cost per Published Ad</h3>
    <div class="rec-card">
      <div class="rec-value">{cost_per_pub:,.0f}</div>
      <div class="rec-label">tokens / published ad</div>
    </div>
  </div>
</div>
<script>
var stageCtx = document.getElementById('stageChart');
if (stageCtx) {{
  new Chart(stageCtx, {{
    type: 'doughnut',
    data: {{ labels: {stage_labels}, datasets: [{{ data: {stage_values},
      backgroundColor: ['#4CAF50','#2196F3','#FF9800','#9C27B0','#00BCD4','#607D8B'] }}] }},
    options: {{ responsive: true, plugins: {{ title: {{ display: false }} }} }}
  }});
}}
var modelCtx = document.getElementById('modelChart');
if (modelCtx) {{
  new Chart(modelCtx, {{
    type: 'bar',
    data: {{ labels: {model_labels}, datasets: [{{ label: 'Tokens', data: {model_values},
      backgroundColor: ['#2196F3','#FF9800','#4CAF50','#9C27B0'] }}] }},
    options: {{ responsive: true, plugins: {{ title: {{ display: false }} }} }}
  }});
}}
var gainCtx = document.getElementById('gainChart');
if (gainCtx) {{
  new Chart(gainCtx, {{
    type: 'line',
    data: {{ labels: {gain_labels}, datasets: [
      {{ label: 'Avg Gain', data: {gain_values}, borderColor: '#2196F3', fill: false, tension: 0.3 }},
      {{ label: 'Min Threshold (0.2)', data: {json.dumps([0.2] * len(gain_curve))}, borderColor: '#F44336', borderDash: [5,5], fill: false, pointRadius: 0 }}
    ] }},
    options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
  }});
}}
</script>
"""


def _build_system_health(health: dict) -> str:
    """Build Panel 7: System Health — SPC, confidence, compliance."""
    spc = health.get("spc", {})
    confidence = health.get("confidence_stats", {})
    compliance = health.get("compliance_stats", {})

    # SPC chart
    batch_avgs = spc.get("batch_averages", [])
    ucl = spc.get("ucl")
    lcl = spc.get("lcl")
    mean = spc.get("mean")
    spc_labels = json.dumps(list(range(1, len(batch_avgs) + 1)))
    spc_data = json.dumps(batch_avgs)
    ucl_line = json.dumps([ucl] * len(batch_avgs) if ucl else [])
    lcl_line = json.dumps([lcl] * len(batch_avgs) if lcl else [])
    mean_line = json.dumps([mean] * len(batch_avgs) if mean else [])

    # Confidence stats
    auto_count = confidence.get("autonomous_count", 0)
    auto_pct = confidence.get("autonomous_pct", 0)
    flagged_count = confidence.get("flagged_count", 0)
    flagged_pct = confidence.get("flagged_pct", 0)
    human_count = confidence.get("human_required_count", 0)
    human_pct = confidence.get("human_required_pct", 0)

    # Compliance stats
    comp_total = compliance.get("total_checked", 0)
    comp_passed = compliance.get("passed", 0)
    comp_failed = compliance.get("failed", 0)
    comp_rate = compliance.get("pass_rate", 0)

    return f"""
<div class="sub-panel-grid-2">
  <div class="sub-panel">
    <h3>SPC Control Chart</h3>
    <canvas id="spcChart"></canvas>
    <p class="spc-legend">UCL: {ucl or 'N/A'} | Mean: {mean or 'N/A'} | LCL: {lcl or 'N/A'}</p>
  </div>
  <div class="sub-panel">
    <h3>Confidence Routing</h3>
    <div class="conf-grid">
      <div class="conf-item conf-auto">
        <div class="conf-value">{auto_count}</div>
        <div class="conf-label">Autonomous ({auto_pct:.0f}%)</div>
      </div>
      <div class="conf-item conf-flagged">
        <div class="conf-value">{flagged_count}</div>
        <div class="conf-label">Flagged ({flagged_pct:.0f}%)</div>
      </div>
      <div class="conf-item conf-human">
        <div class="conf-value">{human_count}</div>
        <div class="conf-label">Human Required ({human_pct:.0f}%)</div>
      </div>
    </div>
  </div>
  <div class="sub-panel">
    <h3>Compliance Stats</h3>
    <div class="compliance-grid">
      <div class="comp-stat"><strong>{comp_total}</strong> checked</div>
      <div class="comp-stat"><strong>{comp_passed}</strong> passed</div>
      <div class="comp-stat"><strong>{comp_failed}</strong> failed</div>
      <div class="comp-stat"><strong>{comp_rate:.0%}</strong> pass rate</div>
    </div>
  </div>
</div>
<script>
var spcCtx = document.getElementById('spcChart');
if (spcCtx && {spc_data}.length > 0) {{
  new Chart(spcCtx, {{
    type: 'line',
    data: {{
      labels: {spc_labels},
      datasets: [
        {{ label: 'Batch Avg', data: {spc_data}, borderColor: '#2196F3', fill: false, tension: 0.2 }},
        {{ label: 'UCL', data: {ucl_line}, borderColor: '#F44336', borderDash: [5,5], fill: false, pointRadius: 0 }},
        {{ label: 'LCL', data: {lcl_line}, borderColor: '#F44336', borderDash: [5,5], fill: false, pointRadius: 0 }},
        {{ label: 'Mean', data: {mean_line}, borderColor: '#999', borderDash: [3,3], fill: false, pointRadius: 0 }}
      ]
    }},
    options: {{ responsive: true, plugins: {{ title: {{ display: true, text: 'SPC Control Chart' }} }} }}
  }});
}}
</script>
"""


def _build_competitive_intel(intel: dict) -> str:
    """Build Panel 8: Competitive Intelligence."""
    if not intel:
        return '<p class="empty-state">No competitive intelligence data collected.</p>'

    hook_dist = intel.get("hook_distribution", {})
    strategy_radar = intel.get("strategy_radar", {})
    gap_analysis = intel.get("gap_analysis", [])
    temporal = intel.get("temporal_trends", [])

    # Hook distribution chart
    hook_labels = json.dumps(list(hook_dist.keys()))
    hook_values = json.dumps(list(hook_dist.values()))

    # Competitor table
    comp_rows = ""
    for comp, hooks in strategy_radar.items():
        top_hooks = ", ".join(f"{k}: {v}" for k, v in sorted(hooks.items(), key=lambda x: -x[1])[:3])
        comp_rows += f'<tr><td>{comp}</td><td>{sum(hooks.values())}</td><td>{top_hooks}</td></tr>'

    # Gap analysis
    gap_items = ""
    for g in gap_analysis:
        gap_items += (
            f'<div class="gap-item">'
            f'<strong>{g.get("hook_type", "")}</strong>: '
            f'{g.get("opportunity", "")}'
            f'</div>'
        )

    # Trends
    trend_items = ""
    for t in temporal:
        direction = t.get("direction", "")
        arrow = "↑" if direction == "increasing" else "↓" if direction == "decreasing" else "→"
        trend_items += (
            f'<div class="trend-item">'
            f'<span class="trend-hook">{t.get("hook_type", "")}</span> '
            f'<span class="trend-arrow">{arrow}</span> '
            f'{t.get("change_pct", 0):.0f}%'
            f'</div>'
        )

    return f"""
<div class="sub-panel-grid-2">
  <div class="sub-panel">
    <h3>Hook Type Distribution</h3>
    <canvas id="hookChart"></canvas>
  </div>
  <div class="sub-panel">
    <h3>Competitor Patterns</h3>
    <table class="corr-table">
      <tr><th>Competitor</th><th>Patterns</th><th>Top Hooks</th></tr>
      {comp_rows}
    </table>
  </div>
  <div class="sub-panel">
    <h3>Gap Analysis</h3>
    {gap_items if gap_items else '<p class="empty-state">No gaps detected.</p>'}
  </div>
  <div class="sub-panel">
    <h3>Trending Hooks</h3>
    {trend_items if trend_items else '<p class="empty-state">No significant trends.</p>'}
  </div>
</div>
<script>
var hookCtx = document.getElementById('hookChart');
if (hookCtx) {{
  new Chart(hookCtx, {{
    type: 'bar',
    data: {{ labels: {hook_labels}, datasets: [{{ label: 'Count', data: {hook_values},
      backgroundColor: ['#4CAF50','#2196F3','#FF9800','#9C27B0','#00BCD4','#F44336'] }}] }},
    options: {{ responsive: true, plugins: {{ title: {{ display: false }} }} }}
  }});
}}
</script>
"""


def _build_panel_content(panel_idx: int, data: dict) -> str:
    """Build content for a specific panel."""
    if panel_idx == 0:
        hero_html = _build_hero_cards(data.get("pipeline_summary", {}))
        return f'<div class="hero-grid">{hero_html}</div>'
    if panel_idx == 1:
        cards_html = _build_iteration_cards(data.get("iteration_cycles", []))
        return f'<div class="cycles-grid">{cards_html}</div>'
    if panel_idx == 2:
        return _build_quality_trends(data.get("quality_trends", {}))
    if panel_idx == 3:
        return _build_dimension_deep_dive(data.get("dimension_deep_dive", {}))
    if panel_idx == 4:
        return _build_ad_library(data.get("ad_library", []))
    if panel_idx == 5:
        return _build_token_economics(data.get("token_economics", {}))
    if panel_idx == 6:
        return _build_system_health(data.get("system_health", {}))
    if panel_idx == 7:
        return _build_competitive_intel(data.get("competitive_intel", {}))
    return '<div class="placeholder"><p>Panel content coming soon.</p></div>'


def generate_dashboard_html(data: dict, output_path: str) -> None:
    """Generate the single-file HTML dashboard.

    Args:
        data: Dashboard data dict (from build_dashboard_data).
        output_path: Path to write the HTML file.
    """
    tab_buttons = []
    for i, name in enumerate(TAB_NAMES):
        active = ' class="tab-btn active"' if i == 0 else ' class="tab-btn"'
        tab_buttons.append(f'<button{active} data-tab="panel-{i}">{name}</button>')
    tabs_html = "\n".join(tab_buttons)

    panels = []
    for i, name in enumerate(TAB_NAMES):
        display = "block" if i == 0 else "none"
        content = _build_panel_content(i, data)
        panels.append(
            f'<div id="panel-{i}" class="panel" style="display: {display};">'
            f'<h2>{name}</h2>'
            f'{content}'
            f'</div>'
        )
    panels_html = "\n".join(panels)

    data_json = json.dumps(data, default=str)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ad-Ops-Autopilot Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }}
header {{ background: #1a1a2e; color: #fff; padding: 20px 30px; }}
header h1 {{ font-size: 1.5rem; font-weight: 600; }}
header p {{ font-size: 0.85rem; color: #aaa; margin-top: 4px; }}
.tab-bar {{ display: flex; gap: 0; background: #16213e; padding: 0 20px; overflow-x: auto; }}
.tab-btn {{ background: none; border: none; color: #999; padding: 12px 18px; cursor: pointer; font-size: 0.85rem; border-bottom: 3px solid transparent; white-space: nowrap; }}
.tab-btn:hover {{ color: #fff; }}
.tab-btn.active {{ color: #fff; border-bottom-color: #4CAF50; }}
.panel {{ padding: 24px 30px; max-width: 1200px; margin: 0 auto; }}
.panel h2 {{ font-size: 1.3rem; margin-bottom: 20px; color: #1a1a2e; }}
.hero-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
.hero-card {{ background: #fff; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }}
.hero-value {{ font-size: 2rem; font-weight: 700; color: #1a1a2e; }}
.hero-label {{ font-size: 0.85rem; color: #666; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
.cycles-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }}
.cycle-card {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }}
.cycle-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
.cycle-ad-id {{ font-weight: 600; font-size: 0.95rem; }}
.badge {{ font-size: 0.7rem; padding: 3px 8px; border-radius: 12px; text-transform: uppercase; font-weight: 600; }}
.badge-published {{ background: #E8F5E9; color: #2E7D32; }}
.badge-discarded {{ background: #FFEBEE; color: #C62828; }}
.badge-regen {{ background: #FFF3E0; color: #E65100; }}
.cycle-scores {{ display: flex; align-items: center; gap: 8px; font-size: 1.3rem; margin-bottom: 8px; }}
.score-before {{ color: #999; }}
.score-after {{ font-weight: 700; }}
.score-delta {{ font-size: 0.9rem; }}
.cycle-detail {{ font-size: 0.8rem; color: #666; }}
.placeholder {{ text-align: center; padding: 60px; color: #999; }}
.empty-state {{ text-align: center; padding: 40px; color: #999; font-style: italic; }}
/* Panel 3: Quality Trends */
.chart-toggles {{ display: flex; gap: 8px; margin-bottom: 16px; }}
.toggle-btn {{ padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.85rem; }}
.toggle-btn.active {{ background: #1a1a2e; color: #fff; border-color: #1a1a2e; }}
.chart-container {{ background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); min-height: 300px; }}
/* Panel 4: Dimension Deep-Dive */
.sub-panel-grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.sub-panel {{ background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }}
.sub-panel h3 {{ font-size: 1rem; margin-bottom: 12px; color: #1a1a2e; }}
.corr-table {{ border-collapse: collapse; width: 100%; font-size: 0.8rem; }}
.corr-table th, .corr-table td {{ padding: 8px; text-align: center; border: 1px solid #eee; }}
.corr-header {{ font-weight: 600; background: #f5f5f5; }}
.corr-label {{ font-weight: 600; text-align: left; background: #f5f5f5; }}
.corr-legend {{ font-size: 0.75rem; margin-bottom: 8px; }}
/* Panel 5: Ad Library */
.filter-bar {{ display: flex; gap: 16px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; background: #fff; padding: 12px 16px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }}
.filter-bar label {{ font-size: 0.85rem; display: flex; align-items: center; gap: 6px; }}
.filter-bar select, .filter-bar input {{ padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; }}
.ad-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 12px; }}
.ad-card {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }}
.ad-card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
.ad-id {{ font-weight: 600; font-size: 0.9rem; }}
.ad-score {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 6px; }}
.score-unit {{ font-size: 0.9rem; color: #999; font-weight: 400; }}
.ad-headline {{ font-weight: 600; margin-bottom: 4px; }}
.ad-preview {{ font-size: 0.85rem; color: #666; margin-bottom: 8px; }}
.ad-dims {{ font-size: 0.75rem; color: #555; margin-bottom: 6px; }}
.dim-score {{ display: inline-block; margin-right: 8px; padding: 2px 6px; background: #f0f0f0; border-radius: 3px; }}
.ad-meta {{ font-size: 0.75rem; color: #999; margin-bottom: 8px; }}
.expand-btn {{ background: none; border: 1px solid #ddd; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }}
.expand-btn:hover {{ background: #f5f5f5; }}
.ad-expanded {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee; }}
.rationale-section h4 {{ font-size: 0.9rem; margin-bottom: 8px; }}
.rationale-section p {{ font-size: 0.8rem; color: #555; margin-bottom: 4px; }}
/* Panel 6: Token Economics */
.sub-panel-grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
.rec-card {{ text-align: center; padding: 20px; }}
.rec-value {{ font-size: 2.5rem; font-weight: 700; color: #1a1a2e; }}
.rec-label {{ font-size: 0.85rem; color: #666; margin-top: 4px; }}
.rec-reason {{ font-size: 0.8rem; color: #555; margin-top: 12px; }}
.rec-savings {{ font-size: 0.8rem; color: #4CAF50; margin-top: 4px; }}
/* Panel 7: System Health */
.spc-legend {{ font-size: 0.75rem; color: #666; margin-top: 8px; text-align: center; }}
.conf-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; text-align: center; }}
.conf-item {{ padding: 16px; border-radius: 8px; }}
.conf-auto {{ background: #E8F5E9; }}
.conf-flagged {{ background: #FFF3E0; }}
.conf-human {{ background: #FFEBEE; }}
.conf-value {{ font-size: 1.5rem; font-weight: 700; }}
.conf-label {{ font-size: 0.75rem; color: #555; margin-top: 4px; }}
.compliance-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
.comp-stat {{ padding: 12px; background: #f9f9f9; border-radius: 6px; text-align: center; font-size: 0.9rem; }}
/* Panel 8: Competitive Intel */
.gap-item {{ padding: 8px 12px; background: #FFF3E0; border-radius: 6px; margin-bottom: 6px; font-size: 0.85rem; }}
.trend-item {{ display: flex; gap: 8px; align-items: center; padding: 6px 0; font-size: 0.85rem; }}
.trend-hook {{ font-weight: 600; }}
.trend-arrow {{ font-size: 1.2rem; }}
@media (max-width: 768px) {{
  .sub-panel-grid-2 {{ grid-template-columns: 1fr; }}
  .sub-panel-grid-3 {{ grid-template-columns: 1fr; }}
  .ad-grid {{ grid-template-columns: 1fr; }}
  .filter-bar {{ flex-direction: column; }}
  .conf-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<header>
<h1>Ad-Ops-Autopilot Dashboard</h1>
<p>Generated: {data.get("generated_at", "N/A")}</p>
</header>
<nav class="tab-bar">
{tabs_html}
</nav>
<main>
{panels_html}
</main>
<script>
const DASHBOARD_DATA = {data_json};

document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).style.display = 'block';
    }});
}});
</script>
</body>
</html>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html)
    logger.info("Dashboard HTML written to %s", output_path)
