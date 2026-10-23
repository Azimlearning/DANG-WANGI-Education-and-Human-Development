"use client";

import type { EnvironmentBlock } from "@synapse/schema";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { DegradedCard } from "../../../components/DegradedCard";
import { Peek } from "../../../components/Peek";
import { Stage } from "../../../components/Stage";
import { TopBar } from "../../../components/TopBar";
import { fetchEnvironment } from "../../../lib/library";
import { addRecent } from "../../../lib/recent";
import { AskError } from "../../../lib/stream";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** A shared Environment: fetched through the server's delivery gate, hash-checked again in the frame, shown with its provenance. */
export default function SharedEnvironment() {
  const { id } = useParams<{ id: string }>();
  const [block, setBlock] = useState<EnvironmentBlock | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [staged, setStaged] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchEnvironment(String(id), { baseUrl: API_BASE, signal: controller.signal })
      .then((b) => {
        setBlock(b);
        addRecent({ id: b.id, title: b.title });
      })
      .catch((err: unknown) => {
        if ((err as Error).name === "AbortError") return;
        setError(err instanceof AskError ? err.message : "Could not reach the server.");
      });
    return () => controller.abort();
  }, [id]);

  return (
    <>
      <TopBar />
      <main className="mx-auto grid max-w-2xl gap-4 p-4">
        {error ? <DegradedCard kind="error" message={error} /> : null}
        {!block && !error ? <p role="status" className="text-ink-dim">Loading…</p> : null}
        {block && !staged ? <Peek block={block} onOpen={() => setStaged(true)} /> : null}
        {block && staged ? <Stage block={block} onBack={() => setStaged(false)} /> : null}
      </main>
    </>
  );
}
