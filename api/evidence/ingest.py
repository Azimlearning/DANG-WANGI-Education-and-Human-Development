"""Build the local corpus from PDFs. Run on the owner's machine only: `uv run python -m api.evidence.ingest --pdf-dir <folder> --out <corpus folder>`.

Needs `pypdf` (`uv add --group local pypdf`), which is not installed in the cloud container; the textbooks are not in this repository and never
should be (hard constraint 13). A PDF with no text layer (the image-only Chemistry experiment books, A-8) produces pages with empty text and a warning:
it needs OCR, which is a local step that is not built. Legal use of the textbooks is unconfirmed (A-8): confirm before ingesting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def extract(pdf: Path) -> list[dict]:
    try:
        from pypdf import PdfReader  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - local tool
        raise SystemExit("pypdf is not installed: uv add --group local pypdf") from exc
    reader = PdfReader(str(pdf))
    return [{"page": i, "text": (page.extract_text() or "").strip()} for i, page in enumerate(reader.pages, start=1)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(args.pdf_dir.glob("*.pdf")):
        pages = extract(pdf)
        empty = sum(1 for p in pages if not p["text"])
        (args.out / f"{pdf.stem}.jsonl").write_text(
            "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pages), encoding="utf-8"
        )
        note = f"  WARNING: {empty} of {len(pages)} pages have no text layer (needs OCR)" if empty else ""
        print(f"{pdf.name}: {len(pages)} pages{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
