# Ad-Ops-Autopilot Interview Prep Summary

## Project Summary
Ad-Ops-Autopilot is an autonomous ad generation system built for Varsity Tutors-style Facebook and Instagram ads. The goal was not just to generate ad copy, but to build a system that can generate, evaluate, and improve ads with minimal human intervention while staying aware of quality, cost, and reproducibility.

At a high level, the project takes a brief, expands it into richer context, generates creative assets, evaluates them using a structured rubric, and surfaces the results through an internal product layer with sessions, campaigns, dashboards, and live progress updates.

The most important framing for an interview is this: this project was approached as a systems engineering problem, not a prompt engineering exercise.

## Story
The main problem I wanted to solve was that most AI creative tools stop at generation. They can produce something quickly, but they cannot reliably explain whether it is good, why it is good, or how to improve it. I wanted to build a system that behaves more like an operator than a simple text generator.

That drove the biggest early decision: I started with evaluation before generation. I defined ad quality using five dimensions:

- clarity
- value proposition
- call to action
- brand voice
- emotional resonance

By decomposing quality this way, I gave the system a way to judge outputs in a structured and explainable way instead of relying on a vague single score.

From there, I separated the project into clear modules for generation, evaluation, orchestration, output, and product UX. That made the system easier to reason about, easier to test, and easier to explain.

## Tech Stack
The project uses a two-layer stack: a pipeline layer and an application layer.

### Pipeline Layer
- Python 3.10+
- Gemini models for text generation and evaluation
- Gemini image generation flows
- Fal / Veo / Kling integrations for video generation
- YAML config via `data/config.yaml`
- `.env`-based secrets management
- `pytest` for testing
- `ruff` for linting
- append-only JSONL ledger for pipeline state

### Application Layer
- FastAPI
- SQLAlchemy
- PostgreSQL
- Celery
- Redis
- React
- Vite

### Storage Model
- PostgreSQL stores application data such as users, sessions, campaigns, and curation state.
- The append-only JSONL ledger remains the source of truth for pipeline events and outputs.

## Systems Design
The system is modular by design.

### Module Responsibilities
- `generate/`: brief expansion, ad generation, brand voice, generation helpers
- `evaluate/`: scoring, quality logic, evaluator behavior
- `iterate/`: orchestration, routing, regeneration-oriented logic
- `output/`: dashboards, exports, ad libraries, reporting
- `app/`: API layer, workers, session management, campaigns, frontend UI

### End-to-End Flow
1. A user creates a session in the app.
2. FastAPI stores the session config in PostgreSQL.
3. Celery runs the pipeline in the background.
4. The pipeline expands the brief.
5. The pipeline generates ad copy and media assets.
6. The evaluator scores the ad on five dimensions.
7. The system routes the ad based on score and thresholds.
8. Every major event is written to the ledger.
9. Redis pushes progress updates for the UI.
10. Dashboard and ad library views are built from ledger-derived data.

### Architectural Principles
- Treat generation as one stage in a broader system, not the whole product.
- Separate pipeline concerns from app concerns.
- Make every major decision traceable.
- Make quality measurable before trying to optimize it.
- Make cost visible and part of the design.

## Key Decision Choices
These are the most important decisions to be ready to explain.

### 1. Evaluator-First
I chose to build the evaluator before the generator.

Why:
- if the system cannot judge quality, the feedback loop is meaningless
- generation without evaluation produces output, but not improvement
- evaluation gives the system a stable target

### 2. Five-Dimension Quality Rubric
I chose to evaluate ads across five separate dimensions instead of using one holistic score.

Why:
- a single score is too vague to improve from
- decomposition makes weaknesses actionable
- it reduces the chance of halo scoring

### 3. Append-Only Ledger
I used a JSONL event ledger as the pipeline’s core state layer.

Why:
- it makes runs reproducible
- it preserves a full audit trail
- it supports replay and debugging
- it keeps the pipeline state inspectable and simple

### 4. Modular Boundaries
I separated generation, evaluation, iteration, output, and app concerns.

Why:
- each layer changes for different reasons
- it reduces coupling
- it makes the project easier to explain and maintain

### 5. Cost-Aware Routing
I designed the system around performance per token, not just output volume.

Why:
- not every ad deserves the same amount of model spend
- cheaper passes can handle initial generation and triage
- more expensive effort should be focused where improvement is likely

### 6. Product Wrapper Around the Pipeline
I built a full app layer instead of leaving the project as a CLI-only script.

Why:
- it makes the system usable by people, not just developers
- it adds sessions, campaigns, dashboards, and monitoring
- it turns a technical pipeline into a real internal tool

## What I Would Say In An Interview
If I had to summarize the project in a few sentences:

"I built an autonomous ad-ops pipeline for Varsity Tutors-style Meta ads. Instead of treating it like a prompt engineering project, I treated it like a systems problem. I started by defining how the system judges quality, broke that into five measurable dimensions, then built a modular pipeline for generation, evaluation, orchestration, and reporting. On top of that, I added an app layer with FastAPI, React, Celery, Redis, and Postgres so users could run sessions, organize campaigns, monitor progress, and inspect outputs."

## Strengths Of The Project
- Strong systems framing instead of a narrow LLM demo
- Clear module separation
- Evaluation is explicit and explainable
- Pipeline state is traceable through the ledger
- The app layer makes the project feel like a product
- Cost and quality are both visible in the architecture

## Honest Limitations
These are good to mention because they show maturity and self-awareness.

- Some iterative and self-healing behaviors were designed more fully than they are wired into the current runtime.
- Some live evaluator behavior depends on API-keyed runs, so not all validation is identical in every environment.
- There is some gap between architectural ambition and hot-path implementation in a few areas of the codebase.

## What I Would Improve Next
- fully wire the iterate layer into the main runtime path
- tighten CI and make test status and documentation always reflect current branch reality
- formalize the read model between ledger outputs and app summaries
- continue hardening production concerns like monitoring and operational consistency

## Quick Talking Points
- This project is about building a system that can judge and improve, not just generate.
- The evaluator came first because quality definition is the foundation.
- The ledger is one of the most important architectural choices because it enables reproducibility and debugging.
- The app layer matters because it turns the pipeline into a usable internal tool.
- The biggest trade-off was balancing architectural ambition with practical implementation time.

## One-Line Summary
Ad-Ops-Autopilot is a modular AI ad-generation system that combines LLM-driven creative generation, structured evaluation, reproducible pipeline state, and a product layer for managing sessions, campaigns, dashboards, and media workflows.
