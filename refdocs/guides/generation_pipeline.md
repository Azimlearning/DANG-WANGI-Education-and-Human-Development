# How a question becomes a lab: the Synapse v4 generation pipeline

> Written 2026-10-29 for the owner, who asked how a prompt goes through "the templates and the prebuilt components", and what is in `data/` and the component folders. It describes the pipeline after W18 and W19 (D-72 to D-78). The code is the authority: `api/pipeline/run.py` is the pipeline from top to bottom.

## The idea in one paragraph

A model never writes the lab's code in the main path. It writes a **Plan**: a small piece of JSON data that says which controls the student gets, which science models compute the numbers, what is drawn and which words go round it. Synapse then **assembles** the page from a fixed **template** (the skeleton) and **prebuilt, audited components** (the Kit), and a real browser **verifies** it before any student sees it. Because the code comes from the Kit and not from the model, every number on the page can be traced back to a checked science model and a textbook page. The **Free lane** is the exception: there a model writes a whole page, which is checked less and labelled so.

## The three lanes

| Lane | What happens | Cost | Label it can earn |
|---|---|---|---|
| **Instantiate** (the library) | A stored lab built earlier from a hand-written Plan is served at once | Free | Kit verified |
| **Compose** | The model writes a Plan; Synapse assembles it from the Kit | About $0.03 to $0.08 (W16 and W18 paid runs) | Kit verified (with a textbook citation) or Model checked |
| **Free** | The model writes the whole page; a second model reads it; the browser checks it | About $0.10 to $0.20 (an estimate: not yet measured on a paid run) | Model checked at most, marked "written whole by a model" |

Which lane leads after the Plan is a setting, `LANE_PREFERENCE` (D-76):

- `balanced` (the default): Free leads when the planner says the Kit only **partly fits** the question (`"fit": "partial"`), or when the Plan would draw **no picture** (no scene, no bench, only sliders and a graph). Otherwise Compose.
- `free`: Free leads for every question that is not in the library.
- `kit`: Compose always; Free only when the Kit cannot take the question at all.

Whenever Free leads and its page fails a check, the Compose Plan already made for the question is the **fallback**, so a student never gets less than before.

## The stages, in order

Each stage is a real step in `api/pipeline/run.py`, and each one sends a stage event that drives the progress bar and the "See how it's built" log in the web page.

1. **Intake.** Refuse obvious prompt injection.
2. **Library** (`api/pipeline/library.py`). If the question was asked before, or the local topic model recognises the topic with enough confidence, serve the stored lab whose title and goal best match the question. No model call, no money.
3. **Route** (`api/routing/router.py`). Decide the KSSM topic, the pattern (simulation or virtual experiment) and the subject. A small local model first, a cheap model call only if it is unsure.
4. **Explain** (`api/prompts/explainer.v1.md`). The written answer streams into the chat first, so the student reads while the lab is built.
5. **Plan** (`api/prompts/planner.v9.md`). The planner model gets the question, the routing, the **Kit pack** (the components and science models allowed for this topic, from the Kit manifest), the **apparatus catalogue**, a worked example Plan, and the JSON schema (`api/prompts/schemas/plan.schema.json`). It replies with a Plan, including `fit`.
6. **Plan checks** (`api/pipeline/plan_checks.py`). Twenty-three rules (`PLAN-001` to `PLAN-023`, registered in `api/pipeline/failchecks.py`): every model exists, units match, ranges stay in each model's domain, a picture's scale fits what the model can reach, a planets control runs from Mercury to Neptune. A failed check is sent back once with the problem written out; a second failure goes to the Free lane or the written answer.
7. **Lane** (W19). The `fit` and the Plan's picture decide whether Free leads (see above).
8. **Assemble** (`api/pipeline/assemble.py`). The Plan's data is written into the **template** `api/pipeline/skeletons/simulation.html` or `virtual_experiment.html`. The template is a plain page with numbered slots (`/*SLOT:controls*/`, `/*SLOT:models*/`, `/*SLOT:scene*/` and so on); the assembler fills each slot with calls to Kit components (`Synapse.planetPicker(env, {...})`, `Synapse.planetGravity({planet: ...})`). The page loads the Kit from `/vendor/kit/<version>/core.js`, never from the internet.
9. **Fill** (optional, `api/prompts/fill.v1.md`). A Plan may ask for up to three short custom slots of model-written code; they are checked hardest and dropped first if anything fails.
10. **Verify** (`api/verify/`). The page runs in headless Chromium at 480 px wide with reduced motion. Layer by layer: a static scan (`scan.py`), post-processing (`postprocess.py`), the Kit's own audit of every number and drawing (`provenance.py`), every control swept across its range, every handle, mass, valve and dial dragged with a mouse and a finger (`render.py`), each number recomputed by an independent Python reference (`references.py`), and accessibility. Any failure refuses the page.
11. **Ground** (`api/pipeline/grounding.py`). The Plan's `citation_ids` are looked up in `data/citations/pointers.json` and each quotation is proved word for word against the textbook corpus. Only then is the label **Kit verified**.
12. **Mint, store and deliver** (`api/verify/mint.py`, `store.py`). The verified page is hashed, stored and sent. The browser re-hashes it before showing it, in a frame that can run scripts and do nothing else.

## What is the pipeline and what is not

The pipeline is the path from a question to a verified lab: stages 1 to 12 above. Its heart is **not** in `data/` or `web/components/`. It is in `api/pipeline/` (`run.py`, `plan.py`, `plan_checks.py`, `assemble.py`), `api/verify/`, the templates in `api/pipeline/skeletons/`, the prompts in `api/prompts/` and the Kit in `packages/kit/src/`. To follow how a lab is made, read `api/pipeline/run.py` top to bottom; treat `data/` as its inputs and outputs and `web/components/` as its display.

Much of `data/` and `web/components/` sits **beside** the pipeline, not on it:

- **Teaching extras** that arrive in the chat after the lab: misconceptions, probes, exam items, the lab report. Separate features (W5a to W5c).
- **Tests and evaluations** that check the pipeline but never run inside it: fixtures, hostile cases, L4 cases, golden-run stores.
- **The app shell**: the top bar, side rail, question box, mascot. Ordinary chat interface.
- **Clutter**: old copies of the store.

## Where things live

### Code folders

| Folder | What it holds | Changed by |
|---|---|---|
| `packages/kit/src/` | **The prebuilt components** (the Kit): controls (`slider.ts`, `mass_hanger.ts`, `valve.ts`, `dial.ts`, `planets.ts`), drawings (`scene.ts` spring, `orbit_scene.ts`, `titration_scene.ts`, `fermentation_scene.ts`, `apparatus.ts` with 26 bench parts in `apparatus_catalogue.ts`), `graph.ts`, `readout.ts`, `table.ts`, and teaching parts (hints, predict, concept check). Every part registers what it drew so the audit can check it. | Engineers, with tests and a registration suite |
| `packages/kit/src/science/` | **The science micro-models**: one file per law (`hookes.ts`, `ohm.ts`, `planet_gravity.ts`, `weight.ts`, ...), each with units, domain, hand-worked reference values and properties, and at least eight planted bugs it must refuse (`science.test.ts`). | Engineers, with a textbook citation |
| `packages/kit/dist/<version>/` | The built Kit (`core.js`) and its **manifest** (`manifest.json`): the catalogue the planner is shown. Built by `pnpm --filter @synapse/kit build`. | The build |
| `api/pipeline/skeletons/` | **The templates**: the two page skeletons with slots. | Engineers |
| `api/prompts/` | **The prompt packs**, one file per version (`planner.v9.md`, `free.v4.md`, ...). The highest version is used; a change is a new file. | Engineers, with an eval note |
| `packages/schema/` | The wire types between the API and the web page (generated into Python with `pnpm codegen`). | Engineers |
| `web/` | The chat shell, the lab bench, the progress bar, the build log and the code view. Components are listed below. | Engineers |

### `data/`, by role

`data/` mixes four kinds of thing. Only the first two are the pipeline.

#### 1. Inputs the pipeline reads

| File | Stage | What it is |
|---|---|---|
| `kssm_topics.json` | Route (3) | The KSSM topic list the router chooses from |
| `models/router/` | Library (2), Route (3) | The small local topic model (training splits, metrics, audit) that saves a paid call when it is confident |
| `plans/*.json` | Library (2) | **Hand-written Plans**: 31 labs (`physics-f4-planet_gravity.json` is the planets bench). Built into stored labs by `uv run python -m api.library_seed --english-only`. The source of the Instantiate lane. |
| `i18n/ms/` | Library (2) | Bahasa Melayu overlays for the library Plans |
| `citations/pointers.json` | Ground (11) | Where each fact is in which textbook (book, page, what it says). No textbook text: the quotations live with the corpus, outside the repository. |

#### 2. Outputs the pipeline writes

| File | What it records |
|---|---|
| `environments.db` | **The store** of verified labs (the library and every lab made for a question). Delivery reads from it. Rebuilt by the seed. |
| `ledger.db` | Every paid call and its cost; the monthly cap is enforced from it. |
| `traces.jsonl` | One line per question: each stage, its time, tokens and cost. Read it to debug a run. |
| `kit_gaps.jsonl` | One line each time the Kit could not take a question (for example `plan_failed:PLAN-001`, ending as text only). The to-do list for new Kit parts (hard constraint 3). |

#### 3. Beside the pipeline: teaching extras

Read by `api/models/` and `api/evidence/`, shown after the lab.

| File | What it is | Shown by |
|---|---|---|
| `misconceptions.json` | Five seed misconceptions ported from Synapse v1 | `ProbeCard` (through its probe) |
| `probes.json` | One follow-up question per misconception | `ProbeCard` |
| `exam_items.json` | Structured exam questions with keyword marking points | `ExamCard` |
| `experiments/catalogue.json` | The experiment catalogue (aim, models, Plan id) | `LabReport` and the evidence pages |

#### 4. Beside the pipeline: tests and evaluations

The running app never reads these.

| File | Used by |
|---|---|
| `fixtures/envs/reference-*.html` and `.plan.json` | The verifier's own tests and the planted-defect suite (L6): known-good pages with the Plan that made each, plus one Free-lane sample (`free-pressure.html`) |
| `hostile/hostile.json` | `eval/hostile/run.py`: attack pages and questions; each must be blocked by two independent layers |
| `l4/cases.json` and `cases.sha256` | `eval/l4/`: every library Plan with one fact changed (a size flipped, a unit swapped); the checks must refuse each change and accept the original. The hash pins the set (hard constraint 9). |
| `store/golden-live-*.db` | Stores kept from the paid golden-set runs (`eval/golden/live.py`), as evidence |

**Clutter.** Every `environments.*.db` other than `environments.db` itself (`pre-w16`, `stale3-w18`, `partial2-w16` and so on) is a copy taken before a re-seed. Nothing reads them; they can be deleted.

### `web/components/`, by purpose

Only the second and third groups show the pipeline's work. `EnvironmentFrame` is the one that matters most: it is the pipeline's last check, in the browser. The `*.test.tsx` files are their Vitest tests.

| Group | Components | Role |
|---|---|---|
| App shell (not the pipeline) | `TopBar`, `SideRail`, `Composer`, `Mascot` | Logo and theme, quick starts and opened labs, the question box (where a question enters, but nothing is generated there), Axi |
| The pipeline in progress | `ProgressStages`, `PeekSkeleton`, `BuildLog`, `MessageList` | The progress bar driven by real stage events; the draft card drawn from a checked Plan (never code); "See how it's built"; the chat with the streamed explanation (stage 4) |
| The pipeline's result | `EnvironmentFrame`, `LabBench`, `LabFrame`, `Peek`, `Stage` | `EnvironmentFrame` re-hashes the HTML against the verified hash and only then runs it in the `allow-scripts` sandbox (hard constraint 1). The others wrap it: the wide-screen column, the bordered lab frame, the inline phone card, full screen and Present mode. |
| Honesty about the result | `Badges`, `Provenance`, `DemoLabNote`, `DegradedCard` | The trust label and lane; the source, what was checked and its limits; a note while the server runs the fake model; the plain card when no lab was made |
| Teaching extras (not the pipeline) | `ProbeCard`, `ExamCard`, `LabReport`, `ProgressPanel`, `ShareButton` | The misconception probe, the exam mirror, the student's lab write-up, concept-check progress on this device, copying a lab's link |

## What changed in W18 and W19

- **Hands, not sliders.** Every graph's point can be dragged; the cannonball's launch arrow can be dragged; the planets have a test mass you carry between them; bench grips and masses already could. A control that has any of these keeps its card (its name and value) and hides its bar until it has keyboard focus.
- **New components:** `planetPicker` (the eight planets as a control), and the science models `planetGravity` (g = G M / R squared for each planet) and `weight` (W = m g).
- **Chained models:** a Plan may feed one model's output into another (gravity into weight into a spring balance), checked end to end.
- **Honest fit and a Free-leaning pipeline:** the planner says when the Kit only partly fits, and that question goes to the Free lane first, with the Kit lab as the fallback.
- **See how it's built:** the web page shows each real stage in a log while the lab is made, and the page's exact code once it has passed its checks (never before: hard constraint 1).
