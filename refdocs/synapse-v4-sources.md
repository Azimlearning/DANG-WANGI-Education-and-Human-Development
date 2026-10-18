# Synapse v4: Sources & References

> Raw research and external dependencies. The PRD is the *decided* view; this file is the *considered* view, including things that were looked at and rejected, which is often the more useful half.
> Record a source when it's chosen, and again when it's rejected. "We already tried that and here's why it didn't fit" is the single most expensive fact to re-derive.

Last updated: 2026-10-16

---

## Founding context documents

| File | What it is |
|---|---|
| [brainstorm-2026-10-16.md](brainstorm-2026-10-16.md) | The direction brainstorm: what the earlier builds give, the outside field, the data-first design, and Amendment A1 which records the interview that made raw HTML primary and introduced Mark 3. Historical: the PRD wins where they differ |

---

## Prior builds (own work; port with provenance, CLAUDE.md rule 5)

| Build | Repo and location | Commit or date | What it gives v4 |
|---|---|---|---|
| Synapse v1 | `Azimlearning/GenUI-Education`, `Synapse/` | 2026-07-01 | Sourced misconception KB (`backend/app/knowledge/`), strategy names, learner-model idea, evaluation plan (10 to 15 students, two-tier diagnostic, pre, post, delayed post) |
| Synapse v2 | same repo, `synapse-v2/` | 2026-07-15 | The `when` principle (answers computed from live state), pins, the expression-grammar idea |
| Synapse v3 | same repo, `Synapse-V3/` | 2026-07-16 to 2026-09 | Raw-HTML pipeline: planner, generator prompt v8, post-processor, verifier, delivery gate, render harness, evals, router distillation, 53-topic KSSM taxonomy (`ml/router-distill/kssm_topics.py` v3), 1,971 ingested passages (not copied), brand and Axi mascot |
| Arcana v2 | `Azimlearning/Arcana-v2` (public) | `21c6dcf54e8c38b0e7e4556e478acd4d42e82bd7`, 2026-10-16 | Lifecycle table, contract, verifier and mint, delivery gate, mutation harness, fixed template host, spend ledger and cap, verbatim quotes, mastery rule, evaluation discipline, doc system |

Measured facts carried from Arcana v2 (its own evidence files): a 120-defect planted suite refused by the named stage; a live generator accepted 2 of 8 first attempts, then 6 of 8 after one prompt revision, at $0.0458 for 15 paid calls; graph retrieval not shown to beat flat (pooled nDCG@10 difference -0.001, p = 0.69, 38 questions).

---

## External code & libraries

| Name | What it does for us | Link | License | Status |
|---|---|---|---|---|
| FastAPI | API framework | https://fastapi.tiangolo.com | MIT | Chosen (D-05); docs to be read at P0 task 3 |
| Pydantic v2 | Strict wire models | https://docs.pydantic.dev | MIT | Chosen |
| uv | Python project and environment manager | https://docs.astral.sh/uv | MIT or Apache-2.0 | Chosen; installed |
| Next.js, React, Tailwind | Web shell | https://nextjs.org | MIT | Chosen; docs to be read at P0 task 8 |
| pnpm | JS workspace manager | https://pnpm.io | MIT | Chosen; installed |
| esbuild | Bundle the Kit | https://esbuild.github.io | MIT | Chosen; docs to be read at P0 task 4 |
| Vitest | Kit and web tests | https://vitest.dev | MIT | Chosen |
| Playwright | Headless render and verification harness | https://playwright.dev | Apache-2.0 | Chosen; **not installed**; browsers add a download |
| KaTeX | Equation rendering inside environments | https://katex.org | MIT | Vendored in v3; carry over at P1 |
| p5, matter-js, three, Chart.js, d3 | Optional vendored drawing libraries (at most one per environment, per v3) | see v3 `vendor/CHECKSUMS.txt` | LGPL-2.1 (p5), MIT, MIT, MIT, ISC (recalled, verify before shipping) | Carry over only if the Kit does not replace them |
| json-render (Vercel Labs) | A catalog-plus-flat-spec renderer | https://github.com/vercel-labs/json-render | Apache-2.0 (secondary sources) | Candidate for a P1 spike only; not adopted |
| `@openai/apps-sdk-ui` | OpenAI's design-system components | https://developers.openai.com/apps-sdk | not checked | Reference for the Kit's ui kind only |

---

## APIs & services

| Service | Used for | Pricing model | Auth / key location | Status |
|---|---|---|---|---|
| Anthropic API | Router fallback, planner, generator, verifier, explainer | Per token. Arcana v2's cost audit (2026-10-07) lists Haiku 4.5 at $1 and $5, Sonnet 5.5 at $2 and $10, Opus 5.5 at $4 and $20 per million input and output tokens. Re-check before the first paid run | `ANTHROPIC_API_KEY` in `.env`, server side only | Chosen. Fakes by default (D-08) |
| OpenRouter | Optional fallback route | Per token | `OPENROUTER_API_KEY` | Optional. Arcana v2 used it when Anthropic credit ran out |
| Dense embeddings provider | Library lookup by meaning | Per token | not chosen | Deferred (D-12, A-9) |

Keys live in `.env` (git-ignored) and are read server-side only. Never commit a key; never expose one to a client bundle.

---

## Reference material

**OpenAI (read 2026-10-16):**
- [UI guidelines](https://developers.openai.com/apps-sdk/concepts/ui-guidelines): inline card, carousel, fullscreen, picture-in-picture; at most two actions; no nested scrolling.
- [UX principles](https://developers.openai.com/apps-sdk/concepts/ux-principles): use UI only when it helps; complete the path; explain limits.
- [Add UI to your MCP server](https://developers.openai.com/apps-sdk/plan/components): `ui://` resources, JSON-RPC over `postMessage`, widget state split into model-visible and UI-only, CSP declared and compared with behaviour at review.
- [ChatKit widgets](https://developers.openai.com/api/docs/guides/chatkit-widgets): `WidgetRoot` of typed nodes; actions to the backend; no chart node documented.
- ChatGPT interactive math and science visuals, launched 2026-03-10, 70+ topics (press only: [Campus Technology](https://campustechnology.com/articles/2026/03/10/openai-adds-interactive-math-and-science-learning-tools-to-chatgpt.aspx), [Engadget](https://www.engadget.com/ai/chatgpt-will-now-generate-interactive-visuals-to-help-you-with-math-and-science-concepts-170000520.html)). OpenAI's own post returned 403.

**Google and others:**
- [The future of practice](https://research.google/blog/the-future-of-practice-enabling-teachers-to-create-learning-interactives-with-generative-ui/) (2026-09-17) and [arXiv 2609.20738](https://arxiv.org/abs/2609.20738) (abstract only): teacher-vetted learning interactives, solvability checks with extreme values.
- [MAIC-UI, arXiv 2604.25806](https://arxiv.org/abs/2604.25806): generate-verify-optimise pipeline; diff-based incremental editing.
- [The Missing Layer, arXiv 2606.15902](https://arxiv.org/abs/2606.15902): the position that runtime GenUI cannot be verified at scale.
- [PDE-grounded intent verification, arXiv 2605.09360](https://arxiv.org/abs/2605.09360): execution-only repair left 39 to 40 percent of cases runnable but wrong.
- [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) and the [ext-apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx).
- [Vercel json-render coverage (InfoQ)](https://www.infoq.com/news/2026/03/vercel-json-render/) (secondary).

**Not read:** OpenAI's interactive-learning announcement (403), json-render's repository, the full text of arXiv 2609.20738, any KSSM textbook in the session that wrote this scaffold.

---

## Considered and rejected

| Option | Why it looked good | Why it lost | Recorded in |
|---|---|---|---|
| Data-first environments (a declarative spec rendered by a fixed Runtime; raw HTML only at authoring time) | Strongest verification and smallest code-execution surface | The owner chose raw HTML for adaptivity and generativity. Its good parts survive as the Instantiate lane, the Kit and the oracle ladder | D-02, brainstorm A1 |
| TypeScript end to end | One evaluator shared by verifier and browser | The raw-HTML pipeline, lifecycle and ML assets are Python; a rewrite is the slow path | D-05 |
| GraphRAG over the KSSM corpus | Fashionable; was the v1 and v2 core | Measured no gain in Arcana v2 (p = 0.69) and the corpus is small and curated | D-12 |
| A trained re-ranker | Cheap quality lift | Arcana v2 measured it not helping | D-12 |
| World-model environments (Genie class) | Rich and novel | Unverifiable; no published education study | PRD section 5 |
| Pyodide or WebAssembly Python for kernels | Python in the browser | Heavy, large attack surface; Arcana v2 rejected it too | PRD section 5 |
| One agent per capability | Clear names | Violates the trust-boundary rule for an agent (Arcana v2 D-30) | PRD section 3 |
| Accounts, payments, teacher dashboards | Retention and revenue | Owner chose single-operator, no auth; devices and links cover the need | D-11 |

## Local tools added 2026-10-18 (Step 2, textbook corpus; not part of the cloud or CI install)

| Tool | Version | Licence | Use |
|---|---|---|---|
| pypdf | 6.21.1 | BSD-3-Clause | Reads the text layer of the owner's textbook PDFs (`api/evidence/ingest.py`). Not OCR. Docs: pypdf.readthedocs.io, "Extract text from a PDF" |
| fonttools | 4.67.0 | MIT | Optional pypdf dependency that decodes CFF Type1 font encodings; without it pypdf warned and could garble characters |

Both are in the `local` dependency group (`uv run --group local ...`). An OCR tool for the five image-only Chemistry experiment books is not chosen yet.
