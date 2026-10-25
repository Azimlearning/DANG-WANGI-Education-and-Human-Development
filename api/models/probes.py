"""Probes: one hand-written follow-up question for each flagship misconception (W5a). Host UI, not an Environment: plain text a student answers, so nothing
here is verified by the verifier and nothing here is HTML. Because of that the data is checked strictly when it is loaded, and a bad file stops the server at
start instead of showing a student a broken or misleading card. The source status shown with a probe is copied from the misconception entry it belongs to.

A match is a topic detector (see misconceptions.py), so a probe is offered as a question about an idea, never as a diagnosis of the student.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from api.models.misconceptions import default_matcher

DATA = Path(__file__).resolve().parents[2] / "data" / "probes.json"
MISCONCEPTIONS = Path(__file__).resolve().parents[2] / "data" / "misconceptions.json"
# Chosen from the threshold sweep on 2026-10-25 (refdocs/evidence/2026-10-25-w5a-probe-threshold.md): every positive statement of the three flagship
# misconceptions is still matched, and 3 of the 30 quiet questions in the probe set fire. A same-author probe set, not students.
PROBE_MIN_SCORE = 3.0

_DASHES = re.compile("[–—]")
Text = Annotated[str, StringConstraints(min_length=10, max_length=260)]
Option = Annotated[str, StringConstraints(min_length=3, max_length=140)]


class Probe(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    id: str
    question: Text
    options: list[Option] = Field(min_length=2, max_length=4)
    correct: int = Field(ge=0)
    explanation: Annotated[str, StringConstraints(min_length=20, max_length=420)]

    @model_validator(mode="after")
    def _checks(self) -> Probe:
        if self.correct >= len(self.options):
            raise ValueError(f"probe {self.id}: correct index {self.correct} is not one of the {len(self.options)} options")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"probe {self.id}: two options are the same")
        for text in (self.question, self.explanation, *self.options):
            if _DASHES.search(text):
                raise ValueError(f"probe {self.id}: no em dash or en dash in student text (CLAUDE.md rule 8)")
        return self


def basis_of(verified: bool) -> str:
    """What the correction rests on, in the words a student reads. Copied from the entry's `source_verified`, never typed."""
    if verified:
        return "This correction rests on a reference that was checked against its source."
    return (
        "This correction is the assistant's own wording of a standard idea. Its reference was not checked against a textbook, "
        "and no teacher has reviewed it yet."
    )


def load(path: Path = DATA, entries_path: Path = MISCONCEPTIONS) -> dict[str, tuple[Probe, bool]]:
    """Probe id to (probe, the entry's source_verified). Raises ValueError for anything that is not exactly right."""
    entries = {e["id"]: e for e in json.loads(entries_path.read_text(encoding="utf-8"))["entries"]}
    out: dict[str, tuple[Probe, bool]] = {}
    for raw in json.loads(path.read_text(encoding="utf-8"))["probes"]:
        probe = Probe.model_validate(raw)
        if probe.id not in entries:
            raise ValueError(f"probe {probe.id} names no misconception entry")
        if probe.id in out:
            raise ValueError(f"probe {probe.id} appears twice")
        out[probe.id] = (probe, bool(entries[probe.id]["source_verified"]))
    return out


@lru_cache(maxsize=1)
def default_probes() -> dict[str, tuple[Probe, bool]]:
    return load()


def probe_for(question: str) -> tuple[Probe, bool] | None:
    """The probe for the best-matching flagship entry at or above the threshold, or None."""
    probes = default_probes()
    for hit in default_matcher().match(question, top=len(probes) + 2, min_score=PROBE_MIN_SCORE):
        if hit.id in probes:
            return probes[hit.id]
    return None
