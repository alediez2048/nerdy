# Architectural Decision Map — 30 Questions

All decisions are in `interviews.md`. This is the quick-reference lookup.

## Round 1 — Foundations: Failure, Brand, ROI

| # | Topic | Decision | Key Principle |
|---|-------|----------|---------------|
| R1-Q1 | Evaluator drift | Statistical Process Control | Cheapest signal, most targeted intervention |
| R1-Q2 | Failed regeneration | Brief mutation + escalation | Fix root cause before giving up |
| R1-Q3 | Dimension weighting | Campaign-goal-adaptive | Weights reflect real ad dynamics |
| R1-Q4 | Model routing | Tiered (cheap → expensive) | Concentrate expensive tokens on improvable ads |
| R1-Q5 | Dimension collapse | Pareto-optimal filtering | Structural prevention > constraint-hoping |
| R1-Q6 | Brand voice | Audience-specific profiles | Few-shot conditioning over rubric descriptions |
| R1-Q7 | Token tracking | Full attribution + marginal analysis | Marginal analysis enables self-tuning budgets |
| R1-Q8 | Cold start | Competitor-bootstrapped calibration | Calibrate the evaluator before trusting the loop |
| R1-Q9 | Quality ratchet | Rolling high-water mark | Remember your best; refuse regression |
| R1-Q10 | Multi-modal coherence | Shared semantic brief | Prevention is cheaper than detection + correction |

## Round 2 — Strategy: Prompts, Intelligence, Testing, Presentation

| # | Topic | Decision | Key Principle |
|---|-------|----------|---------------|
| R2-Q1 | Human-sounding copy | Reference-decompose-recombine | Proven structures > creative gambling |
| R2-Q2 | Competitive intelligence | Structured pattern extraction | Queryable patterns > raw ad collection |
| R2-Q3 | Test design | Inversion tests + correlation | Prove dimensions are independent, not decorative |
| R2-Q4 | Context management | Distilled context objects | Generator needs destination, not journey |
| R2-Q5 | Human escalation | Confidence-gated autonomy | Focus humans on the gray zone |
| R2-Q6 | A/B variants | Single-variable isolation | Each variant = learning investment, not lottery ticket |
| R2-Q7 | Image brand consistency | Attribute checklist evaluation | Decompose visual brand like text quality |
| R2-Q8 | Data logging | Append-only decision ledger | Zero-dependency, fully reproducible, trivially queryable |
| R2-Q9 | Explore vs exploit | Performance-decay-triggered | Explore only when exploitation is provably exhausted |
| R2-Q10 | Demo layer | Narrated pipeline replay | Show the system's thinking, especially failures |

## Round 3 — Engineering: Resilience, Compliance, Scale, Transfer

| # | Topic | Decision | Key Principle |
|---|-------|----------|---------------|
| R3-Q1 | Agentic orchestration | Linear pipeline + error boundaries | 90% of value at 20% of complexity |
| R3-Q2 | API resilience | Checkpoint-and-resume | Pipeline state integrity > retry logic |
| R3-Q3 | Platform compliance | Tiered (prompt + evaluator + regex) | Defense-in-depth |
| R3-Q4 | Reproducibility | Per-ad seed chain + snapshots | Identity-based seeds + forensic replay |
| R3-Q5 | Brief expansion | LLM expansion with grounding | Separate verified facts from creative framing |
| R3-Q6 | Evaluation prompt | Chain-of-thought structured | Force decomposition before scoring |
| R3-Q7 | Caching | Result-level + version TTL | Cache results, not prompts; invalidate on recalibration |
| R3-Q8 | Cross-campaign transfer | Shared structure, isolated content | Craft transfers; substance doesn't |
| R3-Q9 | Pipeline DAG | Batch-sequential processing | Batch-parallel for throughput, sync points for consistency |
| R3-Q10 | Rationale quality | Contrastive rationale generation | "What would +2 look like?" > "What's wrong?" |
