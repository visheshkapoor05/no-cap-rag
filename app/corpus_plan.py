"""
Figures out *what* to ingest and with *what metadata*, from the corpus
layout on disk — the discovery step the CLI (T-M1.9) needs that the API
(T-M1.8) doesn't, since an API caller supplies `type`/`title` directly
instead of them being derived from a directory of files. See ../ANALOGY.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "corpus"
MANIFEST_PATH = CORPUS_DIR / "MANIFEST.md"

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_MANIFEST_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(https?://\S+?)\s*\|", re.MULTILINE
)

# The 13 mixed/ files carry no embedded frontmatter — PDF/DOCX/TXT aren't
# markdown, so there's nowhere to put a YAML block. This mirrors exactly
# what corpus/synthetic/INDEX.md already documents per file; kept here as
# explicit, reviewable data rather than parsed out of INDEX.md's prose
# tables, which would be a second, fragile way to read the same facts.
_MIXED_METADATA: dict[str, dict[str, Any]] = {
    "warranty-policy-v1.0.pdf": {"type": "customer_policy", "title": "Warranty Policy", "policy_id": "WAR-POL-001", "version": "1.0"},
    "shipping-policy.docx": {"type": "customer_policy", "title": "Shipping Policy", "policy_id": "SHIP-POL-001"},
    "campaign-brief-bogo.pdf": {"type": "promotions", "title": "Campaign Brief — BOGO", "policy_id": "PROMO-POL-001"},
    "markdown-policy.docx": {"type": "promotions", "title": "Markdown Policy", "policy_id": "PROMO-POL-003"},
    "stock-take-sop.pdf": {"type": "store_sop", "title": "Stock Take SOP", "policy_id": "SOP-STOCK-005"},
    "pos-outage-postmortem.pdf": {"type": "incident", "title": "POS Outage Postmortem", "policy_id": "POS-ERR-3021"},
    "payment-gateway-failure-postmortem.docx": {"type": "incident", "title": "Payment Gateway Failure Postmortem", "policy_id": "POS-ERR-3045"},
    "inventory-sync-failure-postmortem.txt": {"type": "incident", "title": "Inventory Sync Failure Postmortem", "policy_id": "POS-ERR-3102"},
    "loyalty-double-credit-postmortem.pdf": {"type": "incident", "title": "Loyalty Double-Credit Postmortem", "policy_id": "POS-ERR-3210"},
    "delivery-dispute-runbook.docx": {"type": "runbook", "title": "Delivery Dispute Runbook", "policy_id": "RUN-DEL-002"},
    "chargeback-handling-runbook.pdf": {"type": "runbook", "title": "Chargeback Handling Runbook", "policy_id": "RUN-CHG-003"},
    "oms-choice-adr.docx": {"type": "adr", "title": "OMS Choice ADR", "policy_id": "ADR-001"},
    "loyalty-platform-choice-adr.txt": {"type": "adr", "title": "Loyalty Platform Choice ADR", "policy_id": "ADR-002"},
}


@dataclass(frozen=True)
class PlannedIngest:
    ref: str
    type: str
    title: str
    version: str | None = None
    effective_date: date | None = None
    frontmatter_id: str | None = None  # this document's own natural key, if it has one (clean/ only)
    supersedes_frontmatter_id: str | None = None  # the OLDER doc's natural key, if this one replaces it
    metadata: dict[str, Any] = field(default_factory=dict)


def plan_synthetic(corpus_dir: Path = CORPUS_DIR) -> list[PlannedIngest]:
    """The 28 synthetic documents. `clean/` metadata comes from real YAML
    frontmatter; `mixed/` metadata comes from `_MIXED_METADATA` above,
    since PDF/DOCX/TXT have nowhere to embed it."""
    plans: list[PlannedIngest] = []

    for path in sorted((corpus_dir / "synthetic" / "clean").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if not match:
            raise ValueError(f"{path} has no YAML frontmatter — every clean/ document should")
        fm = yaml.safe_load(match.group(1))
        plans.append(
            PlannedIngest(
                ref=str(path),
                type=fm["document_type"],
                title=fm["title"],
                version=str(fm["version"]) if fm.get("version") is not None else None,
                effective_date=fm.get("effective_date"),
                frontmatter_id=fm.get("id"),
                supersedes_frontmatter_id=fm.get("supersedes"),
                metadata={
                    "policy_id": fm.get("policy_id"),
                    "frontmatter_id": fm.get("id"),
                    "is_synthetic": True,
                },
            )
        )

    for path in sorted((corpus_dir / "synthetic" / "mixed").glob("*")):
        info = _MIXED_METADATA.get(path.name)
        if info is None:
            raise ValueError(f"{path.name} has no entry in _MIXED_METADATA — add one")
        plans.append(
            PlannedIngest(
                ref=str(path),
                type=info["type"],
                title=info["title"],
                version=info.get("version"),
                metadata={
                    "policy_id": info.get("policy_id"),
                    "is_synthetic": True,
                    "format": path.suffix.lstrip("."),
                },
            )
        )

    return plans


def plan_public(manifest_path: Path = MANIFEST_PATH) -> list[PlannedIngest]:
    """The 16 public URLs from MANIFEST.md's Half A table — fetched live,
    for real, via URLSource. Some are expected to fail (per T-M1.4's own
    findings: 3 geo-redirect, 1 403, 1 CAPTCHA) — that's the real world,
    not a bug in this function."""
    text = manifest_path.read_text(encoding="utf-8")
    return [
        PlannedIngest(
            ref=url,
            type="public_policy",
            title=f"{retailer} — {category}",
            metadata={"category": category, "retailer": retailer, "is_synthetic": False},
        )
        for category, retailer, url in _MANIFEST_ROW_RE.findall(text)
    ]
