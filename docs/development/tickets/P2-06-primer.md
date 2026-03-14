# P2-06 Primer: Tiered Compliance Filter

**Project:** Ad-Ops-Autopilot  
**Phase:** 2 — Testing & Validation

## Description

Three-layer compliance (R3-Q3): (1) generation prompts with hard constraints; (2) evaluator binary compliance check; (3) regex/keyword filter for literal violations (guarantees, competitor names, absolute promises). Defense-in-depth.

**Acceptance:** Known-bad ads caught by all three layers; zero false negatives on test set.
