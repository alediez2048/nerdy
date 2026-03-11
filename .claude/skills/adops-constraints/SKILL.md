---
name: adops-constraints
description: Non-negotiable architectural guardrails for Ad-Ops-Autopilot. Use on EVERY task to prevent architectural violations. Triggers on any work involving generate/, evaluate/, iterate/, output/, tests/, data/, docs/, or project configuration files.
---

# Ad-Ops-Autopilot Project Guardrails

## Pipeline Architecture

Custom pipeline — NO LangChain, NO LlamaIndex, NO orchestration frameworks.

Build all pipeline stages from scratch using direct SDK calls:
- `google-genai` for LLM generation and evaluation (Gemini Flash + Pro)
- `pandas` for ledger queries and data analysis
- `matplotlib` for quality trend visualization
- `hashlib` for deterministic per-ad seed chains
- `tiktoken` for token counting

## Tech Stack — Locked

| Component | Technology | Do NOT Substitute |
|-----------|-----------|-------------------|
| Language | Python 3.10+ | — |
| LLM | Google Gemini API (Flash + Pro) | No OpenAI, no Anthropic |
| Data Store | Append-only JSONL ledger | No SQLite, no Postgres |
| Config | python-dotenv + config.yaml | No hardcoded values |
| Testing | pytest | — |
| Linting | ruff | — |
| Visualization | matplotlib + pandas | — |

## Code Standards

- Python type hints on every function signature and return type
- No `Any` types — use explicit typing everywhere
- Environment variables via `python-dotenv` through `.env` — never hardcode keys
- Error handling: `try/except` with typed exceptions, not bare `except:`
- All LLM API calls must include: token counting, purpose tag, seed, checkpoint write

## Module Ownership

| Directory | Owns | Does NOT Own |
|-----------|------|-------------|
| `generate/` | Brief expansion, ad copy generation, compliance prompt layer | Evaluation, regeneration logic |
| `evaluate/` | CoT scoring, dimension aggregation, confidence, calibration | Generation, ad modification |
| `iterate/` | Feedback loop, Pareto selection, brief mutation, quality ratchet, batch processing | Direct LLM calls (delegates) |
| `output/` | Export, replay, visualization | Pipeline state modification |
| `data/` | Static assets: brand KB, config, reference ads, pattern DB, ledger | Executable code |
| `tests/` | All test files | Production logic |
| `docs/` | Decision log, writeup, limitations | Code |

Do not put logic in the wrong module. Generation code does not evaluate. Evaluation code does not generate. Iterate orchestrates but delegates.

## Non-Negotiable Quality Rules

- **Quality threshold:** 7.0/10 weighted average minimum — immutable floor
- **Quality ratchet:** `max(7.0, rolling_5batch_avg - 0.5)` — never decreases
- **Dimension floors:** Clarity ≥ 6.0, Brand Voice ≥ 5.0 — violation = automatic rejection
- **Evaluation:** Chain-of-thought 5-step with contrastive rationales — no holistic scoring
- **Compliance:** Three-layer filter (prompt + evaluator + regex) — all must pass
- **Reproducibility:** Per-ad seed chains + full I/O snapshots — no global seeds

## Append-Only Ledger Schema

Every event must include ALL fields:

```python
{
    "timestamp": str,        # ISO-8601
    "event_type": str,       # AdGenerated|AdEvaluated|AdRegenerated|AdPublished|AdDiscarded|BatchCompleted
    "ad_id": str,
    "brief_id": str,
    "cycle_number": int,
    "action": str,           # generation|evaluation|regeneration-attempt-N|brief-expansion|triage
    "inputs": dict,
    "outputs": dict,
    "scores": dict,
    "tokens_consumed": int,
    "model_used": str,
    "seed": str,
    "checkpoint_id": str,    # UUID for resume
}
```

The ledger is append-only. NEVER modify or delete existing entries. NEVER use a database.

## Compliance Hard Constraints

### NEVER Generate
- Guaranteed score improvements ("Guaranteed 1500+")
- Fear-based language implying the child is deficient
- Specific competitor disparagement by name
- Unverified statistics, pricing, or testimonials
- Absolute promises ("100% guaranteed", "always works")
- PII in generated content

### Regex Layer Must Catch
- Dollar amounts without disclaimers: `\$\d+`
- Competitor trademarks used negatively: `Princeton Review|Kaplan|Khan Academy|Chegg` in negative context
- Absolute guarantees: `guaranteed|100%|always|never fail`

## Commit Discipline

Conventional Commits only: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`

Reference ticket ID in every commit. Do not commit to `main` directly. Branch-per-ticket.

## Scope Discipline

- Implement ONLY what the current ticket asks
- Do NOT import modules from future tickets
- Do NOT build v2/v3 features during v1
- Do NOT refactor code outside the current ticket scope
- Do NOT add packages to requirements.txt unless the ticket requires it
