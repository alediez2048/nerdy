# Ad-Ops-Autopilot — Technical Writeup

**Author:** JAD
**Project:** Autonomous Ad Copy Generation for FB/IG (Varsity Tutors SAT Prep)
**Date:** March 2026

---

*This writeup will be completed after the core pipeline (P1) is implemented and the 50+ ad generation run (P1-20) is complete. The sections below outline the structure; content will be filled with real data and findings.*

---

## 1. Architecture Overview

*How the system is structured and why.*

- Four-module pipeline: generate/ → evaluate/ → iterate/ → output/
- Append-only JSONL ledger as single source of truth
- Tiered model routing: Flash default, Pro for improvable range
- Full-ad pipeline: text + image via Nano Banana Pro
- See [systemsdesign.md](systemsdesign.md) for detailed architecture.

## 2. Methodology

*How the system generates, evaluates, and improves ads.*

- Brief expansion with grounding constraints
- Reference-decompose-recombine generation strategy
- 5-dimension chain-of-thought evaluation with contrastive rationales
- Pareto-optimal regeneration (3–5 variants per cycle)
- Brief mutation after 2 failures, escalation after 3
- Quality ratchet: max(7.0, rolling_5batch_avg − 0.5)

## 3. Key Findings

*What actually worked, what didn't, and what surprised me.*

- *To be completed with real pipeline data*
- Which structural atoms produced highest-scoring ads
- Which dimensions were hardest to improve
- Whether Pareto selection outperformed single-target regeneration
- Evaluator calibration accuracy vs. human judgment

## 4. Quality Trends

*Measurable improvement over 3+ cycles.*

- *Charts and metrics to be inserted from P1-20 run*
- Score progression per batch
- Per-dimension improvement trajectories
- Quality ratchet threshold evolution
- Publishable rate over time

## 5. Performance Per Token

*Cost efficiency of the system.*

- *Data to be inserted from P1-11 token attribution*
- Cost per publishable ad (text + image)
- Token spend by pipeline stage
- Marginal quality gain per regeneration cycle
- Tiered routing savings vs. single-model baseline

## 6. Limitations

*Honest assessment of what doesn't work well.*

- *To be completed after P1-20 run*
- See also: [decisionlog.md](decisionlog.md) §15 (What Doesn't Work Yet)

---

*This is a living document. Final version will be completed as part of P5-08.*
