"""Questions in Bahasa Melayu for the English-trained router (W13, D-63). Pure Python, no model, no network.

The topic router was trained on English questions. Asked a Malay one it mostly says "none" (which the router never trusts, so the question goes to the fallback) and
answers from the library only 19 percent of the probe set, all correctly: it is safe but nearly blind to Malay. Two guards give it sight without retraining:

1. `is_malay` spots a Malay question by its function words ("apakah", "bagaimana", "dengan", "yang" ...), which English never uses.
2. `to_english` rewrites it word by word and phrase by phrase with the glossary (`data/models/router/glossary_ms.json`) into the English the router knows, and reports how much of the
   question it understood. The router trusts its local answer only when most of the question was understood; otherwise every head goes to the fallback, exactly as for any
   question it cannot judge.

On the 68-question probe (`eval/models/bm_probe.py`, written by the same author as the glossary, so optimistic) the guard takes the share answered from the library from 19 to 57 percent
with every answer still right, and the topic accuracy from 31 to 78 percent.

This is a bridge, not a language model: it knows the KSSM science vocabulary the build assistant wrote down, and a question in other words falls through to the fallback.
The learned alternative (a multilingual encoder fine-tuned on a GPU) is the W13 notebook in `eval/models/colab/`; this module is what it has to beat.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

GLOSSARY = Path(__file__).resolve().parents[2] / "data" / "models" / "router" / "glossary_ms.json"
MIN_COVERAGE = 0.6
"""The share of a Malay question's content words the glossary (or the router's English vocabulary) must understand before the router's local answer is trusted. ASSUMED (D-63):
chosen before the probe was scored, not tuned on it."""

_TOKEN = re.compile(r"[a-z0-9]+(?:['\-][a-z0-9]+)*")
_PREFIXES = ("meny", "meng", "mem", "men", "me", "peng", "pem", "pen", "pe", "ber", "ter", "di", "ke", "se", "per")
_SUFFIXES = ("kan", "an", "i", "nya", "lah", "kah")


@dataclass(frozen=True)
class Glossary:
    markers: frozenset[str]
    words: dict[str, str]
    phrases: dict[tuple[str, ...], str]
    longest: int


@lru_cache(maxsize=1)
def glossary(path: Path = GLOSSARY) -> Glossary:
    raw = json.loads(path.read_text(encoding="utf-8"))
    words: dict[str, str] = {}
    phrases: dict[tuple[str, ...], str] = {}
    for key, value in {**raw["words"], **raw["phrases"]}.items():
        parts = key.lower().split()
        if not parts:
            continue
        if len(parts) > 1:
            phrases[tuple(parts)] = value
        else:
            words[parts[0]] = value
    return Glossary(frozenset(raw["markers"]), words, phrases, max((len(p) for p in phrases), default=1))


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def is_malay(text: str) -> bool:
    """True when the question is in Bahasa Melayu: two or more Malay function words, or one function word with at least two more Malay science words around it. English never uses
    these function words, and a Malay word that is also an English word ("air", "gas") counts for nothing on its own."""
    g = glossary()
    toks = tokens(text)
    markers = sum(1 for t in toks if t in g.markers)
    if markers >= 2:
        return True
    if markers == 0:
        return False
    own = sum(1 for t in toks if len(t) >= 3 and t not in g.markers and g.words.get(t, t) != t)
    return markers + own >= 3 or (len(toks) <= 4 and markers + own >= 2)


def _stems(word: str) -> list[str]:
    """Candidate base forms of a Malay word: affixes taken off, and the first letter a prefix swallowed put back (meny-sejuk, mem-panaskan, men-titrat)."""
    out: list[str] = []
    for prefix in ("", *_PREFIXES):
        if not word.startswith(prefix) or len(word) - len(prefix) < 3:
            continue
        rest = word[len(prefix) :]
        restored = {"meny": ("s",), "meng": ("", "k"), "mem": ("", "p"), "men": ("", "t"), "pem": ("", "p"), "pen": ("", "t"), "peng": ("", "k")}.get(prefix, ("",))
        for letter in restored:
            base = letter + rest
            for suffix in ("", *_SUFFIXES):
                if suffix and (not base.endswith(suffix) or len(base) - len(suffix) < 3):
                    continue
                out.append(base[: len(base) - len(suffix)] if suffix else base)
    return out


@dataclass(frozen=True)
class Translation:
    text: str
    understood: int
    total: int

    @property
    def coverage(self) -> float:
        return self.understood / self.total if self.total else 0.0


def to_english(text: str, known: Callable[[str], bool] | None = None) -> Translation:
    """The question with its Malay words and phrases replaced by English. A word the glossary does not know is kept as it is: it is counted as understood only if `known` (the router's
    own English vocabulary) says so. Words of fewer than three letters and numbers are not counted either way."""
    g = glossary()
    toks = tokens(text)
    out: list[str] = []
    understood = total = 0
    i = 0
    while i < len(toks):
        for n in range(min(g.longest, len(toks) - i), 1, -1):
            phrase = tuple(toks[i : i + n])
            if phrase in g.phrases:
                out.append(g.phrases[phrase])
                understood += 1
                total += 1
                i += n
                break
        else:
            word = toks[i]
            i += 1
            if len(word) < 3 or word.isdigit():
                out.append(word)
                continue
            total += 1
            if word in g.words:
                out.append(g.words[word])
                understood += 1
                continue
            hit = next((g.words[s] for s in _stems(word) if s in g.words), None)
            if hit is not None:
                out.append(hit)
                understood += 1
                continue
            out.append(word)
            if known is not None and known(word):
                understood += 1
    return Translation(" ".join(p for p in out if p), understood, total)
