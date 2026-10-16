"""POST /ask on fakes: the stream order, that every event validates against the generated models, the request bounds, and
that a refused delivery reaches the client as an error event, never as an Environment."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from api.app import create_app
from api.core.settings import Settings
from api.schema.generated import EnvironmentEvent, ErrorEnvelope, StreamEvent
from api.seed import seed_reference, store_path

REPO = Path(__file__).resolve().parents[2]
EVENTS = TypeAdapter(StreamEvent)


def _settings(data_dir: Path, kit_dist: Path, **extra) -> Settings:
    return Settings(_env_file=None, data_dir=data_dir, kit_dist_dir=kit_dist, **extra)  # type: ignore[call-arg]


def _data_dir(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    shutil.copytree(REPO / "data" / "fixtures", data / "fixtures")
    return data


@pytest.fixture(scope="module")
def seeded_dir(tmp_path_factory: pytest.TempPathFactory, kit_dist: Path) -> Path:
    data = _data_dir(tmp_path_factory.mktemp("seeded"))
    seed_reference(_settings(data, kit_dist), interaction_seconds=1.0)
    return data


@pytest.fixture
def client(seeded_dir: Path, kit_dist: Path, tmp_path: Path) -> TestClient:
    # A fresh copy of the seeded stores per test, so a test that tampers with a row cannot affect the next one.
    data = tmp_path / "data"
    shutil.copytree(seeded_dir, data)
    return TestClient(create_app(_settings(data, kit_dist)))


def _events(client: TestClient, question: str = "why does a spring stretch") -> list:
    with client.stream("POST", "/ask", json={"question": question}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = [line for line in response.iter_lines() if line.startswith("data:")]
    return [EVENTS.validate_json(line.removeprefix("data:").strip()) for line in lines]


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_stream_order_is_meta_text_environment_done_and_every_event_validates(client: TestClient) -> None:
    kinds = [e.type for e in _events(client)]
    assert kinds[0] == "meta"
    assert kinds[-1] == "done"
    assert kinds[-2] == "environment"
    middle = kinds[1:-2]
    assert len(middle) >= 1
    assert set(middle) == {"text_delta"}


def test_meta_and_block_carry_the_honest_label_and_lane(client: TestClient, kit_version: str) -> None:
    events = _events(client)
    meta, block = events[0], next(e for e in events if isinstance(e, EnvironmentEvent)).block
    assert (meta.lane, meta.label, meta.kitVersion) == ("instantiate", "model-checked", kit_version)
    assert (block.lane, block.label) == ("instantiate", "model-checked")
    assert block.citations[0].verified is False
    assert block.htmlSha256 == hashlib.sha256(block.html.encode("utf-8")).hexdigest()


def test_text_deltas_rejoin_to_the_fake_reply(client: TestClient) -> None:
    text = "".join(e.text for e in _events(client) if e.type == "text_delta")
    assert text.startswith("[fake:explain:")


def test_the_same_question_gets_the_same_text(client: TestClient) -> None:
    def text() -> str:
        return "".join(e.text for e in _events(client, "same question") if e.type == "text_delta")

    assert text() == text()


def test_the_call_goes_through_the_ledger_at_no_cost(client: TestClient) -> None:
    _events(client)
    (row,) = client.app.state.ledger.rows()  # type: ignore[attr-defined]
    assert (row["provider"], row["purpose"], row["status"], row["cost_usd"]) == ("fake", "explain", "ok", 0.0)


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
def test_a_bad_question_is_a_400_envelope_before_any_stream(client: TestClient, question: str) -> None:
    response = client.post("/ask", json={"question": question})
    assert response.status_code == 400
    assert ErrorEnvelope.model_validate(response.json()).code == "bad_request"


@pytest.mark.parametrize("body", [{}, {"question": 5}, {"question": "ok", "extra": 1}])
def test_a_malformed_body_is_a_422_envelope(client: TestClient, body: dict) -> None:
    response = client.post("/ask", json=body)
    assert response.status_code == 422
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.code == "validation_failed"
    assert envelope.issues


def test_an_unseeded_store_is_an_error_event_then_done(tmp_path: Path, kit_dist: Path) -> None:
    client = TestClient(create_app(_settings(_data_dir(tmp_path), kit_dist)))
    events = _events(client)
    assert [e.type for e in events if e.type != "text_delta"] == ["meta", "error", "done"]
    error = next(e for e in events if e.type == "error")
    assert error.error.code == "not_found"
    assert "api.seed" in error.error.message


def test_a_tampered_row_reaches_the_client_as_a_refusal_never_as_an_environment(
    seeded_dir: Path, kit_dist: Path, tmp_path: Path
) -> None:
    data = tmp_path / "data"
    shutil.copytree(seeded_dir, data)
    with sqlite3.connect(store_path(_settings(data, kit_dist))) as conn:
        conn.execute("UPDATE environments SET html = replace(html, 'Extension', 'Extensioz')")
    events = _events(TestClient(create_app(_settings(data, kit_dist))))
    assert not any(e.type == "environment" for e in events)
    error = next(e for e in events if e.type == "error")
    assert error.error.code == "verification_refused"
    assert error.error.issues[0].path == "gate/hash_mismatch"
    assert events[-1].type == "done"


def test_an_unexpected_failure_does_not_leak_its_detail(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_slug: str) -> str:
        raise RuntimeError("secret internal detail /home/x/key")

    monkeypatch.setattr(client.app.state.store, "latest_id", boom)  # type: ignore[attr-defined]
    error = next(e for e in _events(client) if e.type == "error")
    assert error.error.code == "internal"
    assert "secret" not in error.error.message
    assert "/home" not in error.error.model_dump_json()


def test_live_mode_without_a_provider_is_a_clean_error_event(seeded_dir: Path, kit_dist: Path, tmp_path: Path) -> None:
    data = tmp_path / "data"
    shutil.copytree(seeded_dir, data)
    settings = _settings(data, kit_dist, synapse_llm_mode="live", anthropic_api_key="sk-test", llm_monthly_cap_usd=5)
    error = next(e for e in _events(TestClient(create_app(settings))) if e.type == "error")
    assert error.error.code == "provider_unavailable"
    assert error.error.retryable is True


def test_cors_allows_only_the_public_origin(client: TestClient) -> None:
    allowed = client.options(
        "/ask",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    other = client.options("/ask", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in other.headers


def test_the_kit_is_served_same_origin_and_cannot_be_escaped(client: TestClient, kit_version: str) -> None:
    js = client.get(f"/vendor/kit/{kit_version}/core.js")
    assert js.status_code == 200
    assert "Synapse" in js.text
    assert client.get(f"/vendor/kit/{kit_version}/manifest.json").json()["version"] == kit_version
    assert client.get("/vendor/kit/../../pyproject.toml").status_code in (404, 400)
    assert client.get("/vendor/kit/%2e%2e/%2e%2e/pyproject.toml").status_code == 404
