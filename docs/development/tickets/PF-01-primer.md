# PF-01 Primer: File Structure Cleanup

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** All phases (P0–P5, PA, PB, PC, PF-old) complete. See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PF-01 removes stale files, test artifacts, committed runtime data, and build artifacts from the repository. It also updates `.gitignore` to prevent these files from being committed again. This is housekeeping — no code changes, just cleanup.

### Why It Matters

- The repo currently contains ~100+ committed PNG/MP4 files that are runtime output, not source code
- `MagicMock/` is a leaked test fixture directory that shouldn't exist
- `data/sessions/sess_*/ledger.jsonl` files are runtime state, not source — they inflate repo size
- `.vite/deps/` build artifacts are committed — Vite regenerates these on `npm run dev`
- A clean repo is easier to navigate, clone, and review

---

## What Was Already Done

- `.gitignore` exists but is incomplete — doesn't cover `output/images/`, `output/videos/`, `data/sessions/`, `MagicMock/`, `.vite/`
- Generated images and videos were committed across multiple prior sessions

---

## What This Ticket Must Accomplish

### Goal

Remove all non-source files from git tracking, update `.gitignore`, and verify the repo only contains source code, config, and documentation.

### Deliverables Checklist

#### A. Remove Stale Files

- [ ] Delete `MagicMock/` directory entirely (test artifact from mock leakage)
- [ ] Delete `data/ledger.jsonl.bak` (backup file)
- [ ] Delete `.cursor-safety/` directory (Cursor IDE artifacts, not source)

#### B. Remove Committed Runtime Data

- [ ] `git rm` all files in `data/sessions/sess_*/` (runtime ledger data)
- [ ] `git rm` all files in `output/images/*.png` (generated ad images)
- [ ] `git rm` all files in `output/videos/*.mp4` and subdirectories (generated videos)
- [ ] Keep empty directories with `.gitkeep` files:
  - `output/images/.gitkeep`
  - `output/videos/.gitkeep`
  - `data/sessions/.gitkeep`

#### C. Remove Build Artifacts

- [ ] `git rm -r` `app/frontend/.vite/deps/` (Vite build cache)

#### D. Update `.gitignore`

- [ ] Add: `MagicMock/`
- [ ] Add: `data/sessions/`
- [ ] Add: `output/images/*.png` and `output/images/*.jpg`
- [ ] Add: `output/videos/`
- [ ] Add: `*.bak`
- [ ] Add: `app/frontend/.vite/`
- [ ] Add: `.cursor-safety/`
- [ ] Verify existing entries still correct

#### E. Verify

- [ ] `git status` shows only `.gitignore` changes + removals
- [ ] No runtime data, images, videos, or build artifacts tracked
- [ ] Run `git diff --stat HEAD` to confirm repo size reduction
- [ ] Confirm the app still starts correctly after cleanup

---

## Branch & Merge Workflow

Work on `video-implementation-2.0` branch (current branch).

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `output/images/.gitkeep` | Preserve empty directory structure |
| `output/videos/.gitkeep` | Preserve empty directory structure |
| `data/sessions/.gitkeep` | Preserve empty directory structure |

### Files to Modify

| File | Action |
|------|--------|
| `.gitignore` | Add runtime data, build artifacts, test artifacts patterns |
| `docs/DEVLOG.md` | Add ticket entry |

### Files to Delete

| File/Directory | Why |
|------|-----|
| `MagicMock/` | Leaked test mock artifacts |
| `data/ledger.jsonl.bak` | Stale backup |
| `.cursor-safety/` | IDE artifacts |
| `data/sessions/sess_*/**` | Runtime session data |
| `output/images/*.png` | Generated ad images |
| `output/videos/**/*.mp4` | Generated ad videos |
| `app/frontend/.vite/deps/` | Vite build cache |

### Files You Should NOT Modify

- Any source code files
- Any test files
- `data/config.yaml` — configuration stays
- `data/brand_knowledge.json` — source data stays
- `data/reference_ads.json` — source data stays

---

## Edge Cases to Handle

1. `output/images/` may contain subdirectories — remove recursively
2. `output/videos/` has session-specific subdirs (`session_sess_*/`) — remove all
3. Some files may have spaces or special chars in paths — use proper quoting
4. `git rm --cached` for files that should stay on disk but leave tracking
5. Verify `.gitkeep` files are not ignored by the new `.gitignore` rules

---

## Definition of Done

- [ ] No `MagicMock/`, `.cursor-safety/`, `*.bak` files tracked
- [ ] No committed images (`.png`), videos (`.mp4`), or session ledgers
- [ ] `.gitignore` prevents future commits of runtime data
- [ ] Empty directory structure preserved with `.gitkeep`
- [ ] App starts correctly after cleanup
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Identify all stale files | 5 min |
| git rm + delete | 10 min |
| Update .gitignore | 5 min |
| Verify + commit | 5 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PF-02/03:** QA with a clean repo — verify features still work
- **PF-04/05:** Fix bugs discovered during QA
