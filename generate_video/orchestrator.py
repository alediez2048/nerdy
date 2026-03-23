"""Video pipeline orchestrator — generate, evaluate, select (PC-02).

Produces 2 variants per ad (anchor + alternative), evaluates each,
selects the best, and handles failures via graceful degradation.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, replace
from pathlib import Path

from evaluate.video_evaluator import (
    VideoCoherenceResult,
    VideoEvalResult,
    compute_composite_score,
)
from generate_video.video_client import VideoGenerationClient
from generate_video.video_spec import VideoSpec, build_kling_prompt
from iterate.ledger import log_event, read_events

logger = logging.getLogger(__name__)

_ALT_CAMERA_SWAP = {
    "handheld": "static",
    "static": "handheld",
    "dolly-in": "tracking",
    "tracking": "dolly-in",
    "slow-motion": "static",
}


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, object]) -> None:
    # region agent log
    try:
        debug_path = Path("/app/.cursor/debug-c163a9.log")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sessionId": "c163a9",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with debug_path.open("a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # endregion


@dataclass
class VideoVariant:
    """A single generated video variant."""

    ad_id: str
    variant_type: str
    video_path: str
    duration: int
    audio_mode: str
    aspect_ratio: str
    prompt_used: str
    seed: int
    credits_consumed: int
    model_used: str
    remote_url: str | None = None


_CREDITS_PER_SECOND: dict[str, int] = {
    "fal": 100,
    "veo": 150,
    "kling": 120,
}


def _estimate_credits(duration: int, audio: bool, provider: str = "veo") -> int:
    """Estimate cost in milli-dollars for progress reporting."""
    base = _CREDITS_PER_SECOND.get(provider, 150)
    multiplier = 2 if audio else 1
    return duration * base * multiplier


def _build_alt_prompt(spec: VideoSpec) -> str:
    """Build an alternative variant prompt with swapped camera/pacing."""
    alt_camera = _ALT_CAMERA_SWAP.get(spec.camera_movement, "handheld")
    alt_spec = VideoSpec(
        scene=spec.scene,
        visual_style=spec.visual_style,
        camera_movement=alt_camera,
        subject_action=spec.subject_action,
        setting=spec.setting,
        lighting_mood=spec.lighting_mood.replace("warm", "cool").replace("soft", "dramatic")
        if spec.lighting_mood else spec.lighting_mood,
        audio_mode=spec.audio_mode,
        audio_detail=spec.audio_detail,
        color_palette=spec.color_palette,
        negative_prompt=spec.negative_prompt,
        duration=spec.duration,
        aspect_ratio=spec.aspect_ratio,
        text_overlay_sequence=spec.text_overlay_sequence,
        persona=spec.persona,
        campaign_goal=spec.campaign_goal,
    )
    return build_kling_prompt(alt_spec)


def generate_video_variants(
    spec: VideoSpec,
    ad_id: str,
    seed: int,
    output_dir: str,
    ledger_path: str,
    veo_client: VideoGenerationClient,
) -> list[VideoVariant]:
    """Generate anchor + alternative video variants.

    Returns only successful variants (0, 1, or 2).
    Logs VideoGenerated only when file exists on disk.
    Logs VideoGenerationFailed on any API error.
    """
    client = veo_client
    variants: list[VideoVariant] = []
    audio = spec.audio_mode == "with_audio"
    effective_spec = replace(
        spec,
        duration=client.normalize_duration(spec.duration),
        aspect_ratio=client.normalize_aspect_ratio(spec.aspect_ratio),
    )

    configs = [
        ("anchor", build_kling_prompt(effective_spec), seed),
        ("alternative", _build_alt_prompt(effective_spec), seed + 3000),
    ]

    for variant_type, prompt, var_seed in configs:
        out_path = str(
            Path(output_dir)
            / f"{ad_id}_{variant_type}_{effective_spec.aspect_ratio.replace(':', 'x')}.mp4"
        )
        # region agent log
        _debug_log(
            "H9",
            "generate_video/orchestrator.py:generate_video_variants:variant",
            "video variant prompt characteristics",
            {
                "ad_id": ad_id,
                "variant_type": variant_type,
                "camera_movement": effective_spec.camera_movement if variant_type == "anchor" else _ALT_CAMERA_SWAP.get(effective_spec.camera_movement, "handheld"),
                "lighting_mood": effective_spec.lighting_mood if variant_type == "anchor" else (effective_spec.lighting_mood.replace("warm", "cool").replace("soft", "dramatic") if effective_spec.lighting_mood else effective_spec.lighting_mood),
                "prompt_preview": prompt[:240],
                "has_dramatic_keyword": "dramatic" in prompt.lower(),
                "has_contrast_keyword": "contrast" in prompt.lower(),
                "has_cool_keyword": "cool" in prompt.lower(),
            },
        )
        # endregion

        provider_name = getattr(client, "model_used", "unknown")

        try:
            client.generate_video(
                prompt=prompt,
                duration=effective_spec.duration,
                aspect_ratio=effective_spec.aspect_ratio,
                audio=audio,
                negative_prompt=effective_spec.negative_prompt,
                output_path=out_path,
            )

            if not Path(out_path).exists():
                raise FileNotFoundError(f"Video file not created: {out_path}")

            credits = _estimate_credits(effective_spec.duration, audio, provider_name)
            remote_url = getattr(client, "_last_remote_url", None)
            variant = VideoVariant(
                ad_id=ad_id,
                variant_type=variant_type,
                video_path=out_path,
                duration=effective_spec.duration,
                audio_mode=effective_spec.audio_mode,
                aspect_ratio=effective_spec.aspect_ratio,
                prompt_used=prompt,
                seed=var_seed,
                credits_consumed=credits,
                model_used=provider_name,
                remote_url=remote_url,
            )
            variants.append(variant)

            log_event(ledger_path, {
                "event_type": "VideoGenerated",
                "ad_id": ad_id,
                "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                "cycle_number": 0,
                "action": f"video_{variant_type}_generated",
                "tokens_consumed": 0,
                "model_used": provider_name,
                "seed": str(var_seed),
                "outputs": {
                    "video_path": out_path,
                    "remote_url": remote_url,
                    "variant_type": variant_type,
                    "duration": effective_spec.duration,
                    "audio_mode": effective_spec.audio_mode,
                    "credits": credits,
                },
            })

        except Exception as e:
            logger.warning("Video generation failed for %s/%s: %s", ad_id, variant_type, e)
            log_event(ledger_path, {
                "event_type": "VideoGenerationFailed",
                "ad_id": ad_id,
                "brief_id": ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                "cycle_number": 0,
                "action": f"video_{variant_type}_failed",
                "tokens_consumed": 0,
                "model_used": provider_name,
                "seed": str(var_seed),
                "outputs": {"error": str(e), "variant_type": variant_type},
            })

    return variants


def select_best_video(
    variants: list[VideoVariant],
    eval_results: dict[str, VideoEvalResult],
    coherence_results: dict[str, VideoCoherenceResult],
) -> VideoVariant | None:
    """Select the best video variant by composite score.

    Returns the highest-scoring generated/evaluated variant.
    Returns None only when no variant has both evaluation artifacts present.
    """
    candidates: list[tuple[float, VideoVariant]] = []

    for v in variants:
        ev = eval_results.get(v.variant_type)
        co = coherence_results.get(v.variant_type)
        if not ev or not co:
            continue
        score = compute_composite_score(ev, co)
        candidates.append((score, v))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def should_skip_video_ad(ad_id: str, ledger_path: str) -> bool:
    """Check if this ad already has a VideoSelected or VideoBlocked event."""
    events = read_events(ledger_path)
    for ev in events:
        if ev.get("ad_id") == ad_id and ev.get("event_type") in ("VideoSelected", "VideoBlocked"):
            return True
    return False
