"""Ad export writer — Meta-ready file output (P1-18).

Writes assembled ads to structured export folders with copy.json,
winning image, metadata.json, and variant subfolder. File naming
follows Meta Ads Manager conventions.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from output.assembler import AssembledAd, assemble_ad, is_publishable

logger = logging.getLogger(__name__)


@dataclass
class ExportSummary:
    """Summary of a batch export operation."""

    exported: int
    skipped: int
    failed: int
    export_paths: list[str]


def export_ad(assembled: AssembledAd, output_dir: str) -> str:
    """Export an assembled ad to a structured folder.

    Creates:
        {output_dir}/{ad_id}/copy.json
        {output_dir}/{ad_id}/metadata.json
        {output_dir}/{ad_id}/image_winner.png (if source exists)

    Args:
        assembled: The assembled ad to export.
        output_dir: Base directory for exports.

    Returns:
        Path to the export folder.
    """
    ad_dir = Path(output_dir) / assembled.ad_id
    ad_dir.mkdir(parents=True, exist_ok=True)

    # Write copy.json
    copy_path = ad_dir / "copy.json"
    copy_path.write_text(json.dumps(assembled.copy, indent=2))

    # Write metadata.json
    metadata = {
        "ad_id": assembled.ad_id,
        "text_scores": assembled.text_scores,
        "image_selection": assembled.image_selection,
        "generation_metadata": assembled.generation_metadata,
    }
    meta_path = ad_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))

    # Copy winning image if it exists
    if assembled.winning_image_path:
        src = Path(assembled.winning_image_path)
        if src.exists():
            dst = ad_dir / f"image_winner{src.suffix}"
            shutil.copy2(str(src), str(dst))

    logger.info("Exported ad %s to %s", assembled.ad_id, ad_dir)
    return str(ad_dir)


def export_batch(
    ad_ids: list[str],
    ledger_path: str,
    output_dir: str,
) -> ExportSummary:
    """Export all publishable ads in a batch.

    Skips image-blocked ads. Assembles and exports each publishable ad.

    Args:
        ad_ids: List of ad identifiers to consider.
        ledger_path: Path to the JSONL ledger.
        output_dir: Base directory for exports.

    Returns:
        ExportSummary with counts of exported, skipped, and failed ads.
    """
    exported = 0
    skipped = 0
    failed = 0
    paths: list[str] = []

    for ad_id in ad_ids:
        if not is_publishable(ad_id, ledger_path):
            skipped += 1
            logger.info("Skipped %s (not publishable)", ad_id)
            continue

        try:
            assembled = assemble_ad(ad_id, ledger_path)
            path = export_ad(assembled, output_dir)
            paths.append(path)
            exported += 1
        except Exception as e:
            logger.error("Export failed for %s: %s", ad_id, e)
            failed += 1

    logger.info(
        "Batch export: %d exported, %d skipped, %d failed",
        exported, skipped, failed,
    )

    return ExportSummary(
        exported=exported,
        skipped=skipped,
        failed=failed,
        export_paths=paths,
    )
