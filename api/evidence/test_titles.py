from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.evidence.titles import citation_text, document_title

REPO = Path(__file__).resolve().parents[2]
EXPECTED = {
    "textbook-physics-physics-f5-removed": "KSSM Physics Form 5 textbook",
    "textbook-physics-physics-f4-removed": "KSSM Physics Form 4 textbook",
    "textbook-chemistry-chemistry-f4": "KSSM Chemistry Form 4 textbook",
    "textbook-chemistry-chemistry-f5": "KSSM Chemistry Form 5 textbook",
    "textbook-biology-form-4-dlp-biology-f4": "KSSM Biology Form 4 textbook",
    "textbook-biology-form-5-dlp-biology-form-5": "KSSM Biology Form 5 textbook",
}


@pytest.mark.parametrize(("doc", "title"), EXPECTED.items())
def test_known_documents(doc: str, title: str) -> None:
    assert document_title(doc) == title


def test_every_document_the_pointers_name_gets_a_title() -> None:
    pointers = json.loads((REPO / "data" / "citations" / "pointers.json").read_text(encoding="utf-8"))["pointers"]
    docs = {p["doc"] for p in pointers.values()}
    assert docs == set(EXPECTED), "a new document needs its title tested here and in web/lib/citation.test.ts"


def test_an_unrecognised_id_is_shown_as_it_is() -> None:
    assert document_title("UNVERIFIED (corpus not loaded until P2)") == "UNVERIFIED (corpus not loaded until P2)"


def test_text_matches_the_web_wording() -> None:
    assert citation_text("textbook-physics-physics-f5-removed", 36, True) == "KSSM Physics Form 5 textbook, PDF page 36"
    assert citation_text("UNVERIFIED (x)", None, False) == "UNVERIFIED (x) (not verified)"
