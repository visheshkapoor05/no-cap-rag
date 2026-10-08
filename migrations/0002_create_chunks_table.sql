-- One row per retrievable chunk, produced by app/chunking from a
-- document's extracted text. embedding_id/sparse_terms stay NULL until
-- M3 actually embeds/indexes each chunk -- reserved now so M3 doesn't
-- need a schema change later, the same pattern as T-M1.8's index_status.
CREATE TABLE IF NOT EXISTS chunks (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id       UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    section_path      TEXT NOT NULL DEFAULT '',
    contextual_prefix TEXT NOT NULL,
    text              TEXT NOT NULL,
    token_count       INTEGER NOT NULL,
    embedding_id      TEXT,
    sparse_terms      JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every chunk lookup in this project starts from "which document" -- M3's
-- retrieval, M5's citation resolution, a future re-chunk-this-document pass.
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks (document_id);
