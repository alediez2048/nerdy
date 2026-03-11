---
name: adops-generation
description: Ad copy generation pipeline for Ad-Ops-Autopilot — brief expansion, reference-decompose-recombine strategy, audience profiles, compliance, and structural atom management. Use when implementing or modifying generate/ modules, working on brief expansion, ad copy generation, brand voice profiles, or compliance filtering.
---

# Ad-Ops-Autopilot Generation Pipeline

## Pipeline Flow

```
Minimal Brief → Expand (grounded, R3-Q5) → Select structural atoms (R2-Q1)
  → Generate ad copy → Compliance filter (3-layer, R3-Q3) → Output
```

## Brief Expansion (R3-Q5)

Minimal briefs ("Parents, SAT prep, Conversion") contain almost no information. The expansion step adds richness WITHOUT hallucinating.

### Grounding Constraint

The expansion LLM receives:
1. The minimal brief (audience, product, campaign goal, tone)
2. The verified brand knowledge base (`data/brand_knowledge.json`)
3. An explicit instruction: "Expand using ONLY the following verified facts. Do NOT invent statistics, pricing, testimonials, or product features. Flag unverified claims."

### Expanded Brief Output

```json
{
  "brief_id": "brief_001",
  "audience": "parent",
  "product": "SAT prep",
  "campaign_goal": "conversion",
  "tone": "reassuring",
  "expanded": {
    "pain_points": ["college admissions anxiety", "comparing prep options", "wanting the best for their child"],
    "proof_points": ["10,000+ students helped", "200+ average point improvement"],
    "emotional_angle": "relief from anxiety through proven results",
    "hook_suggestions": ["question", "stat", "story"],
    "cta_alignment": "free assessment / practice test (low-friction conversion)"
  },
  "grounding_sources": ["brand_knowledge.json"],
  "unverified_flags": []
}
```

## Reference-Decompose-Recombine (R2-Q1)

This is the core generation strategy. The system does NOT prompt "write an ad." It recombines proven structural elements.

### Step 1: Select Reference Ads
From the pattern database, select 2–3 high-performing reference ads relevant to the audience and campaign goal.

### Step 2: Decompose into Structural Atoms
Each reference ad is broken into:
- **Hook type:** question, stat, story, fear
- **Body pattern:** problem-agitate-solution-proof-CTA, testimonial-benefit-CTA, stat-context-offer-CTA
- **CTA style:** free-trial, sign-up, learn-more, book-now
- **Tone register:** conversational-parent, motivating-student, authoritative-expert
- **Sentence length distribution:** average words per sentence

### Step 3: Recombine
The generation prompt specifies which atoms to use:
```
Create a new ad using:
- Hook type: question
- Body pattern: testimonial → benefit → CTA
- Tone: conversational-parent
- Average sentence length: 12 words
- CTA: free practice test

Brand context: [from knowledge base]
Expanded brief: [from expansion step]
```

## Audience-Specific Brand Voice Profiles (R1-Q6)

### Parent-Facing
- **Tone:** Authoritative, reassuring, outcome-focused
- **Drivers:** College admissions anxiety, comparison shopping
- **Register:** "Your child deserves expert guidance — not generic test prep."
- **Few-shot examples:** 3–4 on-brand parent-facing ads

### Student-Facing
- **Tone:** Relatable, motivating, peer-like
- **Drivers:** Test anxiety, score pressure, desire to prove themselves
- **Register:** "The SAT doesn't have to be scary. With a tutor who gets it, you can feel ready."
- **Few-shot examples:** 3–4 on-brand student-facing ads

The generator selects the correct profile based on the `audience` field in the brief. The evaluator scores Brand Voice against the matching audience rubric.

## Ad Output Schema

Every generated ad must produce ALL components:

```json
{
  "ad_id": "ad_001_cycle_1",
  "brief_id": "brief_001",
  "primary_text": "string (most important — stops the scroll)",
  "headline": "string (5–8 words, benefit-driven)",
  "description": "string (secondary, often truncated on mobile)",
  "cta_button": "Learn More | Sign Up | Get Started | Book Now | Start Free Practice Test",
  "audience": "parent | student",
  "campaign_goal": "awareness | conversion",
  "structural_atoms": {
    "hook_type": "question | stat | story | fear",
    "body_pattern": "problem-agitate-solution | testimonial-benefit | stat-context-offer",
    "cta_style": "free-trial | sign-up | learn-more | book-now",
    "tone_register": "conversational-parent | motivating-student | authoritative-expert"
  },
  "seed": 12345,
  "cycle_number": 1,
  "model_used": "gemini-flash",
  "tokens_consumed": 450
}
```

## Three-Layer Compliance Filter (R3-Q3)

All three layers must pass before an ad is forwarded to evaluation.

### Layer 1: Generation Prompt Constraints
Baked into every generation prompt:
- "Never make guarantees about specific score improvements"
- "Never use fear-based language implying the child is deficient"
- "Never reference competing brands negatively by name"
- "Always include factual basis sourced from the brand knowledge base"

### Layer 2: Evaluator Compliance Check
Binary pass/fail alongside the 5-dimension evaluation:
- "Does this ad contain any claims not supported by the brand knowledge base?"
- "Does this ad violate Meta advertising policies?"
- Compliance failure overrides quality score — rejected regardless.

### Layer 3: Regex/Keyword Filter (Deterministic, Zero Tokens)
```python
COMPLIANCE_PATTERNS = [
    (r"guaranteed?\s+\d+", "Guaranteed score claim"),
    (r"100\s*%", "Absolute guarantee"),
    (r"always\s+work", "Absolute promise"),
    (r"never\s+fail", "Absolute promise"),
    (r"Princeton\s+Review.*(?:worse|bad|terrible|inferior)", "Competitor disparagement"),
    (r"Kaplan.*(?:worse|bad|terrible|inferior)", "Competitor disparagement"),
    (r"\$\d+(?!.*(?:starting|from|as low as))", "Unqualified price claim"),
]
```

## Pattern Database

Winning patterns are promoted to the pattern database for future reference-decompose-recombine cycles:

```json
{
  "pattern_id": "pat_001",
  "hook_type": "question",
  "body_pattern": "problem-agitate-solution-proof-cta",
  "cta_style": "free-trial",
  "audience": "parent",
  "campaign_goal": "conversion",
  "avg_score": 8.2,
  "times_used": 5,
  "times_passed_threshold": 4,
  "campaign_scope": "universal"
}
```

Patterns with `campaign_scope: "universal"` transfer across campaigns (R3-Q8).

## Do NOT

- Prompt the LLM with "write an ad" — use reference-decompose-recombine
- Invent product facts — use ONLY the brand knowledge base
- Skip the compliance filter on any generated ad
- Use the same structural atom combination for every ad — vary for A/B learning
- Generate without logging the seed, model, and token count to the ledger
