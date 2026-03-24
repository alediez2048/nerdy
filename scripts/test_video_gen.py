#!/usr/bin/env python3
"""Diagnostic script for video generation — tests each stage independently.

Usage:
    .venv/bin/python3 scripts/test_video_gen.py [--model MODEL] [--duration SECS]

Tests in order:
  1. API key presence
  2. Fal client construction
  3. Brief generation + expansion
  4. Ad copy generation
  5. Video spec building
  6. Fal API call (actual video generation)
  7. Video download

Each step reports pass/fail with timing, so you can see exactly where it breaks.
"""
import argparse
import os
import sys
import time
import traceback

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()


def step(name: str):
    """Decorator to wrap a test step with timing and error reporting."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n{'='*60}")
            print(f"STEP: {name}")
            print(f"{'='*60}")
            t0 = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - t0
                print(f"  PASS ({elapsed:.1f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - t0
                print(f"  FAIL ({elapsed:.1f}s)")
                print(f"  Error type: {type(e).__name__}")
                print(f"  Error: {e}")
                print("  Traceback:")
                traceback.print_exc()
                return None
        return wrapper
    return decorator


@step("1. Check API Keys")
def check_keys():
    fal_key = os.getenv("FAL_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    print(f"  FAL_KEY: {'set' if fal_key else 'MISSING'} (len={len(fal_key)})")
    print(f"  GEMINI_API_KEY: {'set' if gemini_key else 'MISSING'} (len={len(gemini_key)})")
    if not fal_key:
        raise RuntimeError("FAL_KEY not set in .env")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not set in .env")
    return True


@step("2. Build Fal Client")
def build_client(model: str):
    from generate_video.fal_client import FalVideoClient
    client = FalVideoClient(model=model, timeout_seconds=600)
    print(f"  Model: {client.model}")
    print(f"  Profile: {client._profile}")
    print(f"  Timeout: {client.timeout_seconds}s")
    return client


@step("3. Generate Briefs")
def generate_briefs():
    from iterate.pipeline_runner import PipelineConfig, generate_briefs as gen_briefs
    pconfig = PipelineConfig(
        num_batches=1,
        batch_size=1,
        max_cycles=1,
        ledger_path="/tmp/test_video_diag_ledger.jsonl",
        dry_run=False,
        global_seed="diag_test",
        persona=None,
        audience="parents",
        campaign_goal="conversion",
        key_message="SAT score improvement",
    )
    briefs = gen_briefs(pconfig)[:1]
    print(f"  Generated {len(briefs)} brief(s)")
    if briefs:
        b = briefs[0]
        print(f"  Brief ID: {b.get('brief_id')}")
        print(f"  Brief keys: {sorted(b.keys())}")
    return briefs


@step("4. Expand Brief + Generate Ad Copy")
def generate_copy(brief: dict):
    from generate.brief_expansion import expand_brief
    from generate.ad_generator import generate_ad
    from generate.seeds import get_ad_seed
    from dataclasses import asdict

    expanded = expand_brief(brief, persona=None, ledger_path="/tmp/test_video_diag_ledger.jsonl")
    expanded_dict = asdict(expanded) if hasattr(expanded, '__dataclass_fields__') else expanded
    print(f"  Expanded brief type: {type(expanded).__name__}")
    print(f"  Expanded brief keys: {sorted(expanded_dict.keys()) if isinstance(expanded_dict, dict) else 'N/A'}")

    seed = get_ad_seed("diag_test", brief.get("brief_id", "001"), 0)
    ad = generate_ad(
        expanded,
        seed=seed,
        cycle_number=0,
        ledger_path="/tmp/test_video_diag_ledger.jsonl",
        creative_brief="auto",
    )
    ad_copy = ad.to_evaluator_input()
    print(f"  Ad ID: {ad.ad_id}")
    print(f"  Ad copy keys: {sorted(ad_copy.keys())}")
    print(f"  Headline: {ad_copy.get('headline', '???')[:80]}")
    print(f"  Primary text: {ad_copy.get('primary_text', '???')[:80]}")
    return expanded, ad_copy, ad.ad_id, seed


@step("5. Build Video Spec")
def build_spec(raw_brief: dict, session_config: dict, ad_copy: dict):
    from generate_video.video_spec import build_video_spec, build_kling_prompt
    # NOTE: pipeline_task.py passes the RAW brief dict, not the ExpandedBrief object
    print(f"  Brief type: {type(raw_brief).__name__}")
    print(f"  Brief keys: {sorted(raw_brief.keys()) if isinstance(raw_brief, dict) else 'N/A'}")
    spec = build_video_spec(
        expanded_brief=raw_brief,
        session_config=session_config,
        ad_copy=ad_copy,
    )
    prompt = build_kling_prompt(spec)
    print(f"  Scene: {spec.scene[:80]}")
    print(f"  Visual style: {spec.visual_style}")
    print(f"  Camera: {spec.camera_movement}")
    print(f"  Duration: {spec.duration}s")
    print(f"  Aspect ratio: {spec.aspect_ratio}")
    print(f"  Prompt length: {len(prompt)} chars")
    print(f"  Prompt preview: {prompt[:200]}...")
    return spec, prompt


@step("6. Call Fal API (video generation)")
def call_fal(client, spec, prompt: str, output_path: str):
    print(f"  Model: {client.model}")
    print(f"  Duration: {spec.duration}s (formatted: {client._format_duration(client.normalize_duration(spec.duration))})")
    print(f"  Aspect ratio: {spec.aspect_ratio} (normalized: {client.normalize_aspect_ratio(spec.aspect_ratio)})")
    print(f"  Output path: {output_path}")
    print("  Calling fal_client.subscribe()...")
    print("  (This may take 2-5 minutes depending on model)")

    t0 = time.time()
    result_path = client.generate_video(
        prompt=prompt,
        duration=spec.duration,
        aspect_ratio=spec.aspect_ratio,
        audio=spec.audio_mode == "with_audio",
        negative_prompt=spec.negative_prompt,
        output_path=output_path,
    )
    elapsed = time.time() - t0
    print(f"  Fal API completed in {elapsed:.1f}s")
    print(f"  Result path: {result_path}")
    print(f"  Remote URL: {client._last_remote_url}")

    # Check file
    from pathlib import Path
    p = Path(result_path)
    if p.exists():
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"  File size: {size_mb:.2f} MB")
    else:
        raise FileNotFoundError(f"Video file not found at {result_path}")

    return result_path


def main():
    parser = argparse.ArgumentParser(description="Video generation diagnostic")
    parser.add_argument(
        "--model",
        default="fal-ai/wan/v2.2-5b/text-to-video/distill",
        help="Fal model ID (default: wan distill — cheapest/fastest)",
    )
    parser.add_argument("--duration", type=int, default=4, help="Video duration in seconds")
    parser.add_argument(
        "--skip-gen", action="store_true",
        help="Skip actual Fal API call (test everything up to it)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("VIDEO GENERATION DIAGNOSTIC")
    print(f"Model: {args.model}")
    print(f"Duration: {args.duration}s")
    print("=" * 60)

    # Step 1: Keys
    if not check_keys():
        sys.exit(1)

    # Step 2: Client
    client = build_client(args.model)
    if not client:
        sys.exit(1)

    # Step 3: Briefs
    briefs = generate_briefs()
    if not briefs:
        sys.exit(1)

    # Step 4: Copy
    result = generate_copy(briefs[0])
    if not result:
        sys.exit(1)
    expanded, ad_copy, ad_id, seed = result

    # Step 5: Spec — pipeline passes raw brief dict, not ExpandedBrief
    session_config = {
        "session_type": "video",
        "video_provider": "fal",
        "video_fal_model": args.model,
        "video_duration": args.duration,
        "video_aspect_ratio": "9:16",
        "video_audio_mode": "silent",
        "audience": "parents",
        "campaign_goal": "conversion",
        "persona": "auto",
    }
    spec_result = build_spec(briefs[0], session_config, ad_copy)
    if not spec_result:
        sys.exit(1)
    spec, prompt = spec_result

    # Step 6: Fal API
    if args.skip_gen:
        print("\n--skip-gen: skipping actual Fal API call")
        print("\nSteps 1-5 all PASSED. The issue is likely in the Fal API call itself.")
    else:
        output_path = f"/tmp/test_video_diag_{int(time.time())}.mp4"
        video_path = call_fal(client, spec, prompt, output_path)
        if video_path:
            print(f"\nAll steps PASSED! Video at: {video_path}")
        else:
            print("\nStep 6 FAILED — Fal API call issue.")

    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
