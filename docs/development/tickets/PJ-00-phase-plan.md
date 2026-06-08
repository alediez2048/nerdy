# PJ Phase Plan: Multi-Tenant Brand Profile + Onboarding Agent

**Project:** AdEngine — Autonomous Ad Generation Platform
**Date:** 2026-06-07
**Previous work:** P0–P5, PA, PB, PC, PD, PF, PG, PH, PI complete + BYO API Keys feature shipped 2026-06-05 (`d02e07a` on `main`). See `docs/development/DEVLOG.md`.
**Status:** Design approved — implementation tickets PJ-01..PJ-13 to follow.
**Approach chosen:** In-house focused conversational extractor (Gemini function-calling) + flat-key brand profile + 4 triggered touchpoints. Hermes Agent the framework rejected after evaluation; "Hermes" name dropped in favor of "Onboarding Agent."
**Successor to:** `data/brand_knowledge.json` (Varsity Tutors hardcoded) — replaced by per-user `brand_profile` rows. Pipeline reads only the user's profile.

---

## 1. Problem statement

The platform was designed for one customer (Varsity Tutors). Today's pipeline reads `data/brand_knowledge.json` — a Varsity-specific facts/personas/competitive file — and `data/config.yaml` Varsity-specific defaults at every brief-expansion call. Every Clerk user signing in on production runs against the same tutoring assumptions. The result is:

- A restaurant signing up gets tutoring-flavored ads.
- The "industry" concept doesn't exist in the data model.
- There's no place for users to encode their own audience, mission, value props, voice, palette, or do/don't rules.
- Sessions can't be tailored per business without code edits.
- The system has no memory of what worked for *this* user across sessions.

BYO API Keys (shipped 2026-06-05) solved per-user credentials. PJ solves the parallel problem for per-user **brand context**: every user brings their own brand. The platform's job is to learn that brand once, refine it over time, and make every pipeline call brand-aware.

The user's vision: a "system that grows with you." After brainstorming, that translates concretely to:
- A flat key-value brand profile the LLM writes into.
- A conversational onboarding agent that fills the profile via chat (industry-adaptive).
- The same agent re-engages at multiple touchpoints (post-session reflection, pre-session prep, settings refine) to keep accumulating context.
- The existing pipeline reads the profile instead of hardcoded tutoring data.

---

## 2. Goals & non-goals

### Goals

1. **Multi-tenant brand context:** every user has a `brand_profile` row; pipeline runs read it; no global brand fallback.
2. **Adaptive intake:** an LLM-driven 5-phase onboarding conversation that asks industry-relevant questions. A tutoring brand and a restaurant should get materially different conversations.
3. **Grows with you:** four touchpoints (onboarding · post-session reflection · pre-session prep · refine-in-settings) accumulate into the same profile over time. `brand_profile.updated_at` advances; `extras` JSON gains keys; `conversation_messages` keeps the receipts.
4. **Strict gate, mirroring BYO Keys:** sessions blocked until `brand_profile.good_enough_at IS NOT NULL`. Same pattern, same failure mode, same UX shape as the API-key gate.
5. **Asset capture:** users upload logo, style guide PDF, optional reference images during onboarding; Gemini multimodal vision pass extracts palette hex codes and detected fonts, persists them into typed columns.
6. **Industry extensibility without schema migration:** adding a new industry is a paragraph edit in a system prompt — no new tables, no new files.
7. **Documentation alignment:** every existing reference + deliverable doc that today describes the tutoring-specific platform gets refreshed to reflect the multi-tenant brand-aware architecture.

### Non-goals (deferred)

- **Always-on chat widget** — onboarding + 3 other triggered touchpoints are enough. A persistent sidebar widget is phase 2 if ever.
- **Brand knowledge graph / entity-relation model** — flat key-value bag is sufficient. Graph deferred indefinitely.
- **Brand voice validation as a pipeline step** — "does this ad align with brand voice?" critic is not in scope. Existing media quality evaluator (PI) is unchanged.
- **Programmatic competitive scraping for the user's industry** — out of scope; the existing competitive intel module is Varsity-specific and stays as-is for now (refresh deferred).
- **Self-serve industry templates** — no UI for "I'm in industry X, fill in some defaults." Industry hints live as paragraphs in the system prompt; adding new industries is a developer task.
- **Migration of pre-PJ sessions** — pre-PJ sessions stay readable with their existing data. The onboarding gate applies only to new session creation. Existing Varsity-flavored content is not regenerated.
- **Honcho / agentskills.io / Hermes Agent the framework** — explicitly rejected after architecture review. Reasons documented in §3.

---

## 3. Decisions log

The load-bearing decisions, captured to prevent re-litigation mid-implementation.

1. **Onboarding-finish model = "never done" + lightweight gate.** No "you're done" state. `good_enough_at` gates sessions but the profile keeps growing forever after.
2. **Schema rigidity = typed core + open extras.** ~10 fixed typed columns the pipeline + UI rely on, plus `extras JSONB` for whatever the LLM picks up. Open bag for flexibility, typed bones for reliability.
3. **Touchpoints = triggered (not always-on).** Four discrete touchpoints: `onboarding`, `post_session`, `pre_session_prep`, `refine`. All hit the same `/api/agent/converse` endpoint.
4. **Pipeline integration = strict per-user replace.** No `brand_knowledge.json` fallback. Empty profile = no sessions, mirror of BYO Keys.
5. **Question-selection policy = phased outer loop + LLM intra-phase.** 5 fixed phases (Identify · Core · Extras · Assets · Good-enough). LLM picks questions within each phase. Backend rejects out-of-phase tool calls.
6. **Assets in-chat (with vision pass).** Logo + style guide upload happens in Phase 4 of onboarding via file drop in the chat UI. Gemini multimodal extracts palette + fonts. Files live on Railway volume; metadata in `brand_assets` table.
7. **Conversation runtime = synchronous request/response.** One `/converse` call per turn, returns next assistant message + profile snapshot. No Celery, no SSE — Gemini's function-calling loop is fast (sub-10s). Avoids the SSE auth dance and matches the chatbot UX pattern.
8. **Hermes Agent the framework — rejected.** It's a self-hosted Python CLI agent for one developer per install, not a multi-tenant SaaS embed. Wrong UI surface (CLI/messaging gateways, not React), wrong audience (power users, not non-technical business owners), wrong storage (local files, not Postgres), wrong scope (40+ tools, 6 terminal backends — we want one focused extractor). The "grows with you" goal is a database + context-injection pattern we can build natively in ~3 weeks.
9. **Industry hints = prompt content, not data files.** Per-industry guidance lives as paragraphs in the Phase 3 system prompt. Adding a new industry is a prompt edit, not a new JSON file. No `brand_knowledge_<industry>.json` proliferation.
10. **Tool whitelist enforcement is backend-side.** The LLM is not trusted with phase advancement, good_enough gate, or schema validation — every tool call is validated server-side. The LLM is the policy, the backend is the law.

11. **(GRILL Q1)** **Onboarding agent uses a separate host-side key, not BYO.** The strict-BYO pipeline still requires the user's own `GEMINI_API_KEY` for sessions. But the onboarding chat itself runs on a new env var `AGENT_GEMINI_API_KEY` set on the API server. Reason: requiring users to bring their own key *before* the entry-point conversation would create a permanent deadlock — Settings is reachable only after onboarding, but onboarding needs an LLM. Host-pay is bounded (~25 turns × ~5K tokens per user, once).

12. **(GRILL Q2)** **`user_id` is closure-bound, never an LLM-visible argument.** The agent endpoint creates a per-request `ToolBox` instance that captures `user_id` from the verified Clerk JWT. Tool function signatures sent to Gemini do NOT declare `user_id` as a parameter. If a jailbreak attempt makes the LLM try to inject one, the function signature rejects it. Cross-tenant writes from the LLM surface are physically impossible.

13. **(GRILL Q3)** **Existing users get a one-shot backfill, not an onboarding wall.** On PJ-ship, a migration reads each existing user's most-recent session `config` JSON (which already carries `audience`, `campaign_goal`, `persona`, `key_message`) and pre-fills a `brand_profile` row with `good_enough_at = now()`. Existing users see a "Welcome back — we set up your brand profile from your past sessions" banner; they can refine in Settings whenever. New signups still go through the full 5-phase onboarding.

14. **(GRILL Q4)** **Hybrid runtime: sync chat + async vision pass via Celery.** Chat turns are synchronous request/response (95% of turns are 3–5s, acceptable). The slow path (multimodal vision on uploaded assets, 15–25s) runs as a Celery task triggered by `POST /api/brand-assets/{id}/extract`. Frontend polls until ready, then sends the next `/converse` with the asset_id already enriched. Avoids the SSE auth dance and keeps the chat path tight.

15. **(GRILL Q5)** **Full 4-touchpoint scope confirmed.** Onboarding, post-session reflection, pre-session prep, and refine — all four ship in PJ. No MVP cut. ~17.5 day estimate stands.

16. **(GRILL Q6)** **Pre-session prep = chat THEN form, not chat instead of form.** The agent's pre-session-prep modal collects only the *brief-shaped* fields (audience, persona, campaign_goal, key_message, creative_brief) via 4–6 turn chat. On accept, the existing `NewSessionForm` opens with those 5 fields pre-filled (still editable). The user sets technical fields (aspect_ratio, model, video duration, etc.) on the form. One new tool `propose_brief(audience, persona, campaign_goal, key_message, creative_brief)` is added — it returns the brief draft to the frontend without writing to `brand_profile`.

---

## 4. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          React Frontend                           │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Onboarding │  │ Settings →   │  │ Post-Session Reflection  │  │
│  │ wizard     │  │ "Refine your │  │ modal (opens after each  │  │
│  │ (5 phases) │  │ brand"       │  │ session completes)        │  │
│  └─────┬──────┘  └──────┬───────┘  └──────────────┬───────────┘  │
│                        │ Pre-Session Prep         │              │
│                        │ (modal on session create)│              │
│                        ▼                          ▼              │
│                    <Chat /> reusable component                    │
│              file-drop · message list · tool-call render          │
└─────────────────────────────┬────────────────────────────────────┘
                              │  POST /api/agent/converse
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                           │
│                                                                   │
│  /api/agent/converse — single endpoint, 4 touchpoint modes        │
│    1. Load brand_profile + last 20 messages for this touchpoint   │
│    2. Run vision pass on any new uploaded_asset_ids               │
│    3. Gemini function-calling loop (max 8 iters):                 │
│       save_field, update_extra, ingest_asset,                     │
│       advance_phase, mark_good_enough,                            │
│       ask_user, finish_touchpoint                                 │
│    4. Persist messages + field writes                             │
│    5. Return {assistant_message, phase, good_enough_now,          │
│              profile_snapshot, asset_extractions?}                │
│                                                                   │
│  /api/brand-assets — POST upload, GET serve (auth-gated, scoped)  │
│                                                                   │
│  Pipeline (existing, modified):                                   │
│    generate/brief_expansion.py — reads brand_profile (typed +     │
│    extras) instead of data/brand_knowledge.json.                  │
│    Session creation route (POST /api/sessions) — rejects with     │
│    403 + reason="brand_profile_not_ready" if good_enough_at NULL. │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                          PostgreSQL                               │
│  brand_profile           — typed columns + extras JSONB           │
│  conversation_messages   — append-only log per user+touchpoint    │
│  brand_assets            — uploaded files metadata + facts        │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  Railway volume: output/brand_assets/<user_id>/
```

---

## 5. Data model

### 5.1 `brand_profile`

One row per Clerk user.

```sql
CREATE TABLE brand_profile (
  user_id              TEXT PRIMARY KEY,
  -- Typed core (the pipeline reads these directly)
  business_name        TEXT,
  industry             TEXT,                          -- 'tutoring' | 'restaurant' | 'saas' | 'fitness' | 'professional_services' | …
  audience             TEXT,                          -- free text
  mission              TEXT,
  value_props          TEXT[],                        -- array, min 2 for good_enough
  tone_descriptors     TEXT[],                        -- array, min 2 for good_enough
  avoid_phrases        TEXT[],
  do_dont_rules        JSONB,                         -- {"do":[...], "dont":[...]}
  palette_primary_hex  TEXT,
  palette_secondary_hex TEXT,
  palette_accent_hex   TEXT,
  logo_asset_id        UUID REFERENCES brand_assets(id),
  -- Open extension (LLM-driven, industry-specific keys)
  extras               JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Lifecycle
  onboarding_phase     TEXT NOT NULL DEFAULT 'identify',
                                                     -- identify|core|extras|assets|good_enough|complete
  good_enough_at       TIMESTAMPTZ,                   -- session gate flips when set
  created_at           TIMESTAMPTZ DEFAULT now(),
  updated_at           TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_brand_profile_industry ON brand_profile (industry);
```

### 5.2 `conversation_messages`

```sql
CREATE TABLE conversation_messages (
  id           BIGSERIAL PRIMARY KEY,
  user_id      TEXT NOT NULL,
  touchpoint   TEXT NOT NULL,                         -- onboarding|post_session|pre_session_prep|refine
  session_id   TEXT REFERENCES sessions(session_id),  -- non-null for post_session + pre_session_prep
  role         TEXT NOT NULL,                         -- user|assistant|tool
  content      TEXT,
  tool_calls   JSONB,
  tool_results JSONB,
  phase        TEXT,                                  -- snapshot of onboarding_phase
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_conversation_messages_lookup
  ON conversation_messages (user_id, touchpoint, session_id, created_at);
```

### 5.3 `brand_assets`

```sql
CREATE TABLE brand_assets (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           TEXT NOT NULL,
  asset_type        TEXT NOT NULL,                    -- logo|style_guide|font|reference|other
  original_filename TEXT,
  storage_path      TEXT NOT NULL,                    -- relative to output/brand_assets/
  mime_type         TEXT,
  size_bytes        INTEGER,
  extracted_facts   JSONB,                            -- vision-pass output
  created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_brand_assets_user ON brand_assets (user_id);
```

### 5.4 Migration approach

Same pattern as PG/BYO Keys: model imported in `app/db.py`, `Base.metadata.create_all` at startup creates the tables. No alembic in this project.

---

## 6. Conversation loop + tools

### 6.1 Endpoint

```
POST /api/agent/converse
Headers: Authorization: Bearer <clerk_jwt>
Body: {
  touchpoint: 'onboarding' | 'post_session' | 'pre_session_prep' | 'refine',
  session_id?: string,
  user_message?: string,
  uploaded_asset_ids?: string[]
}

Returns 200: {
  assistant_message: string,
  phase: string,
  good_enough_now: boolean,
  profile_snapshot: BrandProfile,
  asset_extractions?: {asset_id: {palette: [...], fonts: [...], notes: string}}
}

Returns 403 if user has no brand_profile row and touchpoint != 'onboarding'.
Returns 422 on tool-call validation failure surfaced to LLM (not user-facing).
```

### 6.2 Tools

| Tool | Purpose | Backend enforcement |
|---|---|---|
| `save_field(name, value, confidence, rationale)` | Write a typed-core column on `brand_profile`. | Name must be in TYPED_COLUMNS allowlist. Value validated per column (hex format for palette, array for value_props, etc.). |
| `update_extra(key, value, confidence, rationale)` | Stash a free-form fact in `brand_profile.extras`. | Key normalized to snake_case. Value JSON-serializable. |
| `propose_brief(audience, persona, campaign_goal, key_message, creative_brief)` | (`pre_session_prep` only) Return a session brief draft to the frontend. Does NOT write to brand_profile. | Validated as a complete brief shape. Returned in the response payload. |
| `ingest_asset(asset_id, derive_palette, derive_fonts)` | Run vision pass on uploaded asset and persist findings. | asset_id must belong to current user. derive_* flags gate which Gemini multimodal probes run. |
| `advance_phase(next_phase, why)` | Move `onboarding_phase` forward. | Only callable during `onboarding` touchpoint. Phase order strictly enforced; can't skip. |
| `mark_good_enough()` | Sets `good_enough_at = now()`. | Rejected unless gate conditions met (§7.5). |
| `ask_user(message)` | Terminal turn action — returns to user. | Loop exits. |
| `finish_touchpoint(summary)` | Terminal — wraps the conversation. | Loop exits. For `onboarding` also sets `onboarding_phase = 'complete'`. |

### 6.3 Loop

```python
def converse(touchpoint, user_id, user_message, session_id, uploaded_asset_ids):
    profile = load_brand_profile(user_id) or create_empty(user_id)
    history = load_messages(user_id, touchpoint, session_id, limit=20)

    if user_message:
        append_message(role="user", content=user_message)

    for asset_id in uploaded_asset_ids or []:
        facts = vision_extract(asset_id)
        save_asset_extracted_facts(asset_id, facts)

    system_prompt = build_system_prompt(touchpoint, profile, history)
    tool_whitelist = whitelist_for(touchpoint, profile.onboarding_phase)

    for _ in range(MAX_TOOL_ITERATIONS):  # = 8
        resp = gemini.generate_content(system_prompt, history, tools=tool_whitelist)
        if resp.function_call.name in ("ask_user", "finish_touchpoint"):
            break
        result = execute_tool(resp.function_call)
        append_message(role="tool", tool_results=result)

    return {assistant_message, phase, good_enough_now, profile_snapshot}
```

### 6.4 Safety rails

- **Per-phase tool whitelist** — `mark_good_enough` rejected in `identify` phase; `advance_phase('assets')` rejected before typed-core minimums met. Backend not LLM.
- **MAX_TOOL_ITERATIONS = 8** — bounded loop.
- **MAX_MESSAGES_RETURNED = 20** — context bounded.
- **Validation on `save_field`** — hex codes regex-checked, arrays type-checked, enums constrained.
- **Per-user data scope** — every query keyed on `user_id` from Clerk JWT. Zero cross-user leakage.

---

## 7. Five-phase onboarding loop

### 7.1 Phase Identify

Goal: know the business + industry.
Requires: `business_name`, `industry`.
Typical 2–4 turns.

### 7.2 Phase Core

Goal: fill typed-core fields the pipeline reads.
Requires: `audience`, `mission`, `value_props` (≥2), `tone_descriptors` (≥2).
Typical 5–8 turns.

### 7.3 Phase Extras

Goal: capture industry-specific facts via the open bag.
Requires: ≥3 keys written to `extras` (soft target — LLM uses judgment).
Industry hints injected into system prompt at this phase only. Examples:

- `tutoring`: subjects_taught, grade_levels, parent_vs_student_skew, test_prep_vs_subject_help, results_proof
- `restaurant`: cuisine_style, dietary_niches, dine_in_vs_delivery_skew, ambiance, signature_dishes
- `saas`: icp_segment, acv_tier, free_trial_vs_demo_first, churn_signals, integration_story
- `fitness`: modality, class_size, body_composition_vs_performance_focus, equipment_needs
- `professional_services`: practice_area, geo, individual_vs_business_clients, fee_structure

Adding a new industry = 5–10 lines in the Phase 3 system prompt. No code, no data file.
Typical 4–7 turns.

### 7.4 Phase Assets

Goal: capture brand visual identity.
LLM asks for logo upload; optionally style guide PDF. Vision pass returns palette + fonts; LLM confirms with user before saving.
User can skip ("no assets yet") → palette/logo stay null; pipeline uses neutral palette downstream.
Typical 2–5 turns.

### 7.5 Good-enough gate

Backend-enforced. `mark_good_enough` rejected with structured error unless ALL of:
- `business_name`, `industry`, `audience`, `mission` non-null
- `len(value_props) >= 2`
- `len(tone_descriptors) >= 2`

The LLM sees the error and adapts ("you still need 1 more value prop"). When the gate passes, `good_enough_at = now()` is set and sessions unlock.

### 7.6 UI progress display

Five clickable dots labeled `Identify · Core · Extras · Assets · Ready`. Click any dot post-onboarding to open a `refine` touchpoint scoped to that phase's fields.

---

## 8. Touchpoints (4 modes of the same endpoint)

### 8.1 `onboarding`

- Triggered: first sign-in detects `brand_profile` row missing OR `onboarding_phase != 'complete'`.
- UI: dedicated `/onboarding` route, redirect-from-anywhere if not complete.
- System prompt: phased policy per §7.
- Ends: when `finish_touchpoint` called (which requires `good_enough_at` set).

### 8.2 `post_session`

- Triggered: pipeline completion event (`pipeline_complete` or `video_pipeline_complete`).
- UI: modal on session detail page when session transitions to `completed`; can be dismissed.
- System prompt: reads session's ledger summary (top dimensions, winner reasons). Asks 1–2 short reflection questions. Calls `update_extra` / `save_field` based on user feedback. Example: "Your best-scoring variant won on emotional resonance via the parent-anxiety angle — should I make that the default emotional angle for future sessions?" → on yes → `save_field("default_emotional_angle", "parent_anxiety", confidence=high, rationale="user confirmed after session sess_X")`.
- Ends: `finish_touchpoint` after 1–3 turns. User can dismiss without engaging.

### 8.3 `pre_session_prep`

- Triggered: user clicks "Create Session" → modal pops up with the assistant pre-proposing a complete brief based on the profile.
- UI: modal on `/sessions/new`; modal contains a chat interface where the assistant proposes a brief, user can refine via natural language, accept when ready.
- System prompt: reads `brand_profile` + the session-type selection (image vs video). Generates a full `creative_brief` proposal aligned with profile. Engages user only if they want to refine.
- Tools used: read-only mostly (no `save_field` calls), only `ask_user` and `finish_touchpoint`. Output: a finalized `creative_brief` text that becomes the session's `config.creative_brief`.
- Ends: `finish_touchpoint` returns the brief, frontend uses it for the session config.

### 8.4 `refine`

- Triggered: user clicks "Refine your brand" in Settings or a phase dot.
- UI: chat modal scoped to whatever the user wants to update.
- System prompt: free-form. "User wants to revisit their brand profile. Help them update fields or extras as needed."
- Tools used: `save_field`, `update_extra`, `ingest_asset` (re-upload), `ask_user`, `finish_touchpoint`.
- Ends: user closes the modal or `finish_touchpoint`.

---

## 9. Asset upload + vision pass

### 9.1 Upload flow

1. Chat UI accepts file drop (`.png`, `.jpg`, `.pdf`, `.svg` for logos; `.pdf` for style guides; size ≤ 10 MB).
2. Frontend POSTs to `/api/brand-assets` with `multipart/form-data` + `asset_type`. Returns `{asset_id, storage_path}`.
3. Frontend includes `uploaded_asset_ids: [<id>]` in next `/converse` call.
4. Backend runs vision pass (Gemini multimodal) and stores results in `brand_assets.extracted_facts`.
5. The LLM sees the extracted facts in the next system-prompt context block and confirms them with the user before calling `save_field` for palette/logo.

### 9.2 Vision pass details

| Asset type | Probes |
|---|---|
| logo | Dominant colors (top 3 hex), background type (transparent / solid / photo), inferred fonts in wordmark if any |
| style_guide PDF | OCR text → extract palette hex callouts, font names, "do/don't" rules |
| reference | Color tone, mood descriptors |
| font | Font family name detection only (filename heuristic + first-page render) |

Implemented as 1–2 multimodal Gemini calls per asset using `call_gemini_multimodal`. Results returned as structured JSON the LLM can interpret.

### 9.3 Storage

- Path: `output/brand_assets/<user_id>/<asset_uuid>.<ext>` on the Railway volume (same volume as `output/images/` and `output/videos/`).
- Serving: `GET /api/brand-assets/{asset_id}` returns the file. Auth-gated (Clerk JWT, scoped to user). Path traversal guarded.
- Lifecycle: deleted on user delete (cascade from Clerk auth removal). No retention policy beyond that for v1.

---

## 10. Frontend chat UI

### 10.1 Reusable `<Chat />` component

- Props: `touchpoint`, optional `session_id`, optional initial `system_message`, callback `onCompleted(profile)`.
- Renders: message list (user/assistant/tool), input box with file-drop, "Sending..." state, optimistic UX (user message appears immediately, "assistant typing…" indicator).
- Calls: `POST /api/agent/converse` per turn.

### 10.2 Views consuming `<Chat />`

| View | Path | Behavior |
|---|---|---|
| `Onboarding` | `/onboarding` | 5-dot progress bar at top, redirects-from-root if `onboarding_phase != 'complete'`. |
| `Settings` (modified) | `/settings` | Adds a "Brand Profile" card with: phase progress, "Refine your brand" button (opens `refine` modal), typed-field summary, extras viewer. |
| `SessionDetail` (modified) | `/sessions/:id` | When `status` becomes `completed`, auto-opens a `post_session` reflection modal (dismissible). |
| `NewSessionForm` (modified) | `/sessions/new` | Opens a `pre_session_prep` modal when user clicks "Create Session" — assistant proposes brief, user accepts/refines, then real session creation proceeds. |

### 10.3 Asset upload UX

Inline file-drop zone inside the chat. When user drops a file, it uploads via `/api/brand-assets`, the chat shows a "✓ Uploaded logo.png" inline card, and the next `/converse` call includes the `asset_id`. Extracted facts (palette swatches, detected fonts) render as a confirmation card inside the chat message stream.

### 10.4 Onboarding gate enforcement

- Server-side: `POST /api/sessions` returns 403 with `detail: "brand_profile_not_ready"` when `good_enough_at IS NULL`. Frontend routes the user to `/onboarding`.
- Client-side: `App.tsx` auth gate checks profile readiness on mount; if not ready, redirect to `/onboarding`.
- Sessions list page renders a banner: "Complete onboarding to create sessions" with a CTA button.

---

## 11. Pipeline integration

### 11.1 Files modified

| File | Change |
|---|---|
| `generate/brief_expansion.py` | Replace `load_brand_kb('data/brand_knowledge.json')` with `load_brand_profile_for_user(user_id)`. The expanded brief construction now reads from the user's `brand_profile.value_props`, `audience`, `mission`, `tone_descriptors`, `avoid_phrases`, `do_dont_rules`, and `extras`. |
| `generate/competitive.py` | Today this reads Varsity-specific competitive data. For PJ v1, this stays as-is for tutoring users; non-tutoring users get an empty competitive landscape. Refresh deferred to a later phase (PK or later). |
| `app/api/routes/sessions.py` | `POST /api/sessions` gates on `good_enough_at IS NOT NULL`. Returns 403 with structured detail if not. |
| `app/workers/tasks/pipeline_task.py` | Loads `brand_profile` for `session_row.user_id` at task start; passes it through to `_run_image_pipeline` / `_run_video_pipeline` instead of (or alongside) the BYO env-override context. |
| `iterate/pipeline_runner.py` | `PipelineConfig` gains a `brand_profile: BrandProfile` field; downstream callers read from it. |
| `iterate/pipeline_orchestrator.py` | Same — accepts and threads through brand profile. |
| `data/brand_knowledge.json` | **Deleted.** Pre-PJ sessions referencing it stay readable from their ledgers; nothing new uses it. |
| `data/config.yaml` | Varsity-specific defaults (`brand`, `key_message`, `persona` defaults) removed. Per-user defaults come from brand_profile. |

### 11.2 Backward compatibility

- Pre-PJ sessions: their `config` JSON column already contains the resolved brand/persona/key_message at the time they ran. They render the same as before — no regeneration.
- The `brand_knowledge.json` file is deleted from the repo; any code path that imported it gets refactored.
- BYO Keys interaction: PJ does not change the BYO Keys gate. Sessions need BOTH `brand_profile.good_enough_at` AND the user's API keys to run. Both checks happen at session-create time.

---

## 12. Documentation refresh

This is a complex refactor that meaningfully changes the platform narrative. Every doc that today describes the tutoring-specific platform needs an update. Doc updates are **acceptance criteria** for the phase, not afterthoughts.

| Severity | File | Required updates |
|---|---|---|
| Major | `docs/reference/prd.md` | Reframe from "Varsity Tutors ad generator" to "multi-tenant brand-aware ad platform with onboarding agent." Strip tutoring-specific language; add the multi-tenant model. |
| Major | `docs/reference/requirements.md` | Drop Varsity-specific functional requirements; add multi-tenant brand profile + onboarding agent requirements. |
| Major | `docs/deliverables/systemsdesign.md` | Add agent layer + brand profile + asset storage to the systems diagram. Update narrative to describe the 4 touchpoints and the per-user pipeline read. |
| Major | `docs/deliverables/demo-script.md` | Restructure: onboarding is now the front-door demo step. Walk through onboarding → first session → post-session reflection. |
| Moderate | `docs/reference/PRODUCTION.md` | Document new tables (`brand_profile`, `conversation_messages`, `brand_assets`), new endpoints (`/api/agent/converse`, `/api/brand-assets`), new env vars if any. Note the new `/onboarding` route in the Vercel deploy. |
| Moderate | `docs/reference/ENVIRONMENT.md` | Document local setup for the agent — model selection, vision pass dependencies. |
| Moderate | `docs/deliverables/model_orchestration.md` | Add the Gemini function-calling loop as a new orchestration pattern alongside brief/generation/eval. |
| Moderate | `docs/deliverables/feedback_loop_architecture.md` | Add the post-session reflection touchpoint as a new feedback loop alongside the quality ratchet and regen loop. |
| Moderate | `docs/deliverables/writeup.md` | Reflect multi-tenant + agent product story. |
| Minor | `docs/deliverables/decisionlog.md` | Add the 10 decisions from §3 as a new dated entry. |
| Minor | `docs/deliverables/ai-tools.md` | Note Gemini function-calling + multimodal vision usage in the agent. |
| Minor | `CLAUDE.md` / `AGENTS.md` | Project state — new PJ phase, ticket status table. |
| Per-ticket | `docs/development/DEVLOG.md` | Entry per ticket, prepended to top. |

The doc refresh ticket (`PJ-12`) is a single focused pass through all of these; estimated 2–3 days of writing.

---

## 13. Ticket breakdown

Implementation tickets to be written via the `writing-plans` skill after this PRD is approved. Each ticket gets its own primer at `docs/development/tickets/PJ-NN-primer.md`.

| # | Ticket | Scope | Est. effort |
|---|---|---|---|
| PJ-01 | DB models + migration scaffold | 3 new tables (`brand_profile`, `conversation_messages`, `brand_assets`), SQLAlchemy models, imports in `app/db.py`, smoke test the table creation. | 0.5d |
| PJ-02 | Brand assets API + storage | `POST /api/brand-assets`, `GET /api/brand-assets/{id}`, file storage under `output/brand_assets/<user_id>/`, path-traversal guard, auth scope. | 1d |
| PJ-03 | Vision pass module | `app/api/vision.py` — Gemini multimodal probes for logo (palette + bg), style_guide PDF (OCR + facts), reference images. Returns structured JSON. | 1.5d |
| PJ-04 | Agent endpoint scaffold | `POST /api/agent/converse` endpoint with mode dispatch, message persistence, profile loading, tool-call loop infrastructure (no real tools yet). | 1d |
| PJ-05 | Agent tools + validators | `save_field`, `update_extra`, `ingest_asset`, `advance_phase`, `mark_good_enough`, `ask_user`, `finish_touchpoint`. Per-phase whitelisting. Validation rules. | 1.5d |
| PJ-06 | Onboarding system prompt + 5 phases | Phase-specific prompt sections, industry hints block for Phase 3, good-enough gate validation. | 1d |
| PJ-07 | Onboarding chat UI | `<Chat />` reusable component, `/onboarding` view, 5-dot progress bar, file-drop, optimistic message UX, app-level redirect when phase != 'complete'. | 2d |
| PJ-08 | Settings page brand profile section | New "Brand Profile" card on `/settings`: phase progress, typed-field summary, extras viewer, "Refine your brand" button opening the `refine` touchpoint modal. | 1d |
| PJ-09 | Pipeline rewire | Modify `brief_expansion.py`, `pipeline_task.py`, `pipeline_runner.py`, `pipeline_orchestrator.py` to read brand_profile per user. Delete `data/brand_knowledge.json`. Add gate in `POST /api/sessions`. | 2d |
| PJ-10 | Post-session reflection touchpoint | Modal in `SessionDetail` that auto-opens on completion; reads ledger summary; 1–2 question script via the agent. | 1d |
| PJ-11 | Pre-session prep touchpoint | Modal in `NewSessionForm` that proposes a brief from the brand profile and lets user refine via chat before session create. | 1.5d |
| PJ-12 | Documentation refresh | All doc updates per §12. | 2.5d |
| PJ-13 | Verification gate | End-to-end test runbook (manual), ruff + pytest + tsc clean, full demo walkthrough captured. Mirrors PI-11 / PH-07. | 1d |

**Total estimated effort:** ~17.5 days (~3.5 weeks of focused work).

Tickets PJ-01 → PJ-04 are foundation and must land first. PJ-05, PJ-06, PJ-07 form the onboarding MVP (can ship that as an intermediate milestone). PJ-09 is the highest-risk ticket (pipeline rewire) and should land before PJ-10/11 to give them a real pipeline to integrate with.

---

## 14. Risks

1. **Pipeline rewire breaks pre-PJ sessions.** Mitigation: pre-PJ session configs already contain resolved brand context; the rewire only affects new sessions. Verify with a pre-PJ session in the verification gate.
2. **Gemini function-calling latency makes onboarding feel slow.** Mitigation: cap tool iterations at 8; show "typing…" indicator; tool calls run server-side (no extra round-trips). If sub-10s is the typical turn time it's tolerable.
3. **Vision pass extracts wrong palette.** Mitigation: always confirm with user before `save_field`; allow manual hex entry as a fallback.
4. **LLM forgets a must-have field.** Mitigation: backend gate is the source of truth; the LLM physically can't `mark_good_enough` without meeting the criteria. Worst case the conversation rambles.
5. **Multi-tenant data leakage.** Mitigation: every query keyed on `user_id` from the verified Clerk JWT. Tested explicitly in PJ-13.
6. **Doc refresh becomes a tax.** Mitigation: scope is explicit in PJ-12; treat as part of definition-of-done, not optional polish.

---

## 15. Success criteria

The phase is complete when:

1. A brand-new user signing up via Clerk is routed through `/onboarding`, completes the 5-phase chat, and lands on `/sessions` with the gate unlocked.
2. Two different industries (say, tutoring and restaurant) produce materially different Phase 3 conversations and meaningfully different `extras` content.
3. A session run after onboarding produces ad copy that references the user's mission, value props, and audience — verified by manual inspection of one generated ad per industry.
4. Removing the user's `brand_profile.good_enough_at` (simulating mid-onboarding) blocks new session creation with a clear 403 + UI redirect.
5. Post-session reflection writes a new `extras` key when the user accepts the assistant's suggestion; the next session's brief reflects it.
6. All docs in §12 reflect the multi-tenant brand-aware architecture; no doc references `brand_knowledge.json`.
7. `ruff check .` clean, `pytest tests/` no PJ regressions, `npm run build` in `app/frontend` clean.
8. PJ-13 manual runbook executes end-to-end on a fresh user account.
