"""Write a reference fixture (the assembled page and its plan summary) for a golden Plan, so L6 can plant defects into it.

    uv run python eval/l6/make_fixture.py physics-f4-refraction refraction

Writes `data/fixtures/envs/reference-<name>.html` and `reference-<name>.plan.json`. Free: no model call and no browser. The page is exactly what the assembler makes from the
Plan against the built Kit, so it passes the verifier as it stands; a mutation row then breaks one thing in it. Rebuild a fixture when the Plan or the assembler changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api import kitmanifest  # noqa: E402
from api.kit import latest_version  # noqa: E402
from api.pipeline import plan as plan_module  # noqa: E402
from api.pipeline.assemble import assemble  # noqa: E402

FIXTURES = REPO / "data" / "fixtures" / "envs"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    plan_name, short = argv
    kit_dist = REPO / "packages" / "kit" / "dist"
    manifest = kitmanifest.load(kit_dist, latest_version(kit_dist))
    plan = plan_module.parse((REPO / "data" / "plans" / f"{plan_name}.json").read_text(encoding="utf-8"))
    html = assemble(plan, manifest).html
    (FIXTURES / f"reference-{short}.html").write_text(html, encoding="utf-8")
    summary = {
        "id": f"reference-{short}",
        "title": plan.title,
        "lane": "instantiate",
        "label": "model-checked",
        "kitVersion": manifest.version,
        "planSummary": plan.goal,
        "citations": [{"source": "UNVERIFIED (fixture, no corpus)", "page": None, "quote": None, "verified": False}],
        "controls": [c.id for c in plan.controls],
        "readouts": [r.label for r in plan.readouts],
        "models": plan.model_summaries(),
    }
    (FIXTURES / f"reference-{short}.plan.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote reference-{short}.html and reference-{short}.plan.json from {plan_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
