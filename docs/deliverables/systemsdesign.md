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
| 1 | **Decomposition Is the Architecture** | Quality = 5 independent dimensions, not a holistic score. Pipeline = 4 modules, not a monolith. Ads = structural atoms, not opaque blobs. |
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

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AD-OPS-AUTOPILOT                             │
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │          │    │          │    │          │    │          │     │
│  │ generate │───▶│ evaluate │───▶│ iterate  │───▶│  output  │     │
│  │          │    │          │    │          │    │          │     │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘     │
│       │               │               │               │           │
│       │         ┌─────┴──────────────┐│               │           │
│       │         │   Quality Gate     ││               │           │
│       │         │  ≥ 7.0 → publish   ││               │           │
│       │         │ 5.5-7.0 → regen   ││               │           │
│       │         │  < 5.5 → discard   ││               │           │
│       │         └────────────────────┘│               │           │
│       │                               │               │           │
│  ┌────┴───────────────────────────────┴───────────────┴────────┐  │
│  │                     data/ (shared state)                     │  │
│  │  config.yaml │ ledger.jsonl │ brand_kb │ ref_ads │ cache    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Gemini API Layer                           │  │
│  │  Flash (default) ◄──── Model Router ────► Pro (escalation)   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
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

The expansion is grounded — it fills in audience demographics, pain points, and proof points from the brand knowledge base, not hallucinated.

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

Scores every ad across 5 independent dimensions using chain-of-thought prompting.

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

**Core Feedback Loop:**
```
                 ┌──────────────────────────────────────────────┐
                 │             FEEDBACK LOOP                    │
                 │                                              │
  Brief ──▶ EXPAND ──▶ GENERATE (Flash) ──▶ EVALUATE           │
                                               │                │
                              ┌─────────────── │ ◄── Score      │
                              │                │                │
                    ┌─────────┼────────────────┼──────────┐     │
                    │ ≥ 7.0   │ 5.5-7.0        │ < 5.5    │     │
                    │ PUBLISH │ REGEN           │ DISCARD  │     │
                    │         │                 │          │     │
                    │    ┌────┴────┐            │          │     │
                    │    │ Pareto  │            │          │     │
                    │    │ 3-5     │            │          │     │
                    │    │ variants│            │          │     │
                    │    └────┬────┘            │          │     │
                    │         │                 │          │     │
                    │    EVALUATE ALL           │          │     │
                    │         │                 │          │     │
                    │    Select Pareto-optimal  │          │     │
                    │         │                 │          │     │
                    │    Cycle ≤ 2?             │          │     │
                    │    ├── Yes ──▶ loop back  │          │     │
                    │    └── No  ──▶ MUTATE brief          │     │
                    │              └── Cycle 3 fail?       │     │
                    │                  └── ESCALATE        │     │
                    └─────────────────────────────┘        │     │
                                                           │     │
                 └──────────────────────────────────────────────┘
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

### 4.4 `output/` — Export & Visualization

```
output/
├── __init__.py          — Package exports
├── export.py            — Ad library export (JSON/CSV) (P5-05)
├── trends.py            — Quality trend visualization (P5-03)
├── replay.py            — Narrated pipeline replay (P4-07)
└── dashboard.py         — Cost-per-ad, QWTE reporting (P1-11)
```

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

### 4.5 `data/` — Shared State & Configuration

```
data/
├── config.yaml              — Tunable parameters (all thresholds, batch size, API config)
├── ledger.jsonl             — Append-only event log (generation, evaluation, decisions)
├── brand_knowledge.json     — Brand voice profiles, audience personas, proof points (P0-04)
├── reference_ads.json       — Decomposed reference ads with structural atoms (P0-05)
├── pattern_database.json    — Competitive intelligence patterns (P4-03)
├── golden_set.json          — Calibration ads with ground-truth scores (P0-07)
└── cache/                   — Result-level cache with version TTL (P1-12)
```

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
  "seed": 2847291045
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

## 5. Data Flow: Full Pipeline Trace

A single ad's journey through the system, from brief to published library:

```
1. INTAKE
   Brief: {audience: "parents", product: "SAT prep", goal: "conversion"}
                    │
2. EXPAND (generate/brief_expansion.py)
   Load brand KB → LLM expansion → Grounded brief with demographics,
   pain points, proof points, hook/CTA candidates
                    │
3. SEED (generate/seeds.py)
   seed = SHA256("nerdy-p0-default:brief_001:0")[:8] → 0xA3F2B1C9
                    │
4. GENERATE (generate/ad_generator.py)
   Select structural atoms from reference library
   → Recombine with expanded brief + brand voice profile
   → Gemini Flash → Ad copy (primary_text, headline, description, cta_button)
   → Snapshot captured (iterate/snapshots.py)
   → Ledger event: {event_type: "generation", tokens: 850, model: "flash"}
                    │
5. EVALUATE (evaluate/evaluator.py)
   5-step CoT → Scores on 5 dimensions with rationales
   → Check floor constraints (Clarity ≥ 6.0, Brand Voice ≥ 5.0)
   → Compute weighted aggregate (conversion weights)
   → Ledger event: {event_type: "evaluation", scores: {...}, tokens: 1240}
                    │
6. ROUTE (iterate/feedback_loop.py)
   Score = 6.3 → In improvable range (5.5-7.0)
   → Escalate to regeneration cycle
                    │
7. REGENERATE — CYCLE 1 (iterate/feedback_loop.py + pareto_selection.py)
   Distill context → Generate 5 Pareto variants (Gemini Pro)
   → Evaluate all 5 → Select Pareto-optimal
   → Best variant: 6.9 — still below threshold
   → Ledger events: 5x generation + 5x evaluation + 1x selection
                    │
8. REGENERATE — CYCLE 2
   Distill context (includes Cycle 1 best)
   → Generate 5 Pareto variants → Evaluate → Select
   → Best variant: 7.4 — passes threshold and floor constraints
                    │
9. PUBLISH
   → Ad added to published library
   → Ledger event: {event_type: "decision", action: "publish", aggregate: 7.4}
   → Quality ratchet updated with new score
   → Token attribution: total cost for this ad = 850 + 1240 + (10×1100) + (10×1240) = ~25,490 tokens
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
| Image generation (v2) | Gemini image model | $$ | Same API, best text rendering |

### 8.2 Token Budget Projection (50 ads)

```
Scenario: 50 briefs, 60% pass on first eval, 30% need 1 regen cycle, 10% need 2+

First pass (all 50):
  50 × (expansion + generation + evaluation)
  50 × (~300 + ~850 + ~1,240) = ~119,500 tokens (Flash)

Regen cycle 1 (15 ads × 5 Pareto variants):
  75 × (~1,100 + ~1,240) = ~175,500 tokens (Pro for gen, Flash for eval)

Regen cycle 2 (5 ads × 5 Pareto variants):
  25 × (~1,100 + ~1,240) = ~58,500 tokens (Pro)

Brief mutation + cycle 3 (2 ads):
  10 × (~1,100 + ~1,240) = ~23,400 tokens (Pro)

Overhead (distillation, compliance, ratchet):
  ~15,000 tokens (Flash)

TOTAL ESTIMATE: ~392,000 tokens
Published ads: ~47 (94% success rate)
Cost per publishable ad: ~8,340 tokens
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

### v1: Text Pipeline (Current)
```
Brief → Expand → Generate (text) → Evaluate (5 dims) → Iterate → Publish
```

### v2: Multi-Modal (P3)
```
                              ┌── Generate Text ──┐
Brief → Shared Semantic ──────┤                    ├── Coherence Check → Publish
        Brief Expansion       └── Generate Image ──┘
                                        │
                              Attribute Checklist Eval
                              (6 visual brand attributes)
```

Key addition: Shared semantic brief expansion (R1-Q10) prevents text-image incoherence by design. Both generators receive the same enriched creative brief specifying emotional tone, visual setting, subject demographics, color palette, and key objects.

### v3: Autonomous Engine (P4)
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
| Data | JSONL (ledger), YAML (config), JSON (knowledge bases) | Human-readable, no DB dependency |
| Visualization | matplotlib | Quality trend plots, cost dashboards |
| Token counting | tiktoken | Accurate token budget tracking |
| Config | python-dotenv + pyyaml | Env vars for secrets, YAML for tunable params |
| Testing | pytest | Standard, good fixture support |
| Linting | ruff | Fast, opinionated, catches real issues |
| Data analysis | pandas | Ledger queries, correlation analysis, trend computation |

---

## 13. Phased Delivery Map

```
PHASE 0 — Foundation (P0-01 → P0-08)
├── ✅ P0-01: Scaffolding
├── ✅ P0-02: Decision ledger
├── ✅ P0-03: Seed chain + snapshots
├── ⏳ P0-04: Brand knowledge base
├── ⏳ P0-05: Reference ad collection
├── ⏳ P0-06: Evaluator calibration
├── ⏳ P0-07: Golden set tests
└── ⏳ P0-08: Checkpoint-resume

PHASE 1 — Core Pipeline (P1-01 → P1-14)
├── Brief expansion, generator, brand voice
├── CoT evaluator, adaptive weights
├── Model routing, Pareto regen, brief mutation
├── Context distillation, quality ratchet
├── Token tracking, cache, batch processor
└── 50+ ad generation run

PHASE 2 — Testing & Validation (P2-01 → P2-07)
├── Inversion tests, correlation analysis
├── Adversarial boundary tests, SPC
├── Compliance filter, e2e integration
└── 15+ tests total

PHASE 3 — Multi-Modal (P3-01 → P3-06)
├── Shared semantic brief expansion
├── Image generation + attribute eval
├── Text-image coherence, A/B variants
└── Multi-model orchestration

PHASE 4 — Autonomous Engine (P4-01 → P4-07)
├── Agentic orchestration, self-healing
├── Competitive intelligence pipeline
├── Cross-campaign transfer, explore/exploit
└── Narrated pipeline replay

PHASE 5 — Documentation (P5-01 → P5-06)
├── Decision log, technical writeup
├── Quality visualizations, demo
└── README, ad library export
```

---

*This document describes the target architecture. Implementation status is tracked in [DEVLOG.md](../development/DEVLOG.md). Design rationale is documented in [decisionlog.md](decisionlog.md).*
