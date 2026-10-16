"""The confidence gate chosen in `eval/models/calibrate.py`, bound to one artifact by its hash. A gate for a different artifact is refused."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from api.models.router_model import ArtifactError, RouterModel

DEFAULT_GATE = Path(__file__).resolve().parent / "artifacts" / "router-v1.gate.json"


@dataclass(frozen=True)
class HeadGate:
    useful: bool
    threshold: float | None


def load(model: RouterModel, path: Path = DEFAULT_GATE) -> dict[str, HeadGate]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read router gate {path}: {exc}") from exc
    if data.get("artifact_sha256") != model.sha256:
        raise ArtifactError("the router gate was calibrated for a different artifact; re-run eval/models/calibrate.py")
    return {h: HeadGate(bool(g["useful"]), g["threshold"]) for h, g in data["heads"].items()}
