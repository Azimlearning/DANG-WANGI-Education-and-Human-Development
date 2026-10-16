"""The generated wire models fail closed: unknown fields, coerced types and unknown enum values are all refused."""

import pytest
from pydantic import TypeAdapter, ValidationError

from api.schema.generated import Citation, EnvironmentBlock, StreamEvent


def _block() -> dict:
    return {
        "type": "Environment",
        "id": "reference-spring",
        "meta": {"status": "ready", "error": None},
        "title": "A spring",
        "lane": "instantiate",
        "label": "dev-fixture",
        "kitVersion": "0.0.1",
        "htmlSha256": "0" * 64,
        "html": "<!doctype html><html></html>",
        "citations": [{"source": "UNVERIFIED", "page": None, "quote": None, "verified": False}],
        "planSummary": "A hand-written fixture.",
    }


def test_valid_block_is_accepted() -> None:
    assert EnvironmentBlock.model_validate(_block()).lane == "instantiate"


def test_unknown_field_is_rejected() -> None:
    data = _block() | {"surprise": 1}
    with pytest.raises(ValidationError):
        EnvironmentBlock.model_validate(data)


def test_string_is_not_coerced_to_int() -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate({"source": "x", "page": "1", "quote": None, "verified": False})


def test_unknown_lane_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EnvironmentBlock.model_validate(_block() | {"lane": "improvise"})


def test_unknown_label_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EnvironmentBlock.model_validate(_block() | {"label": "trust-me"})


def test_stream_event_union_discriminates_on_type() -> None:
    adapter = TypeAdapter(StreamEvent)
    assert adapter.validate_python({"type": "done"}).type == "done"
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "nonsense"})
