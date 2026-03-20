# Ad-Ops-Autopilot — Documentation Index

**Canonical PRD:** 98+ tickets | 9 phases | per `docs/reference/prd.md`

---

## Read Order (Before Any Ticket Work)

1. **Ticket Primer** — `docs/development/tickets/<TICKET-ID>-primer.md`
2. **PRD** — `docs/reference/prd.md` (Section 6: Project Phases & Tickets)
3. **Interviews** — `docs/reference/interviews.md` (R1–R5 architectural decisions)
4. **DEVLOG** — `docs/development/DEVLOG.md` (Ticket Index, prior work)
5. **Decision log** — `docs/deliverables/decisionlog.md`
6. **Systems design** — `docs/deliverables/systemsdesign.md` (architecture details)

---

## Document Map

| Document | Path | Purpose |
|----------|------|---------|
| PRD | `docs/reference/prd.md` | Product requirements, tickets, acceptance criteria |
| Interviews | `docs/reference/interviews.md` | 50 architectural Q&As (R1–R5) |
| DEVLOG | `docs/development/DEVLOG.md` | Development history, Ticket Index, status |
| Systems design | `docs/deliverables/systemsdesign.md` | Architecture, module boundaries, config |
| Decision log | `docs/deliverables/decisionlog.md` | Design choices, options considered (38 entries + 5 ADRs) |
| Technical writeup | `docs/deliverables/writeup.md` | Technical deep-dive for submission |
| Demo script | `docs/deliverables/demo-script.md` | Walkthrough script for demo |
| AI tools | `docs/deliverables/ai-tools.md` | AI tooling used in the project |
| Feedback loop arch | `docs/deliverables/feedback_loop_architecture.md` | Feedback loop design |
| Model orchestration | `docs/deliverables/model_orchestration.md` | Model routing and orchestration design |
| Ticket primers | `docs/development/tickets/*-primer.md` | Per-ticket goals, deliverables, context |
| ENVIRONMENT | `docs/reference/ENVIRONMENT.md` | Setup, config, troubleshooting |
| Requirements | `docs/reference/requirements.md` | Assignment requirements, rubric |
| Nerdy research | `docs/reference/nerdydeepresearch.md` | Deep research on Nerdy/Varsity Tutors brand |
| Video best practices | `docs/reference/video-ad-creation-best-practices.md` | Video ad creation reference |
| Video E2E test | `docs/development/VIDEO_E2E_TEST.md` | Video pipeline end-to-end test guide |
| Video implementation | `docs/development/VIDEO_IMPLEMENTATION_SESSION_PRIMER.md` | Video session implementation primer |
| Video prompt flow | `docs/development/VIDEO_PROMPT_FLOW.md` | Video prompt engineering flow |

---

## Ticket Structure (98+ Tickets, 9 Phases)

| Phase | Prefix | Tickets | Focus |
|-------|--------|---------|-------|
| P0 | P0 | P0-01 – P0-10 (10) | Foundation: scaffolding, ledger, seeds, brand KB, calibration |
| P1 | P1 | P1-01 – P1-20 (20) | Full-ad pipeline: copy + image generation |
| PA | PA | PA-01 – PA-12 (12) | Application layer: FastAPI, sessions, auth, dashboard |
| PB | PB | PB-01 – PB-14 (14) | Nerdy personalization: personas, compliance, hooks |
| P2 | P2 | P2-01 – P2-07 (7) | Testing: inversion, correlation, SPC, compliance, e2e |
| P3 | P3 | P3-01 – P3-13 (13) | A/B variant engine + UGC video via Veo |
| P4 | P4 | P4-01 – P4-07 (7) | Autonomous engine: agents, self-healing, competitive intel |
| P5 | P5 | P5-01 – P5-11 (11) | Dashboard (8-panel HTML), docs, demo, README |
| PC | PC | PC-00 – PC-12 (13) | Video pipeline: Kling 2.6, orchestrator, app integration |
| PF | PF | PF-00 – PF-10 (11) | Finalization and polish |

---

## Key Paths

- **Primers:** `docs/development/tickets/<TICKET-ID>-primer.md`
- **Phase plans:** `docs/development/tickets/<PHASE>-00-phase-plan.md`
- **PRD:** `docs/reference/prd.md`
- **DEVLOG:** `docs/development/DEVLOG.md`
- **Config:** `data/config.yaml`
- **Brand knowledge:** `data/brand_knowledge.json`
