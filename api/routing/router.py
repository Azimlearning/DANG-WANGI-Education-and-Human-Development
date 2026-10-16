"""Route a question: the local model answers each head it is confident about; the LLM seam answers the rest.

`route()` never raises for a model problem: if the artifact or its gate is missing, stale or corrupt, every head goes to the fallback, and if
there is no fallback either, every head is a flagged default. A head the calibration marked "not useful as a gate" always goes to the fallback.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from api.llm.service import LLMService
from api.models import gate as gate_module
from api.models import router_model
from api.routing import fallback

log = logging.getLogger(__name__)
TAXONOMY = Path(__file__).resolve().parents[2] / "data" / "kssm_topics.json"
Source = Literal["local", "llm_fallback", "default"]


@dataclass(frozen=True)
class Decision:
    value: str | int
    confidence: float
    source: Source


@dataclass(frozen=True)
class Route:
    question: str
    topic: Decision
    domain: Decision
    pattern: Decision
    complexity: Decision

    def decisions(self) -> dict[str, Decision]:
        return {"topic": self.topic, "domain": self.domain, "pattern": self.pattern, "complexity": self.complexity}


def topic_names() -> dict[str, str]:
    topics = json.loads(TAXONOMY.read_text(encoding="utf-8"))["topics"]
    return {f"{t['subject']}_form{t['form']}_{t['slug']}": t["label"] for t in topics}


async def route(
    question: str,
    *,
    model: router_model.RouterModel | None = None,
    gates: dict[str, gate_module.HeadGate] | None = None,
    llm: LLMService | None = None,
) -> Route:
    local: dict[str, router_model.HeadPrediction] = {}
    try:
        model = model or router_model.default_model()
        gates = gates if gates is not None else gate_module.load(model)
        local = model.predict(question)
    except router_model.ArtifactError as exc:
        log.warning("router_model_unavailable reason=%s", exc)
        gates = {}

    decisions: dict[str, Decision] = {}
    need: list[str] = []
    for head in ("topic", "domain", "pattern", "complexity"):
        prediction = local.get(head)
        g = gates.get(head) if gates else None
        # A local "none" is never trusted: the class is weak (see the model card) and a wrong "none" costs the student their Environment, while
        # asking the fallback costs one small call. Everything else is gated by the head's calibrated threshold.
        trusted = not (head == "topic" and prediction is not None and prediction.label == "none")
        if (
            trusted
            and prediction is not None
            and g is not None
            and g.useful
            and g.threshold is not None
            and prediction.confidence >= g.threshold
        ):
            decisions[head] = Decision(prediction.label, round(prediction.confidence, 4), "local")
        else:
            need.append(head)

    if need:
        answered: dict[str, str | int] = {}
        if llm is not None and model is not None:
            allowed = {h: [str(c) for c in model.heads[h]] for h in need if h in model.heads}
            if "topic" in allowed:
                allowed["topic"] = sorted({*allowed["topic"], "none"})
            try:
                answered = await fallback.ask(llm, question, allowed, topic_names())
            except Exception as exc:  # noqa: BLE001 - a failed fallback must not fail the request; the local answer is kept as a default
                log.warning("router_fallback_failed reason=%s", exc)
        for head in need:
            prediction = local.get(head)
            if head in answered:
                value = answered[head]
                if head == "complexity":
                    value = int(value)
                decisions[head] = Decision(value, 1.0, "llm_fallback")
            elif prediction is not None:
                decisions[head] = Decision(prediction.label, round(prediction.confidence, 4), "default")
            else:
                decisions[head] = Decision("none" if head == "topic" else "unknown", 0.0, "default")
    return Route(question, decisions["topic"], decisions["domain"], decisions["pattern"], decisions["complexity"])
