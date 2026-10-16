"""Plan/verifier parity fuzzer: mutate the golden Plans, and for every mutant the plan checks ACCEPT, require the real verifier to mint it.

    uv run python eval/plans/fuzz.py [seed] [count]        # about 3 s per accepted mutant; free, no model call

A mutant the plan checks accept but the verifier refuses is a parity gap (S4): either the plan checks are too lax or the Kit is wrong. The first
runs found two: a slider whose step overshot max for a repeating decimal (Kit fix) and a readout with too few digits to show a control's effect
(PLAN-017). Run several seeds after changing the plan checks, the assembler or the Kit.
"""

from __future__ import annotations

import copy
import glob
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from api import kitmanifest  # noqa: E402
from api.kit import latest_version  # noqa: E402
from api.pipeline import plan as pm  # noqa: E402
from api.pipeline.assemble import AssemblyGap, assemble  # noqa: E402
from api.pipeline.plan_checks import check  # noqa: E402
from api.schema.generated import Citation  # noqa: E402
from api.verify.mint import VerificationFailed, verify_environment  # noqa: E402

KIT = REPO / "packages" / "kit" / "dist"
m = kitmanifest.load(KIT, latest_version(KIT))
plans = [json.load(open(f)) for f in sorted(glob.glob(str(REPO / "data" / "plans" / "*.json")))]
rnd = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)


def mutate(d):
    d = copy.deepcopy(d)
    kind = rnd.choice(["min", "max", "value", "grid", "param", "unit", "label", "sentence", "digits", "second"])
    c = rnd.choice(d["controls"])
    if kind == "min":
        c["min"] = round(c["min"] + rnd.choice([-5, -1, -0.5, 0.5, 1, 5]) * max(abs(c["max"] - c["min"]) / 10, 0.1), 3)
    elif kind == "max":
        c["max"] = round(c["max"] + rnd.choice([-5, -1, 1, 5, 50]) * max(abs(c["max"] - c["min"]) / 10, 0.1), 3)
    elif kind == "value":
        c["value"] = round(rnd.uniform(c["min"], c["max"]), 3)
    elif kind == "grid":
        c["grid"] = rnd.choice([1, 2, 3, 40, 80, 200, 500])
    elif kind == "param":
        mdl = rnd.choice(d["models"])
        if mdl["params"]:
            k = rnd.choice(list(mdl["params"]))
            mdl["params"][k] = round(mdl["params"][k] * rnd.choice([0, 0.5, 2, 10, -1, 1000]), 4)
    elif kind == "unit":
        c["unit"] = rnd.choice(["m", "cm", "kg", "g", "s", "V"])
    elif kind == "label":
        c["label"] = rnd.choice(["Speed 12 km", "x" * 70, "Value 3"])
    elif kind == "sentence":
        d["sentences"] = d["sentences"] + [rnd.choice(["The answer is 7.", "Try 3.7 and 99.", "Step 2 of 5."])]
    elif kind == "digits":
        r = rnd.choice(d["readouts"])
        r["digits"] = rnd.choice([0, 1, 6, 10])
    elif kind == "second":
        if len(d["controls"]) > 1:
            d["controls"].pop()
    return d, kind


results = []
N = int(sys.argv[2]) if len(sys.argv) > 2 else 30
if True:
    for i in range(N):
        base = rnd.choice(plans)
        d, kind = mutate(base)
        try:
            pl = pm.parse(json.dumps(d))
        except Exception:
            results.append((i, kind, base["id"], "schema-reject"))
            continue
        issues = check(pl, m)
        if issues:
            results.append((i, kind, base["id"], "plan-reject " + ",".join(sorted({x.code for x in issues}))))
            continue
        try:
            page = assemble(pl, m)
        except AssemblyGap as g:
            results.append((i, kind, base["id"], f"GAP {g}"))
            continue
        try:
            verify_environment(
                slug=pl.id,
                title=pl.title,
                raw_html=page.html,
                lane="compose",
                label="model-checked",
                kit_version=m.version,
                citations=[Citation(source="UNVERIFIED", page=None, quote=None, verified=False)],
                plan_summary=pl.goal,
                public_origin="http://localhost:3000",
                kit_dist=KIT,
                interaction_seconds=1.0,
                plan_models=pl.model_summaries(),
            )
            results.append((i, kind, base["id"], "minted"))
        except VerificationFailed as f:
            results.append(
                (
                    i,
                    kind,
                    base["id"],
                    f"PARITY-GAP verifier refused {f.stage}/{f.rule}: {f.reason[:120]}\n    mutation: {json.dumps(d['controls'])[:300]} params={[mm['params'] for mm in d['models']]}",
                )
            )
for r in results:
    print(r)
print(
    {
        s: sum(1 for r in results if r[3].startswith(s))
        for s in ["minted", "plan-reject", "schema-reject", "PARITY", "GAP"]
    }
)
