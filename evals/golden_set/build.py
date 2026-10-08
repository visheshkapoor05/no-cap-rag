"""
Builds evals/golden_set/golden_set.yaml: 50 hand-authored questions. Every
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
    "factual_lookup": 15,
    "exact_identifier": 8,
    "multi_hop": 10,
    "unanswerable": 8,
    "ambiguous": 5,
    "version_sensitive": 4,
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

    counts = Counter(q["category"] for q in questions)
    for cat, n in EXPECTED_COUNTS.items():
        assert counts[cat] == n, f"{cat}: expected {n}, got {counts[cat]}"
    assert len(questions) == 50, f"expected 50 total, got {len(questions)}"

    return {"version": 1, "questions": questions}


def main() -> None:
    pool = get_pool()
    data = build(pool)
    OUT_PATH.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True, width=100))
    counts = Counter(q["category"] for q in data["questions"])
    print(f"wrote {OUT_PATH} -- {len(data['questions'])} questions, {dict(counts)}")


if __name__ == "__main__":
    main()
