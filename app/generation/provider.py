"""
T-M4.7: the generation-side counterpart to app/embeddings/provider.py's
EmbeddingProvider -- one interface, Gemini behind it today, a different
LLM (local or otherwise) swappable later without touching callers. This is
what the PRD means by "pluggable LLM/embedding/reranker" -- three
interchangeable-provider requirements, not one.

Two methods, not one, for the same reason EmbeddingProvider has two:
generate_text and generate_structured are genuinely different contracts.
Free text has nothing to validate; structured output has a schema that can
fail validation and needs a repair path (T-M4.8) -- collapsing them into
one method with an optional schema= kwarg would hide that the error
handling is fundamentally different between the two calls.
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@runtime_checkable
class LLMProvider(Protocol):
    model_id: str

    def generate_text(self, prompt: str, *, system: str | None = None, temperature: float = 0.7) -> str:
        """Free-text generation -- no structural contract to validate."""
        ...

    def generate_structured(
        self, prompt: str, schema: type[SchemaT], *, system: str | None = None, temperature: float = 0.0
    ) -> SchemaT:
        """Schema-validated generation. The citation-grounded answer
        (T-M4.8) and the LLM judge (T-M4.10) both need output that's a
        specific, parseable shape -- not prose to parse claims back out
        of after the fact."""
        ...
