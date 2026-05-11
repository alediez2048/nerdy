# PG-03 Primer: Secure Static File Serving for Images/Videos

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. PG-01 must be done first.

---

## What Is This Ticket?

The API serves generated images and videos as static files via FastAPI's `StaticFiles` mount:

```python
app.mount("/api/images", StaticFiles(directory="output/images"), name="images")
app.mount("/api/videos", StaticFiles(directory="output/videos"), name="videos")
```

These mounts have **no access control** — any URL like `/api/images/<filename>` is publicly accessible if the filename is guessed. Since images contain generated ad creatives (potentially sensitive brand assets), they should only be accessible to the session owner or via a valid share token.

### Why It Matters
- Generated ad images may contain proprietary brand assets, unreleased campaign concepts, or competitive intelligence
- Video files from Fal/Veo generation are expensive (~$0.50-1.00 each) and represent real API spend
- A share link should grant access to that session's media only, not all media

---

## What This Ticket Must Accomplish

### Goal
Replace static file mounts with authenticated route handlers that verify the requesting user owns the session that produced the file.

### Deliverables Checklist

#### A. Implementation

- [ ] **Reorganize output directory** to be scoped by session:
  - Current: `output/images/{filename}`, `output/videos/{filename}`
  - Target: `output/sessions/{session_id}/images/{filename}`, `output/sessions/{session_id}/videos/{filename}`
  - OR: keep flat structure but maintain a mapping of `filename → session_id` in DB or filesystem

- [ ] **Replace StaticFiles mounts** in `app/api/main.py` with route handlers:
  ```python
  @app.get("/api/images/{session_id}/{filename}")
  def serve_image(session_id: str, filename: str, user: dict = Depends(get_current_user), db = Depends(get_db)):
      _get_user_session(db, session_id, user["user_id"])  # verify ownership
      path = Path(f"output/sessions/{session_id}/images/{filename}")
      if not path.exists():
          raise HTTPException(404)
      return FileResponse(path)
  ```

- [ ] **Handle share token access**: if the request comes via a share link (query param `?token=xxx`), validate the share token instead of user auth

- [ ] **Update pipeline output paths**: ensure the pipeline writes images/videos into session-scoped subdirectories

- [ ] **Update frontend image/video URLs** in components that display ad previews — update path pattern to include session_id

#### B. Testing

- [ ] Verify authenticated user can access their own session's images
- [ ] Verify authenticated user gets 404 for another user's session images
- [ ] Verify share token grants access to shared session's images only
- [ ] Verify old static mount paths return 404

---

## Key Files

| File | Action |
|------|--------|
| `app/api/main.py` | Remove StaticFiles mounts, add auth routes |
| `app/workers/tasks/pipeline_task.py` | Update output paths to session-scoped dirs |
| `app/frontend/src/views/SessionDetail.tsx` | Update image/video URL patterns |
| `app/frontend/src/components/AdCard.tsx` (if exists) | Update image URL patterns |

---

## Notes

- This is a breaking change for existing image URLs. Existing sessions may have images in the flat `output/images/` directory. Consider a migration script or backward-compatible fallback.
- For share links, the frontend passes `?token=xxx` which the backend can validate against the `share_tokens` table.
- Path traversal prevention: always resolve paths against the expected directory and reject `..` segments.
