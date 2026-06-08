# Ad-Ops-Autopilot — Vision-pass Celery task (PJ-03)
"""Async vision pass for an uploaded ``brand_asset`` row.

Triggered by ``POST /api/brand-assets/{id}/extract``. The chat path
stays sync (PJ-00 §3 decision 14 / GRILL Q4); this Celery task is the
slow lane (10-25s per call).

Reads the asset's bytes from the Railway volume, dispatches to the
per-asset_type probe in ``app.api.vision``, and writes the result back
into ``brand_assets.extracted_facts``. On Gemini failure we still write
a row of the form ``{"error": "..."}`` so the agent UI can ask the user
to enter the facts manually.
"""
from __future__ import annotations

import logging

from app.api.brand_asset_storage import STORAGE_ROOT
from app.api.vision import PROBES, VisionConfigError
from app.db import SessionLocal, init_db
from app.models.brand_asset import BrandAsset
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_vision(asset_id: str) -> dict:
    """Worker-callable core; separated so tests can call without Celery."""
    init_db()
    db = SessionLocal()
    try:
        row = db.query(BrandAsset).filter_by(id=asset_id).one_or_none()
        if row is None:
            return {"error": f"asset {asset_id!r} not found"}

        probe = PROBES.get(row.asset_type)
        if probe is None:
            facts = {"error": f"no probe for asset_type {row.asset_type!r}"}
        else:
            abs_path = STORAGE_ROOT / row.storage_path
            try:
                file_bytes = abs_path.read_bytes()
            except OSError as e:
                facts = {"error": f"could not read asset file: {e}"}
                file_bytes = None

            if file_bytes is not None:
                try:
                    facts = probe(file_bytes, row.mime_type or "", row.original_filename or "")
                except VisionConfigError as e:
                    logger.error("Vision config not ready: %s", e)
                    facts = {"error": f"vision not configured: {e}"}
                except Exception as e:
                    logger.exception("Vision probe failed for asset %s", asset_id)
                    facts = {"error": f"vision probe failed: {e}"}

        row.extracted_facts = facts
        db.commit()
        return facts
    finally:
        db.close()


@celery_app.task(name="brand_asset.vision_pass", bind=True)
def run_vision_pass(self, asset_id: str) -> dict:
    """Celery entry point. Wraps the pure ``_run_vision`` for retries."""
    return _run_vision(asset_id)
