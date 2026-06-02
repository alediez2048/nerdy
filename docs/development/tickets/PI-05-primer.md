# PI-05 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

---

# Ticket PI-05: `media_quality.py` — video path

**Goal:** Extend `evaluate_media` to handle `media_type="video"`. Adds video-specific dimensions, gates, prompt, mime type, and (if needed) frame-extraction fallback when the video file is too large to upload.

**Files:**
- Modify: `evaluate/media_quality.py`
- Modify: `tests/test_evaluation/test_media_quality.py` (add video tests)

- [ ] **Step 1: Write the failing test** — append to `tests/test_evaluation/test_media_quality.py`:

```python
from evaluate.media_quality import VIDEO_DIMENSIONS, VIDEO_GATES


def test_video_dimensions_and_weights():
    """10 dimensions for video, weights sum to 1.0."""
    assert len(VIDEO_DIMENSIONS) == 10
    total = sum(d["weight"] for d in VIDEO_DIMENSIONS)
    assert abs(total - 1.0) < 1e-9
    names = {d["name"] for d in VIDEO_DIMENSIONS}
    assert names == {
        "thumb_stop_potential", "brand_consistency", "emotional_impact",
        "message_alignment", "audience_match", "production_quality",
        "hook_in_3s", "pacing", "motion_quality", "audio_appropriateness",
    }


def test_video_gates_have_caps():
    assert len(VIDEO_GATES) == 5
    names = {g["name"] for g in VIDEO_GATES}
    assert names == {
        "has_ai_artifacts", "has_uncanny_faces", "brand_safety_violation",
        "has_temporal_artifacts", "has_pacing_dead_zones",
    }


def _make_video_payload(score: int = 6) -> dict[str, Any]:
    return {
        "dimensions": {
            d["name"]: {"score": score, "rationale": f"video {d['name']}"}
            for d in VIDEO_DIMENSIONS
        },
        "penalty_gates": {
            g["name"]: {"triggered": False, "rationale": "clean"}
            for g in VIDEO_GATES
        },
    }


def test_evaluate_media_video_happy_path(tmp_path):
    media_path = tmp_path / "ad.mp4"
    media_path.write_bytes(b"fake-mp4")
    payload = json.dumps(_make_video_payload(score=6))
    with patch("evaluate.media_quality._call_multimodal", return_value=(payload, 3000)):
        result = evaluate_media(
            media_path=str(media_path),
            ad_copy={"headline": "Ace SAT", "body": "1-on-1", "cta": "Start"},
            ad_id="ad_001", variant_type="anchor", media_type="video",
        )
    assert not result.failed
    assert result.media_type == "video"
    assert len(result.dimensions) == 10
    assert len(result.penalty_gates) == 5
    assert result.composite_score == pytest.approx(60.0, abs=0.01)
```

- [ ] **Step 2: Run, verify fail (`ImportError: VIDEO_DIMENSIONS`)**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality.py::test_video_dimensions_and_weights -v
```

- [ ] **Step 3: Add `VIDEO_DIMENSIONS` and `VIDEO_GATES` to `evaluate/media_quality.py`**

After the `IMAGE_GATES` definition, add:

```python
# ---- Video rubric (PI-05) ----
VIDEO_DIMENSIONS: tuple[dict[str, Any], ...] = (
    {"name": "thumb_stop_potential", "weight": 0.15,
     "criterion": "Visual hook within 0.3s that stops the scroll."},
    {"name": "brand_consistency", "weight": 0.10,
     "criterion": "Varsity Tutors palette and tone visible throughout."},
    {"name": "emotional_impact", "weight": 0.10,
     "criterion": "Evokes a specific emotion across the clip."},
    {"name": "message_alignment", "weight": 0.10,
     "criterion": "Video reinforces the copy's message and CTA."},
    {"name": "audience_match", "weight": 0.10,
     "criterion": "Casting and setting match the target persona."},
    {"name": "production_quality", "weight": 0.05,
     "criterion": "Composition + color balance + no obvious tells."},
    {"name": "hook_in_3s", "weight": 0.15,
     "criterion": "Opening 3 seconds grab attention — Meta's #1 video metric."},
    {"name": "pacing", "weight": 0.10,
     "criterion": "No dead frames; energy matches the brief."},
    {"name": "motion_quality", "weight": 0.10,
     "criterion": "Smooth motion, no jank or unnatural transitions."},
    {"name": "audio_appropriateness", "weight": 0.05,
     "criterion": "Audio fits tone; intentional silence is OK."},
)

VIDEO_GATES: tuple[dict[str, Any], ...] = (
    {"name": "has_ai_artifacts", "cap": 0.5,
     "criterion": "Warped hands, mangled text, impossible geometry."},
    {"name": "has_uncanny_faces", "cap": 0.6,
     "criterion": "Asymmetric features, melted skin, lifeless eyes."},
    {"name": "brand_safety_violation", "cap": 0.3,
     "criterion": "Competitor logos, inappropriate context."},
    {"name": "has_temporal_artifacts", "cap": 0.4,
     "criterion": "Flickering, frame jumps, faces morphing across cuts."},
    {"name": "has_pacing_dead_zones", "cap": 0.7,
     "criterion": "Long static moments where nothing happens."},
)
```

- [ ] **Step 4: Update `evaluate_media` to dispatch on `media_type`**

Replace the early `if media_type != "image": raise NotImplementedError(...)` line with:

```python
if media_type == "image":
    rubric_dims, rubric_gates = IMAGE_DIMENSIONS, IMAGE_GATES
    prompt = _build_image_prompt(ad_copy, session_config)
elif media_type == "video":
    rubric_dims, rubric_gates = VIDEO_DIMENSIONS, VIDEO_GATES
    prompt = _build_video_prompt(ad_copy, session_config)
else:
    return _failure_result(
        ad_id, variant_type, media_type, media_path,
        "unsupported_media_type", f"media_type={media_type}",
    )
```

- [ ] **Step 5: Add `_build_video_prompt` next to `_build_image_prompt`**

```python
def _build_video_prompt(ad_copy: dict[str, Any], session_config: dict[str, Any] | None) -> str:
    headline = ad_copy.get("headline", "")
    primary_text = ad_copy.get("primary_text", "") or ad_copy.get("body", "")
    cta = ad_copy.get("cta_button", "") or ad_copy.get("cta", "")
    audience = (session_config or {}).get("audience", "")
    persona = (session_config or {}).get("persona", "")

    dims_block = "\n".join(
        f"{i+1}. {d['name']} (weight {d['weight']:.2f}) — {d['criterion']}"
        for i, d in enumerate(VIDEO_DIMENSIONS)
    )
    gates_block = "\n".join(
        f"- {g['name']} (cap {g['cap']:.1f}) — {g['criterion']}"
        for g in VIDEO_GATES
    )
    return f"""You are a strict UGC-style video ad evaluator for Varsity Tutors SAT test prep on Facebook and Instagram.

CALIBRATION: AI-generated video has visible weak points. Be specific. A score of 7 is genuinely good. 9–10 is exceptional and rare. Most generated video clips score 4–6. Watch the full clip before scoring.

AD COPY (for message-alignment evaluation):
- Headline: {headline or "(none)"}
- Primary Text: {primary_text or "(none)"}
- CTA: {cta or "(none)"}
- Target audience: {audience or "(none)"}
- Persona: {persona or "(none)"}

DIMENSIONS — score 1–10 with a 1–2 sentence rationale naming a specific moment or visual element (e.g. "the 0:02 cut from student to tutor").

{dims_block}

PENALTY GATES — answer true / false with a 1-sentence rationale.

{gates_block}

Return ONLY a JSON object with this exact shape:
{{
  "dimensions": {{"thumb_stop_potential": {{"score": 7, "rationale": "..."}}, ...}},
  "penalty_gates": {{"has_ai_artifacts": {{"triggered": false, "rationale": "..."}}, ...}}
}}"""
```

- [ ] **Step 6: Run all media_quality tests, verify pass**

```
.venv/bin/python -m pytest tests/test_evaluation/test_media_quality.py -v
```

Expected: 11/11 PASS (8 from PI-02 + 3 new for video).

- [ ] **Step 7: Commit**

```
git add evaluate/media_quality.py tests/test_evaluation/test_media_quality.py
git commit -m "feat(PI-05): media_quality video path — 10 dimensions + 5 gates"
```

---
