# PJ-06 Primer

**Source plan:** [`PJ-00-phase-plan.md`](PJ-00-phase-plan.md) — §7 (Five-phase onboarding loop) and §3 decision 9 (industry hints in prompt).
**For:** New Cursor Agent session
**Date:** 2026-06-08
**Previous work:** PJ-05 (tools + validators) merged. See `docs/development/DEVLOG.md`.
**Status:** ⏳ Not started

---

# Ticket PJ-06: Onboarding system prompt + 5 phases

## What Is This Ticket?

The tools exist; the whitelist scopes them. Now the agent needs to actually be a good interviewer. This ticket builds the **system prompt** — a phase-aware prompt assembler that composes:

1. A constant identity preamble.
2. A phase-specific section telling the LLM what to extract in this phase, which tools to favor, and when to call `advance_phase`.
3. (Phase 3 only) An industry hints block selected by the user's `industry` field — paragraphs of guidance for `tutoring`, `restaurant`, `saas`, `fitness`, `professional_services`.
4. A profile snapshot (so the LLM doesn't re-ask filled fields).

Per PJ-00 §3 decision 9, industries live as **prompt paragraphs**, not data files. Adding a new industry is 5–10 lines edited into this module.

### Why It Matters

- The quality of the user's brand profile is set by the quality of these prompts.
- The "tutoring vs. restaurant produce materially different Phase 3 conversations" success criterion (§15.2) is satisfied here.
- Hooks the per-phase whitelist from PJ-05 into the LLM's view of "what can I do right now."

---

## What Was Already Done

- **PJ-04** — Endpoint accepts a `system_prompt` parameter into the loop.
- **PJ-05** — Tools + validators + `whitelist_for(touchpoint, phase)`.
- `app/api/routes/agent.py` currently uses a stub prompt (`"You are the onboarding agent..."`).

---

## What This Ticket Must Accomplish

### Goal

Replace the stub prompt with a phase-aware composer that emits an effective Gemini prompt for each of the five onboarding phases + an industry hints block at Phase 3.

### Deliverables Checklist

#### A. Implementation

- [ ] `app/api/agent/prompts.py` — `build_onboarding_prompt(profile, phase) -> str` composes:
  - Constant **identity preamble** (role, voice, tool-use guidance).
  - **Phase block** for the current phase (one of 5 sections below).
  - **Industry hints block** (Phase 3 only) keyed by `profile.industry`.
  - **Profile snapshot** appended at the end so the LLM knows what's already filled.
  - **Tool whitelist hint** ("Tools available right now: …") so the LLM doesn't hallucinate unavailable ones.
- [ ] Phase blocks (per PJ-00 §7):
  - **Identify** — goal: capture `business_name` + `industry`. Typical 2–4 turns.
  - **Core** — goal: capture `audience`, `mission`, `value_props≥2`, `tone_descriptors≥2`. Typical 5–8 turns.
  - **Extras** — goal: ≥3 keys in `extras` via `update_extra`. Industry hints active. Typical 4–7 turns.
  - **Assets** — goal: prompt for logo upload + style guide. Use `ingest_asset`. User can skip. Typical 2–5 turns.
  - **Good-enough** — goal: confirm summary, call `mark_good_enough`, then `finish_touchpoint`.
- [ ] Industry hints (Phase 3 only, per PJ-00 §7.3):
  - `tutoring` — subjects_taught, grade_levels, parent_vs_student_skew, test_prep_vs_subject_help, results_proof
  - `restaurant` — cuisine_style, dietary_niches, dine_in_vs_delivery_skew, ambiance, signature_dishes
  - `saas` — icp_segment, acv_tier, free_trial_vs_demo_first, churn_signals, integration_story
  - `fitness` — modality, class_size, body_composition_vs_performance_focus, equipment_needs
  - `professional_services` — practice_area, geo, individual_vs_business_clients, fee_structure
  - Fallback: a generic paragraph telling the LLM to ask about audience nuance, pricing model, and proof points.
- [ ] `app/api/agent/prompts.py` also exposes:
  - `build_post_session_prompt(profile, session_summary) -> str`
  - `build_pre_session_prep_prompt(profile, session_type) -> str`
  - `build_refine_prompt(profile) -> str`
- [ ] Update `app/api/routes/agent.py` to call the right builder per `touchpoint`.

#### B. Tests (`tests/test_api/test_agent_prompts.py`)

- [ ] `test_identify_phase_prompt_mentions_business_name` — prompt string contains "business name" hint.
- [ ] `test_core_phase_prompt_mentions_value_props_min` — prompt mentions the ≥2 requirement.
- [ ] `test_extras_phase_includes_tutoring_hints` — profile.industry='tutoring' → prompt contains "subjects_taught".
- [ ] `test_extras_phase_includes_restaurant_hints` — profile.industry='restaurant' → prompt contains "cuisine_style".
- [ ] `test_extras_phase_unknown_industry_uses_fallback` — profile.industry='circus' → prompt contains the generic hint paragraph.
- [ ] `test_profile_snapshot_includes_filled_fields` — profile with `business_name='Acme'` → prompt mentions Acme.
- [ ] `test_whitelist_hint_omits_unavailable_tools` — phase='identify' → prompt does not list `mark_good_enough`.
- [ ] (Optional, behavioral) `test_two_industries_produce_different_prompts` — diff `extras_phase('tutoring')` vs `extras_phase('restaurant')` — > 200 char delta.

#### C. Integration Expectations

- [ ] `agent.py` dispatches on `touchpoint` to call the right builder.
- [ ] No tool/validator changes.
- [ ] `tool_decls` list reflects `whitelist_for(touchpoint, phase)` from PJ-05.

#### D. Documentation

- [ ] DEVLOG entry: `## 2026-XX-YY — PJ-06: Onboarding system prompt + 5 phases (✅)`.
- [ ] Doc the "adding a new industry = 5–10 line prompt edit" mantra in the DEVLOG note.

---

## Branch & Merge Workflow

```bash
git switch final-submission && git pull
git switch -c feature/PJ-06-onboarding-prompts
git add app/api/agent/prompts.py app/api/routes/agent.py tests/test_api/test_agent_prompts.py
git commit -m "feat(PJ-06): phase-aware onboarding prompt + industry hints"
git push -u origin feature/PJ-06-onboarding-prompts
```

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/api/agent/prompts.py` | The phase-aware composer |
| `tests/test_api/test_agent_prompts.py` | Prompt-content assertions |

### Files to Modify

| File | Action |
|------|--------|
| `app/api/routes/agent.py` | Dispatch to the right `build_*_prompt` per touchpoint |

### Files to NOT Modify

- `app/api/agent/toolbox.py`, `validators.py`, `whitelist.py` — frozen from PJ-05.

### Files to READ for Context

| File | Why |
|------|-----|
| `docs/development/tickets/PJ-00-phase-plan.md` §7 | Five-phase spec + industry hints content |
| `app/api/agent/whitelist.py` | The tool list to mention in the prompt |

---

## Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Industries as prompt text | PJ-00 §3 decision 9 | No `brand_knowledge_<industry>.json`; paragraphs in `prompts.py` |
| Profile snapshot inlined | PJ-00 §6.3 | Prompt reminds LLM what's already filled to avoid re-asking |
| Whitelist hint in prompt | implementation detail | LLM behaves better when it knows what tools exist; whitelist enforcement still server-side |
| Phase-aware not free-form | PJ-00 §3 decision 5 | 5 fixed phases; LLM picks questions within each phase |

---

## Suggested Implementation Pattern

```python
# app/api/agent/prompts.py
from app.models.brand_profile import BrandProfile
from app.api.agent.whitelist import whitelist_for

IDENTITY = """You are the AdEngine Onboarding Agent. Your job is to learn the user's
brand by chatting, then store what you learn via tool calls. Be warm, concise, and
specific — never ask three questions in one turn. Call exactly one tool per turn:
either to save what you just learned, advance the phase, or ask the user (terminal)."""

PHASE_IDENTIFY = """## Phase: Identify
Goal: learn the business name and industry.
Ask 2–4 turns max. When you know both, call `save_field` for each, then
`advance_phase('core', why=...)`. Industry should be one of:
tutoring | restaurant | saas | fitness | professional_services | other.
"""

PHASE_CORE = """## Phase: Core
Goal: fill the typed-core fields the ad pipeline reads.
- audience (free text, who buys)
- mission (one sentence)
- value_props (list, ≥2)
- tone_descriptors (list, ≥2, e.g. 'warm', 'data-driven')
Use `save_field` per field. When all are filled, `advance_phase('extras', ...)`.
"""

PHASE_EXTRAS = """## Phase: Extras
Goal: capture industry-specific facts the pipeline can use as background.
Use `update_extra(key, value, ...)` with snake_case keys. Aim for ≥3 entries.
"""

INDUSTRY_HINTS = {
    "tutoring": """### Hints for tutoring brands
Probe: subjects_taught, grade_levels, parent_vs_student_skew (who pays vs who uses),
test_prep_vs_subject_help, results_proof (score lifts, college admits).""",
    "restaurant": """### Hints for restaurant brands
Probe: cuisine_style, dietary_niches, dine_in_vs_delivery_skew, ambiance, signature_dishes.""",
    "saas": """### Hints for SaaS brands
Probe: icp_segment, acv_tier, free_trial_vs_demo_first, churn_signals, integration_story.""",
    "fitness": """### Hints for fitness brands
Probe: modality, class_size, body_composition_vs_performance_focus, equipment_needs.""",
    "professional_services": """### Hints for professional-services brands
Probe: practice_area, geo, individual_vs_business_clients, fee_structure.""",
}
INDUSTRY_FALLBACK = """### Hints for brands in less common industries
Probe audience nuance, pricing/monetization model, and the proof points the brand
relies on for credibility."""

PHASE_ASSETS = """## Phase: Assets
Goal: capture visual identity. Ask the user to drop a logo (PNG/SVG) and optionally
a style guide PDF in the chat. When `uploaded_asset_ids` arrives, call `ingest_asset`
for each, then confirm extracted palette/fonts with the user before `save_field`.
User can skip — say "no assets yet" — that's fine, then `advance_phase('good_enough', ...)`.
"""

PHASE_GOOD_ENOUGH = """## Phase: Good-enough
Goal: confirm a summary of what we have. If user confirms, call `mark_good_enough()`,
then `finish_touchpoint(summary=...)`. If `mark_good_enough` is rejected, the error
tells you what's missing — go back and ask the user."""

PHASES = {
    "identify": PHASE_IDENTIFY,
    "core": PHASE_CORE,
    "extras": PHASE_EXTRAS,
    "assets": PHASE_ASSETS,
    "good_enough": PHASE_GOOD_ENOUGH,
}

def _snapshot(profile: BrandProfile) -> str:
    filled = {k: getattr(profile, k) for k in (
        "business_name","industry","audience","mission","value_props",
        "tone_descriptors","palette_primary_hex"
    ) if getattr(profile, k)}
    extras_keys = list((profile.extras or {}).keys())
    return f"### Profile snapshot\nFilled fields: {filled}\nExtras keys: {extras_keys}"

def build_onboarding_prompt(profile, phase: str) -> str:
    parts = [IDENTITY, PHASES.get(phase, PHASE_IDENTIFY)]
    if phase == "extras":
        parts.append(INDUSTRY_HINTS.get(profile.industry, INDUSTRY_FALLBACK))
    parts.append(_snapshot(profile))
    tools = whitelist_for("onboarding", phase)
    parts.append(f"### Tools available: {', '.join(tools)}")
    return "\n\n".join(parts)
```

The post_session / pre_session_prep / refine builders are short — each ~10–20 lines composing IDENTITY + a touchpoint-specific block + snapshot. See PJ-00 §8 for content.

---

## Edge Cases to Handle

1. `profile.industry IS NULL` at Phase 3 — fall through to `INDUSTRY_FALLBACK`. Should not happen in practice (Phase 2 fills it) but defensive.
2. Very long `extras` dict — truncate snapshot to top 10 keys to stay within Gemini token budget.
3. LLM gets `assets` whitelist but user uploaded no files — prompt explicitly tells it skipping is OK.
4. User's `industry='other'` — fallback hint engaged; LLM asks open-ended Phase 3 questions.
5. Snapshot includes secrets? `brand_profile` doesn't hold any; safe.

---

## Definition of Done

- [ ] All eight tests pass.
- [ ] Manual smoke: `curl POST /api/agent/converse` with `touchpoint='onboarding'` produces a phase-appropriate opening.
- [ ] Two-industry smoke: set `industry='tutoring'` vs `'restaurant'` and confirm Phase 3 prompts differ.
- [ ] `ruff check .` clean.
- [ ] DEVLOG entry prepended.
- [ ] Feature branch pushed.

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Prompt writing (identity + 5 phase blocks + 5 industry hints) | 120 min |
| Other touchpoint builders | 45 min |
| `agent.py` dispatch wiring | 30 min |
| Tests | 90 min |
| Manual smoke + iteration | 60 min |
| DEVLOG + commit | 15 min |
| **Total** | **~1 day** |

---

## After This Ticket: What Comes Next

- **PJ-07** — Chat UI consumes phase state & prompts via `/converse`
- **PJ-10** / **PJ-11** — other touchpoints reuse builders defined here
