"""Entry point: `uv run uvicorn api.main:app --reload --port 8000`. Fakes by default (SYNAPSE_LLM_MODE=fake)."""

from api.app import create_app

app = create_app()
