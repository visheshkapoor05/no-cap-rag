"""
The filing clerk: splits a document's already-extracted text into
retrievable chunks along its own heading structure, not blindly every N
tokens — with guards so an oversized section gets split further and a
tiny one gets merged into a neighbour. See ../../ANALOGY.md.

Guard thresholds (MIN/MAX) are a real starting point, not a guess: derived
from T-M2.3's practice run against 3 real documents, where structure-aware
sections landed 70-320 tokens with two genuine outliers at 350/408 —
revisit once T-M2.10's full-corpus chunk statistics land.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import tiktoken

MIN_CHUNK_TOKENS = 40
MAX_CHUNK_TOKENS = 350

_ENC = tiktoken.get_encoding("cl100k_base")
_HEADING_RE = re.compile(r"^(#{2,3})\s+(.*)$")
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


@dataclass(frozen=True)
class Chunk:
    text: str
    token_count: int
    section_path: str  # heading breadcrumb within the document, e.g.
    # "3. Category-Specific Exceptions > 3.2 Discounted Items". Empty for
    # text before the first heading (frontmatter/banner/title).


@dataclass
class _Section:
    breadcrumb: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()

    @property
    def section_path(self) -> str:
        return " > ".join(self.breadcrumb)


def _split_into_sections(text: str) -> list[_Section]:
    """One leaf section per heading, at *any* level (## or ###) — an H2
    with H3 children naturally becomes multiple leaves: the H2's own intro
    text (if any) as one leaf, then one leaf per H3 child. No special-casing
    for "does this section have sub-headings" — walking every heading level
    up front already produces the finest structural granularity."""
    sections: list[_Section] = []
    breadcrumb: list[str] = []
    current = _Section()

    for line in text.split("\n"):
        match = _HEADING_RE.match(line)
        if match is None:
            current.lines.append(line)
            continue

        if current.text:
            sections.append(current)

        level = len(match.group(1))  # 2 (##) or 3 (###)
        heading_text = match.group(2).strip()
        breadcrumb = [heading_text] if level == 2 else [*breadcrumb[:1], heading_text]
        current = _Section(breadcrumb=list(breadcrumb), lines=[line])

    if current.text:
        sections.append(current)

    return sections


def _split_sentences(paragraph: str) -> list[str]:
    """Last-resort fallback for a single paragraph that's still over the
    cap on its own — rare, but a real possibility, not assumed away."""
    if count_tokens(paragraph) <= MAX_CHUNK_TOKENS:
        return [paragraph]
    pieces: list[str] = []
    buffer = ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if count_tokens(candidate) <= MAX_CHUNK_TOKENS or not buffer:
            buffer = candidate
        else:
            pieces.append(buffer)
            buffer = sentence
    if buffer:
        pieces.append(buffer)
    return pieces


def _split_oversized(section: _Section) -> list[_Section]:
    """A leaf section over MAX_CHUNK_TOKENS falls back to paragraph-boundary
    splitting (the same logic as the recursive-character strategy), and any
    single paragraph still too big after that falls back to sentence
    boundaries. Every resulting piece keeps the same section_path — they're
    still all "part of" this heading, just split further for size."""
    if count_tokens(section.text) <= MAX_CHUNK_TOKENS:
        return [section]

    pieces: list[_Section] = []
    buffer = ""
    for para in re.split(r"\n\s*\n", section.text):
        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if count_tokens(candidate) <= MAX_CHUNK_TOKENS:
            buffer = candidate
            continue
        if buffer:
            pieces.append(_Section(breadcrumb=section.breadcrumb, lines=buffer.split("\n")))
            buffer = ""
        if count_tokens(para) <= MAX_CHUNK_TOKENS:
            buffer = para
        else:
            for sub in _split_sentences(para):
                pieces.append(_Section(breadcrumb=section.breadcrumb, lines=sub.split("\n")))
    if buffer:
        pieces.append(_Section(breadcrumb=section.breadcrumb, lines=buffer.split("\n")))
    return pieces


def _merge_breadcrumbs(a: list[str], b: list[str]) -> list[str]:
    """Combines two breadcrumbs being merged together, without silently
    dropping either heading's identity. If one is empty (the no-heading
    preamble), the other wins outright. If they share a parent (e.g. a
    tiny "## 3. Exceptions" intro merging into its own child "### 3.1
    Electronics"), the shared parent is kept once and the more specific
    leaf(ves) are combined — merging two real, differently-named H3
    subsections should still show both labels, not silently keep only one
    (found by testing against returns-policy-v3.0.md: naively keeping just
    "the earlier breadcrumb" made 3.1 Electronics's content vanish under a
    bare "3. Exceptions" label once it got absorbed)."""
    if not a:
        return b
    if not b:
        return a
    if a == b:
        return a
    if a[:1] == b[:1]:
        if len(a) == 1:  # a is the parent-only intro -- the more specific child wins
            return b
        if len(b) == 1:
            return a
        leaves = a[-1] if a[-1] == b[-1] else f"{a[-1]}; {b[-1]}"
        return [a[0], leaves]
    return a if len(a) >= len(b) else b


def _merge_undersized(sections: list[_Section]) -> list[_Section]:
    """A section under MIN_CHUNK_TOKENS merges into the next sibling in
    document order — a short leading section (or the frontmatter/banner
    preamble, which has no heading at all) reads naturally as a preamble to
    what follows. The last section in the document has no "next", so it
    merges backward into the previous one instead.
    """
    merged: list[_Section] = []
    i = 0
    while i < len(sections):
        section = sections[i]
        if len(sections) == 1 or count_tokens(section.text) >= MIN_CHUNK_TOKENS:
            merged.append(section)
            i += 1
            continue

        if i + 1 < len(sections):
            nxt = sections[i + 1]
            sections[i + 1] = _Section(
                breadcrumb=_merge_breadcrumbs(section.breadcrumb, nxt.breadcrumb),
                lines=[*section.lines, "", *nxt.lines],
            )
        elif merged:
            prev = merged.pop()
            merged.append(
                _Section(
                    breadcrumb=_merge_breadcrumbs(prev.breadcrumb, section.breadcrumb),
                    lines=[*prev.lines, "", *section.lines],
                )
            )
        else:
            merged.append(section)
        i += 1
    return merged


def chunk_structure_aware(text: str) -> list[Chunk]:
    """Splits already-extracted document text into chunks along its own
    ##/### heading structure, with guards so no chunk ends up wildly over
    MAX_CHUNK_TOKENS or under MIN_CHUNK_TOKENS where a guard can help.
    Strips a leading YAML frontmatter block first -- it's metadata already
    captured separately at ingestion (T-M1.6/T-M1.9's frontmatter parsing),
    not retrievable prose content, and leaving it in artificially inflates
    the preamble chunk past the merge threshold it should actually fall
    under."""
    text = _FRONTMATTER_RE.sub("", text, count=1)
    sections = _split_into_sections(text)

    sized: list[_Section] = []
    for section in sections:
        sized.extend(_split_oversized(section))

    sized = _merge_undersized(sized)

    return [
        Chunk(text=s.text, token_count=count_tokens(s.text), section_path=s.section_path)
        for s in sized
        if s.text
    ]
