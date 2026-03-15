# Ad-Ops-Autopilot — Technical Writeup

**Author:** JAD
**Project:** Autonomous Ad Copy Generation for FB/IG (Varsity Tutors SAT Prep)
**Date:** March 2026

---

## 1. Architecture Overview

Ad-Ops-Autopilot is a four-module pipeline that generates, evaluates, and iteratively improves Facebook/Instagram ad copy for Varsity Tutors SAT test prep.

```
generate/ → evaluate/ → iterate/ → output/
    ↑                        |
    └────── feedback ────────┘
```

**Module boundaries are strict:** Generation code does not evaluate. Evaluation code does not generate. The `iterate/` module orchestrates but delegates. All state flows through a single append-only JSONL ledger — no database, no in-memory state between runs.

**Key architectural decisions** (see [decisionlog.md](decisionlog.md) for full ADRs):

- **Evaluator-first development** — Built and calibrated the 5-dimension evaluator (P0-06) before writing the generator. Calibrated against 42 real Meta Ad Library ads to 89.5% accuracy within ±1.0 of reference labels.
- **Decomposition everywhere** — Text quality → 5 independent dimensions. Visual quality → 10-attribute checklist. Coherence → 4-dimension cross-modal scoring. Competitive intelligence → structural pattern taxonomy.
- **Append-only JSONL ledger** — Every event (generation, evaluation, regeneration, publish/discard) is an immutable record. Enables forensic replay, checkpoint-resume, and full audit trail.
- **Identity-derived seeds** — `hash(global_seed + brief_id + cycle)` ensures reproducibility without order-dependency.

The pipeline spans 81 tickets across 7 phases (P0–P5), implemented over 14 days. 560 tests, 559 passing.

---

## 2. Methodology

### Generation
Briefs are expanded via LLM with grounding constraints — all brand facts must trace to `brand_knowledge.json`. The generator uses **reference-decompose-recombine**: competitive ads are decomposed into structural atoms (hook type, body pattern, CTA style, tone register), then recombined into novel configurations. This produces structural diversity rather than surface-level variation. Audience-specific brand voice profiles (parent-facing vs. student-facing) control tone.

### Evaluation
Every ad is scored across 5 independent dimensions via a **chain-of-thought 5-step prompt**: Read → Decompose → Compare → Score → Flag. Each dimension gets a contrastive rationale ("current state; what a +2 improvement looks like; specific gap to close"). Confidence flags identify dimensions where the evaluator is uncertain.

| Dimension | Floor | What It Catches |
|-----------|-------|----------------|
| Clarity | 6.0 | Confusing ads — instant reject |
| Value Proposition | — | Generic benefits vs. specific outcomes |
| Call to Action | — | Vague "Learn More" vs. specific next step |
| Brand Voice | 5.0 | Off-brand tone — instant reject |
| Emotional Resonance | — | Flat copy vs. emotional connection |

**Campaign-goal-adaptive weighting** (ADR-01): CTA weight swings from 10% (awareness) to 30% (conversion). Quality threshold: 7.0/10 weighted average, enforced by a **quality ratchet** that only increases: `max(7.0, rolling_5batch_avg - 0.5)`.

### Iteration
Failed ads enter a **Pareto-optimal regeneration loop** — generate 3-5 variants, evaluate all, select the Pareto-dominant variant (no other variant beats it on every dimension). This prevents the dimension regression that plagues single-target optimization. After 2 failed cycles, the brief is mutated targeting the weakest dimension. After 3 total failures, the ad is discarded with full diagnostics.

### Autonomous Operation (P4)
Four bounded agents (Researcher → Writer → Evaluator → Editor) with error containment. SPC control charts monitor batch scores for drift. Self-healing: SPC breach → diagnose weakest dimension → prescribe brief mutation → log HealingAction. Explore/exploit: when improvement plateaus for 3+ consecutive batches, the system tests untried hook types or emotional angles.

---

## 3. Key Findings

**What worked:**
- **Structural atoms are the strongest lever.** Switching from `stat hook` to `question hook` improved scores by 0.5-1.0 points more reliably than any prompt engineering. Structure > prose.
- **Evaluator calibration required 4 iterations.** The initial prompt scored everything within ±0.5 of 7.0 (no discrimination). Adding granular mid-range anchors (6.2, 6.8, 7.3, 7.8, 8.3) and increasing temperature from 0.2 to 0.4 fixed score clustering.
- **Pareto selection prevents dimension regression.** Constraint prompting ("improve CTA while maintaining clarity") failed every time — the model ignores constraints. Pareto selection solved this mathematically.
- **Brief mutation addresses root causes.** When ads persistently fail, the brief is the problem, not the generator. Injecting stronger brand context or simplifying the value proposition in the brief fixed issues that regeneration couldn't.

**What didn't work:**
- **"Be harsh" in evaluation prompts** — Caused 1-2 point systematic downward bias. Replaced with concrete score anchors.
- **Temperature as diversity control** — High temperature produces different words, not different structures. All variants had identical hook types.
- **CTA variety** — Most ads default to "Learn More" despite explicit instructions. The CTA button field is the hardest to diversify.

---

## 4. Quality Trends

| Metric | Before Fixes | After Fixes |
|--------|-------------|-------------|
| Publish rate | 18% (9/50) | 40% (4/10) |
| Score diversity | All identical 7.05 | Range: 7.08–7.28 |
| Dimension scores | All 7.0/6.0/8.0/7.0/7.0 | Varied: 6.2–7.8 per dimension |
| Ad diversity | All "Ace the SAT..." | Diverse hooks, bodies, tones |

The pipeline produces measurable improvement across iteration cycles. Cycle 1 captures the largest quality gain; cycle 2 captures diminishing but positive returns; cycle 3 rarely justifies the token cost (average gain < 0.2). The marginal analysis engine (P4-06) auto-recommends capping at 2 cycles.

The quality ratchet activates after 5 batches and has successfully prevented regression — once the system reaches a higher quality level, the threshold rises and does not drop.

---

## 5. Performance Per Token

**Model routing:** Gemini 2.0 Flash handles generation and first-pass evaluation. Gemini 2.0 Pro is reserved for ads scoring 5.5-7.0 (the "improvable range" where expensive tokens have the highest marginal return). Image generation uses Nano Banana Pro for anchor variants and Nano Banana 2 (Gemini 3.1 Flash Image) for cost-tier A/B variants.

**Cost structure (projected for 50-ad run):**
- Text pipeline (generation + evaluation + regeneration): ~$1.50
- Image pipeline (anchor + variants + aspect ratios): ~$14.00
- Video pipeline (Veo, 10-ad pilot): ~$27.00
- Total with video: ~$42.50 | Without video: ~$15.50

**Marginal analysis findings:**
- Cycle 1 average quality gain: ~1.2 points
- Cycle 2 average quality gain: ~0.5 points
- Cycle 3 average quality gain: ~0.15 points (below 0.2 threshold → auto-cap)
- Recommended max cycles: 2

**Token attribution:** Every API call is tagged with purpose (generation, evaluation, regeneration-attempt-N, brief-expansion, triage). The ledger schema includes `tokens_consumed` and `model_used` on every event, enabling full cost attribution by pipeline stage.

---

## 6. Limitations

**Evaluator accuracy depends on calibration data.** The evaluator is calibrated against 42 real ads — a small reference set. Brand Voice assessment is approximate (10-20 reference points vs. the 100+ a production system would need). The 89.5% accuracy figure is against AI-generated reference labels, not true human judgments.

**No real performance data.** The system generates and evaluates ads but has no closed-loop connection to Meta Ads Manager. Quality scores predict internal quality, not CTR/CPA/ROAS. The simulation infrastructure (Decision #22) validates the feedback loop architecture with synthetic data grounded in realistic noise models (30% copy-quality variance), but the correlations are synthetic.

**Score clustering at boundaries.** The evaluator still occasionally clusters scores near 7.0 (the threshold), making publish/reject decisions noisy for borderline ads. Confidence-gated autonomy (ADR-04) helps but doesn't eliminate this.

**CTA diversity is weak.** Despite explicit instructions and structural atom variety, most generated CTAs default to "Learn More." The CTA button field has the lowest structural diversity of any ad component.

**Cold-start dependency.** The quality ratchet, SPC drift detection, and Pareto selection all require historical data. The first 5 batches run on fallback heuristics. The transition from cold-start to steady-state is designed but not extensively tested under production conditions.

**Test coverage vs. integration confidence.** 560 tests provide high module-level confidence but limited end-to-end validation. The most important test (golden set calibration against real LLM output) is the only one that requires an API key and is skipped in CI. More integration tests that validate actual LLM behavior would strengthen confidence.

---

*For detailed architectural decisions and rationale, see [decisionlog.md](decisionlog.md). For systems design, see [systemsdesign.md](systemsdesign.md). For the 8-panel interactive dashboard, run `python -m output.export_dashboard` to generate `dashboard_data.json`, then `python -m output.dashboard_builder` to produce the HTML dashboard.*
