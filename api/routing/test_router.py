from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path

import pytest

from api.llm.ledger import SpendLedger
from api.llm.providers.fake import FakeProvider
from api.llm.service import LLMService
from api.models import gate as gate_module
from api.models import router_model
from api.models.misconceptions import MisconceptionMatcher, default_matcher
from api.prompts import load
from api.routing import fallback
from api.routing.router import route


def fake_llm(responder=fallback.fake_responder):  # noqa: ANN001
    provider = FakeProvider(responder)
    return LLMService(provider, None, _ledger()), provider


def _ledger() -> SpendLedger:
    from api.core.settings import Settings
    from api.llm.factory import build_ledger

    return build_ledger(Settings(synapse_llm_mode="fake", ledger_path=Path(":memory:")))


@pytest.fixture(scope="module")
def model() -> router_model.RouterModel:
    return router_model.default_model()


@pytest.fixture(scope="module")
def gates(model: router_model.RouterModel) -> dict[str, gate_module.HeadGate]:
    return gate_module.load(model)


def run(coro):  # noqa: ANN001, ANN201
    return asyncio.run(coro)


def test_a_confident_question_is_answered_locally_without_the_llm(model, gates) -> None:  # noqa: ANN001
    llm, provider = fake_llm()
    always = {h: gate_module.HeadGate(True, 0.0) for h in gates}  # accept everything
    r = run(route("Show me how Hooke's law works with a spring", model=model, gates=always, llm=llm))
    assert all(d.source == "local" for d in r.decisions().values())
    assert provider.calls == []


def test_heads_below_their_threshold_go_to_the_llm_in_one_call(model, gates) -> None:  # noqa: ANN001
    llm, provider = fake_llm()
    never = {h: gate_module.HeadGate(True, 1.01) for h in gates}  # nothing reaches the threshold
    r = run(route("Show me how Hooke's law works with a spring", model=model, gates=never, llm=llm))
    assert all(d.source == "llm_fallback" for d in r.decisions().values())
    assert len(provider.calls) == 1
    assert provider.calls[0].purpose == "route" and provider.calls[0].tier == "light"


def test_a_head_marked_not_useful_always_goes_to_the_llm(model, gates) -> None:  # noqa: ANN001
    llm, provider = fake_llm()
    mixed = {**{h: gate_module.HeadGate(True, 0.0) for h in gates}, "complexity": gate_module.HeadGate(False, None)}
    r = run(route("What is osmosis", model=model, gates=mixed, llm=llm))
    assert r.complexity.source == "llm_fallback" and r.domain.source == "local"
    assert (
        len(provider.calls) == 1
        and '"complexity"' in provider.calls[0].prompt
        and '"domain"' not in provider.calls[0].prompt
    )


def test_without_an_llm_the_local_answer_is_kept_and_flagged_as_a_default(model) -> None:  # noqa: ANN001
    never = {h: gate_module.HeadGate(True, 1.01) for h in ("topic", "domain", "pattern", "complexity")}
    r = run(route("What is osmosis", model=model, gates=never, llm=None))
    assert all(d.source == "default" for d in r.decisions().values())


def test_a_garbled_llm_reply_falls_back_to_defaults(model) -> None:  # noqa: ANN001
    llm, _ = fake_llm(lambda _r: "I cannot help with that")
    never = {h: gate_module.HeadGate(True, 1.01) for h in ("topic", "domain", "pattern", "complexity")}
    r = run(route("What is osmosis", model=model, gates=never, llm=llm))
    assert all(d.source == "default" for d in r.decisions().values())


def test_an_llm_reply_with_a_made_up_topic_is_ignored_for_that_field(model) -> None:  # noqa: ANN001
    llm, _ = fake_llm(
        lambda _r: json.dumps(
            {"topic": "physics_form9_magic", "domain": "physics", "pattern": "simulation", "complexity": 2}
        )
    )
    never = {h: gate_module.HeadGate(True, 1.01) for h in ("topic", "domain", "pattern", "complexity")}
    r = run(route("What is osmosis", model=model, gates=never, llm=llm))
    assert r.topic.source == "default" and r.domain.source == "llm_fallback" and r.complexity.value == 2


def test_a_stale_gate_is_refused_so_the_model_is_not_trusted(model, tmp_path) -> None:  # noqa: ANN001
    data = json.loads(gate_module.DEFAULT_GATE.read_text(encoding="utf-8"))
    data["artifact_sha256"] = "0" * 64
    bad = tmp_path / "gate.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(router_model.ArtifactError):
        gate_module.load(model, bad)


def test_routing_uses_no_network(monkeypatch: pytest.MonkeyPatch, model, gates) -> None:  # noqa: ANN001
    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("network used")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    llm, _ = fake_llm()
    run(route("why does a spring stretch", model=model, gates=gates, llm=llm))


def test_the_fallback_prompt_is_a_versioned_file_with_a_stable_hash() -> None:
    p = load("router-fallback")
    assert p.version == 1 and p.purpose and len(p.sha256) == 64
    assert "{{" not in p.render(question="q", fields="f", topics="t")
    with pytest.raises(KeyError):
        p.render(question="q")
    with pytest.raises(FileNotFoundError):
        load("no-such-pack")


def test_fallback_parse_accepts_only_allowed_values() -> None:
    allowed = {"domain": ["biology", "physics"], "complexity": ["1", "2", "3"]}
    assert fallback.parse('noise {"domain": "physics", "complexity": 2} noise', allowed) == {
        "domain": "physics",
        "complexity": "2",
    }
    assert fallback.parse('{"domain": "art"}', allowed) == {}
    assert fallback.parse("not json", allowed) == {}
    assert fallback.parse("[1,2]", allowed) == {}


# ── the misconception matcher ──────────────────────────────────────────────────────────────────────────────────────────


def test_each_seed_misconception_is_found_from_its_own_statement() -> None:
    m = default_matcher()
    for entry in m.entries:
        top = m.match(entry["statement"], top=1)
        assert top and top[0].id == entry["id"], entry["id"]


def test_an_unrelated_question_matches_nothing() -> None:
    assert default_matcher().match("What is the capital of France and how tall is Mount Kinabalu?") == []


def test_every_ported_citation_is_marked_unverified_and_has_provenance() -> None:
    data = json.loads(Path("data/misconceptions.json").read_text(encoding="utf-8"))
    assert "835a2cefda285b4282ea4d0dbf986d1ff08abdb2" in data["provenance"]["source_commit"]
    assert all(e["source_verified"] is False for e in data["entries"])


def test_the_matcher_states_that_its_accuracy_is_unmeasured() -> None:
    import api.models.misconceptions as mod

    assert "accuracy is unmeasured" in (mod.__doc__ or "")
    assert isinstance(default_matcher(), MisconceptionMatcher)


def test_a_local_none_for_the_topic_is_never_trusted_and_goes_to_the_llm(model, gates) -> None:  # noqa: ANN001
    llm, provider = fake_llm()
    q = "Who won the football match last night in the league and what was the score at the end?"
    local = model.predict(q)["topic"]
    assert local.label == "none"  # the model says none for this one
    always = {h: gate_module.HeadGate(True, 0.0) for h in gates}
    r = run(route(q, model=model, gates=always, llm=llm))
    assert r.topic.source == "llm_fallback" and r.domain.source == "local"
    assert len(provider.calls) == 1 and '"topic"' in provider.calls[0].prompt
