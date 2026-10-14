# The Blueprint artifact — design spec (read this before touching it)

**Why this file exists:** an earlier session published this artifact, then a
later session (with zero memory of the first) tried to "update" it, couldn't
recover the original content through its tools, and silently rebuilt the
whole thing from scratch with a different structure — without asking first.
That was a real, serious mistake. This file exists so it can never happen
again: everything needed to correctly regenerate or extend this artifact is
written down here and committed to git, which is the one thing that actually
survives between sessions (a conversation's scratchpad does not).

**If you are a future session asked to "update the blueprint artifact":**
1. Read this file completely first.
2. Read `scripts/build_blueprint_artifact.py` — it's the real generator, not
   a description of one. Prefer editing it and re-running it over writing
   new HTML by hand.
3. Do **not** redesign the colors, layout, or content structure on your own
   initiative. If something here seems wrong or incomplete, say so and ask,
   the same way you'd flag an inconsistency in any other committed doc —
   don't silently "fix" it by rebuilding.
4. Update the task `done`/`commits` data to match the real current state of
   `learnings/*/TASKS.md` before regenerating — read those files fresh,
   don't trust this doc's own task list to still be current (it will drift).

---

## 1. What this artifact is

A single-page HTML dashboard tracking all 155 tasks across the project's 11
milestones (P0, M1–M10), built from the real planning documents
(`BLUEPRINT.md`, `DECISIONS.md`, and `learnings/*/TASKS.md`) — not invented
content. It is **not** a 1:1 render of `BLUEPRINT.md`'s markdown; it's a
custom visual tracker that summarizes and restructures that content for
scanning at a glance.

**Published URL:** `https://claude.ai/code/artifact/efa1270a-9743-4c9f-844f-afd686181449`
To update it: republish with `url=` set to this exact address. Omitting
`url=` mints a brand-new artifact at a different link — always pass it.

**Owning conversation:** the artifact belongs to whichever claude.ai account
published it. A session can only update it directly if that session's
conversation originally published it *or* is explicitly given the URL (as
here) — `action: "list"` on the Artifact tool can recover the URL if it's
lost, by title ("no-cap-rag — Advanced RAG Build Blueprint").

---

## 2. The generator script

`scripts/build_blueprint_artifact.py` is the actual source of truth for the
artifact's content. It's a single Python file with no dependencies beyond
the standard library. Running it:

```bash
cd no-cap-rag
python3 scripts/build_blueprint_artifact.py
```

writes `scripts/blueprint_artifact.out.html` (gitignored — it's a build
output, regenerate it, don't commit it). That file is what gets passed to
the Artifact tool's `file_path`, with `url=` set to the address above.

**To update the artifact for real:**
1. Read the real current state of every `learnings/*/TASKS.md` you're
   touching — don't assume the script's embedded task data is still
   accurate, it drifts every time a task gets marked done or a new decision
   changes something.
2. Edit the relevant `T("...")` tuples in the script (see §4 below for the
   exact shape) — update `done`, add `commits`, add a `table` if a task
   gained a real results table.
3. Re-run the script.
4. Sanity-check tag balance before publishing (the script has no built-in
   validator — run something like this, it catches most structural breaks):
   ```bash
   python3 -c "
   c = open('scripts/blueprint_artifact.out.html').read()
   import re
   for t in ['div','table','tbody','thead','tr','ul','li','details']:
       o = len(re.findall(f'<{t}(?:[ >])', c))
       cl = c.count(f'</{t}>')
       print(t, o, cl, 'OK' if o==cl else 'MISMATCH')
   "
   ```
5. Publish via the Artifact tool with `file_path` = the `.out.html` file and
   `url` = the published URL above. Never omit `url`.
6. **You cannot view the published result yourself.** The in-session
   browser tool hits claude.ai's sign-in wall and cannot render private
   artifact content — screenshots/get_page_text will show a generic "sign
   in" placeholder, not the real page. Say this plainly to the user rather
   than pretending you verified it visually. Structural validation (step 4)
   plus careful data accuracy is the real check available to you.

---

## 3. Design system — colors, type, layout

This is a **utilitarian dashboard treatment**, not an editorial/landing-page
treatment — flat surfaces, no gradients except the progress bar fill, no
decorative flourishes. Scannable checklist first, detail on click.

### Color tokens (`:root`, light mode only — no dark mode variant exists yet)

```css
--bg:#fdfefe; --bg-soft:#f2f7f6; --bg-card:#ffffff;
--text:#1c2b29; --muted:#5b7370; --border:#dbe6e4;
--p0:#5b7370; --p0-bg:#eef3f2; --p0-bd:#c3d2cf;
--v1:#0d9488; --v1-bg:#e9f7f4; --v1-bd:#99f6e4; --v1-text:#0f6f64;
--v2:#d9660b; --v2-bg:#fdf2e9; --v2-bd:#f6c393; --v2-text:#9a4f0d;
--v3:#5b5bd6; --v3-bg:#eeeefb; --v3-bd:#c8c8f2; --v3-text:#40409e;
```

- **p0 (slate grey)** — Phase 0 only
- **v1 (teal)** — milestones shipping toward the V1 release (M1–M4)
- **v2 (burnt orange)** — milestones shipping toward V2 (M5–M7)
- **v3 (indigo)** — milestones shipping toward V3 (M8–M10)
- These four are used for: the tier pill on each milestone card, that
  milestone's left border accent, and its bar color on the timeline.

### Task-type tag colors (separate from the tier colors above)

Defined in `TYPE_COLORS` in the script, applied via the `.tag` class's
`--tag` CSS custom property (one shared class, color set per-instance):

| Type | Hex | Type | Hex |
|---|---|---|---|
| LEARN | `#2a78d6` (blue) | MEASURE | `#dc2626` (red) |
| PRACTICE | `#d97706` (amber) | VERIFY | `#059669` (green) |
| DECIDE | `#7c3aed` (violet) | DOCS | `#64748b` (slate) |
| AUTHOR | `#db2777` (pink) | GIT | `#1e293b` (dark slate) |
| BUILD | `#92400e` (brown) | DOCKER | `#0891b2` (cyan) |
| IMPLEMENT | `#0d9488` (teal) | | |

A legend rendering all 12 is shown once in the header (`build_tag_legend()`).

### Typography

System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Inter,
Roboto, sans-serif`), no custom webfonts. h1 1.6rem, h2 1.2rem (milestone
titles), h3 1rem. Body 16px equivalent via the browser default with
line-height 1.55. Monospace (`ui-monospace, Menlo, Consolas, monospace`) for
task IDs, commit hashes, and `<code>`.

### Layout

Single column, `max-width: 1040px`, centered. Sections top to bottom:

1. **Header card** — title, one-line subtitle, commit pills, progress bar,
   type-tag legend, rebase note (amber callout), commit-policy note (teal
   callout)
2. **Timeline card** — horizontal Gantt-style chart, one row per milestone
3. **11 milestone cards**, P0 through M10 in order, each containing:
   - Header row: tier pill + title (left), date range + progress fraction
     (right)
   - One-line goal statement (muted)
   - 1–2 flowcharts (see §5)
   - Task sections (matching each `TASKS.md`'s own `## ` subheadings, e.g.
     "Learn & decide" / "Implement" / "Measure & deliver"), each a
     `<ul class="task-list">` of checklist items

### The task checklist item (the core content unit — read this carefully)

**This is a checklist, not a table.** Each task is one `<li>`:

```html
<li class="task-list-item">
  <input type="checkbox" checked disabled/>          <!-- real GFM-style checkbox -->
  <div class="task-head">
    <span class="tag" style="--tag:#0d9488;">IMPLEMENT</span>
    <span class="tid">T-M3.7</span>
    <span class="ttitle">Embedding provider abstraction + Gemini adapter</span>
  </div>
  <details class="why-box">                          <!-- collapsed by default -->
    <summary>What · layman · technical · commits</summary>
    <div class="why-inner">
      <p><b>What:</b> ...one-line task description...</p>
      <p><b>Layman:</b> ...plain-English translation, no jargon...</p>
      <p><b>Technical:</b> ...the real engineering detail, grounded in the
         actual TASKS.md text and DECISIONS.md where relevant...</p>
      <!-- real embedded table here ONLY if this specific task has
           genuinely tabular content, e.g. T-M3.12's experiment matrix -->
      <ul class="commit-list">                        <!-- only for IMPLEMENT/API/DOCKER/GIT -->
        <li><input type="checkbox" checked disabled/> <span class="commit-hash">939fd1b</span> feat(T-M3.7): ...</li>
      </ul>
    </div>
  </details>
</li>
```

Checked = done (matches the real `[x]`/`[ ]` in `TASKS.md`). The `<details>`
is collapsed by default — this is deliberate, it's what keeps 155 tasks
scannable instead of a wall of text. Never flatten this into a table where
every task's full explanation is always visible at once (that was the
rejected intermediate attempt — it reads as a spreadsheet, not a checklist).

### Tables — use sparingly, only for genuinely tabular content

A table is embedded inside a task's `why-inner` **only** when that specific
task's real content in `TASKS.md` is a table:

| Task | What table | Status |
|---|---|---|
| T-M2.9 | Golden-set category breakdown (6 rows) | real, filled in |
| T-M3.12 | Experiment matrix (4 configs × Recall@1/5/10/MRR) | empty — not measured yet |
| T-M4.1 | Bi-encoder vs cross-encoder comparison | real, filled in |
| T-M4.2 | Precision@5 worked example (D-014's flaw) | real, filled in |
| T-M4.14 | Full benchmark ladder (3 configs × 7 metrics) | empty — not measured yet |
| T-M8.5 | Superseded-document handling, 3 options | real, filled in |

Do not invent a table for a task that doesn't have one in the real planning
docs. "Tables wherever possible" means wherever the *content* is tabular,
not every task.

---

## 4. The `T(...)` task data shape

Every task in the script is built with the `T()` helper:

```python
T(id_, type_, title, what, layman, technical, done, commits=None, table=None)
```

- `id_` — e.g. `"T-M3.7"`, exact match to `TASKS.md`
- `type_` — one of the 12 keys in `TYPE_COLORS` (must match exactly, case-sensitive)
- `title` — short, matches `TASKS.md`'s task title
- `what` — one sentence, the literal task instruction
- `layman` — one sentence, plain English, no jargon, written fresh (not in `TASKS.md`)
- `technical` — 1–3 sentences, grounded in `TASKS.md`'s real description —
  don't invent detail that isn't in the source, condense instead
- `done` — `True`/`False`, matches `[x]`/`[ ]` in `TASKS.md` **right now**
- `commits` — `None`, or a list of `(hash, message)` tuples. Only populate
  with **real git hashes** (check `git log` yourself, never fabricate one).
  Tasks before the D-019 incremental-commit policy (everything before
  T-M3.5) legitimately have no individual commit — the UI shows "squashed
  into the milestone merge commit" for those automatically when `done=True`
  and `commits` is empty; don't invent hashes to fill the gap.
- `table` — `None`, or a raw HTML string (see §3's table rule above)

Milestones are `dict`s with `tasks` grouped into `sections` (mirroring each
`TASKS.md`'s own `##` subheadings) and a `flows` list of
`(label, html_string)` flowchart pairs.

---

## 5. Flowcharts — what exists, what each shows, how to add more

Flowcharts use plain CSS flexbox boxes and arrow characters — **not** SVG
path art, not canvas, not a charting library. Three CSS-driven shapes exist:

- **`flow_linear(steps, accent_last=False)`** — a horizontal chain of boxes
  joined by `→`. Use for a straight pipeline with no branching.
- **`flow_parallel_then_merge(before, branches, after)`** — one box splits
  into N labeled parallel branches, which then merge back into a chain.
  Use for "two things happen independently, then combine" (e.g. M3's
  dense+sparse retrieval).
- **`flow_decision_loop(before, diamond, yes_label, yes_box, no_label, no_box)`**
  — a box feeds a diamond decision point, which branches into two outcomes;
  one side shows a dashed "loop back" hint. Use for grade/retry/revise
  patterns (M6 evidence grading, M7 claim verification, M9's CI gate).

**Current flowcharts, one per milestone (two where the milestone genuinely
has two distinct sub-flows):**

| Milestone | Flowchart(s) |
|---|---|
| P0 | Request lifecycle (linear) |
| M1 | Ingestion pipeline (branch: URL/File → extract → hash → dedupe → Postgres) |
| M2 | Chunking pipeline (linear) + embedding cache hit/miss (decision) |
| M3 | Hybrid retrieval architecture (branch: dense+sparse → fusion → resolve) + RRF scoring detail (linear) |
| M4 | Two-stage retrieval (linear) + generation & judging (linear) |
| M5 | Router + decomposition (decision/branch) |
| M6 | Evidence grading loop (decision_loop) |
| M7 | Claim verification (decision_loop) |
| M8 | Version-aware filtering (decision/branch) + scheduled recrawl (linear) |
| M9 | Request tracing (linear) + CI regression gate (decision_loop) |
| M10 | Scale benchmark (linear) + provider swap (linear) |

**To add a new flowchart:** add a `(label, html)` tuple to that milestone's
`flows` list, building the HTML with one of the three builders above. Ground
every box in the real pipeline described in that milestone's `TASKS.md` —
don't invent an architecture that isn't what's actually planned/built.

---

## 6. Timeline (Gantt chart)

Horizontal bar chart, one row per milestone, spanning Aug 18 – Nov 12 2026
(`START`/`END` constants — update `END` if the schedule ever extends).
`TODAY` is a manually-set constant (not computed from the real clock) —
**update it every time you regenerate**, or the red "Today" line will be
wrong. Ship markers (V1/V2/V3 release dates) are hardcoded to Oct 3 / Oct 12
/ Nov 12 — update if `BLUEPRINT.md`'s commitment dates ever change.

Bar color = tier color (p0/v1/v2/v3). A bar is drawn solid+opaque
("complete") only when every task in that milestone's `tasks` list is done.

---

## 7. What's actually done vs. planned (as of the last regeneration)

**Do not trust these numbers without checking `learnings/*/TASKS.md`
yourself** — this section is a snapshot, not a live value.

- P0: 13/13 done
- M1: 13/13 done
- M2: 13/13 done
- M3: 11/14 done (T-M3.12/13/14 open — measure, write up, merge)
- M4–M10: 0/102 done (not started)
- **Total: 50/155 (32%)**

Real commit hashes exist only for T-M3.5 through T-M3.11 (the 7 commits on
`feat/m3-hybrid-retrieval`, one per task, per the D-019 incremental-commit
policy). Everything before that predates the policy and is marked
"squashed at milestone merge." Nothing from M4 onward has started.

---

## 8. Things that went wrong before, and the rule that now prevents each one

| What happened | The rule now |
|---|---|
| A session tried to patch the artifact without being able to read its real prior content (sandboxed iframe, no tool access), silently rebuilt it from scratch with a different structure, and published over the original without asking | **Never silently redesign.** If you can't recover the prior content, say so explicitly and ask before publishing anything. |
| A rebuild turned 155 tasks into one giant table — technically complete but unusable as a checklist | **Checklist structure is load-bearing**, not a style preference — one `<li>` per task, checkbox + tag + title always visible, detail behind `<details>`. Never flatten to an always-expanded table. |
| Layman/technical explanations and task-type tags were dropped in an early rebuild because they "weren't in" what little original content was recoverable | They **are** core requirements now, documented here explicitly (§3, §4) — every task needs both, plus its type tag. |
| Screenshots were silently treated as "verification" when the browser tool was actually hitting a sign-in wall and showing nothing real | **You cannot visually verify this artifact yourself.** Say so. Validate structurally (tag balance) and by data accuracy instead. |
| The artifact's content (task data, commit hashes) was reconstructed from a conversation summary rather than the real `TASKS.md`/`git log` | **Always re-read the real source files** before regenerating — `learnings/*/TASKS.md` for task state, `git log` for commit hashes. Never trust a memory of them. |

---

## 9. Quick reference — regenerate and republish in one pass

```bash
cd no-cap-rag
# 1. Read the real current TASKS.md files for anything that changed.
# 2. Edit scripts/build_blueprint_artifact.py's T(...) tuples accordingly.
# 3. Update TODAY at the top of the script.
python3 scripts/build_blueprint_artifact.py
# 4. Validate tag balance (see §2 step 4 above).
# 5. Publish via the Artifact tool:
#      file_path = no-cap-rag/scripts/blueprint_artifact.out.html
#      url = https://claude.ai/code/artifact/efa1270a-9743-4c9f-844f-afd686181449
```
