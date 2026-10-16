"""Static mounts. The Kit is served from the build output at /vendor/kit/<semver>/ on our own origin (hard constraint 2: scripts
load only from /vendor/ and /vendor/kit/<semver>/; no runtime CDN)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


class KitFiles(StaticFiles):
    """S9: an unreleased Kit version is relocked in place (D-16), so a browser must revalidate rather than reuse a stale bundle.
    `no-cache` still lets the browser keep the file and ask with its ETag; a released version can be made immutable at the deploy gate."""

    def file_response(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def mount_kit(app: FastAPI, kit_dist: Path) -> None:
    app.mount("/vendor/kit", KitFiles(directory=kit_dist), name="kit")
