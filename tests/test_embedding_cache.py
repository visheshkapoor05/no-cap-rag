"""T-M2.6: the embedding cache must skip calling embed_fn on a repeat of
the same (text, model_id), and must *not* skip it when either changes."""
from app.embeddings import EmbeddingCache


def _counting_embedder(calls: list[str]):
    def embed_fn(text: str) -> list[float]:
        calls.append(text)
        return [float(len(text))]

    return embed_fn


def test_second_call_with_same_text_and_model_is_a_cache_hit(tmp_path):
    cache = EmbeddingCache(tmp_path / "cache.db")
    calls: list[str] = []
    embed_fn = _counting_embedder(calls)

    first = cache.get_or_embed("some chunk text", "model-a", embed_fn)
    second = cache.get_or_embed("some chunk text", "model-a", embed_fn)

    assert first == second
    assert calls == ["some chunk text"]  # embed_fn ran exactly once


def test_different_model_id_is_a_cache_miss_even_for_the_same_text(tmp_path):
    """The whole reason model_id is part of the key: adding a second
    provider later must not silently reuse the first provider's vectors."""
    cache = EmbeddingCache(tmp_path / "cache.db")
    calls: list[str] = []
    embed_fn = _counting_embedder(calls)

    cache.get_or_embed("some chunk text", "model-a", embed_fn)
    cache.get_or_embed("some chunk text", "model-b", embed_fn)

    assert len(calls) == 2


def test_different_text_is_a_cache_miss_even_for_the_same_model(tmp_path):
    """An edited chunk must re-embed, not silently reuse a stale vector."""
    cache = EmbeddingCache(tmp_path / "cache.db")
    calls: list[str] = []
    embed_fn = _counting_embedder(calls)

    cache.get_or_embed("original text", "model-a", embed_fn)
    cache.get_or_embed("edited text", "model-a", embed_fn)

    assert len(calls) == 2


def test_cache_survives_being_reopened_from_the_same_path(tmp_path):
    """The real point of disk over memory: a brand-new EmbeddingCache
    instance (a new process, days later) must still see yesterday's
    entries just by pointing at the same file."""
    path = tmp_path / "cache.db"
    calls: list[str] = []
    embed_fn = _counting_embedder(calls)

    EmbeddingCache(path).get_or_embed("persisted text", "model-a", embed_fn)

    reopened = EmbeddingCache(path)
    reopened.get_or_embed("persisted text", "model-a", embed_fn)

    assert len(calls) == 1
    assert len(reopened) == 1


def test_get_returns_none_on_a_genuine_miss(tmp_path):
    cache = EmbeddingCache(tmp_path / "cache.db")
    assert cache.get("never embedded", "model-a") is None


def test_embedding_the_real_full_corpus_twice_makes_zero_calls_the_second_time(tmp_path, full_corpus_chunks):
    """T-M2.11: 'run ingestion twice, assert the second run makes zero
    embedding API calls' -- proven here against the real 149 chunks from the
    full corpus (full_corpus_chunks), not synthetic toy strings. The earlier
    tests in this file prove the cache's logic is correct on a handful of
    hand-picked cases; this proves it holds at the actual scale and against
    the actual text (contextual_prefix + text, the real string this
    corpus's chunks would be embedded with) this project will really use."""
    with full_corpus_chunks.connection() as conn:
        rows = conn.execute("SELECT contextual_prefix, text FROM chunks").fetchall()
    texts = [r["contextual_prefix"] + r["text"] for r in rows]
    assert len(texts) == 149  # the real, known corpus size as of T-M2.10

    model_id = "text-embedding-3-small"
    cache_path = tmp_path / "cache.db"
    calls: list[str] = []
    embed_fn = _counting_embedder(calls)

    # Pass 1 -- a fresh cache file, as if this were the very first ingestion
    # run: one EmbeddingCache instance (one process), embedding every chunk.
    first_run = EmbeddingCache(cache_path)
    first_pass_vectors = [first_run.get_or_embed(t, model_id, embed_fn) for t in texts]
    assert len(calls) == 149  # every chunk was a genuine miss

    # Pass 2 -- a brand-new EmbeddingCache instance (the real cross-run
    # scenario: a second script invocation days later, not just a second
    # call within the same process) pointed at the identical file.
    calls.clear()
    second_run = EmbeddingCache(cache_path)
    second_pass_vectors = [second_run.get_or_embed(t, model_id, embed_fn) for t in texts]

    assert calls == []  # zero embedding API calls on the second run
    assert second_pass_vectors == first_pass_vectors
