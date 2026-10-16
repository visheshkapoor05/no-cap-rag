"""
T-M4.7: the real Gemini adapter behind LLMProvider. Mirrors
app/embeddings/gemini.py's singleton/lifecycle pattern exactly.
"""
from __future__ import annotations

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.generation.provider import SchemaT

# Gemini's own SDK already retries transport-level failures internally; a
# 503 UNAVAILABLE is the API itself returning a valid HTTP response that
# says "try again later" -- real transient flakiness observed mid-run
# during T-M4.14's benchmark, not a bug to fix in the request. The SDK's
# own internal retry also covers httpx.TimeoutException/ConnectError, but
# this outer retry catches both as a second layer in case the SDK's
# retries are exhausted and the exception still surfaces here -- a real
# request hung with no response at all for hours during T-M4.14's
# Experiment F (no client-side timeout existed yet to bound the wait;
# see GeminiLLMProvider.__init__'s http_options=HttpOptions(timeout=...)).
# Anything else (4xx, schema problems) should surface immediately rather
# than being retried blindly.
def _is_transient_server_error(exc: BaseException) -> bool:
    if isinstance(exc, genai_errors.ServerError) and exc.code in (429, 500, 503, 504):
        return True
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


_retry_transient = retry(
    retry=retry_if_exception(_is_transient_server_error),
    wait=wait_exponential(multiplier=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)

# Verified live against the real Gemini API's model list (D-003's "verify
# current Gemini model IDs" instruction) -- not recalled from memory. A
# stable dated/named model, not a "-latest" alias that can shift silently
# under an experiment mid-run.
MODEL_ID = "gemini-2.5-flash"

_REPAIR_PROMPT_TEMPLATE = """{original_prompt}

Your previous response failed schema validation with this error:
{error}

Return ONLY corrected JSON matching the schema. No prose, no markdown fences."""


class GenerationError(Exception):
    """Raised when structured generation still fails validation after one repair attempt."""


class GeminiLLMProvider:
    model_id = MODEL_ID

    def __init__(self) -> None:
        settings = get_settings()
        # A real request found during T-M4.14's Experiment F hung with no
        # response at all -- no exception for _retry_transient to catch,
        # CPU time frozen while elapsed time climbed for hours (same
        # stall signature diagnosed earlier in T-M4.14's main run, but
        # this time the connection never returned *anything*, not even a
        # 503). Without a client-side timeout, nothing bounds that wait.
        self._client = genai.Client(
            api_key=settings.gemini.api_key.get_secret_value(),
            http_options=types.HttpOptions(timeout=60_000),
        )

    def generate_text(self, prompt: str, *, system: str | None = None, temperature: float = 0.7) -> str:
        config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
        result = self._generate_content(prompt, config)
        return result.text

    def generate_structured(
        self, prompt: str, schema: type[SchemaT], *, system: str | None = None, temperature: float = 0.0
    ) -> SchemaT:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )
        result = self._generate_content(prompt, config)
        parsed = self._parse(result, schema)
        if parsed is not None:
            return parsed

        # Malformed-output recovery: one repair attempt, feeding the real
        # validation error back to the model, not a second blind retry.
        try:
            schema.model_validate_json(result.text)
        except ValidationError as first_error:
            repair_prompt = _REPAIR_PROMPT_TEMPLATE.format(original_prompt=prompt, error=first_error)
        else:
            repair_prompt = _REPAIR_PROMPT_TEMPLATE.format(
                original_prompt=prompt, error="response was not valid JSON for the schema"
            )

        retry_result = self._generate_content(repair_prompt, config)
        retried = self._parse(retry_result, schema)
        if retried is not None:
            return retried

        try:
            return schema.model_validate_json(retry_result.text)
        except ValidationError as second_error:
            raise GenerationError(
                f"structured generation failed schema validation twice: {second_error}"
            ) from second_error

    @_retry_transient
    def _generate_content(self, contents: str, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        return self._client.models.generate_content(model=MODEL_ID, contents=contents, config=config)

    @staticmethod
    def _parse(result: types.GenerateContentResponse, schema: type[SchemaT]) -> SchemaT | None:
        """The SDK auto-parses into `response_schema` when it's a Pydantic
        model and the JSON is well-formed -- `.parsed` is None when it
        isn't, which is exactly the malformed-output case the caller
        needs to retry rather than crash on."""
        parsed = result.parsed
        return parsed if isinstance(parsed, schema) else None


_provider: GeminiLLMProvider | None = None


def get_llm_provider() -> GeminiLLMProvider:
    """Built once, lazily -- same singleton pattern as get_embedding_provider()."""
    global _provider
    if _provider is None:
        _provider = GeminiLLMProvider()
    return _provider


def close_llm_provider() -> None:
    global _provider
    _provider = None
