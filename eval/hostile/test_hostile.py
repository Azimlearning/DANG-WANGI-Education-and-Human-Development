"""The hostile set stays well formed, and layer A (no browser) blocks every page and document case. The two-layer run is `eval/hostile/run.py`."""

from __future__ import annotations

import json

from eval.hostile.run import CASES, build_html, layer_a

COMMIT = "835a2cefda285b4282ea4d0dbf986d1ff08abdb2"


def cases() -> list[dict]:
    return json.loads(CASES.read_text(encoding="utf-8"))["cases"]


def test_ported_cases_name_their_source_commit() -> None:
    ported = [c for c in cases() if c["id"] in {"H1", "H2", "H3", "H4", "H5"}]
    assert len(ported) == 5 and all(COMMIT in c["source"] for c in ported)


def test_ids_are_unique() -> None:
    ids = [c["id"] for c in cases()]
    assert len(ids) == len(set(ids)) >= 20


def test_layer_a_blocks_every_page_and_document_case() -> None:
    for case in cases():
        if case["kind"] == "question":
            continue
        rule, _ = layer_a(build_html(case))
        assert rule, f"{case['id']} was not blocked by the deterministic front"
