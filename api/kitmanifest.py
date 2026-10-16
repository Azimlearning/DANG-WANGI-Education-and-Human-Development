"""The built Kit manifest as the API sees it. The API never imports Kit source; it reads `dist/<semver>/manifest.json`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Quantity:
    unit: str
    min: float
    exclusive: bool = False


@dataclass(frozen=True)
class ScienceModel:
    model_id: str
    export_name: str
    inputs: dict[str, Quantity]
    params: dict[str, Quantity]
    output_unit: str
    citation: str
    use_when: str
    topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class Manifest:
    version: str
    sha256: str
    components: dict[str, dict]
    models: dict[str, ScienceModel]

    def has(self, component_id: str) -> bool:
        return component_id in self.components


def _quantities(raw: dict) -> dict[str, Quantity]:
    return {k: Quantity(v["unit"], float(v["min"]), bool(v.get("exclusive", False))) for k, v in raw.items()}


def load(kit_dist: Path, version: str) -> Manifest:
    data = json.loads((kit_dist / version / "manifest.json").read_text(encoding="utf-8"))
    components = {c["id"]: c for c in data["components"]}
    models = {
        c["modelId"]: ScienceModel(
            c["modelId"],
            c["id"],
            _quantities(c["inputs"]),
            _quantities(c.get("params", {})),
            c["output"]["unit"],
            c["citation"],
            c.get("useWhen", ""),
            tuple(c.get("topics", ())),
        )
        for c in data["components"]
        if c["kind"] == "science"
    }
    return Manifest(version=data["version"], sha256=data["bundleSha256"], components=components, models=models)
