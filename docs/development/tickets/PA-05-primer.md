# PA-05 Primer: Brief Configuration Form (React)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-01 (FastAPI scaffold), PA-02 (database schema), PA-03 (Google SSO), PA-04 (Session CRUD API) must be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-05 builds the **React brief configuration form** — the primary entry point for users to start a new ad generation session. The form uses progressive disclosure: required fields up front, advanced settings behind an accordion. A "Clone from previous" button lets power users duplicate a prior session's config.

### Why It Matters

- **The Tool Is the Product** (Pillar 9): The form is the first thing users interact with — it must be fast, intuitive, and forgiving
- Progressive disclosure (R5-Q3) makes it fast for repeat users (3 fields) while deep for power users (8+ fields)
- Clone-from-previous reduces friction for iterative workflows — the most common usage pattern
- Client-side validation prevents bad requests and wasted API calls
- This form drives `POST /sessions` which triggers the entire pipeline

---

## What Was Already Done

- PA-01: FastAPI scaffold with Docker Compose (Vite dev server on port 5173)
- PA-02: Session model with config JSONB schema
- PA-03: Google SSO authentication (JWT tokens)
- PA-04: `POST /sessions` endpoint accepts brief config and triggers Celery pipeline

---

## What This Ticket Must Accomplish

### Goal

Build a single-page React form with progressive disclosure for brief configuration. Required fields are always visible; advanced fields hide behind an accordion. Clone-from-previous pre-fills all fields from a selected prior session.

### Deliverables Checklist

#### A. Brief Configuration Form (`app/frontend/src/components/BriefForm.tsx`)

- [ ] **Required Fields (always visible)**
  - `audience` — dropdown or text input (e.g., "Parents of SAT students", "High school juniors")
  - `campaign_goal` — radio buttons: "Awareness" or "Conversion"
  - `ad_count` — number input (min 1, max 100, default 10)
  - `name` — text input (optional, placeholder: "Auto-generated if blank")

- [ ] **Advanced Settings (accordion, collapsed by default)**
  - `threshold` — number input (default 7.0, step 0.1, min 5.0, max 10.0)
  - `weights` — 5 sliders for dimension weights (Clarity, Value Prop, CTA, Brand Voice, Emotional Resonance), must sum to 1.0
  - `model_tier` — radio: "Flash (fast/cheap)" or "Pro (quality/expensive)"
  - `budget_cap` — number input in dollars (optional)
  - `image_settings` — toggle for image generation on/off, aspect ratio selector

- [ ] **Accordion behavior**
  - Collapsed by default with "Advanced Settings" label and chevron
  - Click to expand/collapse
  - Shows count of non-default advanced settings when collapsed (e.g., "2 customized")

#### B. Form Validation

- [ ] Client-side validation before submit
  - `audience` — required, non-empty
  - `campaign_goal` — required, must be "awareness" or "conversion"
  - `ad_count` — required, integer, 1–100
  - `threshold` — if provided, must be 5.0–10.0
  - `weights` — if provided, must sum to 1.0 (±0.01 tolerance)
  - `budget_cap` — if provided, must be positive number
- [ ] Inline error messages next to invalid fields
- [ ] Submit button disabled while validation errors exist
- [ ] Clear visual distinction between required and optional fields

#### C. Clone-from-Previous

- [ ] "Clone from previous session" button above the form
- [ ] Opens a dropdown/modal listing recent sessions (fetches `GET /sessions?limit=10`)
- [ ] Selecting a session pre-fills ALL form fields from that session's config
- [ ] User can modify any pre-filled field before submitting
- [ ] Clear indication that fields were cloned (e.g., "Cloned from: Session Name")

#### D. Form Submission

- [ ] Submit sends POST to `/sessions` with JSON body matching `SessionCreate` schema
- [ ] Includes JWT token in Authorization header
- [ ] On success (201): redirect to session list or session detail page
- [ ] On error (400/422): display server validation errors
- [ ] On error (401): redirect to login
- [ ] Loading state on submit button (prevent double-submit)

#### E. API Integration (`app/frontend/src/api/sessions.ts`)

- [ ] `createSession(config: BriefConfig): Promise<Session>` — POST /sessions
- [ ] `listSessions(params?: ListParams): Promise<SessionListResponse>` — GET /sessions
- [ ] Axios or fetch with JWT interceptor
- [ ] Type definitions matching Pydantic schemas

#### F. Tests (`app/frontend/src/components/__tests__/BriefForm.test.tsx`)

- [ ] TDD first
- [ ] Test required fields show validation errors when empty
- [ ] Test form submits with valid required fields only
- [ ] Test advanced accordion expands/collapses
- [ ] Test weight sliders enforce sum-to-1.0 constraint
- [ ] Test clone pre-fills all fields from selected session
- [ ] Test submit button disabled during loading
- [ ] Test server error displayed on 400 response
- [ ] Minimum: 7+ tests

#### G. Documentation

- [ ] Add PA-05 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/PA-05-brief-config-form
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Progressive disclosure | R5-Q3 | Required fields always visible. Advanced behind accordion. Fast for repeat users, deep for power users. |
| Clone-from-previous | R5-Q3 | Most sessions are variations on a previous run. Clone reduces friction to ~2 clicks. |
| Client-side validation | R5-Q3 | Prevent bad requests. Inline errors. Submit disabled until valid. |
| React + Vite | R5-Q7 | Frontend stack matches Nerdy's existing tooling. |

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/components/BriefForm.tsx` | Brief configuration form component |
| `app/frontend/src/api/sessions.ts` | API client for session endpoints |
| `app/frontend/src/types/session.ts` | TypeScript type definitions |
| `app/frontend/src/components/__tests__/BriefForm.test.tsx` | Form tests |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/api/schemas/session.py` | Pydantic schemas defining expected request body (PA-04) |
| `app/api/routes/sessions.py` | Session endpoints this form submits to (PA-04) |
| `docs/reference/prd.md` (Section 4.7) | Progressive disclosure and brief config spec |

---

## Definition of Done

- [ ] Form submits to POST /sessions successfully
- [ ] Clone pre-fills all fields from a previous session
- [ ] Form validates before submit (client-side)
- [ ] Required vs. advanced fields properly separated
- [ ] Advanced accordion shows count of customized settings
- [ ] Loading state prevents double-submit
- [ ] Error handling for 400/401/422 responses
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**PA-06 (Session list UI)** builds the React session list page showing all user sessions as cards with metadata, filters, and search. It depends on the API client and type definitions from this ticket.
