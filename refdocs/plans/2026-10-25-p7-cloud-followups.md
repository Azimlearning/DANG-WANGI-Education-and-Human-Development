# Plan: cloud follow-ups after the local session (known constants, CI, static gallery)

> Execution doc: `refdocs/execution/2026-10-25-p7-cloud-followups.md`. Items B5, B4, B9 and the "static gallery" route of `refdocs/guides/remaining_work.md`; roadmap workstreams W7 (constants), W6 (friendly citations, no Bahasa Melayu: the owner said to skip it on 2026-10-25) and W9 (CI). Written on a stale base and corrected after the owner's update: PLAN-018 and PLAN-019 were already taken by the bench work, so the constants check is PLAN-020.

## Why this exists

The owner asked the cloud session to carry on from `main` and keep going. After the local session, what is left that needs neither a paid call nor a person is small and specific:

1. **The live planner chose g = 10 where the textbook uses 9.81** (first paid run). Nothing in the plan checks knows a physical constant, so a wrong textbook value passes every layer and the Environment is internally consistent but disagrees with the book.
2. **There is no continuous integration.** The Linux path of the web smoke has not run since it was edited for Windows, and a suite of about 650 tests is run by hand.
3. **There is no way to show the work without a server.** The cheapest credible demo (remaining work, "cheapest route", step 2) is a static gallery of the verified Environments as offline files: no server, no model call, no abuse risk, no bill, and every page carries its provenance.

## What's already covered

| Need | Where |
|---|---|
| Plan checks with stable codes and a registry that cannot drift | `api/pipeline/plan_checks.py`, `api/pipeline/failchecks.py` (a test fails if a code is emitted but not listed, or listed but not emittable) |
| The offline single-file export, hash-checked, exact sandbox | `api/export.py` (D-32) |
| Building every Environment through the gate | `eval/environments/build.py` |

## Scope

**In:**
1. **PLAN-020, a table of well-known constants.** A small, hand-written table (gravitational field strength, speed of light, Avogadro's number, molar volume at room conditions and at STP, specific heat capacity of water) with the values the KSSM textbooks use and the spellings under which a Plan names them. A model parameter or constant whose name or id matches an entry and whose unit matches must carry an accepted value; otherwise the plan is refused with a hint naming the accepted values. Block, retry_plan.
2. **CI.** A GitHub Actions workflow that runs the Kit tests, web tests, codegen drift check, lint and types, the Python suite and the smoke on Linux.
3. **Friendly citations (B4).** The student sees a book title and a PDF page, not a file id. Derived from the document id's own words, so no wire-type change and no textbook content.
4. **A static gallery builder.** `eval/gallery/build.py` builds every Plan in `data/plans/` through the same path as `eval/environments/build.py`, exports each delivered block with `standalone_page`, and writes an `index.html` listing them with subject, form, label and what was checked. Output goes to a git-ignored folder. Nothing is rebuilt from a model.

**Out (and why):**
- B3 (Kit manifest citation text, `biology.cardiac_output`): a Kit change that relocks the Kit, and the honest text depends on the corpus, which is not in the cloud. Left for the local session.
- Publishing the gallery or any quotation: the owner has not answered A-8 (publication of short quotations). The gallery builder takes the label from what the local corpus proves; without a corpus every page says `model-checked`.
- Hosting, naming, licence: the owner's decisions (A5).

## Approach

- PLAN-020 is a pure function over the Plan and a constants table in `api/pipeline/constants.py`. It adds no Kit change: it reads the Plan only. The textbook is the authority for the values, so each entry names the source it was taken from (the textbook value as the Plans already use it, or the SI/IUPAC value) and says that a teacher has not reviewed the table.
- The gallery reuses `build()`'s steps by extracting the shared "plan to delivered block" loop rather than copying it.
- The workflow does not need secrets: fakes are the default, and the test suite refuses non-loopback connections.

## Risks and unknowns

- **Over-strict constants.** A Plan that legitimately uses g = 10 (a textbook that rounds) would be refused. Mitigation: accepted values are a list per entry, and the check refuses only a value outside it; confidence medium, measured by the existing golden Plans (all must still pass).
- **CI cannot be proved from here.** The workflow file can be linted and its commands run locally, but the first real run is on GitHub. Confidence that it runs green first time: medium. This is said in the changelog.
- **Playwright's browser in CI.** The runner installs Chromium itself (`playwright install --with-deps chromium`). Not proved here because this container has a different Chromium build.

## Definition of done

- `uv run pytest` passes with new PLAN-020 tests, including that every committed Plan still passes the checks and that g = 10 is refused with a hint naming 9.81.
- The fail-check registry test passes with PLAN-020 listed.
- `uv run python eval/gallery/build.py` writes one HTML file per Plan and an index; each file's two hashes are checked by a test that opens one in Chromium and sees the Environment run; the index is a static page with no external requests.
- `.github/workflows/ci.yml` exists, and its commands were run locally in order.
- CHANGELOG, STATUS, `remaining_work.md` and `file_map.md` reflect all of the above.
