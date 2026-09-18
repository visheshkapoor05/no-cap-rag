---
id: doc-discount-stacking-rules
policy_id: PROMO-POL-002
title: Discount Stacking Rules
version: "1.0"
effective_date: 2026-02-01
document_type: promotions
is_synthetic: true
---

> **SYNTHETIC — illustrative, not from any real company.** This document was
> written for a portfolio RAG project and does not describe any real
> retailer's actual pricing rules.

# Discount Stacking Rules

**Policy ID:** PROMO-POL-002 · **Version:** 1.0 · **Effective:** February 1, 2026

This is the most cross-referenced document in the corpus — it defines what
counts as a "promotional discount," a term used by RET-POL-001 (Returns
Policy), the Warranty Policy exclusions, and PM-POL-001 (Price Match
Policy) without each of those documents re-deriving the definition
themselves.

## 1. What Counts as a Promotional Discount

A promotional discount is any price reduction applied through a coupon
code, a site-wide sale event, a loyalty-tier exclusive offer, or a
clearance/markdown tag (see PROMO-POL-003, Markdown Policy). A price
reduction from a price-match adjustment (PM-POL-001) is explicitly **not**
a promotional discount under this definition — it restores parity with a
competitor's price rather than creating a new discount, which matters
because RET-POL-001 Section 3.2's 14-day window applies to promotional
discounts of 20% or more, and a price-matched item should not trigger that
shortened window merely because the matched price happened to be 20% lower
than the original tag.

## 2. Stacking Order

Where multiple discounts apply to the same item, they are applied in this
fixed order: (1) any loyalty-tier exclusive percentage, (2) any site-wide
sale percentage, (3) any coupon code, applied to the post-discount price
from steps 1–2, not the original price. Discounts do not compound
multiplicatively beyond this three-step order — a second coupon code
cannot be applied on top of a first.

## 3. Maximum Combined Discount

The combined effect of stacked discounts is capped at 50% off the original
tagged price, regardless of how the individual percentages in Section 2
would otherwise sum. If the stacking order in Section 2 would produce a
combined discount exceeding 50%, the final discount is capped at 50% and
the difference is not carried forward or refunded in any other form.

## 4. Exclusions from Stacking

Clearance-tagged items (per the Markdown Policy) can accept a loyalty-tier
percentage but cannot accept a coupon code — clearance pricing is already
below the threshold where further coupon stacking is profitable at the
unit level. This exclusion is enforced at checkout automatically; if a
coupon code is entered against a clearance item, the coupon is silently
ignored for that line item rather than rejecting the whole order, since
rejecting the order for one ineligible line item creates worse customer
experience than partial application.

## 5. Determining "20% or More" for Returns Purposes

RET-POL-001 Section 3.2 references "a discount of 20% or more" without
specifying whether that means the individual discount or the combined
stacked discount. Per this policy: it means the **combined** discount
actually paid, calculated per Section 2 above, inclusive of the Section 3
cap. An item where a 15% loyalty discount and a 10% coupon stacked to a
combined 23.5% discount (before the cap) falls under the shortened return
window; an item with only a 15% loyalty discount alone does not.

## 6. Related Policies

- **RET-POL-001** — Returns Policy (Section 3.2 depends on this document's
  Section 5 for its own threshold definition)
- **PROMO-POL-003** — Markdown Policy (clearance tagging referenced in
  Sections 1 and 4)
- **PM-POL-001** — Price Match Policy (the explicit non-discount exclusion
  in Section 1)
