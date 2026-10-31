"""The Free lane's reply reader (D-07, D-41): a model was asked for one whole HTML document; this turns its reply into a page or says it is not one.

Nothing here makes the page safe. The reply goes on to the post-processor, the L0 scan, the L4 wording check and the real-browser harness like any other
page. This only separates a document from chatter: a fence or a sentence before the doctype is dropped (the pack forbids both, and models add them anyway),
but a reply with no document, a document with no end (cut off by the token cap) or a title that is not text is refused, never repaired.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html import unescape

MAX_TITLE = 60
DEFAULT_TITLE = "Interactive page"

_FENCE = re.compile(r"^```[a-zA-Z]*\s*\n(.*?)\n?```\s*$", re.DOTALL)
_START = re.compile(r"<!doctype\s+html|<html\b", re.IGNORECASE)
_END = re.compile(r"</html\s*>", re.IGNORECASE)
_TITLE = re.compile(r"<title\b[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class Page:
    title: str
    html: str


def read_reply(raw: str) -> Page | str:
    """The page from the model's reply, or the reason there is none (told to the model on a retry). A reply in labelled sections (W20) is assembled into the
    house frame (`free_house`); a whole document (the older format, and the test fixtures) is taken as it is."""
    from api.pipeline import free_house

    text = raw.lstrip("﻿").strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    if free_house.is_sections(text):
        lab = free_house.parse(text)
        if isinstance(lab, str):
            return lab
        return Page(lab.title or DEFAULT_TITLE, free_house.assemble(lab))
    page = parse_reply(text)
    return page if page is not None else "the reply was not the lab in the @@ sections asked for"


def parse_reply(raw: str) -> Page | None:
    """One document from the model's reply, or None when there is not one."""
    text = raw.lstrip("﻿").strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    start = _START.search(text)
    if start is None:
        return None
    ends = list(_END.finditer(text))
    if not ends:
        return None  # cut off: a page with no end was stopped by the token cap
    document = text[start.start() : ends[-1].end()]
    match = _TITLE.search(document)
    title = " ".join(unescape(match.group(1)).split())[:MAX_TITLE] if match else ""
    return Page(title or DEFAULT_TITLE, document)


def slug_for(canonical_question: str) -> str:
    """A stable id stem for the question: `free_` and 12 hex characters. The question itself is never part of an id."""
    return "free_" + hashlib.sha256(canonical_question.encode("utf-8")).hexdigest()[:12]
