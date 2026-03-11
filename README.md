# Ad-Ops-Autopilot

Autonomous ad copy generation system for Facebook and Instagram. Generates, evaluates, and iteratively improves ad copy for Varsity Tutors (SAT test prep) with measurable quality gains per token spent.

## Setup

```bash
# 1. Clone and enter
git clone <repo-url>
cd nerdy

# 2. Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY from https://ai.google.dev/
```

## Usage

```bash
# Run the pipeline (after P1 implementation)
python run_pipeline.py

# Resume from checkpoint after interruption
python run_pipeline.py --resume
```

*Pipeline runner will be implemented in Phase 1. For now, setup and structure are ready.*

## Project Structure

```
generate/     — Ad copy generation from expanded briefs
evaluate/     — Chain-of-thought scoring, LLM-as-Judge
iterate/      — Feedback loop, Pareto selection, quality ratchet
output/       — Export, visualization, narrated replay
data/         — Config, brand knowledge, reference ads, ledger
tests/        — Golden set, inversion, adversarial, pipeline tests
docs/         — DEVLOG, tickets, reference
```

## Documentation

- **[DEVLOG](docs/DEVLOG.md)** — Development history, ticket status
- **[ENVIRONMENT](docs/reference/ENVIRONMENT.md)** — Setup, config, troubleshooting
- **[PRD](prd.md)** — Product requirements, 48 tickets across 6 phases

## Requirements

- Python 3.10–3.12 (3.14 not yet supported — tiktoken lacks prebuilt wheels)
- Gemini API key (free tier at [ai.google.dev](https://ai.google.dev/))
