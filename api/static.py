"""Static mounts. The Kit is served from the build output at /vendor/kit/<semver>/ on our own origin (hard constraint 2: scripts
load only from /vendor/ and /vendor/kit/<semver>/; no runtime CDN)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_kit(app: FastAPI, kit_dist: Path) -> None:
    app.mount("/vendor/kit", StaticFiles(directory=kit_dist), name="kit")
