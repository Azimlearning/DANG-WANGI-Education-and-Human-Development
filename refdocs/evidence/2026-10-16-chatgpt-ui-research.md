# Research: how ChatGPT's apps UI works, and what it means for the Mark 3 pipeline

> Done 2026-10-16 for the owner's request to research "OpenAI ChatGPT intelligent UI" and use it to improve the Mark 3 pipeline. **Evidence quality: search summaries only.** The container could not fetch web pages directly (DNS failure through the proxy), so OpenAI's own documentation was seen only as search snippets and summaries, and many details come from third-party guides. Each finding below says which kind of source supports it. Nothing here was read from a primary page in full. Re-read the primary pages locally before relying on an exact field name or rule (listed at the end).

> **Scope correction (2026-10-21).** This note describes the **Apps SDK** only (third-party apps). It does not cover **Intelligent UI**, the first-party, model-composed interface that shipped with GPT-6 on 2026-10-07, nine days before this note was written. Where this note says the model does not write the UI, that holds for Apps SDK widgets and not for ChatGPT in general. See [2026-10-21-chatgpt-intelligent-ui-rea.md](2026-10-21-chatgpt-intelligent-ui-rea.md).

## 1. What ChatGPT does (the Apps SDK, i.e. third-party apps)

**In the Apps SDK, the model does not write the UI.** ChatGPT's apps layer (the "Apps SDK", built on the Model Context Protocol) separates two things the model never mixes:

| Role | Who writes it | What it is |
|---|---|---|
| The tool call | The model | A name and arguments, chosen from tool descriptions |
| The UI | A developer, ahead of time | A bundled HTML/React component registered as a `ui://` resource |
| The data for the UI | The tool's server code | `structuredContent`, shown to the model and the widget; `_meta`, shown only to the widget |

How a turn runs, as the sources describe it:
1. A tool's metadata names its UI template (`_meta["openai/outputTemplate"]`, which points at a `ui://` URI; the newer standard field is `_meta.ui.resourceUri`). The host can fetch and vet the template before the tool runs. *(OpenAI reference snippet; MCP Apps spec; third-party guides.)*
2. The tool runs on the server and returns `structuredContent` plus `_meta`. The host renders the template in a sandboxed iframe and exposes the data to it as `window.openai.toolOutput` (props, in effect), with `toolInput` (the call arguments) and `toolResponseMetadata` beside it. *(OpenAI reference snippet.)*
3. The widget talks back through the host over `postMessage`, framed as JSON-RPC 2.0: it can call tools (`callTool`), send a follow-up message, persist UI state (`setWidgetState`, seen in one tutorial only), and ask for a display mode. The host mediates every UI-initiated tool call and may require approval. *(MCP Apps spec summary; third-party guides.)*
4. Display modes are inline (default, stays in history), fullscreen (chat bar remains) and picture-in-picture. The widget requests, the host decides, and picture-in-picture can be coerced to fullscreen on a phone. Resource metadata can declare available modes before load. *(OpenAI "15 lessons" post snippets; third-party reference; one GitHub issue says picture-in-picture fell back to fullscreen on desktop, which is a bug report, not confirmed behaviour.)*
5. Safety is by construction: sandboxed iframe, strict Content Security Policy, no privileged browser APIs (`alert`, `prompt`, `confirm`, clipboard), subframes blocked unless a domain is allow-listed in the resource's CSP metadata (`connectDomains`, `resourceDomains`, `frameDomains`). Inputs are validated server-side even if the model supplied them. *(OpenAI security page snippet; Skybridge docs.)*
6. Tools can be app-only (`_meta.ui.visibility: ["app"]`), hidden from the model, for UI plumbing such as refresh or pagination. Visibility is not a safety property: an app-only tool can still write data. *(Third-party SDK docs.)*
7. Discovery is metadata. Tool descriptions should be one or two sentences, usually "Use this when...", with each argument described and safe ranges or enums named. *(OpenAI "Define tools" snippet via search.)*
8. Hosts without UI support still show the tool's text result. *(MCP Apps summaries.)*

**The MCP Apps extension** (SEP-1865, `io.modelcontextprotocol/ui`, reported final on 2026-01-26) standardises the same design: `text/html;profile=mcp-app` resources, sandboxed iframes, JSON-RPC over `postMessage`, host-mediated tool calls and an audit log of UI-to-host requests, a `ui/resource-teardown` notification before teardown. Multiple UI resources per response and view-to-view communication are deferred. *(Spec summary and secondary articles; one guide claims the Apps SDK is deprecated in favour of MCP Apps, which I could not confirm.)*

## 2. The wider pattern: declarative and constrained generative UI

| Approach | Idea | Source type |
|---|---|---|
| Controlled | The agent picks from a pre-registered component library | Practitioner write-up |
| Declarative (Google A2UI) | The agent emits a JSON component tree; the client draws it from its own trusted catalog. The catalog is the security boundary. v0.9 stable, v1.0 release candidate | Repo and spec summaries |
| Open-ended | The agent writes UI code; needs a sandbox | Practitioner write-up |
| AG-UI | An event stream between agent and UI: text messages as start, content, end; tool calls as start, args, end; state as a snapshot plus JSON Patch deltas; run lifecycle events | SDK docs summaries |

Streaming findings: JSON cannot be parsed until it is complete, so one vendor reports a line-oriented intermediate language so UI can appear before the response ends (self-reported 50 to 67 percent fewer tokens, 2 to 3 times faster render; a conference submission, unverified). A separate talk argues for a delivery layer between model and interface: version-aware rendering contracts, progressive structured-UI streaming, and a backend-for-frontend for fallbacks. Google's 2025 work is cited as finding that users preferred generated HTML to markdown 83 percent of the time (second-hand).

## 3. What this means for Synapse

**The sharpest difference.** ChatGPT's widgets are authored by developers and are safe because the model only supplies data. Synapse lets a model write the page. Everything the platform gets for free (a vetted template, data as props) Synapse has to rebuild as verification. The way to get the platform's reliability back is to move the model's output as far toward data as the content allows.

**Design moves adopted (D-23):**

1. **Plan, then assemble, then fill.** The model's main output becomes a validated *plan* (data). A deterministic *assembler* turns the plan into HTML from a per-pattern *skeleton*. The model writes only small, typed *slot fills* for what the skeleton cannot express. This is "structuredContent into a template", with the template generated from audited parts.
2. **The Kit manifest is the tool-description layer.** ChatGPT discovers tools by "Use this when..." descriptions. The generator should discover micro-components the same way: every manifest entry gets a `useWhen` sentence, argument descriptions with safe ranges, and the kit pack is chosen by retrieval over those sentences.
3. **Model-visible and widget-only data are separate.** An Environment publishes a small model-visible summary (control values, readouts, task state) through the bridge for follow-ups; the audit record and the stored `checked` record are never given to the model.
4. **Fail early, with names.** A registry of fail checks gives every refusal a code, a layer, a repair route, a one-line hint for the model and a plain message for the student. Plan checks run before any HTML exists.
5. **Layers with a skeleton at both ends.** A structural skeleton for generation (above) and a loading skeleton for the student: the Peek card shell, title and study note appear from the plan before the Environment is verified.
6. **Stream in events, not blobs.** Reuse the P0 event stream shape (meta, text, environment, done) and add plan and progress events; state as deltas is a P6 option.
7. **Degrade to text.** The text answer always streams first, so a failed Environment still leaves a useful answer (the equivalent of a host without UI support).
8. **Host decides the presentation; the widget only requests.** This is already the Composer's rule (PRD 3.7).
9. **App-only operations.** UI plumbing (reset, record a result) must never be callable as model-visible actions. In Synapse the bridge events already behave this way; the manifest should mark each interaction as app-only.

**Where the PRD should be corrected.** PRD 3.7 and A-7 say Peek, Stage, Companion and Shelf are "adopted from OpenAI's display modes", and Peek is limited to "at most two actions, no tabs, no nested scrolling". The sources support inline, fullscreen and picture-in-picture, a preference for starting inline, and avoiding nested scrolling. They do **not** show an official "two actions" limit: that number appears only in a third-party reference. Peek's two-action limit is therefore our own design rule, informed by OpenAI's direction. A-7 is updated.

**Not adopted.** Running a widget with network access to developer domains (our CSP is `connect-src 'none'`). Letting the widget call model-visible tools directly. Treating the host as trusted for tool approval (single operator, D-11).

## 4. Primary pages to read locally (the container could not open them)

- OpenAI Apps SDK: reference (`window.openai` fields), "Define tools", UI guidelines and design guidelines, security and privacy.
- OpenAI developer blog, "15 lessons learned building ChatGPT Apps" (only its title and date reached me).
- MCP Apps specification, SEP-1865 and the `modelcontextprotocol/ext-apps` repository.
- Google A2UI repository and specification; the AG-UI event reference.

## Sources (search results, accessed 2026-10-16)

- [OpenAI Apps SDK reference](https://developers.openai.com/apps-sdk/reference)
- [OpenAI Apps SDK: Define tools](https://developers.openai.com/apps-sdk/plan/tools)
- [OpenAI Apps SDK: UI guidelines](https://developers.openai.com/apps-sdk/concepts/ui-guidelines)
- [OpenAI Apps SDK: Security and privacy](https://developers.openai.com/apps-sdk/guides/security-privacy)
- [OpenAI developer blog: 15 lessons learned building ChatGPT apps](https://developers.openai.com/blog/15-lessons-building-chatgpt-apps)
- [MCP SEP-1865: MCP Apps](https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp)
- [modelcontextprotocol/ext-apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- [Google A2UI](https://github.com/google/A2UI)
- [A2UI v0.8 A2A extension](https://a2ui.org/specification/v0.8-a2a-extension/)
- [CopilotKit AG-UI events](https://docs.copilotkit.ai/ag-ui/sdk/python/core/events)
- [A look at OpenAI's Apps SDK under the hood (MCPJam)](https://www.mcpjam.com/blog/apps-sdk-dive)
- [Inside OpenAI's Apps SDK (Alpic)](https://alpic.ai/blog/inside-openai-s-apps-sdk-how-to-build-interactive-chatgpt-apps-with-mcp)
- [ChatGPT App Display Mode Reference (sunpeak)](https://sunpeak.ai/blogs/chatgpt-app-display-mode-reference/)
- [MCP App Tool Metadata: resourceUri, visibility, and App-Only Tools (sunpeak)](https://sunpeak.ai/blogs/mcp-app-tool-meta-resource-uri-visibility/)
- [Skybridge: register widget](https://docs.skybridge.tech/api-reference/register-widget)
- [AI Engineer: Agent output is not UX, the rendering layer](https://ai.engineer/talks/agent-output-is-not-ux-rendering-layer-your-llm-pipeline-is-missing-bala-ramdoss-amazon-lens)
- [Generative UI in 2026: controlled, A2UI declarative, open-ended](https://mer.vin/linkedin/generative-ui-in-2026-controlled-a2ui-declarative-and-open-ended-patterns-on-ag-ui-linkedin/)
