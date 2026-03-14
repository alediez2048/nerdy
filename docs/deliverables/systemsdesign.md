# Ad-Ops-Autopilot — Systems Design & Architecture

**Author:** JAD
**Version:** 1.0
**Last Updated:** March 13, 2026

---

## 1. System Overview

Ad-Ops-Autopilot is an autonomous ad copy generation system for Facebook and Instagram. It generates, evaluates, and iteratively improves ad copy for Varsity Tutors (SAT test prep), tracking quality per dollar of API spend.

**North Star Metric:** Performance Per Token — how much quality improvement per dollar of Gemini API cost.

**Scope Progression:**
- **v1 (Full-Ad Pipeline):** Text copy + image via Nano Banana Pro, 5-dimension text eval + visual attribute checklist, text-image coherence, 50+ full ads
- **v2 (A/B Variant Engine + UGC Video):** Single-variable A/B variants, Nano Banana 2 cost tier, Veo UGC video, multi-format ad assembly (feed, Stories, Reels)
- **v3 (Autonomous Engine):** Self-healing loops, agentic orchestration, competitive intelligence, application layer (sessions, auth, curation)

---

## 2. Architectural Pillars

Nine principles that constrain every design decision (per prd.md):

| # | Pillar | What It Means in Practice |
|---|--------|---------------------------|
| 1 | **Decomposition Is the Architecture** | Quality = 5 independent dimensions, not a holistic score. Pipeline = generate + generate_image + evaluate + iterate + output + app. Ads = structural atoms, not opaque blobs. |
| 2 | **Prevention Over Detection Over Correction** | Shared semantic briefs prevent incoherence (don't detect it). Pareto selection prevents dimension collapse (don't constrain-prompt it). Floor constraints prevent bad ads from scoring well (don't fix them after). |
| 3 | **Every Token Is an Investment** | No API call without a purpose. Tiered routing puts expensive tokens where ROI is highest. Marginal analysis kills diminishing-returns cycles. |
| 4 | **The System Knows What It Doesn't Know** | Confidence scores on every evaluation. SPC detects evaluator drift. Escalation paths for unresolvable failures. |
| 5 | **State Is Sacred** | Append-only JSONL ledger — events are immutable. Identity-derived seeds — deterministic without position coupling. Snapshots capture full I/O for every API call. |
| 6 | **Learning Is Structural** | Reference-decompose-recombine turns "what works" into combinatorial atoms. Pattern databases make competitive intel queryable. Cross-campaign transfer shares patterns, isolates content. |
| 7 | **Visible Reasoning Is a First-Class Output** | Contrastive rationales on every score. Decision ledger records every system choice. Narrated pipeline replay for demos. |
| 8 | **The Reviewer Is a User, Too** | Submission is a product for the reviewer. Curated showcase, 7-min demo, ADR + narrative log. |
| 9 | **The Tool Is the Product** | Session management, auth, brief config, progress monitoring transform the pipeline into a product. |

---

## 3. High-Level Architecture

**Pipeline Flow (v1):**
```
Brief → Expand (R3-Q5) → Generate Copy (R2-Q1) → Generate Image (Nano Banana Pro) → Coherence Check
├─ Coherent → Evaluate Text (R3-Q6) + Evaluate Image (attribute checklist) → Above thresholds?
│   ├─ Yes → Add to published library (full ad: copy + image)
│   └─ No  → Identify weakest dimension → Contrastive rationale (R3-Q10) → Pareto regeneration (R1-Q5) → Re-evaluate
└─ Incoherent → Regenerate image with adjusted prompt (1 retry) → Re-check coherence
```

**Module Overview:**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AD-OPS-AUTOPILOT                                      │
│                                                                                 │
│  ┌──────────┐   ┌──────────────────┐   ┌──────────┐   ┌──────────┐   ┌──────┐│
│  │ generate │──▶│ generate_image    │──▶│ evaluate │──▶│ iterate  │──▶│output││
│  │ (copy)   │   │ (Nano Banana Pro)│   │ (text +  │   │ (regen,   │   │      ││
│  └────┬─────┘   └────────┬─────────┘   │  visual) │   │  ratchet) │   └──┬───┘│
│       │                 │             └────┬─────┘   └────┬─────┘      │     │
│       │                 │                  │              │             │     │
│       │         ┌───────┴──────────────────┴──────────────┴─────────────┘     │
│       │         │   Quality Gate: ≥7.0 text + ≥80% visual + ≥6 coherence      │
│       │         └────────────────────────────────────────────────────────────│
│       │                                                                       │
│  ┌────┴───────────────────────────────────────────────────────────────────┐  │
│  │  data/ (config, ledger, brand_kb, ref_ads, competitive/patterns.json)  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  app/ (FastAPI + React) — Sessions, auth, brief config, progress,      │   │
│  │  curation. Wraps pipeline for multi-session internal product (P1B).    │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  API Layer: Gemini Flash/Pro | Nano Banana Pro (v1) | Veo (v2)      │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Module Architecture

### 4.1 `generate/` — Ad Copy Generation

Transforms briefs into ad copy using reference-decompose-recombine.

```
generate/
├── __init__.py          — Package exports
├── brief_expansion.py   — LLM-grounded brief expansion (P1-01)
├── ad_generator.py      — Core generation with structural atoms (P1-02)
├── brand_voice.py       — Audience-specific brand voice profiles (P1-03)
├── model_router.py      — Tiered Flash/Pro selection (P1-06)
├── seeds.py             — Identity-derived seed chain (P0-03) ✅
└── compliance.py        — Tiered 3-layer compliance filter (P2-06)
```

**Brief Expansion Flow (P1-01):**
```
Raw Brief                    Expanded Brief
┌──────────────────┐        ┌──────────────────────────────────┐
│ audience: parents │        │ audience: parents (35-55)        │
│ product: SAT prep │───LLM─▶│ pain: college admissions anxiety  │
│ goal: conversion  │        │ value: 200+ point improvement     │
│ tone: empowering  │        │ proof: 10,000+ students served   │
└──────────────────┘        │ hook_candidates: [question, stat] │
                             │ cta_candidates: [trial, demo]    │
                             │ brand_profile: parent-facing      │
                             └──────────────────────────────────┘
```

The expansion is grounded — it fills in audience demographics, pain points, and proof points from the brand knowledge base, not hallucinated. P1-01 injects competitive landscape context from `query_patterns(audience, tags)` (P0-10) for differentiation guidance.

**Reference-Decompose-Recombine (P1-02):**
```
Reference Ads ──▶ Decompose into Structural Atoms ──▶ Atom Library
                                                          │
Expanded Brief ──▶ Select Atoms ──▶ Recombine ──▶ Generated Ad
                   (hook + body +                  (primary_text,
                    CTA + tone)                     headline,
                                                    description,
                                                    cta_button)
```

Structural atoms:
| Atom | Options |
|------|---------|
| Hook type | question, stat, story, fear |
| Body pattern | problem-agitate-solution, testimonial-benefit-CTA, stat-context-offer |
| CTA style | urgent, soft, trial-based |
| Tone register | parent-authoritative, student-relatable |

Each generated ad is a specific combination of atoms — making "what worked" learnable and transferable.

**Model Routing (P1-06):**
```
                     ┌─── Score ≥ 7.0 ────▶ PUBLISH (no regen needed)
                     │
Ad Score ────────────┼─── Score 5.5-7.0 ──▶ ESCALATE to Gemini Pro
                     │                       (improvable range)
                     │
                     └─── Score < 5.5 ────▶ DISCARD (cheap exit)
```

Flash handles ~80% of generation. Pro is reserved for the 5.5-7.0 "improvable range" where expensive tokens have the highest marginal ROI.

---

### 4.2 `evaluate/` — LLM-as-Judge Evaluation

Scores every ad across 5 independent text dimensions using chain-of-thought prompting. Image evaluation (attribute checklist, coherence) lives in `generate_image/` (P1-15, P1-16).

```
evaluate/
├── __init__.py          — Package exports
├── evaluator.py         — 5-step CoT evaluator core (P1-04)
├── dimensions.py        — Dimension definitions, weights, floors (P1-05)
├── calibration.py       — Cold-start calibration against reference ads (P0-06)
├── golden_set.py        — Regression tests against known-quality ads (P0-07)
└── drift_detection.py   — SPC control charts + canary injection (P2-04)
```

**5-Step Chain-of-Thought Evaluation (P1-04):**
```
Step 1: Read the ad (full text)
   │
Step 2: Identify structural elements
   │     hook type, value proposition, CTA, emotional angle
   │
Step 3: Compare against calibration examples
   │     "This CTA is stronger than ref_003 (score 6.0)
   │      but weaker than ref_007 (score 9.0)"
   │
Step 4: Score each dimension with contrastive rationale
   │     "Clarity: 8.0 — single clear message. A 10.0 version
   │      would frontload the stat as the first 5 words."
   │
Step 5: Flag low-confidence dimensions
         confidence < 7 → flag for potential re-evaluation
```

**Evaluation Output Schema:**
```json
{
  "ad_id": "ad_001_cycle_1",
  "scores": {
    "clarity":              {"score": 8.0, "rationale": "...", "contrastive": "...", "confidence": 9},
    "value_proposition":    {"score": 8.5, "rationale": "...", "contrastive": "...", "confidence": 8},
    "cta":                  {"score": 9.0, "rationale": "...", "contrastive": "...", "confidence": 9},
    "brand_voice":          {"score": 7.5, "rationale": "...", "contrastive": "...", "confidence": 7},
    "emotional_resonance":  {"score": 7.0, "rationale": "...", "contrastive": "...", "confidence": 7}
  },
  "aggregate_score": 8.1,
  "campaign_goal": "conversion",
  "weights_used": {"clarity": 0.25, "value_proposition": 0.25, "cta": 0.30, "brand_voice": 0.10, "emotional_resonance": 0.10},
  "meets_threshold": true,
  "effective_threshold": 7.0,
  "weakest_dimension": "emotional_resonance",
  "compliance": {"passes": true, "violations": []}
}
```

**Campaign-Goal-Adaptive Weights (P1-05):**

| Dimension | Awareness | Conversion |
|-----------|-----------|------------|
| Clarity | 25% | 25% |
| Value Proposition | 20% | 25% |
| CTA | 10% | 30% |
| Brand Voice | 20% | 10% |
| Emotional Resonance | 25% | 10% |

Floor constraints (apply to both profiles):
- Clarity ≥ 6.0 — a confusing ad is never publishable
- Brand Voice ≥ 5.0 — must sound at least recognizably like Varsity Tutors

If any floor is breached, the ad fails regardless of aggregate score.

**Cold-Start Calibration (P0-06):**
```
                ┌─────────────────────────────────┐
Competitor Ads  │  Run evaluator on 20-30 known   │  Calibrated
(Meta Ad Lib) ──▶  ads BEFORE generating anything  ├──▶ Evaluator
Reference Ads   │  Verify: best score 8+, worst 4- │
                └─────────────────────────────────┘
```

Calibrate the evaluator first, then trust it to score generated ads. This prevents the garbage-in-garbage-out cycle where the evaluator calibrates to its own system's mediocre output.

**Evaluator Drift Detection — SPC (P2-04):**
```
Batch scores ──▶ Control chart (rolling mean ± 2σ)
                    │
                    ├── Within limits ──▶ Continue (no action)
                    │
                    └── Breach ──▶ Inject 3-5 canary ads
                                      │
                                      ├── Canary scores normal ──▶ Real quality shift
                                      │                            (ratchet adjusts)
                                      │
                                      └── Canary scores drifted ──▶ Evaluator drift
                                                                     (recalibrate)
```

---

### 4.3 `iterate/` — Feedback Loop & Quality Ratchet

Orchestrates the generate-evaluate-improve cycle with intelligent failure handling.

```
iterate/
├── __init__.py          — Package exports
├── feedback_loop.py     — Core generate→evaluate→regen cycle (P1-07/08)
├── pareto_selection.py  — Multi-variant Pareto-optimal selection (P1-07)
├── brief_mutation.py    — Diagnose + mutate failing briefs (P1-08)
├── quality_ratchet.py   — Rolling high-water mark threshold (P1-10)
├── context_distiller.py — Compact iteration summaries (P1-09)
├── snapshots.py         — API call I/O capture (P0-03) ✅
├── token_tracker.py     — Per-call cost attribution (P1-11)
└── cache.py             — Result-level cache with version TTL (P1-12)
```

**Core Feedback Loop (v1 — Copy + Image):**
```
                 ┌──────────────────────────────────────────────────────────────┐
                 │                    FEEDBACK LOOP (v1)                         │
                 │                                                               │
  Brief ──▶ EXPAND ──▶ GENERATE COPY ──▶ GENERATE IMAGE (3 variants) ──▶         │
  (shared semantic brief)     (Flash)      (Nano Banana Pro)                      │
                                                                  │              │
                                    ┌── Coherence Check ──────────┤              │
                                    │   (copy + image ≥ 6)        │              │
                                    │   Pass? ──▶ EVALUATE       │              │
                                    │   Fail? ──▶ Regen image    │              │
                                    │            (1 retry)       │              │
                                    └────────────────────────────┘              │
                                                          │                     │
                                    ┌───────────────────── │ ◄── Text + Visual   │
                                    │                     │     scores          │
                          ┌─────────┼─────────────────────┼──────────┐           │
                          │ ≥ 7.0  │ 5.5-7.0             │ < 5.5   │           │
                          │ PUBLISH│ REGEN (Pareto 3-5)   │ DISCARD │           │
                          │        │ Cycle ≤ 2? loop back │         │           │
                          │        │ Cycle 3? MUTATE brief│         │           │
                          │        │ Still fail? ESCALATE  │         │           │
                          └────────┴──────────────────────┴─────────┘           │
                 └──────────────────────────────────────────────────────────────┘
```

**Pareto-Optimal Selection (P1-07):**

Instead of improving one dimension at a time (whack-a-mole), generate 3-5 variants and select via Pareto dominance:

```
Variant A: Clarity=8 VP=7 CTA=6 BV=7 ER=8   ← Pareto-efficient
Variant B: Clarity=7 VP=8 CTA=7 BV=6 ER=7   ← Pareto-efficient
Variant C: Clarity=6 VP=6 CTA=8 BV=7 ER=6   ← Dominated by A (A ≥ C on all dims except CTA)
Variant D: Clarity=7 VP=7 CTA=7 BV=7 ER=7   ← Dominated by A
Variant E: Clarity=8 VP=7 CTA=7 BV=7 ER=8   ← Dominates A (equal or better on all)

Selection: Variant E (dominates A, B)
```

If multiple non-dominated variants exist, break ties with weighted aggregate score.

**Brief Mutation (P1-08):**
```
2 regen failures ──▶ Diagnose weakest dimension
                          │
                ┌─────────┼───────────┬──────────────┐
                │         │           │              │
           Brand Voice  Clarity    CTA          Value Prop
           low          low        low           low
                │         │           │              │
           Inject       Simplify   Make offer    Add specific
           stronger     value      more          outcomes and
           brand        prop       concrete      proof points
           context                                    │
                │         │           │              │
                └─────────┴───────────┴──────────────┘
                          │
                    Mutated Brief ──▶ One more generation cycle
                          │
                    Still fails? ──▶ ESCALATE with diagnostics
                                     (scores per cycle, weakest
                                      dims, all prompts used)
```

**Quality Ratchet (P1-10):**
```
effective_threshold = max(7.0, rolling_5batch_avg - 0.5)

Example progression:
  Batch 1: avg 7.2 → threshold = 7.0 (floor)
  Batch 2: avg 7.5 → threshold = 7.0 (floor, need 5 batches)
  Batch 3: avg 7.8 → threshold = 7.0 (floor)
  Batch 4: avg 8.0 → threshold = 7.0 (floor)
  Batch 5: avg 8.1 → threshold = max(7.0, 7.72-0.5) = 7.22
  Batch 6: avg 8.3 → threshold = max(7.0, 7.92-0.5) = 7.42
  ...
  Batch N: avg 9.0 → threshold ~8.0 (system refuses regression)
```

The ratchet remembers how well the system has performed and refuses to accept regression. The 0.5 buffer prevents one exceptional batch from making the threshold unreachable.

**Distilled Context Objects (P1-09):**
```
Raw iteration history          Distilled context
┌────────────────────┐        ┌────────────────────────────────┐
│ Cycle 1: 5.2       │        │ Best: 6.4 (Cycle 4)           │
│ Cycle 2: 5.8       │───LLM─▶│ Fix: Value Prop (5.8) — too   │
│ Cycle 3: 6.1       │        │   generic, needs specifics     │
│ Cycle 4: 6.4       │        │ Keep: Brand Voice (7.2)        │
│ (contradictory     │        │ Avoid: superlatives, vague     │
│  feedback across   │        └────────────────────────────────┘
│  cycles)           │        Compact, non-contradictory,
└────────────────────┘        constant token cost per cycle
```

---

### 4.4 `generate_image/` — Nano Banana Pro Image Generation (v1)

Generates brand-consistent images from the shared semantic brief. 3 variants per ad (anchor, tone shift, composition shift). Pareto selection by composite score: (attribute_pass_pct × 0.4) + (coherence_avg × 0.6).

```
generate_image/
├── __init__.py          — Package exports
├── visual_spec.py       — Extract visual spec from expanded brief (subject, setting, palette, tone)
├── image_generator.py   — Nano Banana Pro API, 3 variants per ad (P1-14)
├── attribute_eval.py    — Multimodal attribute checklist (P1-15)
├── coherence.py         — Text-image coherence verification, 4 dimensions (P1-16)
└── regen_loop.py        — Targeted image regen when all 3 fail (P1-17)
```

**Attribute Checklist (P1-15):** Age-appropriate, diversity, warm lighting, brand colors, no competitor branding, setting coherence, emotional match, no AI artifacts, aspect ratio. All Required must pass; 70%+ Recommended.

**Targeted Regen (P1-17):** All 3 variants fail → diagnose weakest attribute, append diagnostic, generate 2 regen variants. Best fails coherence → append fix_suggestion, generate 1 regen. Max 5 images/ad. Exhausted → flag "image-blocked."

---

### 4.5 `generate_video/` — Veo UGC Video Generation (v2)

Generates 6-sec UGC-style video from expanded brief. 2 variants per ad. Graceful degradation: video fails → publish copy + image only.

```
generate_video/
├── __init__.py          — Package exports
├── video_spec.py        — Extract video spec from brief (scene, pacing, audio, mood)
├── video_generator.py  — Veo 3.1 Fast API (P3-07)
├── attribute_eval.py   — Video attribute checklist (P3-08)
└── coherence.py        — Script-video coherence (P3-09)
```

---

### 4.6 `app/` — Application Layer (P1B)

Wraps the pipeline in a multi-session internal product. Session = one pipeline run (immutable). Google SSO (@nerdy.com). Curation layer on top of immutable generation.

```
app/
├── api/                 — FastAPI routes (sessions, auth, progress SSE)
├── models/              — SQLAlchemy (users, sessions, curated_sets)
├── workers/             — Celery tasks (pipeline execution, progress reporting)
└── frontend/            — React (session list, brief config, progress view, dashboard shell)
```

**Session Model (R5-Q1):** Immutable after completion. One session = one pipeline run with specific config. Results never edited; create new session to re-run.

**Curation Layer (R5-Q6):** Select/deselect ads, reorder, annotate, light edit with diff tracking. Dashboard metrics always reflect original pipeline output — never curated edits.

---

### 4.7 `output/` — Export & Visualization

```
output/
├── __init__.py              — Package exports
├── export_dashboard.py      — Ledger → dashboard_data.json (P5-01)
├── export.py                — Ad library export (JSON/CSV) (P5-10)
├── trends.py                — Quality trend visualization (P5-03)
├── replay.py                — Narrated pipeline replay (P4-07)
└── nerdy_adgen_dashboard.html — Single-file 8-panel HTML dashboard
```

**8-Panel Dashboard (P5-01–P5-06):** Pipeline Summary, Iteration Cycles, Quality Trends, Dimension Deep-Dive (correlation matrix), Ad Library (filterable with rationales), Token Economics, System Health (SPC, confidence, escalation), Competitive Intelligence. Data source: `output/dashboard_data.json` from `export_dashboard.py`.

**Quality Trend Visualization (P5-03):**
```
Score
10 ─┤
 9 ─┤                              ●●●●●
 8 ─┤                    ●●●●●●●●●
 7 ─┤─ ─ ─ ─ ─●●●●●●●●─ ─ ─ ─ ─ ─ ─ ─ ─ ← threshold (ratcheting up)
 6 ─┤  ●●●●●●
 5 ─┤●●
    └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──▶ Batch
      1  2  3  4  5  6  7  8  9  10 11
```

Plots: per-dimension trends, aggregate score, effective threshold, token cost per publishable ad.

---

### 4.8 `data/` — Shared State & Configuration

```
data/
├── config.yaml                  — Tunable parameters (thresholds, batch size, API config)
├── ledger.jsonl                 — Append-only event log (generation, evaluation, decisions)
├── brand_knowledge.json         — Brand voice profiles, audience personas, proof points (P0-04)
├── reference_ads.json           — Decomposed reference ads with structural atoms (P0-05)
├── competitive/
│   └── patterns.json            — Competitor pattern records from Meta Ad Library (P0-09)
├── golden_set.json              — Calibration ads with ground-truth scores (P0-07)
└── cache/                       — Result-level cache with version TTL (P1-12)
```

**Competitive Pattern Database (P0-09, P0-10):** Claude in Chrome extracts structured records (hook_type, value_prop_structure, cta_style, emotional_register, visual_patterns) from 6 competitors. `query_patterns(audience, tags)` feeds brief expansion and generation.

**Ledger Schema:**

Every system event is a single JSONL line:
```json
{
  "timestamp": "2026-03-13T14:30:00Z",
  "event_type": "evaluation",
  "ad_id": "ad_001_cycle_2",
  "brief_id": "brief_001",
  "cycle_number": 2,
  "action": "evaluate_ad",
  "inputs": {"ad_text": "...", "campaign_goal": "conversion"},
  "outputs": {"scores": {"clarity": 8.0, "...": "..."}, "aggregate": 7.8},
  "scores": {"clarity": 8.0, "value_proposition": 7.5, "cta": 8.5, "brand_voice": 7.0, "emotional_resonance": 6.5},
  "tokens_consumed": 1240,
  "model_used": "gemini-2.0-flash",
  "seed": 2847291045,
  "checkpoint_id": "ckpt_001"
}
```

Append-only = immutable audit trail. Corrections write a new event; they never overwrite.

**Config Cascade:**
```
Environment variable (GLOBAL_SEED, GEMINI_API_KEY)
        │  overrides
        ▼
data/config.yaml (tunable parameters)
        │  overrides
        ▼
Hardcoded defaults in code
```

---

## 5. Data Flow: Full Pipeline Trace (v1)

A single ad's journey through the system, from brief to published full ad (copy + image):

```
1. INTAKE
   Brief: {audience: "parents", product: "SAT prep", goal: "conversion"}
                    │
2. EXPAND (generate/brief_expansion.py)
   Load brand KB + competitive patterns (query_patterns) → LLM expansion
   → Grounded brief with demographics, pain points, proof points, hook/CTA candidates
                    │
3. SEED (generate/seeds.py)
   seed = SHA256("nerdy-p0-default:brief_001:0")[:8] → 0xA3F2B1C9
                    │
4. GENERATE COPY (generate/ad_generator.py)
   Select structural atoms → Recombine with expanded brief + brand voice
   → Gemini Flash → Ad copy (primary_text, headline, description, cta_button)
   → Ledger event: {event_type: "generation", tokens: 850, model: "flash"}
                    │
5. GENERATE IMAGE (generate_image/)
   Extract visual spec from brief → Nano Banana Pro → 3 variants (anchor, tone, composition)
   → Attribute checklist + coherence check → Pareto select best
   → Ledger events: image generation, attribute eval, coherence scores
                    │
6. EVALUATE (evaluate/evaluator.py + generate_image/attribute_eval.py)
   Text: 5-step CoT → 5 dimensions + contrastive rationales
   Image: attribute pass %, coherence score
   → Check: text ≥ 7.0, visual ≥ 80%, coherence ≥ 6
   → Ledger event: {event_type: "evaluation", scores: {...}, tokens: 1240}
                    │
7. ROUTE (iterate/feedback_loop.py)
   Score = 6.3 → In improvable range (5.5-7.0)
   → Escalate to regeneration cycle (Pareto 3-5 variants)
                    │
8. REGENERATE — CYCLE 1
   Distill context → Generate 5 Pareto copy variants (Gemini Pro)
   → Re-evaluate all 5 → Select Pareto-optimal
   → Best variant: 7.4 — passes threshold and floor constraints
                    │
9. PUBLISH (full ad: copy + winning image)
   → Ad added to published library
   → Ledger event: {event_type: "decision", action: "publish", aggregate: 7.4}
   → Quality ratchet updated
   → Token attribution: text tokens + image cost (~$0.13×3 variants) per ad
```

---

## 6. Failure Handling Architecture

Every failure mode has a designed response — no unhandled cases.

### 6.1 Ad Quality Failures

| Failure | Detection | Response | Token Budget |
|---------|-----------|----------|-------------|
| Score < 5.5 | Initial evaluation | Discard immediately (cheap exit) | ~2,100 tokens (1 gen + 1 eval) |
| Score 5.5-7.0 after cycle 1 | Evaluation | Pareto regen with Pro model | +~23,000 tokens (5 gen + 5 eval) |
| Score 5.5-7.0 after cycle 2 | Evaluation | Mutate brief, one more cycle | +~23,000 tokens |
| Still failing after cycle 3 | Evaluation | Escalate with full diagnostics | 0 additional tokens |

Max token spend per ad: ~71,000 tokens (worst case, 3 full Pareto cycles). Expected: ~25,000 (most ads pass by cycle 2).

### 6.2 Evaluator Failures

| Failure | Detection | Response |
|---------|-----------|----------|
| Score inflation/deflation | SPC control chart breach | Inject canary ads to diagnose |
| Canary scores drifted | Canary evaluation | Recalibrate with golden set |
| Halo effect (dims correlated) | Correlation analysis (P2-02) | Redesign evaluation prompts |
| Low confidence | Confidence score < 5 | Flag for optional human review |

### 6.3 System Failures

| Failure | Detection | Response |
|---------|-----------|----------|
| API rate limit | HTTP 429 | Exponential backoff, respect `api_delay_seconds` |
| API error | HTTP 5xx | Retry up to `retry_max_attempts` (3) |
| Pipeline crash mid-batch | Checkpoint-resume (P0-08) | `--resume` flag skips completed work |
| Data corruption | Ledger validation | Append-only = no overwrites; validate on read |

### 6.4 Checkpoint-Resume (P0-08)

Every API call writes a checkpoint before and after:
```
BEFORE: {checkpoint_id: "ckpt_001", status: "started", ad_id: "ad_047", stage: "generation"}
API CALL: ...
AFTER:  {checkpoint_id: "ckpt_001", status: "completed", result_hash: "a3f2..."}
```

On `--resume`, the pipeline:
1. Reads ledger for all completed checkpoint IDs
2. Skips any step already completed
3. Resumes from the first incomplete checkpoint

No work is repeated. No state is lost.

---

## 7. Quality Assurance Architecture

### 7.1 Test Strategy

```
tests/
├── test_evaluation/
│   ├── test_golden_set.py       — Regression against known-quality ads (P0-07)
│   ├── test_inversion.py        — Degrade 1 dim, verify only that score drops (P2-01)
│   ├── test_correlation.py      — Verify dims are independent, not halo (P2-02)
│   └── test_adversarial.py      — Boundary cases: off-brand, no CTA, etc. (P2-03)
├── test_generation/
│   ├── test_brief_expansion.py  — Expansion produces valid structured output
│   ├── test_ad_generator.py     — Generated ads have all required fields
│   └── test_compliance.py       — Compliance filter catches violations (P2-06)
├── test_pipeline/
│   ├── test_scaffold.py         — Package imports work ✅
│   ├── test_seeds.py            — Deterministic seed chain ✅ (10 tests)
│   ├── test_feedback_loop.py    — Full cycle: generate→evaluate→regen
│   └── test_checkpoint.py       — Resume from interruption (P2-07)
├── test_image/                  — Image pipeline (v1)
│   └── test_coherence.py        — Text-image coherence verification
└── test_data/
    └── test_ledger.py           — Append-only, schema validation
```

**Test Types:**

| Type | What It Proves | Example |
|------|----------------|---------|
| **Golden set regression** | Evaluator accuracy stable over time | "Reference ad_007 still scores 8.0 ± 0.5" |
| **Inversion** | Dimensions are independently measurable | "Degrade CTA only → only CTA score drops" |
| **Correlation** | No halo effect between dimensions | "Clarity-VP correlation < 0.7" |
| **Adversarial** | Evaluator catches obvious failures | "Wrong-brand ad scores < 4.0 on Brand Voice" |
| **Integration** | Pipeline stages compose correctly | "Brief → ad → score → regen → improved score" |
| **Determinism** | Same seeds = same output | "get_ad_seed('global', 'brief_001', 0) is stable" |

### 7.2 Compliance Filter (P2-06)

Three-layer tiered filter, applied before publishing:

```
Layer 1: HARD RULES (regex/keyword)
  - No competitor names in ad copy
  - No guaranteed outcomes ("guaranteed 1500 score")
  - No PII patterns

Layer 2: POLICY CHECKS (LLM)
  - No misleading claims
  - CTA matches funnel stage
  - Tone appropriate for audience

Layer 3: BRAND SAFETY (LLM)
  - Nothing that could embarrass Varsity Tutors
  - No cultural insensitivity
  - No urgency that crosses into fear-mongering
```

Each layer is independently testable. Layer 1 is free (regex). Layers 2-3 cost evaluation tokens but only run on ads that pass Layer 1.

---

## 8. Model Strategy

### 8.1 Model Selection Matrix

| Task | Model | Cost Tier | Rationale |
|------|-------|-----------|-----------|
| Brief expansion | Gemini Flash | $ | Cheap, structured output, high ROI |
| First-draft generation | Gemini Flash | $ | 80% of ads are triaged here |
| Initial evaluation | Gemini Flash | $ | Good enough for triage scoring |
| Improvable-range regen | Gemini Pro | $$$ | Quality tokens on borderline ads (5.5-7.0) |
| Context distillation | Gemini Flash | $ | Small prompt, structured summary |
| Compliance check | Gemini Flash | $ | Binary decisions, low complexity |
| Image generation (v1) | Nano Banana Pro (Gemini 3 Pro Image) | $$ | ~$0.13/image, 3 variants per ad |
| Image coherence eval | Gemini Flash (multimodal) | $ | Pass image + copy → coherence score |
| Video generation (v2) | Veo 3.1 Fast | $$$ | ~$0.90/6-sec video, 2 variants per ad |

### 8.2 Cost Projection (50 ads, v1 Copy + Image)

```
Text tokens (same as before):
  First pass + regen cycles: ~392,000 tokens
  Cost per publishable ad (text): ~8,340 tokens

Image cost (Nano Banana Pro, 3 variants per ad):
  50 ads × 3 variants = 150 images × ~$0.13 = ~$19.50
  ~15% regen (2 extra each) = +~$4
  Total image: ~$24 for 50 ads

Combined (50 ads, ~47 published):
  Text: ~392K tokens (~$1–2 on free tier)
  Image: ~$24
  Cost per publishable full ad: ~$0.50 (text + image)
```

---

## 9. Reproducibility Architecture

### 9.1 Seed Chain

```
Global seed: "nerdy-p0-default" (config.yaml, overridable via GLOBAL_SEED env var)
     │
Ad seed = SHA256(global_seed + ":" + brief_id + ":" + cycle_number)[:8]
     │
     ├── "nerdy-p0-default:brief_001:0" → 0xA3F2B1C9  (first attempt)
     ├── "nerdy-p0-default:brief_001:1" → 0x7D4E92A1  (regen cycle 1)
     └── "nerdy-p0-default:brief_001:2" → 0x1F8C6B37  (regen cycle 2)
```

Properties:
- **Deterministic:** Same inputs → same seed, always
- **Identity-derived:** brief_002's seed is independent of brief_001's existence
- **Order-independent:** Adding/removing briefs doesn't affect other seeds

### 9.2 I/O Snapshots

Every API call is captured as a snapshot:
```json
{
  "prompt": "Generate an ad for...",
  "response": "Your child's SAT score...",
  "model_version": "gemini-2.0-flash",
  "timestamp": "2026-03-13T14:30:00Z",
  "parameters": {"temperature": 0.7, "max_tokens": 500},
  "seed": 2751234567
}
```

Snapshots embed into ledger events, enabling full forensic replay: given the same seed and prompt, reproduce the exact output.

---

## 10. Scaling: v1 → v2 → v3

### v1: Full-Ad Pipeline (Copy + Image) — P1
```
Brief → Expand → Generate Copy → Generate Image (3 variants) → Coherence Check
    → Evaluate (5 text dims + visual attribute checklist) → Iterate → Publish
```

Shared semantic brief (R1-Q10) prevents text-image incoherence. 10-attribute checklist (age, lighting, diversity, brand, artifacts, etc.). Pareto selection: composite = (attribute_pass_pct × 0.4) + (coherence_avg × 0.6).

### v2: A/B Variant Engine + UGC Video — P3
```
v1 pipeline +
  Single-variable A/B variants (copy + image)
  Nano Banana 2 cost tier for variant volume
  Veo 3.1 Fast for 6-sec UGC video (2 variants per ad)
  Multi-format output: feed (1:1, 4:5), Stories/Reels (9:16)
```

Video: 10-attribute checklist (hook timing, UGC authenticity, pacing, brand safety). Script-video coherence (4 dimensions). Graceful degradation: video fails → publish copy + image only.

### v3: Autonomous Engine — P4
```
┌──────────────────────────────────────────────────────────┐
│                  AGENTIC ORCHESTRATION                    │
│                                                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │ Researcher│  │  Writer   │  │  Editor   │           │
│  │  Agent    │  │  Agent    │  │  Agent    │           │
│  │           │  │           │  │           │           │
│  │ Comp intel│  │ Generate  │  │ Evaluate  │           │
│  │ Pattern   │  │ from atoms│  │ Score     │           │
│  │ extraction│  │ Brand     │  │ Select    │           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │              │              │                   │
│        └──────────────┼──────────────┘                   │
│                       │                                  │
│              Self-Healing Loop                           │
│              ├── Quality drop? → Diagnose → Auto-fix     │
│              ├── Drift detected? → Recalibrate           │
│              └── Plateau? → Explore new patterns          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │         Confidence-Gated Autonomy               │     │
│  │  High confidence (>7): fully autonomous         │     │
│  │  Medium (5-7): proceed, flag for review         │     │
│  │  Low (<5): pause, require human sign-off        │     │
│  └─────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

Linear pipeline (not DAG) with error boundaries between agents. Each agent has a clear input/output contract and can fail independently.

---

## 11. Configuration Reference

All tunable parameters in `data/config.yaml`:

| Parameter | Default | What It Controls |
|-----------|---------|-----------------|
| `quality_threshold` | 7.0 | Absolute minimum publish score |
| `clarity_floor` | 6.0 | Hard minimum for Clarity dimension |
| `brand_voice_floor` | 5.0 | Hard minimum for Brand Voice dimension |
| `batch_size` | 10 | Ads per processing batch |
| `max_regeneration_cycles` | 3 | Hard cap on regen attempts |
| `pareto_variants` | 5 | Variants per regen cycle |
| `ratchet_window` | 5 | Batches in rolling average |
| `ratchet_buffer` | 0.5 | Buffer below rolling average |
| `improvable_range` | [5.5, 7.0] | Score range that triggers Pro model |
| `exploration_plateau_threshold` | 0.1 | Score improvement below which = plateau |
| `exploration_plateau_batches` | 3 | Consecutive plateau batches before exploring |
| `global_seed` | "nerdy-p0-default" | Root seed for reproducibility |
| `api_delay_seconds` | 1.5 | Delay between API calls (rate limiting) |
| `retry_max_attempts` | 3 | API call retry ceiling |

---

## 12. Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.10+ | Ecosystem, Gemini SDK, data science libs |
| LLM | Gemini API (Flash + Pro) | Free tier, strong creative writing, structured output |
| Image (v1) | Nano Banana Pro (Gemini 3 Pro Image) | ~$0.13/image, 4K, text rendering |
| Video (v2) | Veo 3.1 Fast | Same ecosystem, 6-sec UGC video |
| Data | JSONL (ledger), YAML (config), JSON (knowledge bases) | Human-readable, no DB for pipeline |
| App layer | FastAPI + React + PostgreSQL + Celery + Redis | Sessions, auth, progress, curation (P1B) |
| Visualization | matplotlib, Chart.js (dashboard) | Quality trends, 8-panel HTML dashboard |
| Token counting | tiktoken | Accurate token budget tracking |
| Config | python-dotenv + pyyaml | Env vars for secrets, YAML for tunable params |
| Testing | pytest | Standard, good fixture support |
| Linting | ruff | Fast, opinionated, catches real issues |
| Data analysis | pandas | Ledger queries, correlation analysis, trend computation |

---

## 13. Phased Delivery Map (80 Tickets)

```
PHASE 0 — Foundation & Calibration (P0-01 → P0-10)
├── ✅ P0-01: Scaffolding
├── ✅ P0-02: Decision ledger
├── ✅ P0-03: Seed chain + snapshots
├── ⏳ P0-04: Brand knowledge base
├── ⏳ P0-05: Reference ad collection
├── ⏳ P0-06: Evaluator calibration
├── ⏳ P0-07: Golden set tests
├── ⏳ P0-08: Checkpoint-resume
├── ⏳ P0-09: Competitive pattern database (Claude in Chrome)
└── ⏳ P0-10: Competitive pattern query interface

PHASE 1 — Full-Ad Pipeline v1 (P1-01 → P1-20)
├── Brief expansion (with competitive context), generator, brand voice
├── CoT evaluator, adaptive weights, model routing
├── Pareto regen, brief mutation, context distillation, quality ratchet
├── Token tracking, cache, batch processor
├── Nano Banana Pro: visual spec, 3 variants, attribute eval, coherence (P1-14–P1-17)
├── Full ad assembly, image cost tracking (P1-18–P1-19)
└── 50+ full ad generation run (P1-20)

PHASE 1B — Application Layer (PA-01 → PA-13)
├── FastAPI backend, PostgreSQL, Celery + Redis
├── Google SSO, session CRUD, brief config form
├── Session list UI, progress reporting, "Watch Live" SSE
├── Dashboard integration, curation layer, share link
└── Docker Compose production deployment

PHASE 2 — Testing & Validation (P2-01 → P2-07)
├── Inversion tests, correlation analysis
├── Adversarial boundary tests, SPC
├── Compliance filter, e2e integration
└── 15+ tests total

PHASE 3 — A/B Variant Engine + UGC Video v2 (P3-01 → P3-13)
├── Nano Banana 2 cost tier, single-variable A/B variants
├── Image style transfer, multi-aspect-ratio batch
├── Veo integration, video spec, attribute eval, coherence (P3-07–P3-10)
├── Three-format assembly, video cost tracking
└── 10-ad video pilot run (P3-13)

PHASE 4 — Autonomous Engine v3 (P4-01 → P4-07)
├── Agentic orchestration, self-healing
├── Competitive intelligence (automated refresh, trends)
├── Cross-campaign transfer, explore/exploit
└── Narrated pipeline replay

PHASE 5 — Dashboard, Docs & Submission (P5-01 → P5-11)
├── export_dashboard.py, 8-panel HTML dashboard (P5-01–P5-06)
├── Decision log, technical writeup, demo video (P5-07–P5-09)
└── Ad library export, README (P5-10–P5-11)
```

---

*This document describes the target architecture. Implementation status is tracked in [DEVLOG.md](../development/DEVLOG.md). Design rationale is documented in [decisionlog.md](decisionlog.md).*
