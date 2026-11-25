"use client";

import { useEffect, useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import type { VideoState } from "@/hooks/use-video-job";
import type { VideoQuota } from "@/lib/schemas";

const STATUS_TEXT = {
  sending: "Sending to video server… (first try after a quiet spell can take ~1 min)",
  queued: "Waiting in line…",
  running: "Rendering your clip…",
} as const;

export function VideoPanel({ state }: { state: VideoState }) {
  return (
    <div className="space-y-4">
      {state.phase === "running" && <Running status={state.status} startedAt={state.startedAt} />}
      {state.phase === "error" && (
        <div className="rounded-lg border border-[var(--color-destructive)] bg-[var(--color-accent)] p-3 text-sm">
          <strong>Error:</strong> {state.message}
        </div>
      )}
      {state.phase === "done" ? (
        <div className="space-y-2">
          <video
            src={state.job.url}
            controls
            autoPlay
            loop
            muted
            playsInline
            className="w-full rounded-lg border bg-black"
          />
          <p className="text-xs leading-relaxed text-[var(--color-muted-foreground)]">
            <span className="font-medium text-[var(--color-foreground)]">Prompt:</span> {state.job.prompt}
          </p>
        </div>
      ) : (
        <div className="flex h-[420px] items-center justify-center rounded-xl border border-dashed text-sm text-[var(--color-muted-foreground)]">
          Your video will appear here. Takes about 1–3 minutes.
        </div>
      )}
    </div>
  );
}

function Running({ status, startedAt }: { status: keyof typeof STATUS_TEXT; startedAt: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const secs = Math.max(0, Math.floor((now - startedAt) / 1000));
  const elapsed = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
  return (
    <div className="flex items-center justify-between rounded-lg border bg-[var(--color-card)] p-4 text-xs">
      <span className="flex items-center gap-2 font-medium">
        <Loader2 className="h-4 w-4 animate-spin" /> {STATUS_TEXT[status]}
      </span>
      <span className="tabular-nums text-[var(--color-muted-foreground)]">{elapsed}</span>
    </div>
  );
}

export function VideoQuotaNote({ query }: { query: UseQueryResult<VideoQuota> }) {
  if (query.isLoading) {
    return <p className="text-sm text-[var(--color-muted-foreground)]">Checking your video quota…</p>;
  }
  if (query.isError) {
    return <p className="text-sm text-[var(--color-destructive)]">{(query.error as Error).message}</p>;
  }
  if (!query.data) return null;
  const { left, quota } = query.data;
  return (
    <p className="text-sm text-[var(--color-muted-foreground)]">
      <span className={`font-semibold ${left === 0 ? "text-[var(--color-destructive)]" : "text-[var(--color-foreground)]"}`}>
        {left} of {quota}
      </span>{" "}
      clips left this month · each clip is 10 s at 1080p
    </p>
  );
}
