"""The house frame for a model-written lab (W20, D-80): the model writes the bench and the words in labelled sections; this module assembles the page.

Why: a whole page designed by a model looked unlike every other lab (its own layout, its own dark theme, no tips) and had more ways to fail the checks (a
slider row under 44 px, a missing aria-valuetext, a readout without a name). Here the page shape, the colours, the controls' markup and their accessibility are
ours, the same for every generated lab: kicker, title, try this, key idea, predict, steps, the bench beside the readouts, what you found, fine control, hints and
an explanation. The model supplies only text, a drawing, a stylesheet for the drawing and a script.

Nothing here makes the page safe or correct. The assembled page goes to the post-processor, the L0 scan, the second reader and the real browser like any Free
page. Every model string is HTML-escaped except the three code sections (DRAWING, STYLE, SCRIPT), which are what the checks are for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

SECTION = re.compile(r"^@@([A-Z]+)\s*$", re.MULTILINE)
REQUIRED = ("TITLE", "TRY", "IDEA", "STEPS", "DRAWING", "CONTROLS", "READOUTS", "SCRIPT", "END")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,39}")
MAX_CONTROLS = 4
MAX_READOUTS = 6
MAX_TEXT = 400


@dataclass(frozen=True)
class Control:
    id: str
    label: str
    min: float
    max: float
    step: float
    value: float
    unit: str


@dataclass(frozen=True)
class Readout:
    id: str
    label: str


@dataclass(frozen=True)
class Lab:
    title: str
    kicker: str
    try_this: str
    idea: list[str]
    predict: tuple[str, list[str], str] | None
    steps: list[str]
    hints: list[str]
    explain: list[str]
    drawing: str
    style: str
    controls: list[Control]
    readouts: list[Readout]
    script: str


def is_sections(raw: str) -> bool:
    """A reply in the sectioned format (it has a DRAWING section), as opposed to a whole document."""
    return bool(re.search(r"^@@DRAWING\s*$", raw, re.MULTILINE))


def _sections(raw: str) -> dict[str, str]:
    marks = list(SECTION.finditer(raw))
    out: dict[str, str] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        out.setdefault(m.group(1), raw[m.end() : end].strip("\n").strip())
    return out


def _lines(text: str) -> list[str]:
    return [" ".join(line.split())[:MAX_TEXT] for line in text.splitlines() if line.strip()]


def _items(text: str) -> list[str]:
    return [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line) for line in _lines(text)]


def _number(text: str) -> float:
    value = float(text)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("not a finite number")
    return value


def parse(raw: str) -> Lab | str:
    """The lab, or the reason the reply is not one (told to the model on its retry)."""
    sec = _sections(raw.replace("\r\n", "\n"))
    missing = [name for name in REQUIRED if name not in sec]
    if missing:
        if "END" in missing and len(missing) == 1:
            return "the reply stopped before @@END (it was cut off); write a shorter lab"
        return "the reply is missing these sections: " + ", ".join("@@" + m for m in missing)
    title = _lines(sec["TITLE"])
    if not title:
        return "@@TITLE is empty"
    controls: list[Control] = []
    for line in _lines(sec["CONTROLS"]):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 7 or not _ID.fullmatch(parts[0]):
            return f"a @@CONTROLS line is not 'id | label | min | max | step | start | unit': {line[:80]}"
        try:
            lo, hi, step, value = (_number(p) for p in parts[2:6])
        except ValueError:
            return f"a @@CONTROLS line has a value that is not a number: {line[:80]}"
        if not (lo < hi and step > 0 and lo <= value <= hi):
            return f"the control '{parts[0]}' needs min < max, a step above 0 and a start inside the range"
        controls.append(Control(parts[0], parts[1][:60] or parts[0], lo, hi, step, value, parts[6][:20]))
    if not 1 <= len(controls) <= MAX_CONTROLS:
        return f"@@CONTROLS must list 1 to {MAX_CONTROLS} controls"
    readouts: list[Readout] = []
    for line in _lines(sec["READOUTS"]):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 2 or not _ID.fullmatch(parts[0]):
            return f"a @@READOUTS line is not 'id | label with unit': {line[:80]}"
        readouts.append(Readout(parts[0], parts[1][:60] or parts[0]))
    if not 1 <= len(readouts) <= MAX_READOUTS:
        return f"@@READOUTS must list 1 to {MAX_READOUTS} readouts"
    ids = [c.id for c in controls] + [r.id for r in readouts]
    if len(set(ids)) != len(ids):
        return "every control and readout needs its own id"
    if "<svg" not in sec["DRAWING"].lower():
        return "@@DRAWING must contain one <svg> drawing of the apparatus"
    if re.search(r"<\s*/?\s*script\b", sec["DRAWING"] + sec.get("STYLE", ""), re.IGNORECASE):
        return "@@DRAWING and @@STYLE must not contain <script>: the code goes in @@SCRIPT"
    if re.search(r"<\s*/?\s*(?:style|script)\b", sec["SCRIPT"], re.IGNORECASE) or "</" in sec.get("STYLE", ""):
        return "@@SCRIPT is plain JavaScript and @@STYLE plain CSS, without tags"
    predict = None
    if sec.get("PREDICT"):
        lines = _lines(sec["PREDICT"])
        choices = [re.sub(r"^\s*[-*•]\s*", "", x) for x in lines if re.match(r"^\s*[-*•]", x)]
        reveal = next((x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("check:")), "")
        question = next((x for x in lines if not re.match(r"^\s*[-*•]", x) and not x.lower().startswith("check:")), "")
        if question and choices:
            predict = (question, choices[:4], reveal)
    return Lab(
        title=title[0][:60],
        kicker=(_lines(sec.get("KICKER", "")) or ["Virtual lab"])[0][:60],
        try_this=" ".join(_lines(sec["TRY"]))[:MAX_TEXT],
        idea=_lines(sec["IDEA"])[:3],
        predict=predict,
        steps=_items(sec["STEPS"])[:6],
        hints=_items(sec.get("HINTS", ""))[:4],
        explain=[" ".join(p.split()) for p in re.split(r"\n\s*\n", sec.get("EXPLAIN", "")) if p.strip()][:4],
        drawing=sec["DRAWING"],
        style=sec.get("STYLE", ""),
        controls=controls,
        readouts=readouts,
        script=sec["SCRIPT"],
    )


HOUSE_CSS = """
:root{--bg:#ffffff;--fg:#2f3a34;--muted:#4f5d57;--accent:#0a776b;--card:#f7f8f4;--border:#d3dace;--bench:#fbfcf8;--try:#8a3340;--step:#6b4aa0;--gold:#8f6100;--goldsoft:#fff8e6;--goldborder:#ecd9a6;color-scheme:light}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#16201c;--fg:#e9efea;--muted:#a4b2ab;--accent:#16b6a3;--card:#0e1512;--border:#34403a;--bench:#121a16;--try:#f0a3ad;--step:#b9a0e6;--gold:#e8b84a;--goldsoft:#2a2414;--goldborder:#5a4a1c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#16201c;--fg:#e9efea;--muted:#a4b2ab;--accent:#16b6a3;--card:#0e1512;--border:#34403a;--bench:#121a16;--try:#f0a3ad;--step:#b9a0e6;--gold:#e8b84a;--goldsoft:#2a2414;--goldborder:#5a4a1c;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main.lab{max-width:1100px;margin:0 auto;padding:16px;display:grid;gap:14px}
.kicker{margin:0;font:700 .75rem/1.2 ui-monospace,Consolas,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
h1{margin:.2rem 0 .3rem;font-size:1.6rem;line-height:1.2}
h2{margin:0 0 .4rem;font-size:1rem;letter-spacing:.02em}
.try{margin:0;padding:10px 14px;border-left:4px solid var(--try);background:var(--card);border-radius:10px}
.try strong{color:var(--try)}
.card{background:var(--card);border:2px solid var(--border);border-radius:18px;padding:10px 16px}
.idea{background:var(--goldsoft);border-color:var(--goldborder)}
.idea h2{color:var(--gold)}
.idea p{margin:.2rem 0}
.top{display:grid;gap:14px;grid-template-columns:1fr}
.steps ol{margin:0;padding-left:1.4rem}
.steps li{padding-left:2px}
.predict ul{margin:.2rem 0 .4rem;padding-left:1.2rem}
summary{cursor:pointer;min-height:44px;display:flex;align-items:center;font-weight:600;color:var(--accent)}
.benchrow{display:grid;gap:14px;grid-template-columns:1fr}
.bench{background:var(--bench);border:2px solid var(--border);border-radius:18px;padding:8px;overflow:hidden}
.bench svg{display:block;width:100%;height:auto;max-height:520px;touch-action:none}
.side{display:grid;gap:12px;align-content:start}
.readouts{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(140px,1fr))}
.readout{background:var(--card);border:2px solid var(--border);border-radius:14px;padding:8px 12px}
.readout .name{font-size:.85rem;color:var(--muted)}
.readout output{display:block;font-size:1.35rem;font-weight:700;font-variant-numeric:tabular-nums}
.found{margin:0;border-color:var(--accent)}
.found:empty{display:none}
.fine summary{font-size:.9rem;color:var(--muted)}
.row{display:grid;grid-template-columns:minmax(90px,auto) 1fr;align-items:center;gap:10px;min-height:44px}
.row label{font-size:.9rem;color:var(--muted)}
.row input[type=range]{width:100%;min-height:44px;accent-color:var(--accent)}
.hints details{border-top:1px solid var(--border)}
.hints details:first-of-type{border-top:0}
.explain p{margin:.3rem 0}
@media (min-width:760px){.top{grid-template-columns:1.2fr 1fr}.benchrow{grid-template-columns:minmax(0,1.6fr) minmax(260px,1fr)}}
"""

# The page's own script: the theme the host posts (the Kit accepts the same one message), and each control's spoken value, kept in step with the control.
HOUSE_SCRIPT = """
addEventListener("message", function (e) {
  var d = e.data;
  if (d && typeof d === "object" && d.type === "synapse_theme" && (d.theme === "light" || d.theme === "dark")) document.documentElement.setAttribute("data-theme", d.theme);
});
Array.prototype.forEach.call(document.querySelectorAll("input[data-synapse-control]"), function (el) {
  function say() { el.setAttribute("aria-valuetext", el.value + (el.dataset.unit ? " " + el.dataset.unit : "")); }
  el.addEventListener("input", say);
  say();
});
"""


def _num(v: float) -> str:
    return f"{v:g}"


def assemble(lab: Lab) -> str:
    """The whole page, in the house layout and colours."""
    e = escape
    idea = "".join(f"<p>{e(x)}</p>" for x in lab.idea)
    steps = "".join(f"<li>{e(x)}</li>" for x in lab.steps)
    predict = ""
    if lab.predict is not None:
        q, choices, reveal = lab.predict
        items = "".join(f"<li>{e(c)}</li>" for c in choices)
        check = f"<details><summary>Check your prediction</summary><p>{e(reveal)}</p></details>" if reveal else ""
        predict = f'<section class="card predict"><h2>Predict first</h2><p>{e(q)}</p><ul>{items}</ul>{check}</section>'
    readouts = "".join(
        f'<div class="readout"><div class="name" id="{r.id}-name">{e(r.label)}</div>'
        f'<output id="{r.id}" data-synapse-readout="{r.id}" aria-labelledby="{r.id}-name"></output></div>'
        for r in lab.readouts
    )
    rows = "".join(
        f'<div class="row"><label for="{c.id}">{e(c.label)}</label>'
        f'<input type="range" id="{c.id}" data-synapse-control="{c.id}" min="{_num(c.min)}" max="{_num(c.max)}" step="{_num(c.step)}" value="{_num(c.value)}"'
        f' data-unit="{e(c.unit)}" aria-valuetext="{_num(c.value)} {e(c.unit)}"></div>'
        for c in lab.controls
    )
    hints = "".join(f"<details><summary>Hint {i}</summary><p>{e(h)}</p></details>" for i, h in enumerate(lab.hints, 1))
    hints_card = f'<section class="card hints"><h2>Need a hint?</h2>{hints}</section>' if hints else ""
    explain = "".join(f"<p>{e(x)}</p>" for x in lab.explain)
    explain_card = f'<section class="explain"><h2>Why it happens</h2>{explain}</section>' if explain else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{e(lab.title)}</title><style>{HOUSE_CSS}\n{lab.style}</style></head><body><main class=\"lab\">"
        f'<header><p class="kicker">{e(lab.kicker)}</p><h1>{e(lab.title)}</h1>'
        f'<p class="try"><strong>Try this:</strong> {e(lab.try_this)}</p></header>'
        f'<div class="top"><section class="card idea"><h2>Key idea</h2>{idea}</section>{predict}</div>'
        f'<section class="card steps"><h2>Steps</h2><ol>{steps}</ol></section>'
        f'<section class="benchrow" aria-label="The lab bench"><div class="bench">{lab.drawing}</div>'
        f'<div class="side"><div class="readouts">{readouts}</div><p id="found" class="card found" aria-live="polite"></p>'
        f'<details class="card fine"><summary>Keyboard controls</summary>{rows}</details></div></section>'
        f"{hints_card}{explain_card}</main>"
        f"<script>{HOUSE_SCRIPT}\n(function () {{\n{lab.script}\n}})();</script></body></html>"
    )
