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

from typing import Any

from evaluate.media_quality import MediaEvaluationResult, evaluate_media
from evaluate.media_selector import select_best
from generate_video.video_client import VideoGenerationClient
from generate_video.video_spec import VideoSpec, build_kling_prompt
from iterate.ledger import read_events
from iterate.ledger_events import (
    MediaEvaluation,
    MediaEvaluationFailed,
    VideoGenerated,
    VideoGenerationFailed,
)
from iterate.ledger_writer import LedgerWriter

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

            LedgerWriter(ledger_path).record(VideoGenerated(
                ad_id=ad_id,
                brief_id=ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                cycle_number=0,
                action=f"video_{variant_type}_generated",
                tokens_consumed=0,
                model_used=provider_name,
                seed=str(var_seed),
                outputs={
                    "video_path": out_path,
                    "remote_url": remote_url,
                    "variant_type": variant_type,
                    "duration": effective_spec.duration,
                    "audio_mode": effective_spec.audio_mode,
                    "credits": credits,
                },
            ))

        except Exception as e:
            logger.warning("Video generation failed for %s/%s: %s", ad_id, variant_type, e)
            LedgerWriter(ledger_path).record(VideoGenerationFailed(
                ad_id=ad_id,
                brief_id=ad_id.split("_c")[0] if "_c" in ad_id else ad_id,
                cycle_number=0,
                action=f"video_{variant_type}_failed",
                tokens_consumed=0,
                model_used=provider_name,
                seed=str(var_seed),
                outputs={"error": str(e), "variant_type": variant_type},
            ))

    return variants


def should_skip_video_ad(ad_id: str, ledger_path: str) -> bool:
    """Check if this ad already has a VideoSelected or VideoBlocked event."""
    events = read_events(ledger_path)
    for ev in events:
        if ev.get("ad_id") == ad_id and ev.get("event_type") in ("VideoSelected", "VideoBlocked"):
            return True
    return False


def score_and_select_video_variants(
    ad: Any,
    variants: list[Any],
    brief: dict[str, Any],
    ledger_path: str,
) -> str | None:
    """Evaluate N video variants via unified media_quality, pick winner.

    Returns the winning video path, or None if all variants failed.
    Writes one MediaEvaluation (or MediaEvaluationFailed) ledger event
    per variant. PI-06.
    """
    ad_copy = {
        "headline": ad.headline,
        "primary_text": getattr(ad, "primary_text", "") or getattr(ad, "body", ""),
        "cta_button": getattr(ad, "cta_button", "") or getattr(ad, "cta", ""),
    }
    session_config = brief.get("session_config")
    evaluations: list[MediaEvaluationResult] = []
    for v in variants:
        result = evaluate_media(
            media_path=v.video_path,
            ad_copy=ad_copy,
            ad_id=ad.ad_id,
            variant_type=v.variant_type,
            media_type="video",
            session_config=session_config,
        )
        evaluations.append(result)
        _record_video_evaluation(ledger_path, brief, v, result)

    selection = select_best(evaluations)
    if selection.all_failed or selection.winner is None:
        return None
    return selection.winner.media_path


def _record_video_evaluation(
    ledger_path: str,
    brief: dict[str, Any],
    variant: Any,
    result: MediaEvaluationResult,
) -> None:
    """Append the right ledger event for one video variant evaluation."""
    brief_id = brief.get("brief_id", "unknown")
    seed = str(getattr(variant, "seed", "0"))

    if result.failed:
        LedgerWriter(ledger_path).record(MediaEvaluationFailed(
            ad_id=result.ad_id,
            brief_id=brief_id,
            cycle_number=0,
            action=f"media_eval_failed_{result.variant_type}",
            tokens_consumed=result.tokens_consumed,
            model_used=result.model_used,
            seed=seed,
            inputs={"variant_type": result.variant_type, "media_type": "video"},
            outputs={
                "schema_version": "v2",
                "media_type": "video",
                "failure_reason": result.failure_reason,
                "error_message": result.error_message,
            },
        ))
        return

    LedgerWriter(ledger_path).record(MediaEvaluation(
        ad_id=result.ad_id,
        brief_id=brief_id,
        cycle_number=0,
        action=f"media_eval_{result.variant_type}",
        tokens_consumed=result.tokens_consumed,
        model_used=result.model_used,
        seed=seed,
        inputs={"variant_type": result.variant_type, "media_type": "video"},
        outputs={
            "schema_version": "v2",
            "media_type": "video",
            "media_path": result.media_path,
            "dimensions": {
                name: {"score": ds.score, "weight": ds.weight, "rationale": ds.rationale}
                for name, ds in result.dimensions.items()
            },
            "penalty_gates": {
                name: {"triggered": ge.triggered, "rationale": ge.rationale}
                for name, ge in result.penalty_gates.items()
            },
            "raw_score": result.raw_score,
            "penalty_multiplier": result.penalty_multiplier,
            "composite_score": result.composite_score,
        },
    ))
