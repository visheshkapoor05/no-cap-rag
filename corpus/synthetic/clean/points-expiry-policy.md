---
id: doc-points-expiry-policy
policy_id: LOY-POL-002
title: Points Expiry Policy
version: "1.0"
effective_date: 2026-01-01
document_type: loyalty
is_synthetic: true
---

> **SYNTHETIC — illustrative, not from any real company.** This document was
> written for a portfolio RAG project and does not describe any real
> retailer's actual loyalty program.

# Points Expiry Policy

**Policy ID:** LOY-POL-002 · **Version:** 1.0 · **Effective:** January 1, 2026

This document is the detailed reference for point expiry mechanics. LOY-POL-001
(Loyalty Program Rules) states the headline rule — points expire 18 months
after the calendar month earned — in its own Section 5. This document covers
the edge cases that headline rule doesn't address.

## 1. Standard Expiry

Points expire on a rolling basis, 18 months after the end of the calendar
month in which they were earned. Points earned in March 2026, for example,
expire at the end of September 2027. Expiry runs as a monthly batch job on
the first of each month against the previous month's aged-out cohort.

## 2. First-In, First-Out Redemption

When a member redeems points, the oldest non-expired points are drawn down
first. This matters because it means a member who redeems regularly rarely
experiences expiry at all — expiry primarily affects accounts that accrue
points but redeem rarely or never.

## 3. Account Inactivity

If an account has no purchase or redemption activity for 24 consecutive
months, all points on the account expire immediately regardless of when
individually earned, and the account itself is flagged inactive. Inactive
accounts retain tier history but accrue no further points until a
qualifying purchase reactivates the account.

## 4. Store Closures and System Outages

If a store closure or system outage (see the incident postmortems in
`corpus/synthetic/mixed/`) prevents a member from redeeming points before
their scheduled expiry date, and the member contacts support within 30 days
of the outage, the affected points are reinstated with a new 90-day expiry
window rather than the standard 18 months. This exception exists
specifically because points expiry is an automated batch process that has
no awareness of whether a member was actually able to act on their
balance.

## 5. Account Transfers and Closures

Points do not transfer between accounts under any circumstance, including
between household members, gift transfers, or account consolidation
requests. On account closure — whether voluntary or due to fraud
investigation — all unredeemed points are forfeited immediately and are not
eligible for reinstatement even if the account is later reopened.

## 6. Corporate and Bulk Accounts

Corporate loyalty accounts (registered under a business tax ID rather than
an individual) follow a separate 12-month flat expiry with no rolling
window and no first-in-first-out mechanic — all points earned in a
calendar year expire on December 31 of the following year as a single
batch, not incrementally by earn-month. This is a deliberate simplification
for high-volume corporate accounts where per-month tracking creates
disproportionate reconciliation overhead relative to the accounts' size.

## 7. Related Policies

- **LOY-POL-001** — Loyalty Program Rules (headline expiry rule, accrual,
  redemption)
- **RET-POL-001** — Returns Policy (points handling on returns, which does
  not affect expiry timing)
