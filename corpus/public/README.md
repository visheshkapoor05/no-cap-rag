# Public corpus — fetch log and index

16 real, currently-live retail policy pages, fetched 2026-09-11. Each file
here is a **paraphrased summary plus a short `source_url`-linked note**,
not a verbatim copy of the source page — see
[MANIFEST.md](../MANIFEST.md) for the licence/terms rationale behind that
choice.

This directory is the T-M1.4 deliverable. It complements
[`synthetic/INDEX.md`](../synthetic/INDEX.md), which covers the other 28
documents.

## Fetch outcomes

| # | File | Retailer | Category | Outcome |
|---|---|---|---|---|
| 1 | `target-returns-policy.md` | Target | Returns | direct fetch |
| 2 | `target-returns-exceptions.md` | Target | Returns exceptions | direct fetch |
| 3 | `bestbuy-returns-exchange-policy.md` | Best Buy | Returns | recovered via search (direct fetch geo-redirected) |
| 4 | `ikea-returns-policy.md` | IKEA | Returns | direct fetch |
| 5 | `ikea-delivery-terms.md` | IKEA | Shipping/delivery | direct fetch |
| 6 | `kohls-returns-policy.md` | Kohl's | Returns | recovered via search (direct fetch 403 Forbidden) |
| 7 | `walmart-price-match-policy.md` | Walmart | Price match | recovered via search (direct fetch hit a CAPTCHA) |
| 8 | `nordstrom-loyalty-terms.md` | Nordstrom | Loyalty | direct fetch |
| 9 | `nordstrom-gift-card-info.md` | Nordstrom | Gift cards | direct fetch |
| 10 | `nordstrom-general-terms.md` | Nordstrom | General terms | direct fetch |
| 11 | `nordstrom-promo-terms.md` | Nordstrom | Promotions | direct fetch (page content is a live time-boxed promo, not an evergreen policy — see file's `fetch_note`) |
| 12 | `target-mail-in-returns.md` | Target | Returns (mail-in) | direct fetch |
| 13 | `target-no-receipt-returns.md` | Target | Returns (no receipt) | direct fetch |
| 14 | `bestbuy-warranty-protection.md` | Best Buy | Warranty/protection | recovered via search (direct fetch geo-redirected) |
| 15 | `nordstrom-size-guide.md` | Nordstrom | Size guide | direct fetch — **corrected 2026-09-13**, see note below |
| 16 | `bestbuy-financing-terms.md` | Best Buy | Payment/financing | recovered via search (direct fetch geo-redirected); one data point (minimum purchase threshold) left explicitly unfilled rather than guessed |

**11/16 direct fetches, 5/16 recovered via search snippet of the same
official URL, 0/16 genuine failures.**

**Correction, 2026-09-13:** row 15 was originally logged here as a failure
— "image-based PDF, no extractable text" — based on WebFetch's generic
content-summarizer output during T-M1.4. Once T-M1.5 was built and run
against the same URL with the actual tool the ingestion pipeline uses
(`pdftotext -layout`), it extracted a real, structured size-chart table.
The PDF was never the problem; the generic assessment tool was wrong.
Left visible here rather than quietly fixed, because it's a concrete
instance of a principle this project keeps leaning on: a claim about a
document's extractability is only as good as the tool that produced it,
and the real ingestion adapter is more authoritative than a one-off
summarization pass. See `nordstrom-size-guide.md`'s `fetch_note`.

## Why this outcome mix is being kept rather than "fixed" to look cleaner

This is real evidence for the argument made for doing T-M1.4 at all (see
[BLUEPRINT.md](../../BLUEPRINT.md) M1 reasoning): bot detection, geo/country
interstitials, CAPTCHAs, and image-only PDFs are exactly the kind of
unpredictable failure mode a synthetic-only corpus can never produce,
because I control every property of a synthetic document. Three concrete,
specific ingestion-pipeline requirements fall directly out of this
fetch log, to carry into **T-M1.5**:

1. **A "fetched but blocked/interstitial" outcome is distinct from both
   "fetch succeeded" and "fetch failed with an HTTP error."** Three of the
   five search-recovered pages (all three Best Buy URLs) returned HTTP 200
   with a country-selector page instead of an error — a naive
   `status_code == 200 → success` check would have silently ingested junk.
2. **A "200 OK, zero extractable text" outcome is distinct from a network
   or HTTP failure, and needs its own status** (`NO_TEXT_EXTRACTED` in
   T-M1.5's `Source` interface) so it can be logged differently — e.g.
   flagged for OCR triage — instead of being treated the same as a dead
   link. The Nordstrom size-guide PDF was the original motivating example
   for this requirement, but per the correction above it turned out *not*
   to actually hit this case once the real `pdftotext` adapter ran against
   it — the status still exists and is covered by T-M1.5's tests (a
   simulated unreadable-PDF case), just not by this particular document
   after all.
3. **Search-engine-recovered content should carry different provenance
   metadata than a direct fetch** (`fetch_method: search_recovered` +
   `fetch_note` in every affected file here) — it's still attributed to
   the real official URL, but a downstream consumer should be able to tell
   the two fetch paths apart rather than treating them as identical
   evidence quality.

## What happened when T-M1.9's real CLI actually re-fetched all 16 URLs

**Corrected 2026-09-15.** The provenance recorded above (`fetch_method:
direct_fetch` on 11 files, dated 2026-09-11) describes how each corpus/
public/*.md summary was originally *authored* — via `WebFetch`, a tool
that does more than a plain HTTP client (likely real browser rendering
and/or bot-mitigation handling under the hood). Once T-M1.9's actual
ingestion pipeline (`URLSource`, plain `httpx`, no JS execution) ran
against the same 16 URLs for real, the result was **8/16 succeeded, 8/16
failed** — a new, fourth failure mode surfaced, and one already-documented
failure came out the other way:

- **All 4 Nordstrom URLs newly failed** with `NO_TEXT_EXTRACTED`. Not an
  extraction bug — the raw response is a bot-detection JS challenge page
  (obfuscated challenge script, empty `<title>`, zero real content in the
  HTML), confirmed by fetching it directly and reading the raw bytes. This
  is categorically different from Best Buy's geo-redirect or Walmart's
  CAPTCHA: those still return an interstitial *page* our HTML extractor
  can read (and therefore classify as `BLOCKED`); Nordstrom's challenge
  returns something a plain HTTP client can never pass, JS execution or
  not, without a real browser engine — reproducing what `WebFetch`
  apparently already had access to.
- **Walmart's price-match page succeeded this run**, despite being
  CAPTCHA-blocked in the original T-M1.4 manual check. Live sites aren't
  fully deterministic between runs — a real operational fact, not a bug in
  either result.
- Best Buy (×3, geo-redirect) and Kohl's (×1, 403) reproduced exactly as
  documented in T-M1.4.

**Why this isn't "fixed" by improving `URLSource`:** getting past a
JS-based bot challenge requires a real browser engine (e.g. Playwright),
which is a materially bigger piece of infrastructure than this ingestion
pipeline is scoped for, and edges into bot-evasion territory worth being
deliberate about rather than reaching for by default. The corpus/public/
summary files for the 4 Nordstrom documents remain valid — they were
fetched once, legitimately, by a tool that could get through — but
`URLSource` re-fetching them live (e.g. for M8's freshness recrawl) will
reliably fail until/unless a browser-based adapter is deliberately added.
Logged here as a known, real limitation instead of silently working around
it or leaving it undocumented.

## Related synthetic documents

Each file above has its own "Related synthetic documents" section calling
out the nearest fictional counterpart and what specifically differs —
several are deliberate contrasts (e.g. Nordstrom gift cards never expire
in reality, but the synthetic corpus models expiry on purpose as a
distractor) rather than coincidental overlaps.
