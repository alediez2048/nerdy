# Ad-Ops-Autopilot

Autonomous ad copy generation system for Facebook/Instagram. Generates, evaluates, and iteratively improves ad copy for Varsity Tutors SAT test prep — optimizing for **quality per token spent**.

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd nerdy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY from https://ai.google.dev/

# 3. Run the pipeline
python run_pipeline.py

# 4. View the dashboard
python -m output.export_dashboard    # generates output/dashboard_data.json
python -m output.dashboard_builder   # generates output/dashboard.html
open output/dashboard.html           # macOS — or open in any browser
```

## Architecture

```
Brief → Expand → Generate → Evaluate → [Score ≥ 7.0? Publish : Regenerate]
                     ↑                              |
                     └──── Pareto Selection ─────────┘
```

| Module | Responsibility |
|--------|---------------|
| `generate/` | Brief expansion, ad copy generation, brand voice profiles, compliance, competitive patterns |
| `evaluate/` | 5-dimension CoT scoring, calibration, coherence checking, SPC monitoring |
| `iterate/` | Feedback loop, Pareto selection, quality ratchet, batch processing, self-healing |
| `output/` | Dashboard, ad library export, narrated replay |
| `data/` | Brand knowledge base, reference ads, competitive patterns, config, ledger |
| `tests/` | 670 tests — golden set, inversion, adversarial, pipeline, dashboard |
| `docs/` | Decision log, writeup, systems design, development log |

**Key design decisions:**
- **Evaluator-first** — Built and calibrated the evaluator before the generator (89.5% accuracy vs. reference labels)
- **5 independent dimensions** — Clarity, Value Proposition, CTA, Brand Voice, Emotional Resonance (floors: Clarity ≥ 6.0, Brand Voice ≥ 5.0)
- **Pareto-optimal regeneration** — Generate 3-5 variants, select the Pareto-dominant one. No dimension regression.
- **Append-only JSONL ledger** — Every event is immutable. Full audit trail, checkpoint-resume, forensic replay.
- **Quality ratchet** — `max(7.0, rolling_5batch_avg - 0.5)`. Standards only go up.

## Usage

```bash
# Full pipeline run (50+ ads)
python run_pipeline.py

# Resume from checkpoint after interruption
python run_pipeline.py --resume

# Dry run (no API calls)
python run_pipeline.py --dry-run

# Export ad library (JSON + CSV)
python -m output.export_ad_library

# Run tests
python -m pytest tests/ -v

# Lint
ruff check .
```

## Configuration

All tunable parameters in `data/config.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `quality_threshold` | 7.0 | Minimum weighted score to publish |
| `clarity_floor` | 6.0 | Absolute minimum — violation = auto-reject |
| `brand_voice_floor` | 5.0 | Absolute minimum — violation = auto-reject |
| `batch_size` | 10 | Ads per batch |
| `max_regeneration_cycles` | 3 | Hard cap on regen attempts |
| `pareto_variants` | 5 | Variants generated per regen cycle |
| `improvable_range` | [5.5, 7.0] | Score range that escalates to Gemini Pro |
| `global_seed` | "nerdy-p0-default" | Deterministic seed for reproducibility |

**Environment variables** (`.env`):
- `GEMINI_API_KEY` — Required. Get from [ai.google.dev](https://ai.google.dev/)

## Dashboard

The 8-panel HTML dashboard visualizes all pipeline data:

| Panel | Content |
|-------|---------|
| 1. Hero KPIs | Total ads, publish rate, avg score, cost |
| 2. Iteration Cycles | Before/after improvement cards per ad |
| 3. Quality Trends | Score progression with ratchet line, 4 chart views |
| 4. Dimension Deep-Dive | Per-dimension trends + correlation heatmap (r > 0.7 flagged) |
| 5. Ad Library | Filterable browser with scores, copy preview, expandable rationales |
| 6. Token Economics | Cost attribution, model routing, marginal analysis, auto-cap |
| 7. System Health | SPC control chart, confidence routing, compliance stats |
| 8. Competitive Intel | Hook distribution, competitor strategies, gap analysis |

**Single-file HTML** with embedded CSS/JS. Only external dependency: Chart.js CDN.

## Testing

```bash
python -m pytest tests/ -v          # 670 tests (669 pass, 1 expected API-dependent failure)
python -m pytest tests/ --tb=short  # Compact output
```

Test categories: golden set regression, inversion tests, adversarial boundary, correlation analysis, pipeline integration, dashboard rendering, ad library export.

## Deliverables

| Deliverable | Location |
|-------------|----------|
| Decision Log | [`docs/deliverables/decisionlog.md`](docs/deliverables/decisionlog.md) — 38 entries including 5 formal ADRs |
| Technical Writeup | [`docs/deliverables/writeup.md`](docs/deliverables/writeup.md) — 1-2 page architecture + results |
| Systems Design | [`docs/deliverables/systemsdesign.md`](docs/deliverables/systemsdesign.md) — Architecture and data flow |
| Demo Script | [`docs/deliverables/demo-script.md`](docs/deliverables/demo-script.md) — 7-min video storyboard |
| Ad Library | `output/ad_library.json`, `output/ad_library.csv` — Generated via `python -m output.export_ad_library` |
| Dashboard | `output/dashboard.html` — Generated via `python -m output.dashboard_builder` |
| Development Log | [`docs/development/DEVLOG.md`](docs/development/DEVLOG.md) — Per-ticket implementation notes |

## Limitations

- **No real performance data** — Quality scores predict internal quality, not CTR/CPA/ROAS. Simulation infrastructure validates the feedback loop architecture with synthetic data.
- **Evaluator calibrated on 42 ads** — Small reference set. Brand Voice assessment is approximate (~20 reference points vs. 100+ in production).
- **CTA diversity is weak** — Most generated CTAs default to "Learn More" despite explicit structural variety.
- **Gemini free tier rate limits** — Pipeline includes retry logic with exponential backoff (2^n seconds, max 60s, 3 retries).
- **Cold-start dependency** — Quality ratchet and SPC need 5+ batches of history before activating.

## Requirements

- Python 3.10–3.12
- Gemini API key (free tier at [ai.google.dev](https://ai.google.dev/))
- See [`docs/reference/ENVIRONMENT.md`](docs/reference/ENVIRONMENT.md) for detailed setup and troubleshooting
