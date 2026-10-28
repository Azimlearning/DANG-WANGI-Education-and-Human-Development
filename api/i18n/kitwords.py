"""The Kit's own fixed words in both languages, and whether a person has reviewed the Malay (W12, D-62).

The words live in `packages/kit/src/i18n.ts`. Every Malay Environment carries them, so a Malay translation is not `reviewed` unless the Kit's Malay is too. The review is recorded in
`data/i18n/ms/_kit.json` against a digest of the current words: change a word and the review no longer matches, and every translation drops back to `draft` the next time it is built.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "packages" / "kit" / "src" / "i18n.ts"
RECORD = REPO / "data" / "i18n" / "ms" / "_kit.json"

_DUMP = """
const m = await import(process.argv[1]);
const fill = (v, last) => typeof v === 'function' ? v(...Array.from({ length: v.length }, (_, i) => (i === v.length - 1 && last !== null ? last : '{' + i + '}'))) : v;
const out = {};
for (const [k, e] of Object.entries(m.WORDS)) {
  const row = { en: fill(e.en, null), ms: fill(e.ms, null) };
  const alt = { en: fill(e.en, false), ms: fill(e.ms, false) };
  if (alt.en !== row.en || alt.ms !== row.ms) row.alt = alt;
  out[k] = row;
}
console.log(JSON.stringify(out));
"""


def words(source: Path = SOURCE) -> dict[str, dict]:
    """key -> {en, ms, alt?}. `alt` is the other branch of a word with a yes/no argument (on the hanger or in the tray). Needs Node 22.6 or later (it reads the TypeScript directly)."""
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node is needed to read the Kit's words")
    done = subprocess.run([node, "--input-type=module", "-e", _DUMP, source.as_uri()], capture_output=True, text=True, check=True, timeout=60)  # noqa: S603
    return json.loads(done.stdout)


def digest(table: dict[str, dict] | None = None) -> str:
    table = table if table is not None else words()
    return hashlib.sha256(json.dumps(table, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def reviewed(record: Path | None = None, table: dict[str, dict] | None = None) -> bool:
    """True when `_kit.json` names a reviewer and a date and its digest is the digest of the words as they are now. Any failure to read means not reviewed."""
    try:
        data = json.loads((record or RECORD).read_text(encoding="utf-8"))
        return bool(data.get("reviewer") and data.get("reviewed_on")) and data.get("digest") == digest(table)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return False
