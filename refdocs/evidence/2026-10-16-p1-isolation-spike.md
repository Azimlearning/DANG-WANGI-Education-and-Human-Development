# P1 isolation spike (A-10)

> Run 2026-10-16 in the cloud container with `uv run python eval/isolation/spike.py`. It records what works in THIS container. It does not decide a public deploy.

## Question

A-10 assumed that verification can run generated HTML in headless Chromium inside a no-network container. The residual risk (D-17) is a request that fires only on a condition the harness never reaches: the page has already contacted the outside by the time anyone sees it. Only a process with no route to the outside closes that. Can the harness run that way, and what does it cost?

## What was run

The spike verifies the spring fixture end to end (scan, render, audit, sweep, mint) inside each option, and first probes whether a TCP connection to `1.1.1.1:443` and a DNS lookup succeed from inside.

| Option | Outbound TCP | DNS | Verification | Seconds |
|---|---|---|---|---|
| plain process | open (the container reaches out through its proxy) | blocked | minted | 2.7 |
| `unshare --net --map-root-user` | **blocked** | blocked | minted | 2.7 |
| `unshare --net --pid --fork --mount-proc --map-root-user` | **blocked** | blocked | minted | 2.8 |
| `prlimit --as=6GiB --cpu=120` | open | blocked | **failed**: Chromium would not launch | 0.4 |
| `unshare --net` plus `prlimit --cpu=120 --nproc=400` | **blocked** | blocked | minted | 2.7 |

## Findings

1. **A network namespace costs nothing measurable and verification still works.** The harness serves the page and the Kit from memory, so it needs no network. With `unshare --net`, a connection attempt fails immediately, and the full verification still mints in the same time.
2. **A PID namespace also works** with Chromium.
3. **An address-space limit (`RLIMIT_AS`) breaks Chromium**, which reserves a large virtual range at start. Use a CPU-time limit and a process-count limit, and bound memory with a cgroup (memory.max) in a real deploy rather than `RLIMIT_AS`. Not tried here: cgroup limits (this container exposes no writable cgroup tree).
4. The user namespace is mapped to root inside; the container's own Chromium sandbox flags are unchanged. A hardened deploy should not rely on running as root.

## What this does NOT show

- It does not show that Chromium itself is safe against a browser exploit. A no-network namespace removes the exfiltration route, not the exploit.
- It was run as root in a container, where unprivileged user namespaces are available. Many managed hosts (some serverless platforms, locked-down Kubernetes) forbid them.
- It did not measure memory exhaustion, a fork bomb, or a page that spins the CPU for the full budget.
- It did not test a rootless container runtime, gVisor or Firecracker.

## Options for the public deploy gate (D-11), cheapest first

| Option | Needs | What it closes |
|---|---|---|
| A. Run the verifier in a child process under `unshare --net` (+ cgroup memory and CPU limits) on the same host | unprivileged user namespaces; a cgroup tree or systemd scope | exfiltration from a page the harness did not trigger |
| B. A separate verifier service in a container with no egress rule at the network layer | a second deployable, a queue or HTTP call between them | the same, enforced outside the process; also isolates a browser crash |
| C. A microVM or gVisor sandbox per verification | a host that supports it | a browser exploit as well |

Recommendation: A for the owner's local and first hosted trials (it is a few lines and proven here), B before any public exposure. The choice, the host and the cost are the owner's at the deploy gate.

## Decision

A-10 is **partly confirmed**: no-network verification works and costs nothing at the harness. It stays an assumption for the exploit case. See DECISIONS A-10 and the checklist deploy gate.
