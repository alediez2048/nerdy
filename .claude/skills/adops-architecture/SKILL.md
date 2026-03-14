---
name: adops-architecture
description: Systems design and architecture for Ad-Ops-Autopilot — seven architectural pillars, pipeline flow, module boundaries, model routing, and phased delivery. Use when making any structural decision, creating new modules, designing pipeline stages, or evaluating implementation approaches. Triggers on any work involving generate/, evaluate/, iterate/, output/, data/, or pipeline orchestration.
---

# Ad-Ops-Autopilot Systems Architecture

## Seven Architectural Pillars

Every implementation decision must align with these pillars. When a design choice conflicts with a pillar, the pillar wins.

### 1. Decomposition Is the Architecture
- Quality → 5 independent dimensions (Clarity, Value Prop, CTA, Brand Voice, Emotional Resonance)
- Brand voice → audience-specific profiles (parent-facing, student-facing)
- Ad structure → combinable structural atoms (hook type, body pattern, CTA style, tone register)
- Evaluation → forced chain-of-thought decomposition BEFORE scoring
- Visual consistency (v2) → attribute checklists, never holistic judgment

### 2. Prevention Over Detection Over Correction
- Grounded brief expansion prevents hallucinated product claims (R3-Q5)
- Shared semantic briefs prevent multi-modal incoherence in v2 (R1-Q10)
- Tiered compliance (prompt + evaluator + regex) prevents policy violations (R3-Q3)
- Pareto-optimal selection prevents dimension collapse (R1-Q5)
- Distilled context objects prevent context bloat (R2-Q4)

### 3. Every Token Is an Investment, Not an Expense
- Tiered model routing: Flash for drafts, Pro only for improvable-range (5.5–7.0) (R1-Q4)
- Full token attribution with marginal analysis per pipeline stage (R1-Q7)
- Result-level caching with version-based TTL (R3-Q7)
- Contrastive rationales reduce regeneration cycles (R3-Q10)
- Performance-decay-triggered exploration — explore only when exploit is exhausted (R2-Q9)

### 4. The System Knows What It Doesn't Know
- Confidence scores on every evaluation (feeds human escalation) (R2-Q5)
- Statistical process control (SPC) for evaluator drift detection (R1-Q1)
- Inversion tests + correlation analysis prove dimension independence (R2-Q3)
- Confidence-gated autonomy: >7 autonomous, 5–7 flagged, <5 human required

### 5. State Is Sacred
- Checkpoint-and-resume: every successful API call writes a checkpoint (R3-Q2)
- Append-only decision ledger (JSONL): no data ever lost or modified (R2-Q8)
- Per-ad deterministic seed chains: `seed = hash(global_seed + brief_id + cycle_number)` (R3-Q4)
- Full input-output snapshots for forensic reproducibility

### 6. Learning Is Structural
- Reference-decompose-recombine: proven ad patterns → structural atoms → recombination (R2-Q1)
- Single-variable isolation for A/B variants (R2-Q6)
- Shared structural patterns across campaigns; content stays campaign-specific (R3-Q8)

### 7. Visible Reasoning Is a First-Class Output
- Narrated pipeline replay: chronological walkthrough with reasoning and failures (R2-Q10)
- Contrastive evaluation rationales: "what this is" vs "what +2 would look like" (R3-Q10)
- Decision log documents OPTIONS CONSIDERED, choice, and WHY

## Module Boundaries

| Directory | Responsibility | Does NOT |
|-----------|---------------|----------|
| `generate/` | Brief expansion, ad copy generation, reference-decompose-recombine, compliance prompt layer | Evaluate or regenerate |
| `evaluate/` | Chain-of-thought scoring, dimension aggregation, confidence flagging, calibration | Generate or modify ads |
| `iterate/` | Feedback loop orchestration, Pareto selection, brief mutation, quality ratchet, batch-sequential processing | Directly call LLM — delegates to generate/ and evaluate/ |
| `output/` | Formatting, export, narrated replay, quality trend visualization | Modify pipeline state |
| `data/` | Brand knowledge base, config, reference ads, pattern database, decision ledger | Contain executable code |
| `tests/` | All test files organized by category (golden, inversion, adversarial, correlation, pipeline) | Contain production logic |
| `docs/` | Decision log, technical writeup, limitations | Contain code |

## Pipeline Flow

```
Brief → Expand (grounded, R3-Q5) → Generate (reference-decompose-recombine, R2-Q1)
  → Evaluate (5-step CoT, R3-Q6) → Above threshold?
  ├─ Yes → Published library
  └─ No  → Weakest dimension → Contrastive rationale (R3-Q10)
           → Pareto regeneration: 3–5 variants (R1-Q5) → Re-evaluate
           → After 2 failures: mutate brief (R1-Q2)
           → After 3: escalate with diagnostics
```

## Batch-Sequential DAG (R3-Q9)

Process ads in batches of 10:
1. All generation in parallel within batch
2. All evaluation in parallel within batch
3. Regeneration decisions for the batch
4. All regeneration + re-evaluation in parallel
5. **Shared state updates BETWEEN batches only:**
   - Pattern library (new winning patterns promoted)
   - Quality ratchet (threshold recalculated)
   - Token budget reconciliation
   - SPC control charts

## Model Routing Strategy (R1-Q4)

| Task | Model | Cost Tier | Rationale |
|------|-------|-----------|-----------|
| First-draft generation + initial scoring | Gemini Flash | Cheap | 80% of work at lowest cost |
| Regeneration for improvable ads (5.5–7.0) | Gemini Pro | Expensive | Quality tokens on borderline ads |
| Brief expansion + context distillation | Gemini Flash | Cheap | High ROI, low complexity |
| Image generation (v2) | Imagen / Flux | Variable | Brand-consistent visuals |

Triage logic: ads scoring <5.5 are discarded (no expensive re-evaluation). Ads >7.0 pass directly. Only the 5.5–7.0 range gets escalated to Pro.

## Phased Delivery

| Phase | Name | Tickets | Days | Focus |
|-------|------|---------|------|-------|
| P0 | Foundation & Calibration | P0-01 – P0-08 | 0–1 | Infra, ledger, seeds, evaluator calibration |
| P1 | Core Pipeline (v1) | P1-01 – P1-14 | 1–3 | End-to-end text pipeline, 50+ ads |
| P2 | Testing & Validation | P2-01 – P2-07 | 3–4 | Prove evaluation has substance |
| P3 | Multi-Modal (v2) | P3-01 – P3-06 | 4–7 | Image generation + evaluation |
| P4 | Autonomous Engine (v3) | P4-01 – P4-07 | 7–14 | Self-healing, agents, competitive intel |
| P5 | Documentation & Submission | P5-01 – P5-06 | 13–14 | Decision log, writeup, demo |

**Build order within P0–P1:** Seeds → Ledger → Evaluation prompt → Cold-start calibration → Generator → Regeneration loop → Pareto selection → Batch processing

## Architectural Decision Reference

All 50 architectural decisions are documented in `interviews.md` as R1-Q1 through R5-Q10 (5 rounds). When implementing a feature, identify which questions govern the design and follow the "Best Answer" unless you document a deviation in the decision log.

See [references/decision-map.md](references/decision-map.md) for the complete 30-question decision matrix.
