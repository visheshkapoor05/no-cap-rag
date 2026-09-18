---
id: doc-loyalty-program-rules-v1.0
policy_id: LOY-POL-001
title: Loyalty Program Rules
version: "1.0"
effective_date: 2025-01-15
superseded_by: doc-loyalty-program-rules
document_type: loyalty
is_synthetic: true
---

> **SYNTHETIC — illustrative, not from any real company.** This document was
> written for a portfolio RAG project and does not describe any real
> retailer's actual loyalty program.

# Loyalty Program Rules

**Policy ID:** LOY-POL-001 · **Version:** 1.0 · **Effective:** January 15, 2025
**Superseded by:** Loyalty Program Rules v2.0, effective May 15, 2026

## 1. Tier Structure

| Tier | Annual spend threshold | Points per $1 |
|---|---|---|
| `SILVER_TIER` | $0 | 1 |
| `GOLD_TIER` | $1,000 | 1.5 |
| `PLATINUM_TIER` | $5,000 | 2 |

Tier status is evaluated on a rolling 12-month basis and recalculated on the
first of each month. A member who crosses a threshold mid-month is promoted
immediately; demotion for falling below a threshold takes effect at the
next quarterly review, not immediately, to avoid tier "flapping" from a
single large return.

## 2. Points Accrual

Points accrue on the pre-tax purchase amount actually paid in cash or by
card, at the per-dollar rate for the member's tier at time of purchase, not
at time of accrual posting (accrual can take up to 72 hours to appear).
Points do not accrue on the portion of a purchase paid for using
previously-earned points.

Employees enrolled in the loyalty program accrue points at the `SILVER_TIER`
rate regardless of their actual tier, on personal purchases only —
purchases made using the employee discount under STAFF-POL-002 do not
accrue points at all, since the discounted price does not reflect standard
program economics.

## 3. Points Redemption

100 points redeem for $1 of purchase value, applicable at checkout in any
combination with a standard payment method, up to 100% of the order total.
Redemption is blocked, not just discouraged, on final-sale items, to avoid
a points-refund liability on merchandise that cannot itself be returned.

## 4. Points Handling on Returns

When an item purchased partly or fully with loyalty points is returned, the
points portion of the original purchase is refunded as points, credited
back to the customer's account within 5 business days of the return being
processed. The cash or card portion, if any, is refunded to the original
payment method per RET-POL-001.

Points refunded under this section do not count toward the current year's
tier-qualifying spend, since no new spend occurred.

## 5. Points Expiry

Points expire 12 months after the calendar month in which they were earned.
Redemption draws down the oldest non-expired points first.

## 6. Related Policies

- **RET-POL-001** — Returns Policy (return windows; refund mechanics for
  the non-points portion of a purchase)
- **STAFF-POL-002** — Employee Discount Policy (accrual exception for
  employee purchases, Section 2)
