# Corpus Manifest

Every source in this corpus, why it's here, and its licence/redistribution
status. Two halves, deliberately kept separate and separately labelled — see
[DECISIONS.md D-002](../DECISIONS.md).

- **Half A — public retail sources.** Real, currently-live policy pages.
  Verified via live search on 2026-09-06, not guessed — URLs get re-verified
  at fetch time (T-M1.4) since retailers restructure these pages often.
- **Half B — synthetic enterprise documents.** Fictional, clearly banner-labelled
  `SYNTHETIC — illustrative, not from any real company` in-document and
  `is_synthetic: true` in metadata. See the inventory below.

---

## Half A — Public sources (target: 15–25 documents)

**Licence/terms status, all rows:** these are publicly viewable retailer policy
pages. Nothing here is licensed for redistribution — this project stores
**short excerpts and paraphrased summaries for retrieval-evaluation purposes
only**, not full verbatim republication of any retailer's page. Each fetched
record keeps its `source_url` so provenance and the original are always one
click away. If full-text ingestion of a given page turns out to be needed,
that page's terms of use get checked individually before ingestion — this is
a per-source decision, not a blanket one.

| # | Category | Retailer | URL | Status |
|---|---|---|---|---|
| 1 | Returns | Target | https://www.target.com/help/articles/policies-guidelines/return-policy | fetched 2026-09-11 → [`target-returns-policy.md`](./public/target-returns-policy.md) |
| 2 | Returns exceptions | Target | https://www.target.com/help/article/000061982 | fetched 2026-09-11 → [`target-returns-exceptions.md`](./public/target-returns-exceptions.md) |
| 3 | Returns | Best Buy | https://www.bestbuy.com/site/help-topics/return-exchange-policy/pcmcat260800050014.c?id=pcmcat260800050014 | fetched 2026-09-11 (search-recovered — direct fetch geo-redirected) → [`bestbuy-returns-exchange-policy.md`](./public/bestbuy-returns-exchange-policy.md) |
| 4 | Returns | IKEA | https://www.ikea.com/us/en/customer-service/returns-claims/return-policy/ | fetched 2026-09-11 → [`ikea-returns-policy.md`](./public/ikea-returns-policy.md) |
| 5 | Shipping/delivery | IKEA | https://www.ikea.com/us/en/customer-service/terms-conditions/delivery-terms-and-conditions-pub7aa7b291/ | fetched 2026-09-11 → [`ikea-delivery-terms.md`](./public/ikea-delivery-terms.md) |
| 6 | Returns | Kohl's | https://www.kohls.com/faq/article/893 | fetched 2026-09-11 (search-recovered — direct fetch returned 403) → [`kohls-returns-policy.md`](./public/kohls-returns-policy.md) |
| 7 | Price match | Walmart | https://www.walmart.com/help/article/walmart-price-match-policy/6295d9e1a501489b9aa40a60c899b288 | fetched 2026-09-11 (search-recovered — direct fetch hit a CAPTCHA) → [`walmart-price-match-policy.md`](./public/walmart-price-match-policy.md) |
| 8 | Loyalty program terms | Nordstrom (Nordy Club) | https://www.nordstrom.com/browse/nordy-club/terms-conditions | fetched 2026-09-11 → [`nordstrom-loyalty-terms.md`](./public/nordstrom-loyalty-terms.md) |
| 9 | Gift cards | Nordstrom | https://www.nordstrom.com/browse/customer-service/gift-card-info | fetched 2026-09-11 → [`nordstrom-gift-card-info.md`](./public/nordstrom-gift-card-info.md) |
| 10 | General terms | Nordstrom | https://www.nordstrom.com/browse/customer-service/policy/terms-conditions | fetched 2026-09-11 → [`nordstrom-general-terms.md`](./public/nordstrom-general-terms.md) |
| 11 | Promotion terms | Nordstrom | https://www.nordstrom.com/browse/customer-service/policy/promo-terms-conditions | fetched 2026-09-11 (live time-boxed promo content, not evergreen — see file) → [`nordstrom-promo-terms.md`](./public/nordstrom-promo-terms.md) |
| 12 | Returns (mail-in) | Target | https://www.target.com/help/article/000062920 | fetched 2026-09-11 → [`target-mail-in-returns.md`](./public/target-mail-in-returns.md) |
| 13 | Returns (no receipt) | Target | https://www.target.com/help/article/000062164 | fetched 2026-09-11 → [`target-no-receipt-returns.md`](./public/target-no-receipt-returns.md) |
| 14 | Warranty / protection plan | Best Buy | https://www.bestbuy.com/site/best-buy-membership/best-buy-protection/pcmcat1608643232014.c?id=pcmcat1608643232014 | fetched 2026-09-11 (search-recovered — direct fetch geo-redirected) → [`bestbuy-warranty-protection.md`](./public/bestbuy-warranty-protection.md) |
| 15 | Size guide (PDF) | Nordstrom | https://www.nordstrom.com/sizeguides/2188_sizeguide.pdf | fetched 2026-09-11, **corrected 2026-09-13** — initially misjudged as an image-only PDF by a generic summarizer; T-M1.5's actual `pdftotext -layout` adapter extracts a real size-chart table → [`nordstrom-size-guide.md`](./public/nordstrom-size-guide.md) |
| 16 | Payment / financing terms | Best Buy | https://www.bestbuy.com/site/financing-rewards/storewide-financing-details/pcmcat1592857565498.c?id=pcmcat1592857565498 | fetched 2026-09-11 (search-recovered — direct fetch geo-redirected) → [`bestbuy-financing-terms.md`](./public/bestbuy-financing-terms.md) |

**16 of 15–25 target reached — all 8 planned categories now covered**
(returns, shipping, price match, loyalty, gift cards, promotions, warranty,
size guide, payment/financing — one more than the original 8 since returns
alone has 4 URLs). **T-M1.4 fetch complete: 16/16 succeeded (11 direct, 5
recovered via search snippet after the direct fetch was blocked).** One of
the 11 direct fetches (row 15) was originally misjudged as a failure by a
generic summarizer and corrected once T-M1.5's real `pdftotext`-based
adapter ran against it — see that file's `fetch_note`. Full fetch log,
per-document provenance, and the reasoning behind keeping the
search-recovered flags visible rather than smoothing them over:
[`public/README.md`](./public/README.md).

---

## Half B — Synthetic inventory — **done, 28 documents**

All fictional. Every file carries the SYNTHETIC banner + `is_synthetic: true`
— non-negotiable, see [D-002](../DECISIONS.md). Full per-document breakdown,
cross-reference map, and the reasoning behind each one lives in
[`synthetic/INDEX.md`](./synthetic/INDEX.md) — this section is the summary.

Split across two directories with different jobs (see
[D-011](../DECISIONS.md#d-011--synthetic-corpus-split-clean-md-vs-mixed-pdfdocxtxt)):

| Directory | Format | Count | Purpose |
|---|---|---|---|
| `synthetic/clean/` | `.md` | 15 | Controlled set — M2/M3's chunking and retrieval ablations run against this only, so a bad result is attributable to logic, not format noise |
| `synthetic/mixed/` | 6 `.pdf`, 5 `.docx`, 2 `.txt` | 13 | Format-robustness set — exercises the ingestion parser against real extraction failure modes (broken tables, scrambled columns, images that degrade to fragments, zero-structure plain text) |

| Category | Documents | Count |
|---|---|---|
| Customer policy | Returns Policy **v2.0 & v3.0**, Warranty Policy, Shipping Policy, Gift Card Terms, Price Match Policy | 6 |
| Loyalty | Loyalty Program Rules **v1.0 & v2.0**, Points Expiry Policy | 3 |
| Promotions | Discount Stacking Rules, Markdown Policy, Campaign Brief (BOGO) | 3 |
| Store SOPs | Opening/Closing Checklist, Cash Handling SOP, Stock Take SOP, Returns Exception Matrix v2.0 | 4 |
| Incidents | POS Outage, Payment Gateway Failure, Inventory Sync Failure, Loyalty Double-Credit (all postmortems) | 4 |
| Runbooks | Failed Refund, Delivery Dispute, Chargeback Handling | 3 |
| ADRs | Order Management System Choice, Loyalty Platform Choice | 2 |
| Staff | Shift Policy, Employee Discount Policy, Leave Policy | 3 |
| **Total** | | **28** |

28 falls inside the 25–35 target (the earlier "27" undercounted — it listed
the Returns/Loyalty version pairs as one named policy each rather than two
files). Every document verified at ≥400 tokens by direct extraction (not
assumed) — see the audit summary in `synthetic/INDEX.md`'s Status section.
Room to add 2–7 more later (e.g. a third SOP revision, an additional
incident) if M2's chunking work or M4's evidence
analysis exposes a gap — adding here is cheap; adding after chunking/indexing
means re-running the pipeline.

### Version pairs (target: ≥3 — planning 3)

| # | Family | Older version | Newer version | What changes |
|---|---|---|---|---|
| 1 | Returns Policy | v2.0 | v3.0 | Return window for discounted items narrows from 30 to 14 days |
| 2 | Loyalty Program Rules | v1.0 | v2.0 | Gold tier spend threshold rises; points-per-dollar rate changes |
| 3 | Returns Exception Matrix | v1.0 (implicit in SOP) | v2.0 | New exception added for clearance-tagged items, referencing the Returns Policy v3.0 change above |

Pair #3 deliberately links back to pair #1 — a document revision *caused by*
another document's revision is more realistic than three independent,
unrelated version bumps, and gives M8 a chain to actually resolve rather than
three isolated cases.

### Cross-document dependencies (target: ≥5 — actual: 20+)

Planned 6 at this stage; the actual written corpus has **20+ genuine
cross-document pairs**, found by scanning every document's own "Related
Policies/Documents" section rather than only counting what was originally
designed in. Full list, plus a deliberate 3-document chain, in
[`synthetic/INDEX.md`](./synthetic/INDEX.md#cross-document-dependency-map-for-m5s-decomposition-testing).
The buffer built in at planning time (6 vs. the 5 minimum) turned out
unnecessary — real cross-referencing while writing realistic policies
produced far more than planned, the same way it would in an actual
corporate document set.

---

## Exit check (T-M1.2)

- [x] Public URLs listed (16, all 8 categories covered — fetched under T-M1.4)
- [x] Synthetic inventory planned by category (28 documents)
- [x] ≥3 version pairs planned explicitly, with the mechanism of change stated
- [x] ≥5 cross-document dependencies planned explicitly, with the documents named
