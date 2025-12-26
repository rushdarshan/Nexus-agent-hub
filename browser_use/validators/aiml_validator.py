"""AIML validator wrapper.

This module provides a small helper to call an external AIML API (via the
OpenAI-compatible client) to get a second opinion on choices produced by the
browser automation agent. Credentials must be provided via environment
variables: `AIML_API_KEY` and optional `AIML_BASE_URL` (defaults to
https://api.aimlapi.com/v1).

Do NOT hardcode API keys in source. Add them to a `.env` file or set them in
your environment. Example `.env`:

    AIML_API_KEY=your_key_here
    AIML_BASE_URL=https://api.aimlapi.com/v1

The implementation uses the OpenAI-compatible `openai` Python client (the
`OpenAI` class) so it should work with the AIML provider when `base_url` is
pointed to the AIML API endpoint.
"""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - graceful fallback
    OpenAI = None


load_dotenv()


def _get_client() -> Optional[OpenAI]:
    if OpenAI is None:
        return None

    api_key = os.getenv("AIML_API_KEY")
    base_url = os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1")
    if not api_key:
        return None

    return OpenAI(api_key=api_key, base_url=base_url)


def validate_choice(choice_text: str, context: Optional[str] = None) -> str:
    """Ask the external AIML API to validate the agent's choice.

    Returns a short judgment string explaining whether the choice is a good
    one, and why. If the AIML client is not configured, returns a helpful
    warning string.
    """
    client = _get_client()
    if client is None:
        return (
            "[Validator unavailable] AIML client not configured. "
            "Set AIML_API_KEY and AIML_BASE_URL in your environment." 
        )

    prompt = (
        "You are an expert assistant that validates another agent's product "
        "selection. The user asked the agent to research and the agent "
        "returned the following choice and explanation:\n\n"
        f"{choice_text}\n\n"
        "Please evaluate whether this is the best choice given the task. "
        "If you agree, reply with a short confirmation and one-sentence "
        "reason. If you disagree, propose the better alternative and a short "
        "rationale. Keep the reply concise (2-3 sentences)."
    )

    if context:
        prompt = f"Context: {context}\n\n" + prompt

    try:
        resp = client.responses.create(model="gpt-4.1-mini", input=prompt)
        # The OpenAI-compatible response structure may vary; try to extract
        # the text safely.
        output = None
        if hasattr(resp, "output") and resp.output:
            # New Responses API
            part = resp.output[0]
            if isinstance(part, dict) and "content" in part:
                # content may be a list
                content = part["content"]
                if isinstance(content, list) and content:
                    # join textual segments
                    texts = [c.get("text", "") for c in content if isinstance(c, dict)]
                    output = "".join(texts).strip()
        # Fallback to string conversion
        if not output:
            output = str(resp)

        return output

    except Exception as e:  # pragma: no cover - surface errors
        return f"[Validator error] Could not call AIML API: {e}"
