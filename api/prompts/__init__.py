"""Prompt packs are files (CLAUDE.md rule 7). `load("router-fallback")` reads `api/prompts/router-fallback.v<N>.md` for the highest N.

A pack starts with a small header (`version: N`, `purpose: ...`) and a line of three dashes; the body follows. Placeholders are written
`{{name}}` and filled by `render`. A change to a pack is a new file with the next version number, never an edit in place, so every ledger
row and eval result can name the exact prompt that produced it.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

DIR = Path(__file__).resolve().parent
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    purpose: str
    body: str
    sha256: str

    def render(self, **values: str) -> str:
        missing = set(_PLACEHOLDER.findall(self.body)) - set(values)
        if missing:
            raise KeyError(f"prompt {self.name} v{self.version} needs {sorted(missing)}")
        return _PLACEHOLDER.sub(lambda m: values[m.group(1)], self.body)


def load(name: str, version: int | None = None) -> Prompt:
    candidates = sorted(DIR.glob(f"{name}.v*.md"), key=lambda p: int(p.stem.rsplit(".v", 1)[1]))
    if not candidates:
        raise FileNotFoundError(f"no prompt pack named {name!r} in {DIR}")
    path = candidates[-1] if version is None else DIR / f"{name}.v{version}.md"
    text = path.read_text(encoding="utf-8")
    header, _, body = text.partition("\n---\n")
    fields = dict(line.split(":", 1) for line in header.strip().splitlines() if ":" in line)
    file_version = int(path.stem.rsplit(".v", 1)[1])
    if int(fields.get("version", "0").strip()) != file_version:
        raise ValueError(f"{path.name}: header version does not match the file name")
    return Prompt(
        name,
        file_version,
        fields.get("purpose", "").strip(),
        body.strip() + "\n",
        hashlib.sha256(text.encode()).hexdigest(),
    )
