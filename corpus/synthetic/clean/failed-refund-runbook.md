---
id: doc-failed-refund-runbook
policy_id: RUN-REF-001
title: Failed Refund Runbook
version: "1.0"
effective_date: 2026-03-01
document_type: runbook
is_synthetic: true
---

> **SYNTHETIC — illustrative, not from any real company.** This document was
> written for a portfolio RAG project and does not describe any real
> retailer's actual internal procedure.

# Failed Refund Runbook

**Runbook ID:** RUN-REF-001 · **Effective:** March 1, 2026

Use this runbook when a refund has been approved (per RET-POL-001 or
SOP-RET-014) but fails to actually process — the customer sees no credit
after the stated processing time. This runbook assumes the *decision* to
refund was already correct; it is purely about recovering a stuck
transaction.

## 1. Confirm the Refund Was Actually Approved

Before troubleshooting, confirm in the POS system that a refund was
genuinely initiated and not just verbally promised. Check the transaction
log for a refund record with a status other than "completed." If no refund
record exists at all, this is not a failed refund — return to RET-POL-001
or SOP-RET-014 and process it properly first.

## 2. Identify the Failure Mode

| Symptom | Likely cause | Next step |
|---|---|---|
| Refund record shows "pending" over 48 hours | Payment gateway timeout | Go to Section 3 |
| Refund record shows "failed" with an error code | Card issuer rejection | Go to Section 4 |
| No refund record, but register shows cash removed | Till discrepancy, not a refund failure | Escalate to Cash Handling SOP (SOP-CASH-009) |
| Refund shows "completed" but customer disputes receiving it | Refund succeeded; likely a statement-cycle timing issue | Go to Section 5 |

## 3. Payment Gateway Timeout

Check whether this coincides with a known gateway incident (see the
Payment Gateway Failure Postmortem in `corpus/synthetic/mixed/` if error
code **POS-ERR-3045** appears in the transaction log). If the incident is
active, do not retry the refund — retrying during an active gateway
incident risks a duplicate refund once the gateway recovers. Log the
transaction ID and wait for the incident to clear, then retry once.

If no incident is active and the refund has been pending over 48 hours
with no associated error code, escalate to a shift lead — this is an
unusual case that this runbook does not have a clean answer for, and
guessing at a retry risks a duplicate refund with no incident to explain
it afterward.

## 4. Card Issuer Rejection

A rejection error code (visible in the POS transaction log) usually means
the original card has since been closed or reissued. In this case: do not
retry the same refund. Instead, offer the customer store credit for the
refund amount, and log the original card rejection code for the accounting
team to reconcile separately — the accounting reconciliation process for a
rejected-card refund is handled outside this runbook's scope.

## 5. Statement-Cycle Timing Disputes

If the refund record genuinely shows "completed" but the customer disputes
receiving it, this is very often a statement-cycle timing issue rather
than a real failure — card issuers can take 3–5 business days beyond the
refund date to post it to a statement. Confirm the refund completion
timestamp with the customer and advise them of the issuer-side posting
delay. Do not initiate a second refund in this case; a second refund
against a genuinely completed first one is the single most common cause of
duplicate-refund write-offs.

## 6. When to Escalate Beyond This Runbook

Escalate to a shift lead immediately, without attempting Sections 3–5
first, if: the refund amount exceeds $500, the same customer has had two
or more failed refunds in the past 30 days, or the failure mode doesn't
match any row in the Section 2 table.

## 7. Related Documents

- **RET-POL-001** — Returns Policy / **SOP-RET-014** — Returns Exception
  Matrix (the refund decision this runbook assumes was already correct)
- **SOP-CASH-009** — Cash Handling SOP (till discrepancy escalation path)
