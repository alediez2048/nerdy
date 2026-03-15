"""Dashboard HTML generator — single-file 8-panel dashboard (P5-02).

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


def _build_panel_content(panel_idx: int, data: dict) -> str:
    """Build content for a specific panel."""
    if panel_idx == 0:
        # Panel 1: Pipeline Summary
        hero_html = _build_hero_cards(data.get("pipeline_summary", {}))
        return f'<div class="hero-grid">{hero_html}</div>'

    if panel_idx == 1:
        # Panel 2: Iteration Cycles
        cards_html = _build_iteration_cards(data.get("iteration_cycles", []))
        return f'<div class="cycles-grid">{cards_html}</div>'

    # Panels 3-8: Placeholder for future tickets
    return '<div class="placeholder"><p>Panel content coming in next tickets.</p></div>'


def generate_dashboard_html(data: dict, output_path: str) -> None:
    """Generate the single-file HTML dashboard.

    Args:
        data: Dashboard data dict (from build_dashboard_data).
        output_path: Path to write the HTML file.
    """
    # Build tab buttons
    tab_buttons = []
    for i, name in enumerate(TAB_NAMES):
        active = ' class="tab-btn active"' if i == 0 else ' class="tab-btn"'
        tab_buttons.append(f'<button{active} data-tab="panel-{i}">{name}</button>')
    tabs_html = "\n".join(tab_buttons)

    # Build panel sections
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

    # Embed data as JSON for JS access
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

// Tab switching
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
