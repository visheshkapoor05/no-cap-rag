---
id: pub-nordstrom-size-guide
source_url: https://www.nordstrom.com/sizeguides/2188_sizeguide.pdf
retailer: Nordstrom
category: size_guide
fetched_at: 2026-09-11
fetch_method: direct_fetch
fetch_note: >-
  Corrected 2026-09-13: an earlier pass using WebFetch's generic
  content-summarizer concluded this PDF was image-only with no extractable
  text, and this file originally documented it as a failure. Once
  T-M1.5's real ingestion adapter (`pdftotext -layout`, the actual tool
  the pipeline uses) ran against it, it extracted a genuine, structured
  text table. The earlier conclusion was wrong, not the PDF — a concrete
  example of why "prove it with the real tool" matters more than a
  generic assessment. See MANIFEST.md's status note on this row.
is_synthetic: false
content_hash: pending — computed by the ingestion CLI (T-M1.7) against live-fetched text at ingest time, not against this paraphrase
---

> **PUBLIC SOURCE — paraphrased summary, not a verbatim copy.** See
> [MANIFEST.md](../MANIFEST.md) for the licence/terms policy.

# Nordstrom — Size Guide PDF (summary)

`pdftotext -layout` extracts a real sizing table from this PDF: a
brand-specific women's size chart ("Lyssé Women's Size Chart") mapping
size labels to body measurement ranges.

- Size labels: XS, S, M, L, XL, 1X, 2X, 3X — eight sizes, standard through
  extended range.
- Rows: US size (e.g. 2–4, 4–6, ... 26–28), bust, waist, and hip, each
  given as an inch range per size label rather than a single number —
  reflecting that a "size M" spans a range of actual bodies, not one exact
  measurement.
- The table renders with non-standard hyphen characters (Unicode soft
  hyphens, U+00AD) as the range separator instead of a plain `-` — a
  minor but real character-normalization case for a chunker/embedder to
  handle correctly (e.g. `2\xad4″` should be read as "2-4 inches").

## Why this document's history matters more than its content

This file was originally written as a *documented extraction failure* —
see the `fetch_note` above. The correction only happened because T-M1.5
was built and actually run against the real URL with the real tool the
pipeline uses, rather than trusting the earlier generic assessment.
Concretely: **`corpus/public/README.md`'s fetch-outcome table and
`MANIFEST.md`'s row 15 status both need to move from "1/16 failed" to
"16/16 succeeded"** — done as part of this correction.

## Related synthetic documents

No synthetic counterpart — the synthetic corpus doesn't model a size
guide. Also a reasonable candidate for a future `mixed/` document: a
size-chart-style table with soft-hyphen range separators is a genuinely
distinct extraction case (character normalization) from anything
currently in `synthetic/mixed/`.
