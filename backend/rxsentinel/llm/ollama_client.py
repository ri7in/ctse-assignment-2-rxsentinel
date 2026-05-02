"""Async Ollama client with JSON-mode + retry + fallback model.

Wraps the official `ollama` Python client. We use the chat endpoint with
`format="json"` to coax SLMs into reliable structured outputs, and retry on
network blips. If the primary model is unavailable, fall back to the
configured fallback model so a missing model doesn't crash a demo.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import httpx
from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from rxsentinel.config import settings


class OllamaClient:
    """Thin wrapper around `ollama.AsyncClient` with JSON-mode + retries."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
    ) -> None:
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.fallback = fallback_model or settings.ollama_fallback_model
        self._client = AsyncClient(host=self.host)
        self._available_model: str | None = None

    async def _resolve_model(self) -> str:
        """Pick primary if installed, else fallback. Cached after first call."""
        if self._available_model is not None:
            return self._available_model
        try:
            installed = await self._client.list()
            names = {m.get("name", "") for m in installed.get("models", [])}  # type: ignore[union-attr]
            if any(self.model in n for n in names):
                self._available_model = self.model
            elif any(self.fallback in n for n in names):
                self._available_model = self.fallback
            else:
                # Even if neither is listed, attempt the configured primary;
                # ollama will pull-on-demand for some setups.
                self._available_model = self.model
        except (httpx.HTTPError, ConnectionError, OSError):
            self._available_model = self.model
        return self._available_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        max_retries_on_invalid_json: int = 2,
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        """Run a chat completion expecting strict JSON output.

        Args:
            system: System prompt establishing the agent's role + constraints.
            user: User-turn payload (often the input to the agent).
            temperature: Sampling temperature (0.0 = deterministic).
            max_retries_on_invalid_json: How many times to retry if the model
                returns non-parseable JSON despite format=json.

        Returns:
            Parsed JSON object.

        Raises:
            ValueError: If the model never produces parseable JSON.
        """
        model = await self._resolve_model()
        last_err: Exception | None = None
        for _ in range(max_retries_on_invalid_json + 1):
            response = await self._client.chat(
                model=model,
                format="json",
                options={"temperature": temperature, "num_predict": max_tokens},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = response["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                last_err = e
                continue
        raise ValueError(f"Ollama returned non-JSON after retries: {last_err}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def chat_text(
        self, system: str, user: str, *, temperature: float = 0.4, max_tokens: int = 800,
    ) -> str:
        """Run a chat completion expecting free-text output."""
        model = await self._resolve_model()
        response = await self._client.chat(
            model=model,
            options={"temperature": temperature, "num_predict": max_tokens},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response["message"]["content"]

    async def warmup(self) -> None:
        """Send a tiny prompt to load the model into memory.

        Avoids paying the 5-15s cold-start penalty on the first user request.
        Safe to await at startup; failures are silent.
        """
        try:
            await self.chat_text(
                system="You are warming up.", user="ok", temperature=0.0, max_tokens=4,
            )
        except Exception:  # noqa: BLE001
            pass


@lru_cache(maxsize=1)
def get_ollama_client() -> OllamaClient:
    """Return the process-wide singleton Ollama client."""
    return OllamaClient()
