---
id: doc-cash-handling-sop
policy_id: SOP-CASH-009
title: Cash Handling SOP
version: "1.0"
effective_date: 2026-01-10
document_type: store_sop
is_synthetic: true
---

> **SYNTHETIC — illustrative, not from any real company.** This document was
> written for a portfolio RAG project and does not describe any real
> retailer's actual internal procedure.

# Cash Handling SOP

**SOP ID:** SOP-CASH-009 · **Effective:** January 10, 2026

## 1. Till Assignment

Each register till is assigned to a single associate per shift and counted
in and out under that associate's ID. Tills are never shared mid-shift; if
an associate needs to step away, the till is closed and recounted before a
second associate opens it, even for a short absence.

## 2. Opening Count

At shift start, count the till against the fixed $200 starting float. Any
discrepancy over $2 at opening is logged immediately and reported to the
shift lead before the register is opened for transactions — an opening
discrepancy almost always traces back to the prior shift's closing count,
and is far easier to resolve before a new shift's transactions are mixed
in.

## 3. Mid-Shift Drops

When till cash exceeds $300 above the starting float, perform a cash drop:
remove the excess down to $300 over float, seal it in a drop bag with the
till ID and timestamp written on the bag, and deposit it in the safe.
Drops are performed by the till's assigned associate alone; a second
associate may witness but does not handle the cash, to keep accountability
unambiguous per till.

## 4. Refund and Return Cash Handling

Cash refunds under $75 are paid from the till directly, per RET-POL-001's
refund method rules. Refunds are logged against the till the same as a
sale, as a negative transaction, so the till's expected closing balance
already accounts for it — an associate should never need to manually
subtract refund cash from their own closing count.

## 5. Closing Count and Discrepancy Reporting

At shift end, count the till twice, independently, before comparing
against the POS-expected balance. A discrepancy under $5 is logged but
does not require same-day escalation. A discrepancy of $5–$25 requires
same-shift shift-lead review. A discrepancy over $25 requires the shift
lead to review the register's full transaction log against the physical
count line by line before the associate leaves for the day — not the next
shift, since transaction-log review becomes substantially harder to
reconstruct accurately after 24 hours.

## 6. When a Discrepancy Traces to a Refund

If a closing discrepancy traces to a specific refund transaction that
appears in the log but doesn't match the physical cash removed, this is
not a cash-handling failure in the sense this SOP otherwise covers — refer
to the Failed Refund Runbook (RUN-REF-001), Section 2, "No refund record,
but register shows cash removed," which is the specific failure mode this
situation matches.

## 7. Safe Access and Dual Control

The store safe requires two-person access at all times — no single
associate, including shift leads, opens the safe alone under any
circumstance. This applies to both cash drops (Section 3) and end-of-day
deposit preparation.

## 8. Related Documents

- **RET-POL-001** — Returns Policy (refund method rules referenced in
  Section 4)
- **RUN-REF-001** — Failed Refund Runbook (Section 6 above)
- **SOP-OPEN-002** — Opening/Closing Checklist (till counts are one line
  item within the broader daily open/close procedure)
