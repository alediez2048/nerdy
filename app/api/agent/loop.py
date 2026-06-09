# Ad-Ops-Autopilot — Agent conversation loop (PJ-04)
"""Gemini 2.5 Flash function-calling loop with bounded iterations.

PJ-04 scaffold: two terminal stubs (``ask_user``, ``finish_touchpoint``)
plus the closure-bound ``save_field`` placeholder used by the security
test. PJ-05 replaces the function declarations with the full tool list.

Two invariants the tests in ``test_agent_converse.py`` lock in:

1. **MAX_TOOL_ITERATIONS = 8.** If the model never emits a terminal
   tool call, the loop exits with a fallback message — not an infinite
   billable loop.
2. **No ``user_id`` parameter on any function declaration.** This is
   the schema-level enforcement of the closure-binding rule from
   PJ-00 §3 decision 12 / GRILL Q2.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from app.api.agent.toolbox import ToolBox

logger = logging.getLogger(__name__)

# Per PJ-00 §6.4
MAX_TOOL_ITERATIONS = 8
MODEL_NAME = "gemini-2.5-flash"


def _agent_key() -> str:
    """Resolve the host-side key. AGENT_GEMINI_API_KEY first; falls back
    to GEMINI_API_KEY for local dev convenience."""
    key = os.getenv("AGENT_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    if not key:
        raise RuntimeError(
            "AGENT_GEMINI_API_KEY (or GEMINI_API_KEY fallback) must be set"
        )
    return key


# ---------------------------------------------------------------------------
# Function declarations for Gemini. NO ``user_id`` parameter anywhere.
# ---------------------------------------------------------------------------


_ALL_DECLARATIONS: dict[str, dict[str, Any]] = {
    "ask_user": {
        "name": "ask_user",
        "description": (
            "Return to the user with a question or remark. The frontend "
            "renders the message and waits for the user's reply. Use this "
            "to ask one focused question at a time."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {
                    "type": "STRING",
                    "description": "The text shown to the user.",
                },
            },
            "required": ["message"],
        },
    },
    "finish_touchpoint": {
        "name": "finish_touchpoint",
        "description": (
            "End the current conversation. For onboarding, the backend "
            "will flip the user's onboarding_phase to 'complete'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": "One-sentence wrap-up.",
                },
            },
            "required": ["summary"],
        },
    },
    "save_field": {
        "name": "save_field",
        "description": (
            "Write a typed-core field to the user's brand profile. Allowed "
            "fields: business_name, industry, audience, mission, value_props, "
            "tone_descriptors, avoid_phrases, do_dont_rules, "
            "palette_primary_hex, palette_secondary_hex, palette_accent_hex."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "value": {"description": "Field value. Type depends on the field."},
                "confidence": {"type": "NUMBER", "description": "0.0-1.0."},
                "rationale": {"type": "STRING"},
            },
            "required": ["name", "value"],
        },
    },
    "update_extra": {
        "name": "update_extra",
        "description": (
            "Stash an industry-specific fact in the brand profile's open "
            "extras bag. Use this for facts that don't fit a typed-core "
            "column (e.g. subjects_taught, cuisine_style, icp_segment)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Normalized to snake_case."},
                "value": {"description": "JSON-serializable value."},
                "confidence": {"type": "NUMBER"},
                "rationale": {"type": "STRING"},
            },
            "required": ["key", "value"],
        },
    },
    "ingest_asset": {
        "name": "ingest_asset",
        "description": (
            "Read extracted facts (palette, fonts) from an asset the user "
            "uploaded. Optionally also writes the palette into typed-core."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "asset_id": {"type": "STRING"},
                "derive_palette": {"type": "BOOLEAN"},
                "derive_fonts": {"type": "BOOLEAN"},
            },
            "required": ["asset_id"],
        },
    },
    "advance_phase": {
        "name": "advance_phase",
        "description": (
            "Move the onboarding flow forward by exactly one phase. Order: "
            "identify -> core -> extras -> assets -> good_enough -> complete. "
            "Skipping is rejected; same-phase calls are idempotent."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "next_phase": {"type": "STRING"},
                "why": {"type": "STRING"},
            },
            "required": ["next_phase"],
        },
    },
    "mark_good_enough": {
        "name": "mark_good_enough",
        "description": (
            "Flip the session-creation gate. Backend will reject unless all "
            "typed-core minimums are met (business_name, industry, audience, "
            "mission, >=2 value_props, >=2 tone_descriptors)."
        ),
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    "propose_brief": {
        "name": "propose_brief",
        "description": (
            "(pre_session_prep only) Propose a session brief based on the "
            "user's brand profile. Does NOT write to brand_profile. The "
            "frontend pre-fills NewSessionForm with these values."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "audience": {"type": "STRING"},
                "persona": {"type": "STRING"},
                "campaign_goal": {"type": "STRING"},
                "key_message": {"type": "STRING"},
                "creative_brief": {"type": "STRING"},
            },
            "required": [
                "audience", "persona", "campaign_goal",
                "key_message", "creative_brief",
            ],
        },
    },
}


def build_function_declarations(
    allowed_tools: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return the function-declaration dicts sent to Gemini.

    ``allowed_tools`` (from ``whitelist_for(touchpoint, phase)``) filters
    to only the tools legal in the current context. The order matches the
    input list. If ``None``, all declarations are returned (used by the
    PJ-04 security test that introspects every declaration).
    """
    if allowed_tools is None:
        return list(_ALL_DECLARATIONS.values())
    out: list[dict[str, Any]] = []
    for name in allowed_tools:
        decl = _ALL_DECLARATIONS.get(name)
        if decl is not None:
            out.append(decl)
    return out


# ---------------------------------------------------------------------------
# Loop entry. Returns one of:
#   {"assistant_message": "...", "exit_reason": "ask_user"|"finish_touchpoint"|"max_iter"|"no_tool"}
# ---------------------------------------------------------------------------


def run_conversation_turn(
    toolbox: ToolBox,
    history: list[dict[str, Any]],
    system_prompt: str,
    function_decls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one synchronous turn of the agent loop.

    ``history`` is a list of ``{role, content}`` dicts already converted
    from ``conversation_messages`` rows. PJ-04 scaffold uses a minimal
    text-only conversion; PJ-05 will add tool-call / tool-result parts
    when those become persistent.
    """
    from google import genai
    from google.genai import types

    decls = function_decls or build_function_declarations()

    # Convert dict declarations to SDK types.
    typed_decls = [
        types.FunctionDeclaration(
            name=d["name"],
            description=d.get("description", ""),
            parameters=d.get("parameters"),
        )
        for d in decls
    ]
    tools = [types.Tool(function_declarations=typed_decls)]

    # Build the contents list from history. v1 = text only.
    contents: list[types.Content] = []
    for msg in history:
        role = msg.get("role", "user")
        text = msg.get("content") or ""
        if not text:
            continue
        contents.append(
            types.Content(
                role="model" if role == "assistant" else "user",
                parts=[types.Part.from_text(text=text)],
            )
        )

    client = genai.Client(api_key=_agent_key())

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools,
                temperature=0.4,
                max_output_tokens=2048,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        function_call = _extract_function_call(response)
        if function_call is None:
            # No tool call emitted — treat as a plain text response.
            text = (response.text or "").strip() or "(no response)"
            return {
                "assistant_message": text,
                "exit_reason": "no_tool",
                "iterations": iteration + 1,
            }

        name = function_call.get("name", "")
        args = function_call.get("args") or {}
        result = toolbox.dispatch(name, args)

        if result.get("_terminal"):
            text = result.get("message") or result.get("summary") or ""
            return {
                "assistant_message": text,
                "exit_reason": result.get("kind", name),
                "iterations": iteration + 1,
            }

        # Non-terminal tool result — feed back to the model and loop.
        contents.append(
            types.Content(
                role="model",
                parts=[types.Part.from_function_call(name=name, args=args)],
            )
        )
        contents.append(
            types.Content(
                role="user",  # tool results are sent as the "user" role in the new SDK
                parts=[
                    types.Part.from_function_response(name=name, response=result)
                ],
            )
        )

    # Loop bound reached. Return a fallback message so the UX doesn't dead-end.
    logger.warning(
        "agent loop exited after %d iterations without a terminal tool call",
        MAX_TOOL_ITERATIONS,
    )
    return {
        "assistant_message": (
            "I got a bit stuck — could you say that again or rephrase?"
        ),
        "exit_reason": "max_iter",
        "iterations": MAX_TOOL_ITERATIONS,
    }


def _extract_function_call(response: Any) -> dict[str, Any] | None:
    """Return the first function call in the response, or ``None`` if the
    model emitted a plain-text response.
    """
    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", []) or []:
            fc = getattr(part, "function_call", None)
            if fc is None:
                continue
            name = getattr(fc, "name", "")
            args_obj = getattr(fc, "args", {}) or {}
            # The SDK returns args as a proto-Map; coerce to plain dict.
            try:
                args = dict(args_obj)
            except (TypeError, ValueError):
                args = {}
            if name:
                return {"name": name, "args": args}
    return None
