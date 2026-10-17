"""Hostile set: every case must be blocked by at least two independent layers (the criterion carried over from Synapse v3).

    uv run python eval/hostile/run.py

Provenance: cases H1 to H5 are ported from Synapse-V3 `evals/hostile.yaml` @ 835a2cefda285b4282ea4d0dbf986d1ff08abdb2 (commit named in
data/hostile/hostile.json). H6 onward are v4 additions. Free to run (no model calls).

Layer A is the whole real chain's deterministic front (comment stripping, single document, the L0 scan). Layer B is the render
harness on the same page with the L0 scan SKIPPED, so a page the scan never saw still has to be stopped by the CSP, the navigation
trap, the audit or a runtime error. A case that only one layer stops is reported as single-layer, not hidden.
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api import postprocess  # noqa: E402
from api.kit import latest_version  # noqa: E402
from api.verify.render import render_check  # noqa: E402

CASES = REPO / "data" / "hostile" / "hostile.json"
SPRING = REPO / "data" / "fixtures" / "envs" / "reference-spring.html"
KIT_DIST = REPO / "packages" / "kit" / "dist"
REPORT = REPO / "refdocs" / "evidence" / "2026-10-16-p1-hostile-run.md"
ORIGIN = "http://localhost:3000"
READY = "Synapse.bridge.ready();"


@dataclass
class Result:
    case: dict
    layer_a: str  # "" when not blocked, else "rule"
    layer_b: str
    detail_a: str = ""
    detail_b: str = ""

    @property
    def blocked_by(self) -> int:
        return bool(self.layer_a) + bool(self.layer_b)


def build_html(case: dict) -> str:
    if case["kind"] == "document":
        return case["html"]
    html = SPRING.read_text(encoding="utf-8")
    return html.replace(READY, case["inject"] + "\n  " + READY, 1)


def layer_a(html: str) -> tuple[str, str]:
    out = postprocess.run(html, public_origin=ORIGIN, kit_version=latest_version(KIT_DIST))
    if isinstance(out, postprocess.PostprocessReject):
        return out.rule, out.reason[:120]
    return "", ""


def layer_b(html: str) -> tuple[str, str]:
    """The render harness with the scan skipped: strip comments, single document, then CSP, then run it."""
    s = postprocess.strip_comments(html)
    if isinstance(s, postprocess.PostprocessReject):
        return "", ""  # not an independent test of the runtime layers
    s = postprocess.enforce_single_document(s)
    if isinstance(s, postprocess.PostprocessReject):
        return "", ""
    s = postprocess.inject_csp(postprocess.ensure_charset(postprocess.ensure_viewport(s)), ORIGIN)
    report = render_check(
        s, kit_dist=KIT_DIST, public_origin=ORIGIN, interaction_seconds=1.0, plan_models=None, kit_lane=True
    )
    refusal = report.refusal()
    return (refusal[0], refusal[1][:120]) if refusal else ("", "")


def question_case(case: dict) -> Result:
    from fastapi.testclient import TestClient

    from api.app import create_app
    from api.core.settings import Settings

    word, times = case["question_repeat"]
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            synapse_llm_mode="fake",
            public_origin=ORIGIN,
            data_dir=Path(tmp),
            kit_dist_dir=KIT_DIST,
            ledger_path=Path(tmp) / "ledger.db",
        )
        app = create_app(settings)
        try:
            response = TestClient(app).post("/ask", json={"question": " ".join([word] * times)})
        finally:
            app.state.ledger.close()  # Windows cannot remove the temp directory while the ledger file is open
        blocked = response.status_code == 400
        return Result(case, "api_validation" if blocked else "", "", f"HTTP {response.status_code}")


def run_case(case: dict) -> Result:
    if case["kind"] == "question":
        return question_case(case)
    html = build_html(case)
    a, da = layer_a(html)
    b, db = layer_b(html)
    return Result(case, a, b, da, db)


def main() -> int:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    results = [run_case(c) for c in data["cases"]]
    rows = [
        "| Case | What | Layer A (L0 and post-process) | Layer B (render, scan skipped) | Blocked by |",
        "|---|---|---|---|---|",
    ]
    single, none = [], []
    for r in results:
        need = 1 if r.case["kind"] == "question" else 2
        ok = r.blocked_by >= need
        print(
            f"{r.case['id']:4} {'PASS' if ok else 'FAIL'} A={r.layer_a or '-':22} B={r.layer_b or '-':22} {r.case['reason']}"
        )
        rows.append(
            f"| {r.case['id']} | {r.case['reason']} | {r.layer_a or 'not blocked'} | {r.layer_b or 'not blocked'} | {r.blocked_by} |"
        )
        if r.blocked_by == 0:
            none.append(r.case["id"])
        elif not ok:
            single.append(r.case["id"])
    passed = sum(r.blocked_by >= (1 if r.case["kind"] == "question" else 2) for r in results)
    print(
        f"\n{passed} of {len(results)} blocked by the required number of layers; single-layer: {single or 'none'}; unblocked: {none or 'none'}"
    )
    REPORT.write_text(
        f"""# Hostile set run

> Generated by `uv run python eval/hostile/run.py` (do not edit by hand). Kit {latest_version(KIT_DIST)}. No model calls.
> Criterion carried over from Synapse v3: every item blocked by at least two independent layers. Cases H1 to H5 are ported from
> Synapse-V3 `evals/hostile.yaml`; H6 to H20 are v4 additions. Layer B runs the render harness with the L0 scan skipped.

**Result: {passed} of {len(results)} meet the criterion.** Single-layer: {", ".join(single) or "none"}. Not blocked: {", ".join(none) or "none"}.

{chr(10).join(rows)}

## Limits

- These are known attack shapes written by the people who wrote the defences. They show the layers overlap on those shapes, not that
  a new shape cannot get through.
- Layer B shares the browser with the real chain; both rely on the Content-Security-Policy and the sandbox. Independence here is of
  the checking code, not of the browser.
- A page that only misbehaves under a condition the harness never creates is untested (A-10, isolation, is the answer).
""",
        encoding="utf-8",
    )
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
