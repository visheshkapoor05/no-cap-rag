# -*- coding: utf-8 -*-
"""
Regenerates the HTML fragment for the "no-cap-rag — Advanced RAG Build
Blueprint" artifact (the milestone tracker published at
https://claude.ai/code/artifact/efa1270a-9743-4c9f-844f-afd686181449).

Read docs/BLUEPRINT_ARTIFACT.md FIRST if you're updating this for a new
session -- it explains the whole design system (colors, layout, content
rules) and exactly how to republish without guessing or redesigning.

Usage:
    python3 scripts/build_blueprint_artifact.py
    -> writes scripts/blueprint_artifact.out.html (the Artifact tool's
       file_path input; republish with the SAME artifact url to update
       in place, never without url= or it mints a new link).

Before running: update TODAY below, and update any task's `done`/`commits`
fields to match learnings/*/TASKS.md's real current state -- this script
intentionally does NOT parse TASKS.md automatically (a human/session should
read the real file and transcribe deliberately, the same discipline that
built this data the first time, rather than risk silently mis-parsing free
-form markdown).
"""
import datetime
import os

OUT = os.path.join(os.path.dirname(__file__), "blueprint_artifact.out.html")

TODAY = datetime.date(2026, 10, 12)
START = datetime.date(2026, 8, 18)
END = datetime.date(2026, 11, 12)
SPAN = (END - START).days + 1

def off(d):
    return (d - START).days

TYPE_COLORS = {
    "LEARN": "#2a78d6", "PRACTICE": "#d97706", "DECIDE": "#7c3aed",
    "AUTHOR": "#db2777", "BUILD": "#92400e", "IMPLEMENT": "#0d9488",
    "API": "#4f46e5", "MEASURE": "#dc2626", "VERIFY": "#059669",
    "DOCS": "#64748b", "GIT": "#1e293b", "DOCKER": "#0891b2",
}
CODE_TYPES = {"IMPLEMENT", "API", "DOCKER", "GIT"}  # types that get a commit checklist

CSS = r"""
:root{
  --bg:#fdfefe; --bg-soft:#f2f7f6; --bg-card:#ffffff;
  --text:#1c2b29; --muted:#5b7370; --border:#dbe6e4;
  --p0:#5b7370; --p0-bg:#eef3f2; --p0-bd:#c3d2cf;
  --v1:#0d9488; --v1-bg:#e9f7f4; --v1-bd:#99f6e4; --v1-text:#0f6f64;
  --v2:#d9660b; --v2-bg:#fdf2e9; --v2-bd:#f6c393; --v2-text:#9a4f0d;
  --v3:#5b5bd6; --v3-bg:#eeeefb; --v3-bd:#c8c8f2; --v3-text:#40409e;
}
*{box-sizing:border-box;}
body{background:var(--bg-soft);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;line-height:1.55;margin:0;}
.wrap{max-width:1040px;margin:0 auto;padding:32px 20px 80px;}
h1{font-size:1.6rem;margin:0 0 6px;}
h2{font-size:1.2rem;margin:0 0 12px;}
h3{font-size:1rem;margin:20px 0 8px;color:var(--text);}
p{margin:0 0 10px;}
code{background:#eef1f5;border-radius:4px;padding:1px 5px;font-size:0.88em;}
hr{border:none;border-top:1px solid var(--border);margin:16px 0;}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:0.85em;}
th,td{border:1px solid var(--border);padding:6px 9px;text-align:left;}
th{background:var(--bg-soft);}
.table-wrap{overflow-x:auto;}

.header{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:24px 28px;margin-bottom:20px;}
.header .sub{color:var(--muted);margin-bottom:14px;}
.commit-pills{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;}
.commit-pills .pill{font-size:0.8rem;}
.rebase-note{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 16px;font-size:0.9em;color:#78350f;margin-top:8px;}
.rebase-note b{color:#92400e;}
.commit-note{background:var(--v1-bg);border:1px solid var(--v1-bd);border-radius:8px;padding:12px 16px;font-size:0.88em;color:var(--v1-text);margin-top:10px;}

.progress-wrap{margin-top:16px;}
.progress-bar{height:10px;border-radius:6px;background:var(--border);overflow:hidden;}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--v1),var(--v3));width:0%;transition:width .3s;}
.progress-label{font-size:0.82rem;color:var(--muted);margin-top:6px;}

.pill{display:inline-block;font-size:0.75rem;font-weight:600;letter-spacing:.02em;padding:3px 10px;border-radius:999px;border:1px solid var(--border);background:var(--bg-soft);}
.tier-pill-p0{background:var(--p0-bg);border-color:var(--p0-bd);color:var(--p0);}
.tier-pill-v1{background:var(--v1-bg);border-color:var(--v1-bd);color:var(--v1-text);}
.tier-pill-v2{background:var(--v2-bg);border-color:var(--v2-bd);color:var(--v2-text);}
.tier-pill-v3{background:var(--v3-bg);border-color:var(--v3-bd);color:var(--v3-text);}

.tag{display:inline-block;font-size:0.65rem;font-weight:700;letter-spacing:.03em;padding:2px 7px;border-radius:5px;color:var(--tag);background:color-mix(in srgb, var(--tag) 14%, white);border:1px solid color-mix(in srgb, var(--tag) 45%, white);vertical-align:1px;white-space:nowrap;}
.tag-legend{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:14px;padding-top:12px;border-top:1px dashed var(--border);}
.tag-legend-label{font-size:0.78rem;color:var(--muted);margin-right:4px;}

.timeline{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:20px 24px 24px;margin-bottom:24px;}
.tl-legend{display:flex;flex-wrap:wrap;gap:16px;font-size:0.8rem;color:var(--muted);margin-bottom:14px;}
.tl-legend span{display:flex;align-items:center;gap:6px;}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block;}
.sw-p0{background:var(--p0-bg);border:1px solid var(--p0);}
.sw-v1{background:var(--v1);}
.sw-v2{background:var(--v2);}
.sw-v3{background:var(--v3);}
.tl{display:flex;gap:10px;overflow-x:auto;}
.tl-labels{width:190px;flex-shrink:0;font-size:0.8rem;}
.tl-labels b{color:var(--text);}
.tl-labels .row{height:34px;display:flex;align-items:center;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tl-dates{width:120px;flex-shrink:0;font-size:0.74rem;color:var(--muted);}
.tl-dates .row{height:34px;display:flex;align-items:center;}
.month-row{height:22px;position:relative;}
.tl-canvas-wrap{flex:1;min-width:360px;}
.month-row .month-band{position:absolute;top:0;bottom:0;border-left:1px dashed var(--border);font-size:0.72rem;color:var(--muted);padding-left:6px;}
.tl-canvas{position:relative;border-top:1px solid var(--border);}
.bar{position:absolute;border-radius:5px;box-shadow:inset 0 0 0 1px rgba(0,0,0,0.06);}
.bar-p0{background:var(--p0-bg);border:2px dashed var(--p0);}
.bar-p0.complete{background:var(--p0);border:2px solid var(--p0);opacity:0.55;}
.bar-v1{background:var(--v1);}
.bar-v2{background:var(--v2);}
.bar-v3{background:var(--v3);}
.marker{position:absolute;top:0;bottom:0;border-left:2px dashed;}
.marker-label{position:absolute;top:-20px;left:2px;font-size:0.7rem;font-weight:700;background:#fff;padding:0 3px;white-space:nowrap;}
.today-line{position:absolute;top:0;bottom:0;left:0;border-left:2px solid #dc2626;z-index:2;}
.today-line span{position:absolute;bottom:-18px;left:2px;font-size:0.68rem;font-weight:700;color:#dc2626;white-space:nowrap;}

.ms{background:var(--bg-card);border:1px solid var(--border);border-left-width:5px;border-radius:10px;padding:20px 24px;margin-bottom:16px;}
.ms.tier-p0{border-left-color:var(--p0);}
.ms.tier-v1{border-left-color:var(--v1);}
.ms.tier-v2{border-left-color:var(--v2);}
.ms.tier-v3{border-left-color:var(--v3);}
.ms-head{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;}
.ms-head-left{display:flex;gap:8px;align-items:center;}
.ms-date{font-size:0.85rem;color:var(--muted);font-weight:600;}
.ms h2{font-size:1.15rem;}
.ms-goal{color:var(--muted);font-size:0.92rem;margin:4px 0 14px;}
.sec-progress{font-size:0.72rem;color:var(--muted);font-weight:600;}
.ms-section-title{font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.03em;color:var(--muted);margin:18px 0 6px;}

.flow{display:flex;align-items:center;flex-wrap:wrap;gap:0;margin:10px 0;font-size:0.8rem;}
.flow-box{background:var(--bg-soft);border:1px solid var(--border);border-radius:8px;padding:7px 11px;text-align:center;min-width:100px;}
.flow-box.accent{background:var(--v1-bg);border-color:var(--v1-bd);}
.flow-box b{display:block;font-size:0.8rem;}
.flow-box span{display:block;font-size:0.7rem;color:var(--muted);margin-top:2px;}
.flow-arrow{color:var(--muted);font-size:1.1rem;padding:0 5px;}
.flow-branch{display:flex;flex-direction:column;gap:6px;align-items:center;}
.flow-branch-row{display:flex;gap:16px;align-items:flex-start;justify-content:center;}
.flow-branch-col{display:flex;flex-direction:column;align-items:center;gap:0;}
.flow-branch-label{font-size:0.68rem;color:var(--muted);font-weight:700;margin-bottom:2px;text-transform:uppercase;}
.flow-diamond{background:var(--v2-bg);border:1px solid var(--v2-bd);color:var(--v2-text);border-radius:8px;padding:7px 11px;text-align:center;font-size:0.78rem;font-weight:600;min-width:90px;}
.flow-loop{border:1px dashed var(--muted);border-radius:8px;padding:4px 8px;font-size:0.68rem;color:var(--muted);}
.flow-caption{font-size:0.74rem;color:var(--muted);margin:2px 0 14px;font-style:italic;}

ul.task-list{list-style:none;padding-left:0;margin:6px 0 16px;}
.task-list-item{position:relative;padding:7px 4px 7px 30px;border-bottom:1px dashed var(--border);}
.task-list-item:last-child{border-bottom:none;}
.task-list-item > input[type=checkbox]{position:absolute;left:0;top:10px;width:16px;height:16px;cursor:pointer;accent-color:var(--v1);}
.task-head{display:flex;align-items:baseline;gap:7px;flex-wrap:wrap;}
.tid{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:0.78rem;color:var(--muted);}
.ttitle{font-weight:600;font-size:0.93rem;}
.task-what{font-size:0.86rem;color:var(--text);margin:4px 0 2px;}

.why-box{background:#f7fbfb;border:1px solid var(--v1-bd);border-radius:8px;margin:8px 0 2px;padding:0;}
.why-box summary{cursor:pointer;padding:8px 12px;font-weight:600;font-size:0.82rem;color:var(--v1-text);list-style:revert;}
.why-box summary:hover{background:var(--v1-bg);}
.why-inner{padding:2px 14px 12px;font-size:0.87rem;}
.why-inner p{margin:6px 0;}
.why-inner b{color:var(--text);}

.commit-list{list-style:none;padding:0;margin:8px 0 0;}
.commit-list li{display:flex;align-items:center;gap:7px;font-size:0.8rem;padding:3px 0;color:var(--muted);}
.commit-list input[type=checkbox]{width:13px;height:13px;accent-color:var(--v1);}
.commit-hash{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:0.78em;background:var(--bg-soft);padding:1px 5px;border-radius:4px;color:var(--text);}
.commit-none{font-size:0.78rem;color:var(--muted);font-style:italic;margin-top:6px;}

footer{text-align:center;color:var(--muted);font-size:0.8rem;margin-top:24px;}
"""

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def tag(t):
    c = TYPE_COLORS[t]
    return f'<span class="tag" style="--tag:{c};">{t}</span>'

# ===========================================================================
# Flowchart builders
# ===========================================================================

def flow_linear(steps, accent_last=False):
    parts = []
    n = len(steps)
    for i, (name, sub) in enumerate(steps):
        cls = "flow-box accent" if (accent_last and i == n - 1) else "flow-box"
        parts.append(f'<div class="{cls}"><b>{esc(name)}</b>{f"<span>{esc(sub)}</span>" if sub else ""}</div>')
        if i < n - 1:
            parts.append('<span class="flow-arrow">&rarr;</span>')
    return f'<div class="flow">{"".join(parts)}</div>'

def flow_parallel_then_merge(before, branches, after):
    """before: (name,sub) single box feeding into N parallel branch boxes, which
    then merge into `after` (list of (name,sub))."""
    cols = "".join(
        f'<div class="flow-branch-col"><div class="flow-branch-label">{esc(label)}</div>'
        f'<div class="flow-box">{"".join(f"<b>{esc(n)}</b>" if i==0 else f"<span>{esc(n)}</span>" for i,n in enumerate(box))}</div></div>'
        for label, box in branches
    )
    before_html = f'<div class="flow-box"><b>{esc(before[0])}</b>{f"<span>{esc(before[1])}</span>" if before[1] else ""}</div>'
    after_html = "".join(
        (f'<span class="flow-arrow">&rarr;</span>' if i else '') +
        f'<div class="flow-box accent"><b>{esc(n)}</b>{f"<span>{esc(s)}</span>" if s else ""}</div>'
        for i, (n, s) in enumerate(after)
    )
    return f"""<div class="flow-branch">
  <div class="flow-branch-row">{before_html}<span class="flow-arrow">&rarr;</span>{cols}</div>
  <span class="flow-arrow" style="transform:rotate(90deg);">&rarr;</span>
  <div class="flow">{after_html}</div>
</div>"""

def flow_decision_loop(before, diamond, yes_label, yes_box, no_label, no_box):
    return f"""<div class="flow-branch">
  <div class="flow">
    <div class="flow-box"><b>{esc(before[0])}</b>{f"<span>{esc(before[1])}</span>" if before[1] else ""}</div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-diamond">{esc(diamond)}</div>
  </div>
  <div class="flow-branch-row" style="margin-top:6px;">
    <div class="flow-branch-col"><div class="flow-branch-label">{esc(yes_label)}</div>
      <div class="flow-box">{"".join(f"<b>{esc(n)}</b>" if i==0 else f"<span>{esc(n)}</span>" for i,n in enumerate(yes_box))}</div>
      <div class="flow-loop">&#8635; loop back (bounded)</div>
    </div>
    <div class="flow-branch-col"><div class="flow-branch-label">{esc(no_label)}</div>
      <div class="flow-box accent">{"".join(f"<b>{esc(n)}</b>" if i==0 else f"<span>{esc(n)}</span>" for i,n in enumerate(no_box))}</div>
    </div>
  </div>
</div>"""

# ===========================================================================
# Task data: (id, type, title, what, layman, technical, done, commits, table_html)
# commits: list of (hash, msg) or [] . table_html: raw HTML string or None.
# ===========================================================================

def T(id_, type_, title, what, layman, technical, done, commits=None, table=None):
    return dict(id=id_, type=type_, title=title, what=what, layman=layman,
                technical=technical, done=done, commits=commits or [], table=table)

P0_TASKS = [
    T("T-P0.1","IMPLEMENT","FastAPI app factory + lifespan",
      "Build create_app() with a startup/shutdown lifecycle hook.",
      "Sets up the web server so it can cleanly open things like database connections when the app starts, and close them when it stops — instead of opening a fresh connection for every single visitor.",
      "create_app() with an asynccontextmanager lifespan. Later milestones (M1 Postgres, M3 Milvus) open their connections here, once at startup rather than per-request.",
      True),
    T("T-P0.2","IMPLEMENT","Typed config via Pydantic Settings",
      "Load every setting (DB host, passwords, ports) through validated, typed config classes.",
      "All the app's settings get checked for correctness the moment it starts — a typo in a setting is caught immediately, not three requests in.",
      "Nested sub-settings for Postgres and Redis; @lru_cache singleton. Invalid config fails at startup, not mid-request.",
      True),
    T("T-P0.3","IMPLEMENT","Structured JSON logging + request-ID correlation",
      "Tag every log line from one request with the same unique ID.",
      "You can follow one user's entire request through the logs by searching for one ID, instead of guessing which log lines belong together.",
      "ContextVar-based request ID stamped on every log line. The cheap precursor to M9's real OpenTelemetry tracing.",
      True),
    T("T-P0.4","IMPLEMENT","Exception handlers + structured errors",
      "Catch errors centrally and turn them into safe, structured responses.",
      "When something breaks, the user gets a clear, safe error message — never raw internal details (stack traces, file paths) leaked to them.",
      "Named AppErrors explain themselves; unexpected exceptions log fully but never leak internals to the caller.",
      True),
    T("T-P0.5","DOCKER","Docker Compose: api + postgres + redis",
      "Wire the API, database, and cache together so one command boots all three in the right order.",
      "One command boots the whole app plus its database and cache, and the app automatically waits until the database is actually ready before it tries to start.",
      "Healthchecks on all three; depends_on: condition: service_healthy so the API can't start against a Postgres that isn't accepting connections yet.",
      True),
    T("T-P0.6","DOCKER","Dockerfile with layer-cache-aware ordering",
      "Order the Dockerfile so dependency installs are cached separately from app code.",
      "Rebuilding the app after a small code change is fast, because the (slow) dependency install step only reruns when dependencies actually change.",
      "Dependencies copied and installed before app code, so a code edit doesn't trigger a full reinstall.",
      True),
    T("T-P0.7","IMPLEMENT","pytest harness + /health tests",
      "Set up automated testing and write the first real test against a live endpoint.",
      "An automated test confirms the app actually starts and responds correctly — breakage gets caught immediately by CI, not discovered later by a human.",
      "conftest.py with a TestClient fixture. Verified live that request IDs round-trip into response headers.",
      True),
    T("T-P0.8","GIT","git init, verify .gitignore, first commit",
      "Initialize git, double-check secrets/junk are excluded, make the first commit.",
      "Before anything gets saved to version control forever, double-check secrets and junk files are excluded — once a secret is committed, it never truly disappears from history.",
      "Before the first git add: run git status and confirm .env, .venv/ and __pycache__ are all ignored.",
      True),
    T("T-P0.9","GIT","Create the GitHub repo and push main",
      "Push the code to a new public GitHub repository.",
      "The project becomes publicly visible and discoverable on GitHub, with proper topics so people searching for RAG projects can find it.",
      "Public. Repo description + topics (rag, retrieval, evaluation, llm) — these are how the project gets found.",
      True),
    T("T-P0.10","GIT","Branch protection + PR workflow",
      "Protect the main branch so every change requires a reviewed pull request.",
      "Nobody — including the author — can push straight to the main branch. Every change has to go through a reviewed pull request first.",
      "Protect main, require CI to pass. Forces the per-milestone branch → PR → merge loop instead of committing straight to main.",
      True),
    T("T-P0.11","VERIFY","Confirm CI runs green on GitHub",
      "Prove CI actually catches failures by deliberately breaking something.",
      "Prove the automated checks actually work by watching them pass, then deliberately breaking something and watching them correctly catch it and fail.",
      "Then deliberately break a test, push, and watch it go red. A CI badge that has never actually failed proves nothing.",
      True),
    T("T-P0.12","DOCS","LICENSE + README skeleton + CI badge",
      "Add a license and a real front-page README.",
      "The project gets a license and a front page explaining what it is — and, importantly, what it deliberately is not.",
      "MIT or Apache-2.0. README states what this is and what it deliberately isn't (\"not a chat-with-your-PDFs demo\") from day one.",
      True),
    T("T-P0.13","DOCS","Commit the planning documents",
      "Save the Blueprint, Decisions log, Analogy doc, and PRD into the repo.",
      "The actual plan — this Blueprint, the decisions log, the architecture notes — gets saved into the repo as real, citable documents, not left in someone's notes app.",
      "BLUEPRINT.md, DECISIONS.md, ANALOGY.md, the PRD PDF and docs/architecture.jpg. The PRD names \"Architecture + PRD\" as a portfolio deliverable.",
      True),
]

M1_TASKS = [
    T("T-M1.1","LEARN","Corpus and evaluation-set design",
      "Research what makes a document collection good for evaluation specifically.",
      "Research what actually makes a good *test* dataset for measuring a search system — not just any pile of documents.",
      "What makes a corpus good for evaluation specifically, not just retrieval; why an unrepresentative corpus silently invalidates every downstream metric.",
      True),
    T("T-M1.2","DECIDE","Write corpus/MANIFEST.md",
      "Plan every document, its relationships, and licensing status before writing any of it.",
      "Plan out exactly which documents will exist and how they relate to each other — before writing a single one.",
      "Exact public URLs with licence/terms status for each · synthetic inventory by category · the three planned version pairs · the five planned cross-document dependencies.",
      True),
    T("T-M1.3","AUTHOR","Write the synthetic corpus (28 documents)",
      "Hand-write 28 realistic fake retail policy documents covering returns, loyalty, promotions, SOPs, incidents, runbooks, ADRs, and staff policies.",
      "Hand-write 28 realistic but fake retail policy documents — this is the fake data the whole project gets tested against.",
      "Split clean/ (15 .md) vs. mixed/ (13 .pdf/.docx/.txt). Every document ≥400 tokens, SYNTHETIC-labelled in text and metadata. Built in: exact identifiers, ≥3 contradicting version pairs, ≥5 cross-document dependencies.",
      True),
    T("T-M1.4","BUILD","Collect the public documents (15–25)",
      "Gather 16 real, publicly-available retail policy pages from the actual internet.",
      "Gather 16 real, publicly-available retail policy pages from the actual internet to mix in with the fake ones.",
      "16/16 URLs attempted, all 8 categories covered, stored as paraphrased summary + source_url/fetched_at provenance. 5/16 needed search-engine recovery after a blocked direct fetch (geo-redirect, 403, CAPTCHA).",
      True),
    T("T-M1.5","IMPLEMENT","Source interface + URL and file adapters",
      "Build the code that reads a document from a URL or local file, across 4 formats.",
      "Build the code that can read a document whether it comes from a web link or a local file, in any of 4 formats (PDF/Word/HTML/text).",
      "app/ingestion/: source.py (Source ABC, RawDocument, FetchStatus enum), extract.py (pdftotext -layout, python-docx, stripped HTML), url_source.py, file_source.py. 11 tests.",
      True),
    T("T-M1.6","IMPLEMENT","Document registry in Postgres",
      "Build the documents table and the connection pool + migration runner.",
      "Build the database table that keeps a permanent record of every document ever ingested.",
      "migrations/0001_create_documents_table.sql, unique index on content_hash. app/core/db.py adds a lazy connection pool + idempotent migrate() runner. 5 integration tests against real Postgres.",
      True),
    T("T-M1.7","IMPLEMENT","Content-hash idempotency",
      "Hash each document's extracted text and skip re-inserting anything already seen.",
      "If you accidentally ingest the exact same document twice, the system recognizes it and skips the duplicate instead of storing it twice.",
      "compute_content_hash(text), sha256 over extracted text (never raw bytes). ingest_document() checks find_by_content_hash first. Proven: different raw_bytes, identical text → still recognized as duplicate.",
      True),
    T("T-M1.8","API","POST /documents/ingest and GET /documents/{id}",
      "Build the first real API endpoints to submit and look up documents.",
      "The first real feature a user could call: submit a document by URL or path, or look one up by its ID.",
      "Picks URLSource/FileSource by ref shape, runs T-M1.5→T-M1.7's pipeline. 201 on genuine insert, 200 on repeat. Later extended with POST /documents/upload for real file attachments (D-017).",
      True),
    T("T-M1.9","IMPLEMENT","Ingestion CLI",
      "Build a one-command rebuild of the entire corpus into Postgres.",
      "One terminal command rebuilds the entire document database from scratch, using only what's committed in the repo.",
      "app/corpus_plan.py discovers what to ingest; app/cli.py's ingest_plan() calls the same ingest_document() the API uses. python -m app.cli ingest --scope {synthetic,public,all}.",
      True),
    T("T-M1.10","MEASURE","Prove idempotency and provenance completeness",
      "Write a committed automated test proving no duplicates and no missing metadata.",
      "An automated test proves re-running ingestion never creates duplicates, and every document has its required metadata filled in.",
      "A committed pytest: run ingestion twice, assert row counts match. Query for any NULL content_hash/title/type, assert empty. Re-runs on every future PR via CI.",
      True),
    T("T-M1.11","DOCS","README corpus section",
      "Document the corpus structure and rebuild commands in the README.",
      "Explain in the README what's in the document collection and how to rebuild it.",
      "Added a Corpus section covering the public/synthetic split, clean/mixed split and why, and CLI rebuild commands.",
      True),
    T("T-M1.12a","GIT","Branch → push feat/the-mailroom-opens",
      "Push the M1 work to its own branch.",
      "Save the M1 work onto its own branch in git.",
      "Pushed as two commits (implementation, then project rename) to origin/feat/the-mailroom-opens.",
      True),
    T("T-M1.12b","GIT","PR → merge feat/the-mailroom-opens into main",
      "Open a PR, confirm CI is green, review the diff, merge.",
      "Open a pull request for review, confirm the automated checks pass, then merge the work into the main codebase.",
      "PR #3. CI green, diff read and scanned for stray junk/leaked credentials before merging (82 files, all expected).",
      True),
]

M2_TASKS = [
    T("T-M2.1","LEARN","Write up all six chunking strategies",
      "Research fixed-size, recursive, semantic, structure-aware, contextual-prefix, and parent-document chunking.",
      "Research the six different ways to split a long document into smaller searchable pieces, and understand when each works and when it fails.",
      "Fixed-size, recursive character, semantic/percentile, structure-aware (the choice), contextual prefix, parent-document/small-to-big (deferred to M4).",
      True),
    T("T-M2.2","DECIDE","Record the choice with a falsifiable expectation",
      "Write down a testable prediction before running the real experiment.",
      "Write down, in advance, a specific prediction that could turn out to be wrong — so the later experiment actually tests something real.",
      "\"Structure-aware should beat fixed-size on Recall@5. If it doesn't, my model of this corpus is wrong.\" Recorded before the real M3 measurement.",
      True),
    T("T-M2.3","PRACTICE","Chunk 3 documents three ways, read the boundaries",
      "Manually run 3 real documents through different splitters and inspect the cut points.",
      "Manually run 3 real documents through different splitting methods and look at the actual cut points to see which one damages the text.",
      "practice/02-.../compare_chunking.py. Found the concrete case: fixed-size severs \"this is not a blanket denial\" from its own clarifying explanation; structure-aware keeps it whole.",
      True),
    T("T-M2.4","IMPLEMENT","Structure-aware chunker with token guards",
      "Build the real chunker that splits at headings with min/max token safety limits.",
      "Build the real code that splits documents at their natural headings, with safety limits so no piece is too short or too long to be useful.",
      "app/chunking/chunker.py. Splits at every heading level. MIN=40/MAX=350 tokens. Oversized leaves fall back to paragraph/sentence splitting; undersized merge into a neighbour. 23 tests.",
      True),
    T("T-M2.5","IMPLEMENT","Contextual prefix + full chunk schema",
      "Prepend a self-contained label to every chunk and build the full Postgres chunks table.",
      "Every chunk gets a short label prepended (like \"Returns Policy v3.0 → Section 1\") so it still makes complete sense entirely on its own.",
      "app/chunking/contextual.py (ContextualChunk, build_contextual_prefix) + the chunks table (8 fields, embedding_id/sparse_terms reserved for M3). 6 tests.",
      True),
    T("T-M2.6","IMPLEMENT","Embedding cache keyed on hash(text + model_id)",
      "Save every AI-generated vector to disk so identical text is never re-embedded.",
      "Once a piece of text has been turned into a vector by the AI, that result is saved to disk forever — so the same text is never (expensively) re-processed twice.",
      "app/embeddings/cache.py — plain sqlite3, one row per sha256(text+model_id), vector as a pickled blob. Disk-backed, gitignored. 5 tests including a true cross-process hit.",
      True),
    T("T-M2.7","LEARN","Recall@K and MRR",
      "Hand-compute the two foundational retrieval metrics on a toy 5-question set.",
      "Learn the two main ways to score how good a search result list is: \"did it find the right stuff at all\" and \"how high up was the first right answer.\"",
      "Hand-computed on a toy 5-query set, K=3. Found: the unanswerable question is a genuine 0/0 (excluded from the average); version-sensitive is a deliberate trap for stale chunks. Recall@3=0.875, MRR=0.625.",
      True),
    T("T-M2.8","IMPLEMENT","recall_at_k() and mrr(), hand-written",
      "Turn the two formulas into real, unit-tested code.",
      "Turn the two scoring formulas from the previous task into real, tested code — not a library call.",
      "~15 lines each, hand-written not a library. Both return None (not 0.0) when relevant is empty. 9 tests asserted against the exact hand-computed toy numbers.",
      True),
    T("T-M2.9","AUTHOR","Write the 50-question seed golden set",
      "Hand-write 50 labelled test questions across 6 categories.",
      "Hand-write 50 test questions, each labelled with exactly which document chunk contains the correct answer — this becomes the official exam the search system gets graded against.",
      "6 categories, references resolved by natural key (D-015), not frozen UUIDs — a frozen UUID goes stale the moment the corpus is re-ingested, since gen_random_uuid() assigns a new id every insert.",
      True, None,
      """<div class="table-wrap"><table><thead><tr><th>Category</th><th>n</th><th>Example</th></tr></thead><tbody>
<tr><td>Factual lookup</td><td>15</td><td>"How many days do I have to return an unopened item?"</td></tr>
<tr><td>Exact identifier</td><td>8</td><td>"What does error code POS-ERR-3021 mean?" <i>(the BM25-vs-dense discriminator)</i></td></tr>
<tr><td>Multi-hop</td><td>10</td><td>"If a Gold member returns a discounted item bought partly with points, what happens to the points?"</td></tr>
<tr><td>Unanswerable</td><td>8</td><td>"What is the policy on cryptocurrency payments?" <i>(must abstain, not invent)</i></td></tr>
<tr><td>Ambiguous</td><td>5</td><td>"What's the return window?" — differs by category</td></tr>
<tr><td>Version-sensitive</td><td>4</td><td>"What is the current Gold tier threshold?" — v1.0 and v2.0 disagree</td></tr>
</tbody></table></div>"""),
    T("T-M2.10","MEASURE","Chunk statistics",
      "Measure real chunk-size distribution, orphan rate, and section_path coverage on the full corpus.",
      "Check the real numbers on the full document set: are chunks too short, too long, or missing their section labels?",
      "149 chunks, 28 docs. MIN/MAX guards hold with zero violations. Orphan rate 2.7% (4/149). section_path resolves for 100% of chunks that could possibly have one.",
      True),
    T("T-M2.11","VERIFY","Prove the embedding cache works",
      "Run the real corpus through embedding twice and prove the second run makes zero API calls.",
      "Actually run the whole corpus through the AI embedding step twice, and prove the second run makes zero paid API calls.",
      "test_embedding_the_real_full_corpus_twice_makes_zero_calls_the_second_time — a brand-new EmbeddingCache instance, the real cross-run scenario. Pass 1: 149/149 misses. Pass 2: 0 calls.",
      True),
    T("T-M2.12","DOCS","Start EVALUATION.md",
      "Document the golden-set methodology and its known limitations.",
      "Document how the test questions were written and labelled, plus an honest list of its weaknesses.",
      "Schema + natural-key design explained, all 6 categories with what each tests. Known gap found while writing: 0/50 questions reference the public/ documents.",
      True),
    T("T-M2.13","GIT","Branch → PR → merge feat/m2-chunking-golden-set",
      "Save and merge all the M2 work.",
      "Save and merge all the M2 work to the main codebase.",
      "Golden set committed as a data file. Hit a real GitHub quirk: renaming a branch auto-closed its open PR — recovered by opening a fresh one (#5). Merged via a real merge commit.",
      True),
]

M3_EXPERIMENT_TABLE = """<div class="table-wrap"><table><thead><tr><th>Config</th><th>Recall@1</th><th>Recall@5</th><th>Recall@10</th><th>MRR</th></tr></thead><tbody>
<tr><td>Dense only</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>
<tr><td>BM25 only</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>
<tr><td>Hybrid + RRF</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>
<tr><td>Hybrid + weighted</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>
</tbody></table></div><p class="flow-caption">Not yet measured — this is the actual table T-M3.12 will fill in, pulled directly from TASKS.md.</p>"""

M3_TASKS = [
    T("T-M3.1","LEARN","BM25 mechanics, worked example on 3 toy documents",
      "Learn IDF, TF saturation (k1), and length normalization (b) with a real worked example.",
      "Learn the classic keyword-search scoring formula: rare words matter more than common ones, repeating a word has diminishing returns, and long documents don't get an unfair advantage.",
      "IDF (why POS-ERR-3021 is powerful, \"policy\" is nearly worthless), TF saturation (k1), length normalization (b). Full worked example: dense vs TF-IDF vs BM25 on an exact-identifier query, with the annotated formula diagram.",
      True),
    T("T-M3.2","LEARN","RRF vs. weighted fusion; the normalization problem",
      "Learn why raw scores from two different retrievers can't be added directly, and how RRF sidesteps it.",
      "Learn why you can't just add two different search engines' scores together directly, and the simple trick (using rank position instead of raw score) that sidesteps the whole problem.",
      "Bounded cosine similarity + unbounded BM25 scores can't combine without normalization. RRF (Σ 1/(k+rank)) uses rank only. Doc X/doc Y worked example, k-crossover chart (flips at k≈13.3).",
      True),
    T("T-M3.3","PRACTICE","Implement RRF from scratch on two hardcoded lists",
      "Hand-code RRF on two made-up ranked lists and sweep the k constant.",
      "Hand-code the rank-fusion formula on two made-up ranked lists and watch how changing one constant (k) changes the winner.",
      "practice/03-.../rrf_practice.py. Verified against the hand-computed reference (k=60: X=0.0255/Y=0.0286; k=1: X=0.520/Y=0.182). Swept k=1..100, found the real crossover at k=14.",
      True),
    T("T-M3.4","PRACTICE","Hand-run 5 queries: dense vs. BM25",
      "Predict dense-vs-BM25 winners for 5 real questions before checking.",
      "Before building the real search system, manually predict — for 5 real questions — whether keyword search or AI-meaning search will win, then check.",
      "BM25 hand-rolled over the real 161-chunk corpus. 3 of 5 predictions were wrong — the valuable ones: a vocabulary mismatch inside BM25 itself, a stale-version chunk outranking the current one, a multi-hop query BM25 unexpectedly nailed.",
      True),
    T("T-M3.5","DOCKER","Add Milvus to Docker Compose",
      "Add Milvus plus its required etcd and MinIO services to Compose.",
      "Add the specialized database that stores and searches AI-generated vectors — which itself needs two more supporting services to actually run.",
      "milvus-etcd, milvus-minio, milvus-volume-init, milvus standalone v3.0.2, all with real healthchecks. api's depends_on extended to wait for Milvus healthy. Verified: full stack boots in dependency order.",
      True, [("c7bb56b","feat(T-M3.5): add Milvus (etcd + MinIO + standalone) to Docker Compose")]),
    T("T-M3.6","IMPLEMENT","Milvus collection schema + connection lifecycle",
      "Design the vector collection schema and open the connection once at startup.",
      "Design the actual shelving plan for the vector database: what gets stored, and open that connection once when the app starts, not on every request.",
      "Collection chunk_embeddings: chunk_id/document_id (VARCHAR(36)) + embedding (FLOAT_VECTOR, dim=768). FLAT index + COSINE metric — exact search, no ANN approximation error (D-006). 6 tests incl. a real insert-then-search round trip.",
      True, [("a581c43","feat(T-M3.6): Milvus collection schema + connection lifecycle")]),
    T("T-M3.7","IMPLEMENT","Embedding provider abstraction + Gemini adapter",
      "Build the swappable connector that turns text into vectors via Gemini.",
      "Build the connector that turns text into AI vectors via Google's Gemini, behind an interface so the AI provider can be swapped later without rewriting everything else.",
      "EmbeddingProvider Protocol + GeminiEmbeddingProvider (google-genai SDK). embed_document/embed_query are separate methods — Gemini's task_type measurably changes the vector. Found and fixed 2 real bugs (a falsy-empty-cache bug, a .env corruption bug). 6 real-API tests.",
      True, [("939fd1b","feat(T-M3.7): embedding provider abstraction + Gemini adapter")]),
    T("T-M3.8","IMPLEMENT","RetrievalStrategy interface + DenseRetriever",
      "Build the real \"search by meaning\" engine against Milvus.",
      "Build the actual \"search by meaning\" engine: turn a question into a vector, search the vector database, get back the closest-matching chunks.",
      "RetrievalStrategy Protocol + RetrievedChunk(chunk_id, score). Confirmed live that Milvus COSINE distance = similarity (higher=better). Also built the missing indexing glue (index_all_chunks, python -m app.cli index) and fixed chunking never being wired into the production CLI.",
      True, [("839bfbf","feat(T-M3.8): RetrievalStrategy interface + DenseRetriever")]),
    T("T-M3.9","IMPLEMENT","SparseRetriever via rank_bm25",
      "Build the real \"search by keyword\" engine with the rank_bm25 library.",
      "Build the real \"search by keyword\" engine using the real BM25 library, built from each chunk's text plus its section label.",
      "app/retrieval/sparse.py. rank_bm25 defaults (k1=1.5, b=0.75) verified against the library's own code (D-005: in-memory, fully inspectable). Whole corpus tokenized once at startup. Reproduced T-M3.4's hand-rolled finding exactly with the real library.",
      True, [("41e0316","feat(T-M3.9): SparseRetriever via rank_bm25")]),
    T("T-M3.10","IMPLEMENT","RRFFusion and WeightedFusion behind one interface",
      "Build both fusion methods so switching between them is a config change.",
      "Build both ways of combining the two search engines' results into one ranked list, so switching between them later is just a config change, not new code.",
      "app/retrieval/fusion.py. RRFFusion is T-M3.3's practice code promoted to production, re-verified against the same hand-computed numbers. WeightedFusion does real per-query min-max normalization. 7 tests.",
      True, [("56586cf","feat(T-M3.10): RRFFusion and WeightedFusion behind one interface")]),
    T("T-M3.11","API","POST /retrieve",
      "Build the real search endpoint with a per-stage timing breakdown.",
      "The first real, callable search endpoint: ask it a question, pick a strategy, get back ranked results with a breakdown of how long each step took.",
      "strategy (dense/bm25/hybrid_rrf/hybrid_weighted) only runs the stages it needs. timings_ms per real stage. Found and fixed a real sqlite3 threading bug and a test-singleton staleness trap. 6 end-to-end tests, all 4 strategies.",
      True, [("b24b109","feat(T-M3.11): POST /retrieve, with per-stage timings")]),
    T("T-M3.12","MEASURE","Four configs × 50 questions — Experiments A, B, C",
      "Run the 50-question exam through all four search configs and record the scores.",
      "Actually run the 50-question exam through all four search setups and record which one scores best.",
      "Dense only / BM25 only / Hybrid+RRF / Hybrid+weighted, each scored on Recall@1/5/10 and MRR using T-M2.8's metrics. Broken down by question category, plus D-013's one-cell chunking cross-check.",
      False, None, M3_EXPERIMENT_TABLE),
    T("T-M3.13","DOCS","Commit evals/results/M3_retrieval.md",
      "Save the real experiment scores as a dated, committed file.",
      "Save the real scores from the experiment as a dated file in the repo, so progress over time is visible and provable.",
      "A dated, diffable record of the numbers at this point in the build.",
      False),
    T("T-M3.14","GIT","PR → merge feat/m3-hybrid-retrieval",
      "Open the PR and merge — the branch already has its real incremental commits.",
      "Open the pull request and merge M3's work — the branch and its commits already exist from T-M3.5 onward, per the new incremental-commit policy (D-019).",
      "Push (if needed) → open PR → self-review → merge. Branch kept after merge (D-018). README quick-start updated for the Milvus/etcd/MinIO requirement.",
      False),
]

M4_TASKS = [
    T("T-M4.1","LEARN","Bi-encoder vs. cross-encoder",
      "Learn why a fast first-pass retriever and a slow, accurate second-pass reranker are different model shapes.",
      "Learn the difference between the fast-but-approximate first search pass and the slow-but-accurate second pass that re-checks the top results.",
      "Bi-encoder: query/doc embedded separately, precomputable, scales to millions. Cross-encoder: fed through the model together, ~50 candidates only, higher accuracy.",
      False, None,
      """<div class="table-wrap"><table><thead><tr><th></th><th>Bi-encoder (retrieval)</th><th>Cross-encoder (reranking)</th></tr></thead><tbody>
<tr><td>How</td><td>Query and doc embedded <i>separately</i></td><td>Fed through the model <i>together</i></td></tr>
<tr><td>Precompute</td><td>Yes — embed once, reuse forever</td><td>No — nothing precomputable</td></tr>
<tr><td>Scale</td><td>Millions</td><td>~50 candidates</td></tr>
<tr><td>Accuracy</td><td>Lower — they never "see" each other</td><td>Higher — models their interaction</td></tr>
</tbody></table></div>"""),
    T("T-M4.2","LEARN","Precision@K, R-Precision, and NDCG",
      "Hand-compute 3 more metrics on the same M2 toy set and see why fixed-K precision is flawed.",
      "Learn three more ways to score search quality, each catching something the simpler Recall@K and MRR scores miss.",
      "Hand-computed on the same M2 toy set. Precision@K is capped by how many relevant chunks exist (D-014's flaw — see table); R-Precision removes that cap; NDCG is the one that actually rewards rank position.",
      False, None,
      """<div class="table-wrap"><table><thead><tr><th>Question</th><th>Relevant chunks (R)</th><th>Perfect retriever's top 5</th><th>Precision@5</th></tr></thead><tbody>
<tr><td>Q1 (factual lookup)</td><td>1 (just A)</td><td>[A, X, Y, Z, W]</td><td>1/5 = <b>0.20</b></td></tr>
<tr><td>Q2 (multi-hop)</td><td>3 (A, B, C)</td><td>[A, B, C, X, Y]</td><td>3/5 = <b>0.60</b></td></tr>
</tbody></table></div><p class="flow-caption">Both retrievers are perfect, yet Precision@5 scores them 0.20 vs 0.60 — the gap is about golden-label count, not retrieval quality (D-014). R-Precision (Precision@R) fixes this: both score 1.0.</p>"""),
    T("T-M4.3","LEARN","LLM-judge rubric design and its failure modes",
      "Learn position bias, verbosity bias, and self-preference in AI grading.",
      "Learn how to design the scoring rules for an AI grading another AI's answers, and the common ways that grading goes wrong.",
      "Position bias, verbosity bias, self-preference. Design the rubric to resist each rather than hoping they don't apply.",
      False),
    T("T-M4.4","PRACTICE","Run a local cross-encoder on a fixed candidate set",
      "Try the reranker on real results and manually sanity-check the reordering.",
      "Try the re-ranking model on a real set of results and manually check whether its reordering actually makes sense.",
      "Inspect what moved up, what moved down, and whether you agree with it before wiring it in.",
      False),
    T("T-M4.5","IMPLEMENT","Reranker interface + local cross-encoder",
      "Build the real second-pass reranking step, running locally on CPU.",
      "Build the real second-pass re-ranking step that re-scores the top ~50 results for better precision.",
      "Runs on CPU for a top-50 candidate set. Local rather than an API — free to iterate on, reproducible.",
      False),
    T("T-M4.6","IMPLEMENT","Context builder: dedupe, token budget, citation mapping",
      "Assemble the final context sent to the LLM: dedupe, fit a token budget, track chunk IDs.",
      "Build the step that assembles the final set of chunks sent to the AI to generate an answer — removing duplicates, fitting a size limit, and keeping track of which chunk is which for citations.",
      "Overlapping chunks from two retrievers deduped; assembled context fits a token budget; every surviving chunk keeps its ID for citation mapping.",
      False),
    T("T-M4.7","IMPLEMENT","LLM provider abstraction + Gemini generation adapter",
      "Build the swappable connector for answer generation, mirroring T-M3.7.",
      "Build the connector that sends the final prompt to the AI model to generate an actual answer, behind a swappable interface.",
      "Mirrors the embedding abstraction from T-M3.7. Both are what the PRD means by \"pluggable LLM/embedding/reranker\".",
      False),
    T("T-M4.8","IMPLEMENT","Citation-grounded structured generation + malformed-output recovery",
      "Force the LLM's answer into a validated, cited, structured format with retry-on-failure.",
      "Make the AI's answer come back in a strict, checkable format with every claim linked to the exact chunk it came from — and automatically retry if it gets the format wrong.",
      "Pydantic-validated claims with chunk IDs. Structured-output requests do fail — retry with a repair prompt, then a structured error. Sets up M7's claim verification for free.",
      False),
    T("T-M4.9","IMPLEMENT","Extend metrics.py: precision_at_k(), r_precision(), ndcg()",
      "Add the three new metrics as real, tested code.",
      "Add the three new scoring formulas from the learning task as real, tested code alongside the ones already built in M2.",
      "r_precision() is precision_at_k() called with k=len(relevant) — same function, different K per question (D-014). R-Precision is the column that goes in the real results table.",
      False),
    T("T-M4.10","IMPLEMENT","LLM judge with a fixed rubric",
      "Build the AI grader for faithfulness, correctness, and citation support.",
      "Build the AI grader that scores generated answers for faithfulness, correctness, and whether citations are actually supported.",
      "Temperature 0, versioned rubric text. Faithfulness, answer correctness, citation support rate.",
      False),
    T("T-M4.11","IMPLEMENT","Experiment runner + persistence",
      "Build the tool that records exactly what config produced each experiment result.",
      "Build the tool that runs an experiment and permanently records exactly what config produced each result, so it can be reproduced later.",
      "Every run records dataset version, pipeline config, embedding model, reranker model and LLM version.",
      False),
    T("T-M4.12","API","POST /query, /evaluate, GET /experiments/{id}, POST /experiments/compare",
      "Build the full question-answering + evaluation API surface.",
      "Build the full set of endpoints: ask a real question and get an answer, run an evaluation, and compare experiment results.",
      "The full API surface the PRD specifies. /query returns answer, citations, trace ID and a timing breakdown.",
      False),
    T("T-M4.13","AUTHOR","Expand the golden set to 150–200 questions",
      "Grow the test set using real failure patterns observed so far.",
      "Grow the test-question set using real failure patterns observed over the past three weeks of building, not just guesses made up front.",
      "Write the adversarial cases now — observed failure modes make far better adversarial questions than anything invented up front.",
      False),
    T("T-M4.14","MEASURE","Full benchmark ladder — Experiments D, E, F",
      "Run baseline vs +hybrid vs +reranker across all metrics including answer quality.",
      "Run the full comparison: baseline search vs. +hybrid vs. +reranker, scored on every metric including answer quality and speed.",
      "R-Precision (not fixed Precision@5) is the reported column, per D-014. Plus the context-builder ablation (F) and the contextual-prefix comparison (E).",
      False, None,
      """<div class="table-wrap"><table><thead><tr><th>Config</th><th>Recall@5</th><th>MRR</th><th>R-Precision</th><th>Faithfulness</th><th>Correctness</th><th>Citation support</th><th>P95 latency</th></tr></thead><tbody>
<tr><td>Baseline (dense)</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>
<tr><td>+ hybrid</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>
<tr><td>+ reranker</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td></tr>
</tbody></table></div>"""),
    T("T-M4.15","VERIFY","Hand-score 20 answers; measure judge agreement",
      "Manually grade 20 answers and check the AI judge agrees.",
      "Manually grade 20 real answers yourself, then check whether the AI judge agrees with your grading — if it doesn't, the grading rubric is broken.",
      "The gate on everything downstream. If the judge disagrees with you on 8 of 20, the rubric is broken and every generation metric is noise.",
      False),
    T("T-M4.16","MEASURE","Failure analysis: document three real failures",
      "Document 3 real failures with root cause and measured fix.",
      "Find three real cases where the system got something wrong, and document exactly why and how it was fixed.",
      "A PRD acceptance criterion. For each: what was asked, what came back, the root cause, the measured effect of the fix.",
      False),
    T("T-M4.17","DOCS","Write ARCHITECTURE.md",
      "Document the system architecture and the reasoning behind it.",
      "Document how the whole system fits together and why it was built this way.",
      "The diagram plus the reasoning: why two-stage retrieval, why hybrid, why these interfaces. Links out to DECISIONS.md.",
      False),
    T("T-M4.18","DOCS","Complete EVALUATION.md and the full README",
      "Finish the main docs with real architecture, quick start, benchmarks, and limitations.",
      "Finish the main project documentation with the real architecture, quick start, API examples, benchmark numbers, and known limitations.",
      "README: architecture diagram · quick start · API examples · the benchmark table · failure analysis · limitations.",
      False),
    T("T-M4.19","DOCS","Start CHANGELOG.md",
      "Start a running release log.",
      "Start a running log of what changed in the project, release by release.",
      "Mechanical if you've used conventional commits (D-019); archaeology if you haven't.",
      False),
    T("T-M4.20","GIT","Tag v1.0.0 and publish the GitHub Release",
      "Publish the first official release with real benchmark numbers.",
      "Officially publish the first public release of the project with its real benchmark numbers front and center.",
      "Release notes lead with the benchmark table and the dense-vs-hybrid result. First of the three PRD-mandated releases.",
      False),
    T("T-M4.21","VERIFY","Clean-clone reproducibility check",
      "Prove a fresh clone works using only the README.",
      "Download the project fresh onto a clean machine and prove it actually works using only the README's instructions.",
      "Clone into a fresh directory, follow only the README, confirm the stack comes up and /query answers.",
      False),
]

M5_TASKS = [
    T("T-M5.1","LEARN","LangGraph fundamentals",
      "Learn state, nodes, edges, conditional edges, and checkpointing.",
      "Learn the framework used to build multi-step AI workflows with branching logic.",
      "State, nodes, edges, conditional edges, checkpointing. Scope discipline: it orchestrates, it does not retrieve/fuse/evaluate (D-007) — those stay hand-written.",
      False),
    T("T-M5.2","LEARN","Routing and decomposition strategies",
      "Learn classification approaches and why over-decomposition is the dominant failure mode.",
      "Learn how to detect whether a question is simple or complex, and how splitting a complex question into parts can backfire if overdone.",
      "Classification approaches, sub-query generation. Over-decomposition is the dominant failure mode — splitting a simple question costs 4x and retrieves worse.",
      False),
    T("T-M5.3","PRACTICE","Toy 3-node LangGraph with one conditional edge",
      "Build a tiny non-RAG practice graph to learn the framework in isolation.",
      "Build a tiny, non-RAG practice graph just to learn the framework in isolation first.",
      "Nothing RAG-related — so when the real graph misbehaves later, you know it's your logic, not your understanding of the library.",
      False),
    T("T-M5.4","PRACTICE","Hand-decompose 10 multi-hop golden questions",
      "Manually break down 10 real multi-part questions by hand.",
      "Manually break down 10 real multi-part questions into their sub-questions, by hand, before building the automated version.",
      "Worked example: a Gold-member/discount/points question → 3 sub-queries. Note what a single flat query would have missed.",
      False),
    T("T-M5.5","IMPLEMENT","Port the V1 pipeline into a LangGraph graph, behaviour-identical",
      "Rebuild the existing pipeline inside LangGraph with zero behavior change.",
      "Rebuild the existing working pipeline inside the new graph framework, with zero change in behavior — a pure refactor.",
      "Re-run the benchmark and confirm the numbers are unchanged. Any movement at this step is a bug.",
      False),
    T("T-M5.6","IMPLEMENT","Router node: simple vs. complex",
      "Build the step that decides whether a question needs decomposition.",
      "Build the step that decides, for each incoming question, whether it's simple enough for direct search or needs to be broken down first.",
      "Start with an LLM call. Record the decision and its reasoning in the trace — an unexplainable routing decision is worse than no routing.",
      False),
    T("T-M5.7","IMPLEMENT","Decomposer node + per-sub-query retrieval and merge",
      "Split complex questions, retrieve per sub-query, merge the results.",
      "Build the step that splits a complex question into sub-questions, searches for each one separately, then merges the results.",
      "Sub-queries retrieved independently, evidence merged and deduped before generation. Every sub-query traceable back to the parent question.",
      False),
    T("T-M5.8","API","Extend /query with routing metadata",
      "Expose which route a question took and why.",
      "Make the API response show which route a question took and why.",
      "Route taken, sub-queries generated, evidence per sub-query.",
      False),
    T("T-M5.9","MEASURE","Experiment H: decomposition on/off",
      "Measure whether decomposition helps multi-hop without hurting simple questions.",
      "Measure whether breaking down complex questions actually helps — and confirm it doesn't hurt the simple ones.",
      "Multi-hop subset should improve. Simple questions must not regress — the over-decomposition check.",
      False),
    T("T-M5.10","GIT","Branch → PR → merge feat/m5-router-decomposition",
      "Save and merge the M5 work.",
      "Save and merge the M5 work to the main codebase.",
      "Commit evals/results/M5_decomposition.md alongside the code.",
      False),
]

M6_TASKS = [
    T("T-M6.1","LEARN","Evidence-grading approaches and weak-retrieval signals",
      "Learn the signals that indicate search results are too weak to answer from.",
      "Learn the signals that indicate a search result is probably too weak to answer from confidently.",
      "Top reranker score below threshold, large score gap, no agreement across chunks, chunks not covering sub-parts. Start with a simple score threshold.",
      False),
    T("T-M6.2","LEARN","Bounded-loop design in state graphs",
      "Learn how to guarantee a retry loop eventually stops.",
      "Learn how to build a retry loop that is guaranteed to eventually stop, so it can never run forever and burn unlimited API budget.",
      "Termination guarantees, give-up paths, budget guards. \"Bounded\" is load-bearing.",
      False),
    T("T-M6.3","PRACTICE","Hand-label 20 retrieval results weak/strong",
      "Manually judge 20 results to find the real score cutoff empirically.",
      "Manually judge 20 real search results as weak or strong, to find the right cutoff score empirically rather than guessing.",
      "Compare against reranker scores to find your threshold empirically. Include unanswerable questions — they should cluster at the weak end.",
      False),
    T("T-M6.4","IMPLEMENT","Evidence grader node with a calibrated threshold",
      "Build the real step that judges whether search results are good enough to answer from.",
      "Build the real step that checks, before generating an answer, whether the search results are actually good enough to answer from.",
      "Configurable, not hardcoded — belongs in the experiment config so runs stay reproducible.",
      False),
    T("T-M6.5","IMPLEMENT","Query refinement node + bounded retry loop",
      "Build the retry loop with a hard cap and an explicit give-up path.",
      "Build the step that rewrites a question and retries the search, but only up to a hard limit, with a real give-up path.",
      "Hard cap on attempts, plus an explicit give-up path that hands off to abstention rather than accepting weak evidence.",
      False),
    T("T-M6.6","IMPLEMENT","Budget guard: max retries, max tokens per request",
      "Add a second, independent cost ceiling.",
      "Add a second, independent safety cap on cost, separate from the retry limit.",
      "A hard ceiling independent of the retry cap. The loop and the budget can fail independently.",
      False),
    T("T-M6.7","API","Surface grading decisions in /query and traces",
      "Expose the grading decision and retry status in the API.",
      "Make the grading decision (and whether a retry happened) visible in the API response.",
      "Grade, score, whether a retry fired, and the refined query.",
      False),
    T("T-M6.8","VERIFY","Prove the loop terminates",
      "Write a real test proving the retry loop can't run forever.",
      "Write a real automated test that proves the retry loop can't run forever, even on a deliberately impossible question.",
      "Test with an adversarial unanswerable question. A committed test, not a manual check.",
      False),
    T("T-M6.9","MEASURE","Experiment I: grading + retry on/off",
      "Measure grader agreement, retry rate, and the latency cost.",
      "Measure how well the grading matches your hand labels, how often retries fire, and what they cost in time.",
      "Grader agreement with hand labels, retry-triggered rate, unanswerable questions reliably grade weak, latency cost of the retry path.",
      False),
    T("T-M6.10","GIT","Branch → PR → merge feat/m6-evidence-grading",
      "Save and merge the M6 work including the hand labels.",
      "Save and merge the M6 work, including the hand labels as reusable ground truth.",
      "Commit the results file and the hand labels.",
      False),
]

M7_TASKS = [
    T("T-M7.1","LEARN","Claim extraction: atomicity and edge cases",
      "Learn how to break an answer into individually-checkable claims.",
      "Learn how to break a generated answer down into its individual, checkable factual claims.",
      "What counts as one claim · compound sentences · hedged statements · claims implied rather than stated.",
      False),
    T("T-M7.2","LEARN","NLI-style verification, three outcomes not two",
      "Learn why claim verification needs supported/contradicted/not_addressed, not just right/wrong.",
      "Learn that checking a claim against evidence needs three possible answers, not just right/wrong — the evidence might simply be silent on it.",
      "supported · contradicted · not_addressed. Collapsing the last two loses real information.",
      False),
    T("T-M7.3","LEARN","Abstention and calibration",
      "Learn when refusing to answer is actually the better choice.",
      "Learn when it's actually better for the system to refuse to answer than to answer wrong.",
      "When refusing beats answering · over-abstention as its own failure mode · how to present a refusal usefully.",
      False),
    T("T-M7.4","PRACTICE","Hand-extract and verify claims from 10 answers",
      "Manually extract and check claims from 10 real answers before automating it.",
      "Manually pull out and check the claims from 10 real answers yourself, before building the automated verifier — so your ground truth isn't biased by the machine's own output.",
      "This is the ground truth the automated verifier gets measured against. Do it before building the verifier.",
      False),
    T("T-M7.5","IMPLEMENT","Claim extractor",
      "Build the real step that pulls claims out of a generated answer.",
      "Build the real step that pulls individual claims out of a generated answer.",
      "Leans on T-M4.8's structured output — if generation already emits claim-level data, extraction is mostly validation.",
      False),
    T("T-M7.6","IMPLEMENT","Claim verifier with three-way outcomes",
      "Check each claim strictly against only its own cited chunk.",
      "Build the step that checks each claim strictly against only its own cited source chunk.",
      "Each claim checked against its own cited chunks, not the whole context — otherwise an uncited chunk could rescue a fabricated citation.",
      False),
    T("T-M7.7","IMPLEMENT","Revise-or-abstain + weakest-claim reporting",
      "Score the whole answer by its weakest claim, never the average.",
      "If any single claim in the answer is weak, the whole answer's score reflects that weakest claim — not a misleading average.",
      "Report the minimum claim score, never the mean. Bounded revision — one attempt, then abstain.",
      False),
    T("T-M7.8","IMPLEMENT","Abstention response format",
      "Design a useful refusal message, not a dead-end shrug.",
      "Design what the user actually sees when the system refuses to answer — a useful explanation, not a dead-end shrug.",
      "What the user sees, what evidence was found, why it was judged insufficient, what would need to exist to answer.",
      False),
    T("T-M7.9","API","Surface per-claim verification in /query",
      "Expose each claim's individual outcome in the API.",
      "Make each individual claim's verification outcome visible in the API response.",
      "Each claim with its outcome, its supporting chunk IDs, and the weakest-claim score.",
      False),
    T("T-M7.10","MEASURE","Experiment J: V1 vs. V2",
      "Measure faithfulness improvement and abstention rates.",
      "Measure how much the new verification step actually improves answer faithfulness, and at what cost.",
      "Verifier agreement with hand labels, abstention rate on unanswerable (should be high) and answerable (should be low) questions, faithfulness delta, latency/cost delta.",
      False),
    T("T-M7.11","DOCS","README: the verification and abstention story",
      "Write the honest V1→V2 comparison, including what was traded away.",
      "Write up the honest before/after comparison for the README, including what was traded away.",
      "The V1→V2 comparison table, the weakest-claim reasoning, an honest note on what was traded.",
      False),
    T("T-M7.12","GIT","Tag v2.0.0 and publish the GitHub Release",
      "Publish the second release, leading with faithfulness and abstention numbers.",
      "Officially publish the second release, leading with the faithfulness and abstention numbers.",
      "Release notes lead with the faithfulness improvement and the abstention numbers. Second of the three PRD-mandated releases.",
      False),
]

M8_DECIDE_TABLE = """<div class="table-wrap"><table><thead><tr><th>Approach</th><th>Mechanism</th><th>Trade-off</th></tr></thead><tbody>
<tr><td>Delete on supersede</td><td>Drop the old version at ingest</td><td>Simple, but destroys history — "what was the policy in March?" becomes unanswerable</td></tr>
<tr><td><b>Filter at query time</b> &#9989;</td><td>Index everything; filter to effective_date-current unless historical</td><td><b>The choice.</b> History preserved, "as of" questions answerable</td></tr>
<tr><td>Re-rank by recency</td><td>Boost newer documents in scoring</td><td>Soft signal — a strongly-matching old doc can still outrank a weakly-matching current one. Wrong for policy</td></tr>
</tbody></table></div>"""

M8_TASKS = [
    T("T-M8.1","LEARN","Version-aware retrieval design",
      "Learn effective-date filtering, supersession chains, and \"as of\" queries.",
      "Learn how to make sure search results reflect the current version of a policy, not an outdated one.",
      "Effective-date filtering, supersession chains, \"as of\" queries. Also: what happens when two current documents legitimately contradict each other.",
      False),
    T("T-M8.2","LEARN","Freshness strategies for URL-sourced corpora",
      "Learn content-hash change detection and crawl scheduling.",
      "Learn how to detect when a source webpage has actually changed, so it can be re-fetched only when needed.",
      "Content-hash change detection, crawl scheduling, politeness/rate limits, detecting a moved page.",
      False),
    T("T-M8.3","LEARN","Airflow fundamentals: DAGs, scheduling, idempotent tasks",
      "Learn the scheduler used for the automated recrawl job.",
      "Learn the scheduling tool used to run the recrawl job automatically on a timer.",
      "Scoped tightly to one scheduled ingestion DAG — the PRD's justified use of Airflow, not an excuse to orchestrate everything.",
      False),
    T("T-M8.4","LEARN","Regression and ablation harness design",
      "Learn what makes comparing two experiment runs valid at all.",
      "Learn what makes it valid to compare two experiment runs against each other at all.",
      "Fixed dataset version, fixed seed, recorded config. Comparing two runs with different golden-set versions is meaningless.",
      False),
    T("T-M8.5","DECIDE","How to handle a superseded document",
      "Decide, with a comparison table, how to handle an old policy version once replaced.",
      "Decide what happens to an old policy version once a new one replaces it: delete it, hide it at search time, or just nudge its ranking down.",
      "Three options compared; chosen: filter at query time. Recorded as D-009.",
      False, None, M8_DECIDE_TABLE),
    T("T-M8.6","IMPLEMENT","Metadata filters in the retrieval layer",
      "Build the real filter so both retrievers only return currently-valid documents.",
      "Build the real filter so both search engines only return currently-valid documents by default.",
      "Milvus scalar filtering on effective_date and supersession status, plumbed through the RetrievalStrategy interface so both dense and sparse honour the same filter.",
      False),
    T("T-M8.7","IMPLEMENT","Supersession resolution",
      "Build the logic that follows \"this replaces that\" chains to find the current version.",
      "Build the logic that follows the chain of \"this replaces that\" links to find a document family's current version.",
      "Walk the supersedes chain. Handle broken cases: a chain with a gap, or a cycle from a data-entry error.",
      False),
    T("T-M8.8","IMPLEMENT","Temporal query handling",
      "Detect \"as of\" questions and filter accordingly.",
      "Make the system detect when someone is asking about a past policy (\"as of March\") versus the current one, and answer accordingly.",
      "Default to current; detect \"as of <date>\" and historical phrasing. Cite the version and its effective date.",
      False),
    T("T-M8.9","AUTHOR","Add version-sensitive golden questions",
      "Write more questions designed to trip up a system without currency tracking.",
      "Write more test questions specifically designed to trip up a system that doesn't track document currency correctly.",
      "Expand beyond M2's four: current-policy questions where the superseded version gives a plausible-but-wrong answer, plus explicit historical questions.",
      False),
    T("T-M8.10","DOCKER","Add Airflow to Docker Compose",
      "Add Airflow as an optional extra, not part of the core stack.",
      "Add the scheduling tool to the project's infrastructure, but as an optional extra, not part of the core stack.",
      "Scheduler, webserver and its metadata DB, in an optional Compose profile so the core stack stays lightweight.",
      False),
    T("T-M8.11","IMPLEMENT","Scheduled recrawl DAG",
      "Build the automated job that re-ingests sources only when they actually changed.",
      "Build the automated job that periodically re-checks public source pages and only re-ingests them if they actually changed.",
      "Re-fetch public URLs, compare content hash, re-ingest only on change — creating a new version row rather than overwriting.",
      False),
    T("T-M8.12","IMPLEMENT","Ablation runner",
      "Build a tool that runs several configs and prints a comparison table in one command.",
      "Build a tool that runs several pipeline configurations against the test set in one command and prints a comparison table.",
      "Turns every future \"does X help?\" question into one command instead of a manual afternoon.",
      False),
    T("T-M8.13","IMPLEMENT","Baseline snapshot + regression comparison",
      "Build a way to compare any run against a saved known-good baseline.",
      "Build a way to save a \"known good\" result set and automatically compare any future run against it.",
      "Store a named baseline result set; compare any run against it with per-metric deltas and a configurable tolerance. M9's CI gate consumes this directly.",
      False),
    T("T-M8.14","MEASURE","Experiment L: version-awareness on/off",
      "Measure the improvement on version-sensitive test questions.",
      "Measure how much the version-filtering feature actually improves answers on the version-sensitive test questions.",
      "On the version-sensitive subset. Expect a large, clean improvement.",
      False),
    T("T-M8.15","VERIFY","Freshness end to end",
      "Change a real source, run the recrawl, confirm the system updates — and confirm a no-op when nothing changed.",
      "Actually change a source document, run the recrawl job, and confirm the system picks up the new version — then confirm running it again when nothing changed does nothing.",
      "Modify a locally-cached source, run the DAG, confirm a new version row appears and retrieval switches to it. Then confirm it's a no-op unchanged.",
      False),
    T("T-M8.16","DOCS","Document versioning and freshness in ARCHITECTURE.md",
      "Document the three options considered and why query-time filtering won.",
      "Document the three options considered for handling old documents and why query-time filtering won.",
      "Include the three-approaches table and why query-time filtering won. Update the architecture diagram with the recrawl path.",
      False),
    T("T-M8.17","GIT","Branch → PR → merge feat/m8-versioning-freshness",
      "Save and merge M8, including the baseline snapshot as a permanent reference.",
      "Save and merge the M8 work, including the baseline snapshot as a permanent reference point.",
      "Commit the baseline snapshot — it's the reference every later run is judged against.",
      False),
]

M9_TASKS = [
    T("T-M9.1","LEARN","OpenTelemetry: spans, traces, context propagation",
      "Learn the standard for recording a nested request timeline.",
      "Learn the standard way to record a detailed, nested timeline of everything that happened while answering one request.",
      "How a span tree represents a nested pipeline, and how context propagates across async boundaries.",
      False),
    T("T-M9.2","LEARN","Percentile latency, and why the mean misleads",
      "Hand-compute P50/P95/P99 and see why averages hide slow outliers.",
      "Learn why looking at the average response time hides the worst, most noticeable slowdowns.",
      "Compute P50/P95/P99 by hand on a synthetic heavy-tailed distribution. The retry path guarantees a heavy tail — the mean would actively mislead.",
      False),
    T("T-M9.3","LEARN","Regression gate design for noisy ML metrics",
      "Learn how to set thresholds that catch real regressions without false-alarming.",
      "Learn how to set automated quality thresholds that catch real regressions without constantly false-alarming on normal noise.",
      "Too tight and CI fails on run-to-run noise; too loose and a real regression slips through. Fixed seeds and a fixed subset buy back determinism.",
      False),
    T("T-M9.4","DOCKER","Add a trace backend to Compose",
      "Add a visual tracing tool as an optional profile.",
      "Add a tool that lets you visually see the timeline of each request, not just read it as raw JSON.",
      "Jaeger or an OTel collector, in an optional profile. Being able to see the span tree is most of the value.",
      False),
    T("T-M9.5","IMPLEMENT","OTel instrumentation across every pipeline stage",
      "Add tracing to every step, with retries showing as repeated spans.",
      "Add timing/tracing instrumentation to every single step of the pipeline, so a slow request can be diagnosed at a glance.",
      "Spans for route · decompose · retrieve (dense/sparse separately) · fuse · rerank · grade · generate · extract claims · verify. Retry loop shows as repeated spans.",
      False),
    T("T-M9.6","IMPLEMENT","Bridge the M9 trace ID to the P0 request ID",
      "Make the logging and tracing systems share one identifier.",
      "Make sure the old logging system and the new tracing system use the exact same ID for the same request, so they're not two disconnected views.",
      "The structured logs from Phase 0 and the OTel traces must share an identifier.",
      False),
    T("T-M9.7","IMPLEMENT","Token and cost accounting per stage",
      "Track token/cost per pipeline stage.",
      "Track exactly how many AI tokens (and how much money) each individual pipeline stage costs per request.",
      "Tokens in/out per model call, mapped to per-provider pricing in config. Attribute cost to the stage that spent it.",
      False),
    T("T-M9.8","IMPLEMENT","Caching layer (Redis) with hit-rate reporting",
      "Put the unused Redis service to work caching embeddings and generations.",
      "Finally put the Redis cache (sitting unused since day one) to work caching embeddings and AI responses, and track how often it actually helps.",
      "Redis has been in Compose since Phase 0, unused. Cache embeddings and generation responses; report hit rate as a first-class metric.",
      False),
    T("T-M9.9","IMPLEMENT","Async concurrency for parallel retrieval",
      "Run dense and sparse retrieval concurrently and measure the speedup.",
      "Make the dense and keyword searches run at the same time instead of one after another, since they don't depend on each other.",
      "Dense and sparse retrieval are independent — run them concurrently. Measure before and after rather than assuming the speedup.",
      False),
    T("T-M9.10","IMPLEMENT","Fast CI eval subset",
      "Build a ~20-30 question subset that can run on every PR.",
      "Build a small, fast version of the test set (~20-30 questions) that can run automatically on every code change without slowing CI down.",
      "Spanning all categories, fixed seeds. Has to finish in CI-acceptable time or it will be disabled within a fortnight.",
      False),
    T("T-M9.11","IMPLEMENT","Regression gate workflow with per-metric tolerances",
      "Build the automated check that fails a PR on a quality drop.",
      "Build the automated check that fails a pull request if quality drops too much compared to the saved baseline.",
      "Compares against M8's baseline, fails the build on a drop beyond tolerance, posts the delta table to the PR.",
      False),
    T("T-M9.12","VERIFY","Prove the gate catches a real regression",
      "Deliberately degrade the pipeline and confirm CI fails.",
      "Deliberately break the pipeline on purpose and confirm the automated quality gate actually catches it and fails the build.",
      "Deliberately degrade the pipeline — disable the reranker — push, and confirm CI goes red with a sensible message.",
      False),
    T("T-M9.13","MEASURE","Full cost/latency profile",
      "Measure complete speed and cost, broken down by stage and question type.",
      "Measure the complete speed and cost picture of the system, broken down by pipeline stage and by question type.",
      "P50/P95/P99 per stage and end to end · tokens per request · estimated cost per request · cache hit rate · broken down by route taken.",
      False),
    T("T-M9.14","DOCS","Evaluation dashboard / results view",
      "Publish a report of metrics across runs.",
      "Publish a report showing how the system's metrics have evolved across runs.",
      "A PRD deliverable. A committed static report of metrics across runs is enough.",
      False),
    T("T-M9.15","GIT","Branch → PR → merge feat/m9-observability-gates",
      "Save and merge M9, with a trace screenshot as evidence.",
      "Save and merge the M9 work, with a screenshot proving the tracing actually works.",
      "Include a trace screenshot in the PR — the clearest possible evidence the instrumentation works.",
      False),
]

M10_TASKS = [
    T("T-M10.1","LEARN","ANN index types and their trade-offs",
      "Learn HNSW vs. IVF index trade-offs.",
      "Learn about the faster-but-approximate search index types, and the trade-offs between them.",
      "HNSW (M, efConstruction, ef) vs. IVF variants: build time, memory, query speed, recall.",
      False),
    T("T-M10.2","BUILD","Generate a scale corpus",
      "Programmatically expand to hundreds of thousands of chunks, validated at 10k first.",
      "Programmatically generate a much larger fake document set to stress-test the system at real scale.",
      "Expansion to a few hundred thousand chunks, clearly marked synthetic. Benchmark at 10k first to validate the methodology.",
      False),
    T("T-M10.3","IMPLEMENT","HNSW index + parameter sweep",
      "Build the approximate index and sweep its settings.",
      "Build the faster approximate search index and test it across a range of settings.",
      "Index build time, memory, query latency and recall across several ef values, against the FLAT ground truth.",
      False),
    T("T-M10.4","MEASURE","Experiment K: FLAT vs. HNSW",
      "Measure the recall traded away for the HNSW speed gain.",
      "Measure exactly how much search accuracy is traded away for the speed gain when switching to the faster index.",
      "The recall/latency curve, with your chosen operating point marked and justified. Also check whether rank_bm25 is still viable at this scale.",
      False),
    T("T-M10.5","IMPLEMENT","Local embedding provider (BGE-M3 or equivalent)",
      "Add a free local embedding model as a second provider.",
      "Add a second way to generate AI vectors that runs locally for free, instead of only via Google's paid API.",
      "Added as a second provider, not a replacement. If this requires touching anything outside the adapter, the abstraction was leaky.",
      False),
    T("T-M10.6","MEASURE","Experiment G: Gemini vs. local embeddings",
      "Compare paid cloud vs. free local embeddings.",
      "Compare the paid cloud AI embeddings against the free local ones on quality, speed, and cost.",
      "Retrieval quality, latency, and cost per 1000 chunks. The interesting question is whether local is good enough to buy full reproducibility.",
      False),
    T("T-M10.7","VERIFY","Confirm the embedding cache is provider-aware",
      "Verify switching providers never leaks vectors across providers.",
      "Make sure switching AI providers never accidentally serves one provider's vectors to the other provider's index.",
      "T-M2.6 keyed the cache on hash(text + model_id) for exactly this moment — verify it holds.",
      False),
    T("T-M10.8","LEARN","Prompt injection via retrieved content",
      "Learn how a malicious instruction hidden in a page could try to hijack the AI.",
      "Learn how a malicious instruction hidden inside a web page could try to hijack the AI if it's not treated carefully.",
      "Retrieved content is data, not instructions — the prompt architecture has to enforce that.",
      False),
    T("T-M10.9","IMPLEMENT","Upload validation and parsing isolation",
      "Add safety limits against a malicious uploaded file.",
      "Add safety limits so a malicious uploaded file can't exhaust the server's memory or disk during processing.",
      "File size and type limits, content-type verification, resource limits on parsing.",
      False),
    T("T-M10.10","VERIFY","Injection test, with a documented result",
      "Actually try to inject a hidden instruction and report the outcome honestly.",
      "Actually try to trick the system with a hidden malicious instruction inside a document, and honestly report what happened.",
      "Ingest a document containing embedded instructions, query so it's retrieved, confirm the pipeline treats it as content. Report the outcome honestly, including partial mitigation.",
      False),
    T("T-M10.11","DOCS","Write SECURITY.md",
      "Publish an honest threat model.",
      "Publish an honest document explaining what security risks are and aren't handled.",
      "Threat model, what's mitigated, what explicitly isn't, and how to report an issue.",
      False),
    T("T-M10.12","DOCS","Final README with the full V1→V2→V3 benchmark ladder",
      "Build the final README centerpiece table.",
      "Build the final README centerpiece: one table showing every version's numbers and what each stage actually bought.",
      "One table showing every configuration and what each stage bought. The single most-read artifact in the repo.",
      False),
    T("T-M10.13","DOCS","The quality / latency / cost operating point",
      "State which config would actually run in production and why.",
      "State plainly which configuration would actually be run in production, and explain why it isn't simply the highest-scoring one.",
      "The PRD's closing requirement. Naming what you gave up is the whole point.",
      False),
    T("T-M10.14","DOCS","Expanded failure analysis and limitations",
      "Document everything that still fails, honestly.",
      "Document everything that still fails even at the final version, honestly.",
      "Beyond M4's three cases: what still fails at V3, what a self-authored evaluation set can't tell you, where the LLM judge remains weak.",
      False),
    T("T-M10.15","DOCS","Record the demo",
      "Record a video including a question the system correctly refuses.",
      "Record a short video showing the system in action, including a question it correctly refuses to answer.",
      "Show evidence, citations, verification — and a question the system correctly refuses to answer. The most distinctive thing this project does.",
      False),
    T("T-M10.16","VERIFY","Final clean-clone reproducibility pass",
      "One last fresh-clone, README-only full verification.",
      "One last full test: fresh clone, README only, everything works and the benchmark reproduces.",
      "Fresh clone, README only, full stack up, benchmark reproduced.",
      False),
    T("T-M10.17","GIT","Tag v3.0.0 and publish the final GitHub Release",
      "Publish the third and final release.",
      "Publish the final, third release of the project.",
      "Third of the three PRD-mandated releases. Notes cover the scale results, provider comparison, operating-point decision.",
      False),
]

# ===========================================================================
# Milestone definitions with flowcharts (one per milestone, some with 2)
# ===========================================================================

MILESTONES = [
    dict(key="p0", tier="p0", title="P0 — Foundations & Repository Setup",
         date="Aug 18–24 · Sep 5–6", bars=[("2026-08-18","2026-08-24"),("2026-09-05","2026-09-06")],
         goal="A FastAPI service that boots via Docker Compose with typed config and structured logging — under version control, on GitHub, with CI green.",
         sections=[("Application skeleton", P0_TASKS[:7]), ("Repository & GitHub", P0_TASKS[7:])],
         flows=[("Request lifecycle", flow_linear([("Request","HTTP in"),("Middleware","log + request ID"),("Route handler","FastAPI"),("Response","structured JSON")], accent_last=True))]),
    dict(key="m1", tier="v1", title="M1 — Corpus & Ingestion", date="Sep 6–12",
         bars=[("2026-09-06","2026-09-12")],
         goal="A reproducible retail corpus, ingested with stable IDs and content hashes, queryable from Postgres.",
         sections=[("Learn & decide", M1_TASKS[:2]), ("Build", M1_TASKS[2:4]), ("Implement", M1_TASKS[4:10]), ("Verify & deliver", M1_TASKS[10:])],
         flows=[("Ingestion pipeline", flow_parallel_then_merge(
             ("Source",""), [("URL","(URLSource)",), ("File","(FileSource)",)],
             [("Extract text",""),("Hash (sha256)",""),("Dedupe check",""),("Postgres insert","documents")])
             .replace('("URL","(URLSource)",)', '').strip() if False else
             f"""<div class="flow-branch">
  <div class="flow-branch-row">
    <div class="flow-branch-col"><div class="flow-branch-label">by URL</div><div class="flow-box"><b>URLSource</b></div></div>
    <div class="flow-branch-col"><div class="flow-branch-label">by path</div><div class="flow-box"><b>FileSource</b></div></div>
  </div>
  <span class="flow-arrow" style="transform:rotate(90deg);">&rarr;</span>
  <div class="flow">
    <div class="flow-box"><b>Extract text</b><span>per format</span></div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-box"><b>Hash</b><span>sha256(text)</span></div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-diamond">seen before?</div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-box accent"><b>Postgres</b><span>insert or skip</span></div>
  </div>
</div>""")]),
    dict(key="m2", tier="v1", title="M2 — Chunking & Seed Golden Set", date="Sep 13–19",
         bars=[("2026-09-13","2026-09-19")],
         goal="A defensible retrievable unit, plus 50 labelled questions so M3's choices are measured rather than eyeballed.",
         sections=[("Learn & decide", M2_TASKS[:2]), ("Practice & implement", M2_TASKS[2:6]), ("Metrics foundation", M2_TASKS[6:8]), ("Author & verify", M2_TASKS[8:11]), ("Deliver", M2_TASKS[11:])],
         flows=[
            ("Chunking pipeline", flow_linear([("Document text","from Postgres"),("Split at headings","## / ###"),("Guard check","MIN 40 / MAX 350"),("Contextual prefix","self-contained"),("chunks table","Postgres")], accent_last=True)),
            ("Embedding cache (used across M2 tuning and all of M3)",
             f"""<div class="flow-branch">
  <div class="flow">
    <div class="flow-box"><b>text + model_id</b></div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-box"><b>sha256 hash</b></div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-diamond">in cache?</div>
  </div>
  <div class="flow-branch-row" style="margin-top:6px;">
    <div class="flow-branch-col"><div class="flow-branch-label">hit</div><div class="flow-box accent"><b>Return saved vector</b><span>zero API calls</span></div></div>
    <div class="flow-branch-col"><div class="flow-branch-label">miss</div><div class="flow-box"><b>Call embedding API</b><span>then save to sqlite</span></div></div>
  </div>
</div>"""),
         ]),
    dict(key="m3", tier="v1", title="M3 — Dense, BM25 & RRF", date="Sep 20–26",
         bars=[("2026-09-20","2026-09-26")],
         goal="Two independent retrieval strategies plus fusion, with numbers proving whether hybrid actually beats dense.",
         sections=[("Learn & practice", M3_TASKS[:4]), ("Infrastructure", M3_TASKS[4:6]), ("Implement", M3_TASKS[6:11]), ("Measure & deliver", M3_TASKS[11:])],
         flows=[
            ("Hybrid retrieval architecture (POST /retrieve)",
             f"""<div class="flow-branch">
  <div class="flow"><div class="flow-box"><b>Query</b></div></div>
  <div class="flow-branch-row" style="margin-top:6px;">
    <div class="flow-branch-col"><div class="flow-branch-label">dense</div>
      <div class="flow">
        <div class="flow-box"><b>Embed query</b><span>Gemini, RETRIEVAL_QUERY</span></div>
        <span class="flow-arrow">&rarr;</span>
        <div class="flow-box"><b>Milvus search</b><span>FLAT + COSINE</span></div>
      </div>
    </div>
    <div class="flow-branch-col"><div class="flow-branch-label">sparse</div>
      <div class="flow-box"><b>BM25 search</b><span>rank_bm25, in-memory</span></div>
    </div>
  </div>
  <span class="flow-arrow" style="transform:rotate(90deg);">&rarr;</span>
  <div class="flow">
    <div class="flow-box"><b>Fusion</b><span>RRF or Weighted</span></div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-box"><b>Resolve</b><span>Postgres join</span></div>
    <span class="flow-arrow">&rarr;</span>
    <div class="flow-box accent"><b>Ranked chunks</b><span>+ per-stage timings</span></div>
  </div>
</div>"""),
            ("RRF scoring (per retriever, per chunk)",
             flow_linear([("Rank in dense list","e.g. #3"),("1/(k+rank)","k=60 default"),("+ same for BM25 list",""),("Sum","per chunk_id"),("Sort descending","")], accent_last=True)),
         ]),
    dict(key="m4", tier="v1", title="M4 — Reranking, Citations & Evaluation → V1", date="Sep 27–Oct 3",
         bars=[("2026-09-27","2026-10-03")],
         goal="Cross-encoder reranking, citation-grounded generation, the full golden set, and the metrics that make V1 shippable.",
         sections=[("Learn & practice", M4_TASKS[:4]), ("Implement", M4_TASKS[4:12]), ("Author & measure", M4_TASKS[12:16]), ("Ship V1", M4_TASKS[16:])],
         flows=[
            ("Two-stage retrieval", flow_linear([("Query",""),("Bi-encoder retrieve","~50 candidates"),("Cross-encoder rerank","precision pass"),("Top-K","to context builder")], accent_last=True)),
            ("Generation & judging", flow_linear([("Reranked chunks",""),("Context builder","dedupe + budget"),("LLM generate","structured + cited"),("LLM judge","faithfulness, correctness")], accent_last=True)),
         ]),
    dict(key="m5", tier="v2", title="M5 — Router & Decomposition", date="Oct 4–6",
         bars=[("2026-10-04","2026-10-06")],
         goal="Questions routed by complexity; multi-part questions decomposed into sub-queries. First use of LangGraph.",
         sections=[("Learn & practice", M5_TASKS[:4]), ("Implement", M5_TASKS[4:8]), ("Measure & deliver", M5_TASKS[8:])],
         flows=[("Routing & decomposition",
             f"""<div class="flow-branch">
  <div class="flow"><div class="flow-box"><b>Query</b></div><span class="flow-arrow">&rarr;</span><div class="flow-diamond">simple or complex?</div></div>
  <div class="flow-branch-row" style="margin-top:6px;">
    <div class="flow-branch-col"><div class="flow-branch-label">simple</div><div class="flow-box"><b>Flat retrieval</b></div></div>
    <div class="flow-branch-col"><div class="flow-branch-label">complex</div>
      <div class="flow">
        <div class="flow-box"><b>Decompose</b><span>sub-queries</span></div>
        <span class="flow-arrow">&rarr;</span>
        <div class="flow-box"><b>Retrieve each</b><span>independently</span></div>
        <span class="flow-arrow">&rarr;</span>
        <div class="flow-box"><b>Merge</b><span>dedupe evidence</span></div>
      </div>
    </div>
  </div>
  <span class="flow-arrow" style="transform:rotate(90deg);">&rarr;</span>
  <div class="flow"><div class="flow-box accent"><b>Generate</b></div></div>
</div>""")]),
    dict(key="m6", tier="v2", title="M6 — Evidence Grading & Refinement", date="Oct 7–9",
         bars=[("2026-10-07","2026-10-09")],
         goal="Evidence graded before generation; weak evidence triggers a bounded retry.",
         sections=[("Learn & practice", M6_TASKS[:3]), ("Implement", M6_TASKS[3:7]), ("Measure & deliver", M6_TASKS[7:])],
         flows=[("Evidence grading loop", flow_decision_loop(
             ("Retrieve",""), "evidence weak?",
             "weak", ["Refine query","retry, bounded"],
             "strong", ["Generate",""]))]),
    dict(key="m7", tier="v2", title="M7 — Claim Verification & Abstention → V2", date="Oct 10–12",
         bars=[("2026-10-10","2026-10-12")],
         goal="Answers decomposed into claims, each verified against cited evidence; unsupported claims revised or triggering abstention.",
         sections=[("Learn & practice", M7_TASKS[:4]), ("Implement", M7_TASKS[4:9]), ("Measure & ship V2", M7_TASKS[9:])],
         flows=[("Claim verification", flow_decision_loop(
             ("Generated answer","extract claims"), "any claim weak?",
             "yes", ["Revise","one attempt"],
             "no (or revise fails)", ["Abstain / Answer","weakest-claim score"]))]),
    dict(key="m8", tier="v3", title="M8 — Version-aware Retrieval, Freshness & Eval Harness", date="Oct 13–23",
         bars=[("2026-10-13","2026-10-23")],
         goal="Answers reflect the current policy; sources are recrawled on a schedule; every improvement is provable against a baseline.",
         sections=[("Learn & decide", M8_TASKS[:5]), ("Implement — version awareness", M8_TASKS[5:9]), ("Implement — freshness & harness", M8_TASKS[9:13]), ("Measure & deliver", M8_TASKS[13:])],
         flows=[
            ("Version-aware query filtering",
             f"""<div class="flow-branch">
  <div class="flow"><div class="flow-box"><b>Query</b></div><span class="flow-arrow">&rarr;</span><div class="flow-diamond">"as of &lt;date&gt;"?</div></div>
  <div class="flow-branch-row" style="margin-top:6px;">
    <div class="flow-branch-col"><div class="flow-branch-label">no (default)</div><div class="flow-box accent"><b>Filter: current</b><span>effective_date</span></div></div>
    <div class="flow-branch-col"><div class="flow-branch-label">yes</div><div class="flow-box"><b>Filter: as-of date</b><span>historical version</span></div></div>
  </div>
  <span class="flow-arrow" style="transform:rotate(90deg);">&rarr;</span>
  <div class="flow"><div class="flow-box"><b>Retrieve</b></div><span class="flow-arrow">&rarr;</span><div class="flow-box"><b>Cite version + date</b></div></div>
</div>"""),
            ("Scheduled recrawl (Airflow DAG)", flow_linear([("Fetch public URL","on schedule"),("Compare hash","vs. last known"),("Changed?",""),("Re-ingest","new version row")], accent_last=True)),
         ]),
    dict(key="m9", tier="v3", title="M9 — Observability, Cost/Latency & Regression Gates", date="Oct 24–Nov 2",
         bars=[("2026-10-24","2026-11-02")],
         goal="Every request traced end to end with per-stage latency and cost; CI blocks a quality regression automatically.",
         sections=[("Learn", M9_TASKS[:3]), ("Implement — observability", M9_TASKS[3:9]), ("Implement — CI gate", M9_TASKS[9:12]), ("Measure & deliver", M9_TASKS[12:])],
         flows=[
            ("Request tracing", flow_linear([("Request","= trace ID = log ID"),("route","span"),("retrieve (dense+sparse)","spans"),("fuse→rerank→grade","spans"),("generate→verify","spans")], accent_last=True)),
            ("CI regression gate", flow_decision_loop(
                ("PR pushed","run fast eval subset"), "metric drop > tolerance?",
                "yes", ["CI fails","delta table posted to PR"],
                "no", ["CI passes",""])),
         ]),
    dict(key="m10", tier="v3", title="M10 — Scale Benchmark, Provider Swap & Polish → V3", date="Nov 3–12",
         bars=[("2026-11-03","2026-11-12")],
         goal="Prove the system holds under scale, prove the provider abstraction is real, and make the repo genuinely readable by a stranger.",
         sections=[("Scale", M10_TASKS[:4]), ("Provider swap", M10_TASKS[4:7]), ("Security & hardening", M10_TASKS[7:11]), ("Ship V3", M10_TASKS[11:])],
         flows=[
            ("Scale benchmark", flow_linear([("Scale corpus","~100k+ chunks"),("HNSW index","param sweep"),("vs. FLAT ground truth",""),("Recall/latency curve","chosen operating point")], accent_last=True)),
            ("Provider swap", flow_linear([("Same chunk text",""),("Gemini embed OR Local embed","adapter swap only"),("Provider-aware cache","no cross-provider leak"),("Milvus index","unchanged")], accent_last=True)),
         ]),
]

TOTAL_DONE = sum(sum(1 for t in m["sections"] for tt in t[1] if tt["done"]) for m in MILESTONES)
TOTAL_TASKS = sum(sum(len(t[1]) for t in m["sections"]) for m in MILESTONES)
PCT = round(TOTAL_DONE / TOTAL_TASKS * 100)

COMMITS = [
    ("92636bb", "docs(D-019): commit incrementally through a milestone, not in one batch"),
    ("b24b109", "feat(T-M3.11): POST /retrieve, with per-stage timings"),
    ("56586cf", "feat(T-M3.10): RRFFusion and WeightedFusion behind one interface"),
    ("41e0316", "feat(T-M3.9): SparseRetriever via rank_bm25"),
    ("839bfbf", "feat(T-M3.8): RetrievalStrategy interface + DenseRetriever"),
    ("939fd1b", "feat(T-M3.7): embedding provider abstraction + Gemini adapter"),
    ("a581c43", "feat(T-M3.6): Milvus collection schema + connection lifecycle"),
    ("c7bb56b", "feat(T-M3.5): add Milvus (etcd + MinIO + standalone) to Docker Compose"),
]

def build_timeline():
    rows_labels, rows_dates, bars = [], [], []
    for i, m in enumerate(MILESTONES):
        rows_labels.append(f'<div class="row"><b>{esc(m["title"].split(" — ")[0])}</b></div>')
        rows_dates.append(f'<div class="row">{esc(m["date"])}</div>')
        done = sum(1 for sec in m["sections"] for t in sec[1] if t["done"])
        total = sum(len(sec[1]) for sec in m["sections"])
        for (s, e) in m["bars"]:
            sd, ed = datetime.date.fromisoformat(s), datetime.date.fromisoformat(e)
            left = off(sd) / SPAN * 100
            width = max((off(ed) - off(sd) + 1) / SPAN * 100, 0.9)
            cls = f'bar bar-{m["tier"]}' + (' complete' if done == total else '')
            top = i * 34 + 8
            bars.append(f'<div class="{cls}" style="left:{left:.2f}%;width:{width:.2f}%;top:{top}px;height:18px;"></div>')
    canvas_h = len(MILESTONES) * 34
    months = [("Aug","2026-08-01"),("Sep","2026-09-01"),("Oct","2026-10-01"),("Nov","2026-11-01")]
    bands = []
    for name, iso in months:
        d = max(datetime.date.fromisoformat(iso), START)
        bands.append(f'<div class="month-band" style="left:{off(d)/SPAN*100:.2f}%;">{name}</div>')
    today_left = off(TODAY) / SPAN * 100
    ship_markers = ""
    for label, iso, cls in [("V1","2026-10-03","v2"),("V2","2026-10-12","v2"),("V3","2026-11-12","v3")]:
        d = datetime.date.fromisoformat(iso)
        left = off(d) / SPAN * 100
        ship_markers += f'<div class="marker" style="left:{left:.2f}%;border-color:var(--{cls});"><span class="marker-label">{label}</span></div>'
    return f"""
<div class="timeline">
  <div class="tl-legend">
    <span><span class="sw sw-p0"></span>P0</span>
    <span><span class="sw sw-v1"></span>V1 track</span>
    <span><span class="sw sw-v2"></span>V2 track</span>
    <span><span class="sw sw-v3"></span>V3 track</span>
  </div>
  <div class="tl">
    <div class="tl-labels"><div class="month-row"></div>{''.join(rows_labels)}</div>
    <div class="tl-dates"><div class="month-row"></div>{''.join(rows_dates)}</div>
    <div class="tl-canvas-wrap">
      <div class="month-row">{''.join(bands)}</div>
      <div class="tl-canvas" style="height:{canvas_h}px;">
        {''.join(bars)}
        {ship_markers}
        <div class="today-line" style="left:{today_left:.2f}%;"><span>Today</span></div>
      </div>
    </div>
  </div>
</div>
"""

def build_task_item(t):
    checked = " checked" if t["done"] else ""
    details = f'<p><b>What:</b> {esc(t["what"])}</p><p><b>Layman:</b> {esc(t["layman"])}</p><p><b>Technical:</b> {esc(t["technical"])}</p>'
    if t["table"]:
        details += t["table"]
    if t["type"] in CODE_TYPES:
        if t["commits"]:
            items = "".join(f'<li><input type="checkbox" checked disabled/> <span class="commit-hash">{h}</span> {esc(m)}</li>' for h, m in t["commits"])
            details += f'<ul class="commit-list">{items}</ul>'
        elif t["done"]:
            details += '<p class="commit-none">Squashed into the milestone merge commit — predates the per-task commit policy (D-019).</p>'
        else:
            details += '<p class="commit-none">No commits yet.</p>'
    return f"""<li class="task-list-item">
<input type="checkbox"{checked} disabled/>
<div class="task-head">{tag(t['type'])} <span class="tid">{esc(t['id'])}</span> <span class="ttitle">{esc(t['title'])}</span></div>
<details class="why-box"><summary>What · layman · technical{' · commits' if t['type'] in CODE_TYPES else ''}</summary>
<div class="why-inner">{details}</div></details>
</li>"""

def build_milestone(m):
    all_tasks = [t for sec in m["sections"] for t in sec[1]]
    done = sum(1 for t in all_tasks if t["done"])
    total = len(all_tasks)
    pct = round(done / total * 100) if total else 0
    flows_html = ""
    for label, html in m["flows"]:
        flows_html += f'<div class="ms-section-title">{esc(label)}</div>{html}'
    sections_html = ""
    for sec_title, tasks in m["sections"]:
        sec_done = sum(1 for t in tasks if t["done"])
        sections_html += f'<div class="ms-section-title">{esc(sec_title)} <span class="sec-progress">({sec_done}/{len(tasks)})</span></div>'
        sections_html += f'<ul class="task-list">{"".join(build_task_item(t) for t in tasks)}</ul>'
    return f"""
<div class="ms tier-{m['tier']}">
  <div class="ms-head">
    <div class="ms-head-left">
      <span class="pill tier-pill-{m['tier']}">{m['tier'].upper()}</span>
      <h2 style="margin:0;">{esc(m['title'])}</h2>
    </div>
    <span class="ms-date">{esc(m['date'])} &nbsp;&middot;&nbsp; {done}/{total} ({pct}%)</span>
  </div>
  <div class="ms-goal">{esc(m['goal'])}</div>
  {flows_html}
  {sections_html}
</div>
"""

def build_commit_pills():
    pills = "".join(f'<span class="pill"><code>{h}</code> {esc(msg)}</span>' for h, msg in COMMITS)
    return f'<div class="commit-pills">{pills}</div>'

def build_tag_legend():
    items = "".join(f'<span class="tag" style="--tag:{c};">{t}</span>' for t, c in TYPE_COLORS.items())
    return f'<div class="tag-legend"><span class="tag-legend-label">Task types:</span>{items}</div>'

body = f"""<title>no-cap-rag — Advanced RAG Build Blueprint</title>
<style>{CSS}</style>
<div class="wrap">

<div class="header">
  <h1>no-cap-rag — Advanced RAG Build Blueprint</h1>
  <div class="sub">Retail-domain retrieval-augmented generation, built end to end. Each task below is a checklist item — expand it for what/layman/technical, real tables where the content is genuinely tabular, and a commit checklist for code tasks.</div>
  {build_commit_pills()}
  <div class="progress-wrap">
    <div class="progress-bar"><div class="progress-fill" style="width:{PCT}%;"></div></div>
    <div class="progress-label">{TOTAL_DONE} / {TOTAL_TASKS} tasks complete ({PCT}%)</div>
  </div>
  {build_tag_legend()}
  <div class="rebase-note"><b>Rebased 5 Sep 2026</b> — original targets were 21/30 Sep; repo &amp; GitHub setup ran long, so every milestone date shifted by the same ~12 days rather than compressing durations.</div>
  <div class="commit-note"><b>Commit policy (D-019):</b> from M3 onward, each coding task gets its own commit as it lands — not batched at the end of the milestone. Expand a task to see its commit checklist.</div>
</div>

{build_timeline()}

{''.join(build_milestone(m) for m in MILESTONES)}

<footer>no-cap-rag — a portfolio RAG build.</footer>

</div>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(body)

print("wrote", OUT, len(body), "chars")
print("TOTAL_DONE", TOTAL_DONE, "TOTAL_TASKS", TOTAL_TASKS, "PCT", PCT)
