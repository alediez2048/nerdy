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


def build_function_declarations() -> list[dict[str, Any]]:
    """Return the function-declaration dicts sent to Gemini.

    Kept as dicts (rather than ``types.FunctionDeclaration`` instances)
    so the security test can introspect them without needing the genai
    SDK loaded. The route converts these into the SDK's typed form at
    call time.
    """
    return [
        {
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
        {
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
        {
            "name": "save_field",
            "description": (
                "Write a typed-core field to the user's brand profile. "
                "PJ-04 scaffold accepts any field name; PJ-05 enforces a "
                "strict allowlist."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "name": {
                        "type": "STRING",
                        "description": "Field name (e.g. business_name, industry, audience).",
                    },
                    "value": {
                        "description": "Field value. Type depends on the field.",
                    },
                },
                "required": ["name", "value"],
            },
        },
    ]


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
