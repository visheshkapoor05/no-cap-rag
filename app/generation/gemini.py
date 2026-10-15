"""
T-M4.7: the real Gemini adapter behind LLMProvider. Mirrors
app/embeddings/gemini.py's singleton/lifecycle pattern exactly.
"""
from __future__ import annotations

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.generation.provider import SchemaT

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
        self._client = genai.Client(api_key=settings.gemini.api_key.get_secret_value())

    def generate_text(self, prompt: str, *, system: str | None = None, temperature: float = 0.7) -> str:
        config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
        result = self._client.models.generate_content(model=MODEL_ID, contents=prompt, config=config)
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
        result = self._client.models.generate_content(model=MODEL_ID, contents=prompt, config=config)
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

        retry_result = self._client.models.generate_content(model=MODEL_ID, contents=repair_prompt, config=config)
        retried = self._parse(retry_result, schema)
        if retried is not None:
            return retried

        try:
            return schema.model_validate_json(retry_result.text)
        except ValidationError as second_error:
            raise GenerationError(
                f"structured generation failed schema validation twice: {second_error}"
            ) from second_error

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
