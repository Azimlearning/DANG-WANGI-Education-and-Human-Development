"""A-10 isolation spike: can the verification harness run with no network and bounded resources, and at what cost?

    uv run python eval/isolation/spike.py inner     # what runs INSIDE the sandbox: probe the network, then verify the spring fixture
    uv run python eval/isolation/spike.py           # run `inner` under each isolation option and print a table

Free to run. Records facts about THIS container; it does not decide a public deploy (see the evidence note for the options).
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def inner() -> None:
    probe: dict[str, object] = {}
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=2).close()
        probe["outbound_tcp"] = "OPEN"
    except OSError as e:
        probe["outbound_tcp"] = f"blocked ({type(e).__name__})"
    try:
        socket.getaddrinfo("example.com", 443)
        probe["dns"] = "OPEN"
    except OSError as e:
        probe["dns"] = f"blocked ({type(e).__name__})"
    from api.kit import latest_version
    from api.schema.generated import Citation
    from api.verify.mint import verify_environment

    kit_dist = REPO / "packages" / "kit" / "dist"
    start = time.monotonic()
    try:
        env = verify_environment(
            slug="reference-spring",
            title="t",
            raw_html=(REPO / "data/fixtures/envs/reference-spring.html").read_text(),
            lane="instantiate",
            label="model-checked",
            kit_version=latest_version(kit_dist),
            citations=[Citation(source="UNVERIFIED", page=None, quote=None, verified=False)],
            plan_summary="spike",
            public_origin="http://localhost:3000",
            kit_dist=kit_dist,
            interaction_seconds=1.0,
            plan_models=[{"id": "mechanics.hookes", "params": {"k": 50}}],
        )
        probe["verify"] = f"minted {env.env_id[:12]}"
    except Exception as e:  # noqa: BLE001 - the spike reports whatever happened
        probe["verify"] = f"FAILED {type(e).__name__}: {str(e)[:120]}"
    probe["seconds"] = round(time.monotonic() - start, 1)
    print("RESULT " + json.dumps(probe))


OPTIONS: list[tuple[str, list[str]]] = [
    ("plain process", []),
    ("unshare --net (own network namespace, root mapped)", ["unshare", "--net", "--map-root-user", "--"]),
    (
        "unshare --net --pid --mount-proc",
        ["unshare", "--net", "--pid", "--fork", "--mount-proc", "--map-root-user", "--"],
    ),
    ("prlimit --as 6GiB --cpu 120", ["prlimit", "--as=6442450944", "--cpu=120", "--"]),
    (
        "unshare --net + prlimit --cpu 120 --nproc 400",
        ["unshare", "--net", "--map-root-user", "--", "prlimit", "--cpu=120", "--nproc=400", "--"],
    ),
]


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "inner":
        inner()
        return 0
    rows = ["| Option | Outbound TCP | DNS | Verification | Seconds | Note |", "|---|---|---|---|---|---|"]
    for name, prefix in OPTIONS:
        if prefix and shutil.which(prefix[0]) is None:
            rows.append(f"| {name} | n/a | n/a | n/a | n/a | `{prefix[0]}` not installed |")
            continue
        cmd = [*prefix, sys.executable, str(Path(__file__)), "inner"]
        t = time.monotonic()
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=REPO)
        line = next((ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")), "")
        if line:
            r = json.loads(line[7:])
            rows.append(f"| {name} | {r['outbound_tcp']} | {r['dns']} | {r['verify']} | {r['seconds']} | |")
        else:
            tail = (done.stderr.strip().splitlines() or ["no output"])[-1][:120]
            rows.append(
                f"| {name} | ? | ? | did not run (exit {done.returncode}) | {time.monotonic() - t:.1f} | {tail} |"
            )
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
