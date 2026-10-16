"""Turning retrieved evidence into a cited answer. See ../../ANALOGY.md."""
from app.generation.context_builder import BuiltContext, Citation, ContextSource, build_context
from app.generation.gemini import GeminiLLMProvider, GenerationError, close_llm_provider, get_llm_provider
from app.generation.generate import CitationError, ResolvedClaim, generate_answer, resolve_claims
from app.generation.provider import LLMProvider
from app.generation.schema import Claim, GeneratedAnswer

__all__ = [
    "LLMProvider",
    "GeminiLLMProvider",
    "GenerationError",
    "get_llm_provider",
    "close_llm_provider",
    "ContextSource",
    "Citation",
    "BuiltContext",
    "build_context",
    "Claim",
    "GeneratedAnswer",
    "generate_answer",
    "CitationError",
    "ResolvedClaim",
    "resolve_claims",
]
