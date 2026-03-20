# Video (Veo) integration — end-to-end test

How to run the pipeline with video enabled and verify the full path: brief → copy → image → **video** → evaluation → selection → assembly → export.

## Prerequisites

1. **API key**  
   Same key as for text/image: `GEMINI_API_KEY` in `.env` (or exported). Veo 3.1 Fast uses the same Google AI API.

2. **Quota / cost**  
   - Video: ~\$0.15/sec (~\$0.90 per 6‑sec clip).  
   - A 2‑ad run with video is typically a few dollars (copy + image + 2× video generation/eval).

3. **Environment**  
   From repo root, with your venv activated (or Docker API container). Use `python3` if your system doesn’t have a `python` symlink:

   ```bash
   # Verify key is loaded (use python3 if python is not available)
   python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('GEMINI_API_KEY:', 'set' if os.getenv('GEMINI_API_KEY') else 'MISSING')"
   ```

## Option 1: Minimal smoke test (1 ad, video on)

Fastest way to confirm the video path runs without failing early.

```bash
# Use a fresh ledger so you can inspect it cleanly (use python3 if python is not available)
python3 run_pipeline.py --with-video --max-ads 1 --ledger data/ledger_video_smoke.jsonl --verbose
```

- **Expect:** Pipeline runs brief expansion → copy gen → evaluation → image gen → image selection → **video gen** → video evaluation → video selection (or graceful degradation if Veo fails).
- **Check:**
  - No unhandled exception; if video fails, you should see “graceful degradation” and the ad still published (image-only).
  - Ledger: `data/ledger_video_smoke.jsonl` contains events like `VideoGenerated`, `VideoEvaluated`, `VideoSelected` or `VideoBlocked`.
  - Export: `output/ads/` has at least one ad dir; if video succeeded, that dir should contain a `video_winner.*` file and `metadata.json` with `"formats": ["copy", "image", "video"]` and `winning_video_path`.

## Option 2: Short E2E run (2–3 ads)

Better signal that the full pipeline and export work with video across a small batch.

```bash
python3 run_pipeline.py --with-video --max-ads 3 --ledger data/ledger_video_e2e.jsonl --output output/ads_video_e2e --verbose
```

- **Expect:** 3 ads processed; some may publish with video, some may degrade to image-only (e.g. quality/compliance).
- **Check:**
  - Console: “PIPELINE COMPLETE” with counts; no traceback.
  - `output/ads_video_e2e/`: one folder per published ad; folders with video have `video_winner.*` and metadata listing `"video"` in `formats`.
  - Ledger: mix of `VideoSelected` and possibly `VideoBlocked`; `AdPublished` events include `has_video: true/false`.

## Option 3: Via the app (session with video enabled)

If the app is running (Docker or local):

1. Create a **new session**.
2. In **Advanced** (or Media) set **“Enable video generation”** and choose **Video audio mode** (e.g. Silent).
3. Start the session and **Watch live**.
4. When the run finishes, open the session’s **Ad Library** / **Curated** and confirm:
   - Ads that got a winning video show a video asset and placement mapping (e.g. Stories/Reels → video).
   - Export (if you export from the app) includes video where available.

This tests the same pipeline with config coming from the session (e.g. `video_enabled`, `video_audio_mode`) and Celery/SSE.

## What to look for (success)

| Check | Where |
|-------|--------|
| Video branch runs (no crash) | Console log: “video” or “Veo” / no `RuntimeError` from video code |
| Video generated | Ledger: `VideoGenerated` events with `video_path` |
| Video evaluated | Ledger: `VideoEvaluated` / `VideoCoherenceChecked` |
| Winner chosen or blocked | Ledger: `VideoSelected` or `VideoBlocked` |
| Assembly includes video | `metadata.json`: `formats` includes `"video"`, `winning_video_path` set |
| Export has video file | Ad dir: `video_winner.mp4` (or similar) |

## If something fails

- **“GEMINI_API_KEY not set”** → Load `.env` (e.g. `dotenv` in `run_pipeline`) or export the key in the shell.
- **Veo API error (e.g. 429 / quota)** → Wait and retry, or run with `--max-ads 1` to reduce load.
- **Video fails but ad still published** → Expected: graceful degradation to image-only; check ledger for `VideoBlocked` and `AdPublished` with `has_video: false`.
- **No `VideoGenerated` in ledger** → Confirm `--with-video` was passed (or `video_enabled: true` in config/session). Check that ads reached “publish”/“escalate” (video runs only for publishable ads after image selection).

---

## Session / app: “I enabled video but see no video”

1. **Video is off by default** — When creating a new session, open **Advanced** and **check “Enable video generation (Stories/Reels, ~$0.90/video)”**. If unchecked, the pipeline runs with `video_enabled: false` and skips video. Naming the session “Video Test” does not auto-enable video.
2. **Veo client is still a stub** — Even with video enabled, `generate_video` in `generate_video/veo_client.py` does **not** call the real Veo API; it returns a placeholder path and does not write a video file. Real video output requires wiring the Veo SDK/API.
3. **Ad Library only shows images** — The Ad Library tab displays `image_url` only; it has no video player or thumbnail, so video would not appear there even if present in the ledger.

## Resuming

To re-run without redoing completed work (e.g. after a crash):

```bash
python3 run_pipeline.py --with-video --max-ads 3 --ledger data/ledger_video_e2e.jsonl --resume
```

Completed video work (e.g. `VideoSelected` / `VideoBlocked`) is skipped per ad via checkpoint state.
