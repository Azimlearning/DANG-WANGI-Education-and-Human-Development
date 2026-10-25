"""Exam-mirror items (W5c): hand-written structured questions with one marking point per mark. Host text, not an Environment. The student's answer is marked IN THE BROWSER
by matching key words (web/lib/exam.ts); nothing the student writes reaches the server. This module loads and checks the data, and holds a reference implementation of the
same rule, used only to prove that each item's own sample answer earns every mark and that a wrong answer does not.

The rule: a wording is a list of word stems; a point is earned when ALL stems of ANY one wording appear in the answer. A stem made only of digits must equal a whole number
in the answer; any other stem matches a word that starts with it. Words are runs of letters and digits, lower-cased.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from api.schema.generated import ExamEvent, ExamPoint

DATA = Path(__file__).resolve().parents[2] / "data" / "exam_items.json"
TAXONOMY = Path(__file__).resolve().parents[2] / "data" / "kssm_topics.json"
_DASHES = re.compile("[–—]")
_WORD = re.compile(r"[a-z0-9]+")
Stem = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]{1,24}$")]
Sentence = Annotated[str, StringConstraints(min_length=10, max_length=400)]


class Point(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    text: Sentence
    wordings: list[Annotated[list[Stem], Field(min_length=1, max_length=8)]] = Field(min_length=1, max_length=8)


class Item(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]{3,40}$")]
    topic: str
    stem: Annotated[str, StringConstraints(min_length=30, max_length=500)]
    points: list[Point] = Field(min_length=2, max_length=6)
    sample: Annotated[str, StringConstraints(min_length=30, max_length=700)]

    @model_validator(mode="after")
    def _checks(self) -> Item:
        for text in (self.stem, self.sample, *(p.text for p in self.points)):
            if _DASHES.search(text):
                raise ValueError(f"item {self.id}: no em dash or en dash in student text (CLAUDE.md rule 8)")
        for p in self.points:
            if len({tuple(w) for w in p.wordings}) != len(p.wordings):
                raise ValueError(f"item {self.id}: a point lists the same wording twice")
        return self

    @property
    def marks(self) -> int:
        return len(self.points)


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _stem_in(stem: str, ws: list[str]) -> bool:
    return stem in ws if stem.isdigit() else any(w.startswith(stem) for w in ws)


def earned(point: Point, answer: str) -> bool:
    ws = words(answer)
    return any(all(_stem_in(s, ws) for s in wording) for wording in point.wordings)


def mark(item: Item, answer: str) -> tuple[int, list[bool]]:
    got = [earned(p, answer) for p in item.points]
    return sum(got), got


def _topics() -> set[str]:
    return {f"{t['subject']}_form{t['form']}_{t['slug']}" for t in json.loads(TAXONOMY.read_text(encoding="utf-8"))["topics"]}


def load(path: Path = DATA) -> dict[str, Item]:
    """Topic to item. Raises ValueError for anything not exactly right: a bad item, an unknown topic, two items for one topic, or a sample that does not earn full marks."""
    known = _topics()
    out: dict[str, Item] = {}
    for raw in json.loads(path.read_text(encoding="utf-8"))["items"]:
        item = Item.model_validate(raw)
        if item.topic not in known:
            raise ValueError(f"item {item.id}: '{item.topic}' is not a topic the router knows")
        if item.topic in out:
            raise ValueError(f"item {item.id}: topic {item.topic} already has an item")
        score, _ = mark(item, item.sample)
        if score != item.marks:
            raise ValueError(f"item {item.id}: its own sample answer earns {score} of {item.marks} marks")
        out[item.topic] = item
    return out


@lru_cache(maxsize=1)
def default_items() -> dict[str, Item]:
    return load()


def event_for(topic: str) -> ExamEvent | None:
    item = default_items().get(topic)
    if item is None:
        return None
    return ExamEvent(
        type="exam",
        id=item.id,
        stem=item.stem,
        marks=item.marks,
        points=[ExamPoint(text=p.text, wordings=[list(w) for w in p.wordings]) for p in item.points],
        sample=item.sample,
    )
