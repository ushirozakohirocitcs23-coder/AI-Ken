"""LLM provider abstraction.

Supported providers (set LLM_PROVIDER):
  * anthropic – Anthropic Messages API (default; set ANTHROPIC_API_KEY)
  * openai    – any OpenAI-compatible Chat Completions endpoint (OpenAI, Groq, OpenRouter,
                Ollama at http://localhost:11434/v1, Gemini's OpenAI endpoint, ...)
  * mock      – deterministic offline provider, ONLY when APP_ENV=test (used by the test suite)

If the provider is not configured, LLMNotConfigured is raised and the API returns a clear
setup message (HTTP 503) instead of pretending a poem was generated.
"""
from __future__ import annotations

import json
import re
import time

import httpx

from ..config import settings


class LLMNotConfigured(RuntimeError):
    pass


class LLMError(RuntimeError):
    pass


def llm_status() -> dict:
    ok, hint = settings.llm_configured()
    model = {"anthropic": settings.anthropic_model, "openai": settings.openai_model, "mock": "mock"}.get(
        settings.llm_provider, "?")
    return {"provider": settings.llm_provider, "model": model, "configured": ok, "setup_hint": None if ok else hint}


def complete(system: str, prompt: str, *, max_tokens: int = 1200, temperature: float = 0.8) -> str:
    ok, hint = settings.llm_configured()
    if not ok:
        raise LLMNotConfigured(hint)
    provider = settings.llm_provider
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            if provider == "anthropic":
                return _anthropic(system, prompt, max_tokens, temperature)
            if provider == "openai":
                return _openai(system, prompt, max_tokens, temperature)
            if provider == "mock":
                from .llm_mock import mock_complete
                return mock_complete(system, prompt)
            raise LLMNotConfigured(hint)
        except LLMNotConfigured:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_err = exc
        except LLMError as exc:
            last_err = exc
            if "status 4" in str(exc) and "status 429" not in str(exc):
                break  # client errors (bad key, bad model) won't fix themselves
        time.sleep(1.5 * (attempt + 1))
    raise LLMError(f"The AI service is unavailable right now ({last_err}).")


def _anthropic(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": settings.anthropic_model, "max_tokens": max_tokens, "temperature": temperature,
              "system": system, "messages": [{"role": "user", "content": prompt}]},
        timeout=settings.llm_timeout,
    )
    if resp.status_code != 200:
        raise LLMError(f"Anthropic API status {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


def _openai(system: str, prompt: str, max_tokens: int, temperature: float) -> str:
    headers = {"content-type": "application/json"}
    if settings.openai_api_key:
        headers["authorization"] = f"Bearer {settings.openai_api_key}"
    resp = httpx.post(
        settings.openai_base_url.rstrip("/") + "/chat/completions",
        headers=headers,
        json={"model": settings.openai_model, "max_tokens": max_tokens, "temperature": temperature,
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
        timeout=settings.llm_timeout,
    )
    if resp.status_code != 200:
        raise LLMError(f"OpenAI-compatible API status {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"] or ""


def parse_json(text: str) -> dict:
    """Extract the first JSON object from a model response (tolerates code fences / prose)."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = cleaned.find("{", start + 1)
    raise LLMError("The AI response was not valid JSON.")


def complete_json(system: str, prompt: str, **kw) -> dict:
    text = complete(system + "\n\nRespond with ONE valid JSON object only. No markdown, no commentary.", prompt, **kw)
    try:
        return parse_json(text)
    except LLMError:
        # one corrective retry
        text = complete(system + "\n\nYour previous reply was not valid JSON. Return ONLY a JSON object.", prompt, **kw)
        return parse_json(text)
