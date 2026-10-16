#!/usr/bin/env python3
"""
Secret-literal guard: PreToolUse hook on Write/Edit/MultiEdit.

Reads Claude Code's hook JSON on stdin. For file-write tools, scans the content
being written for key-shaped literals. On a match, exits 2 with a message naming
the file, the line, and the fix, so the model self-corrects without the user
having to intervene.

Scaffolded by /newproject and trimmed to the providers Synapse v4 uses
(Anthropic, OpenRouter, a generic sk- key, GitHub, JWT, private keys).
Standard library only, by design: a hook that needs `pip install` breaks on a
fresh clone.
"""

from __future__ import annotations

import json
import os
import re
import sys

# (label, regex): order matters only for message readability.
PATTERNS: list[tuple[str, str]] = [
    ("JWT token (eyJ...)",
     r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"),
    ("High-entropy literal near key/secret/token/password",
     r"(?:api[_-]?key|secret|token|password)[^A-Za-z0-9\n]{1,8}[A-Za-z0-9+/=_\-]{32,}"),
    ("32-char hex key literal",
     r"(?:=|:\s*['\"])[0-9a-f]{32}(?:['\"]|$)"),
    ("GitHub PAT",         r"gh[pousr]_[A-Za-z0-9]{30,}"),
    ("Anthropic API key",  r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("OpenRouter API key", r"sk-or-v1-[A-Za-z0-9]{20,}"),
    ("sk- API key (OpenAI or other)", r"sk-(?!ant-|or-v1-)(?:proj-)?[A-Za-z0-9_\-]{20,}"),
    ("Private key block",  r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
]

# Where secrets are supposed to live in THIS project.
FIX_LINES = [
    "  - Local dev  -> put the value in .env (gitignored) and read it through api/core/settings.py.",
    "  - Deployed   -> set it in the host's environment-variable settings; never in the web bundle.",
    "  - Document the variable NAME in .env.example and refdocs/guides/env_setup.md.",
]

ALLOW_MARK = "pragma: allowlist secret"

# Files that are allowed to contain secret-shaped strings.
ALLOWED_BASENAMES = {"check_secrets.py"}
ALLOWED_PREFIXES = (".env",)
# Lockfiles and vendored code produce endless false positives.
SKIP_SUBSTRINGS = ("node_modules/", "/vendor/", ".lock", "-lock.json")


def extract(data: dict) -> tuple[str, str] | None:
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    if tool == "Write":
        return ti.get("file_path", "?"), ti.get("content", "") or ""
    if tool == "Edit":
        return ti.get("file_path", "?"), ti.get("new_string", "") or ""
    if tool == "MultiEdit":
        edits = ti.get("edits", []) or []
        return ti.get("file_path", "?"), "\n".join((e.get("new_string", "") or "") for e in edits)
    return None


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        # Fail open: never block work because the hook could not parse its input.
        print(f"[check_secrets] warning: malformed hook JSON ({e}); pass-through.", file=sys.stderr)
        return 0

    pair = extract(data)
    if pair is None:
        return 0
    path, content = pair

    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    if base in ALLOWED_BASENAMES or base.startswith(ALLOWED_PREFIXES):
        return 0
    if any(frag in norm for frag in SKIP_SUBSTRINGS):
        return 0

    lines = [ln for ln in content.splitlines() if ALLOW_MARK not in ln]

    findings: list[tuple[str, list[tuple[int, str]]]] = []
    for label, pattern in PATTERNS:
        hits: list[tuple[int, str]] = []
        for i, line in enumerate(lines, start=1):
            if re.search(pattern, line):
                hits.append((i, line.strip()[:160]))
                if len(hits) >= 3:
                    break
        if hits:
            findings.append((label, hits))

    if not findings:
        return 0

    msg = [f"BLOCKED: secret literal detected in {path}", ""]
    for label, hits in findings:
        msg.append(f"  {label}:")
        msg.extend(f"    line {i}: {snippet}" for i, snippet in hits)
        msg.append("")
    msg.append("Fix:")
    msg.extend(FIX_LINES)
    msg += ["", f"False positive? Append '# {ALLOW_MARK}' to that line. Use sparingly."]
    print("\n".join(msg), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
