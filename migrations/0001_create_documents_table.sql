-- The archive room's shelving: one row per ingested document, public or
-- synthetic. Chunks/embeddings (M2/M3) are derived from `content_hash`'s
-- text, computed here and re-derivable at any time — this table is the
-- thing that's actually durable.
CREATE TABLE IF NOT EXISTS documents (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url     TEXT,
    type           TEXT NOT NULL,
    title          TEXT NOT NULL,
    version        TEXT,
    effective_date DATE,
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash   TEXT NOT NULL,
    supersedes     UUID REFERENCES documents (id),
    metadata       JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- One row per distinct content, enforced at the schema level too, not just
-- in application code (T-M1.7's idempotency check) — belt and suspenders.
CREATE UNIQUE INDEX IF NOT EXISTS documents_content_hash_key ON documents (content_hash);

-- M8's freshness recrawl looks documents up by source_url to re-fetch them.
CREATE INDEX IF NOT EXISTS documents_source_url_idx ON documents (source_url);
