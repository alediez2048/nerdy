"""Shared Gemini API wrapper — captures real token usage from every call.

All modules should use call_gemini() or call_gemini_multimodal() instead
of calling client.models.generate_content() directly. This ensures every
API call captures usage_metadata for accurate cost tracking.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from iterate.retry import retry_with_backoff

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"


@dataclass
class GeminiResponse:
    """Response from a Gemini API call with token usage."""

    text: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    model: str


def call_gemini(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_output_tokens: int = 2048,
) -> GeminiResponse:
    """Call Gemini with a text prompt and return response with token usage."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    def _do_call() -> GeminiResponse:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )

        # Extract real token usage from response metadata
        usage = getattr(response, "usage_metadata", None)
        total = getattr(usage, "total_token_count", 0) or 0
        prompt_t = getattr(usage, "prompt_token_count", 0) or 0
        completion_t = getattr(usage, "candidates_token_count", 0) or 0

        return GeminiResponse(
            text=response.text or "",
            total_tokens=total,
            prompt_tokens=prompt_t,
            completion_tokens=completion_t,
            model=model,
        )

    return retry_with_backoff(_do_call)


def call_gemini_multimodal(
    contents: list[Any],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    max_output_tokens: int = 512,
) -> GeminiResponse:
    """Call Gemini with multimodal contents (image/video + text) and return response with token usage."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    def _do_call() -> GeminiResponse:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )

        usage = getattr(response, "usage_metadata", None)
        total = getattr(usage, "total_token_count", 0) or 0
        prompt_t = getattr(usage, "prompt_token_count", 0) or 0
        completion_t = getattr(usage, "candidates_token_count", 0) or 0

        return GeminiResponse(
            text=response.text or "",
            total_tokens=total,
            prompt_tokens=prompt_t,
            completion_tokens=completion_t,
            model=model,
        )

    return retry_with_backoff(_do_call)
