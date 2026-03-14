# P5-07 Primer: Decision Log

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** All prior phases should be complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

P5-07 produces the **decision log** — the single most important documentation deliverable. Every major architectural and design choice is documented as an ADR (Architecture Decision Record) plus a narrative reflection. The rubric is explicit: "A well-reasoned decision log with honest limitations is worth more than a polished demo with no explanation of how you got there."

### Why It Matters

- **Visible Reasoning Is a First-Class Output** (Pillar 7): The system's thinking is as important as its output
- **The Reviewer Is a User, Too** (Pillar 8): The decision log shows your mind, not just your code (R4-Q9)
- Documentation & Individual Thinking is 20% of the grade — this deliverable is the primary evidence
- Honest failures and wrong assumptions are more valuable than polished success narratives

---

## What Was Already Done

- `docs/deliverables/decisionlog.md` already exists as a skeleton — this ticket extends it
- `docs/DEVLOG.md` contains per-ticket implementation notes that feed into the decision log
- All architectural decisions are documented across `interviews.md` (R1-R3, 30 Q&As)

---

## What This Ticket Must Accomplish

### Goal

Produce a comprehensive decision log covering every major choice as ADR + narrative reflection. Must cover all 5 ambiguous elements from the assignment spec, plus major architectural choices. Must be honest about failures, surprises, and wrong assumptions.

### Deliverables Checklist

#### A. The 5 Ambiguous Elements (Required)

Each must have its own ADR section documenting: options considered, chosen approach, why, limitations, what surprised you, and where assumptions were wrong.

- [ ] **Dimension weighting** — How are the 5 quality dimensions balanced? Why? (campaign-goal-adaptive with floor constraints per R1-Q3)
- [ ] **Improvement strategies** — Re-prompting? Chain-of-thought? Few-shot? What works? (brief mutation + escalation per R1-Q2)
- [ ] **Failure handling** — When quality doesn't improve after N cycles, what happens? (2-3 failures then brief mutation + escalation per R1-Q2)
- [ ] **Human-in-the-loop** — When should a human intervene? (confidence-gated autonomy per R2-Q5)
- [ ] **Context management** — What context does each generation/evaluation call see? (distilled context objects per R2-Q4)

#### B. Major Architectural Choices

ADR entries for key system-level decisions, including but not limited to:

- [ ] Append-only JSONL ledger vs. database (R2-Q8)
- [ ] Checkpoint-and-resume vs. retry-only (R3-Q2)
- [ ] Tiered model routing: Flash default, Pro for 5.5-7.0 range (R1-Q4)
- [ ] Quality ratchet design: rolling high-water mark (R1-Q9)
- [ ] Evaluator calibration strategy: cold start with competitor ads (R1-Q8)
- [ ] SPC for evaluator drift detection (R1-Q1)
- [ ] Pareto-optimal filtering to prevent dimension collapse (R1-Q5)
- [ ] Contrastive evaluation rationales (R3-Q10)
- [ ] Reference-decompose-recombine for generation (R2-Q1)

#### C. ADR Format (per entry)

Each ADR should follow this structure:

```markdown
### ADR-XX: [Decision Title]

**Status:** Accepted | Revised | Superseded
**Context:** Why this decision was needed
**Options Considered:**
1. Option A — [description]
2. Option B — [description]
3. Option C — [description]

**Decision:** [Chosen option and why]
**Consequences:** [Trade-offs, limitations]
**What Surprised Me:** [Honest reflection]
**Where Assumptions Were Wrong:** [What you'd do differently]
```

#### D. Narrative Reflection Section

- [ ] "Failed experiments" — approaches that didn't work, with honest analysis of why
- [ ] "What I'd do differently" — retrospective insights
- [ ] "Biggest surprises" — unexpected behaviors, results, or learnings
- [ ] Clear evidence of independent thinking (not just restating the PRD)

#### E. Documentation

- [ ] Extend `docs/deliverables/decisionlog.md` (do NOT create a new file)
- [ ] Add P5-07 entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

```bash
git switch main && git pull
git switch -c feature/P5-07-decision-log
```

---

## Important Context

### Architectural Decisions

| Decision | Reference | Summary |
|----------|-----------|---------|
| Decision log format | R4-Q9 | ADR + narrative reflection; shows YOUR mind at work |
| 5 ambiguous elements | requirements.md | Dimension weighting, improvement strategies, failure handling, human-in-loop, context management |
| Visible reasoning | Pillar 7 | Decision log with honest failures is a first-class output |

### Files to Create/Modify

| File | Why |
|------|-----|
| `docs/deliverables/decisionlog.md` | Extend with full ADR entries + narrative reflection |

### Files You Should READ for Context

| File | Why |
|------|-----|
| `docs/deliverables/decisionlog.md` | Existing skeleton to extend |
| `docs/DEVLOG.md` | Per-ticket implementation notes feed into decision log |
| `docs/reference/interviews.md` | All 30 architectural Q&As — source material for ADRs |
| `docs/reference/requirements.md` (lines 164-171) | The 5 ambiguous elements |
| `docs/reference/requirements.md` (lines 338-361) | Documentation & Individual Thinking rubric |

---

## Definition of Done

- [ ] All 5 ambiguous elements have dedicated ADR sections
- [ ] Major architectural choices documented with options, rationale, limitations
- [ ] Honest about failures — documents what didn't work and why
- [ ] "What surprised me" and "where assumptions were wrong" sections are genuine reflections
- [ ] Clear evidence of independent thinking (not just restating PRD decisions)
- [ ] `docs/deliverables/decisionlog.md` is the single output file
- [ ] DEVLOG updated
- [ ] Feature branch pushed

---

## Estimated Time: 60–90 minutes

---

## After This Ticket: What Comes Next

**P5-08** (Technical writeup) draws from this decision log for architecture and methodology sections. Complete P5-07 first so the writeup can reference specific ADRs.
