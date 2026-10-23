"""L4, the wording check: what a second model is shown, and how its verdict is read (D-41).

Code cannot judge a sentence. L1 proves where the NUMBERS on a page come from; a note that says "extension is inversely proportional to the load" has no
number and passes every code layer (the L6 row `page-false-prose`). L4 asks a model to read the words. It is a model check, never a proof, and it is
claimed as the layer `wording` only when a real judge answered ok (the mint is told by a flag; fake runs never set it).

This module holds the pure parts: the lines of prose in a Plan, the visible text and script of a Free page, and a strict, fail-closed reader for the
judge's reply. The call itself goes through the pipeline's `_Run.complete`, so it counts against the request budget and the spend ledger.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser

from api.pipeline.plan import Plan

MAX_LINES = 80
MAX_LINE_CHARS = 400
MAX_SCRIPT_CHARS = 12000
MAX_ISSUES = 8
MAX_ISSUE_CHARS = 200


class UnusableVerdict(ValueError):
    """The judge's reply was not a verdict we can read. The caller treats this as 'not checked', never as a pass."""


@dataclass(frozen=True)
class WordingVerdict:
    ok: bool
    issues: tuple[str, ...]


def _clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= MAX_LINE_CHARS else text[: MAX_LINE_CHARS - 1] + "…"


def plan_summary(plan: Plan) -> str:
    """One line saying what the Environment is, for the judge. Titles and goals are ours (from the Plan); no student text."""
    models = ", ".join(sorted({m.model for m in plan.models}))
    return _clip(f"{plan.title}. {plan.goal} (topic {plan.topic}; science models {models})")


def plan_texts(plan: Plan) -> list[str]:
    """Every line of prose or label a student reads, one per line and tagged with where it appears. Units are kept: 'a unit used differently' is
    one of the things the judge looks for. Fills are code, not prose, and are not included (the fill contract checks them)."""
    lines: list[str] = [f"title: {plan.title}", f"goal: {plan.goal}", f"note: {plan.note}"]
    lines += [f"sentence: {s}" for s in plan.sentences]
    lines += [f"step: {s}" for s in plan.steps]
    lines += [f"hint: {h}" for h in plan.hints]
    lines += [f"worked solution step: {s}" for s in plan.worked_solution]
    for c in plan.controls:
        lines.append(f"control: {c.label} [{c.unit}] from {c.min:g} to {c.max:g}, starts at {c.value:g}")
    for k in plan.constants:
        lines.append(f"constant: {k.label} = {k.value:g} [{k.unit}]")
    for r in plan.readouts:
        lines.append(f"readout: {r.label} [{r.unit}]")
    for g in plan.graphs:
        lines.append(f"graph: {g.title} (y is {g.label} [{g.unit}])")
    if plan.table is not None:
        cols = "; ".join(f"{c.label} [{c.unit}]" for c in plan.table.columns)
        lines.append(f"table: {plan.table.caption}: {cols}")
    if plan.experiment is not None:
        e = plan.experiment
        lines += [
            f"experiment aim: {e.aim}",
            f"experiment hypothesis: {e.hypothesis}",
            f"experiment independent variable: {e.independent}",
            f"experiment dependent variable: {e.dependent}",
            f"experiment controlled variables: {', '.join(e.controlled)}",
            f"experiment apparatus: {', '.join(e.apparatus)}",
        ]
    if plan.predict is not None:
        p = plan.predict
        lines += [f"prediction question: {p.prompt}", f"prediction choices: {' | '.join(p.choices)}", f"prediction reveal: {p.reveal}"]
    if plan.concept_check is not None:
        cc = plan.concept_check
        options = " | ".join(f"{o}{' (marked correct)' if i == cc.correct else ''}" for i, o in enumerate(cc.options))
        lines += [f"check question: {cc.question}", f"check options: {options}", f"check explanation: {cc.explanation}"]
    return [_clip(line) for line in lines][:MAX_LINES]


_SKIP = frozenset({"script", "style", "noscript", "template"})


class _PageText(HTMLParser):
    """The text a student can read in a static page: text nodes outside script and style, plus the names assistive technology reads. The inline script
    is collected apart, because in a Free page the formulas are in the script and not in the text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.scripts: list[str] = []
        self._stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack.append(tag)
        for name, value in attrs:
            if name in ("aria-label", "alt", "title") and value and value.strip():
                self.lines.append(f"{name}: {value}")

    def handle_endtag(self, tag: str) -> None:
        while self._stack:
            if self._stack.pop() == tag:
                break

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        top = self._stack[-1] if self._stack else ""
        if top == "script":
            self.scripts.append(data)
        elif top not in _SKIP:
            self.lines.append(data)


def _parsed(html: str) -> _PageText:
    p = _PageText()
    p.feed(html)
    p.close()
    return p


def page_texts(html: str) -> list[str]:
    """The visible words of a Free page, one per line, consecutive repeats collapsed. Nothing is cut: `unread` says when a page is too big to be read whole."""
    out: list[str] = []
    for raw in _parsed(html).lines:
        line = " ".join(raw.split())
        if line and (not out or out[-1] != line):
            out.append(line)
    return out


# Quoted strings are kept whole (a `//` inside one is not a comment); block and line comments are dropped. A reader's input, not a parser: a regular-expression
# literal holding `//` would be cut short, which only removes text and so can hide nothing that was not a comment.
_JS_TOKEN = re.compile(r"""("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)|/\*.*?\*/|//[^\n]*""", re.DOTALL)


def strip_js_comments(script: str) -> str:
    return _JS_TOKEN.sub(lambda m: m.group(1) or "", script)


def page_script(html: str) -> str:
    """The page's inline script with its comments removed (a comment is the easiest place to talk to a judge), so the judge reads the formulas a Free page
    computes with and not a note addressed to it. Nothing is cut: `unread` says when a script is too long to be read whole."""
    return "\n".join(strip_js_comments(s).strip() for s in _parsed(html).scripts).strip()


def unread(html: str) -> str | None:
    """Why a Free page cannot be read whole by the judge, or None. A page the judge would see only part of must not earn the claim that its words and formulas
    were read, so it is refused instead of cut."""
    if len(page_script(html)) > MAX_SCRIPT_CHARS:
        return f"the script is longer than the {MAX_SCRIPT_CHARS} characters the reader takes"
    lines = page_texts(html)
    if len(lines) > MAX_LINES:
        return f"the page has more than {MAX_LINES} lines of text"
    if any(len(line) > MAX_LINE_CHARS for line in lines):
        return f"a line of text is longer than {MAX_LINE_CHARS} characters"
    return None


def numbered(lines: list[str]) -> str:
    return "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def parse_verdict(raw: str) -> WordingVerdict:
    """Read the judge's reply: exactly {"ok": bool, "issues": [str, ...]}. Anything else raises `UnusableVerdict`.

    Fail closed on contradictions: `ok: true` with issues listed is not a pass, and `ok: false` with no issue is a refusal that says so."""
    text = raw.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise UnusableVerdict("the reply is not JSON") from exc
    if not isinstance(data, dict) or set(data) != {"ok", "issues"}:
        raise UnusableVerdict('the reply must be an object with exactly "ok" and "issues"')
    ok, issues = data["ok"], data["issues"]
    if not isinstance(ok, bool):
        raise UnusableVerdict('"ok" must be true or false')
    if not isinstance(issues, list) or not all(isinstance(i, str) for i in issues):
        raise UnusableVerdict('"issues" must be a list of strings')
    kept = tuple(" ".join(i.split())[:MAX_ISSUE_CHARS] for i in issues if i.strip())[:MAX_ISSUES]
    if ok and kept:
        return WordingVerdict(False, kept)
    if not ok and not kept:
        return WordingVerdict(False, ("the wording check refused without saying why",))
    return WordingVerdict(ok, kept)
