# Research: ChatGPT's Intelligent UI, the conflict with the Apps SDK note, and a static analysis of a public look-alike

> Done 2026-10-21 at the owner's request: "do further research on the conflict and update on findings", after a first request for a full reverse-engineering pass on the system. **Evidence quality is mixed and each finding below says which kind supports it.** The owner has no GPT-6 access, so nothing here was observed from a live Intelligent UI session. The only artefacts analysed locally are two public npm packages from a third-party vendor (Thesys, OpenUI Lang 1.0.1), which are a look-alike, **not** OpenAI's code. Nothing in this file says how OpenAI's renderer is built beyond what OpenAI and the press state.

## 1. The conflict, stated

`2026-10-16-chatgpt-ui-research.md` says: "It does not let the model write the UI", and D-23 (DECISIONS.md) rests its "Why" on that: "ChatGPT's reliability comes from the model supplying data to a developer-authored template".

OpenAI's own release notes of 2026-10-07 describe a different, first-party feature: "ChatGPT can now combine text, visuals, and interactive elements to fit your question ... It can choose the format automatically." There the model chooses and composes the interface itself.

**Resolution.** Both are true of different systems. The 2026-10-16 note described the **Apps SDK** (third-party developers ship widgets; the model only calls tools). It never covered **Intelligent UI** (first-party, model-composed, GPT-6). The note was written nine days after Intelligent UI launched and searched only for the Apps SDK. The sentence is correct for the Apps SDK and wrong as a statement about ChatGPT in general. D-23's decision is not overturned (section 5).

## 2. Three different things, kept apart

| | Apps SDK widgets | Interactive learning visuals | Intelligent UI |
|---|---|---|---|
| Launched | 2025 (SDK), MCP Apps standard 2026-01 | 2026-03-10 | 2026-10-07 with GPT-6 |
| Who authors the UI | A developer, ahead of time | Not stated by OpenAI | The model composes it per answer, from a platform catalogue (as reported) |
| Scope | Any third-party app | 70 plus named math and science concepts | Any question, including "text is best" |
| Availability | Apps in ChatGPT | All logged-in users, all plans | Instant to Extra High reasoning; **not** the Pro reasoning option (GPT-6 Astra); Work and Codex unchanged |
| Primary source | developers.openai.com docs (not re-read this session) | OpenAI post, read in full | OpenAI release notes, read in full |

Whether the learning visuals and Intelligent UI share a renderer is **not stated anywhere I found**.

## 3. Findings ledger

Evidence types: **PRIMARY** (OpenAI's own page, fetched this session), **PRESS** (a named outlet reporting OpenAI), **VENDOR-RE** (a competitor's reverse engineering, with a commercial interest, unverified by OpenAI), **LOCAL-STATIC** (analysed here with REA, nothing executed).

| # | Finding | Type | Source | Confidence |
|---|---|---|---|---|
| F1 | GPT-6 with Intelligent UI launched 2026-10-07 for Plus, Pro, Business, Enterprise; Free and Go from 2026-10-08 (GPT-6 Sol for paid, Luna for Free and Go) | PRIMARY | help.openai.com release notes | High |
| F2 | It combines text, visuals and interactive elements; examples are calculators, bill splitters, games, side-by-side comparisons, diagrams; it picks the format automatically and still answers in plain text when that is best | PRIMARY | release notes | High |
| F3 | Not supported by the Pro reasoning option (GPT-6 Astra); not applied to Work or Codex | PRIMARY | release notes | High |
| F4 | The learning visuals cover 70 plus core concepts (examples named: Ohm's law, Hooke's law, PV=nRT, Coulomb's law, lens equation, kinetic energy), trigger when the user asks about one of them, let the user change variables and formulas, and run on all plans | PRIMARY | OpenAI post 2026-03-10 | High |
| F5 | "Underneath it all is a library of native components and a compiler that streams the interface progressively while GPT-6 is still generating it" | PRESS (attributed to OpenAI) | Android Authority | Medium: OpenAI's release notes do not repeat it |
| F6 | Users can ask for fewer visuals; OpenAI did not explain how it decides when to generate one | PRESS | TechCrunch, Android Authority | Medium |
| F7 | Intelligent UI is separate from the Apps SDK; no standalone developer API for it was documented as of 2026-10-08 | PRESS (two secondary outlets) | Scalevise and another guide | Low to medium |
| F8 | The model emits a markup language called "DIL" (Markdown, JSX-like catalogue tags, JS state statements); the server compiles it to a JS program plus JSON; about 70 catalogue components; an `AppBlock` escape hatch runs model-written HTML/CSS/JS in a separate-origin iframe; the program runs in a sandboxed iframe plus Web Worker with network, timers and dynamic code stripped; sliders run with zero model calls; outward actions go through `issueNewTurn`, which sends a new user message built from UI state | VENDOR-RE | Thesys write-up on openui.com | **Unverified.** Author's firm sells a competing product. Treat as a hypothesis to test, not a fact |
| F9 | No public source describes any check that a generated science widget is correct against a textbook or independent reference | Absence in sources searched | n/a | Low (absence of evidence) |

## 4. Local static analysis of the public look-alike (REA)

**Why this target.** The owner picked "open-source proxy" because the live session was unavailable. It shows how a catalogue-plus-streaming-parser design is built in practice. It cannot confirm anything about OpenAI.

**What was analysed.** `@openuidev/lang-core@1.0.1` and `@openuidev/react-lang@1.0.1` (MIT, Thesys). Downloaded with `npm pack --ignore-scripts` into a scratch directory outside the repo, extracted with `tar`, and analysed with REA 6.7.0 (`analyze_javascript_application`, `inspect_analysis_view`, `trace_application_feature`). Nothing was installed or executed. Extracted-directory digests: lang-core `5ba7582bb9d1b58a27c76ca65258f74e1dc616f5daf20341fd2201d00d980bf7`, react-lang `115e055b1d26836ff05da1c657ef9ede5fc4d4f80c24879dae6b5acc0df5e25a`. Evidence ids: lang-core parent `ev_957d83ca600c3493acf913c92af905f1372b4b00de018d75518c92ec60709204`, react-lang parent `ev_8e704f28bbb47c3c3e960569850316009cc8760b99fe62b261d73c9d15206629`, endpoint facts view `ev_f41d03386cf1d47108a9c8a790ef9a234e5c355ffcff69854d9a9355efe9afe8`.

**Observed (LOCAL-STATIC, or read directly from the package files):**

1. **The language is not "DIL".** OpenUI Lang, per the package README, is a list of named statements, `name = Component(args)`, with a `root` and forward references (`root = Stack([header, content])`). That is a different syntax from the Markdown plus JSX-like tags plus JS statements that F8 attributes to ChatGPT. It is a relative in design, not the same format.
2. **The catalogue is both the prompt and the validator.** A library is built from component definitions; `toJSONSchema()` feeds the parser and `generateSystemPrompt({library})` builds the model's instructions from the same spec (README).
3. **Streaming is by re-parsing the whole text.** The streaming parser's `set(fullText)` takes the full text so far; the parse result carries `incomplete`, `unresolved` (references not yet defined, dropped as null) and `orphaned` (unreachable) (README and `dist/index.d.mts` lines 339 to 341). I did not trace the implementation to confirm it re-parses from scratch each time. This is the documented behaviour.
4. **Edits merge by statement name** (`mergeStatements(original, patch)`), and the runtime has reactive `$variables`, and Query and Mutation calls through MCP tools (README).
5. **No sandbox machinery.** A pattern search of both packages' `dist` files for `iframe`, `sandbox`, `srcdoc`, `Worker(`, `dangerouslySetInnerHTML`, `new Function`, `eval(` and `postMessage` found no matches in `react-lang` and only two lines in `lang-core` (`isBrowserWorker`, a runtime sniff used by the telemetry code). OpenUI Lang is declarative only: it has no open-ended escape hatch and relies on the host app for isolation. A pattern search is not proof of absence.
6. **Install-time telemetry.** `lang-core` runs a `postinstall` script (`postinstall.cjs`, then `dist/postinstall.cjs`) that calls `runInstallTelemetry()`. REA flagged a network request in `dist/postinstall.cjs` lines 189 to 201 whose target is an unresolved expression (`postHog.captureUrl`). Reading the code: it POSTs JSON to PostHog with an `api_key`, an event name, a `distinct_id` and properties; it runs `git -C <root> config --get remote.origin.url` with a 1 second timeout; it checks for Docker; and it stores a random id and salt in a state file. The README documents opt-outs (`OPENUI_TELEMETRY_DISABLED=1`, `DO_NOT_TRACK=1`) and says runtime telemetry is opt-in. **I read lines 120 to 209 only; the construction of the payload properties was not reviewed.** The exact fields sent are therefore not verified here.

**Limits of the REA result.** Both graphs are `partial` with semantic coverage `unknown` (12144 semantic unknowns for lang-core, 3602 for react-lang), as is normal for bundled output. A trace on the literal `fetch` returned no match, which REA itself says is not evidence of absence. REA reported 0 workers, 0 browser windows and no Electron surface for both packages. Static analysis does not show runtime behaviour.

## 5. What this means for Synapse

**D-23 stands; its premise is narrowed.** Both systems, the Apps SDK and Intelligent UI as reported, put a vetted, platform-owned catalogue between the model and the pixels, and keep interaction local so it costs no tokens (F5, F8, the bridge in D-23). That is the shape D-23 chose. What changes is the evidence: a first-party, model-composed, progressively streamed catalogue UI now has OpenAI as a precedent (F2, F5), so "the model supplies data to a developer's template" is no longer the whole picture of ChatGPT.

Specific points:

- **Compose lane.** F2 and F5 support Synapse's Compose lane (model chooses from the Kit) as an industry direction, not only a safety choice.
- **Free lane.** The reported `AppBlock` (F8, unverified) matches Synapse's Free lane: an open-ended escape hatch that sits outside the catalogue. Synapse's version is stricter by constraint: exact sandbox, verifier, lane label, gap log.
- **Verification is the gap.** F9: no source describes a correctness check on generated science widgets. That is Synapse's differentiator, but it is a statement about the public record, not about what OpenAI does internally.
- **Streaming.** Progressive streaming (F5) and re-parse-the-whole-text (item 3) are alternatives to D-23's loading skeleton; D-23 chose the skeleton so the student sees the Peek shell before verification finishes. Not changed here.
- **Do not adopt the OpenUI packages as they are.** They add install-time network egress and a git-remote read (item 6), which sits badly with hard constraint 13 (public-repo hygiene) and the project's no-surprises posture. If they are ever evaluated, install with scripts disabled and `DO_NOT_TRACK=1`, and review the payload first. This is a note, not a decision.

## 6. Unknowns, and what would close them

| Unknown | What would close it |
|---|---|
| Whether the learning visuals use the same renderer as Intelligent UI | A passive capture of "Explain how PV=nRT works" in a logged-in browser (any plan). REA's passive capture returns script sources and request shapes but drops raw response bodies, so the model's emitted text would have to be copied from DevTools by the owner |
| Whether DIL, `AppBlock`, the worker sandbox and `issueNewTurn` exist as F8 describes | A capture from an account with GPT-6 access. The owner has none |
| How ChatGPT decides to render a visual | Not observable from outside; one secondary source says the model was trained and graded for it |
| Whether any content check exists | OpenAI statement or a capture; none found |
| The exact fields in OpenUI's install telemetry | Read lines 1 to 119 of `dist/postinstall.cjs` and the shared module |

## Sources (accessed 2026-10-21)

- [ChatGPT release notes, OpenAI Help Center](https://help.openai.com/en/articles/6825453-chatgpt-release-notes) (PRIMARY, entry of 2026-10-07)
- [New ways to learn math and science in ChatGPT, OpenAI](https://openai.com/index/new-ways-to-learn-math-and-science-in-chatgpt/) (PRIMARY, 2026-03-10)
- [GPT-6 gives ChatGPT its biggest visual makeover yet, Android Authority](https://www.androidauthority.com/chatgpt-gpt-6-intelligent-ui-3720464/) (PRESS)
- [ChatGPT is getting a lot more visual, TechCrunch](https://techcrunch.com/2026/10/07/chatgpt-is-getting-a-lot-more-visual-with-the-launch-of-a-new-interface/) (PRESS, read through a fetch summary)
- [How ChatGPT's Intelligent UI works, OpenUI/Thesys](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works) (VENDOR-RE, read through a fetch summary)
- [GPT-6 Intelligent UI Brings Custom Interfaces to ChatGPT, Scalevise](https://scalevise.com/resources/gpt-6-intelligent-ui-chatgpt-custom-interfaces/) (PRESS, search summary only)
- `@openuidev/lang-core@1.0.1` and `@openuidev/react-lang@1.0.1` on npm (LOCAL-STATIC)
