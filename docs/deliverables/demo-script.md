# Ad-Ops-Autopilot — Demo Video Script

**Format:** Pre-recorded narrated walkthrough, 7 minutes max
**Structure:** Problem → Solution → Proof (three-act narrative)

---

## Act 1: The Problem (~1.5 min)

### Narration

> "The hardest part of ad generation isn't generation — it's knowing what's good. Let me show you what happens when you just ask an LLM to write an ad."

### Screen: Terminal

```bash
# Show a naive prompt
python -c "
from google import genai
client = genai.Client()
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents='Write a Facebook ad for Varsity Tutors SAT prep.'
)
print(response.text)
"
```

> "Generic. Could be any tutoring company. No clear CTA. No emotional hook. Let's see what our evaluator thinks."

### Screen: Evaluator scoring the naive ad

```bash
python -c "
from evaluate.evaluator import evaluate_ad
result = evaluate_ad('Write a Facebook ad...', 'conversion', 'parents')
print(result)
"
```

> "Clarity 5.0, Value Proposition 4.5, Brand Voice 3.0. Below our 7.0 threshold on every dimension. The naive approach doesn't work because generation is easy — evaluation is the hard part."

---

## Act 2: The Architecture (~2 min)

### Narration

> "Ad-Ops-Autopilot solves this by building the evaluator first, then using it to drive a feedback loop."

### Screen: Architecture diagram (terminal or slide)

```
Brief → Expand → Generate → Evaluate → [Pass? Publish : Regenerate]
                     ↑                              |
                     └──── Pareto Selection ─────────┘
```

> "Four modules. Generate handles brief expansion and ad copy creation. Evaluate scores every ad across five independent dimensions using chain-of-thought evaluation. Iterate runs the feedback loop — Pareto selection, brief mutation, quality ratchet. Output produces the dashboard and exports."

### Key decisions to highlight (show code briefly):

1. **5-dimension evaluation** — "Not one quality score — five independent dimensions. Clarity, Value Proposition, CTA, Brand Voice, Emotional Resonance. Each with a contrastive rationale."

2. **Pareto selection** — "We don't tell the model 'improve CTA while keeping clarity.' That doesn't work. Instead, generate 5 variants, evaluate all 5, pick the Pareto-dominant one mathematically."

3. **Quality ratchet** — "The threshold starts at 7.0 and only goes up. `max(7.0, rolling_5batch_avg - 0.5)`. Standards never decrease."

4. **Brief mutation** — "After 2 failed regeneration cycles, we mutate the brief — not the ad. If Brand Voice is consistently low, inject stronger brand context into the brief."

---

## Act 3: The Proof (~3.5 min)

### 3a. Before/After Pair (~1 min)

> "Let me show you a real ad's journey through the pipeline."

### Screen: Terminal — show a specific ad's lifecycle

```bash
python scripts/show_published_ads.py
```

> "This ad started at 5.8 — weak CTA, generic value proposition. After one regeneration cycle with Pareto selection, it hit 7.5. The CTA went from 'Learn More' to 'Start your free practice test.' Value Proposition improved from generic tutoring to specific outcomes."

Show the before/after scores side by side.

### 3b. Dashboard Walkthrough (~2 min)

> "The 8-panel dashboard gives a complete view of system performance."

### Screen: Open dashboard HTML in browser

**Panel 1: Hero KPIs**
> "50+ ads generated, 40% publish rate, average score 7.5 for published ads."

**Panel 3: Quality Trends**
> "Score progression across batches. Notice the ratchet line — it rises with performance and never drops."

**Panel 4: Dimension Deep-Dive**
> "Per-dimension trends showing which dimensions improve fastest. The correlation heatmap flags any pair with r > 0.7 — we want independent dimensions, not a halo effect."

**Panel 5: Ad Library**
> "Every ad is browsable. Filter by status, sort by score, expand to see the full contrastive rationale."

**Panel 6: Token Economics**
> "Cost attribution by pipeline stage. The marginal analysis shows diminishing returns — cycle 1 gains 1.2 points, cycle 2 gains 0.5, cycle 3 gains 0.15. The system auto-recommends capping at 2 cycles."

**Panel 7: System Health**
> "SPC control chart monitors for evaluator drift. Confidence routing shows 80% of ads processed autonomously."

**Panel 8: Competitive Intelligence**
> "Hook type distribution across competitors. Gap analysis surfaces underused strategies."

### 3c. Top 3 Ads (~30 sec)

> "Here are the three highest-scoring ads from the run."

### Screen: Show top 3 ads with scores and copy

> "Each of these scored 7.5+ across all five dimensions, passed the brand voice floor, and was selected via Pareto dominance from 3-5 variants."

---

## Closing (~15 sec)

> "Ad-Ops-Autopilot: 50+ ads, 5 dimensions, measurable quality improvement per token spent. The system knows what it doesn't know, fixes what it can, and escalates what it can't. Thank you."

---

## Recording Notes

- **Screen recording tool:** QuickTime (macOS) or OBS
- **Resolution:** 1920x1080 minimum
- **Font size:** Terminal at 16pt+ for readability
- **Dashboard:** Use Chrome, zoom to 110% for visibility
- **Audio:** Record narration separately if possible, mix in post
- **Editing:** Cut dead time (pip installs, API waits). Aim for 6-7 minutes.
- **Fallback:** If no time to record, the dashboard HTML + this script serves as the walkthrough document
