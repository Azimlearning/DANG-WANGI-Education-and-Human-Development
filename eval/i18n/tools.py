"""Tools for the Bahasa Melayu overlays (W12, D-62). Free: no model call, no browser.

    uv run python -m eval.i18n.tools skeleton physics-f4-orbit   # the places to translate, with the English beside each
    uv run python -m eval.i18n.tools check                       # every overlay against its Plan: missing, extra, digits, still English, too long
    uv run python -m eval.i18n.tools sheet review.csv            # a sheet for a fluent reviewer: place, English, Malay, approved
    uv run python -m eval.i18n.tools import review.csv --reviewer "Name" --date 2026-11-03   # corrections in, status reviewed only where every row is approved

A reviewed overlay is the only thing that lets a Malay Environment out of draft. The import changes a Plan's overlay to `reviewed` only if every one of its rows is
marked approved; it writes the reviewer's corrected Malay first, and the next build rebuilds and verifies the Malay Environment from it.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from api.i18n import kitwords  # noqa: E402
from api.i18n import overlay as overlay_module  # noqa: E402
from api.pipeline import plan as plan_module  # noqa: E402

PLANS = REPO / "data" / "plans"
WEB_STRINGS = REPO / "web" / "lib" / "strings.json"
APPROVED = {"yes", "y", "ok", "approved", "1", "true"}


def plan_for(stem_or_id: str) -> plan_module.Plan:
    path = PLANS / f"{stem_or_id}.json"
    if path.exists():
        return plan_module.parse(path.read_text(encoding="utf-8"))
    for p in sorted(PLANS.glob("*.json")):
        plan = plan_module.parse(p.read_text(encoding="utf-8"))
        if plan.id == stem_or_id:
            return plan
    raise SystemExit(f"no Plan '{stem_or_id}'")


def all_plans() -> list[tuple[Path, plan_module.Plan]]:
    return [(p, plan_module.parse(p.read_text(encoding="utf-8"))) for p in sorted(PLANS.glob("*.json"))]


def _kit_malay(table: dict[str, dict], place: str) -> str:
    key, _, alt = place.partition("#")
    return table[key]["alt"]["ms"] if alt else table[key]["ms"]


def skeleton(name: str) -> int:
    plan = plan_for(name)
    print(json.dumps({"plan": plan.id, "lang": "ms", "status": "draft", "reviewer": None, "reviewed_on": None, "strings": overlay_module.translatable(plan)}, ensure_ascii=False, indent=2))
    return 0


def check() -> int:
    bad = 0
    done = 0
    for _, plan in all_plans():
        try:
            overlay = overlay_module.load_for(plan.id)
        except overlay_module.OverlayError as exc:
            print(f"{plan.id}: {exc}")
            bad += 1
            continue
        if overlay is None:
            print(f"{plan.id}: no overlay")
            continue
        try:
            malay = overlay_module.apply(plan, overlay)
        except overlay_module.OverlayError as exc:
            print(exc)
            bad += 1
            continue
        from api.pipeline.plan_checks import COPY_FACTOR, MAX_COPY_CHARS, _texts

        chars = sum(len(t) for t in _texts(malay))
        budget = round(MAX_COPY_CHARS * COPY_FACTOR["ms"])
        if chars > budget:
            print(f"{plan.id}: the Malay words add up to {chars} characters, over {budget}")
            bad += 1
            continue
        done += 1
        print(f"{plan.id}: ok ({overlay.status}, {chars} characters)")
    print(f"{done} overlays ok, {bad} with problems")
    return 1 if bad else 0


def sheet(out: Path) -> int:
    rows = 0
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["plan", "place", "english", "malay", "approved"])
        for _, plan in all_plans():
            overlay = overlay_module.load_for(plan.id)
            if overlay is None or overlay.reviewed:
                continue
            english = overlay_module.translatable(plan)
            for pointer, text in english.items():
                w.writerow([plan.id, pointer, text, overlay.strings.get(pointer, ""), ""])
                rows += 1
        web = json.loads(WEB_STRINGS.read_text(encoding="utf-8"))
        for key, entry in web.items():
            if key != "_about" and not entry["reviewed"]:
                w.writerow(["_web", key, entry["en"], entry["ms"], ""])
                rows += 1
        if not kitwords.reviewed():
            for key, entry in kitwords.words().items():
                w.writerow(["_kit", key, entry["en"], entry["ms"], ""])
                rows += 1
                if "alt" in entry:
                    w.writerow(["_kit", f"{key}#alt", entry["alt"]["en"], entry["alt"]["ms"], ""])
                    rows += 1
    print(f"wrote {rows} rows to {out}")
    return 0


def import_sheet(path: Path, reviewer: str, date: str) -> int:
    by_plan: dict[str, list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_plan.setdefault(row["plan"], []).append(row)
    web_rows, kit_rows = by_plan.pop("_web", []), by_plan.pop("_kit", [])
    if web_rows:
        web = json.loads(WEB_STRINGS.read_text(encoding="utf-8"))
        for row in web_rows:
            entry = web[row["place"]]
            entry["ms"] = row["malay"].strip()
            entry["reviewed"] = row["approved"].strip().lower() in APPROVED
        WEB_STRINGS.write_text(json.dumps(web, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"web strings: {sum(1 for r in web_rows if r['approved'].strip().lower() in APPROVED)} of {len(web_rows)} approved")
    if kit_rows:
        table = kitwords.words()
        unchanged = all(row["malay"].strip() == _kit_malay(table, row["place"]) for row in kit_rows)
        approved = all(r["approved"].strip().lower() in APPROVED for r in kit_rows)
        if approved and unchanged:
            kitwords.RECORD.write_text(json.dumps({"digest": kitwords.digest(table), "reviewer": reviewer, "reviewed_on": date}, indent=2) + "\n", encoding="utf-8")
            print("Kit words: reviewed")
        else:
            print("Kit words: NOT marked reviewed" + ("" if unchanged else " (the reviewer changed a word: apply the changes in packages/kit/src/i18n.ts, then export the sheet again)"))
    for plan_id, rows in by_plan.items():
        file = overlay_module.OVERLAYS / f"{plan_id}.json"
        raw = json.loads(file.read_text(encoding="utf-8"))
        for row in rows:
            raw["strings"][row["place"]] = row["malay"].strip()
        approved = all(r["approved"].strip().lower() in APPROVED for r in rows)
        if approved:
            raw.update(status="reviewed", reviewer=reviewer, reviewed_on=date)
        else:
            raw.update(status="draft", reviewer=None, reviewed_on=None)
        file.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{plan_id}: {'reviewed' if approved else 'draft (not every row approved)'}")
    return check()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sk = sub.add_parser("skeleton")
    sk.add_argument("plan")
    sub.add_parser("check")
    sh = sub.add_parser("sheet")
    sh.add_argument("out", type=Path)
    im = sub.add_parser("import")
    im.add_argument("path", type=Path)
    im.add_argument("--reviewer", required=True)
    im.add_argument("--date", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "skeleton":
        return skeleton(args.plan)
    if args.cmd == "check":
        return check()
    if args.cmd == "sheet":
        return sheet(args.out)
    return import_sheet(args.path, args.reviewer, args.date)


if __name__ == "__main__":
    raise SystemExit(main())
