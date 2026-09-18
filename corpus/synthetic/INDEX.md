# Synthetic corpus — index

28 documents, all fictional (see the SYNTHETIC banner in each file). This
index exists so a reader — human or the ingestion pipeline's own docs —
can tell **what each document is, why a similar one might also exist, and
what specifically differs between them**, without opening all 28.

Two directories, two different jobs — see
[DECISIONS.md D-011](../../DECISIONS.md) for the full reasoning:

- **`clean/`** (15 docs, `.md`) — the controlled set M2/M3's chunking and
  retrieval experiments run against. Format held constant on purpose, so a
  bad result is attributable to the chunking/retrieval logic, not to PDF
  extraction noise.
- **`mixed/`** (13 docs, `.pdf`/`.docx`/`.txt`) — the format-robustness set.
  Exercises the ingestion parser (T-M1.5) against real extraction failure
  modes: broken tables, scrambled multi-column text, images that degrade to
  disconnected fragments. Not used for the chunking-strategy ablation, so its
  format noise can't contaminate that measurement.

Naming convention, both directories: `{policy-id-slug}-v{version}.{ext}`.

---

## `clean/` — the ablation set

| File | Policy ID | What it is | Why a sibling doc exists / what differs |
|---|---|---|---|
| `returns-policy-v2.0.md` | RET-POL-001 | Returns policy, superseded version | Discounted-item window was **30 days**. Superseded by v3.0 — the pair M8's version-aware retrieval resolves. |
| `returns-policy-v3.0.md` | RET-POL-001 | Returns policy, current version | Narrows the discounted-item window to **14 days**. The version-sensitive golden-set questions target this pair specifically. |
| `loyalty-program-rules-v1.0.md` | LOY-POL-001 | Loyalty program rules, superseded | `GOLD_TIER` threshold **$1,000**. |
| `loyalty-program-rules-v2.0.md` | LOY-POL-001 | Loyalty program rules, current | `GOLD_TIER` threshold raised to **$1,500**. Points-on-returns mechanics (§4) are the other half of the flagship cross-document question, alongside the Returns policy above. |
| `points-expiry-policy.md` | LOY-POL-002 | How unredeemed points expire | Separate from LOY-POL-001 on purpose — tests whether retrieval correctly distinguishes "points expiry" questions from "points accrual/redemption" questions that live in LOY-POL-001, despite heavy vocabulary overlap. |
| `gift-card-terms.md` | GC-POL-001 | Gift card issuance, balance, expiry rules | Distractor pair with Points Expiry — both are "stored value expires" documents; a weak retriever conflates them. |
| `price-match-policy.md` | PM-POL-001 | Price-match eligibility and process | Cross-references Discount Stacking Rules (below) — price-match eligibility depends on whether the lower price itself was a stacked-promo price. |
| `discount-stacking-rules.md` | PROMO-POL-002 | What discounts can combine | Referenced by *three* other documents (Returns §3.2, Warranty exclusions, Price Match) — the identifier `PROMO-POL-002` is the single most cross-referenced token in the corpus, deliberately, as a hub node for multi-hop tracing. |
| `returns-exception-matrix-v2.0.md` | SOP-RET-014 | Store-level exceptions to the Returns Policy | Distinct from RET-POL-001 itself: this is the **internal SOP** applying it, not the customer-facing policy. Tests whether retrieval distinguishes policy-vs-procedure documents that describe the same subject. |
| `failed-refund-runbook.md` | RUN-REF-001 | Step-by-step recovery when a refund fails | References POS-ERR codes (below) — a runbook that's meaningless without the incident vocabulary it assumes the reader already knows. |
| `cash-handling-sop.md` | SOP-CASH-009 | Till counts, deposits, discrepancy reporting | Distractor for Failed Refund Runbook — both are "money didn't move correctly" procedures; different root cause, different fix. |
| `opening-closing-checklist.md` | SOP-OPEN-002 | Daily store open/close procedure | Longest single document in the clean set on purpose — a genuinely long checklist gives fixed-size chunking room to sever a step from its own safety caveat, regardless of `chunk_size`. |
| `shift-policy.md` | STAFF-POL-001 | Scheduling, break, overtime rules | |
| `employee-discount-policy.md` | STAFF-POL-002 | Staff purchase discount terms | Cross-references Markdown Policy (mixed set) — discount stacking during a markdown event is explicitly addressed and is one of the corpus's cross-document dependencies. |
| `leave-policy.md` | STAFF-POL-003 | Leave types, accrual, request process | |

## `mixed/` — the format-robustness set

| File | Format | Policy ID | What it is | Deliberate extraction challenge |
|---|---|---|---|---|
| `warranty-policy-v1.0.pdf` | PDF | WAR-POL-001 | Manufacturer/store warranty coverage | `rowspan` table (category column silently disappears on wrapped rows), 2-column CSS section (scrambles linear read order), embedded SVG diagram (degrades to disconnected text fragments). Cross-refs RET-POL-001. |
| `shipping-policy.docx` | DOCX | SHIP-POL-001 | Delivery windows, carriers, address-change rules | Word-native table with merged cells; tests the DOCX adapter path specifically (different failure modes than PDF extraction). |
| `campaign-brief-bogo.pdf` | PDF | PROMO-POL-001 | BOGO mechanics for a named campaign | Marketing-style layout — pull quotes, a pricing table with footnote asterisks whose actual footnote text sits far down the page, disconnected from the marked term on naive linear extraction. |
| `markdown-policy.docx` | DOCX | PROMO-POL-003 | Rules for markdown/clearance pricing | Referenced by Employee Discount Policy (clean set) and Returns Policy §3.2 (clean set) — a mixed-format document sitting at the center of two clean-set cross-references, testing whether cross-document retrieval works *across* the format boundary, not just within it. |
| `stock-take-sop.pdf` | PDF | SOP-STOCK-005 | Periodic inventory count procedure | Multi-page checklist with a table that spans a page break — a real, common PDF extraction failure (the header row doesn't repeat on page 2). |
| `pos-outage-postmortem.pdf` | PDF | POS-ERR-3021 | Root-cause writeup, a point-of-sale outage | Incident timeline as an image (screenshot-style embedded chart), forcing the same "recognize this isn't extractable prose" handling as Warranty's diagram. |
| `payment-gateway-failure-postmortem.docx` | DOCX | POS-ERR-3045 | Root-cause writeup, a payment gateway failure | Distractor pair with the POS outage postmortem — both are "customers couldn't pay" incidents with different root causes; tests whether retrieval returns the right one for a specific error code. |
| `inventory-sync-failure-postmortem.txt` | TXT | POS-ERR-3102 | Root-cause writeup, an inventory sync failure | **No structure at all** — plain text, no headings, no markup. The hardest case in the corpus: the chunker gets zero formatting signal and has to fall back to pure length-based splitting even in the "structure-aware" path. |
| `loyalty-double-credit-postmortem.pdf` | PDF | POS-ERR-3210 | Root-cause writeup, a loyalty points double-credit bug | Completes the four-postmortem incident set; cross-references LOY-POL-001. |
| `delivery-dispute-runbook.docx` | DOCX | RUN-DEL-002 | Steps for a customer-reported delivery dispute | Distractor pair with Failed Refund Runbook — same "runbook" document type, different trigger and resolution path. |
| `chargeback-handling-runbook.pdf` | PDF | RUN-CHG-003 | Steps for handling a card-issuer chargeback | Embedded flowchart diagram, same extraction challenge as Warranty's, in a different document to confirm the pipeline handles it consistently rather than by accident once. |
| `oms-choice-adr.docx` | DOCX | ADR-001 | Architecture decision record — order management system | ADRs in most real companies live in Confluence/Word, not markdown — format chosen to match that convention specifically. |
| `loyalty-platform-choice-adr.txt` | TXT | ADR-002 | Architecture decision record — loyalty platform | Plain text on purpose, same reasoning as the inventory-sync postmortem — a second no-structure test case in a different document type. |

---

## Cross-document dependency map (for M5's decomposition testing)

**Corrected count.** The original plan tracked 7 dependencies — the ones
deliberately designed in up front. A full scan of every document's own
"Related Policies/Documents" section (grep across all 28 files, including
extracted PDF/DOCX text) found **20+ genuine cross-document pairs** —
most weren't planned, they emerged naturally from writing realistic
policies that reference each other, the same way real corporate documents
do. The 5-minimum from `MANIFEST.md` and the golden set's 10-multi-hop-
question target are both comfortably covered with room to spare.

Representative sample (not exhaustive — see each document's own "Related"
section for the full picture):

| Question needs | Documents |
|---|---|
| Gold member returns a discounted item bought with points | `returns-policy-v3.0.md` + `loyalty-program-rules-v2.0.md` |
| Refund runbook exception lookup | `failed-refund-runbook.md` + `returns-exception-matrix-v2.0.md` |
| Was a POS outage handled per SOP? | `pos-outage-postmortem.pdf` + `opening-closing-checklist.md` |
| Price match during a stacked promo | `price-match-policy.md` + `discount-stacking-rules.md` |
| Employee discount during a markdown event | `employee-discount-policy.md` + `markdown-policy.docx` |
| Chargeback on an order hit by the gateway failure | `chargeback-handling-runbook.pdf` + `payment-gateway-failure-postmortem.docx` |
| Warranty claim denied — return still possible? | `warranty-policy-v1.0.pdf` + `returns-policy-v3.0.md` |
| Employee on extended leave — loyalty account still active? | `leave-policy.md` + `points-expiry-policy.md` |
| International warranty claim — who pays return shipping? | `warranty-policy-v1.0.pdf` + `shipping-policy.docx` |
| Clearance item exchange — does the markdown tag qualify it? | `returns-exception-matrix-v2.0.md` + `markdown-policy.docx` |
| Till discrepancy traced to a refund, not a cash error | `cash-handling-sop.md` + `failed-refund-runbook.md` |
| A 3-way chain: employee discount, stacked with clearance, then returned | `employee-discount-policy.md` + `markdown-policy.docx` + `returns-policy-v3.0.md` |

The warranty↔returns and warranty↔shipping pairs deliberately cross the
clean/mixed format boundary — worth watching in M5 whether decomposition +
retrieval handles a cross-format dependency any differently than an
all-`.md` one. The 3-way chain is worth a specific test case in M4/M5: does
decomposition correctly stop at 3 sub-queries rather than over- or
under-decomposing a genuinely 3-document question.

---

## Status

**All 28 documents written.** Verified by direct token-count audit (not
assumed) against extracted text for every file, using the same tokenizer
(`cl100k_base`) and extraction path (`pdftotext -layout` for PDFs,
`python-docx` for Word) the ingestion pipeline will actually use:

- 28/28 documents, 0 under 400 tokens, average 742 tokens/doc, longest 1,321
  (`opening-closing-checklist.md`, deliberately)
- At a typical 150–200 token `chunk_size`, every document produces at least
  3–5 chunks — resolves the earlier "too small, might be 1–2 chunks" concern
  concretely rather than by assertion

**Chunking-severing audit** — simulated naive fixed-size chunking (150/200/300
token sizes, no structure awareness) against all 15 `clean/` documents and
checked whether each cut lands away from a heading boundary. All 15 have
genuine bad cuts; two (`price-match-policy.md`, `shift-policy.md`) were
initially weak discriminators (most cuts happened to land near a heading by
coincidence of section length) and were lengthened until their bad-cut rate
matched the rest of the set (33%→79% and 67%→100% respectively, re-verified
after editing, not assumed fixed).

15/15 `clean/` and 13/13 `mixed/` (6 PDF, 5 DOCX, 2 TXT) complete.
