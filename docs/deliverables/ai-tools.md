# AI Tools & Prompts Used

**Author:** JAD
**Project:** Ad-Ops-Autopilot — Autonomous Ad Copy Generation for FB/IG
**Last Updated:** March 13, 2026

---

> Required deliverable: "Documentation of AI tools and prompts used" — Assignment Brief

This document records every AI tool used in building the system, how it was used, and the key prompts that drive the pipeline.

---

## 1. Development Tools

### Claude (via Cursor IDE)

**Role:** Architecture design, code implementation, documentation
**How used:**
- Architectural pressure testing (30 Q&A rounds informing design decisions)
- Code generation for pipeline modules (generate/, evaluate/, iterate/, output/)
- Test writing (TDD workflow — tests before implementation)
- Documentation authoring (decision log, systems design, DEVLOG entries)

**Key principle:** Claude assisted with implementation, but all architectural decisions were made through deliberate reasoning documented in the [decision log](decisionlog.md). The decision log explains WHY each choice was made, including failed approaches and honest limitations.

### Claude in Chrome (Browser Extension)

**Role:** Semi-automated competitive intelligence extraction
**How used:**
- Analyzed 6 competitors' active Facebook ads via Meta Ad Library (P0-09)
- Structured pattern extraction: hook type, emotional angle, CTA style, audience targeting
- Results stored in `data/competitive/patterns.json`

---

## 2. Pipeline Models (Runtime)

### Gemini Flash (gemini-2.0-flash)

**Role:** Default model for ~80% of pipeline operations
**Used for:**
- Brief expansion (P1-01)
- First-draft ad copy generation (P1-02)
- Initial evaluation / triage scoring (P1-04)
- Context distillation (P1-09)
- Compliance checking (P2-06)
- Image attribute evaluation (P1-15)
- Text-image coherence scoring (P1-16)

**Why Flash:** Cheapest option that produces usable output. Performance-per-token principle — reserve expensive models for where they have highest marginal ROI.

### Gemini Pro (gemini-2.0-pro)

**Role:** Escalation model for borderline ads (5.5–7.0 score range)
**Used for:**
- Improvable-range regeneration (P1-06)
- Pareto variant generation when Flash variants plateau

**Why Pro only for 5.5–7.0:** Ads below 5.5 are fundamentally broken (no model saves them). Ads above 7.0 already pass (no need to spend more). The improvable range is where expensive tokens have highest marginal return.

### Nano Banana Pro (Gemini 3 Pro Image)

**Role:** Ad image generation
**Used for:**
- 3 image variants per ad: anchor, tone shift, composition shift (P1-14)
- Aspect ratio routing: 1:1 default, 4:5 + 9:16 for published winners

**Cost:** ~$0.13/image (1K resolution)

### Veo 3.1 Fast (Phase 3)

**Role:** UGC video generation for Stories/Reels
**Used for:**
- 2 video variants per ad: anchor + alternative scene/pacing (P3-07)
- 9:16 format for Stories/Reels placement

**Cost:** ~$0.15/sec (~$0.90 per 6-second video)

---

## 3. Key Pipeline Prompts

*Exact prompts will be added as each module is implemented. This section will include the final versions used in the 50+ ad generation run.*

### Brief Expansion Prompt (P1-01)
*To be added after implementation.*

### Ad Copy Generation Prompt (P1-02)
*To be added after implementation — includes reference-decompose-recombine structural atoms.*

### Chain-of-Thought Evaluation Prompt (P1-04)
*To be added after implementation — 5-step CoT with contrastive rationales.*

### Calibration Prompt (P0-06)
*To be added after implementation — includes calibration anchors.*

### Context Distillation Prompt (P1-09)
*To be added after implementation.*

### Image Visual Spec Extraction Prompt (P1-14)
*To be added after implementation.*

### Competitive Pattern Extraction Prompt (P0-09)
*To be added after implementation — Claude in Chrome extraction template.*

---

## 4. What AI Did vs. What I Did

| Area | AI's Role | My Role |
|------|-----------|---------|
| Architecture | Explored options via pressure test Q&A | Selected approaches, justified trade-offs |
| Code | Generated implementations from specifications | Reviewed, tested, iterated on failures |
| Evaluation framework | Produced evaluation prompt drafts | Calibrated against reference ads, tuned until reliable |
| Decision log | Assisted with drafting | All reasoning is my own — failures and limitations are honest |
| Prompt engineering | Generated initial prompt versions | Iterated based on output quality, documented what worked/didn't |
| Testing | Generated test scaffolding | Designed test strategy, chose what to test and why |

**The system is AI-assisted, not AI-generated.** Every architectural decision has a documented rationale. Every failed approach is recorded. The decision log reflects genuine thinking, not AI output passed through.

---

*This document will be updated with exact prompt versions after each pipeline module is implemented.*
