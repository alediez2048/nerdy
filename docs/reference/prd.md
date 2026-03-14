Ad-Ops-Autopilot — Product Requirements Document
Autonomous Content Generation System for Facebook & Instagram
BrandVarsity Tutors (Nerdy)North Star MetricPerformance Per TokenScopev1 (Full-Ad Pipeline: Copy + Image) → v2 (A/B Variant Engine + UGC Video) → v3 (Autonomous Engine)Version1.0 — March 2026ClassificationCONFIDENTIAL

Table of Contents

Executive Summary
Problem Statement
Architectural Pillars
System Architecture Overview
4.5 Dashboard Architecture
4.6 Image Generation Architecture — Nano Banana Pro
4.7 Application Layer Architecture — Sessions, Auth & Real-Time UX
4.8 Competitive Intelligence Architecture — Meta Ad Library Pattern Extraction
4.9 UGC Video Architecture — Veo Integration
Quality Evaluation Framework
Project Phases & Tickets
Success Criteria & Rubric Alignment
Risk Register
Technical Dependencies
Ticket Summary


Part I: Assignment Requirements
The Challenge
Most AI-generated ad copy is mediocre. It reads like it was made by a machine, converts poorly, and costs more to produce than the value it creates.
Your challenge: Build an autonomous system that generates Facebook and Instagram ad copy, knows the difference between good and bad, surfaces only its best work, and measurably improves over time. The north star metric is performance per token — how much quality per dollar of API spend.
This is not a prompt engineering exercise. This is a systems engineering challenge: generate, evaluate, iterate, and improve — with minimal human intervention.
The domain is tight and closed: paid social ads for Facebook and Instagram. That's it. No email, no landing pages, no TikTok. One channel family, one content type, done well.
Why This Matters
Real ad engines produce thousands of creatives across campaigns. The ones that win share a pattern: most ads fail (the system that surfaces only its best work wins), quality is decomposable ("good ad copy" is really clarity + value proposition + CTA strength + brand voice + emotional resonance, each independently measurable), improvement compounds (a system that tracks what works and feeds it back gets better every cycle), and ROI is the real metric (not "did the AI generate something?" but "was it worth the tokens?").
What We're Really Evaluating
We're not testing whether you can make an API call. We're evaluating problem decomposition (can you break "generate good ads" into a system of measurable, improvable parts?), taste and judgment (do you know what good looks like? Can you teach a system to know?), creative agency (even if you don't know what good looks like, could you gather context strategically to build a working proof of concept?), systems thinking (does your system handle failure? Does it know when it's producing garbage?), and iteration methodology (what did you try, what worked, what didn't, and why?).
Your decision log matters as much as your output.
The Channel: Facebook & Instagram Paid Ads
What works on Meta right now: authentic > polished (UGC-style outperforms studio creative), story-driven > feature-list (pain point → solution → proof → CTA), pattern interrupts (scroll-stopping hooks in the first line), social proof (reviews, testimonials, numbers) builds trust, and emotional resonance > rational argument for awareness (flip for conversion).
Ad anatomy on Meta: Primary text (main copy above the image — stops the scroll), Headline (bold text below the image — short, punchy), Description (secondary text below headline — often truncated on mobile), CTA button ("Learn More", "Sign Up", "Get Started", etc.), Creative (image via Nano Banana Pro + UGC video via Veo — producing complete multi-format ready-to-publish ads covering feed, Stories, and Reels placements).
Quality Dimensions
Every generated ad gets scored across five dimensions:
DimensionWhat It MeasuresScore 1 (Bad)Score 10 (Excellent)ClarityIs the message immediately understandable?Confusing, multiple messages competingCrystal clear single takeaway in <3 secondsValue PropositionDoes it communicate a compelling benefit?Generic/feature-focused ("we have tutors")Specific, differentiated benefit ("raise your SAT score 200+ points")Call to ActionIs the next step clear and compelling?No CTA or vague ("learn more")Specific, urgent, low-friction ("Start your free practice test")Brand VoiceDoes it sound like the brand?Generic, could be anyoneDistinctly on-brand: empowering, knowledgeable, approachableEmotional ResonanceDoes it connect emotionally?Flat, purely rationalTaps into real motivation (parent worry, student ambition, test anxiety)
Quality threshold: 7.0/10 average to be considered publishable. Below that, the system should flag and regenerate.
Scope Variants
v1: Full-Ad Pipeline (1–3 days) — Complete ad generation: text copy + image creative via Nano Banana Pro. Ad copy generator from minimal briefs, LLM-as-judge evaluation scoring 5 text dimensions + visual attribute checklist, image generation from shared semantic briefs, text-image coherence verification, feedback loop (generate → evaluate → identify weakest dimension → targeted regeneration → re-evaluate), quality threshold enforcement (7.0/10 text minimum + 80% visual attribute pass). Demonstrate 50+ generated full ads, quality improvement over 3+ cycles.
v2: A/B Variant Engine + UGC Video (3–5 days) — Everything in v1, plus single-variable A/B variant generation (control + 3 variants), multi-model image orchestration (Nano Banana Pro vs. Nano Banana 2 for cost/quality tradeoffs), image style transfer experiments, automated variant performance ranking, and UGC video generation via Google Veo (video spec extraction, video attribute evaluation, script-video coherence verification, multi-format ad assembly covering feed, Stories, and Reels).
v3: Autonomous Ad Engine (1–2 weeks) — Everything in v2, plus self-healing feedback loops, quality ratchet (standards only go UP), performance-per-token tracking, agentic orchestration (researcher, writer, editor, visual director, video director, evaluator agents), competitive intelligence, and automated creative style learning from top-performing competitor ads across all formats.
Brand Context: Varsity Tutors (Nerdy)
Brand voice: Empowering, knowledgeable, approachable, results-focused. Lead with outcomes, not features. Confident but not arrogant. Expert but not elitist. Meet people where they are.
Primary audience for this project: SAT test prep — parents anxious about college admissions, high school students stressed about scores, families comparing prep options (Princeton Review, Khan Academy, Chegg, Kaplan).
Assessment Overview
AreaWeightFocusQuality Measurement & Evaluation25%Can the system tell good ads from bad?System Design & Architecture20%Is the system well-built and resilient?Iteration & Improvement20%Does ad quality measurably improve?Speed of Optimization15%How efficiently does the system iterate?Documentation & Individual Thinking20%Can we see YOUR mind at work?
Bonus Points (up to +24)
AchievementBonusSelf-healing / automatic quality improvement+7Multi-model orchestration with clear rationale+3Performance-per-token tracking (ROI awareness)+2Quality trend visualization+2Competitive intelligence from Meta Ad Library+10


Part II: Architectural Pressure Test — 5 Rounds (50 Questions)
Round 1: Foundations — Failure Handling, Brand Voice Integrity, and ROI Maximization

R1-Q1: How should the system detect and recover from evaluator drift — where the LLM-as-Judge gradually inflates or deflates scores across cycles?
Why this matters: If your evaluator silently drifts, your 7.0 threshold becomes meaningless. A "7.0" today could be a "5.5" tomorrow, and the system would never know it's shipping mediocre work.
Option A — Static Calibration Anchors: Maintain a fixed set of 10–15 reference ads with pre-assigned "ground truth" scores. Before every evaluation batch, run the evaluator against these anchors. If the mean score drifts more than ±0.5 from the established baseline, halt the pipeline and re-calibrate the evaluation prompt with few-shot examples from the anchor set.
Option B — Statistical Process Control (SPC): Track the evaluator's score distributions (mean, standard deviation, skew) across every batch using control charts. Set upper/lower control limits (e.g., ±2σ from the rolling 5-batch mean). When a batch breaches these limits, the system automatically injects the anchor ads as "canaries" into the next evaluation run to diagnose whether the drift is real quality change or evaluator instability.
Option C — Dual-Evaluator Consensus with Disagreement Alerting: Run two independent evaluator instances — one using structured rubric prompting, the other using comparative ranking. When these two systems disagree on more than 20% of ads in a batch, flag for human review and trigger recalibration.
Best Answer: Option B (Statistical Process Control)
Option A is necessary but reactive — it only catches drift at explicit checkpoints and burns tokens on every batch regardless of need. Option C is the most robust but also the most expensive (2x evaluation cost), directly undermining performance-per-token. Option B gives you continuous monitoring with minimal overhead: the control charts run on metadata you're already collecting (scores), the canary injection only fires when drift is actually detected, and the statistical rigor means you can distinguish real quality shifts from evaluator noise. Layer in Option A's anchors as the recalibration mechanism once SPC flags an issue.

R1-Q2: When the feedback loop fails to improve an ad after N regeneration cycles, what should the system do?
Why this matters: Infinite retry loops are the silent killer of token budgets. A system that doesn't know when to quit will burn more on a lost cause than the ad could ever be worth.
Option A — Hard Cutoff with Logging: Set a fixed maximum of 3 regeneration attempts. If the ad hasn't cleared 7.0 after 3 cycles, mark it as "failed," log the failure reason, archive it in a quarantine library, and move to the next brief.
Option B — Diminishing Returns Detection: Track the score delta between each cycle. If improvement between cycle N and N-1 is less than 0.3 points, declare "diminishing returns" and stop — triggering a diagnostic on whether the problem is the brief, the generator prompt, or an unreasonably strict evaluator dimension.
Option C — Brief Mutation + Escalation: After 2 failed regeneration attempts, the system mutates the brief — analyzing which dimension is persistently weak and adjusting the input. If mutation also fails (1 additional cycle), it escalates to a "human review" queue with a full diagnostic package.
Best Answer: Option C (Brief Mutation + Escalation)
Option A is safe but leaves value on the table — it treats all failures identically and never learns why a brief is hard. Option B is smarter about when to stop but doesn't attempt to fix the root cause. Option C is the only approach that actually tries to solve the problem before giving up. The key insight: if an ad fails after 2 cycles, the problem usually isn't the generator — it's the brief or the context. Mutating the brief is a cheap intervention that can unlock a stuck loop. The escalation path ensures the system never spirals.

R1-Q3: How should the system weight the five quality dimensions, and should weights be static or dynamic?
Why this matters: Equal weighting treats a confusing ad with great emotional resonance the same as a clear, emotionless ad. In reality, a confusing ad is worthless regardless of its other scores — the hierarchy matters.
Option A — Fixed Hierarchical Weights: Static weights: Clarity (30%), Value Proposition (25%), CTA (20%), Brand Voice (15%), Emotional Resonance (10%).
Option B — Campaign-Goal-Adaptive Weights: Two weight profiles: one for awareness campaigns (Emotional Resonance 25%, Brand Voice 20%, Clarity 25%, Value Prop 20%, CTA 10%) and one for conversion campaigns (CTA 30%, Value Prop 25%, Clarity 25%, Brand Voice 10%, Emotional Resonance 10%). System selects profile based on campaign goal in the brief.
Option C — Dynamic Weights with Floor Constraints: Baseline weights (equal 20%) with minimum floor scores per dimension. Adaptive weights increase the weight of any dimension consistently weakest across the last 10 ads.
Best Answer: Option B (Campaign-Goal-Adaptive Weights)
Option A is defensible but rigid — it assumes awareness and conversion ads value the same things. Option C is intellectually elegant but dangerous: dynamic weights mean your 7.0 threshold represents different quality bars at different times. Option B gives you adaptive weighting tied to a clear input variable (campaign goal) that makes behavior predictable and explainable. Add floor constraints from Option C (Clarity ≥ 6.0 everywhere) as a guard rail.

R1-Q4: How should the system orchestrate model selection to maximize quality-per-dollar?
Why this matters: Using your most expensive model for everything is lazy. Using your cheapest for everything produces garbage. The architecture decision is: which model does what, and when do you escalate?
Option A — Single Model for Everything: Use Gemini for both generation and evaluation. Simplifies architecture and makes token tracking trivial.
Option B — Tiered Model Routing: Smaller/cheaper model (Gemini Flash) for first-draft generation and initial scoring. Escalate to full model (Gemini Pro) only for ads in the "improvable" range (5.5–7.0). Ads below 5.5 discarded without expensive re-evaluation; ads above 7.0 pass directly.
Option C — Specialized Model Assignment: Different models for different tasks: Gemini Pro for generation, a structured-output model for evaluation, Gemini Flash for triage.
Best Answer: Option B (Tiered Model Routing)
Most ads are either clearly bad (discard cheap) or clearly good (pass cheap) — only the borderline cases need expensive attention. At scale, this can reduce token spend by 40–60% while maintaining the same output quality.

R1-Q5: How should the system prevent dimension collapse — optimizing one dimension at the expense of others?
Why this matters: A naive feedback loop that targets the weakest dimension will whack-a-mole: fix Clarity, break Emotional Resonance, fix Resonance, break Brand Voice. The system oscillates instead of converging.
Option A — Constraint-Based Regeneration Prompts: Explicitly instruct the generator to improve dimension X while maintaining all others at current level or above.
Option B — Pareto-Optimal Filtering: Generate 3–5 variants per regeneration cycle, evaluate all, select the variant that is Pareto-optimal: no other variant scores higher on all dimensions simultaneously.
Option C — Sliding Window Regression Detection: After each regeneration, compare all 5 dimension scores against the previous cycle. If any dimension drops by more than 0.5 points, reject and retry.
Best Answer: Option B (Pareto-Optimal Filtering)
Option A relies on the generator's ability to follow multi-constraint instructions, which is unreliable. Option C is reactive — it only catches collapse after it happens. Option B structurally prevents dimension collapse. By generating multiple variants and selecting via Pareto dominance, you never have to trust the generator to manage trade-offs — the selection logic does it mathematically.

R1-Q6: How should the system ensure Brand Voice consistency when the same brand has different tonal registers for different audiences?
Why this matters: Varsity Tutors talks to anxious parents differently than to stressed teenagers. "Empowering, knowledgeable, approachable" manifests differently depending on who's reading.
Option A — Audience-Specific Brand Voice Profiles: Distinct sub-profiles: "Parent-facing" (authoritative, reassuring, outcome-focused) and "Student-facing" (relatable, motivating, peer-like). Each with 3–4 few-shot examples. Generator selects profile based on audience segment; evaluator scores against audience-specific rubric.
Option B — Brand Voice Embedding with Cosine Similarity: Encode approved Varsity Tutors copy into embeddings. Compute cosine similarity for each generated ad against the brand corpus.
Option C — Two-Stage Brand Voice Evaluation: Split Brand Voice into "Brand Alignment" and "Audience Appropriateness." Score both independently.
Best Answer: Option A (Audience-Specific Brand Voice Profiles)
Option B is clever but brittle — cosine similarity measures surface-level lexical overlap, not tonal nuance. Option C adds evaluation complexity (6 effective dimensions). Option A is the right level of abstraction: few-shot examples do the heavy lifting — they show the generator what "empowering" sounds like for a worried parent vs. a stressed teenager.

R1-Q7: How should the system track and optimize "Performance per Token"?
Why this matters: Without explicit cost tracking, the system has no feedback signal for efficiency.
Option A — Simple Cost-Per-Publishable-Ad: Track total tokens per ad that clears 7.0.
Option B — Quality-Weighted Token Efficiency (QWTE): QWTE = (Average Quality Score) / (Total Tokens per Published Ad).
Option C — Full Token Attribution with Marginal Analysis: Tag every API call with its purpose. Build a cost attribution model showing exactly where tokens go. Run marginal analysis: quality gain per regeneration attempt to dynamically adjust regeneration budget.
Best Answer: Option C (Full Token Attribution with Marginal Analysis)
Option C is the only approach that generates actionable optimization signals. The marginal analysis lets the system autonomously decide when additional token spend isn't worth it. Over time, this creates a self-tuning cost envelope. Implement Option A as the dashboard metric, Option B for cross-batch comparison, and Option C as the optimization engine.

R1-Q8: How should the system handle the cold-start problem?
Why this matters: The feedback loop depends on historical data. On day one, you have none. If the system produces garbage in its first batch, the evaluator calibrates to garbage.
Option A — Reference-Seeded Generation: Use reference ads as few-shot examples with structural decomposition.
Option B — Competitor-Bootstrapped Calibration: Run evaluator against 20–30 competitor ads from Meta Ad Library before generating anything. Label 5–10 as excellent, 5–10 as poor. Calibrate evaluator scoring first.
Option C — Synthetic Warm-Up Batch: Generate 20 intentionally diverse ads (safe/conservative, aggressive/creative, reference-mimicking, intentionally bad). Use results to calibrate, then discard.
Best Answer: Option B (Competitor-Bootstrapped Calibration)
Option B solves the right problem first: evaluator calibration. If your evaluator can reliably score competitor ads, you can trust it from batch one. Combine with Option A for the generator side: seed first generation prompts with decomposed reference ads.

R1-Q9: How should the system implement a "quality ratchet" — ensuring standards only go up?
Why this matters: Without a ratchet, the system can regress. A bad batch can pull down the rolling average, the threshold adapts downward, and suddenly you're publishing 6.5-quality ads.
Option A — Fixed Absolute Threshold: 7.0 is immutable. Never changes.
Option B — Rolling High-Water Mark: Effective threshold = max(7.0, rolling_5batch_average − 0.5). If the system has been producing 8.2-average ads, the threshold rises to 7.7.
Option C — Percentile-Based Ratchet: Only publish top 30% of each batch, with a 7.0 floor.
Best Answer: Option B (Rolling High-Water Mark)
Option A isn't actually a ratchet — it's a flat line. Option C discards 70% of work, which is terrible for performance-per-token. Option B is the true ratchet: it remembers how well the system has performed and refuses to accept regression. The 0.5 buffer prevents the ratchet from being too aggressive.

R1-Q10: How should the system handle multi-modal coherence between text and images in v2?
Why this matters: Text and image generated independently will often conflict. Incoherence is worse than no image at all.
Option A — Sequential Generation (Image Conditioned on Text): Generate copy first, extract visual themes, pass to image generator.
Option B — Parallel Generation with Post-Hoc Coherence Scoring: Generate both independently, then score coherence and regenerate image if below 6.0.
Option C — Shared Semantic Brief Expansion: Before generating either, expand the brief into a detailed creative brief specifying emotional tone, visual setting, subject demographic, color palette, and key object/action. Both generators receive this shared input.
Best Answer: Option C (Shared Semantic Brief Expansion)
Option C prevents incoherence by design rather than detecting it after the fact. The expanded creative brief is a cheap LLM call that pays for itself by reducing mismatched generations. Use Option A's coherence evaluation as a verification step, not the primary alignment mechanism.

Round 1 Summary
#QuestionBest AnswerKey Principle1Evaluator Drift DetectionStatistical Process ControlCheapest signal, most targeted intervention2Failed Regeneration HandlingBrief Mutation + EscalationFix root cause before giving up3Dimension WeightingCampaign-Goal-AdaptiveWeights should reflect real ad dynamics4Model OrchestrationTiered Model RoutingConcentrate expensive tokens on improvable ads5Dimension Collapse PreventionPareto-Optimal FilteringStructural prevention > constraint-hoping6Brand Voice ConsistencyAudience-Specific ProfilesFew-shot conditioning over rubric descriptions7Performance per TokenFull Token AttributionMarginal analysis enables self-tuning budgets8Cold-Start ProblemCompetitor-Bootstrapped CalibrationCalibrate the evaluator before trusting the loop9Quality RatchetRolling High-Water MarkRemember your best; refuse regression10Multi-Modal CoherenceShared Semantic BriefPrevention is cheaper than detection + correction

Round 2: Strategy — Prompt Design, Competitive Intelligence, Testing, Scaling, and Human-in-the-Loop

R2-Q1: How should the system structure generation prompts to produce ads that sound human-written rather than AI-generated?
Why this matters: The assignment explicitly states "authentic > polished" and "UGC-style outperforms studio creative." The single biggest failure mode of AI ad copy is that it reads like AI.
Option A — Style-Negative Prompting: Explicit anti-pattern block in every generation prompt with a living blacklist of detected AI-isms.
Option B — Persona-Anchored Generation: Prompt the model to assume a specific persona (e.g., a parent ambassador who helped her daughter raise her SAT score). Different personas for different audience segments.
Option C — Reference-Decompose-Recombine Pipeline: Select 2–3 high-performing reference ads, decompose them into structural atoms (hook type, body pattern, CTA style, tone register, sentence length distribution), then prompt the generator to recombine proven structural elements.
Best Answer: Option C (Reference-Decompose-Recombine Pipeline)
Option C is the only approach that creates a repeatable, improvable system. By decomposing reference ads into structural atoms, you make "what works" explicit and combinatorial. The system can learn that question hooks + testimonial bodies + urgent CTAs outperform other combinations — and feed that back into future generation. This is where competitive intelligence directly feeds the generator.

R2-Q2: How should the system architect its competitive intelligence pipeline?
Why this matters: +10 bonus points for competitive intelligence from Meta Ad Library. This is where the system's "taste" gets trained on real market data rather than its own output.
Option A — Manual Snapshot Analysis: Collect 30–50 competitor ads at project start. Categorize by hook type, body structure, CTA, visual style. Static dataset.
Option B — Structured Pattern Extraction Pipeline: Automated or semi-automated collection from Meta Ad Library. For each ad, run LLM extraction: hook type, emotional angle, specificity level, CTA style, target audience. Store as structured records in a pattern database. Generator queries this database.
Option C — Competitive Differential Positioning: Beyond extracting patterns, run gap analysis to find whitespace that competitors aren't filling.
Best Answer: Option B (Structured Pattern Extraction Pipeline)
Option B is the sweet spot: it systematically converts raw competitive data into structured, queryable patterns. Build Option B's extraction pipeline first, layer Option C's gap analysis as a stretch goal.

R2-Q3: How should the system design tests to verify the evaluation framework measures what it claims to measure?
Why this matters: Testing that the pipeline runs without crashing is table stakes. The real risk is that the evaluator confidently scores garbage highly.
Option A — Golden Set Regression Tests: 15–20 "golden" ads with human-assigned scores. Evaluator must stay within ±1.0.
Option B — Adversarial Boundary Tests: Specific adversarial test cases probing each dimension's boundaries: perfect Clarity but zero Brand Voice, wrong brand entirely, pure emotional manipulation with no substance.
Option C — Inversion Tests + Correlation Analysis: Take high-scoring ads, systematically degrade one dimension at a time. Verify only the degraded dimension's score drops. Then run correlation analysis: if any two dimensions correlate above 0.7, the evaluator isn't measuring them independently.
Best Answer: Option C (Inversion Tests + Correlation Analysis)
Option C tests the evaluator's core claim: that it measures 5 independent dimensions. The correlation analysis catches the most common LLM-as-Judge failure mode: halo effect. Build all three: Option A as regression safety, Option B for boundary validation, Option C as the real proof.

R2-Q4: How should the system manage prompt context windows to avoid quality degradation as iteration history grows?
Why this matters: Each regeneration cycle adds context. A naive implementation that appends all history eventually overflows the context window or dilutes the signal.
Option A — Fixed-Window with Recency Bias: Only include last 2 cycles. Older cycles summarized into one line.
Option B — Structured Context Partitioning: Rigid sections with token budgets: Brief (200), Brand Context (150), Reference Patterns (200), Iteration Feedback (150), Instructions (100).
Option C — Distilled Context Objects: After each cycle, generate a compact "context distillation" — the current brief, highest-scored attempt, single most impactful improvement, and 2–3 anti-patterns. This replaces all raw history.
Best Answer: Option C (Distilled Context Objects)
Option C solves the root problem: the generator doesn't need to see the journey, it needs to see the destination. The generation prompt stays compact regardless of iteration depth, so cycle 5 costs the same tokens as cycle 1.

R2-Q5: How should the system decide when human intervention is necessary?
Why this matters: A system that never asks for help will silently publish mediocre work. A system that asks too often isn't autonomous.
Option A — Threshold-Based Escalation: Explicit trigger conditions (>30% batch failure, stalled ratchet, brand safety violation, cost spike).
Option B — Confidence-Gated Autonomy: Evaluator rates its own confidence (1–10). High (>7) = autonomous. Medium (5–7) = flagged for optional review. Low (<5) = human required.
Option C — Anomaly-Driven Escalation: Statistical baselines for all metrics; escalate on 2σ deviations.
Best Answer: Option B (Confidence-Gated Autonomy)
Option B makes the evaluator self-aware. This concentrates human attention where it has the highest marginal impact — the gray zone. Supplement with Option A's brand safety trigger (score below 4.0 on any dimension = hard stop).

R2-Q6: How should A/B variant generation maximize learning per token spent?
Why this matters: Generating 5 random variants teaches you nothing. Generating 5 strategically differentiated variants that isolate specific variables tells you exactly what works.
Option A — Random Diversity (temperature variation): Generate 5 variants at different temperatures. Log which range produces best quality.
Option B — Single-Variable Isolation: Control ad + 3–4 variants each changing exactly one structural element (hook type, emotional angle, CTA). Compare each variant against control.
Option C — Factorial Design with Pruning: 3 variables × 2–3 options = fractional factorial design. Simple regression to estimate main effects and interactions.
Best Answer: Option B (Single-Variable Isolation)
After just 10 briefs (40 ads), the system has strong signal on which hooks, angles, and CTAs work best. Each token spent on variant generation is an investment in learning, not a lottery ticket.

R2-Q7: How should the image evaluator (v2) assess "brand consistency"?
Why this matters: Visual brand consistency is hard to articulate programmatically. "Does this image look like a Varsity Tutors ad?" is easy for a human, hard for a system.
Option A — Multimodal LLM Evaluation: Holistic rating by a multimodal model.
Option B — Reference Image Similarity Scoring: CLIP embeddings and cosine similarity against reference images.
Option C — Attribute Checklist Evaluation: Structured checklist: student-age subjects? Warm lighting? Educational context? Diversity? No competitor branding? Score each independently.
Best Answer: Option C (Attribute Checklist Evaluation)
Option C decomposes "brand consistency" the same way the text evaluator decomposes "ad quality." Each attribute is binary or near-binary (easy for a multimodal model to assess), the aggregate is interpretable, and the feedback loop can target specific visual attributes.

R2-Q8: How should data storage and logging support retrospective analysis and reproducibility?
Why this matters: A system that can't replay its own history can't learn from it.
Option A — Flat File Logging: Timestamped JSON files per batch.
Option B — Structured Event Store (SQLite): Typed events with causal graph via parent_event_ids.
Option C — Append-Only Decision Ledger: Single JSONL file with standardized schema: {timestamp, event_type, ad_id, brief_id, cycle_number, action, inputs, outputs, scores, tokens_consumed, model_used, seed}. Lightweight query layer with pandas.
Best Answer: Option C (Append-Only Decision Ledger)
Zero-dependency (just a file), fully reproducible (append-only = no data ever lost), trivially queryable with pandas. Quality trend visualization = df.groupby('cycle_number')['score'].mean().plot() — literally one line of code.

R2-Q9: How should the system handle explore vs. exploit for creative approaches?
Why this matters: Pure exploitation converges on a local optimum (creative fatigue). Pure exploration wastes tokens.
Option A — Fixed Exploration Budget: 80% exploit / 20% explore. Successful explorations promoted to "proven" library.
Option B — Performance-Decay-Triggered Exploration: Start in pure exploit. When rolling average plateaus (<0.1 improvement over 3 batches), increase exploration rate until a new pattern breaks the plateau. Return to exploit with expanded pattern library.
Option C — Multi-Armed Bandit with Thompson Sampling: Model each structural combination as an "arm." Thompson Sampling balances explore-exploit probabilistically.
Best Answer: Option B (Performance-Decay-Triggered Exploration)
Option B makes exploration contingent on need. Token-efficient because it only spends on exploration when exploitation is provably exhausted.

R2-Q10: How should the demo and output presentation layer maximize the Documentation & Individual Thinking rubric score (20%)?
Why this matters: The rubric is explicit — "Can we see YOUR mind at work?"
Option A — Static Report Generation: PDF/markdown report with trend charts, score tables, decision log, cost breakdown.
Option B — Interactive Decision Trail: Lightweight HTML dashboard for browsing ad lifecycles, filtering, and viewing actual prompts.
Option C — Narrated Pipeline Replay: Chronological walkthrough of the system's operation: per-batch summary with reasoning, failed experiments highlighted, cost and quality per batch.
Best Answer: Option C (Narrated Pipeline Replay)
The narrated replay makes the system's "thinking" legible without requiring the reviewer to reverse-engineer it from charts. Critically, it highlights failures — which is exactly what the rubric calls "excellent" documentation. Cheap to implement (structured dump of the decision ledger, formatted as readable narrative).

Round 2 Summary
#QuestionBest AnswerKey Principle1Human-Sounding CopyReference-Decompose-RecombineProven structures > creative gambling2Competitive Intelligence PipelineStructured Pattern ExtractionQueryable patterns > raw ad collection3Evaluation Test DesignInversion Tests + CorrelationProve dimensions are independent, not decorative4Context Window ManagementDistilled Context ObjectsGenerator needs the destination, not the journey5Human-in-the-Loop TriggersConfidence-Gated AutonomyFocus humans on the gray zone6A/B Variant StrategySingle-Variable IsolationEach variant is a learning investment, not a lottery ticket7Image Brand Consistency (v2)Attribute Checklist EvaluationDecompose visual brand like you decompose text quality8Data Storage & LoggingAppend-Only Decision LedgerZero-dependency, fully reproducible, trivially queryable9Explore vs. ExploitPerformance-Decay-TriggeredExplore only when exploitation is provably exhausted10Demo & Presentation LayerNarrated Pipeline ReplayShow the system's thinking, especially its failures

Cross-Round Architecture Synthesis (Rounds 1 & 2)
1. Decomposition Everywhere — Text quality → 5 dimensions. Brand voice → audience profiles. Visual consistency → attribute checklists. Competitive intelligence → structural patterns. Ad structure → combinable atoms.
2. Prevention Over Detection — Shared semantic briefs prevent multi-modal incoherence (R1-Q10). Distilled context objects prevent context bloat (R2-Q4). Pareto-optimal selection prevents dimension collapse (R1-Q5).
3. Token-Aware Decision Making — Tiered model routing (R1-Q4). Full token attribution (R1-Q7). Diminishing returns detection (R1-Q2). Performance-decay-triggered exploration (R2-Q9).
4. Self-Awareness as Architecture — Statistical process control for evaluator drift (R1-Q1). Confidence-gated autonomy (R2-Q5). Inversion tests for evaluation integrity (R2-Q3).
5. Visible Reasoning — Narrated pipeline replay (R2-Q10). Append-only decision ledger (R2-Q8). Rolling high-water mark as documented quality trajectory (R1-Q9).

Round 3: Engineering — Agentic Orchestration, Resilience, Guardrails, Reproducibility, Caching, and Pipeline Design
Coverage Map — What Rounds 1 & 2 Already Addressed:
R1: Evaluator drift, failed regeneration, dimension weighting, model routing, dimension collapse, brand voice, token tracking, cold-start, quality ratchet, multi-modal coherence.
R2: Prompt authenticity, competitive intelligence, test design, context management, human escalation, A/B variants, image evaluation, data logging, explore-exploit, demo layer.
Round 3 fills the remaining gaps.

R3-Q1: How should the system design its agentic orchestration layer to avoid cascading failures and circular dependencies?
Why this matters: The v3 spec calls for agentic orchestration. Naively chaining agents creates a fragile pipeline where one agent's failure propagates downstream, and circular feedback can create infinite loops.
Option A — Linear Pipeline with Error Boundaries: Strict sequence: Researcher → Writer → Editor → Evaluator. Each agent has a bounded contract (defined inputs/outputs, max token budget, timeout). If any agent fails, the pipeline halts at that stage. Central controller passes outputs forward.
Option B — Event-Driven Agent Mesh: Agents subscribe to events and publish results. Concurrent where dependencies allow. Circuit breakers prevent token overspend.
Option C — Hierarchical Orchestrator with Contract Negotiation: Lightweight Orchestrator decomposes tasks, assigns to agents with explicit success criteria, monitors completion, can reassign on failure.
Best Answer: Option A (Linear Pipeline with Error Boundaries)
Option B introduces concurrency bugs disproportionate to the task. Option C requires sophisticated meta-prompting that's hard to debug and test. Option A delivers 90% of the value at 20% of the complexity. Run the linear pipeline in parallel across briefs for throughput. Build Option A, demonstrate it works, then describe Option C as the production-grade evolution in your documentation.

R3-Q2: How should the system handle API failures, rate limits, and transient errors without losing work?
Why this matters: Gemini's free tier has aggressive rate limits (15 RPM Flash, 2 RPM Pro). A single 429 at the wrong moment can corrupt a batch mid-evaluation.
Option A — Retry with Exponential Backoff: Wrap every API call in retry handler. On failure after 3 retries, skip and continue.
Option B — Checkpoint-and-Resume Architecture: After every successful API call, write to the append-only decision ledger with a checkpoint_id. On crash or interruption, resume from last checkpoint. No work ever lost, no ad ever double-processed.
Option C — Rate-Aware Batch Scheduler: Calculate total API calls, check remaining rate limit quota, schedule to stay within limits proactively.
Best Answer: Option B (Checkpoint-and-Resume Architecture)
On a free tier with 2 RPM limits, 429s aren't exceptions — they're the steady state. Option B solves pipeline state integrity. Combined with Option A's retry logic and a simple fixed delay between calls, you get resilience and recoverability. python run_pipeline.py --resume picks up from the last checkpoint.

R3-Q3: How should the system enforce platform-specific guardrails for Meta advertising policies?
Why this matters: An ad that says "Guaranteed 1500+ SAT score" violates Meta's prohibition on misleading claims. If the system produces policy-violating ads, the entire output is useless.
Option A — Post-Generation Policy Filter: Separate compliance check pass after generation and scoring.
Option B — Policy-Embedded Generation Prompts: Bake constraints into the generation prompt: no guarantees, no fear-based deficiency language, no negative competitor references.
Option C — Tiered Compliance Architecture: Three layers: (1) generation prompts with hard constraints, (2) evaluator binary compliance check (overrides quality score), (3) regex/keyword filter for obvious violations (dollar amounts without disclaimers, competitor trademarks, absolute guarantees).
Best Answer: Option C (Tiered Compliance Architecture)
Defense-in-depth: the generation prompt reduces violation probability (cheap), the evaluator catches semantic violations (smart), the regex filter catches literal violations (deterministic, zero tokens, milliseconds). Compliance failures require beating all three systems simultaneously.

R3-Q4: How should the system architect seed management and deterministic behavior?
Why this matters: The assignment requires "deterministic behavior (seeds)" and "reproducibility." But LLM APIs with temperature > 0 are inherently non-deterministic.
Option A — Global Seed with Temperature Zero: Single global seed, temperature=0 for all calls.
Option B — Per-Ad Deterministic Seed Chain: seed = hash(global_seed + brief_id + cycle_number). Each ad's seed is derived from its identity, not position in sequence. Failures don't cascade seed shifts.
Option C — Snapshot-Based Reproducibility: Full input-output snapshots for every API call. "Reproduce" by replaying snapshots rather than re-calling the API.
Best Answer: Option B + Option C Combined
Option A fails because a global seed creates order-dependency. Option B fixes this — each ad's seed is identity-derived. Option C provides the ultimate safety net: exact outputs from the original run regardless of API behavior changes. Use Option B for intentional reproducibility and Option C for forensic reproducibility.

R3-Q5: How should the system expand minimal ad briefs into rich generation context without hallucinating?
Why this matters: A brief saying "Parents, SAT prep, Conversion" contains almost no information. The system needs to expand into rich context without inventing product details.
Option A — Static Brand Knowledge Base: Structured file of verified Varsity Tutors facts. Brief expansion looks up relevant facts.
Option B — LLM-Powered Brief Expansion with Grounding Constraints: LLM expands the brief using ONLY verified facts from the knowledge base. Creative framing (emotional angles, story structures) added around verified facts. Unverified product mentions flagged and use generic language instead.
Option C — Template-Based Brief Expansion with Audience Matrices: Pre-built templates for each audience × goal combination.
Best Answer: Option B (LLM-Powered Brief Expansion with Grounding Constraints)
Option B separates what the system knows (knowledge base, deterministic) from how the system frames it (LLM expansion, creative). The grounding constraint ensures creative framing without hallucinated product claims.

R3-Q6: How should the LLM-as-Judge evaluation prompt be structured?
Why this matters: The evaluator is the single most important component. If it scores inconsistently, the feedback loop amplifies noise. If rationales are vague, regeneration has nothing actionable.
Option A — Single-Pass Holistic Evaluation: One prompt, all 5 dimensions scored at once.
Option B — Dimension-Isolated Sequential Evaluation: Each dimension in a separate API call. Prevents halo effects. 5x cost.
Option C — Chain-of-Thought Structured Evaluation: Single call with strict sequence: (1) Read ad, (2) identify hook/value prop/CTA/emotional angle before scoring, (3) compare against rubric calibration examples, (4) score with contrastive rationale, (5) flag low-confidence dimensions. Forced decomposition before scoring reduces halo effect without 5x cost.
Best Answer: Option C (Chain-of-Thought Structured Evaluation)
Option C achieves most of Option B's score independence at Option A's token cost. The forced decomposition in Step 2 breaks the holistic impression into parts that can be independently assessed. Calibration examples drawn from reference ads anchor the scale.

R3-Q7: How should the system implement caching?
Why this matters: The same brand context and compliance rules get sent with every call. Without caching, you pay tokens for identical preamble every time.
Option A — Prompt-Level Deduplication: Hash complete prompts, return cached response on match.
Option B — Semantic Component Caching: Cache static prompt components (brand context, rubric). Reduces code maintenance but doesn't save API tokens.
Option C — Result-Level Caching with Version TTL: Cache evaluation results keyed by hash(ad_text + evaluator_prompt_version). On evaluator recalibration, all cached scores for old prompt version invalidated.
Best Answer: Option C (Result-Level Caching with Staleness TTL)
The prompt-version key ensures recalibration (R1-Q1) automatically invalidates all cached scores. TTL is version-based, not time-based — the right staleness model for event-driven changes.

R3-Q8: How should the system handle cross-campaign learning?
Why this matters: If the system discovers question hooks outperform stat hooks for anxious parents, does that transfer to math tutoring parents?
Option A — Isolated Campaign Silos: No learning transfers. Safest but wasteful.
Option B — Shared Structural Patterns, Isolated Content: Structural learning (hook types, body patterns, CTA styles) is shared. Content learning (specific claims, statistics) is campaign-specific. Pattern library has campaign_scope tag: universal or campaign:{name}.
Option C — Transfer Learning with Validation Gates: Initialize new campaigns with top patterns from most similar existing campaign. Validate before promoting.
Best Answer: Option B (Shared Structural Patterns, Isolated Content)
Option B mirrors how real ad agencies think: the craft of ad writing transfers; the substance doesn't.

R3-Q9: How should the pipeline DAG maximize throughput while preserving correctness?
Why this matters: A strictly sequential pipeline at 50+ ads with 2 RPM rate limits takes hours.
Option A — Batch-Sequential Processing: Fixed-size batches (10 ads). Within a batch: all generation in parallel → all evaluation in parallel → regeneration decisions → all regeneration in parallel. Shared state updated between batches.
Option B — Per-Ad Independent Pipelines with Shared Read-Only State: Each ad runs its own pipeline concurrently. Shared state is read-only, updated at sync points.
Option C — Priority-Queue-Based Pipeline: Highest-priority ads (closest to 7.0 threshold) processed first.
Best Answer: Option A (Batch-Sequential Processing)
Batch-parallel gives 10x throughput over sequential. Between-batch sync points guarantee consistency. The batch size is tunable based on rate limits. Batch boundaries create natural checkpoints (R3-Q2).

R3-Q10: How should evaluation rationales be structured to make regeneration feedback actionable?
Why this matters: This is the connective tissue that makes the entire feedback loop work or fail. If the rationale says "clarity could be improved," regeneration has nothing actionable.
Option A — Free-Text Rationale: 1–2 sentence rationale per score. Quality depends entirely on prompt and model.
Option B — Structured Diagnostic Templates: Per-dimension template with {problem_type, specific_element, suggested_fix_direction}.
Option C — Contrastive Rationale Generation: Evaluator provides not just why the ad scored X, but what a version scoring 2 points higher would look like. "This ad scores 5.8 on Clarity because [reason]. A 7.8 version would [specific change]. The gap is [specific element]."
Best Answer: Option C (Contrastive Rationale Generation)
Option C makes the evaluator do the creative work of imagining the improvement. The contrast gives the generator a concrete target instead of an abstract direction. This dramatically reduces regeneration cycles — arguably the single highest-ROI architectural decision in the entire system.

Round 3 Summary
#QuestionBest AnswerKey Principle1Agentic OrchestrationLinear Pipeline + Error Boundaries90% of the value at 20% of the complexity2API Failure ResilienceCheckpoint-and-ResumePipeline state integrity > retry logic3Platform ComplianceTiered Compliance (3 layers)Defense-in-depth: prompt + evaluator + regex4Seed & ReproducibilityPer-Ad Seed Chain + SnapshotsIdentity-based seeds + forensic replay5Brief ExpansionLLM Expansion with GroundingSeparate verified facts from creative framing6Evaluation Prompt DesignChain-of-Thought StructuredForce decomposition before scoring7Caching StrategyResult-Level + Version TTLCache results, not prompts; invalidate on recalibration8Cross-Campaign TransferShared Structure, Isolated ContentCraft transfers; substance doesn't9Pipeline DAG DesignBatch-Sequential ProcessingBatch-parallel for throughput, sync points for consistency10Rationale QualityContrastive Rationale Generation"What would +2 look like?" > "What's wrong?"

Complete Architecture Synthesis — All Five Rounds
The 50-Question Map
Round 1 — Foundations: Failure, Brand, ROI
#TopicDecision1Evaluator driftStatistical Process Control2Failed regenerationBrief mutation + escalation3Dimension weightingCampaign-goal-adaptive4Model routingTiered (cheap → expensive)5Dimension collapsePareto-optimal filtering6Brand voiceAudience-specific profiles7Token trackingFull attribution + marginal analysis8Cold startCompetitor-bootstrapped calibration9Quality ratchetRolling high-water mark10Multi-modal coherenceShared semantic brief
Round 2 — Strategy: Prompts, Intelligence, Testing, Presentation
#TopicDecision1Human-sounding copyReference-decompose-recombine2Competitive intelligenceStructured pattern extraction3Test designInversion tests + correlation analysis4Context managementDistilled context objects5Human escalationConfidence-gated autonomy6A/B variantsSingle-variable isolation7Image brand consistencyAttribute checklist evaluation8Data loggingAppend-only decision ledger9Explore vs exploitPerformance-decay-triggered10Demo layerNarrated pipeline replay
Round 3 — Engineering: Resilience, Compliance, Scale, Transfer
#TopicDecision1Agentic orchestrationLinear pipeline + error boundaries2API resilienceCheckpoint-and-resume3Platform complianceTiered (prompt + evaluator + regex)4ReproducibilityPer-ad seed chain + snapshots5Brief expansionGrounded LLM expansion6Evaluation promptChain-of-thought structured7CachingResult-level + version TTL8Cross-campaign transferShared structure, isolated content9Pipeline DAGBatch-sequential processing10Rationale qualityContrastive rationale generation
Eight Architectural Pillars (Consolidated)
1. Decomposition Is the Architecture — Quality → 5 dimensions. Brand voice → audience profiles. Visual consistency → attribute checklists. Competitive intelligence → structural patterns. Evaluation → forced chain-of-thought decomposition. The system that decomposes best, evaluates best.
2. Prevention Over Detection Over Correction — Grounded brief expansion prevents hallucination. Shared semantic briefs prevent multi-modal incoherence. Tiered compliance prevents policy violations. Pareto selection prevents dimension collapse. Every dollar spent on prevention saves ten on detection and correction.
3. Every Token Is an Investment, Not an Expense — Tiered model routing. Full token attribution with marginal analysis. Result-level caching. Performance-decay-triggered exploration. Contrastive rationales that reduce regeneration cycles. The system continuously asks: "Is this API call earning its keep?"
4. The System Knows What It Doesn't Know — Confidence-gated autonomy. Statistical process control for evaluator drift. Inversion tests for evaluation integrity. Per-dimension correlation analysis. The system's self-awareness is as important as its output quality.
5. State Is Sacred — Checkpoint-and-resume architecture. Append-only decision ledger. Per-ad deterministic seed chains. Input-output snapshots. No work is ever lost. Every decision is recoverable. Every run is reproducible.
6. Learning Is Structural — Reference-decompose-recombine for generation. Single-variable isolation for variant testing. Shared structural patterns across campaigns. The system doesn't learn "this ad was good" — it learns why it was good, in terms that transfer.
7. Visible Reasoning Is a First-Class Output — Narrated pipeline replay. Contrastive evaluation rationales. Decision log with honest failures. The system's thinking is as important as its output — because the rubric literally says so.

8. The Reviewer Is a User, Too — The submission is a product. The reviewer is the customer. The notebook narrates the journey (R4-Q1). The curated showcase tells the quality story (R4-Q4). The demo respects their time (R4-Q5). The decision log shows your mind, not just your code (R4-Q9). A great system that's hard to evaluate will score worse than a good system that makes its value obvious.

9. The Tool Is the Product — Session management, authentication, brief configuration, and progress monitoring transform the pipeline from a CLI tool into a product (R5). Immutable sessions guarantee reproducibility (R5-Q1). Progressive disclosure makes configuration fast for repeat users, deep for power users (R5-Q3). Hybrid progress monitoring rewards attention without demanding it (R5-Q4). The curation layer preserves metric integrity while enabling practical use (R5-Q6). FastAPI + React matches the existing stack (R5-Q7). Single-VM deployment keeps it simple (R5-Q10).


Part III: Verification Report — 5-Round Interview Alignment Audit
1. Round Progression — Do They Build on Each Other?
Verdict: Yes — with clear thematic escalation.
RoundThemeWhat It EstablishesR1FoundationsThe core feedback loop mechanics: how the system evaluates, fails, recovers, improves, and tracks cost. Decisions you must make before writing a single line of code.R2StrategyHow the system gets smart: prompt design, competitive learning, testing rigor, data infrastructure, human handoff, creative exploration, and how to present the work.R3EngineeringHow the system runs in reality: API resilience, platform compliance, reproducibility, caching, concurrency, agent orchestration, and the connective tissue that makes the feedback loop converge.
R1 answers "what does the system do?", R2 answers "how does the system think?", R3 answers "how does the system survive and scale?"
2. Cross-Reference Integrity
14 explicit cross-references verified. No contradictions found. The append-only ledger (R2-Q8) is the most heavily referenced component, appearing as a dependency in R3-Q2 (checkpoints), R3-Q4 (snapshots), R3-Q7 (cache keys), and R2-Q10 (narrated replay).
ReferenceSourceTargetConsistent?Decision ledger from R2-Q8R3-Q2 (Checkpoint-resume)R2-Q8 (Append-only ledger)YesConfidence-gated autonomy from R2-Q5R3-Q6 (Evaluation prompt Step 5)R2-Q5 (Human escalation)YesCold-start calibration from R1-Q8R3-Q6 (Calibration examples)R1-Q8 (Competitor-bootstrapped)YesInversion tests from R2-Q3R3-Q6 (Halo effect detection)R2-Q3 (Test design)YesQuality ratchet from R1-Q9R3-Q9 (Batch sync points)R1-Q9 (Rolling high-water mark)YesPattern database from R2-Q2R3-Q8 (Campaign scope tags)R2-Q2 (Structured pattern extraction)YesAppend-only ledger from R2-Q8R3-Q4 (Snapshot storage)R2-Q8 (JSONL ledger)YesR1-Q1 recalibrationR3-Q7 (Cache invalidation)R1-Q1 (SPC drift detection)YesPareto-optimal selection R1-Q5R2 SynthesisR1-Q5 (Dimension collapse)YesShared semantic brief R1-Q10R2 SynthesisR1-Q10 (Multi-modal coherence)YesDistilled context objects R2-Q4R2 SynthesisR2-Q4 (Context management)YesNarrated pipeline replay R2-Q10R3 SynthesisR2-Q10 (Demo layer)YesBrief mutation R1-Q2R3-Q5 (Brief expansion)R1-Q2 (Failed regeneration)Implicit — complementaryTiered model routing R1-Q4R3-Q9 (Batch scheduling)R1-Q4 (Model selection)Implicit — complementary
3. Assignment Coverage Audit
All 5 "Ambiguous Elements" answered. All 5 rubric areas covered (6, 8, 7, 5, and 3 questions respectively). All 5 bonus opportunities addressed. All 3 scope variants covered. All 7 code quality requirements addressed.
4. Internal Consistency Check
No hard contradictions. Two tensions worth noting:
Tension 1: Pareto-Optimal Filtering vs. Performance-per-Token — R1-Q5 costs 3–5x generation tokens per cycle. Resolution: R1-Q5's answer notes "cost increase offset by needing fewer total cycles." R1-Q7's marginal analysis validates this empirically.
Tension 2: Linear Pipeline vs. Batch-Sequential — Complementary: linear pipeline is the per-ad architecture; batch-sequential is the batch architecture. R3-Q1 explicitly states "run the linear pipeline in parallel across briefs."
5. Gap Analysis — What's Missing for Production-Ready Handoff
GapImpactRecommendationOutput Format Specification (exact JSON schemas)MediumCreate schemas/ spec with sample JSON for ad output, evaluation result, ledger event, replay formatPrompt Templates (actual prompt text)HighCreate prompts/ directory with first-draft templates annotated with design rationaleBrand Knowledge Base Content (verified facts)MediumBuild from Slack reference ads + Varsity Tutors website + assignment brand contextSpecific Threshold Values (SPC limits, confidence breakpoints, batch sizes)Low-MediumCreate config.yaml with all tunable parameters, initial values, and comments linking to relevant questionsError Message / Logging StandardsLowAdopt Python standard logging levels with simple mapping to event types
6. Assignment-to-Interview Traceability Matrix
Assignment RequirementInterview Coverage"Performance per token"R1-Q7, R1-Q4, R3-Q7, R3-Q9"Generate, evaluate, iterate, and improve"R2-Q1, R3-Q6, R2-Q4, R1-Q9"Minimal human intervention"R2-Q5"Surfaces only its best work"R1-Q9, R1-Q5"Quality is decomposable"R1-Q3, R2-Q3, R3-Q6"5 quality dimensions scored independently"R1-Q3, R2-Q3, R3-Q6, R3-Q10"LLM-as-judge"R3-Q6, R1-Q1, R2-Q3"7.0/10 quality threshold"R1-Q9, R1-Q2, R3-Q3"50+ generated ads"R3-Q9, R2-Q6"3+ iteration cycles with improvement"R1-Q9, R2-Q9"Deterministic behavior (seeds)"R3-Q4"≥10 unit/integration tests"R2-Q3"Decision log"R2-Q8, R2-Q10"Self-healing feedback loops" (v3)R1-Q1, R1-Q2, R1-Q9"Quality ratchet: standards only go UP" (v3)R1-Q9"Agentic orchestration" (v3)R3-Q1"Competitive intelligence" (v3/bonus)R2-Q2"Image generation" (v2)R1-Q10, R2-Q7"A/B variant generation" (v2)R2-Q6"Authentic > polished / UGC-style"R2-Q1"Pattern interrupts / scroll-stopping hooks"R2-Q1, R2-Q2"Brand voice: Empowering, knowledgeable, approachable"R1-Q6"Must run locally"R3-Q2, R3-Q9"Document rate limits and cost"R3-Q2, R1-Q7"One-command setup"R3-Q1, R2-Q8


Part IV: Product Requirements Document
1. Executive Summary
Ad-Ops-Autopilot is an autonomous engine that generates, evaluates, and iteratively improves Facebook and Instagram ad copy for Varsity Tutors. The system solves the fundamental problem of mediocre AI-generated content by connecting three core capabilities: a multi-modal generator (text + image), an LLM-as-Judge evaluator scoring across five quality dimensions, and a self-correcting feedback loop that drives measurable improvement cycle over cycle.
The system is designed around a single north star metric: Performance per Token — maximizing quality output per dollar of API spend. Rather than producing volume, the system ruthlessly filters and regenerates until it meets a 7.0/10 quality threshold with minimal human intervention.
Key outcomes:

50+ publishable full ads (copy + generated image) with evaluation scores across 5 text dimensions + visual attribute checklist
Measurable quality improvement over 3+ iteration cycles with documented causes
Full token cost attribution enabling ROI optimization at every pipeline stage
Autonomous self-healing: the system detects quality drops, diagnoses root causes, and auto-corrects
Complete decision log and narrated pipeline replay demonstrating visible reasoning throughout

2. Problem Statement
Most AI-generated ad copy is mediocre. It reads like it was made by a machine, converts poorly, and costs more to produce than the value it creates. The core challenge is not generation — it is evaluation. A system that cannot reliably distinguish an 8/10 ad from a 5/10 ad cannot improve, regardless of how sophisticated its generator is.
The domain is tight and closed: paid social ads for Facebook and Instagram. No email, no landing pages, no TikTok. One channel family, one content type, done well.
Target audience: SAT test prep for Varsity Tutors — anxious parents, stressed students, and families comparing prep options (Princeton Review, Khan Academy, Chegg, Kaplan).
3. Architectural Pillars
The system architecture is governed by nine pillars derived from five rounds of architectural pressure-testing (50 design questions). These pillars inform every implementation decision.
PillarPrincipleKey Decisions1. Decomposition Is the ArchitectureEvery complex judgment → independently measurable parts5 text quality dimensions (R1-Q3), visual attribute checklist (R2-Q7, Section 4.6.3), 4-dimension coherence scoring (Section 4.6.4), structural pattern atoms (R2-Q1), chain-of-thought evaluation (R3-Q6)2. Prevention Over DetectionPrevent problems architecturallyShared semantic briefs (R1-Q10), grounded brief expansion (R3-Q5), tiered compliance (R3-Q3), Pareto selection (R1-Q5)3. Every Token Is an InvestmentTrack cost and optimize marginal returnsTiered model routing (R1-Q4), full token attribution (R1-Q7), result-level caching (R3-Q7), contrastive rationales (R3-Q10)4. The System Knows What It Doesn't KnowSelf-awareness = output qualitySPC for drift (R1-Q1), confidence-gated autonomy (R2-Q5), inversion tests (R2-Q3)5. State Is SacredNo work lost. Every run reproducible.Checkpoint-resume (R3-Q2), append-only ledger (R2-Q8), per-ad seed chains (R3-Q4)6. Learning Is StructuralLearn why, not just thatReference-decompose-recombine (R2-Q1), single-variable isolation (R2-Q6), shared patterns (R3-Q8)7. Visible ReasoningThinking is a first-class outputNarrated replay (R2-Q10), contrastive rationales (R3-Q10), honest failures (R2-Q10)8. The Reviewer Is a User, TooThe submission is a product for the reviewerNotebook form factor (R4-Q1), curated showcase (R4-Q4), 7-min demo (R4-Q5), ADR + narrative log (R4-Q9)9. The Tool Is the ProductThe pipeline becomes a productSession management, auth, brief config, progress monitoring (R5)
4. System Architecture Overview
4.1 Pipeline Flow
The core pipeline follows a batch-sequential DAG (R3-Q9). Within each batch, ads progress through stages in parallel; shared state updates happen at batch boundaries.
Brief → Expand (R3-Q5) → Generate Copy (R2-Q1) → Generate Image (Nano Banana Pro) → Coherence Check
├─ Coherent → Evaluate Text (R3-Q6) + Evaluate Image (attribute checklist) → Above thresholds?
│   ├─ Yes → Add to published library (full ad: copy + image)
│   └─ No  → Identify weakest dimension → Contrastive rationale (R3-Q10) → Pareto regeneration (R1-Q5) → Re-evaluate
└─ Incoherent → Regenerate image with adjusted prompt (1 retry) → Re-check coherence

4.2 Directory Structure

generate/ — Ad copy generation from expanded briefs
generate_image/ — Nano Banana Pro image generation, prompt construction, coherence verification
generate_video/ — Veo UGC video generation, video spec extraction, script-video coherence verification (v2)
evaluate/ — Chain-of-thought dimension scoring (text), attribute checklist (image), LLM-as-Judge, aggregation
iterate/ — Feedback loop, brief mutation, Pareto selection, quality ratchet
output/ — Formatting, export, quality trend visualization, narrated replay, full ad assembly
data/ — Brand knowledge base, reference ads, reference images, pattern database, config
tests/ — Golden set, adversarial, inversion, correlation tests, image coherence tests
docs/ — Decision log, limitations, technical writeup
app/ — Application layer (R5)

app/api/ — FastAPI routes (sessions, auth, progress SSE)
app/models/ — SQLAlchemy models (users, sessions, curated_sets)
app/workers/ — Celery tasks (pipeline execution, progress reporting)
app/frontend/ — React app (session list, brief config, progress view, dashboard shell)

docker-compose.yml — Local development stack
docker-compose.prod.yml — Production deployment (Nginx + FastAPI + PostgreSQL + Celery + Redis)

4.3 Agentic Orchestration (v3)
Linear pipeline with error boundaries (R3-Q1). Agents execute in strict sequence per ad: Researcher → Writer → Editor → Evaluator. Each agent has a bounded contract (defined inputs/outputs, max token budget, timeout). Parallelism happens across briefs (batch-level), not across agents within a single ad.
4.4 Model Strategy
TaskModelRationaleFirst-draft generation + initial scoringGemini Flash (cheap tier)Handles 80% of work at lowest costRegeneration for improvable ads (5.5–7.0)Gemini Pro (expensive tier)Concentrates quality tokens on borderline adsImage generation (v1)Nano Banana Pro (Gemini 3 Pro Image)State-of-the-art quality, text rendering, 4K output, brand-consistent visuals. ~$0.13/image at 1K res.Image generation — cost tier (v2)Nano Banana 2 (Gemini 3.1 Flash Image)Pro-level quality at Flash speed for A/B variant volume. ~$0.02–0.05/image via third-party.Image coherence evaluationGemini Flash (multimodal)Cheap multimodal call: pass image + copy → coherence score. High ROI.UGC video generation (v2)Veo 3.1 FastSame Google ecosystem. Optimized for programmatic ad generation. Native audio. 1080p, 9:16 for Reels/Stories. ~$0.90/6-sec video (audio), ~$0.60 (silent).Video attribute evaluationGemini Flash (multimodal)Frame sampling + audio analysis for attribute checklist. Same pattern as image evaluation.Script-video coherenceGemini Flash (multimodal)Copy + video → 4-dimension coherence score. Same framework as text-image coherence.Brief expansion + context distillationGemini FlashCheap LLM call, high ROI

4.5 Dashboard Architecture — Live Performance Benchmarks
Single-file HTML dashboard (nerdy_adgen_dashboard.html) reads from the append-only decision ledger and renders 8 panels: Pipeline Summary (hero metrics), Iteration Cycles (before/after), Quality Trends (charts), Dimension Deep-Dive (correlation matrix), Ad Library (filterable with rationales), Token Economics (cost attribution, marginal analysis), System Health (SPC, confidence, escalation), Competitive Intelligence (pattern database). Data source: output/dashboard_data.json from export_dashboard.py.

4.6 Image Generation Architecture — Nano Banana Pro Integration
Complete ads (copy + image) via Gemini 3 Pro Image. Visual spec extraction from shared semantic brief. 3 variants per ad (anchor, tone shift, composition shift). Pareto selection: composite = (attribute_pass_pct × 0.4) + (coherence_avg × 0.6). Attribute checklist (age, lighting, diversity, brand, artifacts). Text-image coherence verification (4 dimensions, ≥6 pass). Targeted regen loop (max 5 images/ad). Meta-ready outputs: 1:1, 4:5, 9:16.

4.7 Application Layer Architecture — Sessions, Auth & Real-Time UX
FastAPI + React + PostgreSQL + Celery + Redis. Session = one pipeline run (immutable). Google SSO (@nerdy.com). Brief config form (progressive disclosure). Session list with sparklines. Hybrid progress (background polling + optional "Watch Live" SSE). Curation layer (select, reorder, annotate, light edit). Docker Compose single-VM deployment.

4.8 Competitive Intelligence Architecture — Meta Ad Library Pattern Extraction
Semi-automated: Claude in Chrome analyzes competitor Ad Library pages. Structured pattern records (hook_type, value_prop_structure, cta_style, emotional_register, visual_patterns) in data/competitive/patterns.json. query_patterns(audience, tags) feeds brief expansion and generation. 6 competitors: Varsity Tutors, Kaplan, Princeton Review, Khan Academy, Chegg, Sylvan Learning.

4.9 UGC Video Architecture — Veo Integration
Veo 3.1 Fast for 6-sec UGC-style video. Video spec from expanded brief. 2 variants per ad (anchor + alternative). Attribute checklist (hook timing, UGC authenticity, pacing, brand safety). Script-video coherence (4 dimensions). Graceful degradation: video fails → publish copy + image only. 9:16 for Stories/Reels.

5. Quality Evaluation Framework
5.1 Five Quality Dimensions
DimensionWhat It MeasuresScore 1 (Bad)Score 10 (Excellent)ClarityMessage immediately understandable?Confusing, competing messagesCrystal clear single takeaway in <3 secondsValue PropositionCompelling, specific benefit?Generic ("we have tutors")Differentiated ("raise SAT score 200+ points")Call to ActionNext step clear and compelling?No CTA or vague ("learn more")Specific, urgent ("Start free practice test")Brand VoiceSounds like Varsity Tutors?Generic, could be anyoneDistinctly on-brand: empowering, knowledgeableEmotional ResonanceConnects emotionally?Flat, purely rationalTaps parent worry, student ambition, test anxiety
5.2 Weighting Strategy
Campaign-goal-adaptive weights (R1-Q3) with floor constraints:
DimensionAwareness WeightConversion WeightFloor ScoreClarity25%25%6.0 (hard minimum)Value Proposition20%25%NoneCall to Action10%30%NoneBrand Voice20%10%5.0 (hard minimum)Emotional Resonance25%10%None
5.3 Evaluation Prompt Design
Chain-of-thought structured evaluation (R3-Q6) enforcing a five-step sequence:

Step 1: Read the ad.
Step 2: Before scoring, identify the ad's hook, value proposition, CTA, and emotional angle in your own words.
Step 3: For each dimension, compare against rubric calibration examples (1-score and 10-score).
Step 4: Assign a score with a contrastive rationale: what the ad is, what a +2 version would look like, and the specific gap (R3-Q10).
Step 5: Flag any dimension where confidence is below 7/10 (feeds into confidence-gated autonomy, R2-Q5).

5.4 Quality Ratchet
Rolling high-water mark (R1-Q9): effective threshold = max(7.0, rolling_5batch_average − 0.5). The quality bar only goes up. The 7.0 absolute floor is immutable.
6. Project Phases & Tickets
Phase 0: Foundation & Calibration (Day 0–1)
Goal: Establish data infrastructure, brand knowledge base, and calibrated evaluator before generating a single ad.
TicketTitleDescriptionAcceptance CriteriaP0-01Project scaffoldingInitialize repo with directory structure. Create requirements.txt, config.yaml, README.One-command setup runs without errors; all directories existP0-02Append-only decision ledgerImplement JSONL event logger (R2-Q8) with standardized schema.Events written to ledger; pandas can filter by ad_id and reconstruct lifecycleP0-03Per-ad seed chain + snapshotsseed = hash(global_seed + brief_id + cycle_number) (R3-Q4). Full I/O snapshots to ledger.Same seed + brief_id + cycle = same seed; snapshots storedP0-04Brand knowledge baseVerified facts file for Varsity Tutors from assignment spec + reference ads (R3-Q5).Covers SAT prep audience; no invented factsP0-05Reference ad collection20–30 Varsity Tutors + 20–30 competitor ads. Label 5–10 excellent and 5–10 poor.Labeled reference set ready for calibrationP0-06Evaluator cold-start calibrationRun CoT evaluator against labeled reference ads (R1-Q8). Tune until calibrated.Scores within ±1.0 of human labels on 80%+P0-07Golden set regression tests15–20 golden ads with human-assigned scores (R2-Q3). Automated test suite.Test suite passes regression within ±1.0P0-08Checkpoint-resume infrastructureEvery successful API call writes checkpoint_id (R3-Q2). Resume from last checkpoint.--resume flag works; no duplicated workP0-09Competitive pattern database — initial scanUse Claude in Chrome to analyze 6 competitors' active Facebook ads via Meta Ad Library (Section 4.8.4). Extract structured pattern records using the extraction prompt (Section 4.8.5). Store in data/competitive/patterns.json.Pattern records for 6 competitors (8–10 ads each); JSON validates against schema; competitor strategy summaries writtenP0-10Competitive pattern query interfaceUtility function to query pattern database by audience, campaign goal, hook type, competitor. Returns top-N relevant patterns for pipeline consumption.query_patterns(audience="parents", tags=["conversion"]) returns ranked results

Phase 1: Full-Ad Pipeline — v1 Copy + Image (Days 1–4)
Goal: End-to-end full ad pipeline (text + image via Nano Banana Pro). 50+ complete ads with text evaluation + visual attribute scoring + coherence verification. Measurable improvement over 3+ cycles.
TicketTitleDescriptionAcceptance CriteriaP1-01Brief expansion engineLLM-powered expansion with grounding (R3-Q5). Expand using ONLY verified facts. Inject competitive landscape context from pattern database (Section 4.8.6) for differentiation guidance.No hallucinated claims; competitive context included in expanded briefP1-02Ad copy generatorReference-decompose-recombine (R2-Q1). Recombine proven structural elements.Produces primary text, headline, description, CTA buttonP1-03Audience-specific brand voice profilesParent-facing + Student-facing sub-profiles with few-shot examples (R1-Q6).Correct profile selected per audience segmentP1-04Chain-of-thought evaluator5-step evaluation prompt (R3-Q6) with contrastive rationales (R3-Q10). Structured JSON output.Per-dimension scores + rationales + confidence flagsP1-05Campaign-goal-adaptive weightingAwareness vs. conversion profiles. Clarity ≥ 6.0, Brand Voice ≥ 5.0 floors (R1-Q3).Correct weights per campaign goal; floor violations → rejectionP1-06Tiered model routingTriage: <5.5 discarded, >7.0 published, 5.5–7.0 escalated to expensive model (R1-Q4).Token spend concentrated on improvable rangeP1-07Pareto-optimal regeneration3–5 variants per cycle; select Pareto-dominant variant (R1-Q5).No dimension regressed vs. prior cycleP1-08Brief mutation + escalationAfter 2 failures: mutate brief. After 3: escalate with diagnostics (R1-Q2).Mutation logged; escalation triggers on third failureP1-09Distilled context objectsCompact context distillation per cycle (R2-Q4): best attempt + improvement + anti-patterns.Prompt stays compact regardless of cycle depthP1-10Quality ratchetRolling high-water mark: max(7.0, rolling_5batch_avg − 0.5) (R1-Q9).Threshold only increases; plot shows monotonic barP1-11Token attribution engineTag every API call (R1-Q7). Cost-per-publishable-ad + marginal quality gain.Dashboard shows spend by stageP1-12Result-level cachehash(ad_text + evaluator_prompt_version) key (R3-Q7). Invalidate on recalibration.Cache hits on resume; recalibration clears allP1-13Batch-sequential processorBatches of 10, parallel within stage, sequential across stages (R3-Q9).50+ ads processed; batch boundaries = checkpointsP1-14Nano Banana Pro integration + multi-variant generationIntegrate Nano Banana Pro API (Gemini 3 Pro Image). Visual spec extraction from expanded briefs. Generate 3 image variants per ad (anchor, tone shift, composition shift). Aspect ratio routing (1:1 default, 4:5 + 9:16 for published winners).3 variants generated per ad; all variants + visual specs logged to ledgerP1-15Visual attribute evaluator + Pareto image selectionMultimodal Gemini Flash call: each variant + visual spec → binary attribute checklist (age, lighting, diversity, brand, artifacts). 80% pass threshold. Pareto selection: composite score = (attribute_pass_pct × 0.4) + (coherence_avg × 0.6). Select best variant; log all 3.Each variant scored; best selected by composite; losing variants logged for learningP1-16Text-image coherence checkerMultimodal coherence verification per variant: copy + image → 4-dimension coherence score. Below 6 = incoherent. Coherence score feeds Pareto selection (60% weight).Coherence scores logged for all variants; incoherent-only ads trigger targeted regen (Section 4.6.6)P1-17Image targeted regen loopWhen all 3 variants fail: diagnose weakest attribute, append diagnostic, generate 2 regen variants. When best variant fails coherence: append fix_suggestion, generate 1 regen variant. Max 5 images per ad. Exhausted budget → flag "image-blocked" for human review. (Section 4.6.6)Regen triggers on failure; capped at 5 total images; image-blocked ads logged with diagnosticsP1-18Full ad assembly + exportAssemble published ads as complete units: copy JSON + selected winner image + all variant metadata. Meta-ready file naming. Export folder per ad.Each published ad has copy + winning image(s) + variant scores in output/P1-19Image cost trackingExtend token attribution engine to track image generation costs (per-image, per-variant, per-regen, per-aspect-ratio). Track variant selection win rates. Unified cost-per-publishable-ad.Dashboard shows text + image cost breakdown; variant strategy stats loggedP1-2050+ full ad generation runFull pipeline: 5+ batches, 3+ cycles. 50+ evaluated full ads (copy + image) meeting both thresholds. Multi-variant image selection active.Quality trend shows improvement; all published ads have winning images; variant metadata logged

Phase 1B: Application Layer (Days 3–5)
Goal: Wrap the pipeline in a multi-session internal application with auth, brief configuration, progress monitoring, and curation. All decisions trace to Round 5.
TicketTitleDescriptionAcceptance CriteriaPA-01FastAPI backend scaffoldFastAPI project with CORS, PostgreSQL via SQLAlchemy, Celery + Redis for background jobs. Docker Compose for local dev. (R5-Q7, R5-Q10)docker compose up starts API, DB, Redis, and Celery workerPA-02Database schema — users & sessionsPostgreSQL tables: users (Google SSO fields), sessions (config JSON, status, results_summary), curated_sets (per-session curation state). (R5-Q1, R5-Q5)Migrations run; schema matches Section 4.7.2 session modelPA-03Google SSO authenticationGoogle OAuth 2.0 login. @nerdy.com domain restriction. JWT session tokens. Per-user session isolation. (R5-Q5)Only @nerdy.com emails can sign in; users see only their sessionsPA-04Session CRUD APIREST endpoints: POST /sessions (create + start pipeline), GET /sessions (list with filters/sort), GET /sessions/:id (detail with full results). (R5-Q1, R5-Q2)Session creation triggers Celery pipeline job; list supports filter by audience, goal, statusPA-05Brief configuration form (React)Single-page form with progressive disclosure (R5-Q3). Required fields: audience, goal, ad count. Advanced accordion: threshold, weights, model tier, budget cap, image settings. Clone-from-previous button.Form submits to POST /sessions; clone pre-fills all fields; form validates before submitPA-06Session list UI (React)Flat reverse-chronological card list (R5-Q2). Cards show name, date, audience/goal badges, ad count, avg score, visual score, cost/ad, quality sparkline, status badge. Filters + sort + search.Cards render with all metadata; running sessions show "Cycle X/Y" progress; filters workPA-07Background job progress reportingCelery worker writes progress to Redis pub/sub during pipeline execution. FastAPI SSE endpoint streams progress to frontend. Session list polls every 30 seconds. (R5-Q4)Running sessions update in real time; progress visible in session list without clicking inPA-08"Watch Live" progress view (React)Dedicated progress dashboard: cycle indicator, ad count bar, live score feed, cost accumulator, live quality trend chart, latest ad preview. SSE-powered. (R5-Q4)All 6 progress elements update in real time during pipeline runPA-09Session detail — dashboard integrationWrap existing 5-tab dashboard in session context. Add breadcrumb nav, back button. Scope all dashboard data to selected session's ledger. (R5-Q8)Clicking a session opens the existing dashboard filtered to that session's dataPA-10Curation layer + Curated Set tab6th dashboard tab. Select/deselect ads, reorder, annotate, light edit with diff tracking. Export curated set as zip (copy JSON + images). (R5-Q6)Curated selections persist; edits tracked with before/after; export produces Meta-ready zipPA-11Share session linkGenerate read-only URL with time-limited token. Shared viewers see dashboard in read-only mode (no curation, no new sessions). (R5-Q5)Shared link opens session detail; no auth required; token expires after 7 daysPA-12Docker Compose production deploymentProduction Docker Compose: Nginx reverse proxy + static React build, FastAPI, PostgreSQL, Celery worker, Redis. Auto-HTTPS. Environment variable configuration. (R5-Q10)docker compose -f docker-compose.prod.yml up serves full application with HTTPS

Phase 2: Testing & Validation (Days 3–4)
Goal: Prove evaluation framework has substance. Demonstrate dimension independence. Validate self-awareness.
TicketTitleDescriptionAcceptance CriteriaP2-01Inversion testsDegrade one dimension at a time in high-scoring ads (R2-Q3).10+ tests; degraded drops ≥1.5, others stable ±0.5P2-02Correlation analysisPairwise correlation across all 5 dimensions. Flag r > 0.7 (R2-Q3).Matrix generated; no pair exceeds 0.7 (or documented)P2-03Adversarial boundary testsEdge cases: perfect Clarity + zero Brand Voice, wrong brand entirely (R2-Q3).8+ tests pass; dimension-specific failures identifiedP2-04SPC drift detectionStatistical process control on evaluator distributions (R1-Q1). Canary injection on breach.Control charts plotted; canary fires on simulated driftP2-05Confidence-gated autonomyConfidence flags → escalation: >7 autonomous, 5–7 flagged, <5 human required (R2-Q5).Correct routing per confidence levelP2-06Tiered compliance filter3 layers: prompt + evaluator + regex (R3-Q3).Known-bad ads caught; zero false negativesP2-07End-to-end integration testFull pipeline with checkpoint-resume: start, kill, resume (R3-Q2).Resumed run = identical output to clean run
Phase 3: A/B Variant Engine + UGC Video — v2 (Days 4–7)
Goal: A/B variant testing with multi-model image orchestration. UGC video generation via Veo. Image generation + evaluation baseline now in Phase 1.
TicketTitleDescriptionAcceptance CriteriaP3-01Nano Banana 2 integration (cost tier)Add Gemini 3.1 Flash Image as cheap alternative for variant volume. Route: Pro for hero images, Flash for variants.Both models producing images; cost tracked separatelyP3-02Single-variable A/B variants — copyControl + 3 copy variants each changing one element (R2-Q6). Same image across variants to isolate copy impact.Winning patterns identified per audience segmentP3-03Single-variable A/B variants — imageSame copy + 3 image variants (different setting, tone, subject). Isolate visual impact on coherence and attribute scores.Image variants produced; coherence scores comparedP3-04Image style transfer experimentsTest different visual styles per audience: UGC-inspired for students, polished/aspirational for parents.Style-audience mapping documented with scoresP3-05Multi-model orchestration docDocument which model does what and why (R1-Q4). Per-model cost attribution across text, image, and video tiers.Architecture doc with rationale and cost comparison across all 3 creative formatsP3-06Multi-aspect-ratio batch generationFor published ads: generate 1:1, 4:5, and 9:16 variants. Verify each passes attribute checklist.All 3 ratios generated per published ad; all pass checklistP3-07Veo integration + video spec extractionIntegrate Veo 3.1 Fast API for UGC video generation. Video spec extraction from expanded briefs (Section 4.9.2). Generate 2 video variants per ad (anchor + alternative scene/pacing). 9:16 default for Stories/Reels.Videos generated from brief; video specs logged; 2 variants produced per adP3-08Video attribute evaluatorMultimodal Gemini Flash call: video frames + video spec → 10-attribute checklist (hook timing, UGC authenticity, pacing, text legibility, brand safety, etc.). Pass threshold: all Required pass. (Section 4.9.4)Each attribute scored per variant; failures logged with diagnosticsP3-09Script-video coherence checkerMultimodal coherence verification: ad copy + video → 4-dimension coherence score (message alignment, audience match, emotional consistency, narrative flow). Below 6 = incoherent. (Section 4.9.5)Coherence scores logged; incoherent pairs trigger targeted regenP3-10Video Pareto selection + regen loopSelect best of 2 variants by composite score. On failure: targeted regen with diagnostic (1 retry, max 3 videos total). Graceful degradation: if video fails, ad publishes with copy + image only.Best variant selected; regen triggers on failure; video-blocked ads fall back to image-onlyP3-11Three-format ad assemblyExtend full ad assembly (P1-18) to include video alongside copy + image. Multi-format output: feed image + Stories/Reels video. Meta placement mapping. (Section 4.9.7)Published ads contain copy + image + video (where enabled); export includes all formatsP3-12Video cost trackingExtend token attribution to track video generation costs (per-video, per-variant, per-regen, audio vs. silent). Unified cost-per-publishable-ad across all 3 formats.Dashboard shows text + image + video cost breakdownP3-1310-ad video pilot runFull pipeline with video enabled: 10 ads, 2 variants each. Verify video attribute pass rate, coherence scores, and graceful degradation on failures.10 ads with video generated; video scores logged; failures degrade to image-only

Phase 4: Autonomous Engine — v3 (Days 7–14)
Goal: Self-healing autonomous engine with agentic orchestration and competitive intelligence.
TicketTitleDescriptionAcceptance CriteriaP4-01Agentic orchestration layerResearcher → Writer → Editor → Evaluator with error boundaries (R3-Q1).Failures contained; diagnostics loggedP4-02Self-healing feedback loopWire: SPC + brief mutation + quality ratchet + explore trigger.Simulated drop detected, diagnosed, and recoveredP4-03Competitive intelligence — automated refresh + trend analysisExtend P0-09 pattern database with automated monthly refresh workflow, temporal trend tracking (strategy shifts over time), and seasonal analysis. Competitive dashboard panel (Section 4.8.7).Trend data visible in dashboard; strategy shift alerts; seasonal patterns documentedP4-04Cross-campaign transferShared structural patterns + isolated content (R3-Q8).Insights transferable via campaign_scope tagsP4-05Performance-decay exploration triggerExplore-exploit logic (R2-Q9): exploit by default, explore on plateau.Exploration triggers; successful patterns promotedP4-06Full marginal analysis engineQuality gain per regen attempt, per model, per dimension (R1-Q7). Auto-adjust budget.System caps low-marginal-return regenerationP4-07Narrated pipeline replayChronological replay from decision ledger (R2-Q10). Failures highlighted.Full operation walkthrough with reasoning
Phase 5: Dashboard, Documentation & Submission (Days 12–14)
Goal: Build the live performance dashboard, produce all submission deliverables, and ensure visible reasoning throughout.
TicketTitleDescriptionAcceptance CriteriaP5-01Dashboard data export scriptexport_dashboard.py reads JSONL ledger via pandas, aggregates into dashboard_data.json covering all 8 panels (Section 4.5): hero metrics, per-cycle stats, dimension averages, correlation matrix, token attribution, SPC data, compliance results, ad library with rationales.Script runs after pipeline; JSON contains all panel data; re-runnableP5-02Dashboard HTML — Pipeline Summary + Iteration CyclesPanels 1–2: hero KPIs (ads generated, publishable rate, avg score, score lift, cost per ad, total tokens), per-cycle before/after cards with dimension improvement tags.All 8 hero metrics render; cycle cards show before/after scores + dimension badgesP5-03Dashboard HTML — Quality Trends + Dimension Deep-DivePanels 3–4: score progression chart (with ratchet threshold line), dimension-over-time lines, passing rate bars, cost efficiency trend, dimension averages, distribution box plots, correlation heatmap, weakest dimension frequency, floor violation counts.4 chart views toggle correctly; correlation matrix renders with r > 0.7 flagged redP5-04Dashboard HTML — Ad LibraryPanel 5: filterable ad browser (audience, goal, score range, cycle, status). Per-ad cards with Meta-formatted copy, color-coded scores, per-dimension mini-chart, expandable contrastive rationales, expandable lifecycle timeline. Curated before/after pairs at top.All 50+ ads browsable; filters work; rationales expand; 3 before/after pairs shownP5-05Dashboard HTML — Token EconomicsPanel 6: cost attribution stacked bars, cost-per-ad trend, marginal analysis chart, model routing pie, cache hit rate, projected cost at 1000 ads.All 6 sub-panels render; projected cost computed and displayedP5-06Dashboard HTML — System Health + Competitive IntelPanels 7–8: SPC control charts with canary markers, confidence histogram, escalation log, compliance pass/fail, quality ratchet timeline, competitor pattern database (if available).SPC charts render; ratchet line is monotonically increasing; compliance shows zero false negativesP5-07Decision logEvery major choice as ADR + narrative reflection (R4-Q9): options considered, chosen, why, limitations, "what surprised me," "where assumptions were wrong."Covers all 5 ambiguous elements + major architectural choices; honest about failuresP5-08Technical writeup (1–2 pages)Architecture, methodology, key findings, quality trends, per-token results.Concise; covers all areasP5-09Demo video (7 min, Problem-Solution-Proof)Act 1: naive approach fails. Act 2: architecture overview. Act 3: before/after pair, quality ratchet, self-healing, cost dashboard, top 3 ads. (R4-Q5)Pre-recorded, edited, ≤ 7 minutes; shows dashboard in Act 3P5-10Generated ad library export50+ ads with full scores, rationales, lifecycle as JSON/CSV.Complete metadata; filterableP5-11README with one-command setupSetup instructions, usage, configuration, architecture overview, dashboard launch instructions.New developer runs pipeline + opens dashboard in < 5 minutes
7. Success Criteria & Rubric Alignment
7.1 Quantitative Targets
CategoryMetricTargetTicketsCoverageFull ads (copy + image) with evaluation50+P1-20Text DimensionsIndependently measured5, proven independentP1-04, P2-01, P2-02Visual QualityImage attribute pass rate≥80% on all published adsP1-15Text-Image CoherenceCoherence score≥6/10 on all published adsP1-16Text QualityAds meeting 7.0/10 text thresholdMajority of final outputP1-07, P1-10ImprovementQuality gain over cyclesMeasurable lift across 3+P1-10, P1-20ExplainabilityEvaluations with rationales100% (text + visual)P1-04, P1-15DocumentationDecision log with reasoningComplete and honestP5-07TestsUnit/integration≥10 (targeting 15+)P0-07, P2-01–P2-07ReproducibilityDeterministic runsSeed-based + snapshot replayP0-03Application LayerMulti-session internal toolAuth + session CRUD + progress + curationPA-01–PA-12Session ModelImmutable, reproducible sessionsOne session = one pipeline runPA-02, PA-04DeploymentOne-command production deployDocker Compose on single VMPA-12
7.2 Rubric Weight Alignment
Rubric Area (Weight)TargetHow This PRD Addresses ItQuality Measurement & Evaluation (25%)23–25 (Excellent)5 independent dimensions with CoT evaluation, calibrated against reference ads, confidence scoring, quality ratchet, documented weighting rationaleSystem Design & Architecture (20%)18–20 (Excellent)Modular structure, checkpoint-resume, 15+ tests, deterministic seeds, context management via distillationIteration & Improvement (20%)18–20 (Excellent)5+ cycles, documented intervention-dimension causation, marginal analysis, performance-per-token awarenessSpeed of Optimization (15%)14–15 (Excellent)Batch-parallel processing, tiered routing, result caching, smart exploration triggeringDocumentation & Thinking (20%)18–20 (Excellent)Decision log, narrated replay, honest limitations, visible reasoning throughout
7.3 Bonus Points Targeted
AchievementPointsTicketSelf-healing / automatic quality improvement+7P4-02Multi-model orchestration with clear rationale+3P1-06 (text routing), P1-14 (Nano Banana Pro), P3-05 (orchestration doc covering text + image + video), P3-07 (Veo integration)Performance-per-token tracking (ROI awareness)+2P1-11, P4-06Quality trend visualization+2P5-03 (Dashboard Panel 3)Competitive intelligence from Meta Ad Library+10P0-09 (initial scan), P0-10 (query interface), P1-01 (pipeline integration), P4-03 (automated refresh + trends)
Total bonus targeted: +24 points
8. Risk Register
RiskImpactProbabilityMitigationEvaluator halo effect (dimensions not independent)HighMediumInversion tests (P2-01) + correlation analysis (P2-02). CoT decomposition reduces it structurally.API rate limits cause pipeline stallsMediumHigh (free tier)Checkpoint-resume (P0-08) + fixed delays. Batch sizing tuned to limits.Feedback loop oscillation (dimension collapse)HighMediumPareto-optimal selection (P1-07) structurally prevents regression.Evaluator drift over long runsMediumLow-MediumSPC monitoring (P2-04) with automatic canary injection.Brief expansion hallucinating product claimsHighMediumGrounding constraints (P1-01) + compliance filter (P2-06) + regex.Cold-start: bad first batch pollutes calibrationHighLowEvaluator calibrated before first generation (P0-06).Token budget overrunMediumMediumToken attribution (P1-11) + marginal analysis (P4-06) + caching (P1-12) + tiered routing (P1-06).Insufficient reference ads from SlackMediumMediumSupplement with Meta Ad Library competitor ads (P0-05).Nano Banana Pro rate limits stall image pipelineMediumMediumBatch image requests; generate images after text passes triage (only for 5.5+ scored ads). Cache generated images by visual spec hash.AI image artifacts (extra fingers, warped faces)HighLow-MediumMulti-variant generation (3 per ad) means artifacts in one variant don't block the ad — Pareto selection picks a clean sibling. Attribute checklist (P1-15) catches artifacts. Targeted regen (P1-17) with "no distortions" appended as fallback.Text-image incoherence (mismatched ad + image)MediumLow-MediumCoherence checker (P1-16) runs on all 3 variants — best coherence score wins Pareto selection (60% weight). Shared semantic brief (Section 4.6.2) prevents by design. Targeted regen with fix_suggestion as fallback.Image generation cost overrun at scaleMediumMedium3 variants per ad = 3x image cost. Mitigated: generate extra aspect ratios only for published winners. Budget tier in brief config falls back to single-image. Third-party providers at ~$0.02–0.05/image for cost reduction.Multi-variant selection bias (one strategy always wins)LowMediumTrack variant win rates (anchor vs. tone vs. composition). If one strategy dominates >80%, adjust visual spec defaults to incorporate winning strategy and reduce to 2 variants. Logged in variant metadata for continuous improvement.Veo video quality inconsistencyMediumMediumUGC aesthetic is forgiving of imperfections, but artifacts in faces/text are still noticeable. Attribute checklist catches major failures. Graceful degradation: failed videos don't block ad — publishes with copy + image only.Video generation cost overrunHighMedium$0.90/video × 2 variants = $1.80/ad before regen. Budget cap in brief config (default $20). Silent mode saves 33%. 10-ad pilot before scaling to 50. Video toggle defaults to off.Veo API rate limits or availabilityMediumLow-MediumSame Google ecosystem as Gemini — shared rate limit awareness. Pipeline generates video after image selection (not in parallel) to stagger API load. Checkpoint-resume covers mid-batch failures.SynthID watermark concerns for production adsLowLowSynthID is imperceptible. Meta does not reject SynthID-watermarked images. Document in decision log.Application layer delays pipeline deliveryMediumMediumPhase 1B runs in parallel with Phase 2. PA-01–PA-04 (backend scaffold) can start as soon as P1-02 works. Pipeline stays CLI-testable regardless.Celery worker crashes mid-pipelineMediumLowCheckpoint-resume (P0-08) applies at the application layer too. Failed sessions restart from last checkpoint. Session status shows "Failed — Resumable."SSE connection drops during "Watch Live"LowMediumFrontend reconnects automatically with exponential backoff. Session list polling (30s) provides fallback visibility. No data loss — SSE reads from immutable ledger.Curation layer edits conflate with generated metricsMediumLowStrict separation: curation lives in its own DB table. Dashboard metrics always read from immutable session data. Curated Set tab clearly labels "as-generated" vs. "as-edited."
9. Technical Dependencies
DependencyTypeNotesGemini API (Flash + Pro)External APIFree tier at ai.google.dev; 15 RPM (Flash), 2 RPM (Pro)Nano Banana Pro (Gemini 3 Pro Image)External API (v1)Image generation for full ads. ~$0.13/image (1K). Access via Google AI Studio API key.Nano Banana 2 (Gemini 3.1 Flash Image)External API (v2)Cost-tier image generation for A/B variant volume. ~$0.02–0.05/image via third-party providers.Veo 3.1 Fast (Google)External API (v2)UGC video generation for Stories/Reels. ~$0.15/sec ($0.90/6-sec video). Same API key as Gemini/Nano Banana Pro.Meta Ad LibraryPublic dataFree; no API — manual or semi-automated collectionReference ads from SlackInternal dataProvided via Gauntlet/Nerdy Slack channelPython 3.10+RuntimePrimary languageFastAPIBackend frameworkApplication layer API (R5-Q7)React (Vite)Frontend frameworkSession list, brief config, progress view, dashboard shell (R5-Q7)PostgreSQLDatabaseUser accounts, session metadata, curation state (R5-Q7)Celery + RedisTask queueBackground pipeline execution + SSE pub/sub (R5-Q4)Google OAuth 2.0Auth provider@nerdy.com SSO, per-user session isolation (R5-Q5)Docker + Docker ComposeDeploymentSingle-VM production deployment (R5-Q10)Claude in ChromeBrowser extensionSemi-automated competitive intelligence extraction from Meta Ad Library (Section 4.8)pandas + matplotlibLibrariesLedger queries + visualization
10. Ticket Summary
PhaseNameTicketsTimelinePhase 0Foundation & Calibration10 tickets (P0-01 – P0-10)Day 0–1Phase 1Full-Ad Pipeline (v1: Copy + Image)20 tickets (P1-01 – P1-20)Days 1–4Phase 1BApplication Layer (Sessions, Auth, UX)12 tickets (PA-01 – PA-12)Days 3–5Phase 2Testing & Validation7 tickets (P2-01 – P2-07)Days 3–4Phase 3A/B Variant Engine + UGC Video (v2)13 tickets (P3-01 – P3-13)Days 4–7Phase 4Autonomous Engine (v3)7 tickets (P4-01 – P4-07)Days 7–14Phase 5Dashboard, Docs & Submission11 tickets (P5-01 – P5-11)Days 12–14TOTAL80 tickets14 days

Recommended Read Order
Assignment spec → Round 1 → Round 2 → Round 3 → Round 4 → Round 5 → 9 Architectural Pillars → PRD Phases
Recommended Build Order
Pipeline track: P0-03 (seed + snapshot) → P0-02 (decision ledger) → P0-09 (competitive pattern scan — can run in parallel, human-in-the-loop) → P0-10 (pattern query interface) → R3-Q6 (evaluation prompt) → P0-06 (cold-start calibration) → P1-01 (brief expansion with competitive context) → P1-02 (copy generation) → P1-14 (Nano Banana Pro + multi-variant generation) → P1-15 (visual attribute eval + Pareto selection) → P1-16 (coherence checker) → P1-17 (image regen loop) → P1-08 (text regeneration loop) → P1-07 (text Pareto selection) → P1-13 (batch processing) → P1-18 (full ad assembly) → everything else.
Application track (can start in parallel after P1-02): PA-01 (FastAPI scaffold + Docker Compose) → PA-02 (DB schema) → PA-03 (Google SSO) → PA-04 (Session CRUD API) → PA-05 (brief config form) → PA-06 (session list UI) → PA-07 (progress reporting) → PA-09 (dashboard integration) → PA-10 (curation layer) → PA-12 (production deployment).
The five load-bearing components: the evaluation prompt (R3-Q6), the decision ledger (R2-Q8), the visual spec extraction pipeline (Section 4.6.2), the session model (Section 4.7.2), and the competitive pattern database (Section 4.8.3).

End of Document