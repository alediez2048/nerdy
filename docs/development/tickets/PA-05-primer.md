# PA-05 Primer: Brief Configuration Form (React)

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PA-04 (Session CRUD API) must be complete — `POST /sessions` with validated `SessionConfig`. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PA-05 builds the **React brief configuration form** — the "New Session" page where users configure a pipeline run. Uses progressive disclosure (R5-Q3): required fields always visible, advanced settings in an accordion.

### Why It Matters

- **The Reviewer Is a User, Too** (Pillar 8): The form is the first touchpoint — it must be intuitive
- Progressive disclosure prevents overwhelming new users while giving power users full control
- Clone-from-previous saves time for repeat users running similar campaigns
- This is the first React component — it establishes the frontend project structure

---

## What Was Already Done

- PA-04: `POST /sessions` with `SessionConfig` validation (audience, campaign_goal, ad_count + advanced fields)
- PA-03: Google SSO auth — JWT token available for API calls
- PRD Section 4.7.10: Full frontend component spec with design tokens

**No frontend code exists yet.** This ticket bootstraps the React app.

---

## What This Ticket Must Accomplish

### Goal

Set up the React (Vite) project and build the brief configuration form with progressive disclosure, validation, and clone-from-previous.

### Deliverables Checklist

#### A. React Project Setup (`app/frontend/`)

- [ ] `npm create vite@latest` with React + TypeScript template
- [ ] Install dependencies: `react-router-dom`, `axios` (or `fetch` wrapper)
- [ ] Configure Vite proxy to `localhost:8000` for API calls
- [ ] Design system tokens file from PRD Section 4.7.10:
  - `src/design/tokens.ts` — colors (ink, surface, cyan, mint, etc.), font (Poppins), radii (24px cards, 100px buttons)
- [ ] Base layout component with Nerdy branding

#### B. API Client (`src/api/sessions.ts`)

- [ ] `createSession(config: SessionConfig): Promise<SessionDetail>`
- [ ] `listSessions(filters?): Promise<SessionSummary[]>`
- [ ] `getSession(sessionId: string): Promise<SessionDetail>`
- [ ] Attach `Authorization: Bearer <jwt>` header from stored token
- [ ] Error handling with typed error responses

#### C. Brief Form Component (`src/views/NewSessionForm.tsx`)

- [ ] **Required fields (always visible):**
  - Audience selector: "Parents" / "Students" (radio or toggle)
  - Campaign Goal selector: "Awareness" / "Conversion" (radio or toggle)
  - Ad Count: number input (default 50, min 1, max 200)
- [ ] **Advanced settings (accordion/collapsible):**
  - Cycle count (1–10, default 3)
  - Quality threshold override (5.0–10.0, default 7.0)
  - Dimension weights preset: "Awareness Profile" / "Conversion Profile" / "Equal"
  - Model tier: "Standard" / "Premium"
  - Budget cap (USD)
  - Image generation toggle (default on)
  - Aspect ratios: checkboxes for 1:1, 4:5, 9:16
- [ ] **Clone-from-previous button:**
  - Shows recent sessions dropdown
  - Populates all form fields from selected session's config
  - User can modify before submitting
- [ ] **Submit button:**
  - Calls `POST /sessions` with form data
  - Shows loading state during submission
  - On success: redirect to session detail or Watch Live view
  - On error: display validation errors inline

#### D. Form Validation

- [ ] Client-side validation matching `SessionConfig` schema from PA-04
- [ ] Required field indicators
- [ ] Inline error messages
- [ ] Disable submit until required fields are filled

#### E. Types (`src/types/session.ts`)

- [ ] `SessionConfig` — matches backend schema
- [ ] `SessionSummary`, `SessionDetail` — matches API responses
- [ ] `ProgressSummary` — for running sessions

#### F. Tests

- [ ] Test required fields render and are interactive
- [ ] Test advanced accordion expands/collapses
- [ ] Test form validation prevents invalid submission
- [ ] Test clone-from-previous populates fields
- [ ] Test submit calls API with correct payload
- [ ] Minimum: 5+ tests

#### G. Documentation

- [ ] Add PA-05 entry in `docs/DEVLOG.md`

---

## Important Context

### Design System (PRD Section 4.7.10)

| Token | Value | Usage |
|-------|-------|-------|
| ink | #202344 | Primary background |
| surface | #161c2c | Card backgrounds |
| cyan | #17e2ea | Hero color, CTAs, active states |
| mint | #35dd8b | Success states |
| yellow | #ffcb19 | Warning, cost metrics |
| red | #ff4e00 | Danger states |
| Font | Poppins | All UI text |
| Card radius | 24px | All cards |
| Button radius | 100px | All pill buttons |

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Progressive disclosure | R5-Q3 | Required fields visible, advanced in accordion |
| Clone-from-previous | R5-Q3 | Repeat users pre-fill from prior sessions |
| React + Vite | R5-Q7 | Matches Nerdy's existing frontend stack |

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/` | Entire React project (Vite scaffold) |
| `src/design/tokens.ts` | Design system tokens |
| `src/views/NewSessionForm.tsx` | Brief configuration form |
| `src/api/sessions.ts` | Session API client |
| `src/types/session.ts` | TypeScript types |
| `src/App.tsx` | Router setup |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/reference/prd.md` (Section 4.7.4) | Brief configuration form spec |
| `docs/reference/prd.md` (Section 4.7.10) | Frontend implementation spec + design tokens |
| `app/api/schemas/session.py` | `SessionConfig` schema — form must match |
| `app/api/routes/sessions.py` | API endpoints the form calls |

---

## Definition of Done

- [ ] Vite React project bootstrapped in `app/frontend/`
- [ ] Form with progressive disclosure: required fields visible, advanced in accordion
- [ ] Clone-from-previous populates form from prior session config
- [ ] Form submits to `POST /sessions` with valid payload
- [ ] Validation errors shown inline
- [ ] Design tokens match PRD Section 4.7.10
- [ ] Tests pass
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time: 90–120 minutes

---

## After This Ticket: What Comes Next

**PA-06 (Session List UI)** builds the home screen that shows all sessions as cards. It uses the same API client and design tokens established here.
