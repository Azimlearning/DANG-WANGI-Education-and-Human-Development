"""Helpers for the /ask stream. The wire shape itself (MetaEvent and the rest) is generated from packages/schema."""

from __future__ import annotations


def split_text(text: str, words_per_chunk: int = 4) -> list[str]:
    """Split a reply into small `text_delta` chunks that re-join to exactly the original text."""
    words = text.split(" ")
    chunks: list[str] = []
    for i in range(0, len(words), words_per_chunk):
        piece = " ".join(words[i : i + words_per_chunk])
        chunks.append(piece if i + words_per_chunk >= len(words) else piece + " ")
    return chunks
