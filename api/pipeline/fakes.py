"""Deterministic fake model replies for development and tests (SYNAPSE_LLM_MODE=fake). They spend nothing and open no socket.

The fake planner answers with the hand-written golden plan for the routed topic (data/plans). A topic with no golden plan gets a reply that fails
the schema, so the repair and degrade paths are exercised honestly. Real replies arrive only after the owner confirms a paid run (D-08).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from api.llm.providers.fake import hashed_reply
from api.llm.types import LLMRequest
from api.routing.fallback import fake_responder as route_responder

PLANS = Path(__file__).resolve().parents[2] / "data" / "plans"
_TOPIC = re.compile(r"topic=([a-z0-9_]+)")


def golden_by_topic() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for path in sorted(PLANS.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        out.setdefault(json.loads(text)["topic"], []).append(text)
    return out


def _overlap(question: str, plan_json: str) -> int:
    plan = json.loads(plan_json)
    words = {
        w for w in re.findall(r"[a-z]+", (plan["title"] + " " + plan["goal"] + " " + plan["id"]).lower()) if len(w) > 3
    }
    return len(words & set(re.findall(r"[a-z]+", question.lower())))


def plan_responder(request: LLMRequest) -> str:
    """The golden plan for the routed topic; when a topic has several, the one whose title and goal share the most words with the question."""
    m = _TOPIC.search(request.prompt)
    plans = golden_by_topic().get(m.group(1) if m else "")
    if not plans:
        return '{"error": "no plan available for this topic in fake mode"}'
    question = re.search(r'Student\'s question:\n"""\n(.*?)\n"""', request.prompt, re.DOTALL)
    q = question.group(1) if question else ""
    return max(plans, key=lambda p: (_overlap(q, p), -plans.index(p)))


def fill_responder(_request: LLMRequest) -> str:
    return 'Synapse.text(env, "Try moving each slider and watch what changes.");'


def fake_responder(request: LLMRequest) -> str:
    return {
        "route": route_responder,
        "plan": plan_responder,
        "fill": fill_responder,
    }.get(request.purpose, hashed_reply)(request)
