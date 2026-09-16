---
id: doc-loyalty-program-rules
policy_id: LOY-POL-001
title: Loyalty Program Rules
version: "2.0"
effective_date: 2026-05-15
supersedes: doc-loyalty-program-rules-v1.0
document_type: loyalty
is_synthetic: true
---

> **SYNTHETIC — illustrative, not from any real company.** This document was
> written for a portfolio RAG project and does not describe any real
> retailer's actual loyalty program.

# Loyalty Program Rules

**Policy ID:** LOY-POL-001 · **Version:** 2.0 · **Effective:** May 15, 2026
**Supersedes:** Loyalty Program Rules v1.0 (effective through May 14, 2026)

## 1. Tier Structure

| Tier | Annual spend threshold | Points per $1 |
|---|---|---|
| `SILVER_TIER` | $0 | 1 |
| `GOLD_TIER` | $1,500 | 1.5 |
| `PLATINUM_TIER` | $5,000 | 2 |

The `GOLD_TIER` threshold rises to $1,500 under this version, up from $1,000
under v1.0. The points-per-dollar rate for `GOLD_TIER` is unchanged.

## 2. Points Accrual

Points accrue on the pre-tax purchase amount actually paid in cash or by
card. Points do **not** accrue on the portion of a purchase paid for using
previously-earned points — points cannot earn further points.

## 3. Points Redemption

100 points redeem for $1 of purchase value, applicable at checkout in any
combination with a standard payment method, up to 100% of the order total.

## 4. Points Handling on Returns

This section governs what Returns Policy RET-POL-001 Section 3.3 refers to.

When an item purchased partly or fully with loyalty points is returned:

1. The **points portion** of the original purchase is refunded as points,
   credited back to the customer's account within 24 hours of the return
   being processed.
2. The **cash/card portion**, if any, is refunded to the original payment
   method per RET-POL-001 Section 4.
3. If the item was purchased at a promotional discount (see RET-POL-001
   Section 3.2) using a blend of points and card, the discount is applied
   proportionally across both portions before the split in steps 1–2 is
   calculated — the points refund is not calculated on the pre-discount
   value.
4. Points refunded under this section do **not** count toward the current
   year's tier-qualifying spend, since no new spend occurred.

**Worked example:** a `GOLD_TIER` member buys a $100 item at a 25% clearance
discount ($75 charged), paying $50 by card and 2,500 points ($25 value). On
return: 2,500 points are credited back; $50 is refunded to the card; the
return does not affect tier status since no new spend occurred to reverse.

## 5. Points Expiry

Points expire 18 months after the calendar month in which they were earned,
tracked on a rolling basis. Points redeemed count against the oldest
non-expired points first ("first in, first out").

## 6. Related Policies

- **RET-POL-001** — Returns Policy (return windows; Section 3.3 defers to
  this document for points-refund mechanics)
- **PROMO-POL-002** — Discount Stacking Rules (defines promotional discounts
  referenced in Section 4, step 3)
