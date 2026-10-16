# Execution: P4 Kit expansion and the nine-plus Environments (cloud scope)

> Plan: `refdocs/plans/2026-10-16-p4-kit-expansion.md`. Written after the build; this is the as-built record.

## As built

1. **Models** (`packages/kit/src/science/*.ts`): spec files with inputs, params, output, domain and citation; `model.ts` and `spec.ts` generate the wrapper, manifest entry (`inputs/params/output`, `useWhen`, `topics`) and registration suite from the spec. Wrappers use the spec's snake_case parameter names (a camelCase mismatch caused "not ready" pages and was fixed once, for all).
2. **References** (`api/verify/references.py`): independent Python formulas with `input_units`, `UNIT_SI` including volume units.
3. **Planted bugs**: 87 planted defects across the new models in `science/science.test.ts` (wrong constant, swapped operands, off-by-unit, clamp, sign). Each is refused by the registration suite.
4. **Plans** (`data/plans/*.json`): eleven golden plans (Physics F5: Hooke, Ohm, pressure depth; Biology F4: magnification, cell size; Biology F5: photosynthesis; Chemistry F4: mole, titration, dilution, rate; Chemistry F5: heat of neutralisation).
5. **Build and report**: `eval/environments/build.py` assembles every plan, verifies it in Chromium and delivers it through the gate, then writes `refdocs/evidence/2026-10-16-p4-environments.md` (11 verified, 3 Physics, 3 Biology, 5 Chemistry).
6. **Layout fixes found on the way**: graph/table overflowed at 360 px (hidden table, six-column table); fixed with a `div.syn-sr` wrapper and fixed table layout.

7. **Second batch (same day):** six more models, each with a spec, manifest entry, independent Python reference, 10 or 11 planted bugs, a golden Plan and an Environment: Physics `wave_speed` and `newton_second` (Form 4), Biology `cardiac_output` and `percent_change_mass` (Form 4), Chemistry `ph_from_h` and `gas_volume` (Form 4). The registration suite caught two weaknesses of mine while writing them (the pH references were all whole numbers and none went above pH 7, so a cap at 7 and rounding escaped; fixed with non-integer references). Plans for these are simulators of a law, not SPM practicals, so only the osmosis (potato) one is added to the experiment catalogue. The report now lists 17 Environments (Physics 5, Biology 5, Chemistry 7).

## Verify

`uv run python eval/environments/build.py` prints "11 Environments verified and delivered". `pnpm --filter kit test` (315 tests). `uv run pytest eval/environments -q`.

## Open

- The wording of every study note and task is the author's; check each against the textbook before any `reviewed` label.
- Ideas for further models (by measured gap): Physics half-life, parallel resistance, refraction; Biology logistic growth; Chemistry molarity, percentage yield.
