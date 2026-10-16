-- T-M4.11: one row per benchmark run. Every run records what produced
-- it (dataset version, pipeline config, embedding/reranker/LLM model
-- versions) alongside the metrics it measured -- a PRD reproducibility
-- requirement that's unrecoverable if not captured at run time (you
-- cannot reconstruct "which embedding model produced this Recall@5"
-- after the fact, only at the moment the run actually happened).
CREATE TABLE IF NOT EXISTS experiments (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    config           JSONB NOT NULL,
    dataset_version  TEXT NOT NULL,
    embedding_model  TEXT NOT NULL,
    reranker_model   TEXT,
    llm_model        TEXT NOT NULL,
    metrics          JSONB NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS experiments_created_at_idx ON experiments (created_at);
