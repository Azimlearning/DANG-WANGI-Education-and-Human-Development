"""The experiment catalogue: which practicals exist, where they are in the owner's documents, and which Kit models and Plans cover them.

Only metadata lives in the repository (a title, an aim in our own words, the document and page where the experiment is, which model and plan serve it).
No textbook text is stored (hard constraint 13). A person confirms every entry: `propose_from_corpus` produces candidates for a person to review from the
local corpus, with `status: "proposed"`; nothing proposed is treated as real.

    uv run python -m api.evidence.catalogue --check           # validate data/experiments/catalogue.json and print coverage
    uv run python -m api.evidence.catalogue --propose DIR     # local: propose entries from a corpus folder (see ingest.py)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api.evidence.corpus import Corpus

REPO = Path(__file__).resolve().parents[2]
CATALOGUE = REPO / "data" / "experiments" / "catalogue.json"
PLANS = REPO / "data" / "plans"

# proposed: found by a tool, nobody has looked. confirmed/planned: a person matched it to the documents. authored: a Plan exists (which may be ahead of confirmation).
Status = Literal["proposed", "confirmed", "planned", "authored"]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Source(_Strict):
    doc: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    page: int = Field(ge=1)


class Entry(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{3,60}$")]
    subject: Literal["physics", "biology", "chemistry"]
    form: Literal[4, 5]
    topic: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$")] | None
    title: Annotated[str, StringConstraints(min_length=3, max_length=120)]
    aim: Annotated[str, StringConstraints(max_length=240)] = ""
    source: Source | None = None
    status: Status
    models: list[str] = Field(default_factory=list)
    plan_id: str | None = None
    confirmed_by_person: bool = False
    note: Annotated[str, StringConstraints(max_length=240)] = ""


class Catalogue(_Strict):
    version: Literal[1]
    entries: list[Entry]


def load(path: Path = CATALOGUE) -> Catalogue:
    return Catalogue.model_validate_json(path.read_text(encoding="utf-8"))


def problems(cat: Catalogue, plan_dir: Path = PLANS) -> list[str]:
    out: list[str] = []
    ids = [e.id for e in cat.entries]
    out += [f"duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    plans = {
        json.loads(p.read_text(encoding="utf-8"))["id"]: json.loads(p.read_text(encoding="utf-8"))
        for p in plan_dir.glob("*.json")
    }
    for e in cat.entries:
        if e.status == "authored":
            if e.plan_id not in plans:
                out.append(f"{e.id}: authored but plan '{e.plan_id}' does not exist")
            elif plans[e.plan_id]["topic"] != e.topic:
                out.append(f"{e.id}: its plan is for topic {plans[e.plan_id]['topic']}, not {e.topic}")
        if e.status in ("confirmed", "planned") and not e.confirmed_by_person:
            out.append(f"{e.id}: status '{e.status}' needs confirmed_by_person (a person must confirm the entry)")
        if e.status == "proposed" and e.confirmed_by_person:
            out.append(f"{e.id}: a proposed entry cannot be marked confirmed")
        if e.topic and not e.topic.startswith(f"{e.subject}_form{e.form}_"):
            out.append(f"{e.id}: topic {e.topic} does not match subject {e.subject} and form {e.form}")
    return out


_HEAD = re.compile(
    r"^\s*(experiment|activity|aktiviti|eksperimen)\s+(\d+(?:\.\d+)*)\b[:.\s-]*(.{3,120})$",
    re.IGNORECASE | re.MULTILINE,
)
_AIM = re.compile(r"\b(aim|objective|tujuan)\s*[:\-]\s*(.{10,200})", re.IGNORECASE)


def propose_from_corpus(corpus: Corpus, subject: str, form: int) -> list[Entry]:
    """Candidate entries found by heading, for a person to review. The aim is cut from the page's own words only as far as the first sentence, and a
    person should rewrite it in their own words before confirming."""
    found: list[Entry] = []
    for doc in corpus.documents:
        for page in sorted(corpus._pages[doc]):  # noqa: SLF001 - same package
            text = corpus._pages[doc][page]  # noqa: SLF001
            for m in _HEAD.finditer(text):
                title = " ".join(m.group(3).split())[:120]
                slug = re.sub(r"[^a-z0-9]+", "_", f"{doc}_{m.group(2)}_{title}".lower()).strip("_")[:60]
                aim = _AIM.search(text[m.end() :])
                found.append(
                    Entry(
                        id=slug or "experiment",
                        subject=subject,  # type: ignore[arg-type]
                        form=form,  # type: ignore[arg-type]
                        topic=None,
                        title=title,
                        aim=(aim.group(2).split(".")[0][:240] if aim else ""),
                        source=Source(doc=doc, page=page),
                        status="proposed",
                    )
                )
    return found


def coverage(cat: Catalogue) -> dict:
    by = Counter((e.subject, e.status) for e in cat.entries)
    return {"entries": len(cat.entries), "by_subject_status": {f"{s}/{st}": n for (s, st), n in sorted(by.items())}}


def main(argv: list[str]) -> int:
    if "--propose" in argv:
        directory = Path(argv[argv.index("--propose") + 1])
        corpus = Corpus.load(directory)
        entries = propose_from_corpus(
            corpus,
            subject=argv[argv.index("--subject") + 1] if "--subject" in argv else "chemistry",
            form=int(argv[argv.index("--form") + 1]) if "--form" in argv else 4,
        )
        print(json.dumps([e.model_dump(mode="json") for e in entries], indent=2, ensure_ascii=False))
        return 0
    cat = load()
    errs = problems(cat)
    print(json.dumps(coverage(cat), indent=2))
    for e in errs:
        print("PROBLEM:", e)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
