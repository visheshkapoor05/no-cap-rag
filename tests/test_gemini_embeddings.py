"""T-M3.7: real calls against the real Gemini API (a genuine cost, a few
cents total) -- proving the SDK usage is actually correct, not just that
the code runs. Mocking the client here would prove nothing about whether
`embed_content`'s real argument shape matches what this adapter sends."""
import pytest

from app.embeddings import EmbeddingCache, GeminiEmbeddingProvider
from app.embeddings.gemini import EMBEDDING_DIM


@pytest.fixture
def provider(tmp_path):
    return GeminiEmbeddingProvider(cache=EmbeddingCache(tmp_path / "cache.db"))


def test_embed_document_returns_a_768_dim_vector(provider):
    vector = provider.embed_document("Active employees receive a 20% discount.")
    assert len(vector) == EMBEDDING_DIM
    assert all(isinstance(v, float) for v in vector)


def test_embed_query_returns_a_768_dim_vector(provider):
    vector = provider.embed_query("What is the employee discount?")
    assert len(vector) == EMBEDDING_DIM


def test_document_and_query_embeddings_of_the_same_text_differ(provider):
    """The whole reason embed_document/embed_query are two methods, not
    one -- RETRIEVAL_DOCUMENT and RETRIEVAL_QUERY task_type measurably
    change the vector Gemini returns for identical input text."""
    text = "Returns are accepted within 30 days of purchase."
    doc_vector = provider.embed_document(text)
    query_vector = provider.embed_query(text)
    assert doc_vector != query_vector


def test_related_document_and_query_are_more_similar_than_unrelated(provider):
    """A real semantic check, not just 'it returns some vector': the
    genuinely matching pair should cosine-score higher than a mismatched
    pair, proving the embeddings actually carry meaning."""
    import math

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb)

    discount_doc = provider.embed_document(
        "Active employees receive a 20% discount on personal purchases."
    )
    matching_query = provider.embed_query("What is the employee discount percentage?")
    unrelated_query = provider.embed_query("How many days of PTO do I accrue per year?")

    assert cosine(discount_doc, matching_query) > cosine(discount_doc, unrelated_query)


def test_second_call_with_same_text_and_task_type_is_a_cache_hit(provider, monkeypatch):
    calls = []
    real_call = provider._call_gemini

    def counting_call(text, task_type):
        calls.append((text, task_type))
        return real_call(text, task_type)

    monkeypatch.setattr(provider, "_call_gemini", counting_call)

    first = provider.embed_document("Gift cards never expire.")
    second = provider.embed_document("Gift cards never expire.")

    assert first == second
    assert len(calls) == 1  # the real API was only hit once


def test_document_and_query_cache_entries_do_not_collide(provider, monkeypatch):
    """Caching on text alone (ignoring task_type) would silently serve a
    query embedding back out of a document-embedding request, or vice
    versa -- this is the regression test for that."""
    calls = []
    real_call = provider._call_gemini
    monkeypatch.setattr(
        provider, "_call_gemini",
        lambda t, tt: (calls.append((t, tt)), real_call(t, tt))[1],
    )

    text = "Loyalty points expire 24 months after the account's last activity."
    provider.embed_document(text)
    provider.embed_query(text)

    assert len(calls) == 2
    assert calls[0][1] == "RETRIEVAL_DOCUMENT"
    assert calls[1][1] == "RETRIEVAL_QUERY"
