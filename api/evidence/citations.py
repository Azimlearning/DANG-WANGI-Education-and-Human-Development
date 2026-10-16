"""Citations that can be re-checked. A citation is `verified` only because a quotation was found on a page of a document in the corpus, and the verifier and
the gate re-run that check; a `verified: true` flag that cannot be re-proved is refused (hard constraints 4 and 11)."""

from __future__ import annotations

from api.evidence.corpus import Corpus
from api.schema.generated import Citation


class UnverifiableCitation(ValueError):
    pass


def cite(corpus: Corpus, doc: str, page: int, quote: str) -> Citation:
    """A verified citation, or UnverifiableCitation. The quotation must be on that page, word for word."""
    if not corpus.verify_quote(doc, page, quote):
        raise UnverifiableCitation(
            f"the quotation is not on page {page} of '{doc}' (25 to 400 characters, word for word)"
        )
    return Citation(source=doc, page=page, quote=" ".join(quote.split()), verified=True)


def unverified(note: str = "UNVERIFIED (corpus not loaded)") -> Citation:
    return Citation(source=note, page=None, quote=None, verified=False)


class Evidence:
    """What the verifier needs from the corpus: re-prove a citation."""

    def __init__(self, corpus: Corpus):
        self.corpus = corpus

    def verify(self, citation: Citation) -> bool:
        return bool(
            citation.verified
            and citation.page is not None
            and citation.quote
            and self.corpus.verify_quote(citation.source, citation.page, citation.quote)
        )
