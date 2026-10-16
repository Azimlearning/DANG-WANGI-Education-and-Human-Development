# Adapted from Azimlearning/Arcana-v2, api/core/settings.py @ 21c6dcf5. Read in full. Changes: the mode variable is
# SYNAPSE_LLM_MODE, embeddings are dropped (A-9), OpenRouter is an optional fallback (it is not required in live mode),
# and PUBLIC_ORIGIN is added because the sandbox CSP names it explicitly (hard constraint 2).
"""Typed settings from the process environment (the `.env` file; never the Environment artifact).

Every variable is documented in refdocs/guides/env_setup.md. Fakes are the default, so with SYNAPSE_LLM_MODE=fake no key
is needed and no network call is made. A live mode without its key or without a spend cap raises ConfigError at startup,
naming each missing variable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_SETUP_DOC = "refdocs/guides/env_setup.md"

Mode = Literal["fake", "live"]


class ConfigError(Exception):
    """Startup configuration is unusable. The message names every missing variable."""

    def __init__(self, missing: list[tuple[str, str]]):
        self.missing = missing
        lines = [f"  {name}: {why}" for name, why in missing]
        super().__init__(
            "Missing required configuration:\n"
            + "\n".join(lines)
            + f"\nSee {ENV_SETUP_DOC} for where to get each value."
        )


class Settings(BaseSettings):
    """Field names are the variable names, case-insensitively."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    synapse_llm_mode: Mode = "fake"
    data_dir: Path = Path("./data")
    ledger_path: Path | None = None
    """Where the spend ledger lives. Unset: `<data_dir>/ledger.db`, ONE file so the monthly cap covers every run."""
    kit_dist_dir: Path = Path("./packages/kit/dist")
    """Where the built Kit lives (`<semver>/core.js` and `manifest.json`). Served at /vendor/kit/ and read by the render harness."""
    public_origin: str = "http://localhost:3000"
    """The origin the web app is served from. The injected CSP names it, because an opaque-origin srcdoc makes 'self' match nothing."""
    log_level: str = "INFO"
    corpus_dir: Path | None = None
    """The local textbook corpus (api/evidence). Never in the repository. Unset: no citation can be verified and `kit-verified` cannot be minted."""
    verify_interaction_seconds: float = 10.0
    """How long the render harness presses controls and inputs while verifying one Environment. Tests use 1; do not go below 5 for real use."""

    rate_limit_per_minute: int = 20
    """Questions one client address may ask per minute (0 turns the limit off). Behind a proxy every client shares the proxy's address: set it at the proxy too."""
    max_concurrent_asks: int = 3
    """How many questions are worked on at once. Each can launch a browser to verify an Environment, so this bounds memory and CPU (0 turns it off)."""
    store_attestation_key: SecretStr | None = None
    """HMAC key that signs stored Environments (A-19). Keep it OUTSIDE the data directory. Unset: rows are unsigned and the gate trusts the store."""
    anthropic_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    llm_monthly_cap_usd: float | None = None

    def resolved_ledger_path(self) -> Path:
        return self.ledger_path if self.ledger_path is not None else self.data_dir / "ledger.db"

    def missing_for_mode(self) -> list[tuple[str, str]]:
        """Variables the selected mode requires but the environment did not supply."""
        missing: list[tuple[str, str]] = []
        if self.synapse_llm_mode == "live":
            if not _has(self.anthropic_api_key):
                missing.append(("ANTHROPIC_API_KEY", "required when SYNAPSE_LLM_MODE=live"))
            if self.llm_monthly_cap_usd is None or self.llm_monthly_cap_usd <= 0:
                missing.append(("LLM_MONTHLY_CAP_USD", "required (a positive number) when SYNAPSE_LLM_MODE=live"))
            if not self.resolved_ledger_path().is_absolute():
                missing.append(
                    (
                        "LEDGER_PATH",
                        "must be an absolute path when SYNAPSE_LLM_MODE=live, so the cap holds whatever directory the API is started from",
                    )
                )
        return missing


def _has(secret: SecretStr | None) -> bool:
    return secret is not None and bool(secret.get_secret_value().strip())


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Build settings and fail loudly if live mode lacks its key or cap.

    Tests pass env_file=None so a developer's real .env never leaks into them.
    """
    settings = Settings(_env_file=env_file)  # pyright: ignore[reportCallIssue]
    missing = settings.missing_for_mode()
    if missing:
        raise ConfigError(missing)
    return settings
