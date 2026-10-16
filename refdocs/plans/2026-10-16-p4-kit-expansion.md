# Plan: P4 Kit expansion and the nine-plus Environments (cloud scope)

> Phase P4 of `refdocs/synapse-v4-PRD.md` section 6, decision D-19. Execution doc: `refdocs/execution/2026-10-16-p4-kit-expansion.md`. **Written after the build** (a deviation from CLAUDE.md rule 2, logged in the changelog); it records what was planned and done so the next session does not rediscover it.

## Why this exists

D-19 sets the end state: at least nine verified Environments, three per subject (Physics, Biology, Chemistry), each tied to a catalogued KSSM experiment or topic. P1 left three Physics models. Biology and Chemistry had none.

## Scope

**In (cloud):**
1. Eight new science micro-models, each with a written precondition, units and domain, a citation field (UNVERIFIED until the corpus is loaded), an independent hand-written Python reference, properties, and a registration suite that refuses every planted defect: Biology `sa_to_v_cube`, `magnification`, `photosynthesis_net`; Chemistry `moles_from_mass`, `titration_concentration`, `dilution`, `heat_energy`, `average_rate`.
2. One hand-written golden Plan per Environment (eleven in all), assembled by the deterministic assembler and verified in real Chromium.
3. Manifest `useWhen`, domain and `topics` for each model so the planner's kit pack finds it (topic-aware retrieval).
4. A breadth set and a generated report listing what the project can make today.

**Out (and why):**
- Wording, units and scope confirmed against textbook pages: needs the local corpus (A-8). Every Environment stays `model-checked` with an UNVERIFIED citation.
- Matching each to the owner's experiment documents: the owner holds them; the catalogue says `confirmed_by_person: false` until then.
- More models than the minimum: later, from measured gaps (D-19 says the Kit grows from them).

## Definition of done

- Eleven Environments verified and delivered through the gate, three or more per subject, listed in `refdocs/evidence/2026-10-16-p4-environments.md` (generated; a test refuses stale).
- Every new model refuses all its planted bugs and its reference agrees with the TypeScript on a grid.
- The photosynthesis curve says on the page that it is a stylised teaching curve.

## Risks

- The formulas are the author's arithmetic; a shared misconception between spec and reference would pass every check. Mitigation: the textbook proof at P2 (local), and `reviewed` by a person.
