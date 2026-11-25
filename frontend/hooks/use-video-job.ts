"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { VideoForm, VideoJob } from "@/lib/schemas";

const POLL_MS = 5000;
const MAX_POLL_ERRORS = 12; // ~1 min of failed polls in a row (server waking, network blip)

export type VideoState =
  | { phase: "idle" }
  | { phase: "running"; status: "sending" | "queued" | "running"; startedAt: number }
  | { phase: "done"; job: VideoJob }
  | { phase: "error"; message: string };

export function useVideoJob(onFinished?: () => void) {
  const [state, setState] = useState<VideoState>({ phase: "idle" });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stop = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  }, []);

  useEffect(() => stop, [stop]);

  const start = useCallback(
    async (form: VideoForm) => {
      stop();
      const startedAt = Date.now();
      setState({ phase: "running", status: "sending", startedAt });
      let jobId: string;
      try {
        jobId = (await api.videoSubmit(form)).job_id;
      } catch (err) {
        setState({ phase: "error", message: (err as Error).message });
        onFinished?.();
        return;
      }

      let errors = 0;
      const poll = async () => {
        try {
          const job = await api.videoStatus(jobId);
          if (job.status === "done") {
            setState({ phase: "done", job });
            onFinished?.();
            return;
          }
          if (job.status === "failed") {
            setState({ phase: "error", message: job.error ?? "Video generation failed" });
            onFinished?.();
            return;
          }
          errors = 0;
          setState({ phase: "running", status: job.status, startedAt });
        } catch (err) {
          if (++errors >= MAX_POLL_ERRORS) {
            setState({ phase: "error", message: (err as Error).message });
            onFinished?.();
            return;
          }
        }
        timer.current = setTimeout(poll, POLL_MS);
      };
      poll();
    },
    [stop, onFinished],
  );

  return { state, start };
}
