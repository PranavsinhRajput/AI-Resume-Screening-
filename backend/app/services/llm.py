"""Gemini gateway (architecture.md §7.3).

Rate limiting: a semaphore bounds concurrency and a shared "next allowed start" keeps call starts at
least GEMINI_MIN_INTERVAL_SECONDS apart. Retries (tenacity) on 429 / 5xx / timeouts with exponential
backoff + jitter, honoring the server's retry-delay hint. Never logs prompts or responses.
"""

import asyncio
import json
import logging
import re
import time
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_ATTEMPTS = 5
REPAIR_REMINDER = (
    "\n\nYour previous answer was not valid JSON for the required schema. "
    "Return valid JSON only, matching the schema exactly. No prose, no code fences."
)


class LLMUnavailable(Exception):
    """The LLM could not produce an answer (rate limits exhausted, auth problem, outage)."""


class LLMInvalidOutput(Exception):
    """The LLM answered, but not with valid JSON for the schema, even after one repair retry."""


class _Retryable(Exception):
    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__("retryable LLM error")
        self.retry_after = retry_after


_RETRY_DELAY_RE = re.compile(r"retry(?:Delay|_delay)?['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", re.I)


def _retry_hint(exc: Exception) -> float | None:
    match = _RETRY_DELAY_RE.search(str(exc))
    if match:
        try:
            return min(float(match.group(1)), 60.0)
        except ValueError:
            return None
    return None


_base_wait = wait_exponential_jitter(initial=2, max=30)


def _wait(retry_state: RetryCallState) -> float:
    base = _base_wait(retry_state)
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, _Retryable) and exc.retry_after:
        return max(base, exc.retry_after)
    return base


def strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_as(text: str, model: type[T]) -> T:
    data = json.loads(strip_code_fences(text))
    return model.model_validate(data)


class LLMGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
        self._semaphore = asyncio.Semaphore(max(1, settings.GEMINI_MAX_CONCURRENCY))
        self._timing_lock = asyncio.Lock()
        self._next_start = 0.0
        # thinking_budget=0 is a Gemini 2.5 option; newer models reject it with a generic 400.
        self._thinking_supported = "2.5" in settings.GEMINI_MODEL

    async def _wait_for_slot(self) -> None:
        async with self._timing_lock:
            now = time.monotonic()
            delay = self._next_start - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_start = time.monotonic() + self._settings.GEMINI_MIN_INTERVAL_SECONDS

    def _config(self, system: str, schema: type[BaseModel] | None) -> types.GenerateContentConfig:
        kwargs: dict = {
            "system_instruction": system,
            "temperature": 0,
            "response_mime_type": "application/json",
        }
        if schema is not None:
            kwargs["response_schema"] = schema
        if self._thinking_supported:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        return types.GenerateContentConfig(**kwargs)

    async def _call_once(self, system: str, user: str, schema: type[BaseModel] | None) -> str:
        if self._client is None:
            raise LLMUnavailable("GEMINI_API_KEY is not configured")
        async with self._semaphore:
            await self._wait_for_slot()
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._settings.GEMINI_MODEL,
                        contents=user,
                        config=self._config(system, schema),
                    ),
                    timeout=self._settings.GEMINI_TIMEOUT_SECONDS,
                )
            except TimeoutError as exc:
                logger.warning("Gemini call timed out")
                raise _Retryable() from exc
            except genai_errors.APIError as exc:
                code = getattr(exc, "code", None) or 0
                if code == 429 or code >= 500:
                    logger.warning("Gemini transient error %s", code)
                    raise _Retryable(_retry_hint(exc)) from exc
                if code == 400 and self._thinking_supported:
                    # The model may not accept the thinking config (the 400 message doesn't always say
                    # so); drop it for the rest of the process and retry.
                    logger.warning("Gemini rejected thinking config; retrying without it")
                    self._thinking_supported = False
                    raise _Retryable(0.1) from exc
                logger.error("Gemini non-retryable error %s", code)
                raise LLMUnavailable(f"Gemini error {code}") from exc
            except (ConnectionError, OSError) as exc:
                logger.warning("Gemini network error: %s", type(exc).__name__)
                raise _Retryable() from exc
        text = getattr(response, "text", None)
        if not text:
            raise _Retryable()
        return text

    async def _call_with_retries(self, system: str, user: str, schema: type[BaseModel] | None) -> str:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(MAX_ATTEMPTS),
                wait=_wait,
                retry=retry_if_exception(lambda e: isinstance(e, _Retryable)),
                reraise=True,
            ):
                with attempt:
                    return await self._call_once(system, user, schema)
        except _Retryable as exc:
            raise LLMUnavailable("Gemini retries exhausted") from exc
        raise LLMUnavailable("Gemini retries exhausted")  # pragma: no cover

    async def generate_json(
        self,
        system: str,
        user: str,
        schema: type[T],
        response_schema: type[BaseModel] | None = None,
    ) -> T:
        """Call Gemini and validate the JSON answer as `schema`.

        `response_schema` (if given) is the Gemini-friendly schema variant sent to the API; the answer is
        always validated leniently with `schema`. One repair retry on invalid JSON.
        """
        api_schema = response_schema or schema
        text = await self._call_with_retries(system, user, api_schema)
        try:
            return parse_json_as(text, schema)
        except (json.JSONDecodeError, ValidationError):
            logger.info("Gemini returned invalid JSON; repair retry")
        text = await self._call_with_retries(system, user + REPAIR_REMINDER, api_schema)
        try:
            return parse_json_as(text, schema)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMInvalidOutput("Invalid JSON after repair retry") from exc


_instance: LLMGateway | None = None


def get_default_llm() -> LLMGateway:
    global _instance
    if _instance is None:
        _instance = LLMGateway(get_settings())
    return _instance


def set_default_llm(llm: LLMGateway | None) -> None:
    """Test hook."""
    global _instance
    _instance = llm
