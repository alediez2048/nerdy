#!/usr/bin/env python
"""Ad-Ops-Autopilot — CLI entry point.

Usage:
    python run_pipeline.py                    # Full run (50 ads, 5 batches)
    python run_pipeline.py --max-ads 10       # Small test run
    python run_pipeline.py --max-ads 1        # Single ad smoke test
    python run_pipeline.py --resume           # Resume from last checkpoint
    python run_pipeline.py --dry-run          # No API calls (mock data)
"""

from __future__ import annotations

import argparse
import logging
import sys

from iterate.pipeline_runner import PipelineConfig, run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ad-Ops-Autopilot — autonomous ad copy generation pipeline",
    )
    parser.add_argument(
        "--max-ads", type=int, default=50,
        help="Total number of ads to generate (default: 50)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=10,
        help="Ads per batch (default: 10)",
    )
    parser.add_argument(
        "--cycles", type=int, default=3,
        help="Max regeneration cycles per ad (default: 3)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint (skip completed work)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without API calls (mock data for testing)",
    )
    parser.add_argument(
        "--seed", type=str, default="nerdy_p1_20",
        help="Global seed for reproducibility (default: nerdy_p1_20)",
    )
    parser.add_argument(
        "--ledger", type=str, default="data/ledger.jsonl",
        help="Path to ledger file (default: data/ledger.jsonl)",
    )
    parser.add_argument(
        "--output", type=str, default="output/ads",
        help="Output directory for exported ads (default: output/ads)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Compute batches from max-ads
    num_batches = max(1, (args.max_ads + args.batch_size - 1) // args.batch_size)

    config = PipelineConfig(
        num_batches=num_batches,
        batch_size=min(args.batch_size, args.max_ads),
        max_cycles=args.cycles,
        ledger_path=args.ledger,
        output_dir=args.output,
        dry_run=args.dry_run,
        global_seed=args.seed,
    )

    logging.info(
        "Pipeline config: %d ads (%d batches x %d), %d cycles, dry_run=%s",
        args.max_ads, num_batches, config.batch_size, config.max_cycles, config.dry_run,
    )

    try:
        summary = run_pipeline(config)
    except KeyboardInterrupt:
        logging.warning("Interrupted — run with --resume to continue")
        return 1

    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Briefs processed:  {summary.total_briefs}")
    print(f"  Ads generated:     {summary.total_generated}")
    print(f"  Ads published:     {summary.total_published}")
    print(f"  Ads discarded:     {summary.total_discarded}")
    print(f"  Ads regenerated:   {summary.total_regenerated}")
    print(f"  Ads escalated:     {summary.total_escalated}")
    print(f"  Batches completed: {summary.batches_completed}")
    publish_rate = (
        summary.total_published / summary.total_generated * 100
        if summary.total_generated > 0 else 0
    )
    print(f"  Publish rate:      {publish_rate:.1f}%")
    print("=" * 60)
    print(f"  Ledger:  {config.ledger_path}")
    print(f"  Output:  {config.output_dir}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
