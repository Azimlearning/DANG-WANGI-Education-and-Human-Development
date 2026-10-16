"""Prompt packs are files (CLAUDE.md rule 7): `api/prompts/<name>.v<N>.md`. `load(name)` reads the highest version.

A pack starts with a header (one `key: value` per line) and a line of three dashes; the body follows. Header keys, all required:
`version` (equals the file's number), `purpose`, `tier` (any, light, standard or heavy), `inputs` (comma separated variable names, may be empty),
`budget` (an estimate of tokens the pack may take), `cache` (stable or variable). `schema` is optional and names a file under `api/prompts/`.

The body may contain one line `=== VARIABLE ===`. Everything above it is the pack's STABLE part (it never changes between requests with the same
stable inputs, so a provider can cache it); everything below varies per request. Placeholders are `{{name}}` and the set used in the body must
equal the declared `inputs` exactly. A change to a pack is a new file with the next version number, never an edit in place, so a ledger row or an
eval result can name the exact prompt that produced it (commit prefix `prompt:` with an eval delta).

Token counts are estimated as characters / 4. ASSUMED: that is close enough for budgets; a provider's tokenizer will differ.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

DIR = Path(__file__).resolve().parent
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
DIVIDER = "=== VARIABLE ==="
TIERS = {"any", "light", "standard", "heavy"}
REQUIRED = ("version", "purpose", "tier", "inputs", "budget", "cache")


class PromptError(ValueError):
    """A pack is malformed: the message names the file and the problem."""


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    purpose: str
    tier: str
    inputs: tuple[str, ...]
    budget: int
    cache: str
    stable: str
    variable: str
    sha256: str
    schema: str | None = None

    @property
    def body(self) -> str:
        return self.stable + (DIVIDER + "\n" + self.variable if self.variable else "")

    def render_parts(self, **values: str) -> tuple[str, str]:
        missing = set(self.inputs) - set(values)
        extra = set(values) - set(self.inputs)
        if missing or extra:
            raise KeyError(f"prompt {self.name} v{self.version}: missing {sorted(missing)}, unexpected {sorted(extra)}")

        def fill(text: str) -> str:
            return _PLACEHOLDER.sub(lambda m: values[m.group(1)], text)

        return fill(self.stable), fill(self.variable)

    def render(self, **values: str) -> str:
        stable, variable = self.render_parts(**values)
        return stable + variable


def _parse(path: Path, name: str, file_version: int) -> Prompt:
    text = path.read_text(encoding="utf-8")
    header, sep, body = text.partition("\n---\n")
    if not sep:
        raise PromptError(f"{path.name}: no header (a line of three dashes must follow it)")
    fields: dict[str, str] = {}
    for line in header.strip().splitlines():
        key, colon, value = line.partition(":")
        if colon:
            fields[key.strip()] = value.strip()
    for key in REQUIRED:
        if key not in fields:
            raise PromptError(f"{path.name}: header is missing '{key}'")
    if int(fields["version"]) != file_version:
        raise PromptError(f"{path.name}: header version {fields['version']} does not match the file name")
    if fields["tier"] not in TIERS:
        raise PromptError(f"{path.name}: unknown tier '{fields['tier']}'")
    if fields["cache"] not in ("stable", "variable"):
        raise PromptError(f"{path.name}: cache must be 'stable' or 'variable'")
    inputs = tuple(i.strip() for i in fields["inputs"].split(",") if i.strip())
    used = set(_PLACEHOLDER.findall(body))
    if used != set(inputs):
        raise PromptError(f"{path.name}: placeholders {sorted(used)} do not match declared inputs {sorted(inputs)}")
    if "schema" in fields and not (DIR / fields["schema"]).is_file():
        raise PromptError(f"{path.name}: schema file '{fields['schema']}' does not exist")
    stable, _, variable = body.strip().partition(DIVIDER)
    static = {i.strip() for i in fields.get("static_inputs", "").split(",") if i.strip()}
    if not static <= set(inputs):
        raise PromptError(f"{path.name}: static_inputs {sorted(static - set(inputs))} are not declared inputs")
    leaked = set(_PLACEHOLDER.findall(stable)) - static
    if leaked:
        # S1: a per-request value above the divider changes the cacheable prefix on every call.
        raise PromptError(
            f"{path.name}: {sorted(leaked)} appear above the {DIVIDER} line; per-request values belong below it "
            "(or list them in static_inputs if they never change between requests)"
        )
    stable, variable = stable.strip() + "\n", variable.strip()
    if variable:
        variable += "\n"
    budget = int(fields["budget"])
    if estimate_tokens(body) > budget:
        raise PromptError(f"{path.name}: about {estimate_tokens(body)} tokens exceeds its budget of {budget}")
    return Prompt(
        name,
        file_version,
        fields["purpose"],
        fields["tier"],
        inputs,
        budget,
        fields["cache"],
        stable,
        variable,
        hashlib.sha256(text.encode()).hexdigest(),
        fields.get("schema"),
    )


def versions(name: str) -> list[int]:
    return sorted(int(p.stem.rsplit(".v", 1)[1]) for p in DIR.glob(f"{name}.v*.md"))


def load(name: str, version: int | None = None) -> Prompt:
    found = versions(name)
    if not found:
        raise FileNotFoundError(f"no prompt pack named {name!r} in {DIR}")
    chosen = found[-1] if version is None else version
    return _parse(DIR / f"{name}.v{chosen}.md", name, chosen)


def all_names() -> list[str]:
    return sorted({p.stem.rsplit(".v", 1)[0] for p in DIR.glob("*.v*.md")})
