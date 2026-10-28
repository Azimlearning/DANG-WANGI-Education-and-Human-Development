"""Build the static gallery: every Environment the project can make, as an offline single file, plus an index page. No server, no model call, no cost.

    uv run python eval/gallery/build.py [--out gallery-output] [--corpus PATH]

Each Environment is built exactly as `eval/environments/build.py` builds it (plan checks, assembler, verifier in real Chromium, mint, store, delivery gate), and the
delivered block, never a raw row, is exported with `api.export.standalone_page`. Each file checks the hashes of its page and its Kit before anything runs and keeps the
sandbox exact. The index lists title, subject, form, trust label and source for each and links to the files; it loads nothing from any other origin.

With the local corpus every citation is re-proved and the label is `kit-verified`; without it every file says `model-checked` and names no source. The
files hold no textbook text: a source is a book title and a PDF page (hard constraint 13). Publishing them is still the owner's decision (A-8).
The output folder is ignored by git.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.evidence.titles import citation_text  # noqa: E402
from api.export import LABEL_TEXT, chapter_pack, standalone_page  # noqa: E402
from api.kit import latest_version  # noqa: E402
from api.pipeline.plan import Plan  # noqa: E402
from api.schema.generated import EnvironmentBlock  # noqa: E402
from eval.environments.build import KIT, SUBJECTS, build, corpus_dir  # noqa: E402

DEFAULT_OUT = REPO / "gallery-output"

_INDEX = """<!doctype html>
<html lang="en">
<head>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none';">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Synapse: verified science Environments</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; margin: 0 auto; max-width: 46rem; padding: 1rem; line-height: 1.5; }
  h1 { font-size: 1.5rem; } h2 { font-size: 1.15rem; margin-top: 2rem; }
  ul { list-style: none; padding: 0; margin: 0; display: grid; gap: .75rem; }
  li { border: 1px solid #8884; border-radius: 12px; padding: .75rem 1rem; }
  a { display: inline-block; min-height: 44px; line-height: 44px; font-weight: 600; }
  .meta { font-size: .9rem; opacity: .8; }
</style>
</head>
<body>
<h1>Synapse: verified science Environments</h1>
<p>__INTRO__</p>
__SECTIONS__
</body>
</html>
"""


def _entry_text(plan: Plan, block: EnvironmentBlock) -> str:
    esc = html.escape
    sources = "; ".join(citation_text(c.source, c.page, c.verified, c.printedPage) for c in block.citations)
    return (
        f'<li><a href="{esc(plan.id)}.html">{esc(block.title)}</a>'
        f'<div class="meta">{esc(LABEL_TEXT[block.label])}. Source: {esc(sources or "none stated")}.</div>'
        f'<div class="meta">{esc(plan.goal)}</div></li>'
    )


def build_gallery(out: Path, corpus_path: Path | None = None) -> list[dict]:
    """Write one file per Environment and an index into `out`. Returns one record per file."""
    out.mkdir(parents=True, exist_ok=True)
    kit_js = (KIT / latest_version(KIT) / "core.js").read_bytes()
    entries: list[tuple[Plan, EnvironmentBlock]] = []

    def on_block(plan: Plan, block: EnvironmentBlock) -> None:
        (out / f"{plan.id}.html").write_text(standalone_page(block, kit_js), encoding="utf-8")
        entries.append((plan, block))

    build(corpus_path, on_block=on_block)

    # Chapter packs (W6, D-49): every Environment of one subject and form in a single offline file, for a school PC.
    packs: list[tuple[str, str, int]] = []
    for key, name in SUBJECTS.items():
        for form in ("4", "5"):
            group = [b for p, b in entries if p.topic.startswith(f"{key}_form{form}_")]
            if group:
                file = f"pack-{key}-form{form}.html"
                (out / file).write_text(chapter_pack(f"{name} Form {form}", group, kit_js), encoding="utf-8")
                packs.append((file, f"{name} Form {form}", len(group)))

    sections = []
    for key, name in SUBJECTS.items():
        items = [(p, b) for p, b in entries if p.topic.startswith(key)]
        if items:
            items.sort(key=lambda pb: (pb[0].topic, pb[0].id))
            sections.append(f"<h2>{html.escape(name)}</h2>\n<ul>\n" + "\n".join(_entry_text(p, b) for p, b in items) + "\n</ul>")
    verified = sum(1 for _, b in entries if b.label == "kit-verified")
    intro = (
        f"{len(entries)} Environments, {verified} with a textbook source proved word for word. Each one is a single file that checks its own hashes before it runs, "
        "keeps its sandbox closed, and says what was checked and what it cannot show. None has been reviewed by a teacher."
    )
    if packs:
        links = "\n".join(
            f'<li><a href="{html.escape(f)}">{html.escape(label)}: all {n} in one file</a><div class="meta">Opens offline; every fingerprint is checked before anything runs.</div></li>'
            for f, label, n in packs
        )
        sections.insert(0, f"<h2>Chapter packs</h2>\n<ul>\n{links}\n</ul>")
    page = _INDEX.replace("__INTRO__", html.escape(intro)).replace("__SECTIONS__", "\n".join(sections))
    (out / "index.html").write_text(page, encoding="utf-8")
    return [
        {
            "id": p.id,
            "file": f"{p.id}.html",
            "label": b.label,
            "sha256": hashlib.sha256((out / f"{p.id}.html").read_bytes()).hexdigest(),
        }
        for p, b in entries
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--corpus", type=Path, default=None, help="the local corpus folder (default: the CORPUS_DIR setting)")
    args = ap.parse_args(argv)
    records = build_gallery(args.out, corpus_dir(args.corpus))
    verified = sum(1 for r in records if r["label"] == "kit-verified")
    print(f"wrote {len(records)} Environments ({verified} kit-verified) and index.html to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
