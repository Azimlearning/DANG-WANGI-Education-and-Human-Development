"""The LLM fallback for heads the local router is not confident about. It goes through the LLM seam (spend ledger, fakes by default).

The prompt is the versioned file `api/prompts/router-fallback.v<N>.md`. The reply is parsed strictly: a field that is missing or not one of
the allowed values is ignored and the router keeps its local answer, flagged as a default.
"""

from __future__ import annotations

import json
import re

from api.llm.service import LLMService
from api.llm.types import LLMRequest
from api.prompts import load
from api.routing.keywords import best_topic

PURPOSE = "route"
_JSON = re.compile(r"\{.*\}", re.DOTALL)


def build_request(question: str, allowed: dict[str, list[str]], topic_names: dict[str, str]) -> LLMRequest:
    prompt = load("router-fallback")
    fields = "\n".join(
        f'- "{head}": one of {json.dumps(values)}' for head, values in allowed.items() if head != "topic"
    )
    if "topic" in allowed:
        fields = '- "topic": a topic slug from the list below, or "none"\n' + fields
    topics = "\n".join(f"{slug}: {name}" for slug, name in sorted(topic_names.items()))
    return LLMRequest(
        prompt=prompt.render(question=question, fields=fields, topics=topics),
        purpose=PURPOSE,
        tier="light",
        max_tokens=200,
    )


def parse(text: str, allowed: dict[str, list[str]]) -> dict[str, str | int]:
    """The valid fields of the reply, as the original typed values. Anything unparseable gives an empty result."""
    match = _JSON.search(text)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str | int] = {}
    for head, values in allowed.items():
        got = data.get(head)
        for v in values:
            if str(v) == str(got):
                out[head] = v
                break
    return out


async def ask(
    llm: LLMService, question: str, allowed: dict[str, list[str]], topic_names: dict[str, str]
) -> dict[str, str | int]:
    result = await llm.complete(build_request(question, allowed, topic_names))
    return parse(result.text, allowed)


def fake_responder(request: LLMRequest) -> str:
    """Deterministic development reply: the first allowed value of every field, the keyword finder's topic, and that topic's subject as the domain. Spends nothing."""
    allowed = {
        m.group(1): json.loads(m.group(2))
        for m in re.finditer(r'^- "(\w+)": one of (\[.*\])$', request.prompt, re.MULTILINE)
    }
    reply: dict[str, object] = {head: values[0] for head, values in allowed.items()}
    if '- "topic"' in request.prompt:
        question = re.search(r'Question:\n"""\n(.*?)\n"""', request.prompt, re.DOTALL)
        reply["topic"] = best_topic(question.group(1)) if question else "none"
    if "domain" in reply and reply.get("topic", "none") != "none":
        subject = str(reply["topic"]).split("_form")[0]
        if subject in allowed["domain"]:
            reply["domain"] = subject
    return json.dumps(reply)
