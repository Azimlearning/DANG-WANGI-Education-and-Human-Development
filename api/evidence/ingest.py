"""Build the local corpus from PDFs. Run on the owner's machine only:
`uv run --group local python -m api.evidence.ingest --pdf-dir <folder of PDFs, searched recursively> --out <corpus folder>`.

Needs `pypdf` (the `local` dependency group: `uv add --group local pypdf`, BSD-3-Clause); the textbooks are not in this repository and never should be
(hard constraint 13). One `<doc_id>.jsonl` per PDF, one line per page, `{"page": <1-based PDF page index>, "text": ...}`. The doc id is a slug of the PDF's
path under `--pdf-dir`, so two files with the same name in different folders do not collide. A PDF with no text layer (a scan) produces pages with empty
text and a warning: it needs OCR (`api/evidence/ocr.py`). A manifest (file name, SHA-256, page counts, a guess of subject, form, language and kind; NO text) is
written beside the corpus as `manifest.json` and is safe to commit (D-14). Re-running skips a PDF whose hash is unchanged unless `--force`.
Legal use of the textbooks is the owner's call (A-8): ingestion keeps them on this machine and quotes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MANIFEST = "manifest.json"
# A page with fewer characters than this is treated as having no text layer (a page number or a stray mark is not text).
MIN_TEXT_CHARS = 20


def slug(relative: Path) -> str:
    """A stable, filesystem-safe document id from a PDF's path under the source folder: `Biology/Form 4/[DLP] BIOLOGY F4.pdf` -> `biology-form-4-dlp-biology-f4`."""
    text = relative.with_suffix("").as_posix().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def describe(relative: Path) -> dict:
    """A guess at what a document is, from its path alone. A guess is a convenience for finding things, never evidence: a person checks it."""
    path = relative.as_posix().lower()
    subject = next(
        (s for key, s in (("biolog", "biology"), ("chem", "chemistry"), ("kimia", "chemistry"), ("physic", "physics"), ("fizik", "physics")) if key in path),
        "unknown",
    )
    form = None
    for pattern in (r"form[ _-]*([45])", r"tingkatan[ _-]*([45])", r"ting[ _-]*([45])", r"\bf([45])\b", r"\bt([45])\b", r"physics[ _-]f([45])", r"kimia[ _-]*(?:ting\w*[ _-]*)?([45])"):
        m = re.search(pattern, path)
        if m:
            form = int(m.group(1))
            break
    language = "ms" if any(k in path for k in ("malay", "biologi", "kimia", "tingkatan", "aktiviti")) else "en"
    kind = "experiment" if "experiment" in path or "eksperimen" in path or "shortlist" in path else "textbook"
    return {"subject": subject, "form": form, "language": language, "kind": kind}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract(pdf: Path) -> tuple[list[dict], int]:
    """Every page's text (`page` is the 1-based index in the PDF, which can differ from the number printed on the page) and how many pages failed to read."""
    try:
        from pypdf import PdfReader  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - local tool
        raise SystemExit("pypdf is not installed: uv run --group local ... (or uv add --group local pypdf)") from exc
    reader = PdfReader(str(pdf))
    pages: list[dict] = []
    failed = 0
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:  # noqa: BLE001 - one unreadable page must not lose the book
            text, failed = "", failed + 1
        pages.append({"page": number, "text": text})
    return pages, failed


def ingest_one(pdf: Path, root: Path, out: Path, previous: dict[str, dict], force: bool) -> dict:
    relative = pdf.relative_to(root)
    doc_id = slug(relative)
    digest = sha256_of(pdf)
    target = out / f"{doc_id}.jsonl"
    old = previous.get(doc_id)
    if old and old.get("sha256") == digest and target.exists() and not force:
        return {**old, "skipped": True}
    pages, failed = extract(pdf)
    target.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pages), encoding="utf-8")
    empty = sum(1 for p in pages if len(p["text"]) < MIN_TEXT_CHARS)
    return {
        "doc_id": doc_id,
        "file": relative.as_posix(),
        "sha256": digest,
        "bytes": pdf.stat().st_size,
        "pages": len(pages),
        "empty_pages": empty,
        "unreadable_pages": failed,
        **describe(relative),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--force", action="store_true", help="re-extract even when the PDF's hash is unchanged")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / MANIFEST
    previous = (
        {d["doc_id"]: d for d in json.loads(manifest_path.read_text(encoding="utf-8"))["documents"]}
        if manifest_path.exists()
        else {}
    )
    pdfs = sorted(args.pdf_dir.rglob("*.pdf"))
    ids = [slug(p.relative_to(args.pdf_dir)) for p in pdfs]
    if len(set(ids)) != len(ids):
        raise SystemExit("two PDFs would get the same document id; rename one")
    documents = []
    for pdf in pdfs:
        entry = ingest_one(pdf, args.pdf_dir, args.out, previous, args.force)
        documents.append(entry)
        warn = ""
        if entry["empty_pages"]:
            warn = f"  WARNING: {entry['empty_pages']} of {entry['pages']} pages have no text layer (needs OCR)"
        print(f"{'skipped ' if entry.get('skipped') else ''}{entry['doc_id']}: {entry['pages']} pages{warn}", flush=True)
        manifest_path.write_text(
            json.dumps({"documents": [{k: v for k, v in d.items() if k != "skipped"} for d in documents]}, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
