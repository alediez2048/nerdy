# Ad-Ops-Autopilot — Brand profile field validators (PJ-05)
"""Per-column validation for ``save_field``.

The agent's ``save_field`` tool calls ``validate(name, value)`` before
writing. Validation errors are surfaced back to the LLM as tool results
(so it can adapt the next turn), NOT exceptions to the user.

The ``TYPED_COLUMNS`` mapping IS the schema-level allowlist. Anything
not in it gets ``unknown_column`` rejected — the LLM cannot write a
field the backend doesn't know about (e.g. ``hax`` or ``user_id``).
"""
from __future__ import annotations

import json
import re
from typing import Any

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Column → validation "kind". Maps every writable typed-core column on
# ``brand_profile`` to a validator. Adding a column here is the only way
# to make it agent-writable.
TYPED_COLUMNS: dict[str, str] = {
    "business_name": "str",
    "industry": "snake_case_str",
    "audience": "str",
    "mission": "str",
    "value_props": "str_list",
    "tone_descriptors": "str_list",
    "avoid_phrases": "str_list",
    "do_dont_rules": "do_dont",
    "palette_primary_hex": "hex",
    "palette_secondary_hex": "hex",
    "palette_accent_hex": "hex",
}


def validate(name: str, value: Any) -> dict[str, Any]:
    """Return ``{ok: True, value: <normalized>}`` or ``{ok: False, error: ...}``."""
    if name not in TYPED_COLUMNS:
        return {"ok": False, "error": f"unknown_column:{name}"}
    kind = TYPED_COLUMNS[name]

    if kind == "hex":
        if not (isinstance(value, str) and HEX_RE.match(value)):
            return {"ok": False, "error": "invalid_hex_format"}
        return {"ok": True, "value": value.lower()}

    if kind == "str_list":
        if not isinstance(value, list):
            return {"ok": False, "error": "must_be_list_of_strings"}
        cleaned = [v.strip() for v in value if isinstance(v, str) and v.strip()]
        if not cleaned:
            return {"ok": False, "error": "must_be_nonempty_string_list"}
        return {"ok": True, "value": cleaned}

    if kind == "do_dont":
        if not isinstance(value, dict) or set(value.keys()) != {"do", "dont"}:
            return {"ok": False, "error": "must_be_do_dont_object"}
        if not all(isinstance(v, list) and all(isinstance(s, str) for s in v) for v in value.values()):
            return {"ok": False, "error": "do_and_dont_must_be_string_lists"}
        return {"ok": True, "value": value}

    # str / snake_case_str
    if not isinstance(value, str) or not value.strip():
        return {"ok": False, "error": "must_be_nonempty_string"}
    cleaned = value.strip()
    if kind == "snake_case_str":
        cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned.lower()).strip("_")
        if not cleaned:
            return {"ok": False, "error": "must_be_nonempty_string"}
    return {"ok": True, "value": cleaned}


def validate_extras_value(value: Any) -> dict[str, Any]:
    """``update_extra`` accepts anything JSON-serializable."""
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return {"ok": False, "error": "value_not_json_serializable"}
    return {"ok": True, "value": value}


def normalize_extras_key(key: str) -> str:
    """LLM-suggested keys are normalized to snake_case so we can dedupe."""
    if not isinstance(key, str) or not key.strip():
        return ""
    return re.sub(r"[^a-z0-9_]+", "_", key.lower()).strip("_")


# ``brand_profile`` columns the agent must NOT use ``update_extra`` for —
# they have typed save_field handlers and would silently shadow the
# typed-core value otherwise.
RESERVED_EXTRAS_KEYS: frozenset[str] = frozenset(TYPED_COLUMNS.keys())


def brief_field_ok(value: Any) -> bool:
    """Field-level check used by ``propose_brief``: non-empty string."""
    return isinstance(value, str) and bool(value.strip())
