"""Pluggable LLM layer for answer synthesis.

The rest of the app talks to `get_provider().stream(system, user_message)` and
doesn't care which model is behind it. Swap providers with the `LLM_PROVIDER`
env var:

  - "groq"      → Llama 3.3 70B on Groq's free tier (default; no credit card)
  - "anthropic" → Claude (paid; richer, includes streamed reasoning)

Each `stream()` is a generator that yields `LLMEvent`s and `return`s an
`LLMUsage` (read via the generator's StopIteration value) — no shared mutable
state, so it's safe under concurrent requests.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator

from django.conf import settings


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMEvent:
    type: str  # "thinking" | "text"
    text: str


class GroqProvider:
    """Free-tier Llama via Groq's OpenAI-compatible API."""

    name = "groq"

    def __init__(self) -> None:
        from groq import Groq

        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com (no credit card) and add it to "
                "backend/.env."
            )
        self._client = Groq(api_key=settings.GROQ_API_KEY)

    def stream(self, system: str, user_message: str) -> Iterator[LLMEvent]:
        usage = LLMUsage()
        stream = self._client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            max_tokens=settings.MAX_OUTPUT_TOKENS,
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            usage_obj = getattr(chunk, "usage", None) or getattr(
                getattr(chunk, "x_groq", None), "usage", None
            )
            if usage_obj:
                usage = LLMUsage(
                    getattr(usage_obj, "prompt_tokens", 0) or 0,
                    getattr(usage_obj, "completion_tokens", 0) or 0,
                )
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield LLMEvent("text", delta.content)
        return usage


class AnthropicProvider:
    """Claude with streamed, summarized reasoning."""

    name = "anthropic"

    def __init__(self) -> None:
        import anthropic

        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to backend/.env, or set "
                "LLM_PROVIDER=groq to use the free provider."
            )
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def stream(self, system: str, user_message: str) -> Iterator[LLMEvent]:
        with self._client.messages.stream(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.MAX_OUTPUT_TOKENS,
            thinking={"type": "adaptive", "display": "summarized"},
            output_config={"effort": settings.ANTHROPIC_EFFORT},
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        yield LLMEvent("thinking", event.delta.thinking)
                    elif event.delta.type == "text_delta":
                        yield LLMEvent("text", event.delta.text)
            final = stream.get_final_message()

        u = final.usage
        return LLMUsage(
            u.input_tokens
            + (u.cache_creation_input_tokens or 0)
            + (u.cache_read_input_tokens or 0),
            u.output_tokens,
        )


_PROVIDERS = {"groq": GroqProvider, "anthropic": AnthropicProvider}


@lru_cache(maxsize=1)
def get_provider():
    provider_cls = _PROVIDERS.get(settings.LLM_PROVIDER)
    if provider_cls is None:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
            f"Choose one of: {', '.join(_PROVIDERS)}."
        )
    return provider_cls()
