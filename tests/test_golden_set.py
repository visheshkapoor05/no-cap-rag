"""T-M2.9: the committed golden set is exactly 50 questions, matches the
planned category breakdown, and every relevant_chunks/relevant_docs spec it
carries still resolves to exactly one real row in Postgres right now -- a
golden label that's gone stale (e.g. the corpus was re-chunked with
different guard thresholds) would silently make every metric computed
against that question meaningless."""
from collections import Counter

from evals.golden_set import load_golden_set, resolve_chunk_ids, resolve_doc_ids

EXPECTED_COUNTS = {
    "factual_lookup": 15,
    "exact_identifier": 8,
    "multi_hop": 10,
    "unanswerable": 8,
    "ambiguous": 5,
    "version_sensitive": 4,
}


def test_total_is_fifty_questions():
    assert len(load_golden_set()) == 50


def test_category_counts_match_the_plan():
    counts = Counter(q.category for q in load_golden_set())
    assert dict(counts) == EXPECTED_COUNTS


def test_every_question_id_is_unique():
    ids = [q.id for q in load_golden_set()]
    assert len(ids) == len(set(ids))


def test_unanswerable_questions_have_no_relevant_chunks():
    for q in load_golden_set():
        if not q.answerable:
            assert q.relevant_chunks == []
            assert q.relevant_docs == []
            assert q.expected_answer is None


def test_answerable_questions_have_at_least_one_relevant_chunk():
    for q in load_golden_set():
        if q.answerable:
            assert len(q.relevant_chunks) >= 1
            assert len(q.relevant_docs) >= 1
            assert q.expected_answer


def test_every_relevant_chunk_spec_resolves_against_postgres_right_now(full_corpus_chunks):
    """Re-resolves every spec fresh against the live chunks table, rather
    than comparing against UUIDs frozen at build time -- see
    evals/golden_set/build.py's module docstring for why frozen UUIDs go
    stale the moment the corpus is re-ingested (gen_random_uuid() assigns a
    new id on every insert)."""
    for q in load_golden_set():
        if q.answerable:
            chunk_ids = resolve_chunk_ids(full_corpus_chunks, q)
            assert len(chunk_ids) == len(q.relevant_chunks), q.id


def test_every_relevant_doc_spec_resolves_against_postgres_right_now(full_corpus_chunks):
    for q in load_golden_set():
        if q.answerable:
            doc_ids = resolve_doc_ids(full_corpus_chunks, q)
            assert len(doc_ids) == len(q.relevant_docs), q.id


def test_version_sensitive_questions_point_at_the_currently_effective_version():
    """Each version-sensitive question should resolve to exactly one
    document -- the whole point of the category is testing whether the
    system picks the CURRENT policy, not whether it can find both versions."""
    version_sensitive = [q for q in load_golden_set() if q.category == "version_sensitive"]
    assert len(version_sensitive) == 4
    for q in version_sensitive:
        assert len(q.relevant_docs) == 1, q.id
