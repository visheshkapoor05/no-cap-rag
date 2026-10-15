"""
Builds evals/golden_set/golden_set.yaml: 150 hand-authored questions
(T-M4.13 expanded the original 50 to the PRD's 150-200 target). Every
relevant chunk is specified as a natural-key reference --
(title, version, section_path-or-text-substring) -- validated against the
REAL chunks table in Postgres at build time (a typo raises immediately,
never ships silently), but the UUID itself is deliberately NOT what gets
stored. Postgres assigns a fresh gen_random_uuid() every time a row is
re-inserted, so a frozen UUID goes stale the moment anyone re-ingests the
corpus (a schema rebuild, or -- found for real while wiring up this file's
own tests -- an unrelated test's TRUNCATE CASCADE elsewhere in the suite).
title/version/section survive a re-ingest because they come from the
corpus files, not from Postgres; evals/golden_set/resolve.py resolves them
to live UUIDs at the point of actual use. See ../../ANALOGY.md and T-M2.9
in learnings/02-cleaning-chunking-metadata/TASKS.md.

Requires the full synthetic corpus already ingested AND chunked into
Postgres (python -m app.cli ingest --scope synthetic, then chunk every
ingested document with app.chunking.chunk_with_context + insert_chunks)
before running:

    python -m evals.golden_set.build
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.db import get_pool  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / "golden_set.yaml"

EXPECTED_COUNTS = {
    "factual_lookup": 52,
    "exact_identifier": 25,
    "multi_hop": 28,
    "unanswerable": 24,
    "ambiguous": 15,
    # T-M4.13: NOT scaled proportionally like the other categories, on
    # purpose. The corpus has exactly two genuinely versioned document
    # pairs (Loyalty Program Rules v1.0/v2.0, Returns Policy v2.0/v3.0) --
    # every real version-to-version difference in the whole corpus was
    # enumerated by hand, and there are 7, not the ~12 a flat 3x scale-up
    # of the original 4 would suggest. Inventing a fake version difference
    # to hit a round number would violate the one rule this whole golden
    # set exists to enforce: every answer traces to real corpus text,
    # never fabricated to fill a quota.
    "version_sensitive": 7,
}


def _load_chunks(pool) -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute("""
            select c.id as chunk_id, d.id as doc_id, d.title, d.version,
                   c.section_path, c.text
            from chunks c join documents d on d.id = c.document_id
        """).fetchall()
    return [
        {
            "chunk_id": str(r["chunk_id"]),
            "doc_id": str(r["doc_id"]),
            "title": r["title"],
            "version": r["version"],
            "section_path": r["section_path"],
            "text": r["text"],
        }
        for r in rows
    ]


def build(pool) -> dict:
    chunks = _load_chunks(pool)
    if not chunks:
        raise RuntimeError(
            "chunks table is empty -- ingest + chunk the synthetic corpus first "
            "(see this file's module docstring)"
        )

    def find(title, version=None, section=None, text=None):
        matches = [
            c for c in chunks
            if c["title"] == title
            and (version is None or c["version"] == version)
            and (section is None or section in c["section_path"])
            and (text is None or text in c["text"])
        ]
        if len(matches) != 1:
            raise AssertionError(
                f"expected 1 match, got {len(matches)} for "
                f"title={title!r} version={version!r} section={section!r} text={text!r}"
            )
        return matches[0]

    def ref(*specs):
        """Validates every spec resolves to exactly one real chunk RIGHT NOW
        (catches a typo immediately) but stores the natural-key spec itself,
        not the chunk's UUID -- gen_random_uuid() assigns a NEW id every time
        a document/chunk row is re-inserted (e.g. after a TRUNCATE + re-ingest
        elsewhere in the test suite, or a full corpus rebuild), so a UUID
        frozen into this file at build time silently goes stale the moment
        anyone re-ingests. title/version/section are stable natural keys that
        survive a re-ingest because they come from the corpus files
        themselves, not from Postgres."""
        docs, chunks_out = [], []
        for spec in specs:
            title, version, section, text = (spec + (None, None, None, None))[:4]
            find(title, version, section, text)  # raises if not exactly 1 match
            doc_key = {"title": title, "version": version}
            if doc_key not in docs:
                docs.append(doc_key)
            chunks_out.append({"title": title, "version": version, "section": section, "text": text})
        return docs, chunks_out

    questions: list[dict] = []

    def add(category, question, expected_answer, answerable, difficulty, tags, *specs):
        docs, relevant_chunks = ref(*specs) if answerable else ([], [])
        n = sum(1 for q in questions if q["category"] == category) + 1
        questions.append({
            "id": f"{category}-{n:02d}",
            "category": category,
            "question": question,
            "expected_answer": expected_answer,
            "relevant_docs": docs,
            "relevant_chunks": relevant_chunks,
            "answerable": answerable,
            "difficulty": difficulty,
            "tags": tags,
        })

    # ---------------------------------------------------------- factual lookup (15)
    add("factual_lookup", "How many days do I have to return an unopened item?",
        "30 days from delivery or purchase for a full refund to the original payment method.",
        True, "easy", ["returns"],
        ("Returns Policy", "3.0", "1. Standard Return Window"))

    add("factual_lookup", "What percentage discount do active employees get on personal purchases?",
        "20%, applied at checkout using the employee's staff ID, on the pre-tax price.",
        True, "easy", ["staff"],
        ("Employee Discount Policy", "1.0", "1. Standard Discount"))

    add("factual_lookup", "How many days' advance notice is required for a PTO request?",
        "7 days' advance notice, except where the emergency leave exception applies.",
        True, "easy", ["staff"],
        ("Leave Policy", "1.0", "2. PTO Accrual"))

    add("factual_lookup", "How many hours of rest are required between the end of one shift and the start of the next?",
        "A minimum of 10 hours, including for closing-to-opening (\"clopening\") schedules.",
        True, "easy", ["staff"],
        ("Shift Policy", "1.0", "4. Minimum Rest Between Shifts"))

    add("factual_lookup", "Do gift card balances expire?",
        "No. Gift card balances do not expire and no dormancy or maintenance fee is charged.",
        True, "easy", ["gift_cards"],
        ("Gift Card Terms", "1.0", "2. Balance and Expiry"))

    add("factual_lookup", "What is the maximum combined discount allowed when multiple promotions stack on one item?",
        "50% off the original tagged price, regardless of what the individual stacked percentages would otherwise sum to.",
        True, "easy", ["promotions"],
        ("Discount Stacking Rules", "1.0", "3. Maximum Combined Discount"))

    add("factual_lookup", "How many paid days of bereavement leave are granted for an immediate family member?",
        "Up to 3 paid days, separate from PTO and sick leave balances.",
        True, "easy", ["staff"],
        ("Leave Policy", "1.0", "4. Bereavement Leave"))

    add("factual_lookup", "What is the fixed starting cash float for a till at the beginning of a shift?",
        "$200, counted against at shift start; any discrepancy over $2 at opening is logged immediately.",
        True, "easy", ["cash_handling"],
        ("Cash Handling SOP", "1.0", "2. Opening Count"))

    add("factual_lookup", "How long is the full-replacement warranty on general electronics?",
        "90 days from the date of purchase.",
        True, "easy", ["warranty"],
        ("Warranty Policy", "1.0", None, "Electronics (general)"))

    add("factual_lookup", "What is the typical delivery window for Standard shipping?",
        "5-7 business days, not guaranteed unless Expedited or Scheduled service is purchased.",
        True, "easy", ["shipping"],
        ("Shipping Policy", None, None, "Standard | 5"))

    add("factual_lookup", "How many business days does a price-match refund take to process?",
        "Within 5 business days, refunded to the original payment method, never as store credit or points.",
        True, "easy", ["price_match"],
        ("Price Match Policy", "1.0", "5. Refund of the Difference"))

    add("factual_lookup", "Above what till cash amount does a mid-shift cash drop need to be performed?",
        "When till cash exceeds $300 above the starting float.",
        True, "easy", ["cash_handling"],
        ("Cash Handling SOP", "1.0", "3. Mid-Shift Drops"))

    add("factual_lookup", "Under the current loyalty program rules, how many points does a member need to redeem for $1 of purchase value?",
        "100 points redeem for $1 of purchase value, up to 100% of the order total.",
        True, "easy", ["loyalty"],
        ("Loyalty Program Rules", "2.0", "3. Points Redemption"))

    add("factual_lookup", "Under the current loyalty program rules, how many months after being earned do points expire?",
        "18 months after the calendar month in which they were earned, tracked on a rolling basis.",
        True, "easy", ["loyalty"],
        ("Loyalty Program Rules", "2.0", "5. Points Expiry"))

    add("factual_lookup", "After how many consecutive months of no account activity are a member's loyalty points expired?",
        "24 consecutive months of no purchase or redemption activity, at which point all points expire immediately and the account is flagged inactive.",
        True, "easy", ["loyalty"],
        ("Points Expiry Policy", "1.0", "3. Account Inactivity"))

    # ---------------------------------------------------------- factual lookup, continued (T-M4.13, +32)
    add("factual_lookup", "What is the minimum and maximum denomination for a gift card?",
        "$10 to $500.",
        True, "easy", ["gift_cards"],
        ("Gift Card Terms", "1.0", "1. Issuance"))

    add("factual_lookup", "What's required to get a replacement for a lost physical gift card?",
        "The original purchase receipt or activation record -- without proof of the original balance, no replacement or transfer is possible.",
        True, "easy", ["gift_cards"],
        ("Gift Card Terms", "1.0", "4. Loss, Theft, and Fraud"))

    add("factual_lookup", "At how many days on the sales floor does an item first get marked down, and by how much?",
        "45 days, marked down 20%.",
        True, "easy", ["promotions"],
        ("Markdown Policy", None, None, "20% at 45 days"))

    add("factual_lookup", "At what markdown percentage is an item physically re-tagged as clearance?",
        "40% or deeper.",
        True, "easy", ["promotions"],
        ("Markdown Policy", None, None, "clearance\" in addition"))

    add("factual_lookup", "Who must approve reversing a markdown that was applied due to a pricing error?",
        "Regional merchandising approval -- it cannot be done at store level.",
        True, "medium", ["promotions"],
        ("Markdown Policy", None, None, "Markdown Reversal"))

    add("factual_lookup", "What markdown percentage is applied to seasonal inventory at season transition?",
        "30%, two weeks before a further 50% markdown and eventual full clearance liquidation up to 70%.",
        True, "easy", ["promotions"],
        ("Markdown Policy", None, None, "End-of-Season Markdown"))

    add("factual_lookup", "Under the Summer BOGO campaign, what discount applies to the lower-priced qualifying item?",
        "50% off.",
        True, "easy", ["promotions"],
        ("Campaign Brief — BOGO", None, None, "discounted 50%"))

    add("factual_lookup", "By how much can the Summer BOGO campaign's actual margin impact exceed its modeled ceiling before early termination is considered?",
        "More than 15% in any 3-day window, with 48 hours' notice to stores before the promotion is pulled.",
        True, "medium", ["promotions"],
        ("Campaign Brief — BOGO", None, None, "15% in any 3-day window"))

    add("factual_lookup", "What is the employee discount purchase cap?",
        "$2,000 per rolling 30-day period -- purchases beyond the cap are still permitted but don't receive the discount on the excess.",
        True, "easy", ["staff"],
        ("Employee Discount Policy", "1.0", "4. Purchase Limits"))

    add("factual_lookup", "What does an extended warranty add-on cost?",
        "8% of the item's purchase price, and it must be purchased at the time of sale, not added retroactively.",
        True, "easy", ["warranty"],
        ("Warranty Policy", "1.0", None, "8% of the item"))

    add("factual_lookup", "Above what repair-cost percentage is a warranty claim resolved via replacement instead of repair?",
        "When repair cost would exceed 60% of the item's original purchase price, or when parts are discontinued.",
        True, "medium", ["warranty"],
        ("Warranty Policy", "1.0", None, "60% of the item"))

    add("factual_lookup", "How long is the structural-frame warranty on furniture?",
        "5 years (upholstery/fabric coverage is 1 year).",
        True, "easy", ["warranty"],
        ("Warranty Policy", "1.0", None, "Structural frame"))

    add("factual_lookup", "How long is the parts warranty on major appliances?",
        "2 years for parts; labor is covered for 1 year.",
        True, "easy", ["warranty"],
        ("Warranty Policy", "1.0", None, "Major Appliances"))

    add("factual_lookup", "Within how many days must a new owner register a warranty transfer after taking possession of a gifted or resold item?",
        "30 days, providing the original receipt and the original purchaser's written consent.",
        True, "medium", ["warranty"],
        ("Warranty Policy", "1.0", None, "Warranty Transfer"))

    add("factual_lookup", "What is the typical delivery window for Expedited shipping?",
        "2-3 business days, guaranteed or the shipping charge is refunded.",
        True, "easy", ["shipping"],
        ("Shipping Policy", None, None, "Expedited | 2"))

    add("factual_lookup", "What is the typical delivery window for a freight (large item) shipment?",
        "7-14 business days, not guaranteed.",
        True, "easy", ["shipping"],
        ("Shipping Policy", None, None, "Freight (large item)"))

    add("factual_lookup", "Up until what point in order fulfillment can a shipping address be changed at no cost?",
        "Until the order enters \"picking\" status, typically within 2 hours of order placement.",
        True, "medium", ["shipping"],
        ("Shipping Policy", None, None, "without cost up until"))

    add("factual_lookup", "After how many price-match requests within a rolling 30-day period is a customer flagged for manual review?",
        "More than 5.",
        True, "medium", ["price_match"],
        ("Price Match Policy", "1.0", "4. Repeated or Suspicious Requests"))

    add("factual_lookup", "Within how many days after purchase can a customer submit a post-purchase online price-match request?",
        "14 days.",
        True, "easy", ["price_match"],
        ("Price Match Policy", "1.0", "3. Process"))

    add("factual_lookup", "At what variance percentage does a stock-take zone require a recount before the count is finalized?",
        "A variance of 2-5% requires a recount of that zone alone.",
        True, "medium", ["inventory"],
        ("Stock Take SOP", None, None, "2–5% requires"))

    add("factual_lookup", "Within how many hours of count completion must stock-take sheets be submitted to regional inventory control?",
        "48 hours.",
        True, "easy", ["inventory"],
        ("Stock Take SOP", None, None, "48 hours of count completion"))

    add("factual_lookup", "Above what dollar amount does an opening till-count discrepancy get logged and reported to the shift lead immediately?",
        "Over $2.",
        True, "easy", ["cash_handling"],
        ("Cash Handling SOP", "1.0", "2. Opening Count"))

    add("factual_lookup", "What closing till discrepancy amount requires same-shift shift-lead review?",
        "$5-$25 -- under $5 is logged with no escalation, over $25 requires a full transaction-log review before the associate leaves.",
        True, "medium", ["cash_handling"],
        ("Cash Handling SOP", "1.0", "5. Closing Count and Discrepancy Reporting"))

    add("factual_lookup", "What paid and unpaid breaks are included in a shift of 5 hours or more?",
        "One paid 15-minute break and one unpaid 30-minute meal break.",
        True, "easy", ["staff"],
        ("Shift Policy", "1.0", "2. Breaks"))

    add("factual_lookup", "How many days in advance are employee schedules posted?",
        "14 days.",
        True, "easy", ["staff"],
        ("Shift Policy", "1.0", "1. Scheduling"))

    add("factual_lookup", "How many unexcused no-shows within a rolling 90-day period trigger a formal attendance review?",
        "Two.",
        True, "easy", ["staff"],
        ("Shift Policy", "1.0", "5. Attendance and No-Shows"))

    add("factual_lookup", "Below what order value may a shift lead authorize an immediate replacement without waiting for a carrier trace to complete?",
        "Under $30.",
        True, "medium", ["shipping"],
        ("Delivery Dispute Runbook", None, None, "under $30"))

    add("factual_lookup", "How many delivery disputes within a rolling 6-month period flags an account for manual review?",
        "3 or more.",
        True, "medium", ["shipping"],
        ("Delivery Dispute Runbook", None, None, "3 or more delivery disputes"))

    add("factual_lookup", "Within how many business days of a chargeback notice must evidence be gathered?",
        "5 business days.",
        True, "medium", ["chargebacks"],
        ("Chargeback Handling Runbook", None, None, "Within 5 business days"))

    add("factual_lookup", "What is the typical deadline to respond to a chargeback before it's automatically decided in the customer's favor?",
        "10-14 business days, per the card issuer's deadline.",
        True, "medium", ["chargebacks"],
        ("Chargeback Handling Runbook", None, None, "10–14 business days"))

    add("factual_lookup", "What is the annual spend threshold for PLATINUM_TIER under the current loyalty program rules?",
        "$5,000.",
        True, "easy", ["loyalty"],
        ("Loyalty Program Rules", "2.0", "1. Tier Structure"))

    add("factual_lookup", "What was the card transaction failure rate during the Payment Gateway Failure incident?",
        "Approximately 35% of attempts, for 22 minutes store-wide.",
        True, "medium", ["incidents"],
        ("Payment Gateway Failure Postmortem", None, None, "35% of attempts"))

    add("factual_lookup", "Approximately how long did the POS Outage incident last?",
        "Approximately 47 minutes.",
        True, "medium", ["incidents"],
        ("POS Outage Postmortem", None, None, "47 minutes"))

    add("factual_lookup", "Approximately how many SKUs had incorrect online-availability counts during the Inventory Sync Failure incident?",
        "Approximately 4,100 SKUs across all stores, for a three-day window.",
        True, "medium", ["incidents"],
        ("Inventory Sync Failure Postmortem", None, None, "4,100 SKUs"))

    add("factual_lookup", "Approximately how many transactions were affected by the Loyalty Points Double-Credit incident?",
        "Approximately 1,900 transactions of the day's roughly 40,000, at a total write-off cost of about $4,200.",
        True, "medium", ["incidents", "loyalty"],
        ("Loyalty Double-Credit Postmortem", None, None, "roughly 1,900"))

    add("factual_lookup", "Does warranty coverage begin on the purchase date or the delivery date for a shipped order?",
        "The purchase date, as shown on the original receipt or order confirmation -- not the delivery date.",
        True, "medium", ["warranty"],
        ("Warranty Policy", "1.0", None, "begins on the date of purchase"))

    add("factual_lookup", "What is the restocking fee that may apply to an opened electronics return accepted outside the standard window?",
        "Up to 15%, applied at associate discretion.",
        True, "medium", ["returns"],
        ("Returns Policy", "2.0", "3. Exceptions > 3.1 Electronics"))

    # ---------------------------------------------------------- exact identifier (8)
    add("exact_identifier", "What does incident code POS-ERR-3021 refer to?",
        "The POS Outage Postmortem -- a ~47-minute network-layer outage affecting register connectivity at 14 stores on 2026-03-18.",
        True, "medium", ["identifier", "incidents"],
        ("POS Outage Postmortem", None, None, "Incident Postmortem: Point-of-Sale Outage"))

    add("exact_identifier", "What does incident code POS-ERR-3045 refer to?",
        "The Payment Gateway Failure Postmortem -- a 22-minute payment-authorization failure caused by an uncommunicated TLS certificate rotation, on 2026-04-09.",
        True, "medium", ["identifier", "incidents"],
        ("Payment Gateway Failure Postmortem", None, None, "Incident Postmortem: Payment Gateway Failure"))

    add("exact_identifier", "What does incident code POS-ERR-3102 refer to?",
        "The Inventory Sync Failure Postmortem -- a silent 3-night inventory sync failure caused by a POS export schema change, detected 2026-05-02.",
        True, "medium", ["identifier", "incidents"],
        ("Inventory Sync Failure Postmortem", None, None, "Incident Postmortem - Inventory Sync Failure"))

    add("exact_identifier", "What does incident code POS-ERR-3210 refer to?",
        "The Loyalty Double-Credit Postmortem -- a race condition in the accrual retry logic that double-credited points on ~1,900 transactions, on 2026-05-22.",
        True, "medium", ["identifier", "incidents"],
        ("Loyalty Double-Credit Postmortem", None, None, "Incident Postmortem: Loyalty Points Double-Credit"))

    add("exact_identifier", "What is document SOP-RET-014?",
        "The Returns Exception Matrix -- the internal procedure associates follow when a return request doesn't cleanly fit the standard Returns Policy (RET-POL-001).",
        True, "medium", ["identifier", "returns"],
        ("Returns Exception Matrix", "2.0", None, "SOP ID:** SOP-RET-014"))

    add("exact_identifier", "What is runbook RUN-REF-001 used for?",
        "The Failed Refund Runbook -- used when a refund was already approved but fails to actually process; it assumes the decision to refund was correct and is purely about recovering a stuck transaction.",
        True, "medium", ["identifier", "refunds"],
        ("Failed Refund Runbook", "1.0", None, "Runbook ID:** RUN-REF-001"))

    add("exact_identifier", "What is policy PROMO-POL-002?",
        "The Discount Stacking Rules -- the most cross-referenced document in the corpus, defining what counts as a \"promotional discount\" for the Returns Policy, Warranty Policy exclusions, and Price Match Policy.",
        True, "medium", ["identifier", "promotions"],
        ("Discount Stacking Rules", "1.0", None, "Policy ID:** PROMO-POL-002"))

    add("exact_identifier", "What is SOP-CASH-009?",
        "The Cash Handling SOP -- governs till assignment, opening/closing counts, mid-shift drops, and safe access procedures.",
        True, "medium", ["identifier", "cash_handling"],
        ("Cash Handling SOP", "1.0", None, "SOP ID:** SOP-CASH-009"))

    # ---------------------------------------------------------- exact identifier, continued (T-M4.13, +17)
    add("exact_identifier", "What is runbook RUN-CHG-003 used for?",
        "The Chargeback Handling Runbook -- used when a card issuer notifies the store of a customer-initiated chargeback.",
        True, "medium", ["identifier", "chargebacks"],
        ("Chargeback Handling Runbook", None, None, "Runbook ID: RUN-CHG-003"))

    add("exact_identifier", "What is runbook RUN-DEL-002 used for?",
        "The Delivery Dispute Runbook -- used when a customer reports an online order as not received despite carrier tracking showing delivery.",
        True, "medium", ["identifier", "shipping"],
        ("Delivery Dispute Runbook", None, None, "Runbook ID: RUN-DEL-002"))

    add("exact_identifier", "What is policy GC-POL-001?",
        "The Gift Card Terms -- issuance, balance/expiry, redemption, loss/theft/fraud, and returns involving gift cards.",
        True, "medium", ["identifier", "gift_cards"],
        ("Gift Card Terms", "1.0", None, "Policy ID:** GC-POL-001"))

    add("exact_identifier", "What is policy STAFF-POL-001?",
        "The Shift Policy -- scheduling, breaks, overtime, minimum rest between shifts, and attendance.",
        True, "medium", ["identifier", "staff"],
        ("Shift Policy", "1.0", None, "Policy ID:** STAFF-POL-001"))

    add("exact_identifier", "What is policy STAFF-POL-002?",
        "The Employee Discount Policy -- the 20% standard staff discount and its interactions with loyalty points, markdowns, and purchase limits.",
        True, "medium", ["identifier", "staff"],
        ("Employee Discount Policy", "1.0", None, "Policy ID:** STAFF-POL-002"))

    add("exact_identifier", "What is policy STAFF-POL-003?",
        "The Leave Policy -- PTO, sick leave, bereavement leave, and unpaid personal leave.",
        True, "medium", ["identifier", "staff"],
        ("Leave Policy", "1.0", None, "Policy ID:** STAFF-POL-003"))

    add("exact_identifier", "What is policy LOY-POL-001?",
        "The Loyalty Program Rules -- tier structure, points accrual, redemption, points handling on returns, and points expiry (headline rule).",
        True, "medium", ["identifier", "loyalty"],
        ("Loyalty Program Rules", "2.0", None, "Policy ID:** LOY-POL-001 · **Version:** 2.0"))

    add("exact_identifier", "What is policy LOY-POL-002?",
        "The Points Expiry Policy -- the detailed reference for point expiry mechanics, including account inactivity and store-closure reinstatement.",
        True, "medium", ["identifier", "loyalty"],
        ("Points Expiry Policy", "1.0", None, "Policy ID:** LOY-POL-002"))

    add("exact_identifier", "What is policy PM-POL-001?",
        "The Price Match Policy -- eligibility, process, repeated-request flagging, and refund of the difference.",
        True, "medium", ["identifier", "price_match"],
        ("Price Match Policy", "1.0", None, "Policy ID:** PM-POL-001"))

    add("exact_identifier", "What is policy PROMO-POL-001?",
        "The Summer BOGO Campaign Brief -- the \"buy one, get one 50% off\" promotion's mechanics, eligible categories, and return handling.",
        True, "medium", ["identifier", "promotions"],
        ("Campaign Brief — BOGO", None, None, "Policy ID: PROMO-POL-001"))

    add("exact_identifier", "What is policy PROMO-POL-003?",
        "The Markdown Policy -- the markdown cadence, clearance tagging, markdown reversal, and seasonal markdown schedule.",
        True, "medium", ["identifier", "promotions"],
        ("Markdown Policy", None, None, "Policy ID: PROMO-POL-003"))

    add("exact_identifier", "What is SOP-OPEN-002?",
        "The Opening/Closing Checklist -- pre-opening, during-business-hours, pre-closing, and post-closing procedures.",
        True, "medium", ["identifier"],
        ("Opening/Closing Checklist", "1.0", None, "SOP ID:** SOP-OPEN-002"))

    add("exact_identifier", "What is SOP-STOCK-005?",
        "The Stock Take SOP -- the quarterly periodic full-store inventory count procedure.",
        True, "medium", ["identifier", "inventory"],
        ("Stock Take SOP", None, None, "SOP ID: SOP-STOCK-005"))

    add("exact_identifier", "What is policy SHIP-POL-001?",
        "The Shipping Policy -- delivery windows, carriers, address changes, shipping-charge refunds, and international shipping.",
        True, "medium", ["identifier", "shipping"],
        ("Shipping Policy", None, None, "Policy ID: SHIP-POL-001"))

    add("exact_identifier", "What is policy WAR-POL-001?",
        "The Warranty Policy -- coverage by category, filing a claim, extended warranty, transfer, and international/online-only purchases.",
        True, "medium", ["identifier", "warranty"],
        ("Warranty Policy", "1.0", None, "Policy ID: WAR-POL-001"))

    add("exact_identifier", "What architecture decision does ADR-001 record?",
        "The Order Management System choice -- adopting a commercial OMS platform with a dedicated integration layer, rather than building in-house or extending the POS vendor's order module.",
        True, "hard", ["identifier", "architecture"],
        ("OMS Choice ADR", None, None, "ADR ID: ADR-001"))

    add("exact_identifier", "What architecture decision does ADR-002 record?",
        "The Loyalty Platform choice -- building the points ledger in-house on the existing transactional database, rather than adopting a commercial platform or extending the OMS event log.",
        True, "hard", ["identifier", "architecture", "loyalty"],
        ("Loyalty Platform Choice ADR", None, None, "ADR ID ADR-002"))

    # ---------------------------------------------------------- multi-hop (10)
    add("multi_hop",
        "A GOLD_TIER member returns an item they bought partly with points at a 25% clearance discount. What happens to the points portion, and does the return affect their tier status?",
        "The points portion is refunded back to the member's account (within 24 hours under the current Loyalty Program Rules), the discount is applied proportionally across the points/cash split before that refund is calculated, and the return does not affect tier status since no new spend occurred to reverse -- this is the exact worked example in Loyalty Program Rules v2.0 Section 4, which Returns Policy v3.0 Section 3.3 defers to.",
        True, "hard", ["multi_hop", "loyalty", "returns"],
        ("Loyalty Program Rules", "2.0", "4. Points Handling on Returns"),
        ("Returns Policy", "3.0", "3. Exceptions > 3.3 Items Purchased Partly or Fully with Loyalty Points"))

    add("multi_hop",
        "Does a price-matched item qualify for the shortened 14-day return window that applies to discounted items?",
        "No. A price match is explicitly not a promotional discount under the Discount Stacking Rules, so Returns Policy Section 3.2's shortened window (for items discounted 20% or more) does not apply to a price-matched item.",
        True, "hard", ["multi_hop", "price_match", "returns"],
        ("Price Match Policy", "1.0", "2. What Is Not a Price Match"),
        ("Returns Policy", "3.0", "3. Exceptions > 3.1 Electronics; 3.2 Discounted Items"))

    add("multi_hop",
        "An employee buys a $100 item that's been marked down 30% to $70 using their employee discount. What's the final price, and is it subject to the customer-facing 50% combined-discount cap?",
        "$56. The employee discount is applied after the markdown price ($70), not the original tag price, for a final price of $56 -- and it is not subject to the Discount Stacking Rules' 50% cap, since that cap applies to customer promotions and the employee discount is a staff benefit the two policies deliberately don't cross-apply.",
        True, "hard", ["multi_hop", "staff", "promotions"],
        ("Employee Discount Policy", "1.0", "3. Interaction with Markdown/Clearance Pricing"),
        ("Markdown Policy", None, None, "Markdown percentage is calculated"))

    add("multi_hop",
        "A customer's chargeback arrives after the store already processed a refund for the same transaction through normal channels. Is this a strong or weak case for the store to dispute?",
        "Strong case for dispute -- the customer has effectively attempted to be refunded twice, since a refund was already issued via the Returns Policy before the chargeback was filed.",
        True, "hard", ["multi_hop", "chargebacks", "refunds"],
        ("Chargeback Handling Runbook", None, None, "Gathering Evidence"),
        ("Chargeback Handling Runbook", None, None, "Refund already issued via RET-POL-001"))

    add("multi_hop",
        "After the loyalty points double-credit incident, was the decision to build the points ledger in-house (rather than use a commercial platform) reconsidered?",
        "No. The ADR was explicitly not revisited -- the bug was an application-layer idempotency-key defect in the accrual retry logic, independent of the underlying database/platform choice, and the same bug class could have occurred against a commercial platform's API too if its retry contract were misunderstood.",
        True, "hard", ["multi_hop", "loyalty", "architecture"],
        ("Loyalty Platform Choice ADR", None, None, "A note on hindsight"),
        ("Loyalty Double-Credit Postmortem", None, None, "Root Cause"))

    add("multi_hop",
        "A closing-shift discrepancy traces back to a specific refund transaction that appears in the log but doesn't match the physical cash removed. What should the associate do?",
        "This isn't a cash-handling failure in the sense the Cash Handling SOP otherwise covers -- it should be escalated to the Failed Refund Runbook, Section 2, specifically the \"No refund record, but register shows cash removed\" row, which routes it back to the Cash Handling SOP's till-discrepancy process -- the two documents cross-reference each other for exactly this case.",
        True, "hard", ["multi_hop", "cash_handling", "refunds"],
        ("Cash Handling SOP", "1.0", "6. When a Discrepancy Traces to a Refund"),
        ("Failed Refund Runbook", "1.0", "2. Identify the Failure Mode"))

    add("multi_hop",
        "An associate declines to approve a disputed final-sale tagging at the register. Who actually has the authority to resolve it, and can a shift lead override that decision?",
        "No -- a shift lead or store manager can override most \"No\"/\"Manager may override\" rows in the Exception Matrix, but disputed final-sale tagging specifically requires escalation to a regional manager and must not be overridden at the register.",
        True, "hard", ["multi_hop", "returns"],
        ("Returns Exception Matrix", "2.0", "2. Exception Table"),
        ("Returns Exception Matrix", "2.0", "4. Manager Override Authority"))

    add("multi_hop",
        "During the payment gateway outage, should stalled refunds have been retried?",
        "No -- the Failed Refund Runbook's guidance is not to retry during an active known gateway incident, since retrying risks a duplicate refund once the gateway recovers. This is exactly what happened with the 18 refunds stalled during the Payment Gateway Failure incident: none were retried, all completed automatically once the gateway recovered, and no duplicates resulted.",
        True, "hard", ["multi_hop", "refunds", "incidents"],
        ("Failed Refund Runbook", "1.0", "3. Payment Gateway Timeout"),
        ("Payment Gateway Failure Postmortem", None, None, "The 18 stalled refunds"))

    add("multi_hop",
        "A customer's warranty claim on a 6-month-old item is denied for misuse. Are they automatically entitled to a standard return instead?",
        "Not automatically -- a denied warranty claim and an expired return window are independent conditions. The customer may still be eligible for a standard return, but only if the item still falls within the Returns Policy's applicable window for its category.",
        True, "hard", ["multi_hop", "warranty", "returns"],
        ("Warranty Policy", "1.0", None, "independent conditions"),
        ("Returns Policy", "3.0", "1. Standard Return Window"))

    add("multi_hop",
        "A corporate loyalty account is closed mid-year with unredeemed points on it. Are those points forfeited, or do they follow the standard annual corporate batch-expiry schedule?",
        "Forfeited immediately on closure, not carried to the next batch-expiry date -- account closure (voluntary or fraud-related) forfeits all unredeemed points right away, regardless of which expiry mechanic (standard rolling, or the corporate flat annual batch) would otherwise have applied to them.",
        True, "hard", ["multi_hop", "loyalty"],
        ("Points Expiry Policy", "1.0", "5. Account Transfers and Closures"),
        ("Points Expiry Policy", "1.0", "6. Corporate and Bulk Accounts"))

    # ---------------------------------------------------------- multi-hop, continued (T-M4.13, +18)
    add("multi_hop",
        "Under the Summer BOGO campaign, is a loyalty-tier discount applied before or after the BOGO 50% discount?",
        "The loyalty-tier percentage is applied first, then the BOGO 50% discount is calculated on the resulting post-loyalty price of the lower-priced qualifying item -- this follows the standard stacking order defined in the Discount Stacking Rules.",
        True, "hard", ["multi_hop", "promotions", "loyalty"],
        ("Campaign Brief — BOGO", None, None, "Stacking with Loyalty Discounts"),
        ("Discount Stacking Rules", "1.0", "2. Stacking Order"))

    add("multi_hop",
        "Does a clearance-tagged item that falls within the 14-day discounted-item return window qualify for a same-item size exchange?",
        "Yes -- this exception was added in Returns Exception Matrix v2.0 specifically for items tagged clearance under the Markdown Policy that fall within Returns Policy Section 3.2's shortened window.",
        True, "hard", ["multi_hop", "returns", "promotions"],
        ("Markdown Policy", None, None, "Clearance Tagging"),
        ("Returns Exception Matrix", "2.0", "3. New in This Version: Clearance-Tagged Item Exception"))

    add("multi_hop",
        "An employee buys a clearance-tagged item using their staff discount. Does the discount apply on top of the clearance price, and is the combination subject to the customer-facing 50% combined-discount cap?",
        "Yes, the employee discount stacks with the already-marked-down clearance price, and no, it is not subject to the Discount Stacking Rules' 50% cap -- the employee discount is a staff benefit, not a customer promotion, and the two policies deliberately don't cross-apply.",
        True, "hard", ["multi_hop", "staff", "promotions"],
        ("Markdown Policy", None, None, "Employee Discount Interaction"),
        ("Employee Discount Policy", "1.0", "3. Interaction with Markdown/Clearance Pricing"))

    add("multi_hop",
        "A stock-take zone shows a variance over 5%. What does the store manager need to review, and why?",
        "The zone's recent transaction log for the same window covered by the Cash Handling SOP's discrepancy thresholds -- a large inventory variance and a cash variance in the same period often share a root cause, most commonly a miscoded return or an unlogged damage write-off.",
        True, "hard", ["multi_hop", "inventory", "cash_handling"],
        ("Stock Take SOP", None, None, "over 5% requires"),
        ("Cash Handling SOP", "1.0", "5. Closing Count and Discrepancy Reporting"))

    add("multi_hop",
        "A customer purchased an item online and shipped to an address outside the country of sale. If they need a warranty service return, who pays the return shipping cost?",
        "The customer -- unlike domestic warranty service where the store covers return shipping for an approved claim, an international online purchase returned for warranty service is the customer's shipping responsibility.",
        True, "hard", ["multi_hop", "warranty", "shipping"],
        ("Warranty Policy", "1.0", None, "International and Online-Only"),
        ("Shipping Policy", None, None, "International orders are subject"))

    add("multi_hop",
        "Can a non-keyholder employee cover an opening shift through a shift-swap request?",
        "No -- shift swaps require both employees to be qualified for the role, and only keyholders may cover opening/closing shifts, per the Opening/Closing Checklist's individual-code requirement.",
        True, "hard", ["multi_hop", "staff"],
        ("Shift Policy", "1.0", "1. Scheduling"),
        ("Opening/Closing Checklist", "1.0", "1. Pre-Opening (before doors unlock)"))

    add("multi_hop",
        "An employee goes on unpaid personal leave for 70 days. What happens to their personal loyalty account?",
        "It is treated as any other inactive account under the standard 24-month inactivity rule -- employment status does not exempt an account, and extended leave alone does not reset that clock.",
        True, "hard", ["multi_hop", "staff", "loyalty"],
        ("Leave Policy", "1.0", "7. Leave and Loyalty Program Interaction"),
        ("Points Expiry Policy", "1.0", "3. Account Inactivity"))

    add("multi_hop",
        "Why wasn't the loyalty points ledger folded into the Order Management System's own event log instead of staying a separate system?",
        "It was rejected specifically because keeping loyalty state as a single source of truth queried by the OMS, rather than replicated into it, avoids the class of consistency bug that caused the loyalty double-credit incident -- extending the OMS event log to carry loyalty state directly would have reintroduced that exact risk.",
        True, "hard", ["multi_hop", "architecture", "loyalty"],
        ("Loyalty Platform Choice ADR", None, None, "Second, against extending the OMS event log"),
        ("OMS Choice ADR", None, None, "loyalty point balances remain authoritative"))

    add("multi_hop",
        "What do the Inventory Sync Failure and Payment Gateway Failure incidents have in common in terms of root-cause pattern?",
        "Both trace back to an external system change made without advance notice to the team depending on that system's stable interface -- a POS export schema change in one case, an uncommunicated TLS certificate rotation in the other.",
        True, "hard", ["multi_hop", "incidents"],
        ("Inventory Sync Failure Postmortem", None, None, "similar in spirit to the certificate rotation"),
        ("Payment Gateway Failure Postmortem", None, None, "not communicated to the integration team"))

    add("multi_hop",
        "A customer wants a second price match on the same item after an even lower price appeared following their first match. What's their recourse?",
        "A second match on the same item is not permitted -- their recourse is the standard return window under the Returns Policy, followed by a new purchase at the lower price if it's still available.",
        True, "hard", ["multi_hop", "price_match", "returns"],
        ("Price Match Policy", "1.0", "6. One Match Per Item"),
        ("Returns Policy", "3.0", "1. Standard Return Window"))

    add("multi_hop",
        "A chargeback is filed for a transaction where a refund had already been issued through the Failed Refund Runbook's recovery process. Is this a strong or weak case for the store to dispute?",
        "A strong case -- a chargeback filed after a refund was already processed, whether through normal Returns Policy channels or the Failed Refund Runbook's recovery path, means the customer has effectively attempted to be refunded twice.",
        True, "hard", ["multi_hop", "chargebacks", "refunds"],
        ("Chargeback Handling Runbook", None, None, "Refund already issued via RET-POL-001"),
        ("Failed Refund Runbook", "1.0", None, "Use this runbook when a refund has been approved"))

    add("multi_hop",
        "Why don't gift card balances expire the way loyalty points do?",
        "Because the two are legally and operationally distinct instruments -- a gift card represents pre-paid store credit, while loyalty points represent an earned, non-purchased reward that's designed to expire on a rolling basis.",
        True, "medium", ["multi_hop", "gift_cards", "loyalty"],
        ("Gift Card Terms", "1.0", "2. Balance and Expiry"),
        ("Points Expiry Policy", "1.0", "1. Standard Expiry"))

    add("multi_hop",
        "If an employee returns an item they bought using their staff discount, is the refund calculated on the discounted price or the original tag price?",
        "The discounted price actually paid, not the original tag price -- consistent with how any promotional-price return is handled, though the return window itself still follows the standard Returns Policy windows.",
        True, "hard", ["multi_hop", "staff", "returns"],
        ("Employee Discount Policy", "1.0", "5. Returns on Employee-Discounted Purchases"),
        ("Returns Policy", "3.0", "1. Standard Return Window"))

    add("multi_hop",
        "Can a customer apply a coupon code to a clearance-tagged item?",
        "No -- clearance-tagged items can accept a loyalty-tier percentage but not a coupon code; if one is entered, it's silently ignored for that line item rather than rejecting the whole order.",
        True, "hard", ["multi_hop", "promotions"],
        ("Discount Stacking Rules", "1.0", "4. Exclusions from Stacking"),
        ("Markdown Policy", None, None, "Clearance Tagging"))

    add("multi_hop",
        "An online order's shipping address is changed after the order has already entered picking status. How is the original charge handled?",
        "The order must be canceled and re-placed -- the original charge is refunded per standard Returns Policy processing times, once the original shipment is confirmed returned to the fulfillment center by the carrier.",
        True, "hard", ["multi_hop", "shipping", "returns"],
        ("Shipping Policy", None, None, "After picking has begun"),
        ("Returns Policy", "3.0", "4. Refund Method"))

    add("multi_hop",
        "A package's tracking shows delivery to an address that doesn't match the order. Is this processed as a return under the Returns Policy?",
        "No -- this is treated as carrier error, not a return. A replacement ships immediately at no cost and the original charge is left untouched, since no return of goods is possible or expected from the customer in this scenario.",
        True, "hard", ["multi_hop", "shipping", "returns"],
        ("Delivery Dispute Runbook", None, None, "Misdelivered Package Cases"),
        ("Returns Policy", "3.0", "2. Non-Returnable Items"))

    add("multi_hop",
        "A points-expiry-eligible customer's points were set to expire during the POS Outage window and they couldn't redeem them in time. What can they do?",
        "Contact support within 30 days of the outage -- the affected points are eligible for reinstatement with a fresh 90-day expiry window, since this incident is the specific case the Points Expiry Policy's store-closure/outage provision was written to cover.",
        True, "hard", ["multi_hop", "incidents", "loyalty"],
        ("POS Outage Postmortem", None, None, "Interaction with Points Expiry"),
        ("Points Expiry Policy", "1.0", "4. Store Closures and System Outages"))

    add("multi_hop",
        "After the loyalty points double-credit incident, what specific corrective action followed directly from the decision to build the ledger in-house rather than adopt a commercial platform?",
        "The ledger-level uniqueness constraint added as a second line of defense, independent of the application-level idempotency logic -- a commercial platform's internal correctness guarantees would not have been the team's problem to solve, whereas building in-house made it exactly that.",
        True, "hard", ["multi_hop", "architecture", "incidents", "loyalty"],
        ("Loyalty Platform Choice ADR", None, None, "Consequences: the team owns the full correctness burden"),
        ("Loyalty Double-Credit Postmortem", None, None, "ledger-level uniqueness constraint"))

    # ---------------------------------------------------------- unanswerable (8)
    add("unanswerable", "What is the store's policy on accepting cryptocurrency as a payment method?",
        None, False, "medium", ["unanswerable"])

    add("unanswerable", "Does the store price-match against Amazon specifically?",
        None, False, "medium", ["unanswerable", "price_match"])

    add("unanswerable", "What is the maximum weight allowed for a freight (large-item) shipment?",
        None, False, "medium", ["unanswerable", "shipping"])

    add("unanswerable", "Is accidental water damage covered under the standard warranty?",
        None, False, "medium", ["unanswerable", "warranty"])

    add("unanswerable", "Does the company offer an employee referral bonus program?",
        None, False, "medium", ["unanswerable", "staff"])

    add("unanswerable", "What is the minimum age to open a store loyalty account?",
        None, False, "medium", ["unanswerable", "loyalty"])

    add("unanswerable", "Can an item purchased on a corporate business account be exchanged for a different size?",
        None, False, "medium", ["unanswerable", "returns"])

    add("unanswerable", "What is the store's policy on matching a competitor's Black Friday doorbuster price specifically?",
        None, False, "medium", ["unanswerable", "price_match"])

    # ---------------------------------------------------------- unanswerable, continued (T-M4.13, +16)
    add("unanswerable", "Is there a free-shipping threshold for Standard delivery?",
        None, False, "medium", ["unanswerable", "shipping"])

    add("unanswerable", "Does the store offer a layaway program?",
        None, False, "medium", ["unanswerable"])

    add("unanswerable", "Can customers pre-order an item that's currently out of stock?",
        None, False, "medium", ["unanswerable"])

    add("unanswerable", "Are employees eligible for health insurance benefits?",
        None, False, "medium", ["unanswerable", "staff"])

    add("unanswerable", "Is there an employee dress code policy?",
        None, False, "medium", ["unanswerable", "staff"])

    add("unanswerable", "What is the process for an employee to request a transfer to a different store location?",
        None, False, "medium", ["unanswerable", "staff"])

    add("unanswerable", "Does the Warranty Policy cover rental or demo units?",
        None, False, "medium", ["unanswerable", "warranty"])

    add("unanswerable", "Is there a dedicated process for business-to-business bulk purchase returns?",
        None, False, "medium", ["unanswerable", "returns"])

    add("unanswerable", "Does the store price-match against its own other store locations?",
        None, False, "medium", ["unanswerable", "price_match"])

    add("unanswerable", "Is there an annual, rather than rolling 30-day, cap on the number of price-match requests a customer can submit?",
        None, False, "medium", ["unanswerable", "price_match"])

    add("unanswerable", "Does accrued PTO transfer if an employee moves to a different store location?",
        None, False, "medium", ["unanswerable", "staff"])

    add("unanswerable", "Are remote or work-from-home shifts permitted under the Shift Policy?",
        None, False, "medium", ["unanswerable", "staff"])

    add("unanswerable", "Is there a referral bonus program for customers who refer friends?",
        None, False, "medium", ["unanswerable"])

    add("unanswerable", "Can a customer get a price adjustment if the store itself lowers the price after their purchase, separate from a competitor price match?",
        None, False, "medium", ["unanswerable", "price_match"])

    add("unanswerable", "Does the store offer installment or buy-now-pay-later payment plans?",
        None, False, "medium", ["unanswerable"])

    add("unanswerable", "What is the minimum age requirement to be hired as an employee?",
        None, False, "medium", ["unanswerable", "staff"])

    # ---------------------------------------------------------- ambiguous (5)
    add("ambiguous", "What's the return window?",
        "Depends on category: 30 days standard, 15 days for electronics, 14 days for items discounted 20%+ (current policy), and gift cards/personalized/perishable/final-sale items are not returnable at all.",
        True, "hard", ["ambiguous", "returns"],
        ("Returns Policy", "3.0", "1. Standard Return Window"),
        ("Returns Policy", "3.0", "3. Exceptions > 3.1 Electronics; 3.2 Discounted Items"),
        ("Returns Policy", "3.0", "2. Non-Returnable Items"))

    add("ambiguous", "How much is the discount?",
        "Depends which discount: 20% flat for the employee discount, up to 50% combined cap for stacked customer promotions, or a markdown cadence of 20-70% depending on how long an item has been on the floor -- these are three distinct, non-interchangeable mechanisms.",
        True, "hard", ["ambiguous", "promotions"],
        ("Employee Discount Policy", "1.0", "1. Standard Discount"),
        ("Discount Stacking Rules", "1.0", "3. Maximum Combined Discount"),
        ("Markdown Policy", None, None, "Markdown Cadence"))

    add("ambiguous", "When do points expire?",
        "Depends on account type and activity: 18 months after the earn-month under the standard rolling rule, immediately on 24 months of account inactivity, or as a single annual batch on December 31 for corporate/bulk accounts -- three different mechanics, not one rule.",
        True, "hard", ["ambiguous", "loyalty"],
        ("Loyalty Program Rules", "2.0", "5. Points Expiry"),
        ("Points Expiry Policy", "1.0", "3. Account Inactivity"),
        ("Points Expiry Policy", "1.0", "6. Corporate and Bulk Accounts"))

    add("ambiguous", "What happens if there's a discrepancy?",
        "Depends which kind: a cash-till discrepancy follows the Cash Handling SOP's dollar-threshold escalation ladder, while an inventory discrepancy found during a stock take follows the Stock Take SOP's percentage-variance recount/review thresholds -- unrelated procedures that both use the word \"discrepancy.\"",
        True, "hard", ["ambiguous", "cash_handling"],
        ("Cash Handling SOP", "1.0", "5. Closing Count and Discrepancy Reporting"),
        ("Stock Take SOP", None, None, "A variance under 2%"))

    add("ambiguous", "Who can authorize an override?",
        "Depends on context: for most Returns Exception Matrix rows, a shift lead or store manager; for disputed final-sale tagging specifically, only a regional manager; for a non-emergency schedule change, the affected employee has to agree, store management alone can't impose it.",
        True, "hard", ["ambiguous", "returns", "staff"],
        ("Returns Exception Matrix", "2.0", "4. Manager Override Authority"),
        ("Returns Exception Matrix", "2.0", "2. Exception Table"),
        ("Shift Policy", "1.0", "1. Scheduling"))

    # ---------------------------------------------------------- ambiguous, continued (T-M4.13, +10)
    add("ambiguous", "How much advance notice is required?",
        "Depends what for: 14 days for a posted schedule, 7 days for a standard PTO request (waived entirely for a genuine emergency), or 7 days before the next schedule posting for a standing availability change -- three unrelated notice requirements.",
        True, "hard", ["ambiguous", "staff"],
        ("Shift Policy", "1.0", "1. Scheduling"),
        ("Leave Policy", "1.0", "2. PTO Accrual"),
        ("Leave Policy", "1.0", "5. Emergency Leave Exception"))

    add("ambiguous", "What is the warranty period?",
        "Depends on category: 90 days full replacement for general electronics, 2 years parts/1 year labor for major appliances, 5 years structural/1 year upholstery for furniture, 1 year full replacement for small kitchen appliances -- all extendable by 1 additional year for 8% of purchase price.",
        True, "hard", ["ambiguous", "warranty"],
        ("Warranty Policy", "1.0", None, "Electronics (general)"),
        ("Warranty Policy", "1.0", None, "Major Appliances"),
        ("Warranty Policy", "1.0", None, "Structural frame"))

    add("ambiguous", "Can I get cash back for a refund?",
        "Depends on the amount: cash refunds under $75 are paid from the till directly, but cash purchases over $75 are refunded as store credit rather than cash, specifically to reduce till discrepancy risk at close.",
        True, "hard", ["ambiguous", "cash_handling", "returns"],
        ("Cash Handling SOP", "1.0", "4. Refund and Return Cash Handling"),
        ("Returns Policy", "3.0", "4. Refund Method"))

    add("ambiguous", "Is it eligible for exchange?",
        "Depends which item: a clearance-tagged item within the 14-day discounted-item window can be exchanged for a different size/color at associate discretion, while a final-sale item is never eligible for return or exchange under any circumstance an associate can authorize.",
        True, "hard", ["ambiguous", "returns"],
        ("Returns Exception Matrix", "2.0", "3. New in This Version: Clearance-Tagged Item Exception"),
        ("Returns Policy", "3.0", "2. Non-Returnable Items"))

    add("ambiguous", "What happens if there's fraud?",
        "Depends which kind: a gift card can be deactivated and its balance transferred with proof of purchase, a price-match request pattern consistent with abuse is flagged for manual review, and a loyalty account closed due to a fraud investigation forfeits all unredeemed points immediately -- three unrelated fraud-handling procedures.",
        True, "hard", ["ambiguous", "gift_cards", "price_match", "loyalty"],
        ("Gift Card Terms", "1.0", "4. Loss, Theft, and Fraud"),
        ("Price Match Policy", "1.0", "4. Repeated or Suspicious Requests"),
        ("Points Expiry Policy", "1.0", "5. Account Transfers and Closures"))

    add("ambiguous", "How is a dispute resolved?",
        "Depends which kind: a chargeback dispute is filed through the payment processor's merchant portal with gathered evidence, a delivery dispute is resolved via a carrier trace request, and a price-match dispute comes down to a store associate's discretion over whether a competitor listing is genuine -- three unrelated processes.",
        True, "hard", ["ambiguous", "chargebacks", "shipping", "price_match"],
        ("Chargeback Handling Runbook", None, None, "Filing the Dispute"),
        ("Delivery Dispute Runbook", None, None, "file a trace request"),
        ("Price Match Policy", "1.0", "3. Process"))

    add("ambiguous", "What's required to file a claim?",
        "Depends which kind: a warranty claim requires a matching product serial number, a chargeback claim requires evidence gathered within 5 business days of the notice, and a price-match request requires proof like a current ad or the competitor's live product page.",
        True, "hard", ["ambiguous", "warranty", "chargebacks", "price_match"],
        ("Warranty Policy", "1.0", None, "requires the product's serial number"),
        ("Chargeback Handling Runbook", None, None, "Within 5 business days"),
        ("Price Match Policy", "1.0", "1. Eligibility"))

    add("ambiguous", "Does it affect tier status?",
        "Depends on the event: a points refund from a return does not count toward tier-qualifying spend since no new spend occurred, but tier demotion for falling below a threshold only takes effect at the next quarterly review, not immediately -- two different tier-status rules that sound related but aren't.",
        True, "hard", ["ambiguous", "loyalty"],
        ("Loyalty Program Rules", "2.0", "4. Points Handling on Returns"),
        ("Loyalty Program Rules", "2.0", "1. Tier Structure"))

    add("ambiguous", "What's the replacement process?",
        "Depends which kind: a warranty replacement is decided by the servicing technician based on parts availability and cost, a misdelivered-package replacement ships immediately at no cost with no investigation required, and a lost gift card replacement requires proof of the original purchase -- three unrelated \"replacement\" procedures.",
        True, "hard", ["ambiguous", "warranty", "shipping", "gift_cards"],
        ("Warranty Policy", "1.0", None, "Repair vs. Replacement Determination"),
        ("Delivery Dispute Runbook", None, None, "Misdelivered Package Cases"),
        ("Gift Card Terms", "1.0", "4. Loss, Theft, and Fraud"))

    add("ambiguous", "Is the refund issued to the original payment method?",
        "Depends on how the item was bought: an item purchased with a gift card is refunded to a (possibly new) gift card, never a different method; a price-match difference is always refunded in cash/card, never as points; and the general policy refunds to the original payment method where possible.",
        True, "hard", ["ambiguous", "returns", "gift_cards", "price_match"],
        ("Gift Card Terms", "1.0", "5. Returns Involving Gift Cards"),
        ("Price Match Policy", "1.0", "5. Refund of the Difference"),
        ("Returns Policy", "3.0", "4. Refund Method"))

    # ---------------------------------------------------------- version-sensitive (4)
    add("version_sensitive", "What is the current GOLD_TIER annual spend threshold?",
        "$1,500 under the current Loyalty Program Rules v2.0 -- up from $1,000 under the superseded v1.0.",
        True, "medium", ["version_sensitive", "loyalty"],
        ("Loyalty Program Rules", "2.0", "1. Tier Structure"))

    add("version_sensitive", "What is the current return window for an item discounted 20% or more?",
        "14 days under the current Returns Policy v3.0 -- shortened from the 30-day (i.e. standard) window under the superseded v2.0, specifically to reduce return-driven margin loss on clearance-priced inventory.",
        True, "medium", ["version_sensitive", "returns"],
        ("Returns Policy", "3.0", "3. Exceptions > 3.1 Electronics; 3.2 Discounted Items"))

    add("version_sensitive", "How many months after being earned do loyalty points currently expire?",
        "18 months under the current Loyalty Program Rules v2.0 -- extended from 12 months under the superseded v1.0.",
        True, "medium", ["version_sensitive", "loyalty"],
        ("Loyalty Program Rules", "2.0", "5. Points Expiry"))

    add("version_sensitive", "Can a clearance-tagged item be exchanged for a different size or color outside the standard return window?",
        "Yes, under the current Returns Exception Matrix v2.0 -- this exception is new in v2.0; associates were incorrectly declining legitimate size exchanges under the v1.0 matrix before this clarification was added (v1.0 itself was never persisted as its own document, only referenced retrospectively).",
        True, "medium", ["version_sensitive", "returns"],
        ("Returns Exception Matrix", "2.0", "3. New in This Version: Clearance-Tagged Item Exception"))

    # ---------------------------------------------------------- version-sensitive, continued (T-M4.13, +3)
    add("version_sensitive", "Under the current loyalty program rules, how quickly is the points portion of a return refunded?",
        "Within 24 hours under the current Loyalty Program Rules v2.0 -- down from within 5 business days under the superseded v1.0.",
        True, "medium", ["version_sensitive", "loyalty"],
        ("Loyalty Program Rules", "2.0", "4. Points Handling on Returns"))

    add("version_sensitive", "Under the current Returns Policy, does a restocking fee apply to an opened electronics item accepted outside the standard return window?",
        "No -- the current Returns Policy v3.0's electronics exception doesn't mention a restocking fee at all, unlike the superseded v2.0, which specified a fee of up to 15% at associate discretion.",
        True, "medium", ["version_sensitive", "returns"],
        ("Returns Policy", "3.0", "3. Exceptions > 3.1 Electronics; 3.2 Discounted Items"))

    add("version_sensitive", "Under the current loyalty program rules, is a promotional discount applied proportionally when calculating a points refund on an item bought with blended points and card?",
        "Yes -- this is an explicit step added in Loyalty Program Rules v2.0 Section 4 that wasn't present under the superseded v1.0's points-handling-on-returns section.",
        True, "medium", ["version_sensitive", "loyalty"],
        ("Loyalty Program Rules", "2.0", "4. Points Handling on Returns"))

    counts = Counter(q["category"] for q in questions)
    for cat, n in EXPECTED_COUNTS.items():
        assert counts[cat] == n, f"{cat}: expected {n}, got {counts[cat]}"
    assert len(questions) == 151, f"expected 151 total, got {len(questions)}"

    return {"version": 1, "questions": questions}


def main() -> None:
    pool = get_pool()
    data = build(pool)
    OUT_PATH.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True, width=100))
    counts = Counter(q["category"] for q in data["questions"])
    print(f"wrote {OUT_PATH} -- {len(data['questions'])} questions, {dict(counts)}")


if __name__ == "__main__":
    main()
