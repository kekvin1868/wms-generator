"use client";

import { useQuery } from "@tanstack/react-query";
import { Luggage } from "lucide-react";
import { api } from "@/lib/api";
import { StudioForm } from "@/components/studio-form";
import { Gallery } from "@/components/gallery";
import { ProgressBar } from "@/components/progress-bar";
import { HistoryDrawer } from "@/components/history-drawer";
import { useGenerationStream } from "@/hooks/use-generation-stream";

export default function HomePage() {
  const optionsQ = useQuery({ queryKey: ["options"], queryFn: api.options });
  const presetsQ = useQuery({ queryKey: ["presets"], queryFn: api.presets });
  const { state, start } = useGenerationStream();

  const busy = state.phase === "running";
  const images = state.phase === "done" ? state.result.images : [];
  const prompt = state.phase === "done" ? state.result.prompt : undefined;
  const seedUsed = state.phase === "done" ? state.result.seed_used : null;

  if (optionsQ.isLoading || presetsQ.isLoading) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-16 text-center text-sm text-[var(--color-muted-foreground)]">
        Connecting to backend at <code>http://localhost:8000</code>…
      </main>
    );
  }

  if (optionsQ.isError || presetsQ.isError || !optionsQ.data || !presetsQ.data) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="text-xl font-semibold">Backend not reachable</h1>
        <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
          Start it with <code>uvicorn backend.main:app --reload</code> and refresh.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <header className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Luggage className="h-7 w-7 text-[var(--color-primary)]" />
          <div>
            <h1 className="text-2xl font-bold leading-tight">Travel Bag Co. — AI Image Studio</h1>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Pick options, press the button. Images saved to <code>outputs/</code>.
            </p>
          </div>
        </div>
        <HistoryDrawer />
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <StudioForm
          options={optionsQ.data}
          presets={presetsQ.data}
          onSubmit={start}
          busy={busy}
        />

        <div className="space-y-4">
          {state.phase === "running" && <ProgressBar progress={state.progress} />}
          {state.phase === "error" && (
            <div className="rounded-lg border border-[var(--color-destructive)] bg-[var(--color-accent)] p-3 text-sm">
              <strong>Error:</strong> {state.message}
            </div>
          )}
          <Gallery images={images} prompt={prompt} />
          {seedUsed != null && (
            <div className="rounded-lg border bg-[var(--color-card)] p-3 text-sm">
              Seed used: <span className="font-semibold">{seedUsed}</span>{" "}
              <span className="text-[var(--color-muted-foreground)]">
                — type this into the Seed box to recreate these images.
              </span>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
