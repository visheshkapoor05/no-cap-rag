"""Reads the committed golden_set.yaml back into typed records. See ./build.py."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set.yaml"


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    category: str
    question: str
    expected_answer: str | None
    relevant_docs: list[dict]  # [{title, version}, ...] -- natural keys, resolved at use time
    relevant_chunks: list[dict]  # [{title, version, section, text}, ...] -- see resolve.py
    answerable: bool
    difficulty: str
    tags: list[str]


def load_golden_set(path: Path = GOLDEN_SET_PATH) -> list[GoldenQuestion]:
    data = yaml.safe_load(path.read_text())
    return [GoldenQuestion(**q) for q in data["questions"]]
