"""Build the seeded library into the API's own store (D-42): `uv run python -m api.library_seed`.

Every hand-written Plan in `data/plans` is built into a verified Environment (headless Chromium, about 12 seconds each at the default time box), stored in
`<DATA_DIR>/environments.db` and indexed by its KSSM topic. After this, a question the local router recognises with enough confidence is answered from the
library with no model call. A Plan with a Bahasa Melayu overlay in `data/i18n/ms` also gets its translation built and linked (W12, D-62). Free: no model call, fakes only. With `CORPUS_DIR` set each Plan's citations are re-proved against the corpus, as for any
Environment; without it they are `model-checked`, and they are rebuilt as `kit-verified` the next time this is run with the corpus.
"""

from __future__ import annotations

import argparse

from api.app import citations_for, evidence_for
from api.core.settings import load_settings
from api.i18n.overlay import OVERLAYS
from api.pipeline import library
from api.seed import open_store


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interaction-seconds", type=float, default=None, help="how long the browser presses controls per Environment (default: the setting)")
    ap.add_argument("--english-only", action="store_true", help="do not build the Bahasa Melayu translations (an English-only demo)")
    args = ap.parse_args(argv)
    settings = load_settings()
    store = open_store(settings)
    evidence, book = evidence_for(settings), citations_for(settings)
    built = library.seed(
        store,
        kit_dist=settings.kit_dist_dir,
        public_origin=settings.public_origin,
        book=book,
        evidence=evidence,
        interaction_seconds=args.interaction_seconds or settings.verify_interaction_seconds,
        translations_dir=None if args.english_only else OVERLAYS,
    )
    verified = sum(1 for _, env in built if env.label == "kit-verified")
    translated = sum(len(store.translations_of(env.env_id)) for _, env in built)
    print(f"{len(built)} Environments built, stored and indexed by topic ({verified} kit-verified), {translated} Bahasa Melayu translations linked, in {settings.data_dir / 'environments.db'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
