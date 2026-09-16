---
id: doc-opening-closing-checklist
policy_id: SOP-OPEN-002
title: Opening/Closing Checklist
version: "1.0"
effective_date: 2026-01-10
document_type: store_sop
is_synthetic: true
---

> **SYNTHETIC — illustrative, not from any real company.** This document was
> written for a portfolio RAG project and does not describe any real
> retailer's actual internal procedure.

# Opening/Closing Checklist

**SOP ID:** SOP-OPEN-002 · **Effective:** January 10, 2026

The longest procedure document in this corpus, deliberately — a genuinely
long checklist gives fixed-size chunking a real chance to sever a step from
its own safety caveat, regardless of which chunk size is chosen, in a way a
short document can't.

## 1. Pre-Opening (before doors unlock)

1.1. Disarm the security system using the shift lead's individual code, not
a shared code — shared codes were retired following a 2025 incident where a
terminated employee's still-active shared code was used after hours.

1.2. Walk the sales floor for overnight damage, spills, or signage left
from the prior close. Log anything found in the daily incident log, even
minor items — the log's value is in the pattern across many days, not any
single entry.

1.3. Power on all registers and confirm each connects to the POS network
before assigning tills (see SOP-CASH-009 for till assignment and opening
count procedure).

1.4. Confirm the price-check scanner and the loyalty-signup tablet are both
online. If either is offline, log a ticket immediately rather than waiting
until a customer needs it — IT response time during business hours is
substantially slower than during the pre-opening window.

1.5. Unlock the fitting rooms and confirm the call-button system responds
at each station.

1.6. Confirm the store's posted hours sign matches the current week's
actual hours — holiday-week hours changes have historically been updated
in the POS system but not on the physical door sign, causing a mismatch
customers notice before staff do.

1.7. Brief the opening team on any promotions active that day (see the
Campaign Brief documents in `corpus/synthetic/mixed/` for specifics), any
items on the daily incident watch list from Section 1.2, and any pending
price-match or return-exception cases carried over from the prior day.

## 2. During Business Hours

2.1. Perform a sales-floor walk every two hours, checking for the same
damage/spill/signage issues as the pre-opening walk, plus stock levels on
posted-promotion items specifically — promotion items sell down faster and
an empty promotional endcap left unrestocked reads as a signage error to
customers, not a stock error.

2.2. Log any register error codes immediately in the incident log, cross-
referencing the error code against known incidents (POS-ERR-3021,
POS-ERR-3045, POS-ERR-3102, POS-ERR-3210 — the four incident postmortems
in `corpus/synthetic/mixed/`) if the code matches one of those.

2.3. Confirm fitting room call-buttons are still responsive at the midday
walk — button failures are disproportionately reported by customers rather
than caught by staff walks, so a proactive midday check catches most
failures before a customer does.

## 3. Pre-Closing (last 30 minutes before doors lock)

3.1. Announce closing per standard store announcement script at the
scheduled time, then again 15 minutes and 5 minutes before lock.

3.2. Begin directing remaining customers toward checkout; do not
physically block the entrance or aggressively hurry customers still
browsing — customer complaints about aggressive closing procedures are
tracked separately and reviewed monthly.

3.3. Close and lock the fitting rooms once the last customer has exited
them, confirming no items were left behind.

3.4. Begin the till closing count per SOP-CASH-009 Section 5 for any
register not actively serving a customer, staggering register closures so
at least one register remains open until the doors physically lock.

## 4. Post-Closing (after doors lock)

4.1. Complete till closing counts for all remaining registers per
SOP-CASH-009 Section 5.

4.2. Perform a full sales-floor walk, checking every fitting room, restroom,
and stockroom entrance for a customer who may have been missed during the
closing announcement sequence in Section 3. This walk is not optional even
on nights when the store appeared empty at lock time — the incident that
prompted this SOP's most recent revision was a customer found asleep in a
fitting room during a night when staff reported the store as empty at
closing.

4.3. Reconcile the day's total till counts against the POS-expected total.
Any store-wide discrepancy over $50 across combined tills requires the
closing shift lead to complete a written incident report before leaving,
not the next morning.

4.4. Prepare the end-of-day deposit under two-person dual control per
SOP-CASH-009 Section 7 — the safe is never opened by a single associate,
including the closing shift lead, under any circumstance, even when no
other staff member is scheduled to close alongside them; in that case, call
the on-call manager rather than opening the safe solo.

4.5. Arm the security system using the closing associate's individual code
and confirm the system reports "armed" before the final associate exits
the building — do not assume arming succeeded from the keypad beep alone;
the confirmation screen must show "armed" explicitly, since the beep
pattern is identical for a successful arm and a failed arm with a door
sensor still open.

4.6. Log the final exit time and confirm all exterior doors are locked
before leaving the parking lot, not just the main entrance — this includes
the loading dock door, which has a separate lock from the interior
stockroom door and has been the source of two after-hours entry incidents
when checked only from the interior side.

## 5. Related Documents

- **SOP-CASH-009** — Cash Handling SOP (till counts referenced throughout
  Sections 1, 3, and 4)
- Incident postmortems (`corpus/synthetic/mixed/`) — the four POS-ERR
  incidents referenced in Section 2.2
