"""Before a commit: no textbook text may appear in any file git would add (CLAUDE.md hard constraint 13). Needs the local corpus.

    uv run python eval/evidence/leak_check.py [--corpus DIR]        # prints counts only, never the text; exit 1 if anything leaks

It takes every quotation in `<corpus>/citations.json` and looks for any 9-word run of it in every tracked or not-ignored file. Nine words, because shorter runs
are common scientific phrasing ("the rate of change of momentum") that is not a copied sentence. It does not read the textbooks themselves, so it cannot
find a passage that was never made a quotation; it guards what the citation machinery put near the repository. Run it before `git add`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from api.core.settings import Settings  # noqa: E402

WINDOW = 9


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def committable_files() -> list[Path]:
    """Tracked files plus untracked files git does not ignore: what `git add -A` would stage."""
    names: set[str] = set()
    for args in (["ls-files"], ["ls-files", "-o", "--exclude-standard"]):
        names |= set(subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.split("\n"))
    return sorted(REPO / n for n in names if n and (REPO / n).is_file())


def leaks(quotes: dict[str, str], files: list[Path]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in files:
        try:
            text = normalise(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue  # binary: not text we could have written a quotation into
        for cid, quote in quotes.items():
            words = normalise(quote).split()
            if len(words) < WINDOW:
                continue
            if any(" ".join(words[i : i + WINDOW]) in text for i in range(len(words) - WINDOW + 1)):
                found.append((path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else str(path), cid))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=None)
    args = ap.parse_args(argv)
    corpus = args.corpus or Settings(_env_file=REPO / ".env").corpus_dir  # pyright: ignore[reportCallIssue]
    if corpus is None:
        raise SystemExit("no corpus configured (--corpus DIR or CORPUS_DIR): nothing to check against")
    quotes = {k: str(v) for k, v in json.loads((corpus / "citations.json").read_text(encoding="utf-8"))["quotes"].items()}
    files = committable_files()
    found = leaks(quotes, files)
    print(f"checked {len(files)} files against {len(quotes)} quotations ({WINDOW}-word runs)")
    for name, cid in found:
        print(f"LEAK: {name} contains text from the quotation '{cid}'")
    print("no leaks" if not found else f"{len(found)} leak(s): do not commit")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
