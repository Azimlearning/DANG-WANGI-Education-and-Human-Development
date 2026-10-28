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
    max: float | None = None
    """A ceiling, for a quantity that has one (an angle of incidence below 90 degrees). Most have none."""
    max_exclusive: bool = False


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
    apparatus: dict[str, dict] | None = None
    """The apparatus catalogue (W16, D-66): part kind to its channels ({type, units?, optional?}), doc and use. None for a Kit built before it."""

    def has(self, component_id: str) -> bool:
        return component_id in self.components


def _quantities(raw: dict) -> dict[str, Quantity]:
    return {
        k: Quantity(
            v["unit"],
            float(v["min"]),
            bool(v.get("exclusive", False)),
            float(v["max"]) if v.get("max") is not None else None,
            bool(v.get("maxExclusive", False)),
        )
        for k, v in raw.items()
    }


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
    return Manifest(version=data["version"], sha256=data["bundleSha256"], components=components, models=models, apparatus=data.get("apparatus"))
