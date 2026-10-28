"""How a citation's document reads to a student: a book, not a file id. The offline export uses it; the web app has the same rule in `web/lib/citation.ts`
(the two surfaces share no source, D-1, so both are tested against the same document ids). The title comes from the id's own words (subject and form), so
no textbook content is involved; an id that does not follow the pattern is shown as it is. When the printed page is known both are shown (the book's number first, since that is what a student can find on paper); otherwise the page is called a PDF page."""

from __future__ import annotations

import re

_PATTERN = re.compile(r"^textbook-(physics|chemistry|biology)(?:-.*?)?-(?:f|form-?)([45])(?:-|$)")


def document_title(source: str) -> str:
    m = _PATTERN.match(source)
    return f"KSSM {m.group(1).capitalize()} Form {m.group(2)} textbook" if m else source


def citation_text(source: str, page: int | None, verified: bool, printed_page: int | None = None) -> str:
    if page is None:
        where = ""
    elif printed_page is not None:
        where = f", page {printed_page} (PDF page {page})"
    else:
        where = f", PDF page {page}"
    return f"{document_title(source)}{where}{'' if verified else ' (not verified)'}"
