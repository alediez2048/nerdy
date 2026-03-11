---
name: adops-evaluation
description: Evaluation framework for Ad-Ops-Autopilot — LLM-as-Judge design, chain-of-thought prompt structure, calibration strategy, dimension weighting, quality ratchet, and drift detection. Use when implementing or modifying evaluate/ modules, working on evaluator calibration, designing evaluation prompts, or building the quality ratchet.
---

# Ad-Ops-Autopilot Evaluation Framework

## Why This Is the Most Important Component

The evaluator is the single most important component in the system. If it scores inconsistently, the feedback loop amplifies noise. If its rationales are vague, the regeneration system has nothing actionable. Every design choice here must maximize discriminative power and actionable feedback.

The taste problem: The hardest part isn't generation — it's evaluation. Can your system reliably tell an 8/10 ad from a 5/10? If it can, the rest is plumbing. If it can't, nothing else matters.

## Five Quality Dimensions

| Dimension | Measures | Score 1 | Score 10 |
|-----------|----------|---------|----------|
| Clarity | Message understandable in <3 seconds? | Confusing, competing messages | Crystal clear single takeaway |
| Value Proposition | Specific, compelling benefit? | Generic ("we have tutors") | Differentiated ("raise SAT 200+ points") |
| Call to Action | Next step clear and low-friction? | No CTA or vague ("learn more") | Specific, urgent ("Start free practice test") |
| Brand Voice | Sounds like Varsity Tutors? | Generic, could be anyone | Distinctly empowering, knowledgeable, approachable |
| Emotional Resonance | Connects emotionally? | Flat, purely rational | Taps parent worry, student ambition, test anxiety |

## Campaign-Goal-Adaptive Weighting (R1-Q3)

| Dimension | Awareness | Conversion | Floor |
|-----------|-----------|------------|-------|
| Clarity | 25% | 25% | **6.0** (hard — violate = reject) |
| Value Proposition | 20% | 25% | — |
| CTA | 10% | 30% | — |
| Brand Voice | 20% | 10% | **5.0** (hard — violate = reject) |
| Emotional Resonance | 25% | 10% | — |

## Chain-of-Thought Evaluation Prompt (R3-Q6)

The evaluation prompt MUST enforce this 5-step sequence in a single API call:

```
Step 1: READ the ad completely.

Step 2: DECOMPOSE — Before scoring, identify in your own words:
  - The hook (first line/sentence)
  - The value proposition
  - The call to action
  - The emotional angle
  
Step 3: COMPARE each identified element against the rubric:
  - Reference the 1-score example (worst) and 10-score example (best) for each dimension
  - Where does this ad fall on that spectrum?

Step 4: SCORE each dimension with a CONTRASTIVE rationale:
  - "This ad scores [X] on [dimension] because [specific reason]."
  - "A version scoring [X+2] would [specific concrete change]."
  - "The gap is [specific element that needs to change]."

Step 5: FLAG CONFIDENCE per dimension (1–10).
  - Below 7 = flag for optional human review
  - Below 5 = pause pipeline, require human sign-off
```

## Evaluation Output Schema

```json
{
  "ad_id": "string",
  "scores": {
    "clarity": {
      "score": 7.5,
      "rationale": "Single clear message about SAT score improvement",
      "contrastive": "A 9.5 version would lead with the specific number in the first 5 words",
      "confidence": 8
    }
  },
  "aggregate_score": 7.2,
  "campaign_goal": "conversion",
  "weights_used": {"clarity": 0.25, "value_proposition": 0.25, "cta": 0.30, "brand_voice": 0.10, "emotional_resonance": 0.10},
  "meets_threshold": true,
  "effective_threshold": 7.0,
  "weakest_dimension": "emotional_resonance",
  "flags": ["low_confidence:emotional_resonance"],
  "compliance": {"passes": true, "violations": []}
}
```

## Cold-Start Calibration (R1-Q8)

Before the system generates a single ad:

1. Collect 20–30 competitor ads from Meta Ad Library (Princeton Review, Kaplan, Khan Academy, Chegg)
2. Manually label 5–10 as "excellent" and 5–10 as "poor"
3. Run the CoT evaluator against all labeled ads
4. Tune the evaluation prompt until: evaluator scores excellent ads ≥7.5 and poor ads ≤5.0
5. Store the calibrated reference set as `tests/test_data/golden_ads.json`

Combine with reference-seeded generation: decompose top reference ads into structural atoms for the generator.

## Quality Ratchet (R1-Q9)

```python
effective_threshold = max(7.0, rolling_5batch_average - 0.5)
```

- The 7.0 floor is **immutable** — it never changes
- If the system has been producing 8.2-average ads, the threshold rises to 7.7
- A temporary dip still clears 7.0 but would fail the ratcheted threshold
- Plot the effective threshold over time — it must be monotonically non-decreasing

## Evaluator Drift Detection — SPC (R1-Q1)

Track score distributions (mean, σ, skew) across every batch using control charts:

1. Compute rolling 5-batch mean and standard deviation per dimension
2. Set upper/lower control limits at ±2σ from the rolling mean
3. When a batch breaches limits → inject anchor/canary ads into next evaluation
4. If canary scores drift from baseline → halt pipeline and recalibrate prompt with few-shot examples

This catches drift that would make the 7.0 threshold meaningless over time.

## Contrastive Rationale Quality (R3-Q10)

The rationale is what the regeneration system uses to improve ads. Quality matters:

| Bad Rationale | Good Rationale |
|---------------|----------------|
| "Clarity could be improved" | "The opening hook competes with the value prop — the reader sees two messages before understanding either. A +2 version would lead with the score improvement number and delay the brand context to line 2." |
| "CTA is weak" | "The CTA says 'Learn More' which is generic. A +2 version would use 'Start Your Free Practice Test' — specific, low-friction, and aligned with conversion funnel." |

## Dimension Independence Validation (R2-Q3)

The evaluation framework claims 5 independent dimensions. Prove it:

1. **Inversion tests:** Degrade one dimension in a high-scoring ad. Only that score should drop (≥1.5) while others stay stable (±0.5).
2. **Correlation analysis:** Compute pairwise Pearson r across all scored ads. If any pair exceeds r > 0.7, the evaluator is applying a "general quality" halo — fix the prompt.
3. **Adversarial tests:** Wrong brand voice entirely (fast food), pure emotional manipulation with no substance, perfect clarity with zero CTA.

If dimensions aren't independent, the 5-dimension framework is a 1-dimension framework with extra steps.

## Do NOT

- Use single-pass holistic scoring — causes halo effects
- Use 5 separate API calls per dimension — too expensive (5x tokens)
- Provide free-text rationales without contrastive targets
- Skip the decomposition step (Step 2) before scoring
- Skip calibration against reference ads before running the pipeline
- Allow the quality threshold to decrease under any circumstance
- Treat correlation analysis as optional
