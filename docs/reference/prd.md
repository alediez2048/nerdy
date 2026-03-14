# Ad-Ops-Autopilot — Product Requirements Document
## Autonomous Content Generation System for Facebook & Instagram

| Field | Value |
|---|---|
| Brand | Varsity Tutors (Nerdy) |
| North Star Metric | Performance Per Token |
| Scope | v1 (Full-Ad Pipeline: Copy + Image) → v2 (A/B Variant Engine + UGC Video) → v3 (Autonomous Engine) |
| Version | 1.0 — March 2026 |
| Classification | CONFIDENTIAL |

---

## Table of Contents

1. Executive Summary
2. Problem Statement
3. Architectural Pillars
4. System Architecture Overview
   - 4.5 Dashboard Architecture
   - 4.6 Image Generation Architecture — Nano Banana Pro
   - 4.7 Application Layer Architecture — Sessions, Auth & Real-Time UX
   - 4.8 Competitive Intelligence Architecture — Meta Ad Library Pattern Extraction
   - 4.9 UGC Video Architecture — Veo Integration
5. Quality Evaluation Framework
6. Project Phases & Tickets
7. Success Criteria & Rubric Alignment
8. Risk Register
9. Technical Dependencies
10. Ticket Summary

---

# Part I: Assignment Requirements

## The Challenge

Most AI-generated ad copy is mediocre. It reads like it was made by a machine, converts poorly, and costs more to produce than the value it creates. Your challenge: Build an autonomous system that generates Facebook and Instagram ad copy, knows the difference between good and bad, surfaces only its best work, and measurably improves over time. The north star metric is performance per token — how much quality per dollar of API spend.

This is not a prompt engineering exercise. This is a systems engineering challenge: generate, evaluate, iterate, and improve — with minimal human intervention. The domain is tight and closed: paid social ads for Facebook and Instagram. That's it. No email, no landing pages, no TikTok. One channel family, one content type, done well.

## Why This Matters

Real ad engines produce thousands of creatives across campaigns. The ones that win share a pattern: most ads fail (the system that surfaces only its best work wins), quality is decomposable ("good ad copy" is really clarity + value proposition + CTA strength + brand voice + emotional resonance, each independently measurable), improvement compounds (a system that tracks what works and feeds it back gets better every cycle), and ROI is the real metric (not "did the AI generate something?" but "was it worth the tokens?").

## What We're Really Evaluating

We're not testing whether you can make an API call. We're evaluating problem decomposition (can you break "generate good ads" into a system of measurable, improvable parts?), taste and judgment (do you know what good looks like? Can you teach a system to know?), creative agency (even if you don't know what good looks like, could you gather context strategically to build a working proof of concept?), systems thinking (does your system handle failure? Does it know when it's producing garbage?), and iteration methodology (what did you try, what worked, what didn't, and why?). Your decision log matters as much as your output.

## The Channel: Facebook & Instagram Paid Ads

What works on Meta right now: authentic > polished (UGC-style outperforms studio creative), story-driven > feature-list (pain point → solution → proof → CTA), pattern interrupts (scroll-stopping hooks in the first line), social proof (reviews, testimonials, numbers) builds trust, and emotional resonance > rational argument for awareness (flip for conversion).

Ad anatomy on Meta: Primary text (main copy above the image — stops the scroll), Headline (bold text below the image — short, punchy), Description (secondary text below headline — often truncated on mobile), CTA button ("Learn More", "Sign Up", "Get Started", etc.), Creative (image via Nano Banana Pro + UGC video via Veo — producing complete multi-format ready-to-publish ads covering feed, Stories, and Reels placements).

## Quality Dimensions

Every generated ad gets scored across five dimensions:

| Dimension | What It Measures | Score 1 (Bad) | Score 10 (Excellent) |
|---|---|---|---|
| Clarity | Is the message immediately understandable? | Confusing, multiple messages competing | Crystal clear single takeaway in <3 seconds |
| Value Proposition | Does it communicate a compelling benefit? | Generic/feature-focused ("we have tutors") | Specific, differentiated benefit ("raise your SAT score 200+ points") |
| Call to Action | Is the next step clear and compelling? | No CTA or vague ("learn more") | Specific, urgent, low-friction ("Start your free practice test") |
| Brand Voice | Does it sound like the brand? | Generic, could be anyone | Distinctly on-brand: empowering, knowledgeable, approachable |
| Emotional Resonance | Does it connect emotionally? | Flat, purely rational | Taps into real motivation (parent worry, student ambition, test anxiety) |

Quality threshold: 7.0/10 average to be considered publishable. Below that, the system should flag and regenerate.

## Scope Variants

**v1: Full-Ad Pipeline (1–3 days)** — Complete ad generation: text copy + image creative via Nano Banana Pro. Ad copy generator from minimal briefs, LLM-as-judge evaluation scoring 5 text dimensions + visual attribute checklist, image generation from shared semantic briefs, text-image coherence verification, feedback loop (generate → evaluate → identify weakest dimension → targeted regeneration → re-evaluate), quality threshold enforcement (7.0/10 text minimum + 80% visual attribute pass). Demonstrate 50+ generated full ads, quality improvement over 3+ cycles.

**v2: A/B Variant Engine + UGC Video (3–5 days)** — Everything in v1, plus single-variable A/B variant generation (control + 3 variants), multi-model image orchestration (Nano Banana Pro vs. Nano Banana 2 for cost/quality tradeoffs), image style transfer experiments, automated variant performance ranking, and UGC video generation via Google Veo (video spec extraction, video attribute evaluation, script-video coherence verification, multi-format ad assembly covering feed, Stories, and Reels).

**v3: Autonomous Ad Engine (1–2 weeks)** — Everything in v2, plus self-healing feedback loops, quality ratchet (standards only go UP), performance-per-token tracking, agentic orchestration (researcher, writer, editor, visual director, video director, evaluator agents), competitive intelligence, and automated creative style learning from top-performing competitor ads across all formats.

## Brand Context: Varsity Tutors (Nerdy)

Brand voice: Empowering, knowledgeable, approachable, results-focused. Lead with outcomes, not features. Confident but not arrogant. Expert but not elitist. Meet people where they are. Primary audience for this project: SAT test prep — parents anxious about college admissions, high school students stressed about scores, families comparing prep options (Princeton Review, Khan Academy, Chegg, Kaplan).

## Assessment Overview

| Area | Weight | Focus |
|---|---|---|
| Quality Measurement & Evaluation | 25% | Can the system tell good ads from bad? |
| System Design & Architecture | 20% | Is the system well-built and resilient? |
| Iteration & Improvement | 20% | Does ad quality measurably improve? |
| Speed of Optimization | 15% | How efficiently does the system iterate? |
| Documentation & Individual Thinking | 20% | Can we see YOUR mind at work? |

## Bonus Points (up to +24)

| Achievement | Bonus |
|---|---|
| Self-healing / automatic quality improvement | +7 |
| Multi-model orchestration with clear rationale | +3 |
| Performance-per-token tracking (ROI awareness) | +2 |
| Quality trend visualization | +2 |
| Competitive intelligence from Meta Ad Library | +10 |

---

# Part II: Architectural Pressure Test — 5 Rounds (50 Questions)

## Round 1: Foundations — Failure Handling, Brand Voice Integrity, and ROI Maximization

### R1-Q1: How should the system detect and recover from evaluator drift?

**Why this matters:** If your evaluator silently drifts, your 7.0 threshold becomes meaningless.

**Option A — Static Calibration Anchors:** Fixed set of 10–15 reference ads with ground truth scores. Run before every batch. Halt if drift >±0.5.

**Option B — Statistical Process Control (SPC):** Track score distributions via control charts. ±2σ limits. Canary injection on breach.

**Option C — Dual-Evaluator Consensus:** Two independent evaluators. Flag when >20% disagreement.

**Best Answer: Option B (Statistical Process Control)** — Continuous monitoring with minimal overhead. Canary injection only fires when needed. Option A's anchors become the recalibration mechanism once SPC flags an issue.

### R1-Q2: When the feedback loop fails after N regeneration cycles, what should the system do?

**Why this matters:** Infinite retry loops silently kill token budgets.

**Option A — Hard Cutoff:** Max 3 attempts, then archive as failed.

**Option B — Diminishing Returns Detection:** Stop when delta <0.3 points between cycles.

**Option C — Brief Mutation + Escalation:** After 2 failures, mutate the brief targeting the weak dimension. After 3 total failures, escalate with full diagnostics.

**Best Answer: Option C (Brief Mutation + Escalation)** — The only approach that tries to fix the root cause before giving up.

### R1-Q3: How should the system weight the five quality dimensions?

**Why this matters:** Equal weighting treats confusing ads with great resonance the same as clear, emotionless ads.

**Option A — Fixed Hierarchical Weights:** Static weights (Clarity 30%, VP 25%, CTA 20%, BV 15%, ER 10%).

**Option B — Campaign-Goal-Adaptive Weights:** Two profiles: awareness (ER 25%, BV 20%, Clarity 25%, VP 20%, CTA 10%) and conversion (CTA 30%, VP 25%, Clarity 25%, BV 10%, ER 10%).

**Option C — Dynamic Weights with Floor Constraints:** Adaptive weights that increase for consistently weak dimensions.

**Best Answer: Option B (Campaign-Goal-Adaptive Weights)** — Predictable, explainable. Add floor constraints from Option C (Clarity ≥ 6.0, Brand Voice ≥ 5.0).

### R1-Q4: How should the system orchestrate model selection to maximize quality-per-dollar?

**Option A — Single Model:** Gemini for everything.

**Option B — Tiered Model Routing:** Flash for first drafts + triage. Pro only for borderline ads (5.5–7.0). Below 5.5 discarded cheap; above 7.0 passes cheap.

**Option C — Specialized Model Assignment:** Different models for different tasks.

**Best Answer: Option B (Tiered Model Routing)** — 40–60% token reduction. Most ads are clearly bad or clearly good.

### R1-Q5: How should the system prevent dimension collapse?

**Why this matters:** Naive targeting of weakest dimension creates whack-a-mole oscillation.

**Option A — Constraint-Based Prompts:** Instruct generator to improve X while maintaining others.

**Option B — Pareto-Optimal Filtering:** Generate 3–5 variants, select Pareto-dominant (no other variant scores higher on all dimensions).

**Option C — Sliding Window Regression:** Reject if any dimension drops >0.5.

**Best Answer: Option B (Pareto-Optimal Filtering)** — Structurally prevents collapse. Selection logic handles trade-offs mathematically.

### R1-Q6: How should the system ensure Brand Voice consistency across audiences?

**Option A — Audience-Specific Profiles:** "Parent-facing" (authoritative, reassuring) and "Student-facing" (relatable, motivating) with few-shot examples.

**Option B — Embedding + Cosine Similarity:** Compare against brand corpus.

**Option C — Two-Stage Evaluation:** Split Brand Voice into alignment + appropriateness.

**Best Answer: Option A (Audience-Specific Brand Voice Profiles)** — Few-shot examples do the heavy lifting for tonal nuance.

### R1-Q7: How should the system track "Performance per Token"?

**Option A — Cost-Per-Publishable-Ad:** Simple total tokens / published ads.

**Option B — Quality-Weighted Token Efficiency:** QWTE = avg score / tokens per published ad.

**Option C — Full Token Attribution + Marginal Analysis:** Tag every API call. Marginal analysis: quality gain per regen attempt.

**Best Answer: Option C (Full Token Attribution with Marginal Analysis)** — The only approach generating actionable optimization signals. Self-tuning cost envelope.

### R1-Q8: How should the system handle the cold-start problem?

**Option A — Reference-Seeded Generation:** Few-shot with structural decomposition.

**Option B — Competitor-Bootstrapped Calibration:** Run evaluator against 20–30 competitor ads first. Calibrate before generating.

**Option C — Synthetic Warm-Up Batch:** Generate 20 intentionally diverse ads, calibrate, discard.

**Best Answer: Option B (Competitor-Bootstrapped Calibration)** — Solve the right problem first: evaluator calibration. Combine with Option A for the generator.

### R1-Q9: How should the system implement a "quality ratchet"?

**Option A — Fixed Absolute Threshold:** 7.0 forever.

**Option B — Rolling High-Water Mark:** Effective threshold = max(7.0, rolling_5batch_avg − 0.5).

**Option C — Percentile-Based:** Only publish top 30%.

**Best Answer: Option B (Rolling High-Water Mark)** — True ratchet: remembers best performance, refuses regression. 0.5 buffer prevents over-aggressiveness.

### R1-Q10: How should the system handle multi-modal coherence?

**Option A — Sequential (image conditioned on text).**

**Option B — Parallel + post-hoc coherence scoring.**

**Option C — Shared Semantic Brief Expansion:** Expand brief into detailed creative brief before generating either.

**Best Answer: Option C (Shared Semantic Brief Expansion)** — Prevents incoherence by design. Use Option A's coherence evaluation as verification.

### Round 1 Summary

| # | Question | Best Answer | Key Principle |
|---|---|---|---|
| 1 | Evaluator Drift Detection | Statistical Process Control | Cheapest signal, most targeted intervention |
| 2 | Failed Regeneration Handling | Brief Mutation + Escalation | Fix root cause before giving up |
| 3 | Dimension Weighting | Campaign-Goal-Adaptive | Weights should reflect real ad dynamics |
| 4 | Model Orchestration | Tiered Model Routing | Concentrate expensive tokens on improvable ads |
| 5 | Dimension Collapse Prevention | Pareto-Optimal Filtering | Structural prevention > constraint-hoping |
| 6 | Brand Voice Consistency | Audience-Specific Profiles | Few-shot conditioning over rubric descriptions |
| 7 | Performance per Token | Full Token Attribution | Marginal analysis enables self-tuning budgets |
| 8 | Cold-Start Problem | Competitor-Bootstrapped Calibration | Calibrate the evaluator before trusting the loop |
| 9 | Quality Ratchet | Rolling High-Water Mark | Remember your best; refuse regression |
| 10 | Multi-Modal Coherence | Shared Semantic Brief | Prevention is cheaper than detection + correction |

---

## Round 2: Strategy — Prompt Design, Competitive Intelligence, Testing, Scaling, and Human-in-the-Loop

### R2-Q1: How should generation prompts produce human-sounding ads?

**Option A — Style-Negative Prompting:** Anti-pattern blacklist.

**Option B — Persona-Anchored Generation:** Specific personas per audience.

**Option C — Reference-Decompose-Recombine:** Decompose high-performing ads into structural atoms (hook type, body pattern, CTA style), recombine proven elements.

**Best Answer: Option C (Reference-Decompose-Recombine Pipeline)** — Creates a repeatable, improvable system. Competitive intelligence feeds directly into the generator.

### R2-Q2: How should the competitive intelligence pipeline work?

**Option A — Manual Snapshot:** 30–50 ads at project start. Static.

**Option B — Structured Pattern Extraction:** Automated/semi-automated collection. LLM extraction into structured records. Pattern database.

**Option C — Competitive Differential Positioning:** Beyond patterns, run gap analysis for whitespace.

**Best Answer: Option B (Structured Pattern Extraction Pipeline)** — Systematically converts competitive data into queryable patterns. Layer Option C as stretch.

### R2-Q3: How should tests verify the evaluation framework?

**Option A — Golden Set Regression:** 15–20 golden ads, ±1.0 tolerance.

**Option B — Adversarial Boundary Tests:** Perfect Clarity + zero Brand Voice, wrong brand, etc.

**Option C — Inversion Tests + Correlation Analysis:** Degrade one dimension at a time. Verify only that dimension drops. Correlation analysis: flag r > 0.7.

**Best Answer: Option C (Inversion Tests + Correlation Analysis)** — Tests the evaluator's core claim of 5 independent dimensions. Build all three: A for regression, B for boundaries, C as real proof.

### R2-Q4: How should context windows be managed as iteration history grows?

**Option A — Fixed-Window with Recency Bias:** Last 2 cycles only.

**Option B — Structured Context Partitioning:** Rigid sections with token budgets.

**Option C — Distilled Context Objects:** Compact distillation per cycle: best attempt + improvement + anti-patterns. Replaces all raw history.

**Best Answer: Option C (Distilled Context Objects)** — Generator needs the destination, not the journey. Prompt stays compact regardless of depth.

### R2-Q5: When should human intervention occur?

**Option A — Threshold-Based Escalation:** Explicit triggers (>30% batch failure, etc.).

**Option B — Confidence-Gated Autonomy:** Evaluator self-rates confidence. >7 autonomous, 5–7 flagged, <5 human required.

**Option C — Anomaly-Driven:** Statistical baselines, escalate on 2σ.

**Best Answer: Option B (Confidence-Gated Autonomy)** — Concentrates human attention on the gray zone. Supplement with Option A's brand safety trigger.

### R2-Q6: How should A/B variants maximize learning per token?

**Option A — Random Diversity:** Different temperatures.

**Option B — Single-Variable Isolation:** Control + 3 variants each changing one structural element.

**Option C — Factorial Design with Pruning.**

**Best Answer: Option B (Single-Variable Isolation)** — After 10 briefs (40 ads), strong signal on what works. Each token is a learning investment.

### R2-Q7: How should the image evaluator assess brand consistency?

**Option A — Multimodal LLM holistic rating.**

**Option B — CLIP embeddings + cosine similarity.**

**Option C — Attribute Checklist:** Student-age subjects? Warm lighting? Educational context? Diversity? No competitor branding?

**Best Answer: Option C (Attribute Checklist Evaluation)** — Decomposes visual brand like text quality. Binary/near-binary per attribute. Aggregate is interpretable.

### R2-Q8: How should data storage support retrospective analysis?

**Option A — Flat file JSON per batch.**

**Option B — SQLite event store.**

**Option C — Append-Only Decision Ledger:** Single JSONL with standardized schema. Lightweight query with pandas.

**Best Answer: Option C (Append-Only Decision Ledger)** — Zero-dependency, fully reproducible, trivially queryable.

### R2-Q9: How should the system handle explore vs. exploit?

**Option A — Fixed 80/20 split.**

**Option B — Performance-Decay-Triggered:** Pure exploit until plateau (<0.1 improvement over 3 batches), then explore.

**Option C — Multi-Armed Bandit.**

**Best Answer: Option B (Performance-Decay-Triggered Exploration)** — Explores only when exploitation is provably exhausted.

### R2-Q10: How should demo/presentation maximize Documentation rubric (20%)?

**Option A — Static PDF/markdown report.**

**Option B — Interactive HTML decision trail.**

**Option C — Narrated Pipeline Replay:** Chronological walkthrough with per-batch reasoning, failures highlighted.

**Best Answer: Option C (Narrated Pipeline Replay)** — Makes system thinking legible. Highlights failures — exactly what rubric calls "excellent."

### Round 2 Summary

| # | Question | Best Answer | Key Principle |
|---|---|---|---|
| 1 | Human-Sounding Copy | Reference-Decompose-Recombine | Proven structures > creative gambling |
| 2 | Competitive Intelligence Pipeline | Structured Pattern Extraction | Queryable patterns > raw ad collection |
| 3 | Evaluation Test Design | Inversion Tests + Correlation | Prove dimensions are independent |
| 4 | Context Window Management | Distilled Context Objects | Generator needs destination, not journey |
| 5 | Human-in-the-Loop Triggers | Confidence-Gated Autonomy | Focus humans on the gray zone |
| 6 | A/B Variant Strategy | Single-Variable Isolation | Each variant is a learning investment |
| 7 | Image Brand Consistency | Attribute Checklist Evaluation | Decompose visual brand like text quality |
| 8 | Data Storage & Logging | Append-Only Decision Ledger | Zero-dependency, fully reproducible |
| 9 | Explore vs. Exploit | Performance-Decay-Triggered | Explore only when exploitation exhausted |
| 10 | Demo & Presentation Layer | Narrated Pipeline Replay | Show thinking, especially failures |

### Cross-Round Architecture Synthesis (Rounds 1 & 2)

1. **Decomposition Everywhere** — Text quality → 5 dimensions. Brand voice → audience profiles. Visual consistency → attribute checklists. Competitive intelligence → structural patterns.
2. **Prevention Over Detection** — Shared semantic briefs (R1-Q10). Distilled context objects (R2-Q4). Pareto-optimal selection (R1-Q5).
3. **Token-Aware Decision Making** — Tiered routing (R1-Q4). Full attribution (R1-Q7). Diminishing returns (R1-Q2). Decay-triggered exploration (R2-Q9).
4. **Self-Awareness as Architecture** — SPC for drift (R1-Q1). Confidence-gated autonomy (R2-Q5). Inversion tests (R2-Q3).
5. **Visible Reasoning** — Narrated replay (R2-Q10). Append-only ledger (R2-Q8). Rolling high-water mark (R1-Q9).

---

## Round 3: Engineering — Agentic Orchestration, Resilience, Guardrails, Reproducibility, Caching, and Pipeline Design

### R3-Q1: How should agentic orchestration avoid cascading failures?

**Option A — Linear Pipeline + Error Boundaries:** Strict sequence: Researcher → Writer → Editor → Evaluator. Bounded contracts. Halt on failure.

**Option B — Event-Driven Agent Mesh:** Concurrent with circuit breakers.

**Option C — Hierarchical Orchestrator with Contract Negotiation.**

**Best Answer: Option A (Linear Pipeline with Error Boundaries)** — 90% of value at 20% of complexity. Parallelize across briefs for throughput.

### R3-Q2: How should the system handle API failures and rate limits?

**Option A — Retry with Exponential Backoff.**

**Option B — Checkpoint-and-Resume:** After every successful API call, write checkpoint_id to ledger. Resume from last checkpoint on crash.

**Option C — Rate-Aware Batch Scheduler.**

**Best Answer: Option B (Checkpoint-and-Resume)** — On free tier with 2 RPM, 429s are steady state. Combined with Option A's retry logic.

### R3-Q3: How should Meta advertising policy guardrails work?

**Option A — Post-Generation Policy Filter.**

**Option B — Policy-Embedded Generation Prompts.**

**Option C — Tiered Compliance Architecture:** (1) generation prompts with hard constraints, (2) evaluator binary compliance check, (3) regex/keyword filter for obvious violations.

**Best Answer: Option C (Tiered Compliance Architecture)** — Defense-in-depth. Violations must beat all three layers.

### R3-Q4: How should seed management and deterministic behavior work?

**Option A — Global Seed, temperature=0.**

**Option B — Per-Ad Seed Chain:** seed = hash(global_seed + brief_id + cycle_number). Identity-derived, not position-dependent.

**Option C — Snapshot-Based Reproducibility:** Full I/O snapshots for every API call.

**Best Answer: Option B + C Combined** — B for intentional reproducibility, C for forensic reproducibility.

### R3-Q5: How should minimal briefs expand without hallucinating?

**Option A — Static Brand Knowledge Base.**

**Option B — LLM Expansion with Grounding:** Expand using ONLY verified facts. Creative framing around verified facts.

**Option C — Template-Based with Audience Matrices.**

**Best Answer: Option B (LLM-Powered Brief Expansion with Grounding Constraints)** — Separates what the system knows from how it frames it.

### R3-Q6: How should the LLM-as-Judge evaluation prompt be structured?

**Option A — Single-Pass Holistic.**

**Option B — Dimension-Isolated Sequential:** Separate call per dimension. 5x cost.

**Option C — Chain-of-Thought Structured:** Single call, strict 5-step sequence: (1) Read ad, (2) identify hook/VP/CTA/emotional angle, (3) compare against calibration examples, (4) score with contrastive rationale, (5) flag low-confidence dimensions.

**Best Answer: Option C (Chain-of-Thought Structured Evaluation)** — Achieves most of B's independence at A's cost. Forced decomposition reduces halo effect.

### R3-Q7: How should caching work?

**Option A — Prompt-Level Deduplication.**

**Option B — Semantic Component Caching.**

**Option C — Result-Level Caching with Version TTL:** Cache keyed by hash(ad_text + evaluator_prompt_version). Recalibration invalidates all cached scores.

**Best Answer: Option C (Result-Level Caching with Version TTL)** — Prompt-version key ensures recalibration automatically invalidates.

### R3-Q8: How should cross-campaign learning work?

**Option A — Isolated Campaign Silos.**

**Option B — Shared Structural Patterns, Isolated Content:** Structural learning shared (hook types, CTA styles). Content isolated. Campaign_scope tags.

**Option C — Transfer Learning with Validation Gates.**

**Best Answer: Option B (Shared Structural Patterns, Isolated Content)** — Mirrors how real ad agencies think: craft transfers, substance doesn't.

### R3-Q9: How should the pipeline DAG maximize throughput?

**Option A — Batch-Sequential:** Batches of 10. Parallel within stage, sequential across stages. Sync at batch boundaries.

**Option B — Per-Ad Independent Pipelines.**

**Option C — Priority-Queue-Based.**

**Best Answer: Option A (Batch-Sequential Processing)** — 10x throughput over sequential. Natural checkpoints at batch boundaries.

### R3-Q10: How should evaluation rationales be structured?

**Option A — Free-Text Rationale.**

**Option B — Structured Diagnostic Templates.**

**Option C — Contrastive Rationale Generation:** Not just "why X scored Y" but "what a +2 version would look like" with specific gap identification.

**Best Answer: Option C (Contrastive Rationale Generation)** — Makes the evaluator imagine the improvement. Dramatically reduces regeneration cycles.

### Round 3 Summary

| # | Question | Best Answer | Key Principle |
|---|---|---|---|
| 1 | Agentic Orchestration | Linear Pipeline + Error Boundaries | 90% of value at 20% of complexity |
| 2 | API Failure Resilience | Checkpoint-and-Resume | Pipeline state integrity > retry logic |
| 3 | Platform Compliance | Tiered Compliance (3 layers) | Defense-in-depth |
| 4 | Seed & Reproducibility | Per-Ad Seed Chain + Snapshots | Identity-based seeds + forensic replay |
| 5 | Brief Expansion | LLM Expansion with Grounding | Separate verified facts from creative framing |
| 6 | Evaluation Prompt Design | Chain-of-Thought Structured | Force decomposition before scoring |
| 7 | Caching Strategy | Result-Level + Version TTL | Cache results, not prompts |
| 8 | Cross-Campaign Transfer | Shared Structure, Isolated Content | Craft transfers; substance doesn't |
| 9 | Pipeline DAG Design | Batch-Sequential Processing | Batch-parallel for throughput, sync for consistency |
| 10 | Rationale Quality | Contrastive Rationale Generation | "What would +2 look like?" > "What's wrong?" |

---

## Round 4: Business & UX — Form Factor, Data Strategy, Presentation, and Scope

### R4-Q1: What should the deliverable form factor be?

**Best Answer: Jupyter Notebook** — The notebook IS the decision log. Narrative + code + output in one artifact.

### R4-Q2: What data should train the ad engine?

**Best Answer: Multi-source assembly** — Slack reference ads + competitor ads from Meta Ad Library + Varsity Tutors public presence + ad writing best practices.

### R4-Q3: How should the brief authoring UX work?

**Best Answer: Structured YAML with example briefs** — Machine-parseable, version-controllable, with templates.

### R4-Q4: How should the ad library be presented?

**Best Answer: Curated showcase** — Best 5 ads + before/after pairs + interesting failures. Not a raw dump.

### R4-Q5: What should the demo video structure be?

**Best Answer: Problem-Solution-Proof in 7 minutes** — Act 1: naive approach fails. Act 2: architecture. Act 3: before/after + dashboard.

### R4-Q6: How should LLM scores relate to real ad performance?

**Best Answer: Regress against performance data if available; acknowledge gap honestly if not.**

### R4-Q7: How should scope be prioritized?

**Best Answer: v1 core + cherry-picked bonus (21 of 24 points without needing full v2/v3).**

### R4-Q8: How should configuration be designed?

**Best Answer: Single config.yaml with rationale linking to architectural decisions.**

### R4-Q9: What should the decision log strategy be?

**Best Answer: Structured ADRs + narrative reflection** — Options considered, chosen, why, limitations, "what surprised me."

### R4-Q10: What non-functional requirements matter?

**Best Answer: Cost projections + scaling analysis + specific roadmap.**

### Updated Architecture — Adding Pillar 8

**Pillar 8: The Reviewer Is a User, Too** — The submission is a product. The reviewer is the customer. The notebook narrates the journey (R4-Q1). The curated showcase tells the quality story (R4-Q4). The demo respects their time (R4-Q5). The decision log shows your mind, not just your code (R4-Q9).

---

## Round 5: Application Layer — Sessions, Auth, Brief Config, Progress & Deployment

### R5-Q1: Session Granularity — What IS a session?

**Best Answer: One pipeline run = one session.** Immutable after completion. Config stored as JSON. Results computed at completion, never updated. New parameters → new session.

### R5-Q2: Session List — How should users browse past runs?

**Best Answer: Flat reverse-chronological card list** with sparkline quality trends, status badges, audience/goal filters. Running sessions show live progress.

### R5-Q3: Brief Configuration — How should users set up a new session?

**Best Answer: Progressive disclosure form.** Required fields always visible (audience, goal, ad count). Advanced settings in collapsible accordion. Clone-from-previous for repeat users.

### R5-Q4: Progress Monitoring — How should users track running sessions?

**Best Answer: Hybrid — background by default, live view optional.** Session list polls every 30s. Optional "Watch Live" with SSE streaming (cycle indicator, live score feed, cost accumulator).

### R5-Q5: Authentication — Who can access what?

**Best Answer: Google SSO with @nerdy.com domain restriction.** Per-user session isolation. Share via read-only time-limited links.

### R5-Q6: Post-Generation Editability — Can users modify results?

**Best Answer: Immutable generation + mutable curation layer.** Select, reorder, annotate, light-edit with diff tracking. Dashboard metrics always reflect original pipeline output.

### R5-Q7: Tech Stack — What should power the app?

**Best Answer: FastAPI (Python) + React (Vite) + PostgreSQL + Celery/Redis.** Same language as pipeline. Dashboard already in React.

### R5-Q8: Dashboard Integration — How does the existing dashboard become session-aware?

**Best Answer: Session detail = existing dashboard, scoped to selected session's ledger.** Add breadcrumbs + back button + 6th Curated Set tab.

### R5-Q9: Session Comparison — How to compare two runs?

**Best Answer: Deferred to v1.1.** Ship core value first. Plan: overlay comparison on session detail.

### R5-Q10: Deployment Model — Where does it run?

**Best Answer: Single cloud VM via Docker Compose on Railway or Render.** `git push` → auto-deploy. $20–50/month. Auto-HTTPS.

### Updated Architecture — Adding Pillar 9

**Pillar 9: The Tool Is the Product** — Session management, authentication, brief configuration, and progress monitoring transform the pipeline from a CLI tool into a product. Immutable sessions guarantee reproducibility. Progressive disclosure makes configuration fast. The curation layer preserves metric integrity while enabling practical use.

### Cross-Round Synthesis (All 5 Rounds)

| Round | Theme | Establishes |
|---|---|---|
| R1 | Foundations | Core feedback loop mechanics |
| R2 | Strategy | How the system gets smart |
| R3 | Engineering | How the system survives and scales |
| R4 | Business & UX | How the work is presented and evaluated |
| R5 | Application Layer | How the pipeline becomes a product |

---

# Part III: Verification Report — 5-Round Interview Alignment Audit

## 1. Round Progression

Verdict: Yes — clear thematic escalation. R1 answers "what does the system do?", R2 answers "how does the system think?", R3 answers "how does the system survive?", R4 answers "how is the work presented?", R5 answers "how does the pipeline become a product?"

## 2. Cross-Reference Integrity

14 explicit cross-references verified. Zero contradictions found. The append-only ledger (R2-Q8) is the most heavily referenced component.

## 3. Assignment Coverage Audit

All 5 "Ambiguous Elements" answered. All 5 rubric areas covered. All 5 bonus opportunities addressed. All 3 scope variants covered. All 7 code quality requirements addressed.

## 4. Internal Consistency

No hard contradictions. Two managed tensions: (1) Pareto-Optimal Filtering costs 3–5x but reduces total cycles. (2) Linear pipeline (per-ad) + batch-sequential (batch-level) are complementary.

## 5. Gap Analysis

| Gap | Impact | Recommendation |
|---|---|---|
| Output JSON schemas | Medium | Create schemas/ with sample JSON |
| Prompt templates (actual text) | High | Create prompts/ with annotated first drafts |
| Brand knowledge base content | Medium | Build from Slack + website + assignment |
| Specific threshold values | Low-Medium | Create config.yaml with all tunable params |
| Error message / logging standards | Low | Adopt Python standard logging |

## 6. Recommended Read Order

Assignment spec → Round 1 → Round 2 → Round 3 → Round 4 → Round 5 → 9 Architectural Pillars → PRD Phases

---

# Part IV: Product Requirements Document

## 1. Executive Summary

Ad-Ops-Autopilot is an autonomous engine that generates, evaluates, and iteratively improves Facebook and Instagram ad copy for Varsity Tutors. The system solves the fundamental problem of mediocre AI-generated content by connecting three core capabilities: a multi-modal generator (text + image), an LLM-as-Judge evaluator scoring across five quality dimensions, and a self-correcting feedback loop that drives measurable improvement cycle over cycle.

The system is designed around a single north star metric: Performance per Token — maximizing quality output per dollar of API spend.

Key outcomes:
- 50+ publishable full ads (copy + generated image) with evaluation scores across 5 text dimensions + visual attribute checklist
- Measurable quality improvement over 3+ iteration cycles with documented causes
- Full token cost attribution enabling ROI optimization at every pipeline stage
- Autonomous self-healing: the system detects quality drops, diagnoses root causes, and auto-corrects
- Complete decision log and narrated pipeline replay demonstrating visible reasoning throughout

## 2. Problem Statement

Most AI-generated ad copy is mediocre. The core challenge is not generation — it is evaluation. A system that cannot reliably distinguish an 8/10 ad from a 5/10 ad cannot improve, regardless of how sophisticated its generator is.

Target audience: SAT test prep for Varsity Tutors — anxious parents, stressed students, and families comparing prep options (Princeton Review, Khan Academy, Chegg, Kaplan).

## 3. Architectural Pillars

The system architecture is governed by nine pillars derived from five rounds of architectural pressure-testing (50 design questions).

| Pillar | Principle | Key Decisions |
|---|---|---|
| 1. Decomposition Is the Architecture | Every complex judgment → independently measurable parts | 5 text dimensions, visual attribute checklist, 4-dimension coherence, structural patterns, chain-of-thought evaluation |
| 2. Prevention Over Detection | Prevent problems architecturally | Shared semantic briefs, grounded expansion, tiered compliance, Pareto selection |
| 3. Every Token Is an Investment | Track cost and optimize marginal returns | Tiered routing, full attribution, result caching, contrastive rationales |
| 4. The System Knows What It Doesn't Know | Self-awareness = output quality | SPC for drift, confidence-gated autonomy, inversion tests |
| 5. State Is Sacred | No work lost. Every run reproducible. | Checkpoint-resume, append-only ledger, per-ad seed chains |
| 6. Learning Is Structural | Learn why, not just that | Reference-decompose-recombine, single-variable isolation, shared patterns |
| 7. Visible Reasoning | Thinking is a first-class output | Narrated replay, contrastive rationales, honest failures |
| 8. The Reviewer Is a User, Too | The submission is a product for the reviewer | Notebook form factor, curated showcase, 7-min demo, ADR + narrative log |
| 9. The Tool Is the Product | The pipeline becomes a product | Session management, auth, brief config, progress monitoring |

## 4. System Architecture Overview

### 4.1 Pipeline Flow

Brief → Expand (R3-Q5) → Generate Copy (R2-Q1) → Generate Image (Nano Banana Pro) → Coherence Check
├─ Coherent → Evaluate Text (R3-Q6) + Evaluate Image (attribute checklist) → Above thresholds?
│ ├─ Yes → Add to published library (full ad: copy + image)
│ └─ No → Identify weakest dimension → Contrastive rationale (R3-Q10) → Pareto regeneration (R1-Q5) → Re-evaluate
└─ Incoherent → Regenerate image with adjusted prompt (1 retry) → Re-check coherence

### 4.2 Directory Structure

```
generate/          — Ad copy generation from expanded briefs
generate_image/    — Nano Banana Pro image generation, prompt construction, coherence verification
generate_video/    — Veo UGC video generation, video spec extraction (v2)
evaluate/          — Chain-of-thought dimension scoring, attribute checklist, LLM-as-Judge
iterate/           — Feedback loop, brief mutation, Pareto selection, quality ratchet
output/            — Formatting, export, quality trend visualization, narrated replay, full ad assembly
data/              — Brand knowledge base, reference ads, pattern database, config
tests/             — Golden set, adversarial, inversion, correlation tests
docs/              — Decision log, limitations, technical writeup
app/               — Application layer (R5)
  app/api/         — FastAPI routes (sessions, auth, progress SSE)
  app/models/      — SQLAlchemy models (users, sessions, curated_sets)
  app/workers/     — Celery tasks (pipeline execution, progress reporting)
  app/frontend/    — React app (session list, brief config, progress view, dashboard shell)
docker-compose.yml      — Local development stack
docker-compose.prod.yml — Production deployment
```

### 4.3 Agentic Orchestration (v3)

Linear pipeline with error boundaries (R3-Q1). Agents: Researcher → Writer → Editor → Evaluator. Parallelism happens across briefs, not within a single ad.

### 4.4 Model Strategy

| Task | Model | Rationale |
|---|---|---|
| First-draft generation + initial scoring | Gemini Flash (cheap tier) | 80% of work at lowest cost |
| Regeneration for improvable ads (5.5–7.0) | Gemini Pro (expensive tier) | Quality tokens on borderline ads |
| Image generation (v1) | Nano Banana Pro (Gemini 3 Pro Image) | 4K output, text rendering, ~$0.13/image |
| Image generation — cost tier (v2) | Nano Banana 2 (Gemini 3.1 Flash Image) | ~$0.02–0.05/image via third-party |
| Image coherence evaluation | Gemini Flash (multimodal) | Cheap multimodal call |
| UGC video generation (v2) | Veo 3.1 Fast | Native audio, 1080p 9:16, ~$0.90/6-sec video |
| Video attribute evaluation | Gemini Flash (multimodal) | Frame sampling + audio analysis |
| Script-video coherence | Gemini Flash (multimodal) | Same framework as text-image coherence |
| Brief expansion + context distillation | Gemini Flash | Cheap LLM call, high ROI |

### 4.5 Dashboard Architecture — Live Performance Benchmarks

Single-file HTML dashboard reads from the append-only decision ledger and renders 8 panels: Pipeline Summary (hero metrics), Iteration Cycles (before/after), Quality Trends (charts), Dimension Deep-Dive (correlation matrix), Ad Library (filterable with rationales), Token Economics (cost attribution, marginal analysis), System Health (SPC, confidence, escalation), Competitive Intelligence (pattern database). Data source: output/dashboard_data.json from export_dashboard.py.

### 4.6 Image Generation Architecture — Nano Banana Pro Integration

#### 4.6.1 Why Nano Banana Pro

Google's Gemini 3 Pro Image model. 4K resolution, 10 Meta-compatible aspect ratios, text rendering capability, SynthID safety watermarking. ~$0.13/image at 1K resolution. Same Google ecosystem as Gemini text models — single API key, unified billing.

#### 4.6.2 Visual Spec Extraction

From the same expanded brief that drives copy generation, extract a structured visual spec:
- Subject: demographic, activity, emotional expression
- Setting: location, lighting, time of day
- Color palette: brand colors + mood-appropriate accents
- Emotional tone: matching the copy's emotional register
- Campaign goal cue: aspirational (awareness) or action-oriented (conversion)
- Text overlay: headline if applicable
- Aspect ratio: 1:1 default, 4:5 for feed, 9:16 for Stories/Reels
- Negative prompt: no competitor branding, no AI artifacts

#### 4.6.3 Multi-Variant Image Generation & Pareto Selection

Generate 3 image variants per ad instead of one:
1. **Anchor variant** — straight interpretation of visual spec
2. **Tone shift variant** — same subject/setting, adjusted emotional register (e.g., warmer, more aspirational)
3. **Composition shift variant** — different framing (close-up vs. environment, single subject vs. group)

Evaluate all 3 via attribute checklist + coherence check. Select best via composite score:

```
composite = (attribute_pass_pct × 0.4) + (coherence_avg × 0.6)
```

Log all 3 variants with scores — losing variants provide learning data for future visual spec refinement.

#### 4.6.4 Visual Attribute Checklist (10 Attributes)

Multimodal Gemini Flash call: image + visual spec → binary checklist:

| # | Attribute | Type | Pass Criteria |
|---|---|---|---|
| 1 | Age-appropriate subject | Required | Subject appears 16–18 (student) or 35–50 (parent) |
| 2 | Diversity representation | Required | Not exclusively one demographic |
| 3 | Warm/professional lighting | Required | No harsh shadows, no dark/gloomy |
| 4 | Brand color presence | Recommended | Varsity Tutors teal/blue visible |
| 5 | No competitor branding | Required | No Kaplan, Princeton Review, etc. logos |
| 6 | Setting matches spec | Recommended | Location aligns with visual spec |
| 7 | Emotional tone matches brief | Required | Expression/body language matches intended emotion |
| 8 | Text overlay legibility | Conditional | If text present, readable at mobile size |
| 9 | No AI artifacts | Required | No extra fingers, warped faces, impossible geometry |
| 10 | Correct aspect ratio | Required | Matches requested format |

**Pass threshold:** 80% (8/10) with all Required attributes passing.

#### 4.6.5 Text-Image Coherence Verification

Separate multimodal Gemini Flash call: ad copy + generated image → 4-dimension coherence score:

| Dimension | What It Measures |
|---|---|
| Message alignment | Does the image support what the copy says? |
| Audience match | Would the target audience connect with this pairing? |
| Emotional consistency | Do copy tone and image mood match? |
| Brand coherence | Do they feel like one brand together? |

**Below 6 on any dimension = incoherent.** Coherence score feeds Pareto selection (60% weight).

#### 4.6.6 Image Feedback Loop — Targeted Regeneration

When all 3 variants fail attribute checklist:
1. Diagnose weakest attribute across all 3 variants
2. Append diagnostic to visual prompt (e.g., "no distortions, warmer lighting, add brand teal")
3. Generate 2 regen variants (cost-conscious retry)
4. Re-evaluate via attribute checklist + coherence

When best variant fails coherence only:
1. Append fix_suggestion from coherence checker to visual prompt
2. Generate 1 targeted regen variant
3. Re-check coherence

**Hard cap: 5 total images per ad.** Exhausted budget → flag as "image-blocked" for human review.

#### 4.6.7 Full Ad Assembly

Each published ad assembled as:
```json
{
  "ad_id": "ad_001",
  "copy": { "primary_text": "...", "headline": "...", "description": "...", "cta_button": "Learn More" },
  "image": {
    "winner": { "file": "ad_001_v2.png", "variant_type": "tone_shift", "composite_score": 8.7 },
    "all_variants": [
      { "file": "ad_001_v1.png", "variant_type": "anchor", "attribute_score": 0.8, "coherence": 7.2, "composite": 7.48 },
      { "file": "ad_001_v2.png", "variant_type": "tone_shift", "attribute_score": 0.9, "coherence": 8.1, "composite": 8.7 },
      { "file": "ad_001_v3.png", "variant_type": "composition_shift", "attribute_score": 0.7, "coherence": 6.8, "composite": 6.88 }
    ]
  },
  "scores": { "text_aggregate": 7.8, "visual_pass_pct": 90, "coherence_avg": 8.1 },
  "meta": { "audience": "Parents", "campaign_goal": "conversion", "cycle": 3, "regen_count": 1 }
}
```

#### 4.6.8 Cost Economics

| Scenario | Images | Cost (Google Direct) | Cost (Third-Party) |
|---|---|---|---|
| 50 ads × 3 variants | 150 | ~$20.10 | ~$3.00–7.50 |
| + regen (~20% failure) | +30 | ~$4.02 | ~$0.60–1.50 |
| + extra aspect ratios (winners only) | +76 | ~$10.18 | ~$1.52–3.80 |
| **Total** | **~256** | **~$34.30** | **~$5.12–12.80** |

#### 4.6.9 Meta-Ready Output Specs

| Placement | Aspect Ratio | Min Resolution | Format |
|---|---|---|---|
| Feed | 1:1 | 1080×1080 | JPG/PNG |
| Feed (tall) | 4:5 | 1080×1350 | JPG/PNG |
| Stories/Reels | 9:16 | 1080×1920 | JPG/PNG |

---

### 4.7 Application Layer Architecture — Sessions, Auth & Real-Time UX

#### 4.7.1 Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend API | FastAPI (Python) | Same language as pipeline (R5-Q7) |
| Frontend | React (Vite) | Dashboard already in React (R5-Q7) |
| Database | PostgreSQL | Session metadata, user accounts, curation state (R5-Q7) |
| Background Jobs | Celery + Redis | Long-running pipeline runs (R5-Q4) |
| Auth | Google SSO | @nerdy.com domain restriction (R5-Q5) |
| Real-Time Updates | Server-Sent Events (SSE) | Live progress streaming (R5-Q4) |
| Deployment | Single cloud VM, Docker Compose | Railway or Render. `git push` deployment (R5-Q10) |

#### 4.7.2 Session Model

A session is one pipeline run — immutable after completion (R5-Q1).

```json
{
  "session_id": "sess_20260313_a7f2",
  "user_id": "user_google_sso_id",
  "created_at": "2026-03-13T14:32:00Z",
  "status": "completed",
  "config": {
    "product": "SAT Prep",
    "audience": "Parents",
    "campaign_goal": "conversion",
    "ad_count": 50,
    "cycle_count": 5,
    "quality_threshold": 7.0,
    "dimension_weights": "conversion_profile",
    "model_tier": "standard",
    "budget_cap_usd": 25.00,
    "image_enabled": true,
    "aspect_ratios": ["1:1"]
  },
  "results_summary": {
    "ads_generated": 50,
    "ads_published": 38,
    "pass_rate": 0.76,
    "avg_text_score": 7.82,
    "avg_visual_score_pct": 91,
    "avg_coherence": 8.4,
    "total_cost_usd": 15.62,
    "cost_per_published_ad": 0.41,
    "cycles_completed": 5,
    "score_lift": 1.34
  },
  "ledger_path": "data/sessions/sess_20260313_a7f2/ledger.jsonl",
  "output_path": "data/sessions/sess_20260313_a7f2/output/"
}
```

#### 4.7.3 Session List (Home Screen)

Flat reverse-chronological card list (R5-Q2). Each card: session name, date, audience/goal badges, ad count, avg score, visual score, cost/ad, quality sparkline, status badge. Filters by audience, goal, date range, status. Running sessions show progress badge updated every 30s.

#### 4.7.4 New Session — Brief Configuration

Progressive disclosure form (R5-Q3):

**Required (always visible):** Audience, Campaign Goal, Ad Count (default 50).

**Advanced (accordion):** Cycle count, quality threshold override, dimension weights, model tier, budget cap, image toggle, aspect ratios, UGC video toggle (v2), video budget cap, video audio mode, custom brand voice notes, reference ad upload.

**Clone-from-previous** button for repeat users.

#### 4.7.5 Progress Monitoring — Hybrid Model

**Background (default):** Session list polls every 30s. "Running" badge with cycle progress.

**"Watch Live" (optional):** SSE-powered dashboard: cycle indicator, ads generated progress bar, live score feed, running cost accumulator, live quality trend chart, latest ad preview.

**On completion:** Status flips to "Completed," in-app notification, session card updates with final metrics.

#### 4.7.6 Session Detail — Dashboard Integration

Existing dashboard IS the session detail view (R5-Q8). Click session → land on Overview → navigate 7 tabs. Breadcrumb nav + back button.

#### 4.7.7 Curation Layer

Immutable generation + mutable curation (R5-Q6):
1. **Select** ads for curated set
2. **Reorder** within curated set
3. **Annotate** — add notes per ad
4. **Light edit** — minor copy polish with before/after diff tracking
5. **Export** curated set as Meta-ready zip

Dashboard metrics always reflect original pipeline output, never curated edits.

#### 4.7.8 Authentication & Authorization

Google OAuth 2.0 with @nerdy.com domain restriction (R5-Q5). Per-user session isolation. Share session via read-only time-limited link. v1: flat roles. v2: admin role.

#### 4.7.9 Deployment Architecture

```
┌──────────────────────────────────────────────────┐
│  Docker Compose (Single VM — Railway/Render)     │
│                                                   │
│  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  Nginx       │  │  FastAPI                  │   │
│  │  (reverse    │──│  - REST API               │   │
│  │   proxy)     │  │  - SSE endpoint           │   │
│  │  + React     │  │  - Google SSO             │   │
│  │   (static)   │  │  - Pipeline orchestration │   │
│  └─────────────┘  └──────────────────────────┘   │
│                          │                         │
│  ┌─────────────┐  ┌──────────────────────────┐   │
│  │  PostgreSQL  │  │  Celery Worker            │   │
│  │  - Users     │  │  - Background pipeline    │   │
│  │  - Sessions  │  │    execution              │   │
│  │  - Curation  │  │  - Progress reporting     │   │
│  └─────────────┘  └──────────────────────────┘   │
│                          │                         │
│                   ┌──────────────────────────┐   │
│                   │  Redis                    │   │
│                   │  - Celery broker          │   │
│                   │  - SSE pub/sub            │   │
│                   └──────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

Estimated cost: $20–50/month. Deployment: `git push` → auto-build → deploy with HTTPS.

#### 4.7.10 Frontend Implementation Spec — Mockup-to-Production Handoff

Reference file: `NerdyAdGen_Dashboard_v3.jsx` (1,341 lines). This is the pixel-perfect design spec.

**Design system tokens:**

| Token | Value | Usage |
|---|---|---|
| ink | #202344 | Primary background |
| surface | #161c2c | Card backgrounds |
| cyan | #17e2ea | Hero color, CTAs, active states |
| mint | #35dd8b | Success states |
| lightPurple | #a488f7 | Video elements |
| yellow | #ffcb19 | Warning, cost metrics |
| red | #ff4e00 | Danger states |
| Font | Poppins | All UI text |
| Card radius | 24px | All cards |
| Button radius | 100px | All pill buttons |

**Component decomposition:**

```
src/
├── design/tokens.js           ← N object, gradients, FONT
├── components/
│   ├── Card.jsx, Badge.jsx, Metric.jsx, GradientText.jsx
│   ├── CTAButton.jsx, ImagePlaceholder.jsx
│   ├── Sparkline.jsx, ProgressBar.jsx, NerdyLogo.jsx
├── views/
│   ├── SessionList.jsx        ← Home screen
│   ├── NewSessionForm.jsx     ← Brief config
│   └── SessionDetail.jsx      ← Tab router for 7 tabs
├── tabs/
│   ├── Overview.jsx, Quality.jsx, AdLibrary.jsx
│   ├── CompetitiveIntel.jsx, TokenEconomics.jsx
│   ├── CuratedSet.jsx, SystemHealth.jsx
├── api/
│   ├── sessions.js, curation.js, sse.js
└── App.jsx                    ← Router
```

**Data wiring:**

| Mock Data | Production API | Notes |
|---|---|---|
| sessions array | GET /api/sessions | Paginated, filterable |
| heroMetrics | GET /api/sessions/:id/summary | From decision ledger |
| cycleData | GET /api/sessions/:id/cycles | Per-cycle aggregation |
| dimOverTime | GET /api/sessions/:id/dimensions | Dimension scores per cycle |
| costData | GET /api/sessions/:id/costs | Token attribution output |
| sampleAds | GET /api/sessions/:id/ads | Full ad objects with media |
| compIntel | GET /api/competitive/summary | Pattern database |
| spcData | GET /api/sessions/:id/spc | SPC control chart data |
| curatedAds | GET /api/sessions/:id/curated | Curation state |
| SSE stream | GET /api/sessions/:id/progress (SSE) | Real-time progress |

---

### 4.8 Competitive Intelligence Architecture — Meta Ad Library Pattern Extraction

#### 4.8.1 Why Semi-Automated

No public API for commercial ads on Meta Ad Library. Automated scraping blocked. Semi-automated via Claude in Chrome: human browses, AI extracts structured patterns.

#### 4.8.2 Target Competitors

Varsity Tutors (own ads), Kaplan, Princeton Review, Khan Academy, Chegg, Sylvan Learning.

#### 4.8.3 Pattern Record Schema

```json
{
  "competitor": "Kaplan",
  "ad_id": "kaplan_001",
  "observed_date": "2026-03-10",
  "copy_patterns": {
    "hook_type": "fear",
    "value_prop_structure": "outcome_guarantee",
    "cta_style": "free_trial",
    "emotional_register": "anxiety_to_relief",
    "specificity_level": "high",
    "social_proof": true,
    "word_count": 45
  },
  "visual_patterns": {
    "creative_type": "static_image",
    "visual_style": "studio_polished",
    "subject": "student_studying",
    "color_dominant": "blue",
    "text_overlay": true
  },
  "structural": {
    "formula": "pain_point → solution → proof → cta",
    "differentiator": "price_anchoring",
    "weakness": "generic_cta"
  }
}
```

#### 4.8.4 Chrome Research Workflow

1. Open Meta Ad Library filtered to competitor
2. Claude in Chrome analyzes visible ads using extraction prompt
3. Output: JSON array of pattern records + competitor strategy summary
4. Save to `data/competitive/patterns.json`
5. Repeat for each competitor (~15 min per competitor, ~90 min total)

#### 4.8.5 Extraction Prompt

Full prompt available in standalone file: `Competitive_Analysis_Chrome_Prompt.md`

#### 4.8.6 Pipeline Integration Points

1. **Brief expansion (P1-01):** Inject top competitive patterns as "landscape context"
2. **Generation (P1-02):** Reference-decompose-recombine draws from competitive structural atoms
3. **Evaluation (P1-04):** Differentiation nudge — evaluator flags if generated ad is too similar to top competitor pattern

#### 4.8.7 Competitive Dashboard Panel

Hook type distribution (our ads vs. competitors), strategy radar chart, gap analysis cards with opportunity flags.

#### 4.8.8 Maintenance

Monthly refresh recommended. Track temporal trends (strategy shifts over time).

---

### 4.9 UGC Video Architecture — Veo Integration

#### 4.9.1 Why Veo

Google Veo 3.1 Fast. Same ecosystem as Gemini/Nano Banana Pro — single API key. Native audio generation. Optimized for programmatic ad generation. 1080p, 9:16 for Stories/Reels. ~$0.15/sec ($0.90/6-sec video with audio, $0.60 silent).

#### 4.9.2 Video Spec Extraction

From expanded brief, extract:
- Scene description: setting, subjects, action
- Pacing: fast-cut UGC vs. testimonial-style
- Camera style: handheld/authentic vs. steady
- Audio direction: voiceover script (from ad copy) or ambient
- Text overlay sequence: hook → value prop → CTA timing
- Opening hook: first 2 seconds must stop the scroll
- Duration: 6 seconds default (Stories/Reels sweet spot)

#### 4.9.3 Video Generation Pipeline

Generate 2 variants per ad:
1. **Anchor variant** — straight interpretation of video spec
2. **Alternative variant** — different scene/pacing/camera approach

Evaluate both. Select best by composite score. Graceful degradation: if video fails, ad publishes with copy + image only.

#### 4.9.4 Video Attribute Checklist (10 Attributes)

| # | Attribute | Type | Pass Criteria |
|---|---|---|---|
| 1 | Hook timing | Required | Attention-grabbing element in first 2 seconds |
| 2 | UGC authenticity | Required | Feels genuine, not overproduced |
| 3 | Pacing | Required | Matches campaign energy (fast for conversion, measured for awareness) |
| 4 | Subject appearance | Required | Age/demo appropriate, no uncanny valley |
| 5 | Text overlay legibility | Required | Readable at mobile size throughout |
| 6 | Brand safety | Required | No competitor refs, no inappropriate content |
| 7 | Audio quality | Conditional | If audio: clear, natural speech. If silent: effective text/music |
| 8 | CTA placement | Required | CTA visible in final 1.5 seconds |
| 9 | Aspect ratio | Required | 9:16 for Stories/Reels |
| 10 | No AI artifacts | Required | No facial distortion, temporal glitches, or physics violations |

Pass: All Required pass.

#### 4.9.5 Script-Video Coherence

4 dimensions: message alignment, audience match, emotional consistency, narrative flow. Below 6 = incoherent → targeted regen.

#### 4.9.6 Cost Economics

| Scenario | Videos | Cost |
|---|---|---|
| 50 ads × 2 variants (audio) | 100 | ~$90.00 |
| 50 ads × 2 variants (silent) | 100 | ~$60.00 |
| + regen (~15%) | +15 | ~$9.00–13.50 |
| **Total (audio)** | **~115** | **~$103.50** |
| **Total (silent)** | **~115** | **~$69.00** |

Budget cap in brief config (default $20) prevents runaway costs. Video defaults to off.

#### 4.9.7 Three-Format Ad Assembly

Published ads contain: copy JSON + winning image + winning video (where enabled). Meta placement mapping: feed → image (1:1 or 4:5), Stories/Reels → video (9:16) or image fallback.

#### 4.9.8 Dashboard Integration

Ad Library cards show video badge + video score. Token Economics tracks text + image + video cost separately. System Health escalation log includes video regen events.

---

## 5. Quality Evaluation Framework

### 5.1 Five Quality Dimensions

| Dimension | What It Measures | Score 1 (Bad) | Score 10 (Excellent) |
|---|---|---|---|
| Clarity | Message immediately understandable? | Confusing, competing messages | Crystal clear single takeaway in <3 seconds |
| Value Proposition | Compelling, specific benefit? | Generic ("we have tutors") | Differentiated ("raise SAT score 200+ points") |
| Call to Action | Next step clear and compelling? | No CTA or vague ("learn more") | Specific, urgent ("Start free practice test") |
| Brand Voice | Sounds like Varsity Tutors? | Generic, could be anyone | Distinctly on-brand: empowering, knowledgeable |
| Emotional Resonance | Connects emotionally? | Flat, purely rational | Taps parent worry, student ambition, test anxiety |

### 5.2 Weighting Strategy

Campaign-goal-adaptive weights (R1-Q3) with floor constraints:

| Dimension | Awareness Weight | Conversion Weight | Floor Score |
|---|---|---|---|
| Clarity | 25% | 25% | 6.0 (hard minimum) |
| Value Proposition | 20% | 25% | None |
| Call to Action | 10% | 30% | None |
| Brand Voice | 20% | 10% | 5.0 (hard minimum) |
| Emotional Resonance | 25% | 10% | None |

### 5.3 Evaluation Prompt Design

Chain-of-thought structured evaluation (R3-Q6) — five-step sequence:
1. Read the ad
2. Identify the hook, value proposition, CTA, and emotional angle before scoring
3. Compare against rubric calibration examples (1-score and 10-score)
4. Score with contrastive rationale: what the ad is, what +2 would look like, the specific gap (R3-Q10)
5. Flag any dimension where confidence < 7/10 (feeds confidence-gated autonomy, R2-Q5)

### 5.4 Quality Ratchet

Rolling high-water mark (R1-Q9): `effective_threshold = max(7.0, rolling_5batch_average − 0.5)`. The quality bar only goes up. The 7.0 absolute floor is immutable.

---

## 6. Project Phases & Tickets

### Phase 0: Foundation & Calibration (Day 0–1)

| Ticket | Title | Description | Acceptance Criteria |
|---|---|---|---|
| P0-01 | Project scaffolding | Initialize repo with directory structure. Create requirements.txt, config.yaml, README. | One-command setup runs without errors |
| P0-02 | Append-only decision ledger | Implement JSONL event logger (R2-Q8) with standardized schema. | Events written; pandas can filter by ad_id |
| P0-03 | Per-ad seed chain + snapshots | seed = hash(global_seed + brief_id + cycle_number) (R3-Q4). Full I/O snapshots. | Same seed + brief_id + cycle = same seed |
| P0-04 | Brand knowledge base | Verified facts file for Varsity Tutors from assignment spec + reference ads (R3-Q5). | Covers SAT prep audience; no invented facts |
| P0-05 | Reference ad collection | 20–30 VT + 20–30 competitor ads. Label 5–10 excellent and 5–10 poor. | Labeled reference set ready |
| P0-06 | Evaluator cold-start calibration | Run CoT evaluator against labeled reference ads (R1-Q8). Tune until calibrated. | Scores within ±1.0 of human labels on 80%+ |
| P0-07 | Golden set regression tests | 15–20 golden ads with human-assigned scores (R2-Q3). Automated test suite. | Test suite passes regression within ±1.0 |
| P0-08 | Checkpoint-resume infrastructure | Every successful API call writes checkpoint_id (R3-Q2). Resume from last checkpoint. | --resume flag works; no duplicated work |
| P0-09 | Competitive pattern database — initial scan | Use Claude in Chrome to analyze 6 competitors via Meta Ad Library (Section 4.8.4). Extract structured pattern records. | Pattern records for 6 competitors; JSON validates |
| P0-10 | Competitive pattern query interface | Utility function to query pattern database by audience, goal, hook type, competitor. | query_patterns() returns ranked results |

### Phase 1: Full-Ad Pipeline — v1 Copy + Image (Days 1–4)

| Ticket | Title | Description | Acceptance Criteria |
|---|---|---|---|
| P1-01 | Brief expansion engine | LLM expansion with grounding (R3-Q5). Inject competitive context from pattern database (Section 4.8.6). | No hallucinated claims; competitive context included |
| P1-02 | Ad copy generator | Reference-decompose-recombine (R2-Q1). Produces primary text, headline, description, CTA. | All 4 components generated |
| P1-03 | Audience-specific brand voice profiles | Parent-facing + Student-facing with few-shot examples (R1-Q6). | Correct profile selected per audience |
| P1-04 | Chain-of-thought evaluator | 5-step evaluation prompt (R3-Q6) with contrastive rationales (R3-Q10). | Per-dimension scores + rationales + confidence flags |
| P1-05 | Campaign-goal-adaptive weighting | Awareness vs. conversion profiles. Clarity ≥ 6.0, Brand Voice ≥ 5.0 floors (R1-Q3). | Correct weights per goal; floor violations → rejection |
| P1-06 | Tiered model routing | <5.5 discarded, >7.0 published, 5.5–7.0 escalated (R1-Q4). | Token spend concentrated on improvable range |
| P1-07 | Pareto-optimal regeneration | 3–5 variants per cycle; select Pareto-dominant (R1-Q5). | No dimension regressed vs. prior cycle |
| P1-08 | Brief mutation + escalation | After 2 failures: mutate. After 3: escalate with diagnostics (R1-Q2). | Mutation logged; escalation triggers on third failure |
| P1-09 | Distilled context objects | Compact distillation per cycle (R2-Q4). | Prompt stays compact regardless of depth |
| P1-10 | Quality ratchet | Rolling high-water mark: max(7.0, rolling_5batch_avg − 0.5) (R1-Q9). | Threshold only increases |
| P1-11 | Token attribution engine | Tag every API call (R1-Q7). Cost-per-publishable-ad + marginal gain. | Dashboard shows spend by stage |
| P1-12 | Result-level cache | hash(ad_text + evaluator_prompt_version) (R3-Q7). Invalidate on recalibration. | Cache hits on resume; recalibration clears all |
| P1-13 | Batch-sequential processor | Batches of 10, parallel within stage, sequential across (R3-Q9). | 50+ ads processed; batch boundaries = checkpoints |
| P1-14 | Nano Banana Pro integration + multi-variant generation | 3 image variants per ad (anchor, tone shift, composition shift). Aspect ratio routing. | 3 variants generated per ad; all logged |
| P1-15 | Visual attribute evaluator + Pareto image selection | Binary attribute checklist (10 attributes). 80% pass. Pareto selection by composite score. | Each variant scored; best selected; losers logged |
| P1-16 | Text-image coherence checker | 4-dimension coherence. Below 6 = incoherent. Feeds Pareto selection (60% weight). | Coherence scores logged for all variants |
| P1-17 | Image targeted regen loop | All 3 fail → diagnose + 2 regen. Coherence-only fail → 1 regen. Max 5 per ad. (Section 4.6.6) | Regen triggers; capped at 5; image-blocked ads logged |
| P1-18 | Full ad assembly + export | Copy JSON + winning image + variant metadata. Meta-ready file naming. | Each published ad has copy + winning image |
| P1-19 | Image cost tracking | Per-image, per-variant, per-regen, per-aspect-ratio costs. Variant win rates. | Dashboard shows text + image cost breakdown |
| P1-20 | 50+ full ad generation run | Full pipeline: 5+ batches, 3+ cycles. 50+ full ads meeting both thresholds. | Quality trend shows improvement; variant metadata logged |

### Phase 1B: Application Layer (Days 3–5)

| Ticket | Title | Description | Acceptance Criteria |
|---|---|---|---|
| PA-01 | FastAPI backend scaffold | FastAPI + CORS + PostgreSQL + Celery + Redis. Docker Compose. (R5-Q7, R5-Q10) | docker compose up starts all services |
| PA-02 | Database schema — users & sessions | PostgreSQL tables: users, sessions, curated_sets. (R5-Q1, R5-Q5) | Migrations run; schema matches Section 4.7.2 |
| PA-03 | Google SSO authentication | Google OAuth 2.0. @nerdy.com restriction. JWT tokens. (R5-Q5) | Only @nerdy.com emails can sign in |
| PA-04 | Session CRUD API | POST /sessions, GET /sessions, GET /sessions/:id. (R5-Q1, R5-Q2) | Session creation triggers Celery job; list supports filters |
| PA-05 | Brief configuration form (React) | Progressive disclosure (R5-Q3). Clone-from-previous. | Form submits to POST /sessions; clone works |
| PA-06 | Session list UI (React) | Flat reverse-chronological cards (R5-Q2). Sparklines, badges, filters. | Cards render with metadata; running sessions show progress |
| PA-07 | Background job progress reporting | Celery writes to Redis pub/sub. FastAPI SSE endpoint. Session list polls 30s. (R5-Q4) | Running sessions update in real time |
| PA-08 | "Watch Live" progress view (React) | Cycle indicator, ad count bar, live score feed, cost accumulator, trend chart, latest ad preview. SSE. (R5-Q4) | All 6 elements update in real time |
| PA-09 | Session detail — dashboard integration | Wrap 7-tab dashboard in session context. Breadcrumbs, back button. Scope data to session ledger. (R5-Q8, Section 4.7.10) | Clicking session opens dashboard filtered to that session |
| PA-10 | Curation layer + Curated Set tab | 7th tab. Select, reorder, annotate, light edit with diff tracking. Export zip. (R5-Q6) | Selections persist; edits tracked; export produces Meta-ready zip |
| PA-11 | Share session link | Read-only URL with time-limited token. (R5-Q5) | Shared link opens read-only session; token expires 7 days |
| PA-12 | Docker Compose production deployment | Nginx + static React + FastAPI + PostgreSQL + Celery + Redis. Auto-HTTPS. (R5-Q10) | docker compose -f docker-compose.prod.yml up serves full app |
| PA-13 | Frontend component build — mockup-to-production | Decompose NerdyAdGen_Dashboard_v3.jsx per Section 4.7.10. Extract tokens. Split views/tabs. Wire API. Wire SSE. | All views match mockup; zero mock data; SSE works; Lighthouse a11y ≥ 80 |

### Phase 2: Testing & Validation (Days 3–4)

| Ticket | Title | Description | Acceptance Criteria |
|---|---|---|---|
| P2-01 | Inversion tests | Degrade one dimension at a time (R2-Q3). | 10+ tests; degraded drops ≥1.5, others stable ±0.5 |
| P2-02 | Correlation analysis | Pairwise correlation across 5 dimensions. Flag r > 0.7 (R2-Q3). | Matrix generated; no pair exceeds 0.7 |
| P2-03 | Adversarial boundary tests | Edge cases: perfect Clarity + zero Brand Voice, wrong brand (R2-Q3). | 8+ tests pass |
| P2-04 | SPC drift detection | Statistical process control on evaluator distributions (R1-Q1). Canary injection. | Control charts plotted; canary fires on simulated drift |
| P2-05 | Confidence-gated autonomy | Confidence flags → routing: >7 autonomous, 5–7 flagged, <5 human (R2-Q5). | Correct routing per confidence level |
| P2-06 | Tiered compliance filter | 3 layers: prompt + evaluator + regex (R3-Q3). | Known-bad ads caught; zero false negatives |
| P2-07 | End-to-end integration test | Full pipeline with checkpoint-resume: start, kill, resume (R3-Q2). | Resumed run = identical output |

### Phase 3: A/B Variant Engine + UGC Video — v2 (Days 4–7)

| Ticket | Title | Description | Acceptance Criteria |
|---|---|---|---|
| P3-01 | Nano Banana 2 integration (cost tier) | Gemini 3.1 Flash Image for variant volume. | Both models producing; cost tracked separately |
| P3-02 | Single-variable A/B variants — copy | Control + 3 copy variants changing one element (R2-Q6). | Winning patterns identified per segment |
| P3-03 | Single-variable A/B variants — image | Same copy + 3 image variants. Isolate visual impact. | Image variants produced; coherence compared |
| P3-04 | Image style transfer experiments | Different styles per audience. | Style-audience mapping documented |
| P3-05 | Multi-model orchestration doc | Which model does what and why (R1-Q4). Cost attribution across text + image + video. | Architecture doc with rationale across 3 formats |
| P3-06 | Multi-aspect-ratio batch generation | For published ads: 1:1, 4:5, 9:16 variants. | All 3 ratios per published ad; all pass checklist |
| P3-07 | Veo integration + video spec extraction | Veo 3.1 Fast API. Video spec from briefs (Section 4.9.2). 2 variants per ad. | Videos generated; specs logged; 2 variants produced |
| P3-08 | Video attribute evaluator | 10-attribute checklist (Section 4.9.4). | Each attribute scored; failures logged |
| P3-09 | Script-video coherence checker | 4-dimension coherence (Section 4.9.5). Below 6 = incoherent. | Coherence logged; incoherent pairs trigger regen |
| P3-10 | Video Pareto selection + regen loop | Best of 2 variants. Targeted regen (1 retry, max 3 total). Graceful degradation. | Best selected; failures fall back to image-only |
| P3-11 | Three-format ad assembly | Copy + image + video. Meta placement mapping (Section 4.9.7). | Published ads contain all formats where enabled |
| P3-12 | Video cost tracking | Per-video, per-variant, per-regen, audio vs. silent costs. | Dashboard shows 3-format cost breakdown |
| P3-13 | 10-ad video pilot run | 10 ads with video, 2 variants each. Verify attributes, coherence, degradation. | 10 ads with video; failures degrade to image-only |

### Phase 4: Autonomous Engine — v3 (Days 7–14)

| Ticket | Title | Description | Acceptance Criteria |
|---|---|---|---|
| P4-01 | Agentic orchestration layer | Researcher → Writer → Editor → Evaluator with error boundaries (R3-Q1). | Failures contained; diagnostics logged |
| P4-02 | Self-healing feedback loop | Wire: SPC + brief mutation + quality ratchet + explore trigger. | Simulated drop detected, diagnosed, recovered |
| P4-03 | Competitive intelligence — automated refresh + trends | Monthly refresh workflow, temporal trend tracking, seasonal analysis. | Trends visible in dashboard; strategy shift alerts |
| P4-04 | Cross-campaign transfer | Shared structural patterns + isolated content (R3-Q8). | Insights transferable via campaign_scope tags |
| P4-05 | Performance-decay exploration trigger | Exploit by default, explore on plateau (R2-Q9). | Exploration triggers; successful patterns promoted |
| P4-06 | Full marginal analysis engine | Quality gain per regen attempt, per model, per dimension (R1-Q7). | System caps low-marginal-return regeneration |
| P4-07 | Narrated pipeline replay | Chronological replay from decision ledger (R2-Q10). Failures highlighted. | Full walkthrough with reasoning |

### Phase 5: Dashboard, Documentation & Submission (Days 12–14)

| Ticket | Title | Description | Acceptance Criteria |
|---|---|---|---|
| P5-01 | Dashboard data export script | export_dashboard.py reads JSONL, aggregates into dashboard_data.json for all 8 panels. | Script runs; JSON contains all panel data |
| P5-02 | Dashboard HTML — Pipeline Summary + Iteration Cycles | Panels 1–2: hero KPIs, per-cycle before/after cards. | All 8 hero metrics render; cycle cards show before/after |
| P5-03 | Dashboard HTML — Quality Trends + Dimension Deep-Dive | Panels 3–4: score progression, dimension lines, correlation heatmap, ratchet line. | 4 chart views toggle; r > 0.7 flagged red |
| P5-04 | Dashboard HTML — Ad Library | Panel 5: filterable browser, per-ad cards with scores, expandable rationales, before/after pairs. | All 50+ ads browsable; rationales expand |
| P5-05 | Dashboard HTML — Token Economics | Panel 6: cost attribution, cost-per-ad trend, marginal analysis, model routing, projected cost. | All 6 sub-panels render |
| P5-06 | Dashboard HTML — System Health + Competitive Intel | Panels 7–8: SPC charts, confidence, escalation, compliance, competitor patterns. | SPC renders; ratchet monotonically increasing |
| P5-07 | Decision log | Every major choice as ADR + narrative reflection (R4-Q9). | Covers all major choices; honest about failures |
| P5-08 | Technical writeup (1–2 pages) | Architecture, methodology, key findings, quality trends, per-token results. | Concise; covers all areas |
| P5-09 | Demo video (7 min, Problem-Solution-Proof) | Act 1: naive fails. Act 2: architecture. Act 3: before/after + dashboard. (R4-Q5) | ≤ 7 minutes; shows dashboard in Act 3 |
| P5-10 | Generated ad library export | 50+ ads with full scores, rationales, lifecycle as JSON/CSV. | Complete metadata; filterable |
| P5-11 | README with one-command setup | Setup, usage, configuration, architecture, dashboard launch. | New developer runs pipeline + dashboard in < 5 minutes |

---

## 7. Success Criteria & Rubric Alignment

### 7.1 Quantitative Targets

| Category | Metric | Target | Tickets |
|---|---|---|---|
| Full ads (copy + image) | With evaluation | 50+ | P1-20 |
| Text Dimensions | Independently measured | 5, proven independent | P1-04, P2-01, P2-02 |
| Visual Quality | Image attribute pass rate | ≥80% on all published ads | P1-15 |
| Text-Image Coherence | Coherence score | ≥6/10 on all published ads | P1-16 |
| Text Quality | Ads meeting 7.0/10 threshold | Majority of final output | P1-07, P1-10 |
| Improvement | Quality gain over cycles | Measurable lift across 3+ | P1-10, P1-20 |
| Explainability | Evaluations with rationales | 100% (text + visual) | P1-04, P1-15 |
| Documentation | Decision log with reasoning | Complete and honest | P5-07 |
| Tests | Unit/integration | ≥10 (targeting 15+) | P0-07, P2-01–P2-07 |
| Reproducibility | Deterministic runs | Seed-based + snapshot replay | P0-03 |
| Application Layer | Multi-session internal tool | Auth + session CRUD + progress + curation | PA-01–PA-13 |
| Session Model | Immutable, reproducible | One session = one pipeline run | PA-02, PA-04 |
| Deployment | One-command production deploy | Docker Compose on single VM | PA-12 |

### 7.2 Rubric Weight Alignment

| Rubric Area (Weight) | Target | How This PRD Addresses It |
|---|---|---|
| Quality Measurement (25%) | 23–25 (Excellent) | 5 independent dimensions, CoT evaluation, calibrated, confidence scoring, ratchet, documented weighting |
| System Design (20%) | 18–20 (Excellent) | Modular structure, checkpoint-resume, 15+ tests, deterministic seeds, context distillation |
| Iteration (20%) | 18–20 (Excellent) | 5+ cycles, documented causation, marginal analysis, performance-per-token |
| Speed (15%) | 14–15 (Excellent) | Batch-parallel, tiered routing, caching, smart exploration |
| Documentation (20%) | 18–20 (Excellent) | Decision log, narrated replay, honest limitations, visible reasoning |

### 7.3 Bonus Points Targeted

| Achievement | Points | Ticket |
|---|---|---|
| Self-healing / automatic quality improvement | +7 | P4-02 |
| Multi-model orchestration with clear rationale | +3 | P1-06, P1-14, P3-05, P3-07 |
| Performance-per-token tracking | +2 | P1-11, P4-06 |
| Quality trend visualization | +2 | P5-03 |
| Competitive intelligence from Meta Ad Library | +10 | P0-09, P0-10, P1-01, P4-03 |

**Total bonus targeted: +24 points**

---

## 8. Risk Register

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| Evaluator halo effect | High | Medium | Inversion tests (P2-01) + correlation analysis (P2-02). CoT decomposition. |
| API rate limits cause stalls | Medium | High (free tier) | Checkpoint-resume (P0-08) + fixed delays. Batch sizing. |
| Feedback loop oscillation | High | Medium | Pareto-optimal selection (P1-07). |
| Evaluator drift over long runs | Medium | Low-Medium | SPC monitoring (P2-04) with canary injection. |
| Brief expansion hallucination | High | Medium | Grounding constraints (P1-01) + compliance filter (P2-06) + regex. |
| Cold-start bad batch | High | Low | Evaluator calibrated before first generation (P0-06). |
| Token budget overrun | Medium | Medium | Attribution (P1-11) + marginal analysis (P4-06) + caching (P1-12) + tiered routing. |
| Insufficient reference ads | Medium | Medium | Supplement with Meta Ad Library competitor ads (P0-05). |
| Nano Banana Pro rate limits | Medium | Medium | Batch requests; generate after text triage. Cache by visual spec hash. |
| AI image artifacts | High | Low-Medium | Multi-variant (3 per ad). Attribute checklist catches. Targeted regen fallback. |
| Text-image incoherence | Medium | Low-Medium | Coherence checker on all 3 variants. Shared semantic brief prevents by design. |
| Image cost overrun at scale | Medium | Medium | 3 variants = 3x cost. Extra ratios for winners only. Budget tier. Third-party providers. |
| Variant selection bias | Low | Medium | Track win rates. If >80% dominant, adjust defaults. |
| Veo video quality inconsistency | Medium | Medium | UGC aesthetic forgiving. Attribute checklist catches. Graceful degradation. |
| Video cost overrun | High | Medium | Budget cap (default $20). Silent mode saves 33%. 10-ad pilot first. Defaults to off. |
| Veo API rate limits | Medium | Low-Medium | Pipeline generates video after image selection. Checkpoint-resume covers failures. |
| SynthID watermark concerns | Low | Low | SynthID imperceptible. Meta does not reject. Document in decision log. |
| App layer delays pipeline | Medium | Medium | Phase 1B runs parallel with Phase 2. Pipeline stays CLI-testable. |
| Celery worker crash | Medium | Low | Checkpoint-resume applies at app layer. Sessions restart from last checkpoint. |
| SSE connection drops | Low | Medium | Frontend auto-reconnects. Session list polling as fallback. No data loss. |
| Curation edits conflate with metrics | Medium | Low | Strict separation. Dashboard reads immutable session data. Curated Set tab labels both states. |

---

## 9. Technical Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Gemini API (Flash + Pro) | External API | Free tier; 15 RPM (Flash), 2 RPM (Pro) |
| Nano Banana Pro (Gemini 3 Pro Image) | External API (v1) | ~$0.13/image. Google AI Studio API key. |
| Nano Banana 2 (Gemini 3.1 Flash Image) | External API (v2) | ~$0.02–0.05/image via third-party |
| Veo 3.1 Fast (Google) | External API (v2) | ~$0.15/sec (~$0.90/6-sec video). Same API key. |
| Meta Ad Library | Public data | Free; no API — semi-automated collection |
| Reference ads from Slack | Internal data | Provided via Gauntlet/Nerdy Slack |
| Python 3.10+ | Runtime | Primary language |
| FastAPI | Backend framework | Application layer API |
| React (Vite) | Frontend framework | Dashboard + session management |
| PostgreSQL | Database | Users, sessions, curation |
| Celery + Redis | Task queue | Background pipeline + SSE pub/sub |
| Google OAuth 2.0 | Auth provider | @nerdy.com SSO |
| Docker + Docker Compose | Deployment | Single-VM production |
| Claude in Chrome | Browser extension | Competitive intelligence extraction |
| pandas + matplotlib | Libraries | Ledger queries + visualization |

---

## 10. Ticket Summary

| Phase | Name | Tickets | Timeline |
|---|---|---|---|
| Phase 0 | Foundation & Calibration | 10 tickets (P0-01 – P0-10) | Day 0–1 |
| Phase 1 | Full-Ad Pipeline (v1: Copy + Image) | 20 tickets (P1-01 – P1-20) | Days 1–4 |
| Phase 1B | Application Layer (Sessions, Auth, UX) | 13 tickets (PA-01 – PA-13) | Days 3–5 |
| Phase 2 | Testing & Validation | 7 tickets (P2-01 – P2-07) | Days 3–4 |
| Phase 3 | A/B Variant Engine + UGC Video (v2) | 13 tickets (P3-01 – P3-13) | Days 4–7 |
| Phase 4 | Autonomous Engine (v3) | 7 tickets (P4-01 – P4-07) | Days 7–14 |
| Phase 5 | Dashboard, Docs & Submission | 11 tickets (P5-01 – P5-11) | Days 12–14 |
| **TOTAL** | | **81 tickets** | **14 days** |

---

## Recommended Build Order

**Pipeline track:** P0-03 (seed + snapshot) → P0-02 (decision ledger) → P0-09 (competitive scan — parallel, human-in-the-loop) → P0-10 (pattern query) → R3-Q6 (evaluation prompt) → P0-06 (cold-start calibration) → P1-01 (brief expansion) → P1-02 (copy generation) → P1-14 (Nano Banana Pro + multi-variant) → P1-15 (visual eval + Pareto) → P1-16 (coherence) → P1-17 (image regen loop) → P1-08 (text regen) → P1-07 (text Pareto) → P1-13 (batch processing) → P1-18 (full ad assembly) → everything else.

**Application track (parallel after P1-02):** PA-01 (FastAPI scaffold) → PA-02 (DB schema) → PA-03 (Google SSO) → PA-04 (Session CRUD) → PA-05 (brief config) → PA-06 (session list) → PA-07 (progress reporting) → PA-13 (frontend component build) → PA-09 (dashboard integration) → PA-10 (curation) → PA-12 (production deployment).

**Five load-bearing components:** the evaluation prompt (R3-Q6), the decision ledger (R2-Q8), the visual spec extraction pipeline (Section 4.6.2), the session model (Section 4.7.2), and the competitive pattern database (Section 4.8.3).

---

*End of Document*