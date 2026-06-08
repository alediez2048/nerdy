# Ad-Ops-Autopilot — Brand asset storage helper (PJ-02)
"""Path construction + path-traversal guard for uploaded brand assets.

Files live under ``output/brand_assets/<user_id>/<uuid>.<ext>`` on the
Railway volume (same volume as ``output/images/`` and ``output/videos/``).
The user-supplied ``original_filename`` is used ONLY to derive the
extension; the on-disk name is always a fresh UUID. This makes path
traversal via crafted filenames impossible — there's nothing to traverse.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

# Accepted extensions per PJ-00 §9.1.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".svg", ".pdf"})

# Accepted MIME types — both extension AND mime must validate.
ALLOWED_MIMES: frozenset[str] = frozenset({
    "image/png",
    "image/jpeg",
    "image/svg+xml",
    "application/pdf",
})

# Allowed asset_type values per PJ-00 §5.3.
ASSET_TYPES: frozenset[str] = frozenset({"logo", "style_guide", "font", "reference", "other"})

MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB per PJ-00 §9.1

# Module-level so tests can monkey-patch a temp dir.
STORAGE_ROOT: Path = Path("output/brand_assets")


class UnsupportedExtension(ValueError):
    """Filename has an extension we don't accept."""


def build_storage_path(user_id: str, original_filename: str) -> tuple[str, Path]:
    """Return ``(asset_id, absolute_path)`` for a new upload.

    ``original_filename`` is consulted ONLY for its extension; the on-disk
    name is the UUID. The per-user directory is created if missing.

    Raises ``UnsupportedExtension`` when the extension isn't allowlisted.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedExtension(f"unsupported extension: {ext or '(none)'}")
    asset_id = str(uuid4())
    abs_path = STORAGE_ROOT / user_id / f"{asset_id}{ext}"
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    return asset_id, abs_path


def resolve_for_serve(user_id: str, storage_path: str) -> Path:
    """Translate the DB ``storage_path`` into an absolute path for serving,
    re-verifying it stays inside the user's prefix.

    ``storage_path`` is ``<user_id>/<uuid>.<ext>`` (relative to STORAGE_ROOT).
    Defense-in-depth: even if the DB row were tampered with, the resolved
    path must canonically live under ``STORAGE_ROOT/<user_id>/``.
    """
    requested = (STORAGE_ROOT / storage_path).resolve()
    user_root = (STORAGE_ROOT / user_id).resolve()
    requested_str = str(requested)
    user_root_str = str(user_root)
    if not (
        requested_str == user_root_str
        or requested_str.startswith(user_root_str + "/")
    ):
        raise PermissionError("resolved storage_path escapes the user prefix")
    return requested
