"""A translation overlay: the Bahasa Melayu for every sentence of one Plan (W12, D-62).

An overlay is a flat map from a place in the Plan (a JSON pointer such as `/steps/0` or `/readouts/1/label`) to the translated text. Applying it to a Plan gives a Plan in Bahasa Melayu
with the same ids, units, numbers, models and ranges, so the plan checks, the assembler, the verifier and the delivery gate treat it exactly like the English Plan. Nothing here can
change a number: the overlay checks refuse a translation whose digits differ from the English, a missing or an extra sentence, and a text that is still English.

Review: an overlay is `draft` until a person who reads Bahasa Melayu has approved every string. `reviewed` needs a reviewer name and a date; a file that says `reviewed` without
them is refused. Only the review changes the status; the build assistant writes drafts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from api.pipeline.plan import Plan

OVERLAYS = Path(__file__).resolve().parents[2] / "data" / "i18n" / "ms"

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_WORD = re.compile(r"[A-Za-z]{2,}")


class OverlayError(ValueError):
    """The overlay cannot be used. The message lists every problem found."""


@dataclass(frozen=True)
class Overlay:
    plan: str
    lang: str
    status: str
    reviewer: str | None
    reviewed_on: str | None
    strings: dict[str, str]

    @property
    def reviewed(self) -> bool:
        return self.status == "reviewed"


def translatable(plan: Plan) -> dict[str, str]:
    """Every place in the Plan that holds words a student reads, by pointer. Units, ids and the symbols of a formula stay as they are, and so do `custom` slots (model-written code)."""
    out: dict[str, str] = {"/title": plan.title, "/goal": plan.goal, "/note": plan.note}
    for i, c in enumerate(plan.controls):
        out[f"/controls/{i}/label"] = c.label
    for i, k in enumerate(plan.constants):
        out[f"/constants/{i}/label"] = k.label
    for i, r in enumerate(plan.readouts):
        out[f"/readouts/{i}/label"] = r.label
    for i, g in enumerate(plan.graphs):
        out[f"/graphs/{i}/title"] = g.title
        out[f"/graphs/{i}/label"] = g.label
    for i, part in enumerate(plan.apparatus):
        out[f"/apparatus/{i}/label"] = part.label
        if part.drop is not None:
            out[f"/apparatus/{i}/drop/item"] = part.drop.item
    if plan.table:
        out["/table/caption"] = plan.table.caption
        for i, col in enumerate(plan.table.columns):
            out[f"/table/columns/{i}/label"] = col.label
    if plan.experiment:
        e = plan.experiment
        out["/experiment/aim"] = e.aim
        out["/experiment/hypothesis"] = e.hypothesis
        out["/experiment/independent"] = e.independent
        out["/experiment/dependent"] = e.dependent
        for i, text in enumerate(e.controlled):
            out[f"/experiment/controlled/{i}"] = text
        for i, text in enumerate(e.apparatus):
            out[f"/experiment/apparatus/{i}"] = text
    for i, text in enumerate(plan.sentences):
        out[f"/sentences/{i}"] = text
    for i, text in enumerate(plan.steps):
        out[f"/steps/{i}"] = text
    for i, text in enumerate(plan.hints):
        out[f"/hints/{i}"] = text
    for i, text in enumerate(plan.worked_solution):
        out[f"/worked_solution/{i}"] = text
    if plan.predict:
        out["/predict/prompt"] = plan.predict.prompt
        for i, text in enumerate(plan.predict.choices):
            out[f"/predict/choices/{i}"] = text
        out["/predict/reveal"] = plan.predict.reveal
    if plan.concept_check:
        out["/concept_check/question"] = plan.concept_check.question
        for i, text in enumerate(plan.concept_check.options):
            out[f"/concept_check/options/{i}"] = text
        out["/concept_check/explanation"] = plan.concept_check.explanation
    return out


def load(path: Path) -> Overlay:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) - {"plan", "lang", "status", "reviewer", "reviewed_on", "strings"}:
        raise OverlayError(f"{path.name}: the file has fields an overlay does not have")
    strings = raw.get("strings")
    if not isinstance(strings, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in strings.items()):
        raise OverlayError(f"{path.name}: strings must map a place to a text")
    overlay = Overlay(
        plan=str(raw.get("plan", "")),
        lang=str(raw.get("lang", "")),
        status=str(raw.get("status", "")),
        reviewer=raw.get("reviewer"),
        reviewed_on=raw.get("reviewed_on"),
        strings=strings,
    )
    if overlay.lang != "ms":
        raise OverlayError(f"{path.name}: lang must be 'ms'")
    if overlay.status not in ("draft", "reviewed"):
        raise OverlayError(f"{path.name}: status must be 'draft' or 'reviewed'")
    if overlay.reviewed and not (overlay.reviewer and overlay.reviewed_on):
        raise OverlayError(f"{path.name}: a reviewed translation names its reviewer and the date")
    return overlay


def load_for(plan_id: str, directory: Path | None = None) -> Overlay | None:
    path = (directory or OVERLAYS) / f"{plan_id}.json"
    return load(path) if path.exists() else None


def _numbers(text: str) -> list[str]:
    return sorted(_NUMBER.findall(text))


def problems(plan: Plan, overlay: Overlay) -> list[str]:
    """Why this overlay cannot be applied to this Plan, or an empty list."""
    out: list[str] = []
    if overlay.plan != plan.id:
        out.append(f"the overlay is for '{overlay.plan}', not '{plan.id}'")
    want = translatable(plan)
    for pointer in sorted(set(want) - set(overlay.strings)):
        out.append(f"missing {pointer}")
    for pointer in sorted(set(overlay.strings) - set(want)):
        out.append(f"extra {pointer}: the Plan has nothing there")
    for pointer, english in want.items():
        malay = overlay.strings.get(pointer)
        if malay is None:
            continue
        if malay.strip() == "":
            out.append(f"{pointer} is empty")
            continue
        if _numbers(malay) != _numbers(english):
            out.append(f"{pointer}: the digits differ from the English ({_numbers(english)} against {_numbers(malay)})")
        # Three or more words left exactly as the English were not translated. A short label ("pH", "Eye") may legitimately stay.
        if malay == english and len(_WORD.findall(english)) >= 3:
            out.append(f"{pointer} is still English")
    return out


def apply(plan: Plan, overlay: Overlay) -> Plan:
    """The Plan with every string replaced. Raises OverlayError listing every problem, including a text the Plan's own limits refuse (a Malay sentence that is too long)."""
    found = problems(plan, overlay)
    if found:
        raise OverlayError(f"{plan.id}: " + "; ".join(found))
    data: dict[str, Any] = plan.model_dump(mode="python")
    for pointer, text in overlay.strings.items():
        _set(data, pointer, text)
    try:
        return Plan.model_validate(data)
    except ValidationError as exc:
        where = "; ".join(f"{'/'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
        raise OverlayError(f"{plan.id}: the translated Plan is not valid ({where})") from exc


def _set(data: Any, pointer: str, text: str) -> None:
    parts = pointer.lstrip("/").split("/")
    node = data
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = text
    else:
        node[last] = text
